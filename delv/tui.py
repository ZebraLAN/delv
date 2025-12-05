"""TUI interface for Delv using Textual."""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

import pyperclip
from textual import on
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
from textual.message import Message
from textual.screen import ModalScreen
from textual.widgets import (
    Footer,
    Header,
    Input,
    Label,
    ListItem,
    ListView,
    Markdown,
    Static,
    Tree,
)
from textual.widgets.tree import TreeNode

from .config import get_current_tree_name, get_editor, set_current_tree_name
from .storage import (
    delete_tree,
    list_trees,
    load_tree,
    rename_tree,
    save_tree,
    tree_exists,
)
from .tree import ExplorationTree, Node, NodeStatus


# === Screens ===

class HelpScreen(ModalScreen):
    """Help screen showing keybindings."""
    
    BINDINGS = [
        Binding("escape", "dismiss", "Close"),
        Binding("q", "dismiss", "Close"),
        Binding("j", "scroll_down", "Scroll down", show=False),
        Binding("k", "scroll_up", "Scroll up", show=False),
        Binding("down", "scroll_down", "Scroll down", show=False),
        Binding("up", "scroll_up", "Scroll up", show=False),
        Binding("pagedown", "page_down", "Page down", show=False),
        Binding("pageup", "page_up", "Page up", show=False),
        Binding("g", "scroll_top", "Top", show=False),
        Binding("G", "scroll_bottom", "Bottom", show=False),
    ]
    
    def compose(self) -> ComposeResult:
        help_text = """# Delv - Keyboard Shortcuts

**Navigation:** `j/k` scroll, `q/Esc` close

## Navigation
| Key | Action |
|-----|--------|
| `h` `l` | Switch panel focus (left/right) |
| `j` `k` | Move up/down in list |
| `Enter` | Enter node / Open tree |
| `Backspace` | Go to parent node |
| `-` | Go back in history |
| `r` | Jump to root |
| `g` | Goto node by ID |
| `]` `[` | Jump to next/prev link |

## Editing
| Key | Action |
|-----|--------|
| `a` | Add child node |
| `A` | Add sibling node |
| `e` | Edit node (external editor) |
| `E` | Quick edit title |
| `i` | Quick append to body |
| `d` | Mark done (auto-return) |
| `x` | Mark dropped (auto-return) |
| `t` | Mark todo |

## Links & Structure
| Key | Action |
|-----|--------|
| `L` | Add link |
| `U` | Remove link |
| `B` | Show backlinks |
| `m` | Move node mode |
| `y` | Yank body to clipboard |
| `p` | Paste to body |
| `Y` | Yank node ID |

## Trees
| Key | Action |
|-----|--------|
| `n` | New tree |
| `R` | Rename tree |
| `D` | Delete tree |

## Other
| Key | Action |
|-----|--------|
| `/` | Search |
| `s` | Statistics |
| `?` | This help |
| `q` | Quit |
| `Ctrl+S` | Force save |
"""
        from textual.containers import VerticalScroll
        yield Container(
            VerticalScroll(
                Markdown(help_text, id="help-content"),
                id="help-scroll",
            ),
            id="help-container",
        )
    
    def action_dismiss(self) -> None:
        self.app.pop_screen()
    
    def action_scroll_down(self) -> None:
        self.query_one("#help-scroll").scroll_down()
    
    def action_scroll_up(self) -> None:
        self.query_one("#help-scroll").scroll_up()
    
    def action_page_down(self) -> None:
        self.query_one("#help-scroll").scroll_page_down()
    
    def action_page_up(self) -> None:
        self.query_one("#help-scroll").scroll_page_up()
    
    def action_scroll_top(self) -> None:
        self.query_one("#help-scroll").scroll_home()
    
    def action_scroll_bottom(self) -> None:
        self.query_one("#help-scroll").scroll_end()


