from pathlib import Path

from path_utils import resolve_inside


class ReadCommand:
    def __init__(self, work_dir: Path):
        self._work_dir = work_dir

    def execute(self, path: str) -> str:
        try:
            target = resolve_inside(self._work_dir, path)
            if not target.exists():
                return f"Read failed: file not found: {path}"
            if not target.is_file():
                return f"Read failed: not a file: {path}"
            contents = target.read_text(encoding="utf-8")
            return f"--- {path} ---\n{contents}\n--- end ---"
        except ValueError:
            return f"Read failed: path outside work directory: {path}"
        except Exception as e:
            return f"Read failed: {e}"
