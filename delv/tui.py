"""TUI interface for Delv using Textual."""

from __future__ import annotations

import pyperclip
from textual import on, work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.command import Hit, Hits, Provider
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import (
    Footer,
    Header,
    Input,
    Label,
    Markdown,
    MarkdownViewer,
    OptionList,
    Static,
    Tree,
)
from textual.suggester import Suggester
from textual.widgets.option_list import Option
from textual.widgets.tree import TreeNode

from .config import Config, get_current_tree_name, set_current_tree_name
from .editor import edit_node_interactive
from .storage import (
    delete_tree,
    list_trees,
    load_tree,
    rename_tree,
    save_tree,
    tree_exists,
)
from .themes import THEME_DISPLAY_NAMES, THEME_NAMES, get_themes
from .tree import ExplorationTree, Node, NodeStatus


# === Custom Suggester for Node IDs ===

class NodeIdSuggester(Suggester):
    """Suggester that provides node ID completions."""
    
    def __init__(self, tree: ExplorationTree, case_sensitive: bool = False) -> None:
        super().__init__(case_sensitive=case_sensitive)
        self._tree = tree
    
    async def get_suggestion(self, value: str) -> str | None:
        """Get a completion suggestion for the given input."""
        if not value:
            return None
        
        value_lower = value.lower() if not self.case_sensitive else value
        
        # Find matching node IDs
        for nid in self._tree.nodes:
            nid_cmp = nid.lower() if not self.case_sensitive else nid
            if nid_cmp.startswith(value_lower) and nid != value:
                return nid
        
        return None


# === Command Palette Provider ===

class DelvCommands(Provider):
    """Command palette provider for Delv actions."""
    
    async def search(self, query: str) -> Hits:
        """Search for commands."""
        app = self.app
        
        # Define all available commands
        commands = [
            ("添加子节点", "创建新的子节点", app.action_add_child),
            ("添加兄弟节点", "创建同级节点", app.action_add_sibling),
            ("编辑节点", "使用外部编辑器编辑", app.action_edit_external),
            ("编辑标题", "快速修改节点标题", app.action_edit_title),
            ("追加内容", "向节点追加文本", app.action_append_body),
            ("标记完成", "将节点标记为已完成", app.action_mark_done),
            ("标记放弃", "将节点标记为已放弃", app.action_mark_dropped),
            ("标记待办", "将节点标记为待办", app.action_mark_todo),
            ("添加链接", "创建到其他节点的链接", app.action_add_link),
            ("移除链接", "删除现有链接", app.action_remove_link),
            ("显示反向链接", "查看指向此节点的链接", app.action_show_backlinks),
            ("移动节点", "将节点移动到新位置", app.action_move_node),
            ("复制内容", "复制节点内容到剪贴板", app.action_yank_body),
            ("粘贴内容", "从剪贴板粘贴内容", app.action_paste_body),
            ("复制节点ID", "复制节点ID到剪贴板", app.action_yank_id),
            ("新建树", "创建新的探索树", app.action_new_tree),
            ("重命名树", "重命名当前树", app.action_rename_tree),
            ("删除树", "删除当前树", app.action_delete_tree),
            ("搜索", "在树中搜索节点", app.action_search),
            ("统计信息", "显示树的统计数据", app.action_show_stats),
            ("切换主题", "更换界面主题", app.action_select_theme),
            ("跳转到根节点", "返回根节点", app.action_go_root),
            ("跳转到节点", "按ID跳转到节点", app.action_goto_node),
            ("返回父节点", "向上导航一级", app.action_go_parent),
            ("历史后退", "返回上一个访问的节点", app.action_go_back),
            ("强制保存", "立即保存当前树", app.action_force_save),
            ("帮助", "显示快捷键帮助", app.action_show_help),
        ]
        
        matcher = self.matcher(query)
        
        for name, description, callback in commands:
            score = matcher.match(name)
            if score > 0:
                yield Hit(
                    score,
                    matcher.highlight(name),
                    callback,
                    help=description,
                )


# === Help Text ===

