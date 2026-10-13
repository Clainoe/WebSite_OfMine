"""
网站管理系统 - 业务操作模块
包含：录入、查询、弃用（假删除）、恢复、按 id 获取。
"""

import datetime

from wm.db import get_conn, init_db
from wm.utils import normalize_url


# -------------------- 录入 --------------------
def add_site(data: dict) -> tuple[bool, str]:
    """
    录入一个网站。
    data 需包含: site_name, url；可选: function, remarks。
    返回 (成功与否, 提示信息)。
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
            VALUES (?, ?, ?, ?, '在用', ?)
            """,
            (
                name,
                url,
                str(data.get("function") or "").strip(),
                str(data.get("remarks") or "").strip(),
                datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            ),
        )
        conn.commit()
    except Exception as e:  # noqa: BLE001
        return False, f"录入失败：{e}"
    finally:
        conn.close()

    return True, f"网站【{name}】录入成功"


# -------------------- 查询 --------------------
def query_sites(include_deprecated: bool = False, keyword: str = "", field: str = "all") -> list:
    """
    查询网站。
    include_deprecated=False（默认）时只返回「在用」记录（已弃用的自动隐藏）。
    field 可选：all / site_name / function / url
    """
    init_db()
    sql = "SELECT * FROM sites WHERE 1=1"
    params = []

    if not include_deprecated:
        sql += " AND status = '在用'"

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


def get_site(site_id: int) -> dict | None:
    """按 id 获取单个网站。"""
    init_db()
    conn = get_conn()
    try:
        row = conn.execute("SELECT * FROM sites WHERE id = ?", (site_id,)).fetchone()
    finally:
        conn.close()
    return dict(row) if row else None


# -------------------- 弃用（假删除）--------------------
def deprecate_site(site_id: int, reason: str) -> tuple[bool, str]:
    """
    假删除：把状态改成「已弃用」，并记录弃用原因与弃用时间。
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
        if row["status"] == "已弃用":
            return False, f"网站【{row['site_name']}】已是弃用状态"

        conn.execute(
            """
            UPDATE sites
            SET status = '已弃用', deprecate_reason = ?, deprecate_time = ?
            WHERE id = ?
            """,
            (
                reason,
                datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                site_id,
            ),
        )
        conn.commit()
        name = row["site_name"]
    finally:
        conn.close()

    return True, f"网站【{name}】已弃用"


# -------------------- 恢复 --------------------
def restore_site(site_id: int) -> tuple[bool, str]:
    """把已弃用的网站恢复为「在用」。"""
    init_db()
    conn = get_conn()
    try:
        row = conn.execute(
            "SELECT id, site_name, status FROM sites WHERE id = ?", (site_id,)
        ).fetchone()
        if row is None:
            return False, f"未找到序号为 {site_id} 的网站"
        if row["status"] != "已弃用":
            return False, f"网站【{row['site_name']}】本来就未弃用"

        conn.execute(
            """
            UPDATE sites
            SET status = '在用', deprecate_reason = NULL, deprecate_time = NULL
            WHERE id = ?
            """,
            (site_id,),
        )
        conn.commit()
        name = row["site_name"]
    finally:
        conn.close()

    return True, f"网站【{name}】已恢复为在用"


def batch_restore(ids: list[int]) -> tuple[int, list[str]]:
    """批量恢复，返回 (成功条数, 失败消息列表)。"""
    success, failed = 0, []
    for site_id in ids:
        ok, msg = restore_site(site_id)
        if ok:
            success += 1
        else:
            failed.append(msg)
    return success, failed