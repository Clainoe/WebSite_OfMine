"""
网站管理系统 - 主程序入口（图形界面）
运行：python main.py
"""

import os
import subprocess
import sys
import datetime
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

from wm.db import init_db
from wm.operations import query_sites, deprecate_site, restore_site
from wm.browser import open_in_edge
from wm.export import save_to_excel
from wm.dialogs import AddSiteDialog, ReasonDialog


APP_TITLE = "网站管理系统"

COLUMNS = [
    ("id", "序号", 60),
    ("site_name", "网站名", 150),
    ("url", "网址", 260),
    ("function", "功能", 160),
    ("remarks", "备注", 180),
    ("status", "状态", 80),
    ("deprecate_reason", "弃用原因", 150),
    ("deprecate_time", "弃用时间", 140),
]


def build_tree(parent):
    """创建带滚动条的表格。"""
    container = ttk.Frame(parent)
    container.pack(fill="both", expand=True, padx=8, pady=8)

    tree = ttk.Treeview(
        container,
        columns=[c[0] for c in COLUMNS],
        show="headings",
        selectmode="extended",
    )
    for key, label, width in COLUMNS:
        tree.heading(key, text=label)
        tree.column(key, width=width, anchor="center", stretch=False)

    vsb = ttk.Scrollbar(container, orient="vertical", command=tree.yview)
    hsb = ttk.Scrollbar(container, orient="horizontal", command=tree.xview)
    tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

    tree.grid(row=0, column=0, sticky="nsew")
    vsb.grid(row=0, column=1, sticky="ns")
    hsb.grid(row=1, column=0, sticky="ew")
    container.rowconfigure(0, weight=1)
    container.columnconfigure(0, weight=1)

    tree.tag_configure("odd", background="#F4F7FB")
    tree.tag_configure("even", background="#FFFFFF")
    tree.tag_configure("deprecated", background="#F2F2F2", foreground="#9A9A9A")
    return tree


def fill_tree(tree, records):
    """把记录填充进 Treeview（iid 使用数据库 id）。"""
    tree.delete(*tree.get_children())
    for idx, rec in enumerate(records):
        values = ["" if rec.get(key) is None else rec.get(key) for key, _, _ in COLUMNS]
        if rec.get("status") == "已弃用":
            tag = "deprecated"
        else:
            tag = "odd" if idx % 2 else "even"
        tree.insert("", "end", iid=str(rec["id"]), values=values, tags=(tag,))