HELP_FULL = """# Delv 快捷键

## 速查
| 操作 | 快捷键 |
|------|--------|
| 方向移动 | `h` `j` `k` `l` |
| 进入/选择 | `Enter` |
| 返回父节点 | `Backspace` |
| 历史后退 | `-` |
| 添加子节点 | `a` |
| 编辑节点 | `e` |
| 标记完成 | `d` |
| 搜索 | `/` |

---

## 导航
| 快捷键 | 操作 |
|--------|------|
| `h` `l` | 切换面板焦点 (左/右) |
| `j` `k` | 上下移动 |
| `Enter` | 进入节点 / 打开树 |
| `Backspace` | 返回父节点 |
| `-` | 历史后退 |
| `r` | 跳转到根节点 |
| `g` | 按 ID 跳转 |
| `]` `[` | 跳转到下/上一个链接 |

## 编辑
| 快捷键 | 操作 |
|--------|------|
| `a` | 添加子节点 |
| `A` | 添加兄弟节点 |
| `e` | 编辑节点 (外部编辑器) |
| `E` | 快速编辑标题 |
| `i` | 快速追加内容 |
| `d` | 标记完成 (自动返回) |
| `x` | 标记放弃 (自动返回) |
| `t` | 标记待办 |

## 链接与结构
| 快捷键 | 操作 |
|--------|------|
| `L` | 添加链接 |
| `U` | 移除链接 |
| `B` | 显示反向链接 |
| `m` | 移动节点 |
| `y` | 复制内容到剪贴板 |
| `p` | 粘贴到内容 |
| `Y` | 复制节点 ID |

## 树管理
| 快捷键 | 操作 |
|--------|------|
| `n` | 新建树 |
| `R` | 重命名树 |
| `D` | 删除树 |

## 其他
| 快捷键 | 操作 |
|--------|------|
| `Ctrl+P` | **命令面板** (模糊搜索所有命令) |
| `/` | 搜索 |
| `s` | 统计信息 |
| `T` | 切换主题 |
| `?` | 帮助 |
| `Ctrl+S` | 强制保存 |
| `q` | 退出 |

> **提示**: 按 `Ctrl+P` 打开命令面板，可以模糊搜索所有可用命令！
"""


# === Screens ===

class HelpScreen(ModalScreen):
    """Help screen showing keybindings."""
    
    BINDINGS = [
        Binding("escape", "dismiss", "关闭"),
        Binding("q", "dismiss", "关闭"),
    ]
    
    def compose(self) -> ComposeResult:
        # MarkdownViewer has built-in scrolling and keyboard navigation
        yield Container(
            MarkdownViewer(HELP_FULL, show_table_of_contents=False, id="help-viewer"),
            id="help-container",
        )
    
    def on_mount(self) -> None:
        self.query_one("#help-viewer").focus()
    
    def action_dismiss(self) -> None:
        self.app.pop_screen()


class InputScreen(ModalScreen[str | None]):
    """Modal screen for text input."""
    
    BINDINGS = [
        Binding("escape", "cancel", "取消"),
    ]
    
    def __init__(
        self,
        prompt: str,
        default: str = "",
        suggester: Suggester | None = None,
    ) -> None:
        super().__init__()
        self.prompt = prompt
        self.default = default
        self.suggester = suggester
    
    def compose(self) -> ComposeResult:
        yield Container(
            Label(self.prompt, id="input-prompt"),
            Input(
                value=self.default,
                id="input-field",
                suggester=self.suggester,
            ),
            id="input-container",
            classes="modal-container",
        )
    
    def on_mount(self) -> None:
        self.query_one(Input).focus()
    
    @on(Input.Submitted)
    def on_submit(self, event: Input.Submitted) -> None:
        self.dismiss(event.value)
    
    def action_cancel(self) -> None:
        self.dismiss(None)


class ConfirmScreen(ModalScreen[bool]):
    """Modal screen for confirmation."""
    
    BINDINGS = [
        Binding("y", "confirm", "是"),
        Binding("n", "cancel", "否"),
        Binding("escape", "cancel", "取消"),
    ]
    
    def __init__(self, message: str) -> None:
        super().__init__()
        self.message = message
    
    def compose(self) -> ComposeResult:
        yield Container(
            Label(self.message, id="confirm-message"),
            Label("[y] 是  [n] 否", id="confirm-options"),
            id="confirm-container",
            classes="modal-container",
        )
    
    def action_confirm(self) -> None:
        self.dismiss(True)
    
    def action_cancel(self) -> None:
        self.dismiss(False)


