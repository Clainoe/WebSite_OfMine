"""
网站管理系统 - 数据库模块
负责数据库的初始化与连接管理。
"""

import os
import sqlite3

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "websites.db")


def get_conn():
    """获取数据库连接（自动创建库文件）。"""
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """初始化数据库，首次运行时创建 sites 表。"""
    conn = get_conn()
    conn.execute(
        """
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
    )
    conn.commit()
    conn.close()


if __name__ == "__main__":
    init_db()
    print(f"数据库已初始化：{DB_PATH}")