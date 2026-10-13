"""
网站管理系统 - 弹窗对话框
包含：添加网站对话框、弃用原因对话框。
"""

import tkinter as tk
from tkinter import ttk, messagebox

from wm.operations import add_site


class AddSiteDialog(tk.Toplevel):
    """录入对话框：网站名和网址必填，其余可选。"""

    def __init__(self, master, on_saved):
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
        self._center_on(master)

    def _center_on(self, master):
        x = master.winfo_rootx() + (master.winfo_width() - self.winfo_width()) // 2
        y = master.winfo_rooty() + (master.winfo_height() - self.winfo_height()) // 3
        self.geometry(f"+{max(x, 0)}+{max(y, 0)}")

    def _save(self):
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
    """弃用原因对话框：必须填写原因。"""

    def __init__(self, master, count: int, on_ok):
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
        x = master.winfo_rootx() + (master.winfo_width() - self.winfo_width()) // 2
        y = master.winfo_rooty() + (master.winfo_height() - self.winfo_height()) // 3
        self.geometry(f"+{max(x, 0)}+{max(y, 0)}")

    def _ok(self):
        reason = self.text.get("1.0", "end").strip()
        if not reason:
            messagebox.showwarning("提示", "请填写弃用原因", parent=self)
            return
        self.on_ok(reason)
        self.destroy()