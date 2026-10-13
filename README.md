# WebSite_OfMine

基于 Python 标准库 `tkinter` 的本地网站管理工具。用于集中维护常用网址，支持录入、检索、
一键跳转、弃用（假删除）与恢复，并可将结果导出为 Excel。

所有数据保存在本地 SQLite 数据库中，不依赖网络与任何后端服务，双击即可运行。

---

## 功能特性

| 功能 | 说明 |
| --- | --- |
| 录入管理 | 记录网站名、网址、功能分类与备注；网址自动补全协议头（默认 `https://`） |
| 多维度检索 | 可按网站名 / 功能 / 网址单独筛选，也可四列全字段模糊匹配 |
| 一键跳转 | 双击表格任意一行即用 Microsoft Edge 打开；未安装 Edge 时自动回退到系统默认浏览器 |
| 弃用而非删除 | 采用「假删除」策略，记录保留可追溯，支持随时恢复为在用 |
| 批量操作 | 表格支持 Ctrl / Shift 多选，可批量弃用或批量恢复 |
| 导出 Excel | 将当前筛选结果导出为带样式表头的 `.xlsx`，列宽按内容自适应（中文按 2 字符宽估算） |

---

## 环境要求

- **Python 3.10 及以上**（代码使用了 `X | None` 等新式类型标注语法）
- **操作系统**：Windows（跳转功能优先定位 Edge，路径按 Windows 约定编写；其他系统会自动回退到默认浏览器）
- **可选**：Microsoft Edge —— 未安装时不影响使用，只是改用系统默认浏览器

---

## 安装

```bash
# 1. 获取代码
git clone <repository-url>
cd WebSite_OfMine

# 2. 创建并激活虚拟环境（推荐）
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS / Linux

# 3. 安装依赖
pip install -r requirements.txt
```

> `tkinter` 与 `sqlite3` 属于 Python 标准库，通常随安装包一同提供，无需单独安装。

---

## 使用

```bash
python main.py
```

启动后进入主界面，自上而下分为四个区域：

1. **工具栏** —— 添加录入 / 跳转网站 / 弃用删除 / 恢复在用 / 刷新 / 导出 Excel
2. **查询条件区** —— 关键词 + 查询范围（全部 / 网站名 / 功能 / 网址）+ 「包含已弃用」开关
3. **记录表格** —— 支持多选；双击任意行用 Edge 打开对应网站；已弃用记录显示为灰色
4. **状态栏** —— 显示当前记录总数与已弃用条数

### 常用操作

| 操作 | 方式 |
| --- | --- |
| 打开网站 | 双击表格中的任意一行，或选中后按 `Enter` |
| 批量弃用 | 按住 `Ctrl` 或 `Shift` 多选，点击「弃用删除」并填写原因 |
| 恢复网站 | 勾选「包含已弃用」→ 选中灰色行 → 点击「恢复在用」 |
| 快速查询 | 在关键词框输入后按 `Enter` |
| 清空条件 | 点击「重置」 |

---

## 项目结构

```
WebSite_OfMine/
├── main.py                 # 程序入口：tkinter 主窗口与界面编排
├── wm/                     # 业务逻辑包
│   ├── __init__.py         # 包声明与版本号
│   ├── db.py               # 数据库连接与建表
│   ├── operations.py       # 录入 / 查询 / 弃用 / 恢复
│   ├── browser.py          # Edge 优先的浏览器跳转
│   ├── export.py           # Excel 导出
│   ├── dialogs.py          # 录入对话框、弃用原因对话框
│   └── utils.py            # 通用工具函数
├── .gitattributes          # 行尾与文件类型规范
├── .gitignore
├── LICENSE
├── README.md
└── requirements.txt
```

分层约定：`main.py` 只负责界面展示与交互，**不直接访问数据库**；全部数据与业务逻辑
由 `wm` 包提供。这样界面与逻辑可以独立演进，也便于单独测试。

---

## 数据说明

- 数据库文件位于 `wm/websites.db`，首次运行 `main.py` 时自动创建。
- 数据表 `sites` 的字段如下：

  | 字段 | 类型 | 说明 |
  | --- | --- | --- |
  | `id` | INTEGER | 主键，自增序号 |
  | `site_name` | TEXT | 网站名（必填） |
  | `url` | TEXT | 网址（必填） |
  | `function` | TEXT | 功能分类 |
  | `remarks` | TEXT | 备注 |
  | `status` | TEXT | 状态：`在用` / `已弃用`，默认 `在用` |
  | `deprecate_reason` | TEXT | 弃用原因 |
  | `deprecate_time` | TEXT | 弃用时间 |
  | `created_at` | TEXT | 录入时间 |

- **该数据库含个人数据，已在 `.gitignore` 中排除，不会被提交到仓库。**
- 备份数据只需复制 `wm/websites.db` 这一个文件。

---

## 开发约定

### 文档注释

全部模块、类与函数均使用 **Google 风格 docstring**，包含 `Args` / `Returns` / `Raises` /
`Attributes` 等段落，并配合完整的类型标注。示例：

```python
def query_sites(
    include_deprecated: bool = False,
    keyword: str = "",
    field: str = "all",
) -> list[dict[str, Any]]:
    """按条件查询网站记录。

    Args:
        include_deprecated: 是否包含已弃用记录。为 ``False``（默认）时
            只返回状态为「在用」的记录。
        keyword: 关键词，匹配方式为 ``LIKE %keyword%``。
        field: 关键词的匹配范围，可选 ``all`` / ``site_name`` / ``function`` / ``url``。

    Returns:
        匹配到的记录列表，按 ``id`` 升序排列。
    """
```

### 提交规范

提交信息遵循 [Conventional Commits](https://www.conventionalcommits.org/)：

```
<type>(<scope>): <subject>

[optional body]

[optional footer]
```

常用 `type`：`feat` 新功能、`fix` 修复、`docs` 文档、`style` 格式、`refactor` 重构、
`chore` 构建与杂项。

示例：

```
feat(export): 支持按当前筛选结果导出 Excel

fix(dialogs): 修正弃用原因对话框在空输入时未拦截的问题

docs: 统一全部模块为 Google 风格 docstring
```

### 分支模型

- `main`：随时可运行的稳定分支
- 功能开发使用 `feat/<简述>`，缺陷修复使用 `fix/<简述>`，完成后合并回 `main`

---

## 许可证

本项目采用 [MIT License](LICENSE)。
