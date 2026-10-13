"""网站管理系统 —— 主程序入口（图形界面）。

基于 :mod:`tkinter` 的单窗口应用，用于集中管理常用网站：录入、检索、
跳转、弃用（假删除）与恢复，并支持导出 Excel。

本模块只承担界面职责，数据与业务逻辑全部委托给 :mod:`wm` 包。

运行方式::

    python main.py

界面布局自上而下依次为：

1. 工具栏：添加录入 / 跳转网站 / 弃用删除 / 恢复在用 / 刷新 / 导出 Excel
2. 查询条件区：关键词 + 查询范围 + 是否包含已弃用
3. 记录表格：支持多选，双击任意行即用 Edge 打开对应网站
4. 状态栏：显示当前记录总数与已弃用条数
"""

from __future__ import annotations

import datetime
import os
import subprocess
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Any

from wm.browser import open_in_edge
from wm.db import init_db
from wm.dialogs import AddSiteDialog, ReasonDialog
from wm.export import save_to_excel
from wm.operations import (
    STATUS_ACTIVE,
    STATUS_DEPRECATED,
    deprecate_site,
    query_sites,
    restore_site,
)

__all__ = ["APP_TITLE", "COLUMNS", "WebsiteManager", "main"]

#: 窗口标题
APP_TITLE = "网站管理系统"

#: 表格列定义，元素为 ``(字段名, 表头文字, 默认列宽)``。
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

#: 表格斑马纹与弃用行的配色
_ROW_ODD_BG = "#F4F7FB"
_ROW_EVEN_BG = "#FFFFFF"
_ROW_DEPRECATED_BG = "#F2F2F2"
_ROW_DEPRECATED_FG = "#9A9A9A"


def build_tree(parent: tk.Misc) -> ttk.Treeview:
    """创建带纵横滚动条的记录表格。

    Args:
        parent: 表格的父容器。

    Returns:
        配置完成的 :class:`ttk.Treeview` 实例；列宽、表头、斑马纹标签
        均已设置。
    """
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

    tree.tag_configure("odd", background=_ROW_ODD_BG)
    tree.tag_configure("even", background=_ROW_EVEN_BG)
    tree.tag_configure(
        "deprecated", background=_ROW_DEPRECATED_BG, foreground=_ROW_DEPRECATED_FG
    )
    return tree


def fill_tree(tree: ttk.Treeview, records: list[dict[str, Any]]) -> None:
    """把记录填充进表格。

    表格行的 ``iid`` 直接使用数据库主键 ``id``，因此选中行后可通过
    ``int(tree.selection()[0])`` 反查记录。已弃用记录使用灰色样式，
    其余记录按奇偶行交替配色。

    Args:
        tree: 目标表格。
        records: 记录列表，每项为「字段名 -> 值」的字典。
    """
    tree.delete(*tree.get_children())
    for idx, rec in enumerate(records):
        values = ["" if rec.get(key) is None else rec.get(key) for key, _, _ in COLUMNS]
        if rec.get("status") == STATUS_DEPRECATED:
            tag = "deprecated"
        else:
            tag = "odd" if idx % 2 else "even"
        tree.insert("", "end", iid=str(rec["id"]), values=values, tags=(tag,))


