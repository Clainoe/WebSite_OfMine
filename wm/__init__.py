"""网站管理系统 —— 业务逻辑包（``wm`` = Website Manager）。

界面层（``main.py``）只负责展示与交互，全部数据与业务逻辑都由本包提供。

Modules:
    db: 数据库连接与表结构初始化。
    operations: 网站记录的录入、查询、弃用与恢复。
    browser: 调用 Edge（或默认浏览器）打开网址。
    export: 将查询结果导出为 Excel。
    dialogs: 录入与弃用确认对话框。
    utils: 与业务无关的通用工具函数。
"""

from __future__ import annotations

__all__ = ["__version__"]

#: 包版本号，与 ``git tag`` 保持一致。
__version__ = "1.0.0"
