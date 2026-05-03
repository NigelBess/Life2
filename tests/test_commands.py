import shutil
import unittest
from contextlib import contextmanager
from pathlib import Path
from uuid import uuid4

from clone_manager import CloneManager
from commands.read_cmd import ReadCommand
from commands.write_cmd import WriteCommand
from response_parser import Hunk


TEMP_ROOT = Path(__file__).resolve().parents[1] / ".test_tmp"


@contextmanager
def temporary_workspace():
    TEMP_ROOT.mkdir(exist_ok=True)
    path = TEMP_ROOT / f"test_{uuid4().hex}"
    path.mkdir()
    try:
        yield str(path)
    finally:
        shutil.rmtree(path, ignore_errors=True)


class CommandSafetyTests(unittest.TestCase):
    def test_read_rejects_sibling_prefix_escape(self) -> None:
        with temporary_workspace() as tmp:
            base = Path(tmp)
            work_dir = base / "Life2"
            sibling = base / "Life2_evil"
            work_dir.mkdir()
            sibling.mkdir()
            (sibling / "secret.txt").write_text("nope", encoding="utf-8")

            result = ReadCommand(work_dir).execute("../Life2_evil/secret.txt")

        self.assertIn("path outside work directory", result)
        self.assertNotIn("nope", result)

    def test_write_rejects_empty_hunk_for_existing_file(self) -> None:
        with temporary_workspace() as tmp:
            work_dir = Path(tmp)
            target = work_dir / "note.txt"
            target.write_text("original", encoding="utf-8")

            result = WriteCommand(work_dir).execute("note.txt", [Hunk(old="", new="prefix")])

            self.assertIn("empty old text for existing file", result)
            self.assertEqual("original", target.read_text(encoding="utf-8"))

    def test_write_creates_new_file_with_empty_old_hunk(self) -> None:
        with temporary_workspace() as tmp:
            work_dir = Path(tmp)
            result = WriteCommand(work_dir).execute("new/file.txt", [Hunk(old="", new="hello")])

            self.assertIn("Write succeeded", result)
            self.assertEqual("hello", (work_dir / "new" / "file.txt").read_text(encoding="utf-8"))

    def test_clone_ignores_runtime_artifacts(self) -> None:
        with temporary_workspace() as tmp:
            launch_dir = Path(tmp) / "Life2"
            launch_dir.mkdir()
            (launch_dir / "main.py").write_text("print('ok')", encoding="utf-8")
            (launch_dir / ".env").write_text("SECRET=1", encoding="utf-8")
            (launch_dir / "context.json").write_text("{}", encoding="utf-8")
            (launch_dir / "__pycache__").mkdir()
            (launch_dir / "__pycache__" / "main.pyc").write_bytes(b"compiled")

            work_dir = CloneManager(launch_dir).create_work_dir(2)

            self.assertTrue((work_dir / "main.py").exists())
            self.assertFalse((work_dir / ".env").exists())
            self.assertFalse((work_dir / "context.json").exists())
            self.assertFalse((work_dir / "__pycache__").exists())


if __name__ == "__main__":
    unittest.main()
