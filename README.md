# Delv - 探索树 TUI 工具

A tree-based exploration tracking tool for DFS-style research. Record exploration paths, intermediate discoveries, and dead ends with a navigable tree structure and Ranger-style three-column TUI interface.

## Installation

```bash
pip install -e .
```

## Quick Start

```bash
# Create a new exploration tree
delv new render "理解渲染系统"

# Add child nodes
delv add "Draw_0 入口"
delv append "看起来是主循环"

# Add more nodes
delv add "batch_sprites"
delv edit  # Opens external editor

# Mark as done and return to parent
delv done "确认是按 texture 分组"

# Show tree
delv show

# Open TUI
delv tui
```

## TUI Interface

```
┌─ Trees ─────────┬─ Nodes ──────────────────────┬─ Content ─────────────────────┐
│                 │                              │                               │
│   render-study  │ root: 理解渲染系统           │ ## batch_sprites 函数         │
│ > input-system  │ ├── ✓ n1 Draw_0 入口         │                               │
│   save-format   │ │   ├── ► n3 batch_sprites ← │ 发现 object 1847 被特殊处理   │
│                 │ │   └── ? n4 排序逻辑        │                               │
│                 │ └── ✗ n2 shader 猜想         │ ```gml                        │
│                 │                              │ if (obj_index == 1847)        │
│                 │                              │ ```                           │
│                 │                              │                               │
│                 │                              │ ─────────────────────────────│
│                 │                              │ → Links: [n4] 排序逻辑        │
│                 │                              │ ← Backlinks: [n1] Draw_0      │
│                 │                              │                               │
├─────────────────┴──────────────────────────────┴───────────────────────────────┤
│ j/k:移动 h/l:面板 enter:进入 a:添加 e:编辑 d:done x:drop /:搜索 ?:帮助 q:退出  │
└────────────────────────────────────────────────────────────────────────────────┘
```

### Status Icons
- `►` active
- `✓` done
- `✗` dropped
- `?` todo

### Key Bindings

| Key | Action |
|-----|--------|
| `h` `l` | Switch panel focus |
| `j` `k` | Move up/down |
| `Enter` | Enter node / Open tree |
| `Backspace` | Go to parent |
| `-` | Go back in history |
| `a` | Add child node |
| `A` | Add sibling node |
| `e` | Edit node (external editor) |
| `E` | Quick edit title |
| `i` | Quick append to body |
| `d` | Mark done (auto-return) |
| `x` | Mark dropped (auto-return) |
| `t` | Mark todo |
| `L` | Add link |
| `U` | Remove link |
| `B` | Show backlinks |
| `m` | Move node |
| `y` | Yank body to clipboard |
| `p` | Paste to body |
| `/` | Search |
| `g` | Goto node by ID |
| `r` | Jump to root |
| `]` `[` | Jump to next/prev link |
| `n` | New tree |
| `R` | Rename tree |
| `D` | Delete tree |
| `s` | Statistics |
| `?` | Help |
| `q` | Quit |

## CLI Commands

### Mode
```bash
delv                       # Enter TUI or show tree (based on config)
delv tui                   # Force TUI
delv show                  # Force CLI display
```

### Tree Management
```bash
delv new <name> [title]    # Create new tree
delv ls                    # List all trees
delv open <name>           # Switch to tree
delv rm <name>             # Delete tree
delv rename <old> <new>    # Rename tree
delv cp <src> <dst>        # Copy tree
```

### Display
```bash
delv show                  # Show current tree
delv show -a, --all        # Expand all nodes
delv show -d, --depth <n>  # Limit display depth
delv path                  # Show root → current path
delv cat [node-id]         # Output node body
```

### Navigation
```bash
delv go <node-id>          # Jump to node
delv up                    # Parent node
delv down [n]              # Nth child node
delv next                  # Next sibling
delv prev                  # Previous sibling
delv root                  # Go to root
delv back                  # History back
```

### Editing
```bash
delv add [title]           # Add child node
delv add -s [title]        # Add as sibling
delv edit [node-id]        # Edit node
delv title <text>          # Change title
delv append <text>         # Append to body
delv yank [node-id]        # Copy to clipboard
delv paste                 # Paste to body
```

### Status
```bash
delv done [summary]        # Mark done, auto up
delv drop [reason]         # Mark dropped, auto up
delv todo                  # Mark todo
delv active                # Mark active
```

### Links
```bash
delv link <target>         # Add link from current
delv link <from> <to>      # Add link between nodes
delv unlink <target>       # Remove link
delv links [node]          # List links
delv backlinks [node]      # List backlinks
```

### Structure
```bash
delv mv <target>           # Move current node
delv mv <node> <target>    # Move specified node
delv cpnode <node> <target> # Copy subtree
delv rmnode [node]         # Delete subtree
```

### Search
```bash
delv grep <pattern>        # Search title and body
delv find-status <status>  # Find by status
delv find-leaf             # Find leaf nodes
delv find-orphan           # Find unlinked leaves
```

### Export/Import
```bash
delv export [file]         # Export JSON
delv export --md [file]    # Export Markdown
delv import <file>         # Import tree
```

### Misc
```bash
delv stat                  # Statistics
delv log                   # Navigation history
```

## Configuration

Configuration file: `~/.delv/config.json`

```json
{
  "editor": "vim",
  "defaultMode": "tui"
}
```

- `editor`: External editor for editing nodes
- `defaultMode`: `"tui"` or `"cli"` - behavior when running `delv` without arguments

Environment variable `DELV_DIR` can override the data directory (default: `~/.delv/`).

## Data Format

Trees are stored as JSON files in `~/.delv/trees/`:

```json
{
  "name": "my-exploration",
  "created": "2024-01-15T10:00:00Z",
  "updated": "2024-01-15T14:30:00Z",
  "current": "n3",
  "nextId": 5,
  "history": ["root", "n1", "n3"],
  "nodes": {
    "root": {
      "id": "root",
      "title": "根问题描述",
      "status": "active",
      "children": ["n1", "n2"],
      "body": "",
      "links": []
    },
    "n1": {
      "id": "n1",
      "parent": "root",
      "title": "子问题 1",
      "status": "done",
      "children": ["n3", "n4"],
      "body": "任意 markdown 内容",
      "links": ["n2"]
    }
  }
}
```

## License

MIT