class SearchScreen(ModalScreen[str | None]):
    """Modal screen for search."""
    
    BINDINGS = [
        Binding("escape", "cancel", "取消"),
    ]
    
    def __init__(self, tree: ExplorationTree) -> None:
        super().__init__()
        self.current_tree = tree
        self.results: list[str] = []
    
    def compose(self) -> ComposeResult:
        yield Container(
            Input(placeholder="搜索...", id="search-input"),
            OptionList(id="search-results"),
            id="search-container",
            classes="modal-container",
        )
    
    def on_mount(self) -> None:
        self.query_one(Input).focus()
    
    @on(Input.Changed)
    def on_search_changed(self, event: Input.Changed) -> None:
        results_view = self.query_one("#search-results", OptionList)
        results_view.clear_options()
        
        query = event.value.strip()
        if not query:
            self.results = []
            return
        
        self.results = self.current_tree.search(query)
        for nid in self.results[:20]:  # Limit to 20 results
            node = self.current_tree.nodes[nid]
            results_view.add_option(Option(f"[{nid}] {node.status.icon} {node.title}", id=nid))
    
    @on(Input.Submitted)
    def on_search_submit(self, event: Input.Submitted) -> None:
        if self.results:
            self.dismiss(self.results[0])
        else:
            self.dismiss(None)
    
    @on(OptionList.OptionSelected)
    def on_result_selected(self, event: OptionList.OptionSelected) -> None:
        if event.option.id:
            self.dismiss(event.option.id)
    
    def action_cancel(self) -> None:
        self.dismiss(None)


class SelectNodeScreen(ModalScreen[str | None]):
    """Modal screen for selecting a node (for move/link operations)."""
    
    BINDINGS = [
        Binding("escape", "cancel", "取消"),
    ]
    
    def __init__(self, tree: ExplorationTree, prompt: str, exclude: str | None = None) -> None:
        super().__init__()
        self.current_tree = tree
        self.prompt = prompt
        self.exclude = exclude
    
    def compose(self) -> ComposeResult:
        # Build options from tree
        options = []
        for nid, depth in self.current_tree.iter_tree():
            if nid == self.exclude:
                continue
            node = self.current_tree.nodes[nid]
            indent = "  " * depth
            options.append(Option(f"{indent}[{nid}] {node.status.icon} {node.title}", id=nid))
        
        yield Container(
            Label(self.prompt, id="select-prompt"),
            OptionList(*options, id="select-list"),
            id="select-container",
            classes="modal-container",
        )
    
    def on_mount(self) -> None:
        self.query_one("#select-list", OptionList).focus()
    
    @on(OptionList.OptionSelected)
    def on_selected(self, event: OptionList.OptionSelected) -> None:
        self.dismiss(event.option.id)
    
    def action_cancel(self) -> None:
        self.dismiss(None)


class BacklinksScreen(ModalScreen):
    """Modal screen showing backlinks."""
    
    BINDINGS = [
        Binding("escape", "dismiss", "关闭"),
        Binding("q", "dismiss", "关闭"),
    ]
    
    def __init__(self, tree: ExplorationTree, node_id: str) -> None:
        super().__init__()
        self.current_tree = tree
        self.node_id = node_id
    
    def compose(self) -> ComposeResult:
        node = self.current_tree.nodes[self.node_id]
        backlink_ids = self.current_tree.get_backlinks(self.node_id)
        
        if backlink_ids:
            options = [
                Option(f"[{nid}] {self.current_tree.nodes[nid].status.icon} {self.current_tree.nodes[nid].title}", id=nid)
                for nid in backlink_ids
            ]
        else:
            options = [Option("(无反向链接)", disabled=True)]
        
        yield Container(
            Label(f"反向链接: [{self.node_id}] {node.title}", id="backlinks-title"),
            OptionList(*options, id="backlinks-list"),
            id="backlinks-container",
            classes="modal-container",
        )
    
    def on_mount(self) -> None:
        self.query_one("#backlinks-list", OptionList).focus()
    
    @on(OptionList.OptionSelected)
    def on_selected(self, event: OptionList.OptionSelected) -> None:
        if event.option.id:
            self.app.navigate_to(event.option.id)
            self.app.pop_screen()
    
    def action_dismiss(self) -> None:
        self.app.pop_screen()


class StatisticsScreen(ModalScreen):
    """Modal screen showing statistics."""
    
    BINDINGS = [
        Binding("escape", "dismiss", "关闭"),
        Binding("q", "dismiss", "关闭"),
    ]
    
    def __init__(self, tree: ExplorationTree) -> None:
        super().__init__()
        self.current_tree = tree
    
    def compose(self) -> ComposeResult:
        stats = self.current_tree.get_statistics()
        content = f"""# {self.current_tree.name} 统计

| 指标 | 数值 |
|------|------|
| 总节点数 | {stats['total']} |
| ► 活跃 | {stats['active']} |
| ✓ 完成 | {stats['done']} |
| ✗ 放弃 | {stats['dropped']} |
| ? 待办 | {stats['todo']} |
| 叶子节点 | {stats['leaves']} |
| 最大深度 | {stats['max_depth']} |

**创建时间**: {self.current_tree.created.strftime('%Y-%m-%d %H:%M')}

**更新时间**: {self.current_tree.updated.strftime('%Y-%m-%d %H:%M')}
"""
        yield Container(
            Markdown(content, id="stats-content"),
            id="stats-container",
            classes="modal-container",
        )
    
    def action_dismiss(self) -> None:
        self.app.pop_screen()


