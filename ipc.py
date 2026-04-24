import json
import socket
import threading
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from input_handler import UserInputHandler


class AgentIPCClient:
    def __init__(self, port: int):
        self._port = port
        self._sock: Optional[socket.socket] = None
        self._lock = threading.Lock()

    def connect(self) -> bool:
        try:
            self._sock = socket.create_connection(("127.0.0.1", self._port), timeout=10)
            return True
        except (ConnectionRefusedError, OSError):
            return False

    def send_to_user(self, content: str) -> None:
        self._send({"type": "to_user", "content": content})

    def send_status(self, content: str) -> None:
        self._send({"type": "status", "content": content})

    def start_reader(self, input_handler: "UserInputHandler") -> None:
        threading.Thread(target=self._reader, args=(input_handler,), daemon=True).start()

    def _reader(self, input_handler: "UserInputHandler") -> None:
        buf = ""
        try:
            while True:
                chunk = self._sock.recv(4096)
                if not chunk:
                    break
                buf += chunk.decode("utf-8")
                while "\n" in buf:
                    line, buf = buf.split("\n", 1)
                    try:
                        obj = json.loads(line)
                        if obj.get("type") == "user_input":
                            input_handler.push(obj["content"])
                    except json.JSONDecodeError:
                        pass
        except OSError:
            pass

    def _send(self, obj: dict) -> None:
        if self._sock is None:
            return
        try:
            with self._lock:
                self._sock.sendall((json.dumps(obj) + "\n").encode("utf-8"))
        except OSError:
            pass