class WebsiteManager(tk.Tk):
    """主窗口。

    Attributes:
        records (list[dict]): 当前列表中的记录（与表格内容一致）。
        record_by_id (dict[int, dict]): 以主键索引的当前记录，供选中行反查。
        field_map (dict[str, str]): 查询范围下拉框的「显示名 -> 字段名」映射。
        tree (ttk.Treeview): 记录表格。
        status_var (tk.StringVar): 状态栏文本。
        var_keyword (tk.StringVar): 关键词输入值。
        var_field (tk.StringVar): 查询范围显示名。
        var_include (tk.BooleanVar): 是否包含已弃用记录。
    """

    def __init__(self) -> None:
        """初始化数据库、构建界面并载入首屏数据。"""
        super().__init__()
        self.title(APP_TITLE)
        self.minsize(980, 560)

        self.records: list[dict[str, Any]] = []
        self.record_by_id: dict[int, dict[str, Any]] = {}
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

    # ---------- 界面构建 ----------
    def _center(self, w: int, h: int) -> None:
        """把主窗口居中显示。

        Args:
            w: 窗口宽度（像素）。
            h: 窗口高度（像素）。
        """
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        x, y = max((sw - w) // 2, 0), max((sh - h) // 3, 0)
        self.geometry(f"{w}x{h}+{x}+{y}")

    def _setup_style(self) -> None:
        """配置 ttk 主题与控件样式（行高、字体、按钮内边距）。"""
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("Treeview", rowheight=26, font=("", 10))
        style.configure("Treeview.Heading", font=("", 10, "bold"))
        style.configure("TButton", padding=(10, 5))

    def _build_toolbar(self) -> None:
        """构建顶部工具栏（功能按钮 + 操作提示）。"""
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

    def _build_filter(self) -> None:
        """构建查询条件区（关键词、查询范围、包含已弃用）。"""
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

    def _build_statusbar(self) -> None:
        """构建底部状态栏。"""
        self.status_var = tk.StringVar(value="就绪")
        bar = ttk.Frame(self)
        bar.pack(side="bottom", fill="x")
        ttk.Separator(bar, orient="horizontal").pack(fill="x")
        ttk.Label(bar, textvariable=self.status_var, anchor="w", padding=(10, 5)).pack(fill="x")

    def _bind_tree_events(self) -> None:
        """为表格绑定双击与回车事件（均触发「跳转网站」）。"""
        self.tree.bind("<Double-1>", self._on_double_click)
        self.tree.bind("<Return>", lambda _e: self.open_selected())

    def _on_double_click(self, event: tk.Event) -> None:
        """双击表格时打开对应网站。

        仅在双击落在单元格上时响应，点表头或空白区域不触发。

        Args:
            event: tkinter 事件对象，提供点击坐标。
        """
        if self.tree.identify_region(event.x, event.y) != "cell":
            return
        self.open_selected()

    # ---------- 数据刷新 ----------
    def refresh(self) -> None:
        """按当前查询条件重新载入列表，并更新状态栏统计。"""
        records = query_sites(
            include_deprecated=self.var_include.get(),
            keyword=self.var_keyword.get().strip(),
            field=self.field_map.get(self.var_field.get(), "all"),
        )
        self.records = records
        self.record_by_id = {r["id"]: r for r in records}
        fill_tree(self.tree, records)

        total = len(records)
        deprecated = sum(1 for r in records if r.get("status") == STATUS_DEPRECATED)
        scope = "（含已弃用）" if self.var_include.get() else "（仅在用）"
        self.status_var.set(f"共 {total} 条记录{scope}，其中已弃用 {deprecated} 条")

    def reset_filter(self) -> None:
        """清空查询条件并刷新列表。"""
        self.var_keyword.set("")
        self.var_field.set("全部")
        self.var_include.set(False)
        self.refresh()

    # ---------- 操作 ----------
    def open_add_dialog(self) -> None:
        """弹出录入对话框，保存成功后自动刷新列表。"""
        AddSiteDialog(self, on_saved=self.refresh)

    def open_selected(self) -> None:
        """用 Edge 打开当前选中的网站。

        未选中任何行时给出提示；跳转结果会写入状态栏，失败时另弹错误框。
        """
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

    def deprecate_selected(self) -> None:
        """弃用当前选中的网站（支持 Ctrl 多选）。

        只会对「在用」状态的记录发起弃用；确认原因后交由
        :meth:`_do_deprecate` 执行。
        """
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("提示", "请先选中要弃用的网站（可按住 Ctrl 多选）")
            return
        ids = [int(i) for i in sel]
        active = [i for i in ids if self.record_by_id.get(i, {}).get("status") == STATUS_ACTIVE]
        if not active:
            messagebox.showinfo("提示", "选中的网站都已经是弃用状态了")
            return
        ReasonDialog(self, len(active), lambda reason: self._do_deprecate(active, reason))

    def _do_deprecate(self, ids: list[int], reason: str) -> None:
        """批量执行弃用并汇总结果。

        Args:
            ids: 待弃用记录的主键列表。
            reason: 统一的弃用原因。
        """
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

    def restore_selected(self) -> None:
        """把选中的已弃用网站恢复为「在用」（支持 Ctrl 多选）。"""
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("提示", "请先选中要恢复的网站（可按住 Ctrl 多选）")
            return
        ids = [int(i) for i in sel]
        deprecated = [
            i for i in ids if self.record_by_id.get(i, {}).get("status") == STATUS_DEPRECATED
        ]
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

    def export_excel(self) -> None:
        """把当前列表导出为 Excel。

        导出的是界面上当前筛选结果（``self.records``），而非全库数据。
        保存成功后询问是否立即打开文件。
        """
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
    def _open_path(path: str) -> None:
        """用系统默认程序打开指定文件，失败时静默忽略。

        Args:
            path: 待打开的文件路径。
        """
        try:
            if os.name == "nt":
                os.startfile(path)  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                subprocess.Popen(["open", path])
            else:
                subprocess.Popen(["xdg-open", path])
        except Exception:  # noqa: BLE001
            pass


def main() -> None:
    """程序入口：初始化数据库并进入主事件循环。"""
    init_db()
    app = WebsiteManager()
    app.mainloop()


if __name__ == "__main__":
    main()