class ThemeSelectorScreen(ModalScreen[str | None]):
    """Modal screen for selecting a theme."""
    
    BINDINGS = [
        Binding("escape", "cancel", "取消"),
        Binding("q", "cancel", "取消"),
    ]
    
    def __init__(self, current_theme: str) -> None:
        super().__init__()
        self.current_theme = current_theme
    
    def compose(self) -> ComposeResult:
        yield Container(
            Label("选择主题", id="theme-title"),
            OptionList(
                *[
                    Option(
                        f"{'► ' if name == self.current_theme else '  '}{THEME_DISPLAY_NAMES.get(name, name)}",
                        id=name,
                    )
                    for name in THEME_NAMES
                ],
                id="theme-list",
            ),
            id="theme-selector",
            classes="modal-container",
        )
    
    def on_mount(self) -> None:
        option_list = self.query_one("#theme-list", OptionList)
        # Highlight current theme
        for i, name in enumerate(THEME_NAMES):
            if name == self.current_theme:
                option_list.highlighted = i
                break
        option_list.focus()
    
    @on(OptionList.OptionSelected)
    def on_selected(self, event: OptionList.OptionSelected) -> None:
        self.dismiss(event.option.id)
    
    def action_cancel(self) -> None:
        self.dismiss(None)


# === Main App ===

