"""
网站管理系统 - 通用工具函数
"""


def normalize_url(url: str) -> str:
    """补全协议头，方便直接跳转。"""
    url = (url or "").strip()
    if not url:
        return url
    if not url.lower().startswith(("http://", "https://", "ftp://", "file://")):
        url = "https://" + url
    return url


def display_width(text) -> int:
    """中文按 2 个字符宽度估算，用于设置 Excel 列宽。"""
    width = 0
    for ch in str(text):
        width += 2 if ord(ch) > 127 else 1
    return width