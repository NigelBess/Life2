from pathlib import Path


class ReadCommand:
    def __init__(self, work_dir: Path):
        self._work_dir = work_dir

    def execute(self, path: str) -> str:
        try:
            target = (self._work_dir / path).resolve()
            if not str(target).startswith(str(self._work_dir.resolve())):
                return f"Read failed: path outside work directory: {path}"
            if not target.exists():
                return f"Read failed: file not found: {path}"
            contents = target.read_text(encoding="utf-8")
            return f"--- {path} ---\n{contents}\n--- end ---"
        except Exception as e:
            return f"Read failed: {e}"
