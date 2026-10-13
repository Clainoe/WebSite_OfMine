"""网站管理系统 —— Excel 导出模块。

把查询结果导出为带表头样式的 ``.xlsx`` 工作簿，并根据内容自动调整列宽。

Dependencies:
    openpyxl: 导出功能依赖该第三方库，安装方式见 ``requirements.txt``。

Functions:
    save_to_excel: 将记录列表写入指定路径的 Excel 文件。
"""

from __future__ import annotations

from typing import Any

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from wm.utils import display_width

__all__ = ["EXPORT_COLUMNS", "save_to_excel"]

#: 导出列定义，元素为 ``(数据库字段名, 表头文字)``，顺序即导出后的列顺序。
EXPORT_COLUMNS = [
    ("id", "序号"),
    ("site_name", "网站名"),
    ("url", "网址"),
    ("function", "功能"),
    ("remarks", "备注"),
    ("status", "状态"),
    ("deprecate_reason", "弃用原因"),
    ("deprecate_time", "弃用时间"),
]

#: 表头样式：白字、加粗、深蓝底
_HEADER_FONT = Font(bold=True, color="FFFFFF")
_HEADER_FILL = PatternFill("solid", fgColor="4472C4")

#: 列宽上限，避免超长网址把表格撑得过宽
_MAX_COLUMN_WIDTH = 50

#: 列宽在内容宽度基础上额外留出的余量
_COLUMN_WIDTH_PADDING = 4


def save_to_excel(records: list[dict[str, Any]], path: str) -> None:
    """把记录列表写入 Excel 文件。

    工作表命名为「网站清单」，首行为带样式的表头，随后依次写入数据行。
    列宽按内容宽度自动计算（中文按 2 个字符宽估算），并受
    :data:`_MAX_COLUMN_WIDTH` 限制。

    Args:
        records: 记录列表，每项为「字段名 -> 值」的字典，字段名需与
            :data:`EXPORT_COLUMNS` 对应。
        path: 目标 ``.xlsx`` 文件的保存路径，会被直接覆盖。

    Raises:
        OSError: 目标路径不可写时由 :meth:`openpyxl.Workbook.save` 抛出。
    """
    wb = Workbook()
    ws = wb.active
    ws.title = "网站清单"

    # 表头
    for col_idx, (_key, label) in enumerate(EXPORT_COLUMNS, start=1):
        cell = ws.cell(row=1, column=col_idx, value=label)
        cell.font = _HEADER_FONT
        cell.fill = _HEADER_FILL
        cell.alignment = Alignment(horizontal="center", vertical="center")

    # 数据行
    for row_idx, rec in enumerate(records, start=2):
        for col_idx, (key, _label) in enumerate(EXPORT_COLUMNS, start=1):
            value = rec.get(key)
            ws.cell(row=row_idx, column=col_idx, value="" if value is None else value)

    # 自动列宽：取表头与所有数据行中最大显示宽度
    for col_idx, (key, label) in enumerate(EXPORT_COLUMNS, start=1):
        max_len = display_width(label)
        for rec in records:
            max_len = max(max_len, display_width(rec.get(key) or ""))
        ws.column_dimensions[get_column_letter(col_idx)].width = min(
            max_len + _COLUMN_WIDTH_PADDING, _MAX_COLUMN_WIDTH
        )

    wb.save(path)
