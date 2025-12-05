"""CLI commands for Delv."""

from __future__ import annotations

from pathlib import Path

import click
import pyperclip

from . import display
from .config import (
    Config,
    ensure_delv_dir,
    get_current_tree_name,
    set_current_tree_name,
)
from .editor import edit_node_interactive
from .storage import (
    copy_tree,
    delete_tree,
    export_tree,
    export_tree_markdown,
    import_tree,
    list_trees,
    load_tree,
    rename_tree,
    save_tree,
    tree_exists,
)
from .tree import ExplorationTree, NodeStatus


def get_current_tree() -> ExplorationTree:
    """Get the current tree or raise an error."""
    name = get_current_tree_name()
    if not name:
        raise click.ClickException("No tree is currently open. Use 'delv open <name>' or 'delv new <name>'")
    try:
        return load_tree(name)
    except FileNotFoundError:
        raise click.ClickException(f"Tree '{name}' not found")


def save_current(tree: ExplorationTree) -> None:
    """Save the current tree."""
    save_tree(tree)




# === Main group ===

@click.group(invoke_without_command=True)
@click.pass_context
def cli(ctx):
    """Delv - A tree-based exploration tracking tool."""
    ensure_delv_dir()
    
    if ctx.invoked_subcommand is None:
        config = Config.load()
        if config.default_mode == "tui":
            ctx.invoke(tui_cmd)
        else:
            ctx.invoke(show_cmd)


# === Mode commands ===

@cli.command("tui")
def tui_cmd():
    """Open the TUI interface."""
    from .tui import run_tui
    run_tui()


@cli.command("show")
@click.option("-a", "--all", "show_all", is_flag=True, help="Show all nodes expanded")
@click.option("-d", "--depth", type=int, help="Limit display depth")
def show_cmd(show_all, depth):
    """Show the current tree."""
    tree = get_current_tree()
    display.print_tree(tree, max_depth=depth, show_all=show_all)


# === Tree management ===

@cli.command("new")
@click.argument("name")
@click.argument("title", default="Root")
def new_cmd(name, title):
    """Create a new tree."""
    if tree_exists(name):
        raise click.ClickException(f"Tree '{name}' already exists")
    
    tree = ExplorationTree.create(name, title)
    save_tree(tree, backup=False)
    set_current_tree_name(name)
    display.print_success(f"Created tree '{name}'")


@cli.command("ls")
def ls_cmd():
    """List all trees."""
    trees = list_trees()
    current = get_current_tree_name()
    display.print_trees_list(trees, current)


@cli.command("open")
@click.argument("name")
def open_cmd(name):
    """Open/switch to a tree."""
    if not tree_exists(name):
        raise click.ClickException(f"Tree '{name}' not found")
    
    set_current_tree_name(name)
    display.print_success(f"Opened tree '{name}'")


@cli.command("rm")
@click.argument("name")
@click.confirmation_option(prompt="Are you sure you want to delete this tree?")
def rm_tree_cmd(name):
    """Delete a tree."""
    if not tree_exists(name):
        raise click.ClickException(f"Tree '{name}' not found")
    
    delete_tree(name)
    
    if get_current_tree_name() == name:
        set_current_tree_name(None)
    
    display.print_success(f"Deleted tree '{name}'")


@cli.command("rename")
@click.argument("old_name")
@click.argument("new_name")
def rename_tree_cmd(old_name, new_name):
    """Rename a tree."""
    try:
        rename_tree(old_name, new_name)
        if get_current_tree_name() == old_name:
            set_current_tree_name(new_name)
        display.print_success(f"Renamed '{old_name}' to '{new_name}'")
    except FileNotFoundError:
        raise click.ClickException(f"Tree '{old_name}' not found")
    except FileExistsError:
        raise click.ClickException(f"Tree '{new_name}' already exists")


@cli.command("cp")
@click.argument("src")
@click.argument("dst")
def cp_tree_cmd(src, dst):
    """Copy a tree."""
    try:
        copy_tree(src, dst)
        display.print_success(f"Copied '{src}' to '{dst}'")
    except FileNotFoundError:
        raise click.ClickException(f"Tree '{src}' not found")
    except FileExistsError:
        raise click.ClickException(f"Tree '{dst}' already exists")


# === Display commands ===

@cli.command("path")
def path_cmd():
    """Show path from root to current node."""
    tree = get_current_tree()
    display.print_path(tree)


@cli.command("cat")
@click.argument("node_id", required=False)
def cat_cmd(node_id):
    """Output node body."""
    tree = get_current_tree()
    display.print_node_body(tree, node_id)


# === Navigation ===

@cli.command("go")
@click.argument("node_id")
def go_cmd(node_id):
    """Jump to a node."""
    tree = get_current_tree()
    if node_id not in tree.nodes:
        raise click.ClickException(f"Node '{node_id}' not found")
    
    tree.go_to(node_id)
    save_current(tree)
    display.print_success(f"Moved to [{node_id}]")


