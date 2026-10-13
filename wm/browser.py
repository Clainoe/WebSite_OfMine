"""网站管理系统 —— 浏览器跳转模块。

负责把网址交给浏览器打开，跳转优先级依次为：

1. 常见安装路径下的 Microsoft Edge（见 :data:`EDGE_PATHS`）
2. ``PATH`` 中可直接调用的 ``msedge``
3. 系统默认浏览器（:mod:`webbrowser`）

Functions:
    open_in_edge: 按上述优先级打开网址。
"""

from __future__ import annotations

import os
import shutil
import subprocess
import webbrowser

from wm.utils import normalize_url

__all__ = ["EDGE_PATHS", "open_in_edge"]

#: 常见的 Edge 安装路径，按优先级排列。
#: ``%LOCALAPPDATA%`` 一项会在导入时展开为当前用户的实际路径。
EDGE_PATHS = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Edge\Application\msedge.exe"),
]


def open_in_edge(url: str) -> tuple[bool, str]:
    """用 Edge 打开网址；找不到 Edge 时回退到系统默认浏览器。

    Args:
        url: 目标网址，允许不带协议头（内部会先补全）。

    Returns:
        二元组 ``(是否成功, 提示信息)``。提示信息会说明实际使用了
        Edge 还是默认浏览器，可直接展示给用户。
    """
    url = normalize_url(url)
    if not url:
        return False, "网址为空，无法跳转"

    # 1) 常见安装路径
    for path in EDGE_PATHS:
        if path and os.path.exists(path):
            try:
                subprocess.Popen([path, url])
                return True, f"已通过 Edge 打开：{url}"
            except Exception as e:  # noqa: BLE001
                return False, f"启动 Edge 失败：{e}"

    # 2) 已加入 PATH 的 msedge
    if shutil.which("msedge"):
        try:
            subprocess.Popen(["msedge", url])
            return True, f"已通过 Edge 打开：{url}"
        except Exception:  # noqa: BLE001
            pass

    # 3) 兜底：系统默认浏览器
    try:
        webbrowser.open(url)
        return True, f"未找到 Edge，已使用默认浏览器打开：{url}"
    except Exception as e:  # noqa: BLE001
        return False, f"打开失败：{e}"
