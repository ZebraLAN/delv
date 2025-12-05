"""Theme system for Delv TUI using Textual's built-in theme system."""

from __future__ import annotations

from textual.theme import Theme


THEME_NAMES = [
    "delv-tokyo-night",
    "delv-gruvbox",
    "delv-catppuccin",
    "delv-nord",
    "delv-solarized-light",
    "delv-dracula",
]

# Display names for UI
THEME_DISPLAY_NAMES = {
    "delv-tokyo-night": "Tokyo Night - 深邃东京夜色",
    "delv-gruvbox": "Gruvbox - 温暖复古色调",
    "delv-catppuccin": "Catppuccin - 柔和糖果色",
    "delv-nord": "Nord - 北极冰蓝",
    "delv-solarized-light": "Solarized Light - 经典浅色",
    "delv-dracula": "Dracula - 吸血鬼紫",
}


# === Theme Definitions using Textual's Theme class ===

THEMES: list[Theme] = [
    # Tokyo Night - 深邃的东京夜色，蓝紫色调
    Theme(
        name="delv-tokyo-night",
        primary="#7aa2f7",
        secondary="#a9b1d6",
        accent="#7dcfff",
        warning="#e0af68",
        error="#f7768e",
        success="#9ece6a",
        foreground="#c0caf5",
        background="#1a1b26",
        surface="#24283b",
        panel="#414868",
        dark=True,
    ),
    # Gruvbox - 温暖的复古色调
    Theme(
        name="delv-gruvbox",
        primary="#fe8019",
        secondary="#d5c4a1",
        accent="#83a598",
        warning="#fabd2f",
        error="#fb4934",
        success="#b8bb26",
        foreground="#ebdbb2",
        background="#1d2021",
        surface="#282828",
        panel="#3c3836",
        dark=True,
        variables={
            "block-cursor-foreground": "#ebdbb2",
        },
    ),
    # Catppuccin Mocha - 柔和的糖果色
    Theme(
        name="delv-catppuccin",
        primary="#f5c2e7",
        secondary="#bac2de",
        accent="#94e2d5",
        warning="#f9e2af",
        error="#f38ba8",
        success="#a6e3a1",
        foreground="#cdd6f4",
        background="#11111b",
        surface="#1e1e2e",
        panel="#313244",
        dark=True,
    ),
    # Nord - 北极冰蓝
    Theme(
        name="delv-nord",
        primary="#88c0d0",
        secondary="#d8dee9",
        accent="#81a1c1",
        warning="#ebcb8b",
        error="#bf616a",
        success="#a3be8c",
        foreground="#eceff4",
        background="#242933",
        surface="#2e3440",
        panel="#3b4252",
        dark=True,
    ),
    # Solarized Light - 经典浅色主题
    Theme(
        name="delv-solarized-light",
        primary="#268bd2",
        secondary="#586e75",
        accent="#2aa198",
        warning="#b58900",
        error="#dc322f",
        success="#859900",
        foreground="#073642",
        background="#fdf6e3",
        surface="#eee8d5",
        panel="#eee8d5",
        dark=False,
    ),
    # Dracula - 吸血鬼紫
    Theme(
        name="delv-dracula",
        primary="#bd93f9",
        secondary="#f8f8f2",
        accent="#8be9fd",
        warning="#ffb86c",
        error="#ff5555",
        success="#50fa7b",
        foreground="#f8f8f2",
        background="#1e1f29",
        surface="#282a36",
        panel="#44475a",
        dark=True,
        variables={
            "block-cursor-foreground": "#f8f8f2",
        },
    ),
]


def get_themes() -> list[Theme]:
    """Get all Delv themes."""
    return THEMES