@cli.command("up")
def up_cmd():
    """Go to parent node."""
    tree = get_current_tree()
    if tree.go_up():
        save_current(tree)
        display.print_success(f"Moved to [{tree.current}]")
    else:
        display.print_info("Already at root")


@cli.command("down")
@click.argument("n", type=int, default=0)
def down_cmd(n):
    """Go to nth child node."""
    tree = get_current_tree()
    if tree.go_down(n):
        save_current(tree)
        display.print_success(f"Moved to [{tree.current}]")
    else:
        display.print_info("No children")


@cli.command("next")
def next_cmd():
    """Go to next sibling."""
    tree = get_current_tree()
    if tree.go_next_sibling():
        save_current(tree)
        display.print_success(f"Moved to [{tree.current}]")
    else:
        display.print_info("No next sibling")


@cli.command("prev")
def prev_cmd():
    """Go to previous sibling."""
    tree = get_current_tree()
    if tree.go_prev_sibling():
        save_current(tree)
        display.print_success(f"Moved to [{tree.current}]")
    else:
        display.print_info("No previous sibling")


@cli.command("root")
def root_cmd():
    """Go to root node."""
    tree = get_current_tree()
    tree.go_root()
    save_current(tree)
    display.print_success("Moved to root")


@cli.command("back")
def back_cmd():
    """Go back in history."""
    tree = get_current_tree()
    if tree.go_back():
        save_current(tree)
        display.print_success(f"Moved to [{tree.current}]")
    else:
        display.print_info("No history")


# === Editing ===

@cli.command("add")
@click.argument("title", required=False)
@click.option("-s", "--sibling", is_flag=True, help="Add as sibling instead of child")
def add_cmd(title, sibling):
    """Add a new node."""
    tree = get_current_tree()
    title = title or "New node"
    
    if sibling:
        if tree.current == "root":
            raise click.ClickException("Cannot add sibling to root")
        node = tree.add_sibling(tree.current, title)
    else:
        node = tree.add_child(tree.current, title)
    
    save_current(tree)
    display.print_success(f"Created [{node.id}] {title}")


@cli.command("edit")
@click.argument("node_id", required=False)
def edit_cmd(node_id):
    """Edit a node in external editor."""
    tree = get_current_tree()
    nid = node_id or tree.current
    try:
        edit_node_interactive(tree, nid)
        save_current(tree)
        display.print_success(f"Updated node [{nid}]")
    except ValueError as e:
        raise click.ClickException(str(e))


@cli.command("title")
@click.argument("text")
def title_cmd(text):
    """Change current node's title."""
    tree = get_current_tree()
    tree.update_node(tree.current, title=text)
    save_current(tree)
    display.print_success(f"Updated title to '{text}'")


@cli.command("append")
@click.argument("text")
def append_cmd(text):
    """Append text to current node's body."""
    tree = get_current_tree()
    tree.append_body(tree.current, text)
    save_current(tree)
    display.print_success("Appended to body")


@cli.command("yank")
@click.argument("node_id", required=False)
def yank_cmd(node_id):
    """Copy node body to clipboard."""
    tree = get_current_tree()
    nid = node_id or tree.current
    node = tree.nodes.get(nid)
    if not node:
        raise click.ClickException(f"Node '{nid}' not found")
    
    pyperclip.copy(node.body)
    display.print_success(f"Copied body of [{nid}] to clipboard")


@cli.command("paste")
def paste_cmd():
    """Paste clipboard to current node's body."""
    tree = get_current_tree()
    text = pyperclip.paste()
    tree.append_body(tree.current, text)
    save_current(tree)
    display.print_success("Pasted to body")


# === Status ===

@cli.command("done")
@click.argument("summary", required=False)
def done_cmd(summary):
    """Mark current node as done."""
    tree = get_current_tree()
    if summary:
        tree.append_body(tree.current, f"\n---\n**Summary:** {summary}")
    tree.set_status(tree.current, NodeStatus.DONE, auto_up=True)
    save_current(tree)
    display.print_success(f"Marked as done, moved to [{tree.current}]")


@cli.command("drop")
@click.argument("reason", required=False)
def drop_cmd(reason):
    """Mark current node as dropped."""
    tree = get_current_tree()
    if reason:
        tree.append_body(tree.current, f"\n---\n**Dropped:** {reason}")
    tree.set_status(tree.current, NodeStatus.DROPPED, auto_up=True)
    save_current(tree)
    display.print_success(f"Marked as dropped, moved to [{tree.current}]")


@cli.command("todo")
def todo_cmd():
    """Mark current node as todo."""
    tree = get_current_tree()
    tree.set_status(tree.current, NodeStatus.TODO, auto_up=False)
    save_current(tree)
    display.print_success("Marked as todo")


@cli.command("active")
def active_cmd():
    """Mark current node as active."""
    tree = get_current_tree()
    tree.set_status(tree.current, NodeStatus.ACTIVE, auto_up=False)
    save_current(tree)
    display.print_success("Marked as active")


# === Links ===

