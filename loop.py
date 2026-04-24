from pathlib import Path
from typing import Optional

from context import AgentContext
from clone_manager import CloneManager
from commands.executor import CommandExecutor
from input_handler import UserInputHandler
from ipc import AgentIPCClient
from llm.base import LLMProvider
from response_parser import parse_response
from system_prompt import build_system_prompt


class AgentLoop:
    def __init__(
        self,
        context: AgentContext,
        llm: LLMProvider,
        soul_content: str,
        work_dir: Path,
        launch_dir: Path,
        input_handler: UserInputHandler,
        ipc: Optional[AgentIPCClient] = None,
    ):
        self._context = context
        self._llm = llm
        self._soul_content = soul_content
        self._work_dir = work_dir
        self._launch_dir = launch_dir
        self._input_handler = input_handler
        self._ipc = ipc
        self._executor = CommandExecutor(work_dir, context)

    def _update_pointer(self) -> None:
        pointer = self._launch_dir / "last_context.txt"
        pointer.write_text(str(self._work_dir / "context.json"), encoding="utf-8")

    def run(self) -> None:
        while True:
            self._cycle()

    def _cycle(self) -> None:
        for msg in self._input_handler.drain():
            self._context.messages.append({"role": "user", "content": msg})

        system = build_system_prompt(self._work_dir, self._soul_content)
        raw = self._llm.send(self._context.messages, system)
        self._context.messages.append({"role": "assistant", "content": raw})

        response = parse_response(raw)

        if response.to_user:
            if self._ipc:
                self._ipc.send_to_user(response.to_user)
            else:
                print(f"\n{response.to_user}\n", flush=True)

        results, should_evolve = self._executor.execute(response.commands)

        if results:
            numbered = "\n".join(f"{i+1}. {r}" for i, r in enumerate(results))
            feedback = f"[COMMAND RESULTS]\n{numbered}\n\n[TO_SELF]\n{response.to_self}"
        else:
            feedback = f"[COMMAND RESULTS]\n(none)\n\n[TO_SELF]\n{response.to_self}"

        self._context.messages.append({"role": "user", "content": feedback})

        self._context.save(self._work_dir / "context.json")
        self._update_pointer()

        if should_evolve:
            CloneManager(self._launch_dir).evolve(self._context, self._work_dir)
