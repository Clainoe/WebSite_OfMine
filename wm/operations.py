"""网站管理系统 —— 业务操作模块。

本模块封装对网站记录的全部业务操作，是界面层与数据库层之间的唯一
通道。所有对外函数都返回「显式的成功标志 + 人类可读的提示信息」，
界面层可直接展示返回值，无需依赖异常来控制流程。

Functions:
    add_site: 录入一个新网站。
    query_sites: 按条件查询网站记录。
    get_site: 按主键获取单条记录。
    deprecate_site: 弃用（假删除）一个网站。
    restore_site: 把已弃用的网站恢复为在用。
    batch_restore: 批量恢复多个网站。
"""

from __future__ import annotations

import datetime
from typing import Any

from wm.db import get_conn, init_db
from wm.utils import normalize_url

__all__ = [
    "add_site",
    "query_sites",
    "get_site",
    "deprecate_site",
    "restore_site",
    "batch_restore",
]

#: 状态取值：在用
STATUS_ACTIVE = "在用"

#: 状态取值：已弃用
STATUS_DEPRECATED = "已弃用"

#: 时间字段统一使用的格式
_TIME_FORMAT = "%Y-%m-%d %H:%M:%S"


def _now() -> str:
    """返回当前时间的字符串表示。

    Returns:
        形如 ``2026-10-13 15:58:46`` 的时间字符串。
    """
    return datetime.datetime.now().strftime(_TIME_FORMAT)