class WebsiteManager(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.minsize(980, 560)

        self.records = []
        self.record_by_id = {}
        self.field_map = {
            "全部": "all",
            "网站名": "site_name",
            "功能": "function",
            "网址": "url",
        }

        init_db()
        self._setup_style()
        self._build_toolbar()
        self._build_filter()
        self._build_statusbar()
        self.tree = build_tree(self)
        self._bind_tree_events()
        self._center(1240, 720)
        self.refresh()

    def _center(self, w, h):
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        x, y = max((sw - w) // 2, 0), max((sh - h) // 3, 0)
        self.geometry(f"{w}x{h}+{x}+{y}")

    def _setup_style(self):
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("Treeview", rowheight=26, font=("", 10))
        style.configure("Treeview.Heading", font=("", 10, "bold"))
        style.configure("TButton", padding=(10, 5))

    def _build_toolbar(self):
        bar = ttk.Frame(self, padding=(10, 8))
        bar.pack(side="top", fill="x")

        ttk.Button(bar, text="添加录入", command=self.open_add_dialog).pack(side="left")
        ttk.Button(bar, text="跳转网站", command=self.open_selected).pack(side="left", padx=(8, 0))
        ttk.Button(bar, text="弃用删除", command=self.deprecate_selected).pack(side="left", padx=(8, 0))
        ttk.Button(bar, text="恢复在用", command=self.restore_selected).pack(side="left", padx=(8, 0))
        ttk.Button(bar, text="刷新", command=self.refresh).pack(side="left", padx=(8, 0))
        ttk.Button(bar, text="导出 Excel", command=self.export_excel).pack(side="left", padx=(8, 0))

        ttk.Button(bar, text="退出", command=self.destroy).pack(side="right")
        ttk.Label(
            bar,
            text="双击表格任意一行即可用 Edge 打开该网站",
            foreground="#888888",
        ).pack(side="right", padx=(0, 14))

    def _build_filter(self):
        box = ttk.LabelFrame(self, text="查询条件", padding=10)
        box.pack(side="top", fill="x", padx=8, pady=(0, 4))

        self.var_keyword = tk.StringVar()
        self.var_field = tk.StringVar(value="全部")
        self.var_include = tk.BooleanVar(value=False)

        ttk.Label(box, text="关键词：").grid(row=0, column=0, padx=(0, 4))
        entry = ttk.Entry(box, textvariable=self.var_keyword, width=26)
        entry.grid(row=0, column=1, padx=(0, 12))
        entry.bind("<Return>", lambda _e: self.refresh())

        ttk.Label(box, text="查询范围：").grid(row=0, column=2, padx=(0, 4))
        ttk.Combobox(
            box,
            textvariable=self.var_field,
            values=list(self.field_map.keys()),
            state="readonly",
            width=10,
        ).grid(row=0, column=3, padx=(0, 12))

        ttk.Checkbutton(box, text="包含已弃用", variable=self.var_include).grid(
            row=0, column=4, padx=(0, 12)
        )
        ttk.Button(box, text="查询", command=self.refresh).grid(row=0, column=5, padx=(0, 6))
        ttk.Button(box, text="重置", command=self.reset_filter).grid(row=0, column=6)

    def _build_statusbar(self):
        self.status_var = tk.StringVar(value="就绪")
        bar = ttk.Frame(self)
        bar.pack(side="bottom", fill="x")
        ttk.Separator(bar, orient="horizontal").pack(fill="x")
        ttk.Label(bar, textvariable=self.status_var, anchor="w", padding=(10, 5)).pack(fill="x")

    def _bind_tree_events(self):
        self.tree.bind("<Double-1>", self._on_double_click)
        self.tree.bind("<Return>", lambda _e: self.open_selected())

    def _on_double_click(self, event):
        if self.tree.identify_region(event.x, event.y) != "cell":
            return
        self.open_selected()

    def refresh(self):
        records = query_sites(
            include_deprecated=self.var_include.get(),
            keyword=self.var_keyword.get().strip(),
            field=self.field_map.get(self.var_field.get(), "all"),
        )
        self.records = records
        self.record_by_id = {r["id"]: r for r in records}
        fill_tree(self.tree, records)

        total = len(records)
        deprecated = sum(1 for r in records if r.get("status") == "已弃用")
        scope = "（含已弃用）" if self.var_include.get() else "（仅在用）"
        self.status_var.set(f"共 {total} 条记录{scope}，其中已弃用 {deprecated} 条")

    def reset_filter(self):
        self.var_keyword.set("")
        self.var_field.set("全部")
        self.var_include.set(False)
        self.refresh()

    # ---------- 操作 ----------
    def open_add_dialog(self):
        AddSiteDialog(self, on_saved=self.refresh)

    def open_selected(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("提示", "请先在列表中选中一个网站")
            return
        record = self.record_by_id.get(int(sel[0]))
        if record is None:
            return
        ok, msg = open_in_edge(record["url"])
        self.status_var.set(msg)
        if not ok:
            messagebox.showerror("跳转失败", msg)

    def deprecate_selected(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("提示", "请先选中要弃用的网站（可按住 Ctrl 多选）")
            return
        ids = [int(i) for i in sel]
        active = [i for i in ids if self.record_by_id.get(i, {}).get("status") == "在用"]
        if not active:
            messagebox.showinfo("提示", "选中的网站都已经是弃用状态了")
            return
        ReasonDialog(self, len(active), lambda reason: self._do_deprecate(active, reason))

    def _do_deprecate(self, ids, reason):
        success, failed = 0, []
        for site_id in ids:
            ok, msg = deprecate_site(site_id, reason)
            if ok:
                success += 1
            else:
                failed.append(msg)

        self.refresh()

        if failed:
            messagebox.showwarning(
                "部分操作未完成",
                f"成功 {success} 条，失败 {len(failed)} 条：\n" + "\n".join(failed[:10]),
            )
        else:
            messagebox.showinfo("完成", f"已成功弃用 {success} 个网站")

    def restore_selected(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("提示", "请先选中要恢复的网站（可按住 Ctrl 多选）")
            return
        ids = [int(i) for i in sel]
        deprecated = [i for i in ids if self.record_by_id.get(i, {}).get("status") == "已弃用"]
        if not deprecated:
            messagebox.showinfo("提示", "选中的网站都不是弃用状态，无需恢复")
            return
        if not messagebox.askyesno("确认恢复", f"确定将选中的 {len(deprecated)} 个网站恢复为「在用」？"):
            return

        success, failed = 0, []
        for site_id in deprecated:
            ok, msg = restore_site(site_id)
            if ok:
                success += 1
            else:
                failed.append(msg)

        self.refresh()

        if failed:
            messagebox.showwarning(
                "部分操作未完成",
                f"成功 {success} 条，失败 {len(failed)} 条：\n" + "\n".join(failed[:10]),
            )
        else:
            messagebox.showinfo("完成", f"已成功恢复 {success} 个网站为「在用」")

    def export_excel(self):
        if not self.records:
            messagebox.showinfo("提示", "当前列表没有数据，无法导出")
            return
        default_name = f"网站清单_{datetime.datetime.now():%Y%m%d}.xlsx"
        path = filedialog.asksaveasfilename(
            title="导出为 Excel",
            defaultextension=".xlsx",
            initialfile=default_name,
            filetypes=[("Excel 工作簿", "*.xlsx")],
        )
        if not path:
            return
        try:
            save_to_excel(self.records, path)
        except Exception as e:  # noqa: BLE001
            messagebox.showerror(
                "导出失败",
                f"导出过程中出现错误：\n{e}\n\n请确认已安装 openpyxl：pip install openpyxl",
            )
            return
        self.status_var.set(f"已导出：{path}")
        if messagebox.askyesno("导出成功", f"已保存到：\n{path}\n\n是否打开该文件？"):
            self._open_path(path)

    @staticmethod
    def _open_path(path):
        try:
            if os.name == "nt":
                os.startfile(path)  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                subprocess.Popen(["open", path])
            else:
                subprocess.Popen(["xdg-open", path])
        except Exception:  # noqa: BLE001
            pass


def main():
    init_db()
    app = WebsiteManager()
    app.mainloop()


if __name__ == "__main__":
    main()