import queue
import threading
from typing import Optional


class UserInputHandler:
    def __init__(self):
        self._queue: queue.Queue[str] = queue.Queue()

    def start_stdin(self) -> None:
        threading.Thread(target=self._read_loop, daemon=True).start()

    def push(self, message: str) -> None:
        self._queue.put(message)

    def drain(self) -> list[str]:
        messages = []
        while True:
            try:
                messages.append(self._queue.get_nowait())
            except queue.Empty:
                break
        return messages

    def get(self, timeout: Optional[float] = None) -> Optional[str]:
        try:
            return self._queue.get(timeout=timeout)
        except queue.Empty:
            return None

    def _read_loop(self) -> None:
        while True:
            try:
                line = input()
                self._queue.put(line)
            except EOFError:
                break
