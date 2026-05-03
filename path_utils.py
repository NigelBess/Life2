from pathlib import Path


def resolve_inside(root: Path, relative_path: str) -> Path:
    """Resolve a user-provided path and ensure it stays inside root."""
    root = root.resolve()
    target = (root / relative_path).resolve()
    target.relative_to(root)
    return target
