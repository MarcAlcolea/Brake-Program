"""Read/write nested dataclass attributes by dotted path, e.g. ``"mass.front_weight_fraction"``.

Shared by the sensitivity analysis and the GUI so parameters can be addressed uniformly.
"""

from __future__ import annotations


def get_by_path(obj: object, path: str) -> float:
    """Return the attribute at ``path`` as a float."""
    for part in path.split("."):
        obj = getattr(obj, part)
    return obj  # type: ignore[return-value]


def set_by_path(obj: object, path: str, value) -> None:
    """Set the attribute at ``path`` to ``value``."""
    parts = path.split(".")
    for part in parts[:-1]:
        obj = getattr(obj, part)
    setattr(obj, parts[-1], value)
