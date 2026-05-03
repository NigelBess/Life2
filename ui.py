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
from flask import Flask, Response, jsonify, render_template, request, stream_with_context

AGENT_PORT = 7337
WEB_PORT   = 8080

# Lives outside Life2/ so it survives the directory being deleted on evolution
LOG_DIR = Path(__file__).parent.resolve().parent / "life2_logs"
APP_DIR = Path(__file__).parent.resolve()
ENV_PATH = APP_DIR / ".env"

app = Flask(__name__)

# Messages waiting to be forwarded to the agent
pending: queue.Queue[str] = queue.Queue()

# SSE client queues — one per open browser tab
_sse_clients: list[queue.Queue] = []
_sse_lock = threading.Lock()

_state         = {"generation": 0, "connected": False}
_session_start = datetime.now().strftime("%Y%m%d_%H%M%S")
_agent_process: subprocess.Popen | None = None
_agent_lock = threading.Lock()


# ── Helpers ────────────────────────────────────────────────────────────────────

def _push(event: dict) -> None:
    """Broadcast an event to all connected browser tabs."""
    with _sse_lock:
        for q in _sse_clients:
            q.put(event)


def _log(type_: str, content: str, generation: int = 0) -> None:
    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        path = LOG_DIR / f"session_{_session_start}.jsonl"
        entry = {"ts": datetime.now().isoformat(), "type": type_,
                 "content": content, "gen": generation}
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
    except OSError:
        pass


def _load_api_key() -> str:
    load_dotenv(dotenv_path=ENV_PATH, override=True)
    return os.environ.get("ANTHROPIC_API_KEY", "").strip()


# ── Routes ─────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/events")
def events():
    """Server-Sent Events stream — pushes agent messages to the browser."""
    client_q: queue.Queue = queue.Queue()
    with _sse_lock:
        _sse_clients.append(client_q)

    def stream():
        try:
            while True:
                try:
                    event = client_q.get(timeout=25)
                    yield f"data: {json.dumps(event)}\n\n"
                except queue.Empty:
                    yield ": keepalive\n\n"   # prevents proxy timeouts
        finally:
            with _sse_lock:
                if client_q in _sse_clients:
                    _sse_clients.remove(client_q)

    return Response(
        stream_with_context(stream()),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.route("/api/send", methods=["POST"])
def send():
    """Receive a message from the browser and forward to the agent."""
    content = ((request.json or {}).get("content") or "").strip()
    if content:
        pending.put(content)
        _log("user", content)
    return jsonify({"ok": True, "queued": not _state["connected"]})


@app.route("/api/check-key")
def check_key():
    return jsonify({"has_key": bool(_load_api_key())})


@app.route("/api/set-key", methods=["POST"])
def set_key():
    key = ((request.json or {}).get("key") or "").strip()
    if not key:
        return jsonify({"ok": False, "error": "Key cannot be empty."})

    lines = ENV_PATH.read_text(encoding="utf-8").splitlines() if ENV_PATH.exists() else []
    found, new_lines = False, []
    for line in lines:
        if line.startswith("ANTHROPIC_API_KEY="):
            new_lines.append(f"ANTHROPIC_API_KEY={key}")
            found = True
        else:
            new_lines.append(line)
    if not found:
        new_lines.append(f"ANTHROPIC_API_KEY={key}")

    ENV_PATH.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
    os.environ["ANTHROPIC_API_KEY"] = key
    return jsonify({"ok": True})


@app.route("/api/start-agent", methods=["POST"])
def start_agent():
    global _agent_process
    if not _load_api_key():
        return jsonify({"ok": False, "error": "Missing Anthropic API key."}), 400

    agent_path = APP_DIR / "main.py"
    with _agent_lock:
        if _agent_process and _agent_process.poll() is None:
            return jsonify({"ok": True, "already_running": True})
        _push({"type": "status", "status": "starting"})
        _agent_process = subprocess.Popen(
            [sys.executable, str(agent_path), "--ui-port", str(AGENT_PORT)],
            cwd=str(APP_DIR),
        )
    return jsonify({"ok": True})


# ── Agent IPC server ───────────────────────────────────────────────────────────

def _agent_ipc_server() -> None:
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(("127.0.0.1", AGENT_PORT))
    server.listen(1)

    while True:
        conn, _ = server.accept()
        _state["generation"] += 1
        _state["connected"] = True
        gen = _state["generation"]

        _log("status", "connected", gen)
        _push({"type": "status", "status": "connected", "generation": gen})

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
                                _log("agent", obj["content"], g)
                                _push({"type": "message", "content": obj["content"], "generation": g})
                            elif obj["type"] == "status":
                                _log("status", obj["content"], g)
                                _push({"type": "status", "status": obj["content"], "generation": g})
                        except (json.JSONDecodeError, KeyError):
                            pass
            except OSError:
                pass
            finally:
                evt.set()

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
        _state["connected"] = False
        _log("status", "evolving", gen)
        _push({"type": "status", "status": "evolving"})


# ── Entry point ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    threading.Thread(target=_agent_ipc_server, daemon=True).start()
    threading.Timer(1.2, lambda: webbrowser.open(f"http://localhost:{WEB_PORT}")).start()
    print(f"Life2 -> http://localhost:{WEB_PORT}", flush=True)
    app.run(host="0.0.0.0", port=WEB_PORT, debug=False, threaded=True)
