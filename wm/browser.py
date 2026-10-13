"""
网站管理系统 - 浏览器跳转模块
优先使用 Edge 打开，找不到时回退到系统默认浏览器。
"""

import os
import shutil
import subprocess
import webbrowser

from wm.utils import normalize_url

# 常见的 Edge 安装路径
EDGE_PATHS = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Edge\Application\msedge.exe"),
]


def open_in_edge(url: str) -> tuple[bool, str]:
    """优先用 Edge 打开；找不到 Edge 时回退到系统默认浏览器。"""
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