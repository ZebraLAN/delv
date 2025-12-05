"""Configuration management for Delv."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal


def get_delv_dir() -> Path:
    """Get the Delv data directory."""
    if env_dir := os.environ.get("DELV_DIR"):
        return Path(env_dir)
    return Path.home() / ".delv"


@dataclass
class Config:
    """Delv configuration."""
    
    editor: str = "nvim"
    default_mode: Literal["tui", "cli"] = "tui"
    theme: str = "delv-tokyo-night"
    
    @classmethod
    def load(cls) -> "Config":
        """Load configuration from file."""
        config_path = get_delv_dir() / "config.json"
        if config_path.exists():
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                return cls(
                    editor=data.get("editor", "vim"),
                    default_mode=data.get("defaultMode", "tui"),
                    theme=data.get("theme", "delv-tokyo-night"),
                )
            except (json.JSONDecodeError, IOError):
                pass
        return cls()
    
    def save(self) -> None:
        """Save configuration to file."""
        config_path = get_delv_dir() / "config.json"
        config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump({
                "editor": self.editor,
                "defaultMode": self.default_mode,
                "theme": self.theme,
            }, f, indent=2)


def ensure_delv_dir() -> Path:
    """Ensure the Delv directory structure exists."""
    delv_dir = get_delv_dir()
    delv_dir.mkdir(parents=True, exist_ok=True)
    (delv_dir / "trees").mkdir(exist_ok=True)
    return delv_dir


def get_current_tree_name() -> str | None:
    """Get the name of the currently open tree."""
    current_file = get_delv_dir() / "current"
    if current_file.exists():
        return current_file.read_text(encoding="utf-8").strip() or None
    return None


def set_current_tree_name(name: str | None) -> None:
    """Set the name of the currently open tree."""
    ensure_delv_dir()
    current_file = get_delv_dir() / "current"
    if name:
        current_file.write_text(name, encoding="utf-8")
    elif current_file.exists():
        current_file.unlink()


def get_editor() -> str:
    """Get the editor command to use."""
    if env_editor := os.environ.get("EDITOR"):
        return env_editor
    return Config.load().editor