# -------------------- 录入 --------------------
def add_site(data: dict[str, Any]) -> tuple[bool, str]:
    """录入一个新网站。

    Args:
        data: 记录字段字典。必填 ``site_name``、``url``；可选 ``function``、
            ``remarks``。字段缺失或为 ``None`` 时按空字符串处理，
            网址会自动补全协议头。

    Returns:
        二元组 ``(是否成功, 提示信息)``，提示信息可直接展示给用户。

    Note:
        本函数不抛出异常；数据库写入失败时以 ``(False, 错误说明)`` 返回。
    """
    name = str(data.get("site_name") or "").strip()
    if not name:
        return False, "网站名不能为空"

    raw_url = str(data.get("url") or "").strip()
    if not raw_url:
        return False, "网址不能为空，否则无法跳转"
    url = normalize_url(raw_url)

    init_db()
    conn = get_conn()
    try:
        conn.execute(
            """
            INSERT INTO sites
            (site_name, url, function, remarks, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                name,
                url,
                str(data.get("function") or "").strip(),
                str(data.get("remarks") or "").strip(),
                STATUS_ACTIVE,
                _now(),
            ),
        )
        conn.commit()
    except Exception as e:  # noqa: BLE001
        return False, f"录入失败：{e}"
    finally:
        conn.close()

    return True, f"网站【{name}】录入成功"


# -------------------- 查询 --------------------
def query_sites(
    include_deprecated: bool = False,
    keyword: str = "",
    field: str = "all",
) -> list[dict[str, Any]]:
    """按条件查询网站记录。

    Args:
        include_deprecated: 是否包含已弃用记录。为 ``False``（默认）时
            只返回状态为「在用」的记录。
        keyword: 关键词，匹配方式为 ``LIKE %keyword%``。空字符串表示
            不做关键词筛选。
        field: 关键词的匹配范围，可选值：

            - ``"all"``（默认）：网站名、网址、功能、备注四列全部参与匹配
            - ``"site_name"``：仅匹配网站名
            - ``"function"``：仅匹配功能
            - ``"url"``：仅匹配网址

    Returns:
        匹配到的记录列表，按 ``id`` 升序排列；每条记录为「列名 -> 值」
        的字典。无匹配结果时返回空列表。
    """
    init_db()
    sql = "SELECT * FROM sites WHERE 1=1"
    params: list[Any] = []

    if not include_deprecated:
        sql += " AND status = ?"
        params.append(STATUS_ACTIVE)

    kw = (keyword or "").strip()
    if kw:
        like = f"%{kw}%"
        if field == "site_name":
            sql += " AND site_name LIKE ?"
            params.append(like)
        elif field == "function":
            sql += " AND function LIKE ?"
            params.append(like)
        elif field == "url":
            sql += " AND url LIKE ?"
            params.append(like)
        else:
            sql += " AND (site_name LIKE ? OR url LIKE ? OR function LIKE ? OR remarks LIKE ?)"
            params.extend([like, like, like, like])

    sql += " ORDER BY id ASC"

    conn = get_conn()
    try:
        rows = conn.execute(sql, params).fetchall()
    finally:
        conn.close()
    return [dict(r) for r in rows]


def get_site(site_id: int) -> dict[str, Any] | None:
    """按主键获取单个网站记录。

    Args:
        site_id: 网站记录的主键 ``id``。

    Returns:
        记录字段字典；若指定 ``id`` 不存在则返回 ``None``。
    """
    init_db()
    conn = get_conn()
    try:
        row = conn.execute("SELECT * FROM sites WHERE id = ?", (site_id,)).fetchone()
    finally:
        conn.close()
    return dict(row) if row else None


# -------------------- 弃用（假删除）--------------------
def deprecate_site(site_id: int, reason: str) -> tuple[bool, str]:
    """弃用一个网站（假删除）。

    所谓「假删除」即不物理删除数据，而是把 ``status`` 置为
    ``已弃用``，同时记录弃用原因与弃用时间。已弃用记录默认不在列表中
    显示，但可通过「包含已弃用」选项或「恢复在用」找回。

    Args:
        site_id: 目标网站的主键 ``id``。
        reason: 弃用原因，必填；仅含空白字符视为未填写。

    Returns:
        二元组 ``(是否成功, 提示信息)``。记录不存在、已是弃用状态或
        原因为空时，均返回 ``False`` 及相应说明。
    """
    reason = (reason or "").strip()
    if not reason:
        return False, "请填写弃用原因"

    init_db()
    conn = get_conn()
    try:
        row = conn.execute(
            "SELECT id, site_name, status FROM sites WHERE id = ?", (site_id,)
        ).fetchone()
        if row is None:
            return False, f"未找到序号为 {site_id} 的网站"
        if row["status"] == STATUS_DEPRECATED:
            return False, f"网站【{row['site_name']}】已是弃用状态"

        conn.execute(
            """
            UPDATE sites
            SET status = ?, deprecate_reason = ?, deprecate_time = ?
            WHERE id = ?
            """,
            (STATUS_DEPRECATED, reason, _now(), site_id),
        )
        conn.commit()
        name = row["site_name"]
    finally:
        conn.close()

    return True, f"网站【{name}】已弃用"


# -------------------- 恢复 --------------------
def restore_site(site_id: int) -> tuple[bool, str]:
    """把已弃用的网站恢复为「在用」。

    恢复时会一并清空 ``deprecate_reason`` 与 ``deprecate_time``。

    Args:
        site_id: 目标网站的主键 ``id``。

    Returns:
        二元组 ``(是否成功, 提示信息)``。记录不存在或本身未弃用时，
        返回 ``False`` 及相应说明。
    """
    init_db()
    conn = get_conn()
    try:
        row = conn.execute(
            "SELECT id, site_name, status FROM sites WHERE id = ?", (site_id,)
        ).fetchone()
        if row is None:
            return False, f"未找到序号为 {site_id} 的网站"
        if row["status"] != STATUS_DEPRECATED:
            return False, f"网站【{row['site_name']}】本来就未弃用"

        conn.execute(
            """
            UPDATE sites
            SET status = ?, deprecate_reason = NULL, deprecate_time = NULL
            WHERE id = ?
            """,
            (STATUS_ACTIVE, site_id),
        )
        conn.commit()
        name = row["site_name"]
    finally:
        conn.close()

    return True, f"网站【{name}】已恢复为在用"


def batch_restore(ids: list[int]) -> tuple[int, list[str]]:
    """批量恢复多个网站。

    Args:
        ids: 待恢复记录的主键列表。

    Returns:
        二元组 ``(成功条数, 失败信息列表)``。失败信息可直接拼接展示。
    """
    success, failed = 0, []
    for site_id in ids:
        ok, msg = restore_site(site_id)
        if ok:
            success += 1
        else:
            failed.append(msg)
    return success, failed