class DelvApp(App):
    """Delv TUI Application."""
    
    TITLE = "Delv"
    SUB_TITLE = "探索树"
    
    # Enable command palette with custom provider
    COMMANDS = {DelvCommands}
    
    # Enable command palette toggle
    ENABLE_COMMAND_PALETTE = True
    
    # Load static CSS from file
    CSS_PATH = "styles.tcss"
    
    BINDINGS = [
        # Navigation - show key ones in footer
        Binding("h", "focus_left", "◀ 左", show=False),
        Binding("l", "focus_right", "右 ▶", show=False),
        Binding("j", "move_down", "↓", show=False),
        Binding("k", "move_up", "↑", show=False),
        Binding("enter", "select", "进入", show=False),
        Binding("backspace", "go_parent", "返回", show=False),
        Binding("minus", "go_back", "后退", show=False),
        Binding("r", "go_root", "根", show=False),
        Binding("g", "goto_node", "跳转", show=False),
        Binding("bracketright", "next_link", "下链", show=False),
        Binding("bracketleft", "prev_link", "上链", show=False),
        
        # Editing - show important ones
        Binding("a", "add_child", "+子节点"),
        Binding("A", "add_sibling", "+兄弟", show=False),
        Binding("e", "edit_external", "编辑"),
        Binding("E", "edit_title", "改标题", show=False),
        Binding("i", "append_body", "追加", show=False),
        Binding("d", "mark_done", "完成"),
        Binding("x", "mark_dropped", "放弃", show=False),
        Binding("t", "mark_todo", "待办", show=False),
        
        # Links & Structure
        Binding("L", "add_link", "链接", show=False),
        Binding("U", "remove_link", "删链", show=False),
        Binding("B", "show_backlinks", "反链", show=False),
        Binding("m", "move_node", "移动", show=False),
        Binding("y", "yank_body", "复制", show=False),
        Binding("p", "paste_body", "粘贴", show=False),
        Binding("Y", "yank_id", "复制ID", show=False),
        
        # Trees
        Binding("n", "new_tree", "新建", show=False),
        Binding("R", "rename_tree", "重命名", show=False),
        Binding("D", "delete_tree", "删除树", show=False),
        
        # Other - show key ones
        Binding("slash", "search", "搜索"),
        Binding("s", "show_stats", "统计", show=False),
        Binding("T", "select_theme", "主题"),
        Binding("question_mark", "show_help", "?帮助"),
        Binding("ctrl+p", "command_palette", "命令"),  # Built-in command palette
        Binding("ctrl+s", "force_save", "保存", show=False),
        Binding("q", "quit", "退出"),
    ]
    
    def __init__(self) -> None:
        super().__init__()
        self.current_tree: ExplorationTree | None = None
        self.current_trees_list: list[str] = []
        self.focus_panel: int = 1  # 0=trees, 1=nodes, 2=content
        self.link_index: int = 0
        self._updating_tree: bool = False  # Prevent recursive updates
        
        # Register custom themes
        for theme in get_themes():
            self.register_theme(theme)
        
        # Load saved theme preference
        self._config = Config.load()
        self._theme_name: str = self._config.theme
        # Ensure theme name has delv- prefix for our custom themes
        if not self._theme_name.startswith("delv-") and f"delv-{self._theme_name}" in THEME_NAMES:
            self._theme_name = f"delv-{self._theme_name}"
        # Set the theme
        self.theme = self._theme_name
    
    def on_mount(self) -> None:
        self.refresh_trees_list()
        self.load_current_tree()
        self.update_focus()
    
    def compose(self) -> ComposeResult:
        yield Header()
        yield Horizontal(
            Vertical(
                Static("树", classes="panel-title"),
                OptionList(id="trees-list"),
                id="trees-panel",
                classes="panel",
            ),
            Vertical(
                Static("节点", classes="panel-title"),
                Tree("root", id="node-tree"),
                id="nodes-panel",
                classes="panel",
            ),
            Vertical(
                Static("内容", classes="panel-title"),
                VerticalScroll(
                    Container(
                        Static("", id="node-title"),
                        Static("", id="node-meta"),
                        id="node-header",
                    ),
                    Markdown("", id="node-body"),
                    Static("", id="links-section"),
                    id="content-scroll",
                ),
                id="content-panel",
                classes="panel",
            ),
            id="main-container",
        )
        yield Footer()
    
    
    def refresh_trees_list(self) -> None:
        """Refresh the trees list."""
        self.current_trees_list = list_trees()
        trees_view = self.query_one("#trees-list", OptionList)
        trees_view.clear_options()
        
        current_name = get_current_tree_name()
        for name in self.current_trees_list:
            prefix = "► " if name == current_name else "  "
            trees_view.add_option(Option(f"{prefix}{name}", id=name))
    
    def load_current_tree(self) -> None:
        """Load the current tree."""
        name = get_current_tree_name()
        if name and tree_exists(name):
            try:
                self.current_tree = load_tree(name)
                self.refresh_node_tree()
                self.refresh_content()
            except Exception:
                self.current_tree = None
        else:
            self.current_tree = None
            self.refresh_node_tree()
            self.refresh_content()
    
    def refresh_node_tree(self) -> None:
        """Refresh the node tree display."""
        was_updating = self._updating_tree
        self._updating_tree = True
        try:
            tree_widget = self.query_one("#node-tree", Tree)
            tree_widget.clear()
            
            if not self.current_tree:
                tree_widget.root.set_label("(未加载树)")
                return
            
            root_node = self.current_tree.nodes["root"]
            tree_widget.root.set_label(self._format_node_label(root_node))
            tree_widget.root.data = "root"
            
            self._add_children_to_tree(tree_widget.root, "root")
            tree_widget.root.expand_all()
            
            # Select current node
            self._select_tree_node(self.current_tree.current)
        finally:
            self._updating_tree = was_updating
    
    def _format_node_label(self, node: Node) -> str:
        """Format a node label for the tree."""
        status_icon = node.status.icon
        is_current = self.current_tree and node.id == self.current_tree.current
        
        if node.id == "root":
            label = f"root: {node.title}"
        else:
            label = f"[{node.id}] {status_icon} {node.title}"
        
        # Add current marker with emphasis
        if is_current:
            return f"● {label}"
        return f"  {label}"
    
    def _add_children_to_tree(self, parent: TreeNode, node_id: str) -> None:
        """Recursively add children to tree widget."""
        if not self.current_tree:
            return
        
        node = self.current_tree.nodes[node_id]
        for child_id in node.children:
            child = self.current_tree.nodes[child_id]
            child_tree_node = parent.add(self._format_node_label(child), data=child_id)
            self._add_children_to_tree(child_tree_node, child_id)
    
    def _select_tree_node(self, node_id: str) -> None:
        """Select a node in the tree widget."""
        tree_widget = self.query_one("#node-tree", Tree)
        
        def find_node(tree_node: TreeNode) -> TreeNode | None:
            if tree_node.data == node_id:
                return tree_node
            for child in tree_node.children:
                result = find_node(child)
                if result:
                    return result
            return None
        
        target = find_node(tree_widget.root)
        if target:
            tree_widget.select_node(target)
            target.expand()
    
    def refresh_content(self) -> None:
        """Refresh the content panel."""
        title_widget = self.query_one("#node-title", Static)
        meta_widget = self.query_one("#node-meta", Static)
        body_widget = self.query_one("#node-body", Markdown)
        links_widget = self.query_one("#links-section", Static)
        
        if not self.current_tree:
            title_widget.update("未加载树")
            meta_widget.update("")
            body_widget.update("使用 `n` 新建树，或从左侧选择")
            links_widget.update("")
            return
        
        node = self.current_tree.get_current_node()
        
        # Title with status icon
        status_class = f"status-{node.status.value}"
        title_widget.update(f"{node.status.icon} {node.title}")
        
        # Meta info
        meta_widget.update(f"[{node.id}] · {node.status.value}")
        
        # Body
        if node.body:
            body_widget.update(node.body)
        else:
            body_widget.update("*空*")
        
        # Links
        links_parts = []
        if node.links:
            link_strs = []
            for lid in node.links:
                link_node = self.current_tree.nodes.get(lid)
                if link_node:
                    link_strs.append(f"[{lid}] {link_node.title}")
            links_parts.append("→ " + ", ".join(link_strs))
        
        backlinks = self.current_tree.get_backlinks(node.id)
        if backlinks:
            bl_strs = []
            for blid in backlinks:
                bl_node = self.current_tree.nodes.get(blid)
                if bl_node:
                    bl_strs.append(f"[{blid}] {bl_node.title}")
            links_parts.append("← " + ", ".join(bl_strs))
        
        links_widget.update("\n".join(links_parts) if links_parts else "")
    
    def update_focus(self) -> None:
        """Focus the appropriate widget based on focus_panel."""
        # CSS :focus-within handles visual styling automatically
        if self.focus_panel == 0:
            self.query_one("#trees-list", OptionList).focus()
        elif self.focus_panel == 1:
            self.query_one("#node-tree", Tree).focus()
        elif self.focus_panel == 2:
            self.query_one("#content-scroll", VerticalScroll).focus()
    
    def save_tree(self) -> None:
        """Save the current tree."""
        if self.current_tree:
            save_tree(self.current_tree)
    
    def navigate_to(self, node_id: str) -> None:
        """Navigate to a node."""
        if self._updating_tree:
            return
        if self.current_tree and node_id in self.current_tree.nodes:
            if self.current_tree.current == node_id:
                # Already at this node, just update content
                self.refresh_content()
                return
            self._updating_tree = True
            try:
                self.current_tree.go_to(node_id)
                self.save_tree()
                self.refresh_node_tree()
                self.refresh_content()
                self.link_index = 0
            finally:
                self._updating_tree = False
    
    # === Actions ===
    
    def action_focus_left(self) -> None:
        if self.focus_panel > 0:
            self.focus_panel -= 1
            self.update_focus()
    
    def action_focus_right(self) -> None:
        if self.focus_panel < 2:
            self.focus_panel += 1
            self.update_focus()
    
    def action_move_down(self) -> None:
        if self.focus_panel == 0:
            self.query_one("#trees-list", OptionList).action_cursor_down()
        elif self.focus_panel == 1:
            self.query_one("#node-tree", Tree).action_cursor_down()
    
    def action_move_up(self) -> None:
        if self.focus_panel == 0:
            self.query_one("#trees-list", OptionList).action_cursor_up()
        elif self.focus_panel == 1:
            self.query_one("#node-tree", Tree).action_cursor_up()
    
    def action_select(self) -> None:
        if self.focus_panel == 0:
            # Select tree - handled by OptionList.OptionSelected event
            trees_view = self.query_one("#trees-list", OptionList)
            if trees_view.highlighted is not None:
                option = trees_view.get_option_at_index(trees_view.highlighted)
                if option.id:
                    self._select_tree(option.id)
        elif self.focus_panel == 1:
            # Enter node
            tree_widget = self.query_one("#node-tree", Tree)
            if tree_widget.cursor_node and tree_widget.cursor_node.data:
                self.navigate_to(tree_widget.cursor_node.data)
    
    def _select_tree(self, name: str) -> None:
        """Select a tree by name."""
        set_current_tree_name(name)
        self.load_current_tree()
        self.refresh_trees_list()
        self.focus_panel = 1
        self.update_focus()
    
    def action_go_parent(self) -> None:
        if self.current_tree and self.current_tree.go_up():
            self.save_tree()
            self.refresh_node_tree()
            self.refresh_content()
    
    def action_go_back(self) -> None:
        if self.current_tree and self.current_tree.go_back():
            self.save_tree()
            self.refresh_node_tree()
            self.refresh_content()
    
    def action_go_root(self) -> None:
        if self.current_tree:
            self.current_tree.go_root()
            self.save_tree()
            self.refresh_node_tree()
            self.refresh_content()
    
    @work
    async def action_goto_node(self) -> None:
        if not self.current_tree:
            return
        
        # Use NodeIdSuggester for autocomplete
        suggester = NodeIdSuggester(self.current_tree)
        result = await self.push_screen_wait(InputScreen("跳转到节点 ID:", suggester=suggester))
        if result and result in self.current_tree.nodes:
            self.navigate_to(result)
    
    def action_next_link(self) -> None:
        if not self.current_tree:
            return
        
        node = self.current_tree.get_current_node()
        if node.links:
            self.link_index = (self.link_index + 1) % len(node.links)
            self.navigate_to(node.links[self.link_index])
    
    def action_prev_link(self) -> None:
        if not self.current_tree:
            return
        
        node = self.current_tree.get_current_node()
        if node.links:
            self.link_index = (self.link_index - 1) % len(node.links)
            self.navigate_to(node.links[self.link_index])
    
    @work
    async def action_add_child(self) -> None:
        if not self.current_tree:
            return
        
        result = await self.push_screen_wait(InputScreen("新子节点标题:"))
        if result:
            self.current_tree.add_child(self.current_tree.current, result)
            self.save_tree()
            self.refresh_node_tree()
            self.refresh_content()
    
    @work
    async def action_add_sibling(self) -> None:
        if not self.current_tree or self.current_tree.current == "root":
            return
        
        result = await self.push_screen_wait(InputScreen("新兄弟节点标题:"))
        if result:
            self.current_tree.add_sibling(self.current_tree.current, result)
            self.save_tree()
            self.refresh_node_tree()
            self.refresh_content()
    
    def action_edit_external(self) -> None:
        if not self.current_tree:
            return
        
        node_id = self.current_tree.current
        
        with self.suspend():
            try:
                edit_node_interactive(self.current_tree, node_id)
            except ValueError as e:
                self.notify(str(e), severity="error")
                return
        
        self.save_tree()
        self.refresh_node_tree()
        self.refresh_content()
    
    @work
    async def action_edit_title(self) -> None:
        if not self.current_tree:
            return
        
        node = self.current_tree.get_current_node()
        result = await self.push_screen_wait(InputScreen("编辑标题:", node.title))
        if result:
            self.current_tree.update_node(node.id, title=result)
            self.save_tree()
            self.refresh_node_tree()
            self.refresh_content()
    
    @work
    async def action_append_body(self) -> None:
        if not self.current_tree:
            return
        
        result = await self.push_screen_wait(InputScreen("追加内容:"))
        if result:
            self.current_tree.append_body(self.current_tree.current, result)
            self.save_tree()
            self.refresh_content()
    
    def action_mark_done(self) -> None:
        if not self.current_tree:
            return
        
        self.current_tree.set_status(self.current_tree.current, NodeStatus.DONE, auto_up=True)
        self.save_tree()
        self.refresh_node_tree()
        self.refresh_content()
        self.notify("✓ 已完成", timeout=1.5)
    
    def action_mark_dropped(self) -> None:
        if not self.current_tree:
            return
        
        self.current_tree.set_status(self.current_tree.current, NodeStatus.DROPPED, auto_up=True)
        self.save_tree()
        self.refresh_node_tree()
        self.refresh_content()
        self.notify("✗ 已放弃", timeout=1.5)
    
    def action_mark_todo(self) -> None:
        if not self.current_tree:
            return
        
        self.current_tree.set_status(self.current_tree.current, NodeStatus.TODO, auto_up=False)
        self.save_tree()
        self.refresh_node_tree()
        self.refresh_content()
        self.notify("? 待办", timeout=1.5)
    
    @work
    async def action_add_link(self) -> None:
        if not self.current_tree:
            return
        
        result = await self.push_screen_wait(
            SelectNodeScreen(self.current_tree, "选择链接目标:", self.current_tree.current)
        )
        if result:
            self.current_tree.add_link(self.current_tree.current, result)
            self.save_tree()
            self.refresh_content()
    
    @work
    async def action_remove_link(self) -> None:
        if not self.current_tree:
            return
        
        node = self.current_tree.get_current_node()
        if not node.links:
            return
        
        result = await self.push_screen_wait(InputScreen("移除链接到节点 ID:"))
        if result and result in node.links:
            self.current_tree.remove_link(node.id, result)
            self.save_tree()
            self.refresh_content()
    
    def action_show_backlinks(self) -> None:
        if not self.current_tree:
            return
        
        self.push_screen(BacklinksScreen(self.current_tree, self.current_tree.current))
    
    @work
    async def action_move_node(self) -> None:
        if not self.current_tree or self.current_tree.current == "root":
            return
        
        result = await self.push_screen_wait(
            SelectNodeScreen(self.current_tree, f"移动 [{self.current_tree.current}] 到:", self.current_tree.current)
        )
        if result:
            try:
                self.current_tree.move_node(self.current_tree.current, result)
                self.save_tree()
                self.refresh_node_tree()
            except ValueError as e:
                self.notify(str(e), severity="error")
    
    def action_yank_body(self) -> None:
        if not self.current_tree:
            return
        
        node = self.current_tree.get_current_node()
        try:
            pyperclip.copy(node.body)
            self.notify("已复制内容", timeout=1.5)
        except Exception:
            self.notify("剪贴板不可用", severity="warning")
    
    def action_paste_body(self) -> None:
        if not self.current_tree:
            return
        
        try:
            text = pyperclip.paste()
            self.current_tree.append_body(self.current_tree.current, text)
            self.save_tree()
            self.refresh_content()
            self.notify("已粘贴", timeout=1.5)
        except Exception:
            self.notify("剪贴板不可用", severity="warning")
    
    def action_yank_id(self) -> None:
        if not self.current_tree:
            return
        
        try:
            pyperclip.copy(self.current_tree.current)
            self.notify(f"已复制 [{self.current_tree.current}]", timeout=1.5)
        except Exception:
            self.notify("剪贴板不可用", severity="warning")
    
    @work
    async def action_new_tree(self) -> None:
        result = await self.push_screen_wait(InputScreen("新建树名称:"))
        if result:
            if tree_exists(result):
                self.notify(f"树 '{result}' 已存在", severity="error")
                return
            
            tree = ExplorationTree.create(result, "根节点")
            save_tree(tree, backup=False)
            set_current_tree_name(result)
            self.load_current_tree()
            self.refresh_trees_list()
            self.notify(f"已创建 '{result}'", timeout=2)
    
    @work
    async def action_rename_tree(self) -> None:
        if not self.current_tree:
            return
        
        result = await self.push_screen_wait(InputScreen("新名称:", self.current_tree.name))
        if result and result != self.current_tree.name:
            if tree_exists(result):
                self.notify(f"树 '{result}' 已存在", severity="error")
                return
            
            old_name = self.current_tree.name
            try:
                rename_tree(old_name, result)
                set_current_tree_name(result)
                self.load_current_tree()
                self.refresh_trees_list()
                self.notify(f"已重命名为 '{result}'", timeout=2)
            except Exception as e:
                self.notify(str(e), severity="error")
    
    @work
    async def action_delete_tree(self) -> None:
        if not self.current_tree:
            return
        
        confirmed = await self.push_screen_wait(
            ConfirmScreen(f"删除树 '{self.current_tree.name}'?")
        )
        if confirmed:
            name = self.current_tree.name
            delete_tree(name)
            set_current_tree_name(None)
            self.current_tree = None
            self.refresh_trees_list()
            self.refresh_node_tree()
            self.refresh_content()
            self.notify(f"已删除 '{name}'", timeout=2)
    
    @work
    async def action_search(self) -> None:
        if not self.current_tree:
            return
        
        result = await self.push_screen_wait(SearchScreen(self.current_tree))
        if result:
            self.navigate_to(result)
    
    def action_show_stats(self) -> None:
        if not self.current_tree:
            return
        
        self.push_screen(StatisticsScreen(self.current_tree))
    
    def action_show_help(self) -> None:
        self.push_screen(HelpScreen())
    
    @work
    async def action_select_theme(self) -> None:
        result = await self.push_screen_wait(ThemeSelectorScreen(self._theme_name))
        if result and result != self._theme_name:
            self._theme_name = result
            self._config.theme = result
            self._config.save()
            # Hot reload theme using Textual's built-in mechanism
            self.theme = result
            display_name = THEME_DISPLAY_NAMES.get(result, result)
            self.notify(f"主题已切换: {display_name}", timeout=2)
    
    def action_force_save(self) -> None:
        self.save_tree()
        self.notify("已保存", timeout=1.5)
    
    @on(Tree.NodeHighlighted)
    def on_tree_node_highlighted(self, event: Tree.NodeHighlighted) -> None:
        """Handle tree node highlight (cursor movement)."""
        if self._updating_tree:
            return
        if event.node.data and self.current_tree:
            node_id = event.node.data
            if self.current_tree.current != node_id:
                self._updating_tree = True
                try:
                    self.current_tree.go_to(node_id)
                    self.save_tree()
                    self.refresh_content()
                    self.link_index = 0
                finally:
                    self._updating_tree = False
    
    @on(OptionList.OptionSelected, "#trees-list")
    def on_tree_list_selected(self, event: OptionList.OptionSelected) -> None:
        """Handle tree list selection."""
        if event.option.id:
            self._select_tree(event.option.id)


def run_tui() -> None:
    """Run the TUI application."""
    app = DelvApp()
    app.run()


if __name__ == "__main__":
    run_tui()
