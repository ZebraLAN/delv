"""CLI display formatting for Delv."""

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.text import Text
from rich.tree import Tree as RichTree

from .tree import ExplorationTree, Node, NodeStatus


console = Console()


def format_status_counts(tree: ExplorationTree) -> str:
    """Format status counts for display."""
    stats = tree.get_statistics()
    parts = []
    if stats["done"]:
        parts.append(f"{stats['done']} done")
    if stats["todo"]:
        parts.append(f"{stats['todo']} todo")
    if stats["active"]:
        parts.append(f"{stats['active']} active")
    if stats["dropped"]:
        parts.append(f"{stats['dropped']} dropped")
    return f"[{', '.join(parts)}]" if parts else ""


def format_node_label(node: Node, current_id: str, show_id: bool = True) -> Text:
    """Format a node label with status icon and optional current marker."""
    text = Text()
    
    if show_id and node.id != "root":
        text.append(f"[{node.id}] ", style="dim")
    
    # Status icon with color
    status_colors = {
        NodeStatus.ACTIVE: "green",
        NodeStatus.DONE: "blue",
        NodeStatus.DROPPED: "red",
        NodeStatus.TODO: "yellow",
    }
    text.append(f"{node.status.icon} ", style=status_colors[node.status])
    
    # Title
    text.append(node.title)
    
    # Current marker
    if node.id == current_id:
        text.append(" ← HERE", style="bold magenta")
    
    return text


def print_tree(tree: ExplorationTree, max_depth: int | None = None, 
               show_all: bool = False) -> None:
    """Print the tree structure."""
    # Header
    console.print()
    header = Text(tree.name, style="bold cyan")
    header.append("  ")
    header.append(format_status_counts(tree), style="dim")
    console.print(header)
    console.rule(style="dim")
    console.print()
    
    # Build tree display
    def add_children(rich_node, node_id: str, depth: int):
        node = tree.nodes[node_id]
        
        for child_id in node.children:
            child = tree.nodes[child_id]
            label = format_node_label(child, tree.current)
            child_rich = rich_node.add(label)
            
            if max_depth is None or depth < max_depth:
                add_children(child_rich, child_id, depth + 1)
    
    root = tree.nodes["root"]
    root_label = Text()
    root_label.append("root: ", style="dim")
    root_label.append(root.title, style="bold")
    if root.id == tree.current:
        root_label.append(" ← HERE", style="bold magenta")
    
    rich_tree = RichTree(root_label)
    add_children(rich_tree, "root", 1)
    
    console.print(rich_tree)
    console.print()
    
    # Current node details
    current = tree.get_current_node()
    console.rule(style="dim")
    
    # Node header
    node_header = Text()
    node_header.append(f"[{current.id}] ", style="dim")
    node_header.append(current.title, style="bold")
    node_header.append(f" ({current.status.value})", style="dim")
    console.print(node_header)
    console.rule(style="dim")
    
    # Body
    if current.body:
        console.print()
        console.print(Markdown(current.body))
        console.print()
    
    # Links section
    console.rule(style="dim")
    
    if current.links:
        links_text = Text("→ Links: ", style="dim")
        for i, link_id in enumerate(current.links):
            if i > 0:
                links_text.append(", ")
            link_node = tree.nodes.get(link_id)
            if link_node:
                links_text.append(f"[{link_id}] ", style="cyan")
                links_text.append(link_node.title)
        console.print(links_text)
    
    backlinks = tree.get_backlinks(current.id)
    if backlinks:
        bl_text = Text("← Backlinks: ", style="dim")
        for i, bl_id in enumerate(backlinks):
            if i > 0:
                bl_text.append(", ")
            bl_node = tree.nodes.get(bl_id)
            if bl_node:
                bl_text.append(f"[{bl_id}] ", style="cyan")
                bl_text.append(bl_node.title)
        console.print(bl_text)
    
    console.rule(style="dim")
    
    # Navigation hints
    nav = Text()
    if current.parent:
        nav.append(f"↑ parent: {current.parent}", style="dim")
    
    siblings = tree.get_siblings(current.id)
    if siblings:
        if nav:
            nav.append(" ")
        nav.append(f"↔ siblings: {', '.join(siblings)}", style="dim")
    
    if current.children:
        if nav:
            nav.append(" ")
        nav.append(f"↓ children: {', '.join(current.children)}", style="dim")
    else:
        if nav:
            nav.append(" ")
        nav.append("↓ children: (none)", style="dim")
    
    console.print(nav)
    console.print()


