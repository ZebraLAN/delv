"""Tree data structure and operations for Delv."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Iterator


class NodeStatus(str, Enum):
    """Status of a node."""
    ACTIVE = "active"
    DONE = "done"
    DROPPED = "dropped"
    TODO = "todo"
    
    @property
    def icon(self) -> str:
        """Get the icon for this status."""
        return {
            NodeStatus.ACTIVE: "►",
            NodeStatus.DONE: "✓",
            NodeStatus.DROPPED: "✗",
            NodeStatus.TODO: "?",
        }[self]


@dataclass
class Node:
    """A node in the exploration tree."""
    
    id: str
    title: str
    status: NodeStatus = NodeStatus.ACTIVE
    parent: str | None = None
    children: list[str] = field(default_factory=list)
    body: str = ""
    links: list[str] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        """Convert node to dictionary."""
        data = {
            "id": self.id,
            "title": self.title,
            "status": self.status.value,
            "children": self.children,
            "body": self.body,
            "links": self.links,
        }
        if self.parent:
            data["parent"] = self.parent
        return data
    
    @classmethod
    def from_dict(cls, data: dict) -> "Node":
        """Create node from dictionary."""
        return cls(
            id=data["id"],
            title=data["title"],
            status=NodeStatus(data.get("status", "active")),
            parent=data.get("parent"),
            children=data.get("children", []),
            body=data.get("body", ""),
            links=data.get("links", []),
        )


@dataclass
class ExplorationTree:
    """An exploration tree."""
    
    name: str
    created: datetime
    updated: datetime
    current: str = "root"
    next_id: int = 1
    history: list[str] = field(default_factory=list)
    nodes: dict[str, Node] = field(default_factory=dict)
    
    def __post_init__(self):
        """Ensure root node exists."""
        if "root" not in self.nodes:
            self.nodes["root"] = Node(id="root", title="Root")
            self.history = ["root"]
    
    def to_dict(self) -> dict:
        """Convert tree to dictionary."""
        return {
            "name": self.name,
            "created": self.created.isoformat(),
            "updated": self.updated.isoformat(),
            "current": self.current,
            "nextId": self.next_id,
            "history": self.history,
            "nodes": {k: v.to_dict() for k, v in self.nodes.items()},
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "ExplorationTree":
        """Create tree from dictionary."""
        nodes = {k: Node.from_dict(v) for k, v in data.get("nodes", {}).items()}
        tree = cls(
            name=data["name"],
            created=datetime.fromisoformat(data["created"]),
            updated=datetime.fromisoformat(data["updated"]),
            current=data.get("current", "root"),
            next_id=data.get("nextId", 1),
            history=data.get("history", ["root"]),
            nodes=nodes,
        )
        return tree
    
    @classmethod
    def create(cls, name: str, title: str = "Root") -> "ExplorationTree":
        """Create a new exploration tree."""
        now = datetime.now()
        tree = cls(
            name=name,
            created=now,
            updated=now,
            current="root",
            next_id=1,
            history=["root"],
            nodes={},
        )
        tree.nodes["root"] = Node(id="root", title=title)
        return tree
    
    def touch(self) -> None:
        """Update the modified timestamp."""
        self.updated = datetime.now()
    
    def get_node(self, node_id: str) -> Node | None:
        """Get a node by ID."""
        return self.nodes.get(node_id)
    
    def get_current_node(self) -> Node:
        """Get the current node."""
        return self.nodes[self.current]
    
    def generate_id(self) -> str:
        """Generate a new node ID."""
        node_id = f"n{self.next_id}"
        self.next_id += 1
        return node_id
    
    def add_child(self, parent_id: str, title: str, enter: bool = True) -> Node:
        """Add a child node to the specified parent."""
        parent = self.nodes.get(parent_id)
        if not parent:
            raise ValueError(f"Parent node {parent_id} not found")
        
        node_id = self.generate_id()
        node = Node(id=node_id, title=title, parent=parent_id)
        self.nodes[node_id] = node
        parent.children.append(node_id)
        
        if enter:
            self.go_to(node_id)
        
        self.touch()
        return node
    
    def add_sibling(self, sibling_id: str, title: str, enter: bool = True) -> Node:
        """Add a sibling node after the specified node."""
        sibling = self.nodes.get(sibling_id)
        if not sibling or not sibling.parent:
            raise ValueError(f"Cannot add sibling to {sibling_id}")
        
        parent = self.nodes[sibling.parent]
        node_id = self.generate_id()
        node = Node(id=node_id, title=title, parent=sibling.parent)
        self.nodes[node_id] = node
        
        # Insert after sibling
        idx = parent.children.index(sibling_id)
        parent.children.insert(idx + 1, node_id)
        
        if enter:
            self.go_to(node_id)
        
        self.touch()
        return node
    
    def go_to(self, node_id: str) -> None:
        """Navigate to a node."""
        if node_id not in self.nodes:
            raise ValueError(f"Node {node_id} not found")
        
        if self.current != node_id:
            self.history.append(node_id)
            self.current = node_id
            self.touch()
    
    def go_up(self) -> bool:
        """Navigate to parent node. Returns True if moved."""
        node = self.get_current_node()
        if node.parent:
            self.go_to(node.parent)
            return True
        return False
    
    def go_down(self, index: int = 0) -> bool:
        """Navigate to a child node. Returns True if moved."""
        node = self.get_current_node()
        if node.children and 0 <= index < len(node.children):
            self.go_to(node.children[index])
            return True
        return False
    
    def go_next_sibling(self) -> bool:
        """Navigate to next sibling. Returns True if moved."""
        node = self.get_current_node()
        if not node.parent:
            return False
        
        parent = self.nodes[node.parent]
        idx = parent.children.index(node.id)
        if idx + 1 < len(parent.children):
            self.go_to(parent.children[idx + 1])
            return True
        return False
    
    def go_prev_sibling(self) -> bool:
        """Navigate to previous sibling. Returns True if moved."""
        node = self.get_current_node()
        if not node.parent:
            return False
        
        parent = self.nodes[node.parent]
        idx = parent.children.index(node.id)
        if idx > 0:
            self.go_to(parent.children[idx - 1])
            return True
        return False
    
    def go_root(self) -> None:
        """Navigate to root node."""
        self.go_to("root")
    
    def go_back(self) -> bool:
        """Go back in history. Returns True if moved."""
        if len(self.history) > 1:
            self.history.pop()
            self.current = self.history[-1]
            self.touch()
            return True
        return False
    
    def set_status(self, node_id: str, status: NodeStatus, auto_up: bool = True) -> None:
        """Set the status of a node."""
        node = self.nodes.get(node_id)
        if not node:
            raise ValueError(f"Node {node_id} not found")
        
        node.status = status
        
        if auto_up and status in (NodeStatus.DONE, NodeStatus.DROPPED):
            self.go_up()
        
        self.touch()
    
    def update_node(self, node_id: str, title: str | None = None, 
                    body: str | None = None, status: NodeStatus | None = None,
                    links: list[str] | None = None) -> None:
        """Update a node's properties."""
        node = self.nodes.get(node_id)
        if not node:
            raise ValueError(f"Node {node_id} not found")
        
        if title is not None:
            node.title = title
        if body is not None:
            node.body = body
        if status is not None:
            node.status = status
        if links is not None:
            node.links = links
        
        self.touch()
    
    def append_body(self, node_id: str, text: str) -> None:
        """Append text to a node's body."""
        node = self.nodes.get(node_id)
        if not node:
            raise ValueError(f"Node {node_id} not found")
        
        if node.body:
            node.body += "\n\n" + text
        else:
            node.body = text
        
        self.touch()
    
    def add_link(self, from_id: str, to_id: str) -> None:
        """Add a link from one node to another."""
        from_node = self.nodes.get(from_id)
        to_node = self.nodes.get(to_id)
        
        if not from_node:
            raise ValueError(f"Node {from_id} not found")
        if not to_node:
            raise ValueError(f"Node {to_id} not found")
        
        if to_id not in from_node.links:
            from_node.links.append(to_id)
            self.touch()
    
    def remove_link(self, from_id: str, to_id: str) -> None:
        """Remove a link from one node to another."""
        from_node = self.nodes.get(from_id)
        if not from_node:
            raise ValueError(f"Node {from_id} not found")
        
        if to_id in from_node.links:
            from_node.links.remove(to_id)
            self.touch()
    
    def get_backlinks(self, node_id: str) -> list[str]:
        """Get all nodes that link to the specified node."""
        backlinks = []
        for nid, node in self.nodes.items():
            if node_id in node.links:
                backlinks.append(nid)
        return backlinks
    
    def move_node(self, node_id: str, new_parent_id: str) -> None:
        """Move a node to a new parent."""
        if node_id == "root":
            raise ValueError("Cannot move root node")
        
        node = self.nodes.get(node_id)
        new_parent = self.nodes.get(new_parent_id)
        
        if not node:
            raise ValueError(f"Node {node_id} not found")
        if not new_parent:
            raise ValueError(f"Node {new_parent_id} not found")
        
        # Check for circular reference
        if self._is_ancestor(node_id, new_parent_id):
            raise ValueError("Cannot move node under its own descendant")
        
        # Remove from old parent
        if node.parent:
            old_parent = self.nodes[node.parent]
            old_parent.children.remove(node_id)
        
        # Add to new parent
        node.parent = new_parent_id
        new_parent.children.append(node_id)
        
        self.touch()
    
    def _is_ancestor(self, ancestor_id: str, descendant_id: str) -> bool:
        """Check if ancestor_id is an ancestor of descendant_id."""
        node = self.nodes.get(descendant_id)
        while node and node.parent:
            if node.parent == ancestor_id:
                return True
            node = self.nodes.get(node.parent)
        return False
    
    def delete_node(self, node_id: str) -> None:
        """Delete a node and all its descendants."""
        if node_id == "root":
            raise ValueError("Cannot delete root node")
        
        node = self.nodes.get(node_id)
        if not node:
            raise ValueError(f"Node {node_id} not found")
        
        # Collect all descendants
        to_delete = []
        self._collect_descendants(node_id, to_delete)
        
        # Remove from parent
        if node.parent:
            parent = self.nodes[node.parent]
            parent.children.remove(node_id)
        
        # Remove all links to deleted nodes
        for nid in to_delete:
            for other in self.nodes.values():
                if nid in other.links:
                    other.links.remove(nid)
        
        # Delete nodes
        for nid in to_delete:
            del self.nodes[nid]
        
        # Update current if deleted
        if self.current in to_delete:
            self.current = node.parent or "root"
            self.history = [h for h in self.history if h not in to_delete]
            if not self.history:
                self.history = ["root"]
        
        self.touch()
    
    def _collect_descendants(self, node_id: str, result: list[str]) -> None:
        """Collect a node and all its descendants."""
        result.append(node_id)
        node = self.nodes.get(node_id)
        if node:
            for child_id in node.children:
                self._collect_descendants(child_id, result)
    
    def copy_subtree(self, node_id: str, new_parent_id: str) -> str:
        """Copy a node and its subtree to a new parent. Returns new root ID."""
        node = self.nodes.get(node_id)
        new_parent = self.nodes.get(new_parent_id)
        
        if not node:
            raise ValueError(f"Node {node_id} not found")
        if not new_parent:
            raise ValueError(f"Node {new_parent_id} not found")
        
        return self._copy_node_recursive(node_id, new_parent_id)
    
    def _copy_node_recursive(self, node_id: str, parent_id: str) -> str:
        """Recursively copy a node and its children."""
        node = self.nodes[node_id]
        new_id = self.generate_id()
        
        new_node = Node(
            id=new_id,
            title=node.title,
            status=node.status,
            parent=parent_id,
            children=[],
            body=node.body,
            links=list(node.links),
        )
        
        self.nodes[new_id] = new_node
        self.nodes[parent_id].children.append(new_id)
        
        for child_id in node.children:
            self._copy_node_recursive(child_id, new_id)
        
        self.touch()
        return new_id
    
    def search(self, pattern: str) -> list[str]:
        """Search for nodes matching the pattern in title or body."""
        pattern_lower = pattern.lower()
        results = []
        for nid, node in self.nodes.items():
            if pattern_lower in node.title.lower() or pattern_lower in node.body.lower():
                results.append(nid)
        return results
    
    def find_by_status(self, status: NodeStatus) -> list[str]:
        """Find all nodes with the given status."""
        return [nid for nid, node in self.nodes.items() if node.status == status]
    
    def find_leaves(self) -> list[str]:
        """Find all leaf nodes (nodes with no children)."""
        return [nid for nid, node in self.nodes.items() if not node.children]
    
    def find_orphans(self) -> list[str]:
        """Find leaf nodes with no links."""
        orphans = []
        for nid, node in self.nodes.items():
            if not node.children and not node.links and not self.get_backlinks(nid):
                orphans.append(nid)
        return orphans
    
    def get_path_to_root(self, node_id: str) -> list[str]:
        """Get the path from root to the specified node."""
        path = []
        current = node_id
        while current:
            path.append(current)
            node = self.nodes.get(current)
            current = node.parent if node else None
        return list(reversed(path))
    
    def get_siblings(self, node_id: str) -> list[str]:
        """Get sibling node IDs."""
        node = self.nodes.get(node_id)
        if not node or not node.parent:
            return []
        parent = self.nodes[node.parent]
        return [s for s in parent.children if s != node_id]
    
    def get_statistics(self) -> dict:
        """Get statistics about the tree."""
        stats = {
            "total": len(self.nodes),
            "active": 0,
            "done": 0,
            "dropped": 0,
            "todo": 0,
            "leaves": 0,
            "max_depth": 0,
        }
        
        for node in self.nodes.values():
            stats[node.status.value] += 1
            if not node.children:
                stats["leaves"] += 1
        
        # Calculate max depth
        for nid in self.nodes:
            depth = len(self.get_path_to_root(nid))
            stats["max_depth"] = max(stats["max_depth"], depth)
        
        return stats
    
    def iter_tree(self, start: str = "root") -> Iterator[tuple[str, int]]:
        """Iterate through the tree in DFS order, yielding (node_id, depth)."""
        def _iter(node_id: str, depth: int):
            yield node_id, depth
            node = self.nodes.get(node_id)
            if node:
                for child_id in node.children:
                    yield from _iter(child_id, depth + 1)
        
        yield from _iter(start, 0)

