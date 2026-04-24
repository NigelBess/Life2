"""
Stable UI process. Run once — survives all agent evolutions.
Opens a browser UI at http://localhost:8080
"""
import json
import os
import queue
import socket
import subprocess
import sys
import threading
import webbrowser
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request
from flask_socketio import SocketIO

AGENT_PORT = 7337
WEB_PORT = 8080

# Logs live in a sibling directory so they survive Life2/ being deleted on evolution
LOG_DIR = Path(__file__).parent.resolve().parent / "life2_logs"

app = Flask(__name__)
app.config["SECRET_KEY"] = "life2"
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

pending: queue.Queue[str] = queue.Queue()
_state = {"conn": None, "generation": 0}
_state_lock = threading.Lock()


# ── Logging ────────────────────────────────────────────────────────────────────

_session_log: Path | None = None


def _get_session_log() -> Path:
    global _session_log
    if _session_log is None:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        _session_log = LOG_DIR / f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl"
    return _session_log


def log(type_: str, content: str, generation: int = 0) -> None:
    entry = {
        "ts": datetime.now().isoformat(),
        "type": type_,
        "content": content,
        "gen": generation,
    }
    try:
        with open(_get_session_log(), "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
    except OSError:
        pass


# ── Flask routes ───────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/check-key")
def check_key():
    load_dotenv(override=True)
    return jsonify({"has_key": bool(os.environ.get("ANTHROPIC_API_KEY", "").strip())})


@app.route("/api/set-key", methods=["POST"])
def set_key():
    key = (request.json or {}).get("key", "").strip()
    if not key:
        return jsonify({"ok": False, "error": "Key cannot be empty."})

    env_path = Path(__file__).parent / ".env"
    lines = env_path.read_text(encoding="utf-8").splitlines() if env_path.exists() else []
    found = False
    new_lines = []
    for line in lines:
        if line.startswith("ANTHROPIC_API_KEY="):
            new_lines.append(f"ANTHROPIC_API_KEY={key}")
            found = True
        else:
            new_lines.append(line)
    if not found:
        new_lines.append(f"ANTHROPIC_API_KEY={key}")

    env_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
    os.environ["ANTHROPIC_API_KEY"] = key
    return jsonify({"ok": True})


@app.route("/api/start-agent", methods=["POST"])
def start_agent():
    agent_path = Path(__file__).parent / "main.py"
    subprocess.Popen([sys.executable, str(agent_path), "--ui-port", str(AGENT_PORT)])
    return jsonify({"ok": True})


# ── Socket.IO events ───────────────────────────────────────────────────────────

@socketio.on("user_message")
def handle_user_message(data):
    content = (data.get("content") or "").strip()
    if content:
        pending.put(content)
        log("user", content)


# ── Agent IPC server ───────────────────────────────────────────────────────────

def _agent_ipc_server() -> None:
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(("127.0.0.1", AGENT_PORT))
    server.listen(1)

    while True:
        conn, _ = server.accept()

        with _state_lock:
            _state["generation"] += 1
            _state["conn"] = conn
            gen = _state["generation"]

        log("status", "connected", gen)
        socketio.emit("agent_status", {"status": "connected", "generation": gen})

        disconnected = threading.Event()

        def _reader(c=conn, g=gen, evt=disconnected) -> None:
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
                                log("agent", obj["content"], g)
                                socketio.emit("agent_message", {
                                    "content": obj["content"],
                                    "generation": g,
                                })
                            elif obj["type"] == "status":
                                log("status", obj["content"], g)
                                socketio.emit("agent_status", {
                                    "status": obj["content"],
                                    "generation": g,
                                })
                        except (json.JSONDecodeError, KeyError):
                            pass
            except OSError:
                pass
            finally:
                evt.set()
                with _state_lock:
                    _state["conn"] = None

        def _writer(c=conn, evt=disconnected) -> None:
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

        threading.Thread(target=_reader, daemon=True).start()
        threading.Thread(target=_writer, daemon=True).start()

        disconnected.wait()
        log("status", "evolving", gen)
        socketio.emit("agent_status", {"status": "evolving"})


# ── Entry point ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    threading.Thread(target=_agent_ipc_server, daemon=True).start()
    threading.Timer(1.2, lambda: webbrowser.open(f"http://localhost:{WEB_PORT}")).start()
    print(f"Life2  →  http://localhost:{WEB_PORT}", flush=True)
    socketio.run(app, host="0.0.0.0", port=WEB_PORT, debug=False, allow_unsafe_werkzeug=True)
