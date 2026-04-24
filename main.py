import argparse
import shutil
from pathlib import Path
from typing import Optional

import config
from clone_manager import CloneManager
from context import AgentContext
from input_handler import UserInputHandler
from ipc import AgentIPCClient
from llm.claude import ClaudeProvider
from loop import AgentLoop


def _find_last_context(launch_dir: Path) -> Optional[Path]:
    pointer = launch_dir / "last_context.txt"
    if not pointer.exists():
        return None
    path = Path(pointer.read_text(encoding="utf-8").strip())
    return path if path.exists() else None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--context", type=Path, default=None)
    parser.add_argument("--ui-port", type=int, default=None)
    args = parser.parse_args()

    launch_dir = Path(__file__).parent.resolve()
    clone_mgr = CloneManager(launch_dir)

    context_path = args.context or _find_last_context(launch_dir)

    input_handler = UserInputHandler()

    ipc: Optional[AgentIPCClient] = None
    if args.ui_port:
        ipc = AgentIPCClient(args.ui_port)
        ipc.connect()
        ipc.start_reader(input_handler)

    if context_path and context_path.exists():
        ctx = AgentContext.load(context_path)

        if ctx.parent_to_delete:
            shutil.rmtree(ctx.parent_to_delete, ignore_errors=True)

        work_dir = clone_mgr.create_work_dir(ctx.generation + 1)
        ctx.work_dir = str(work_dir)
        ctx.parent_to_delete = None

        if args.ui_port:
            ctx.ui_port = args.ui_port

        if not args.context:
            msg = "Resuming previous session."
            if ipc:
                ipc.send_to_user(msg)
            else:
                print(msg, flush=True)
    else:
        ctx = AgentContext(generation=0, ui_port=args.ui_port)
        work_dir = clone_mgr.create_work_dir(1)
        ctx.work_dir = str(work_dir)

        greeting = "Hello there"
        if ipc:
            ipc.send_to_user(greeting)
            first_input = input_handler.get()
        else:
            print(greeting, flush=True)
            input_handler.start_stdin()
            first_input = input_handler.get()

        if first_input:
            ctx.messages.append({"role": "user", "content": first_input})

    if not ipc:
        input_handler.start_stdin()

    soul_path = launch_dir / "soul.md"
    soul_content = soul_path.read_text(encoding="utf-8") if soul_path.exists() else ""

    llm = ClaudeProvider(api_key=config.ANTHROPIC_API_KEY, model=config.MODEL)

    AgentLoop(
        context=ctx,
        llm=llm,
        soul_content=soul_content,
        work_dir=work_dir,
        launch_dir=launch_dir,
        input_handler=input_handler,
        ipc=ipc,
    ).run()


if __name__ == "__main__":
    main()