def print_path(tree: ExplorationTree) -> None:
    """Print the path from root to current node."""
    path = tree.get_path_to_root(tree.current)
    
    parts = []
    for node_id in path:
        node = tree.nodes[node_id]
        if node_id == "root":
            parts.append(f"root:{node.title}")
        else:
            parts.append(f"{node_id}:{node.title}")
    
    console.print(" → ".join(parts))


def print_node_body(tree: ExplorationTree, node_id: str | None = None) -> None:
    """Print just the body of a node."""
    nid = node_id or tree.current
    node = tree.nodes.get(nid)
    if not node:
        console.print(f"[red]Node {nid} not found[/red]")
        return
    
    if node.body:
        console.print(node.body)
    else:
        console.print("[dim](empty)[/dim]")


def print_node_list(tree: ExplorationTree, node_ids: list[str], 
                    title: str | None = None) -> None:
    """Print a list of nodes."""
    if title:
        console.print(f"\n[bold]{title}[/bold]")
        console.rule(style="dim")
    
    if not node_ids:
        console.print("[dim](none)[/dim]")
        return
    
    for nid in node_ids:
        node = tree.nodes.get(nid)
        if node:
            label = format_node_label(node, tree.current)
            console.print(label)


def print_links(tree: ExplorationTree, node_id: str | None = None) -> None:
    """Print links for a node."""
    nid = node_id or tree.current
    node = tree.nodes.get(nid)
    if not node:
        console.print(f"[red]Node {nid} not found[/red]")
        return
    
    print_node_list(tree, node.links, f"Links from [{nid}]")


def print_backlinks(tree: ExplorationTree, node_id: str | None = None) -> None:
    """Print backlinks for a node."""
    nid = node_id or tree.current
    backlinks = tree.get_backlinks(nid)
    print_node_list(tree, backlinks, f"Backlinks to [{nid}]")


def print_statistics(tree: ExplorationTree) -> None:
    """Print tree statistics."""
    stats = tree.get_statistics()
    
    console.print(f"\n[bold]{tree.name}[/bold] Statistics")
    console.rule(style="dim")
    console.print(f"Total nodes: {stats['total']}")
    console.print(f"  ► Active: {stats['active']}")
    console.print(f"  ✓ Done: {stats['done']}")
    console.print(f"  ✗ Dropped: {stats['dropped']}")
    console.print(f"  ? Todo: {stats['todo']}")
    console.print(f"Leaf nodes: {stats['leaves']}")
    console.print(f"Max depth: {stats['max_depth']}")
    console.print()


def print_history(tree: ExplorationTree) -> None:
    """Print navigation history."""
    console.print("\n[bold]Navigation History[/bold]")
    console.rule(style="dim")
    
    for i, nid in enumerate(tree.history):
        node = tree.nodes.get(nid)
        if node:
            marker = " ← current" if i == len(tree.history) - 1 else ""
            console.print(f"{i+1}. [{nid}] {node.title}{marker}")
    console.print()


def print_trees_list(trees: list[str], current: str | None = None) -> None:
    """Print list of available trees."""
    console.print("\n[bold]Available Trees[/bold]")
    console.rule(style="dim")
    
    if not trees:
        console.print("[dim](no trees)[/dim]")
        return
    
    for name in trees:
        if name == current:
            console.print(f"► {name}", style="green bold")
        else:
            console.print(f"  {name}")
    console.print()


def print_error(message: str) -> None:
    """Print an error message."""
    console.print(f"[red]Error:[/red] {message}")


def print_success(message: str) -> None:
    """Print a success message."""
    console.print(f"[green]✓[/green] {message}")


def print_info(message: str) -> None:
    """Print an info message."""
    console.print(f"[blue]ℹ[/blue] {message}")