class InputScreen(ModalScreen[str | None]):
    """Modal screen for text input."""
    
    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
    ]
    
    def __init__(self, prompt: str, default: str = "") -> None:
        super().__init__()
        self.prompt = prompt
        self.default = default
    
    def compose(self) -> ComposeResult:
        yield Container(
            Label(self.prompt, id="input-prompt"),
            Input(value=self.default, id="input-field"),
            id="input-container",
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
        Binding("y", "confirm", "Yes"),
        Binding("n", "cancel", "No"),
        Binding("escape", "cancel", "Cancel"),
    ]
    
    def __init__(self, message: str) -> None:
        super().__init__()
        self.message = message
    
    def compose(self) -> ComposeResult:
        yield Container(
            Label(self.message, id="confirm-message"),
            Label("[y] Yes  [n] No", id="confirm-options"),
            id="confirm-container",
        )
    
    def action_confirm(self) -> None:
        self.dismiss(True)
    
    def action_cancel(self) -> None:
        self.dismiss(False)


class SearchScreen(ModalScreen[str | None]):
    """Modal screen for search."""
    
    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
    ]
    
    def __init__(self, tree: ExplorationTree) -> None:
        super().__init__()
        self.current_tree = tree
        self.results: list[str] = []
    
    def compose(self) -> ComposeResult:
        yield Container(
            Input(placeholder="Search...", id="search-input"),
            ListView(id="search-results"),
            id="search-container",
        )
    
    def on_mount(self) -> None:
        self.query_one(Input).focus()
    
    @on(Input.Changed)
    def on_search_changed(self, event: Input.Changed) -> None:
        results_view = self.query_one("#search-results", ListView)
        results_view.clear()
        
        query = event.value.strip()
        if not query:
            self.results = []
            return
        
        self.results = self.current_tree.search(query)
        for nid in self.results[:20]:  # Limit to 20 results
            node = self.current_tree.nodes[nid]
            results_view.append(
                ListItem(Label(f"[{nid}] {node.status.icon} {node.title}"))
            )
    
    @on(Input.Submitted)
    def on_search_submit(self, event: Input.Submitted) -> None:
        if self.results:
            self.dismiss(self.results[0])
        else:
            self.dismiss(None)
    
    @on(ListView.Selected)
    def on_result_selected(self, event: ListView.Selected) -> None:
        if event.list_view.index is not None and event.list_view.index < len(self.results):
            self.dismiss(self.results[event.list_view.index])
    
    def action_cancel(self) -> None:
        self.dismiss(None)


class SelectNodeScreen(ModalScreen[str | None]):
    """Modal screen for selecting a node (for move/link operations)."""
    
    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
    ]
    
    def __init__(self, tree: ExplorationTree, prompt: str, exclude: str | None = None) -> None:
        super().__init__()
        self.current_tree = tree
        self.prompt = prompt
        self.exclude = exclude
        self.node_ids: list[str] = []
    
    def compose(self) -> ComposeResult:
        yield Container(
            Label(self.prompt, id="select-prompt"),
            ListView(id="select-list"),
            id="select-container",
        )
    
    def on_mount(self) -> None:
        list_view = self.query_one("#select-list", ListView)
        
        for nid, depth in self.current_tree.iter_tree():
            if nid == self.exclude:
                continue
            node = self.current_tree.nodes[nid]
            indent = "  " * depth
            self.node_ids.append(nid)
            list_view.append(
                ListItem(Label(f"{indent}[{nid}] {node.status.icon} {node.title}"))
            )
        
        list_view.focus()
    
    @on(ListView.Selected)
    def on_selected(self, event: ListView.Selected) -> None:
        if event.list_view.index is not None and event.list_view.index < len(self.node_ids):
            self.dismiss(self.node_ids[event.list_view.index])
    
    def action_cancel(self) -> None:
        self.dismiss(None)


