import shutil
import sys
import subprocess
from pathlib import Path
from uuid import uuid4

from context import AgentContext


class CloneManager:
    def __init__(self, launch_dir: Path):
        self.launch_dir = launch_dir

    def create_work_dir(self, generation: int) -> Path:
        base = self.launch_dir.parent
        name = f"{self.launch_dir.name}_gen{generation}_{uuid4().hex[:8]}"
        work_dir = base / name
        shutil.copytree(self.launch_dir, work_dir)
        return work_dir

    def evolve(self, context: AgentContext, work_dir: Path) -> None:
        context.parent_to_delete = str(self.launch_dir)
        context.generation += 1
        context.work_dir = str(work_dir)

        context_path = work_dir / "context.json"
        context.save(context_path)

        cmd = [sys.executable, str(work_dir / "main.py"), "--context", str(context_path)]
        if context.ui_port:
            cmd += ["--ui-port", str(context.ui_port)]

        flags = 0
        if sys.platform == "win32" and context.ui_port:
            flags = subprocess.CREATE_NO_WINDOW

        subprocess.Popen(cmd, creationflags=flags)
        sys.exit(0)
