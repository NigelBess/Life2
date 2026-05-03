from pathlib import Path

from path_utils import resolve_inside
from response_parser import Hunk


class WriteCommand:
    def __init__(self, work_dir: Path):
        self._work_dir = work_dir

    def execute(self, path: str, hunks: list[Hunk]) -> str:
        try:
            target = resolve_inside(self._work_dir, path)
            if target.exists() and not target.is_file():
                return f"Write failed: not a file: {path}"
            if not hunks:
                return f"Write failed: no hunks provided for {path}"

            content = target.read_text(encoding="utf-8") if target.exists() else ""

            for i, hunk in enumerate(hunks):
                if hunk.old == "":
                    if target.exists():
                        return f"Write failed: hunk {i+1} has empty old text for existing file: {path}"
                    content = hunk.new
                    continue
                if hunk.old not in content:
                    preview = hunk.old[:60].replace("\n", "\\n")
                    return f"Write failed: hunk {i+1} not found in {path}: {preview!r}"
                content = content.replace(hunk.old, hunk.new, 1)

            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
            return f"Write succeeded: {path} ({len(hunks)} hunk{'s' if len(hunks) != 1 else ''})"
        except ValueError:
            return f"Write failed: path outside work directory: {path}"
        except Exception as e:
            return f"Write failed: {e}"
