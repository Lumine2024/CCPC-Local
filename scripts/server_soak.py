"""Run a real launcher and HTTP/judge workload from an external JSON scenario."""
import argparse
from datetime import datetime, timezone
import http.cookiejar
import json
import math
import os
from pathlib import Path
import re
import socket
import struct
import subprocess
import sys
import threading
import time
import urllib.request


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    cfg = json.loads(args.config.read_text(encoding="utf-8"))
    for key in ("sample_s", "duration_s", "startup_timeout_s", "startup_poll_s", "request_timeout_s",
                "shutdown_timeout_s", "judge_timeout_s", "poll_s", "submit_interval_s", "disconnect_interval_s"):
        if not math.isfinite(cfg[key]) or cfg[key] <= 0:
            parser.error(f"{key} must be finite and positive")
    root = Path(__file__).resolve().parents[1]
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    (out / "scenario.json").write_text(json.dumps(cfg, indent=2), encoding="utf-8")
    wake = threading.Event()
    result = dict(started=datetime.now(timezone.utc).isoformat(), submissions=[], errors=[])
    with (out / "client.jsonl").open("a", encoding="utf-8", buffering=1) as events, \
            (out / "launcher.log").open("w", encoding="utf-8") as console:
        def record(event, **fields):
            events.write(json.dumps(dict(wall=time.time(), event=event, **fields)) + "\n")

        process = subprocess.Popen([sys.executable, str(root / "launcher.py"),
            "--problem-list", str(root / cfg["problems"]), "--submissions", str(root / cfg["history"]),
            "--port", str(cfg["port"]), "--data-dir", str(out), "--no-browser",
            "--diagnostics-interval", str(cfg["sample_s"])], cwd=root, stdout=console,
            stderr=subprocess.STDOUT, creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            env={**os.environ, "PYTHONIOENCODING": "utf-8"})
        result["launcher_pid"] = process.pid
        try:
            deadline = time.monotonic() + cfg["startup_timeout_s"]
            while True:
                match = re.search(r"http://127\.0\.0\.1:\d+", (out / "launcher.log").read_text(encoding="utf-8"))
                if match:
                    break
                if process.poll() is not None or time.monotonic() >= deadline:
                    raise RuntimeError("launcher failed or startup timed out")
                wake.wait(cfg["startup_poll_s"])
            url = match.group()
            result["url"] = url
            client = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
            csrf = None

            def request(path, payload=None):
                headers = {"X-CSRF-Token": csrf or "", "Content-Type": "application/json"}
                req = urllib.request.Request(url + path, data=json.dumps(payload).encode() if payload else None, headers=headers)
                before = time.monotonic()
                with client.open(req, timeout=cfg["request_timeout_s"]) as response:
                    data = json.load(response)
                record("request", path=path, elapsed_s=time.monotonic()-before)
                return data

            csrf = request("/api/state")["csrf"]
            sid = request("/api/vp", {"name": cfg["team"]})["session_id"]
            record("ready", url=url, launcher_pid=process.pid)
            started = time.monotonic()
            next_submit = next_disconnect = started
            pending = {}
            while time.monotonic() - started < cfg["duration_s"] or pending:
                if process.poll() is not None:
                    raise RuntimeError("server exited during soak")
                now = time.monotonic()
                if now >= next_submit and now-started < cfg["duration_s"]:
                    for item in cfg["submissions"]:
                        payload = dict(session_id=sid, problem=item["problem"], language=item["language"],
                                       source=(root / item["source"]).read_text(encoding="utf-8"))
                        sub_id = request("/api/submissions", payload)["id"]
                        pending[sub_id] = (item, now)
                    next_submit = now + cfg["submit_interval_s"]
                if now >= next_disconnect:
                    port = int(url.rsplit(":", 1)[1])
                    with socket.create_connection(("127.0.0.1", port), timeout=cfg["request_timeout_s"]) as sock:
                        sock.sendall(f"GET /api/state HTTP/1.1\r\nHost: 127.0.0.1:{port}\r\n\r\n".encode())
                        sock.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER,
                                        struct.pack("HH" if os.name == "nt" else "ii", 1, 0))
                    record("intentional_disconnect")
                    next_disconnect = now + cfg["disconnect_interval_s"]
                try:
                    state = request("/api/state?session_id=" + sid)
                    for sub in state["submissions"]:
                        if sub["id"] in pending and sub["verdict"] not in {"Queued", "Compiling", "Running"}:
                            item, _ = pending.pop(sub["id"])
                            record("verdict", id=sub["id"], verdict=sub["verdict"], expected=item["expected"])
                            result["submissions"].append(dict(id=sub["id"], verdict=sub["verdict"], expected=item["expected"]))
                    if any(now-t > cfg["judge_timeout_s"] for _, t in pending.values()):
                        raise RuntimeError("judge progress timeout")
                except Exception as exc:
                    result["errors"].append(repr(exc))
                    record("error", error=repr(exc))
                    if any(now-t > cfg["judge_timeout_s"] for _, t in pending.values()):
                        raise
                wake.wait(cfg["poll_s"])
        except Exception as exc:
            result["errors"].append(repr(exc))
            record("fatal", error=repr(exc))
        finally:
            (out / "diagnostics-stop.request").touch()
            try:
                process.wait(timeout=cfg["shutdown_timeout_s"])
            except subprocess.TimeoutExpired:
                process.terminate()
                process.wait(timeout=cfg["shutdown_timeout_s"])
                result["errors"].append("forced termination after shutdown timeout")
            result["finished"] = datetime.now(timezone.utc).isoformat()
            result["exit_code"] = process.returncode
            result["passed"] = (process.returncode == 0 and not result["errors"] and
                                bool(result["submissions"]) and
                                all(s["verdict"] == s["expected"] for s in result["submissions"]))
            (out / "summary.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
