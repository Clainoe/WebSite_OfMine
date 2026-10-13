"""网站管理系统 —— 通用工具函数。

本模块只包含不依赖业务状态的纯函数，可被其余模块安全复用。

Functions:
    normalize_url: 补全网址的协议头，使其可直接跳转。
    display_width: 估算字符串的显示宽度，中文按 2 个字符宽计算。

Example:
    补全协议头后即可直接交给浏览器打开::

        >>> normalize_url("www.example.com")
        'https://www.example.com'
"""

from __future__ import annotations

__all__ = ["normalize_url", "display_width"]

#: 视为「已带协议」的前缀。命中其中任意一个即不再补全。
_URL_SCHEMES = ("http://", "https://", "ftp://", "file://")

#: 判定为「宽字符」的码点下限。中日韩文字、全角符号等均超过该值。
_WIDE_CHAR_THRESHOLD = 127


def normalize_url(url: str | None) -> str:
    """补全网址的协议头，使其可直接用于浏览器跳转。

    Args:
        url: 待处理的网址。允许不带协议头（如 ``www.example.com``），
            也允许传入 ``None`` 或仅含空白字符的字符串。

    Returns:
        补全协议头后的网址；若入参为空或仅含空白字符，则返回空字符串。

    Example:
        >>> normalize_url("www.example.com")
        'https://www.example.com'
        >>> normalize_url("http://example.com")
        'http://example.com'
    """
    url = (url or "").strip()
    if not url:
        return url
    if not url.lower().startswith(_URL_SCHEMES):
        url = "https://" + url
    return url


def display_width(text: object) -> int:
    """估算字符串的显示宽度，用于设置 Excel 列宽。

    中文、全角符号等非 ASCII 字符在等宽环境下约占 2 个字符宽，
    因此以 ``ord(ch) > 127`` 判定，命中则计为 2。

    Args:
        text: 任意对象。内部会先转为字符串，再逐字符累计宽度。

    Returns:
        估算出的显示宽度（以半角字符为单位）。
    """
    width = 0
    for ch in str(text):
        width += 2 if ord(ch) > _WIDE_CHAR_THRESHOLD else 1
    return width
