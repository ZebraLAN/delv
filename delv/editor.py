"""External editor integration for Delv."""

from __future__ import annotations

import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

import yaml

from .config import get_editor
from .tree import ExplorationTree, Node, NodeStatus


@dataclass
class NodeEdit:
    """Parsed result from node edit."""
    title: str
    status: NodeStatus
    links: list[str]
    body: str


def format_node_for_edit(node: Node) -> str:
    """Format a node for external editing with YAML frontmatter."""
    return f"""---
title: {node.title}
status: {node.status.value}
links: {node.links}
---

{node.body}"""


def parse_node_frontmatter(
    content: str,
    default_title: str,
    default_status: NodeStatus,
    default_links: list[str],
) -> NodeEdit:
    """Parse frontmatter from node edit content."""
    if not content.startswith("---"):
        return NodeEdit(default_title, default_status, default_links, content.strip())
    
    parts = content.split("---", 2)
    if len(parts) < 3:
        return NodeEdit(default_title, default_status, default_links, content.strip())
    
    try:
        fm = yaml.safe_load(parts[1]) or {}
    except yaml.YAMLError:
        # If YAML parsing fails, treat as body-only
        return NodeEdit(default_title, default_status, default_links, content.strip())
    
    # Parse status
    status = default_status
    if "status" in fm:
        try:
            status = NodeStatus(fm["status"])
        except ValueError:
            pass
    
    # Parse links
    links = fm.get("links", default_links)
    if links is None:
        links = []
    elif isinstance(links, str):
        # Handle comma-separated string format
        links = [l.strip() for l in links.split(",") if l.strip()]
    
    return NodeEdit(
        title=fm.get("title", default_title),
        status=status,
        links=links,
        body=parts[2].strip(),
    )


def edit_node_interactive(tree: ExplorationTree, node_id: str) -> bool:
    """
    Edit a node using external editor.
    
    Returns True if the node was modified, False otherwise.
    Raises ValueError if node not found.
    """
    node = tree.nodes.get(node_id)
    if not node:
        raise ValueError(f"Node '{node_id}' not found")
    
    content = format_node_for_edit(node)
    
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".md", delete=False, encoding="utf-8"
    ) as f:
        f.write(content)
        temp_path = Path(f.name)
    
    try:
        editor = get_editor()
        subprocess.run([editor, str(temp_path)], check=True)
        
        new_content = temp_path.read_text(encoding="utf-8")
        edit = parse_node_frontmatter(
            new_content, node.title, node.status, node.links
        )
        
        tree.update_node(
            node_id,
            title=edit.title,
            body=edit.body,
            status=edit.status,
            links=edit.links,
        )
        return True
    except subprocess.CalledProcessError:
        return False
    finally:
        temp_path.unlink()

