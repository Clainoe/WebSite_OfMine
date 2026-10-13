"""
网站管理系统 - Excel 导出模块
"""

from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill
from openpyxl.utils import get_column_letter

from wm.utils import display_width

# 导出列定义 (key, 表头, 建议宽度)
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


def save_to_excel(records: list, path: str):
    """把记录写入 Excel 文件。"""
    wb = Workbook()
    ws = wb.active
    ws.title = "网站清单"

    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill("solid", fgColor="4472C4")

    # 表头
    for col_idx, (_key, label) in enumerate(EXPORT_COLUMNS, start=1):
        cell = ws.cell(row=1, column=col_idx, value=label)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center", vertical="center")

    # 数据
    for row_idx, rec in enumerate(records, start=2):
        for col_idx, (key, _label) in enumerate(EXPORT_COLUMNS, start=1):
            value = rec.get(key)
            ws.cell(row=row_idx, column=col_idx, value="" if value is None else value)

    # 自动列宽（中文按 2 字符宽估算）
    for col_idx, (key, label) in enumerate(EXPORT_COLUMNS, start=1):
        max_len = display_width(label)
        for rec in records:
            max_len = max(max_len, display_width(rec.get(key) or ""))
        ws.column_dimensions[get_column_letter(col_idx)].width = min(max_len + 4, 50)

    wb.save(path)