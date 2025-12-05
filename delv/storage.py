"""File storage operations for Delv."""

import json
import shutil
from pathlib import Path

from .config import ensure_delv_dir, get_delv_dir
from .tree import ExplorationTree


def get_trees_dir() -> Path:
    """Get the trees directory."""
    return get_delv_dir() / "trees"


def list_trees() -> list[str]:
    """List all available trees."""
    trees_dir = get_trees_dir()
    if not trees_dir.exists():
        return []
    return sorted([f.stem for f in trees_dir.glob("*.json")])


def tree_exists(name: str) -> bool:
    """Check if a tree exists."""
    return (get_trees_dir() / f"{name}.json").exists()


def get_tree_path(name: str) -> Path:
    """Get the path to a tree file."""
    return get_trees_dir() / f"{name}.json"


def load_tree(name: str) -> ExplorationTree:
    """Load a tree from disk."""
    path = get_tree_path(name)
    if not path.exists():
        raise FileNotFoundError(f"Tree '{name}' not found")
    
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    return ExplorationTree.from_dict(data)


def save_tree(tree: ExplorationTree, backup: bool = True) -> None:
    """Save a tree to disk."""
    ensure_delv_dir()
    path = get_tree_path(tree.name)
    
    # Create backup if file exists
    if backup and path.exists():
        backup_path = path.with_suffix(".json.bak")
        shutil.copy2(path, backup_path)
    
    # Write atomically via temp file
    temp_path = path.with_suffix(".json.tmp")
    with open(temp_path, "w", encoding="utf-8") as f:
        json.dump(tree.to_dict(), f, indent=2, ensure_ascii=False)
    
    temp_path.replace(path)


def delete_tree(name: str) -> None:
    """Delete a tree."""
    path = get_tree_path(name)
    if path.exists():
        path.unlink()
    
    backup_path = path.with_suffix(".json.bak")
    if backup_path.exists():
        backup_path.unlink()


def rename_tree(old_name: str, new_name: str) -> None:
    """Rename a tree."""
    old_path = get_tree_path(old_name)
    new_path = get_tree_path(new_name)
    
    if not old_path.exists():
        raise FileNotFoundError(f"Tree '{old_name}' not found")
    if new_path.exists():
        raise FileExistsError(f"Tree '{new_name}' already exists")
    
    # Load, update name, save with new name
    tree = load_tree(old_name)
    tree.name = new_name
    save_tree(tree, backup=False)
    
    # Delete old file
    old_path.unlink()
    old_backup = old_path.with_suffix(".json.bak")
    if old_backup.exists():
        old_backup.unlink()


def copy_tree(src_name: str, dst_name: str) -> None:
    """Copy a tree to a new name."""
    src_path = get_tree_path(src_name)
    dst_path = get_tree_path(dst_name)
    
    if not src_path.exists():
        raise FileNotFoundError(f"Tree '{src_name}' not found")
    if dst_path.exists():
        raise FileExistsError(f"Tree '{dst_name}' already exists")
    
    # Load, update name, save with new name
    tree = load_tree(src_name)
    tree.name = dst_name
    save_tree(tree, backup=False)


def export_tree(tree: ExplorationTree, path: Path | None = None) -> str:
    """Export tree to JSON string or file."""
    data = json.dumps(tree.to_dict(), indent=2, ensure_ascii=False)
    if path:
        path.write_text(data, encoding="utf-8")
    return data


def export_tree_markdown(tree: ExplorationTree, path: Path | None = None) -> str:
    """Export tree to Markdown format."""
    lines = [f"# {tree.name}", ""]
    
    def _export_node(node_id: str, depth: int = 0):
        node = tree.nodes[node_id]
        indent = "  " * depth
        prefix = "- " if depth > 0 else ""
        status_icon = node.status.icon
        
        lines.append(f"{indent}{prefix}**[{node.id}]** {status_icon} {node.title}")
        
        if node.body:
            lines.append("")
            for line in node.body.split("\n"):
                lines.append(f"{indent}  {line}")
            lines.append("")
        
        if node.links:
            link_strs = [f"[{lid}]" for lid in node.links]
            lines.append(f"{indent}  → Links: {', '.join(link_strs)}")
            lines.append("")
        
        for child_id in node.children:
            _export_node(child_id, depth + 1)
    
    _export_node("root")
    
    result = "\n".join(lines)
    if path:
        path.write_text(result, encoding="utf-8")
    return result


def import_tree(path: Path) -> ExplorationTree:
    """Import tree from JSON file."""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    tree = ExplorationTree.from_dict(data)
    
    # Check if tree with this name exists
    if tree_exists(tree.name):
        raise FileExistsError(f"Tree '{tree.name}' already exists")
    
    save_tree(tree, backup=False)
    return tree

