"""
Standalone UI process. Run this once — it starts the agent and stays alive
across all agent generations. The agent connects back on every startup.
"""
import json
import queue
import socket
import subprocess
import sys
import threading
from pathlib import Path

PORT = 7337


def main() -> None:
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(("127.0.0.1", PORT))
    server.listen(1)

    pending: queue.Queue[str] = queue.Queue()

    def stdin_reader() -> None:
        while True:
            try:
                line = input()
                pending.put(line)
            except EOFError:
                break

    threading.Thread(target=stdin_reader, daemon=True).start()

    agent_path = Path(__file__).parent / "main.py"
    subprocess.Popen([sys.executable, str(agent_path), "--ui-port", str(PORT)])

    print(f"Life2  (port {PORT})", flush=True)

    while True:
        conn, _ = server.accept()
        disconnected = threading.Event()

        def agent_reader(c=conn, evt=disconnected) -> None:
            buf = ""
            try:
                while True:
                    chunk = c.recv(4096)
                    if not chunk:
                        break
                    buf += chunk.decode("utf-8")
                    while "\n" in buf:
                        line, buf = buf.split("\n", 1)
                        try:
                            obj = json.loads(line)
                            if obj["type"] == "to_user":
                                print(f"\n{obj['content']}\n", flush=True)
                            elif obj["type"] == "status":
                                print(f"[{obj['content']}]", flush=True)
                        except (json.JSONDecodeError, KeyError):
                            pass
            except OSError:
                pass
            finally:
                evt.set()

        def agent_writer(c=conn, evt=disconnected) -> None:
            try:
                while not evt.is_set():
                    try:
                        msg = pending.get(timeout=0.1)
                    except queue.Empty:
                        continue
                    payload = json.dumps({"type": "user_input", "content": msg}) + "\n"
                    c.sendall(payload.encode("utf-8"))
            except OSError:
                pass

        threading.Thread(target=agent_reader, daemon=True).start()
        threading.Thread(target=agent_writer, daemon=True).start()

        disconnected.wait()
        print("[evolving — reconnecting...]", flush=True)


if __name__ == "__main__":
    main()
