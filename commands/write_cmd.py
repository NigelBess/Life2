from pathlib import Path
from response_parser import Hunk


class WriteCommand:
    def __init__(self, work_dir: Path):
        self._work_dir = work_dir

    def execute(self, path: str, hunks: list[Hunk]) -> str:
        try:
            target = (self._work_dir / path).resolve()
            if not str(target).startswith(str(self._work_dir.resolve())):
                return f"Write failed: path outside work directory: {path}"

            content = target.read_text(encoding="utf-8") if target.exists() else ""

            for i, hunk in enumerate(hunks):
                if hunk.old == "" and content == "":
                    content = hunk.new
                    continue
                if hunk.old not in content:
                    preview = hunk.old[:60].replace("\n", "\\n")
                    return f"Write failed: hunk {i+1} not found in {path}: {preview!r}"
                content = content.replace(hunk.old, hunk.new, 1)

            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
            return f"Write succeeded: {path} ({len(hunks)} hunk{'s' if len(hunks) != 1 else ''})"
        except Exception as e:
            return f"Write failed: {e}"
