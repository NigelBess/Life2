from pathlib import Path

from context import AgentContext
from response_parser import Command
from .read_cmd import ReadCommand
from .write_cmd import WriteCommand
from .evolve_cmd import EvolveCommand


class CommandExecutor:
    def __init__(self, work_dir: Path, context: AgentContext):
        self._work_dir = work_dir
        self._context = context
        self._read = ReadCommand(work_dir)
        self._write = WriteCommand(work_dir)
        self._evolve = EvolveCommand()

    def execute(self, commands: list[Command]) -> tuple[list[str], bool]:
        if not commands:
            return [], False

        has_evolve = any(c.type == "evolve" for c in commands)
        if has_evolve and len(commands) > 1:
            return [
                "Evolve failed: evolve must be the only command in a response. Send evolve alone."
            ], False

        results = []
        should_evolve = False

        for cmd in commands:
            if cmd.type == "read":
                results.append(self._read.execute(cmd.path or ""))
            elif cmd.type == "write":
                results.append(self._write.execute(cmd.path or "", cmd.hunks or []))
            elif cmd.type == "evolve":
                results.append(self._evolve.execute(self._context.generation))
                should_evolve = True

        return results, should_evolve