class BacklinksScreen(ModalScreen):
    """Modal screen showing backlinks."""
    
    BINDINGS = [
        Binding("escape", "dismiss", "Close"),
        Binding("q", "dismiss", "Close"),
    ]
    
    def __init__(self, tree: ExplorationTree, node_id: str) -> None:
        super().__init__()
        self.current_tree = tree
        self.node_id = node_id
        self.backlink_ids: list[str] = []
    
    def compose(self) -> ComposeResult:
        node = self.current_tree.nodes[self.node_id]
        yield Container(
            Label(f"Backlinks to [{self.node_id}] {node.title}", id="backlinks-title"),
            ListView(id="backlinks-list"),
            id="backlinks-container",
        )
    
    def on_mount(self) -> None:
        list_view = self.query_one("#backlinks-list", ListView)
        self.backlink_ids = self.current_tree.get_backlinks(self.node_id)
        
        if not self.backlink_ids:
            list_view.append(ListItem(Label("(no backlinks)")))
        else:
            for nid in self.backlink_ids:
                node = self.current_tree.nodes[nid]
                list_view.append(
                    ListItem(Label(f"[{nid}] {node.status.icon} {node.title}"))
                )
        
        list_view.focus()
    
    @on(ListView.Selected)
    def on_selected(self, event: ListView.Selected) -> None:
        if self.backlink_ids and event.list_view.index is not None:
            if event.list_view.index < len(self.backlink_ids):
                # Navigate to the selected backlink
                self.app.navigate_to(self.backlink_ids[event.list_view.index])
                self.app.pop_screen()
    
    def action_dismiss(self) -> None:
        self.app.pop_screen()


class StatisticsScreen(ModalScreen):
    """Modal screen showing statistics."""
    
    BINDINGS = [
        Binding("escape", "dismiss", "Close"),
        Binding("q", "dismiss", "Close"),
    ]
    
    def __init__(self, tree: ExplorationTree) -> None:
        super().__init__()
        self.current_tree = tree
    
    def compose(self) -> ComposeResult:
        stats = self.current_tree.get_statistics()
        content = f"""
# {self.current_tree.name} Statistics

| Metric | Value |
|--------|-------|
| Total nodes | {stats['total']} |
| ► Active | {stats['active']} |
| ✓ Done | {stats['done']} |
| ✗ Dropped | {stats['dropped']} |
| ? Todo | {stats['todo']} |
| Leaf nodes | {stats['leaves']} |
| Max depth | {stats['max_depth']} |

Created: {self.current_tree.created.strftime('%Y-%m-%d %H:%M')}
Updated: {self.current_tree.updated.strftime('%Y-%m-%d %H:%M')}
"""
        yield Container(
            Markdown(content, id="stats-content"),
            id="stats-container",
        )
    
    def action_dismiss(self) -> None:
        self.app.pop_screen()


# === Main App ===

