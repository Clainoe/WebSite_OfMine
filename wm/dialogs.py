"""网站管理系统 —— 弹窗对话框。

本模块提供两个模态对话框：

- :class:`AddSiteDialog`: 录入新网站，网站名与网址为必填项。
- :class:`ReasonDialog`: 填写弃用原因，原因为必填项。

两者均继承自 :class:`tkinter.Toplevel`，通过 ``transient`` + ``grab_set``
实现模态效果；确认后由调用方通过回调刷新列表。
"""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from tkinter import messagebox, ttk

from wm.operations import add_site

__all__ = ["AddSiteDialog", "ReasonDialog"]


def _center_over(master: tk.Misc, window: tk.Toplevel) -> None:
    """把窗口定位到父窗口的偏上居中位置。

    Args:
        master: 父窗口，作为定位参照。
        window: 待定位的窗口（通常是对话框自身）。
    """
    x = master.winfo_rootx() + (master.winfo_width() - window.winfo_width()) // 2
    y = master.winfo_rooty() + (master.winfo_height() - window.winfo_height()) // 3
    window.geometry(f"+{max(x, 0)}+{max(y, 0)}")


class AddSiteDialog(tk.Toplevel):
    """录入对话框：网站名与网址必填，其余字段可选。

    Attributes:
        on_saved (Callable[[], None]): 保存成功后的回调，用于让主窗口刷新列表。
        var_name (tk.StringVar): 网站名输入值。
        var_url (tk.StringVar): 网址输入值。
        var_func (tk.StringVar): 功能输入值。
        var_rem (tk.StringVar): 备注输入值。
    """

    def __init__(self, master: tk.Misc, on_saved: Callable[[], None]) -> None:
        """构建并显示录入对话框。

        Args:
            master: 父窗口。
            on_saved: 保存成功后的回调（通常为 ``主窗口.refresh``）。
        """
        super().__init__(master)
        self.on_saved = on_saved
        self.title("添加网站")
        self.resizable(False, False)
        self.transient(master)
        self.grab_set()

        body = ttk.Frame(self, padding=16)
        body.pack(fill="both", expand=True)

        ttk.Label(
            body, text="带 * 为必填项", foreground="#666666"
        ).grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 10))

        self.var_name = tk.StringVar()
        self.var_url = tk.StringVar()
        self.var_func = tk.StringVar()
        self.var_rem = tk.StringVar()

        rows = [
            ("网站名 *", self.var_name, "必填"),
            ("网址 *", self.var_url, "如 www.baidu.com，自动补 https://"),
            ("功能", self.var_func, "选填，如 查资料"),
            ("备注", self.var_rem, "选填"),
        ]

        for i, (label, var, hint) in enumerate(rows, start=1):
            ttk.Label(body, text=label).grid(row=i, column=0, sticky="e", padx=(0, 8), pady=5)
            entry = ttk.Entry(body, textvariable=var, width=36)
            entry.grid(row=i, column=1, sticky="w", pady=5)
            ttk.Label(body, text=hint, foreground="#999999").grid(
                row=i, column=2, sticky="w", padx=(8, 0)
            )
            if i == 1:
                entry.focus_set()

        btns = ttk.Frame(body)
        btns.grid(row=len(rows) + 1, column=0, columnspan=3, sticky="e", pady=(16, 0))
        ttk.Button(btns, text="保存", command=self._save).pack(side="right", padx=(8, 0))
        ttk.Button(btns, text="取消", command=self.destroy).pack(side="right")

        self.bind("<Return>", lambda _e: self._save())
        self.bind("<Escape>", lambda _e: self.destroy())

        self.update_idletasks()
        _center_over(master, self)

    def _save(self) -> None:
        """校验并提交录入请求。

        校验与写库由 :func:`wm.operations.add_site` 完成；成功时回调
        ``on_saved`` 并关闭对话框，失败时以错误弹窗提示且保持对话框打开。
        """
        data = {
            "site_name": self.var_name.get().strip(),
            "url": self.var_url.get().strip(),
            "function": self.var_func.get().strip(),
            "remarks": self.var_rem.get().strip(),
        }
        ok, msg = add_site(data)
        if ok:
            messagebox.showinfo("成功", msg, parent=self)
            self.on_saved()
            self.destroy()
        else:
            messagebox.showerror("失败", msg, parent=self)


class ReasonDialog(tk.Toplevel):
    """弃用原因对话框：必须填写原因后才能确认。

    Attributes:
        on_ok (Callable[[str], None]): 确认后的回调，入参为用户填写的原因。
        text (tk.Text): 原因输入框。
    """

    def __init__(self, master: tk.Misc, count: int, on_ok: Callable[[str], None]) -> None:
        """构建并显示弃用确认对话框。

        Args:
            master: 父窗口。
            count: 本次将要弃用的网站数量，仅用于提示文案。
            on_ok: 确认后的回调，入参为去除首尾空白的原因文本。
        """
        super().__init__(master)
        self.on_ok = on_ok
        self.title("弃用确认")
        self.resizable(False, False)
        self.transient(master)
        self.grab_set()

        body = ttk.Frame(self, padding=16)
        body.pack(fill="both", expand=True)

        ttk.Label(
            body,
            text=f"即将弃用 {count} 个网站，请填写弃用原因（必填）：",
        ).pack(anchor="w")

        self.text = tk.Text(body, width=46, height=6, wrap="word")
        self.text.pack(fill="both", expand=True, pady=(8, 12))
        self.text.focus_set()

        btns = ttk.Frame(body)
        btns.pack(fill="x")
        ttk.Button(btns, text="确认弃用", command=self._ok).pack(side="right", padx=(8, 0))
        ttk.Button(btns, text="取消", command=self.destroy).pack(side="right")

        self.bind("<Escape>", lambda _e: self.destroy())

        self.update_idletasks()
        _center_over(master, self)

    def _ok(self) -> None:
        """校验原因非空后触发回调并关闭对话框。

        原因为空时仅弹出提示，不关闭对话框，以便用户继续填写。
        """
        reason = self.text.get("1.0", "end").strip()
        if not reason:
            messagebox.showwarning("提示", "请填写弃用原因", parent=self)
            return
        self.on_ok(reason)
        self.destroy()
