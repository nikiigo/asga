"""Runtime helpers for locating bundled resources in source and frozen builds."""

from __future__ import annotations

from pathlib import Path
import shutil
import sys


_BUNDLED_CONFIG_NAMES = (
    "sample_config.json",
    "sample_render_config.json",
    "config_1000_steps_all_strategies_20_fast.json",
    "config_1000_steps_all_strategies_20_render_static.json",
    "config_10000_steps_all_strategies_20_fast.json",
    "config_10000_steps_all_strategies_20_render_static.json",
)


def resource_root() -> Path:
    """Return the active resource root for source and frozen builds."""
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS"))
    return Path(__file__).resolve().parent.parent


def resource_path(*parts: str) -> Path:
    """Resolve a resource path under the active runtime root."""
    return resource_root().joinpath(*parts)


def bundled_sample_config_path() -> Path:
    """Return the default bundled simulation config path."""
    return resource_path("sample_config.json")


def copy_example_configs(destination_dir: str | Path) -> list[Path]:
    """Copy the bundled example configs into a user-selected directory."""
    destination = Path(destination_dir)
    destination.mkdir(parents=True, exist_ok=True)
    copied: list[Path] = []
    for name in _BUNDLED_CONFIG_NAMES:
        source = resource_path(name)
        target = destination / name
        shutil.copy2(source, target)
        copied.append(target)
    return copied
