"""网站管理系统 —— 数据库访问层。

本模块负责 SQLite 数据库的连接管理与表结构初始化。数据库文件
``websites.db`` 与 ``wm`` 包位于同一目录，首次访问时自动创建。

Note:
    数据库属于本地数据（含个人网址记录），已通过 ``.gitignore`` 排除，
    不纳入版本控制。

Attributes:
    DB_PATH (str): 数据库文件的绝对路径。
"""

from __future__ import annotations

import os
import sqlite3

__all__ = ["DB_PATH", "get_conn", "init_db"]

#: 数据库文件路径。固定为 wm 包所在目录，保证无论从哪个工作目录启动，
#: 程序访问的都是同一个库文件。
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "websites.db")

#: ``sites`` 表建表语句。字段含义见 :func:`init_db` 的说明。
_CREATE_SITES_TABLE = """
CREATE TABLE IF NOT EXISTS sites (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    site_name         TEXT NOT NULL,                 -- 网站名
    url               TEXT NOT NULL,                 -- 网址
    function          TEXT,                          -- 功能
    remarks           TEXT,                          -- 备注
    status            TEXT NOT NULL DEFAULT '在用',  -- 状态：在用 / 已弃用
    deprecate_reason  TEXT,                          -- 弃用原因
    deprecate_time    TEXT,                          -- 弃用时间
    created_at        TEXT NOT NULL                  -- 录入时间
)
"""


def get_conn() -> sqlite3.Connection:
    """创建并返回一个数据库连接。

    连接的 ``row_factory`` 被设为 :class:`sqlite3.Row`，因此查询结果
    既支持下标访问，也支持按列名访问（如 ``row["site_name"]``）。

    Returns:
        已就绪的 SQLite 连接对象。调用方负责在使用结束后关闭它。

    Note:
        每次调用都会新建连接，不做共享或缓存，以避免多线程下的竞态。
    """
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """初始化数据库，确保 ``sites`` 表存在。

    建表语句使用 ``CREATE TABLE IF NOT EXISTS``，因此本函数是幂等的，
    可以在每次业务操作前安全地重复调用。

    ``sites`` 表字段说明：

    - ``id``：主键，自增序号
    - ``site_name``：网站名（必填）
    - ``url``：网址（必填）
    - ``function``：功能分类
    - ``remarks``：备注
    - ``status``：状态，取值 ``在用`` 或 ``已弃用``，默认为 ``在用``
    - ``deprecate_reason``：弃用原因
    - ``deprecate_time``：弃用时间
    - ``created_at``：录入时间
    """
    conn = get_conn()
    try:
        conn.execute(_CREATE_SITES_TABLE)
        conn.commit()
    finally:
        conn.close()


if __name__ == "__main__":
    init_db()
    print(f"数据库已初始化：{DB_PATH}")