@cli.command("link")
@click.argument("target")
@click.argument("to_node", required=False)
def link_cmd(target, to_node):
    """Add a link to a node."""
    tree = get_current_tree()
    
    if to_node:
        # link <from> <to>
        from_id = target
        to_id = to_node
    else:
        # link <target> (from current)
        from_id = tree.current
        to_id = target
    
    if to_id not in tree.nodes:
        raise click.ClickException(f"Node '{to_id}' not found")
    
    tree.add_link(from_id, to_id)
    save_current(tree)
    display.print_success(f"Added link [{from_id}] → [{to_id}]")


@cli.command("unlink")
@click.argument("target")
def unlink_cmd(target):
    """Remove a link from current node."""
    tree = get_current_tree()
    tree.remove_link(tree.current, target)
    save_current(tree)
    display.print_success(f"Removed link to [{target}]")


@cli.command("links")
@click.argument("node_id", required=False)
def links_cmd(node_id):
    """List links from a node."""
    tree = get_current_tree()
    display.print_links(tree, node_id)


@cli.command("backlinks")
@click.argument("node_id", required=False)
def backlinks_cmd(node_id):
    """List nodes that link to this node."""
    tree = get_current_tree()
    display.print_backlinks(tree, node_id)


# === Structure operations ===

@cli.command("mv")
@click.argument("node_or_target")
@click.argument("target", required=False)
def mv_cmd(node_or_target, target):
    """Move a node to a new parent."""
    tree = get_current_tree()
    
    if target:
        node_id = node_or_target
        target_id = target
    else:
        node_id = tree.current
        target_id = node_or_target
    
    if target_id not in tree.nodes:
        raise click.ClickException(f"Target node '{target_id}' not found")
    
    try:
        tree.move_node(node_id, target_id)
        save_current(tree)
        display.print_success(f"Moved [{node_id}] under [{target_id}]")
    except ValueError as e:
        raise click.ClickException(str(e))


@cli.command("cpnode")
@click.argument("node_id")
@click.argument("target")
def cpnode_cmd(node_id, target):
    """Copy a node and its subtree."""
    tree = get_current_tree()
    
    if target not in tree.nodes:
        raise click.ClickException(f"Target node '{target}' not found")
    
    try:
        new_id = tree.copy_subtree(node_id, target)
        save_current(tree)
        display.print_success(f"Copied [{node_id}] to [{new_id}] under [{target}]")
    except ValueError as e:
        raise click.ClickException(str(e))


@cli.command("rmnode")
@click.argument("node_id", required=False)
@click.confirmation_option(prompt="Are you sure you want to delete this node and its children?")
def rmnode_cmd(node_id):
    """Delete a node and its subtree."""
    tree = get_current_tree()
    nid = node_id or tree.current
    
    try:
        tree.delete_node(nid)
        save_current(tree)
        display.print_success(f"Deleted [{nid}]")
    except ValueError as e:
        raise click.ClickException(str(e))


# === Search ===

@cli.command("grep")
@click.argument("pattern")
def grep_cmd(pattern):
    """Search for nodes matching pattern."""
    tree = get_current_tree()
    results = tree.search(pattern)
    display.print_node_list(tree, results, f"Search results for '{pattern}'")


@cli.command("find-status")
@click.argument("status", type=click.Choice(["active", "done", "dropped", "todo"]))
def find_status_cmd(status):
    """Find nodes by status."""
    tree = get_current_tree()
    results = tree.find_by_status(NodeStatus(status))
    display.print_node_list(tree, results, f"Nodes with status '{status}'")


@cli.command("find-leaf")
def find_leaf_cmd():
    """Find all leaf nodes."""
    tree = get_current_tree()
    results = tree.find_leaves()
    display.print_node_list(tree, results, "Leaf nodes")


@cli.command("find-orphan")
def find_orphan_cmd():
    """Find leaf nodes with no links."""
    tree = get_current_tree()
    results = tree.find_orphans()
    display.print_node_list(tree, results, "Orphan nodes")


# === Export/Import ===

@cli.command("export")
@click.argument("file", required=False, type=click.Path())
@click.option("--md", "as_markdown", is_flag=True, help="Export as Markdown")
def export_cmd(file, as_markdown):
    """Export tree to file."""
    tree = get_current_tree()
    
    path = Path(file) if file else None
    
    if as_markdown:
        result = export_tree_markdown(tree, path)
    else:
        result = export_tree(tree, path)
    
    if path:
        display.print_success(f"Exported to {path}")
    else:
        click.echo(result)


@cli.command("import")
@click.argument("file", type=click.Path(exists=True))
def import_cmd(file):
    """Import tree from file."""
    try:
        tree = import_tree(Path(file))
        set_current_tree_name(tree.name)
        display.print_success(f"Imported tree '{tree.name}'")
    except FileExistsError:
        raise click.ClickException("A tree with this name already exists")


# === Misc ===

@cli.command("stat")
def stat_cmd():
    """Show tree statistics."""
    tree = get_current_tree()
    display.print_statistics(tree)


@cli.command("log")
def log_cmd():
    """Show navigation history."""
    tree = get_current_tree()
    display.print_history(tree)


if __name__ == "__main__":
    cli()