class DelvApp(App):
    """Delv TUI Application."""
    
    CSS = """
    /* Layout */
    #main-container {
        layout: horizontal;
    }
    
    #trees-panel {
        width: 20%;
        min-width: 16;
        border: solid $primary;
    }
    
    #nodes-panel {
        width: 40%;
        border: solid $primary;
    }
    
    #content-panel {
        width: 40%;
        border: solid $primary;
    }
    
    .panel-title {
        background: $primary;
        color: $text;
        text-align: center;
        padding: 0 1;
    }
    
    .focused .panel-title {
        background: $accent;
    }
    
    /* Trees list */
    #trees-list {
        height: 100%;
    }
    
    #trees-list > ListItem {
        padding: 0 1;
    }
    
    #trees-list > ListItem.--highlight {
        background: $accent;
    }
    
    /* Node tree */
    #node-tree {
        height: 100%;
        scrollbar-gutter: stable;
    }
    
    #node-tree > .tree--cursor {
        background: $accent;
    }
    
    /* Content panel */
    #content-scroll {
        height: 100%;
        padding: 1;
    }
    
    #node-title {
        text-style: bold;
        margin-bottom: 1;
    }
    
    #node-body {
        margin-bottom: 1;
    }
    
    #links-section {
        border-top: solid $primary-darken-2;
        padding-top: 1;
        margin-top: 1;
    }
    
    /* Modal screens */
    #input-container, #confirm-container,
    #search-container, #select-container, #backlinks-container,
    #stats-container {
        align: center middle;
        width: 80%;
        max-width: 80;
        height: auto;
        max-height: 80%;
        background: $surface;
        border: thick $primary;
        padding: 1 2;
    }
    
    #help-container {
        align: center middle;
        width: 90%;
        max-width: 100;
        height: 90%;
        background: $surface;
        border: thick $primary;
        padding: 1 2;
    }
    
    #help-scroll {
        height: 100%;
        scrollbar-gutter: stable;
    }
    
    #help-content {
        height: auto;
    }
    
    #stats-content {
        height: auto;
        max-height: 60;
        overflow-y: auto;
    }
    
    #input-prompt, #select-prompt, #confirm-message, #backlinks-title {
        margin-bottom: 1;
    }
    
    #confirm-options {
        text-align: center;
        margin-top: 1;
    }
    
    #search-results, #select-list, #backlinks-list {
        height: auto;
        max-height: 20;
        margin-top: 1;
    }
    
    /* Status colors */
    .status-active { color: $success; }
    .status-done { color: $primary; }
    .status-dropped { color: $error; }
    .status-todo { color: $warning; }
    
    /* Focus indicators */
    .panel:focus-within {
        border: solid $accent;
    }
    """
    
    BINDINGS = [
        # Navigation
        Binding("h", "focus_left", "Left panel", show=False),
        Binding("l", "focus_right", "Right panel", show=False),
        Binding("j", "move_down", "Down", show=False),
        Binding("k", "move_up", "Up", show=False),
        Binding("enter", "select", "Select", show=False),
        Binding("backspace", "go_parent", "Parent", show=False),
        Binding("minus", "go_back", "Back", show=False),
        Binding("r", "go_root", "Root", show=False),
        Binding("g", "goto_node", "Goto", show=False),
        Binding("bracketright", "next_link", "Next link", show=False),
        Binding("bracketleft", "prev_link", "Prev link", show=False),
        
        # Editing
        Binding("a", "add_child", "Add child", show=False),
        Binding("A", "add_sibling", "Add sibling", show=False),
        Binding("e", "edit_external", "Edit", show=False),
        Binding("E", "edit_title", "Edit title", show=False),
        Binding("i", "append_body", "Append", show=False),
        Binding("d", "mark_done", "Done", show=False),
        Binding("x", "mark_dropped", "Drop", show=False),
        Binding("t", "mark_todo", "Todo", show=False),
        
        # Links & Structure
        Binding("L", "add_link", "Add link", show=False),
        Binding("U", "remove_link", "Remove link", show=False),
        Binding("B", "show_backlinks", "Backlinks", show=False),
        Binding("m", "move_node", "Move", show=False),
        Binding("y", "yank_body", "Yank", show=False),
        Binding("p", "paste_body", "Paste", show=False),
        Binding("Y", "yank_id", "Yank ID", show=False),
        
        # Trees
        Binding("n", "new_tree", "New tree", show=False),
        Binding("R", "rename_tree", "Rename", show=False),
        Binding("D", "delete_tree", "Delete", show=False),
        
        # Other
        Binding("slash", "search", "Search", show=False),
        Binding("s", "show_stats", "Stats", show=False),
        Binding("question_mark", "show_help", "Help"),
        Binding("ctrl+s", "force_save", "Save", show=False),
        Binding("q", "quit", "Quit"),
    ]
    
    def __init__(self) -> None:
        super().__init__()
        self.current_tree: ExplorationTree | None = None
        self.current_trees_list: list[str] = []
        self.focus_panel: int = 1  # 0=trees, 1=nodes, 2=content
        self.link_index: int = 0
        self._updating_tree: bool = False  # Prevent recursive updates
    
    def compose(self) -> ComposeResult:
        yield Header()
        yield Horizontal(
            Vertical(
                Static("Trees", classes="panel-title"),
                ListView(id="trees-list"),
                id="trees-panel",
                classes="panel",
            ),
            Vertical(
                Static("Nodes", classes="panel-title"),
                Tree("root", id="node-tree"),
                id="nodes-panel",
                classes="panel",
            ),
            Vertical(
                Static("Content", classes="panel-title"),
                Container(
                    Static("", id="node-title"),
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
    
    def on_mount(self) -> None:
        self.refresh_trees_list()
        self.load_current_tree()
        self.update_focus()
    
    def refresh_trees_list(self) -> None:
        """Refresh the trees list."""
        self.current_trees_list = list_trees()
        trees_view = self.query_one("#trees-list", ListView)
        trees_view.clear()
        
        current_name = get_current_tree_name()
        for name in self.current_trees_list:
            prefix = "► " if name == current_name else "  "
            trees_view.append(ListItem(Label(f"{prefix}{name}")))
    
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
                tree_widget.root.set_label("(no tree loaded)")
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
        current_marker = " ←" if self.current_tree and node.id == self.current_tree.current else ""
        
        if node.id == "root":
            return f"root: {node.title}{current_marker}"
        return f"[{node.id}] {status_icon} {node.title}{current_marker}"
    
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
        body_widget = self.query_one("#node-body", Markdown)
        links_widget = self.query_one("#links-section", Static)
        
        if not self.current_tree:
            title_widget.update("No tree loaded")
            body_widget.update("")
            links_widget.update("")
            return
        
        node = self.current_tree.get_current_node()
        
        # Title
        title_widget.update(f"[{node.id}] {node.status.icon} {node.title} ({node.status.value})")
        
        # Body
        body_widget.update(node.body if node.body else "*empty*")
        
        # Links
        links_text = ""
        if node.links:
            link_strs = []
            for lid in node.links:
                link_node = self.current_tree.nodes.get(lid)
                if link_node:
                    link_strs.append(f"[{lid}] {link_node.title}")
            links_text += "→ Links: " + ", ".join(link_strs) + "\n"
        
        backlinks = self.current_tree.get_backlinks(node.id)
        if backlinks:
            bl_strs = []
            for blid in backlinks:
                bl_node = self.current_tree.nodes.get(blid)
                if bl_node:
                    bl_strs.append(f"[{blid}] {bl_node.title}")
            links_text += "← Backlinks: " + ", ".join(bl_strs)
        
        links_widget.update(links_text)
    
    def update_focus(self) -> None:
        """Update visual focus indicators."""
        panels = ["#trees-panel", "#nodes-panel", "#content-panel"]
        for i, panel_id in enumerate(panels):
            panel = self.query_one(panel_id)
            if i == self.focus_panel:
                panel.add_class("focused")
            else:
                panel.remove_class("focused")
        
        # Actually focus the widget
        if self.focus_panel == 0:
            self.query_one("#trees-list", ListView).focus()
        elif self.focus_panel == 1:
            self.query_one("#node-tree", Tree).focus()
    
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
            self.query_one("#trees-list", ListView).action_cursor_down()
        elif self.focus_panel == 1:
            self.query_one("#node-tree", Tree).action_cursor_down()
    
    def action_move_up(self) -> None:
        if self.focus_panel == 0:
            self.query_one("#trees-list", ListView).action_cursor_up()
        elif self.focus_panel == 1:
            self.query_one("#node-tree", Tree).action_cursor_up()
    
    def action_select(self) -> None:
        if self.focus_panel == 0:
            # Select tree
            trees_view = self.query_one("#trees-list", ListView)
            if trees_view.index is not None and trees_view.index < len(self.current_trees_list):
                name = self.current_trees_list[trees_view.index]
                set_current_tree_name(name)
                self.load_current_tree()
                self.refresh_trees_list()
                self.focus_panel = 1
                self.update_focus()
        elif self.focus_panel == 1:
            # Enter node
            tree_widget = self.query_one("#node-tree", Tree)
            if tree_widget.cursor_node and tree_widget.cursor_node.data:
                self.navigate_to(tree_widget.cursor_node.data)
    
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
    
    async def action_goto_node(self) -> None:
        if not self.current_tree:
            return
        
        result = await self.push_screen_wait(InputScreen("Go to node ID:"))
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
    
    async def action_add_child(self) -> None:
        if not self.current_tree:
            return
        
        result = await self.push_screen_wait(InputScreen("New child title:"))
        if result:
            self.current_tree.add_child(self.current_tree.current, result)
            self.save_tree()
            self.refresh_node_tree()
            self.refresh_content()
    
    async def action_add_sibling(self) -> None:
        if not self.current_tree or self.current_tree.current == "root":
            return
        
        result = await self.push_screen_wait(InputScreen("New sibling title:"))
        if result:
            self.current_tree.add_sibling(self.current_tree.current, result)
            self.save_tree()
            self.refresh_node_tree()
            self.refresh_content()
    
    def action_edit_external(self) -> None:
        if not self.current_tree:
            return
        
        node = self.current_tree.get_current_node()
        
        # Create temp file
        links_str = ", ".join(node.links) if node.links else ""
        content = f"""---
title: {node.title}
status: {node.status.value}
links: [{links_str}]
---

{node.body}"""
        
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8") as f:
            f.write(content)
            temp_path = Path(f.name)
        
        try:
            editor = get_editor()
            # Suspend TUI and run editor
            with self.suspend():
                subprocess.run([editor, str(temp_path)], check=True)
            
            # Parse result
            new_content = temp_path.read_text(encoding="utf-8")
            
            if new_content.startswith("---"):
                parts = new_content.split("---", 2)
                if len(parts) >= 3:
                    frontmatter = parts[1].strip()
                    body = parts[2].strip()
                    
                    title = node.title
                    status = node.status
                    links = node.links
                    
                    for line in frontmatter.split("\n"):
                        if ":" in line:
                            key, value = line.split(":", 1)
                            key = key.strip()
                            value = value.strip()
                            
                            if key == "title":
                                title = value
                            elif key == "status":
                                try:
                                    status = NodeStatus(value)
                                except ValueError:
                                    pass
                            elif key == "links":
                                value = value.strip("[]")
                                if value:
                                    links = [l.strip() for l in value.split(",") if l.strip()]
                                else:
                                    links = []
                    
                    self.current_tree.update_node(node.id, title=title, body=body, status=status, links=links)
            else:
                self.current_tree.update_node(node.id, body=new_content.strip())
            
            self.save_tree()
            self.refresh_node_tree()
            self.refresh_content()
        
        finally:
            temp_path.unlink()
    
    async def action_edit_title(self) -> None:
        if not self.current_tree:
            return
        
        node = self.current_tree.get_current_node()
        result = await self.push_screen_wait(InputScreen("Edit title:", node.title))
        if result:
            self.current_tree.update_node(node.id, title=result)
            self.save_tree()
            self.refresh_node_tree()
            self.refresh_content()
    
    async def action_append_body(self) -> None:
        if not self.current_tree:
            return
        
        result = await self.push_screen_wait(InputScreen("Append to body:"))
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
    
    def action_mark_dropped(self) -> None:
        if not self.current_tree:
            return
        
        self.current_tree.set_status(self.current_tree.current, NodeStatus.DROPPED, auto_up=True)
        self.save_tree()
        self.refresh_node_tree()
        self.refresh_content()
    
    def action_mark_todo(self) -> None:
        if not self.current_tree:
            return
        
        self.current_tree.set_status(self.current_tree.current, NodeStatus.TODO, auto_up=False)
        self.save_tree()
        self.refresh_node_tree()
        self.refresh_content()
    
    async def action_add_link(self) -> None:
        if not self.current_tree:
            return
        
        result = await self.push_screen_wait(
            SelectNodeScreen(self.current_tree, "Select link target:", self.current_tree.current)
        )
        if result:
            self.current_tree.add_link(self.current_tree.current, result)
            self.save_tree()
            self.refresh_content()
    
    async def action_remove_link(self) -> None:
        if not self.current_tree:
            return
        
        node = self.current_tree.get_current_node()
        if not node.links:
            return
        
        result = await self.push_screen_wait(InputScreen("Remove link to node ID:"))
        if result and result in node.links:
            self.current_tree.remove_link(node.id, result)
            self.save_tree()
            self.refresh_content()
    
    def action_show_backlinks(self) -> None:
        if not self.current_tree:
            return
        
        self.push_screen(BacklinksScreen(self.current_tree, self.current_tree.current))
    
    async def action_move_node(self) -> None:
        if not self.current_tree or self.current_tree.current == "root":
            return
        
        result = await self.push_screen_wait(
            SelectNodeScreen(self.current_tree, f"Move [{self.current_tree.current}] to:", self.current_tree.current)
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
            self.notify("Copied body to clipboard")
        except Exception:
            self.notify("Clipboard not available", severity="warning")
    
    def action_paste_body(self) -> None:
        if not self.current_tree:
            return
        
        try:
            text = pyperclip.paste()
            self.current_tree.append_body(self.current_tree.current, text)
            self.save_tree()
            self.refresh_content()
            self.notify("Pasted to body")
        except Exception:
            self.notify("Clipboard not available", severity="warning")
    
    def action_yank_id(self) -> None:
        if not self.current_tree:
            return
        
        try:
            pyperclip.copy(self.current_tree.current)
            self.notify(f"Copied [{self.current_tree.current}] to clipboard")
        except Exception:
            self.notify("Clipboard not available", severity="warning")
    
    async def action_new_tree(self) -> None:
        result = await self.push_screen_wait(InputScreen("New tree name:"))
        if result:
            if tree_exists(result):
                self.notify(f"Tree '{result}' already exists", severity="error")
                return
            
            tree = ExplorationTree.create(result, "Root")
            save_tree(tree, backup=False)
            set_current_tree_name(result)
            self.load_current_tree()
            self.refresh_trees_list()
            self.notify(f"Created tree '{result}'")
    
    async def action_rename_tree(self) -> None:
        if not self.current_tree:
            return
        
        result = await self.push_screen_wait(InputScreen("New name:", self.current_tree.name))
        if result and result != self.current_tree.name:
            if tree_exists(result):
                self.notify(f"Tree '{result}' already exists", severity="error")
                return
            
            old_name = self.current_tree.name
            try:
                rename_tree(old_name, result)
                set_current_tree_name(result)
                self.load_current_tree()
                self.refresh_trees_list()
                self.notify(f"Renamed to '{result}'")
            except Exception as e:
                self.notify(str(e), severity="error")
    
    async def action_delete_tree(self) -> None:
        if not self.current_tree:
            return
        
        confirmed = await self.push_screen_wait(
            ConfirmScreen(f"Delete tree '{self.current_tree.name}'?")
        )
        if confirmed:
            name = self.current_tree.name
            delete_tree(name)
            set_current_tree_name(None)
            self.current_tree = None
            self.refresh_trees_list()
            self.refresh_node_tree()
            self.refresh_content()
            self.notify(f"Deleted tree '{name}'")
    
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
    
    def action_force_save(self) -> None:
        self.save_tree()
        self.notify("Saved")
    
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
    
    @on(ListView.Selected, "#trees-list")
    def on_tree_list_selected(self, event: ListView.Selected) -> None:
        """Handle tree list selection."""
        if event.list_view.index is not None and event.list_view.index < len(self.current_trees_list):
            name = self.current_trees_list[event.list_view.index]
            set_current_tree_name(name)
            self.load_current_tree()
            self.refresh_trees_list()
            self.focus_panel = 1
            self.update_focus()


def run_tui() -> None:
    """Run the TUI application."""
    app = DelvApp()
    app.run()


if __name__ == "__main__":
    run_tui()

