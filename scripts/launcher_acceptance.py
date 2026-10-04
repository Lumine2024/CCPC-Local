"""Exercise launcher fallback, occupied ports, spaced paths and diagnostics."""
import json
import os
from pathlib import Path
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "tests")]
from test_core import fixture


def main():
    output = ROOT / "tmp/acceptance"
    output.mkdir(parents=True, exist_ok=True)
    checks = []
    with tempfile.TemporaryDirectory(prefix="launcher with spaces ") as tmp:
        root = Path(tmp); problems, history = fixture(root)
        python = shutil.which("python") or sys.executable
        base = [python, str(ROOT / "launcher.py"), "--problem-list", str(problems), "--submissions", str(history),
                "--no-browser", "--data-dir", str(root / "data with spaces")]
        env = os.environ | {"PYTHONIOENCODING": "utf-8"}
        with socket.socket() as occupied:
            occupied.bind(("127.0.0.1", 0)); occupied.listen()
            logfile = root / "launch.log"
            with logfile.open("wb") as stream:
                process = subprocess.Popen(base + ["--port", str(occupied.getsockname()[1])], stdout=stream, stderr=stream, env=env,
                                           creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0)
            try:
                import re
                deadline = time.time() + 30
                while time.time() < deadline:
                    text = logfile.read_text(encoding="utf-8", errors="replace")
                    match = re.search(r"http://127\.0\.0\.1:(\d+)/", text)
                    if match: break
                    if process.poll() is not None: raise RuntimeError(text)
                    time.sleep(.2)
                else: raise RuntimeError("Launcher timeout")
                assert int(match[1]) != occupied.getsockname()[1]
                assert json.load(urllib.request.urlopen(match[0]+"api/state"))["contest"]["title"] == "Toy, with comma"
                checks.append("Plain python launcher, automatic venv fallback, spaced input/data paths, occupied port fallback")
            finally:
                process.send_signal(signal.CTRL_BREAK_EVENT if os.name == "nt" else signal.SIGINT)
                process.wait(timeout=20)
                assert process.returncode == 0
            checks.append("Graceful Ctrl+C/SIGBREAK shutdown returns zero")
        for label, arguments, environment in [
            ("Invalid port", base + ["--port", "65536"], env),
            ("Missing input", base + ["--submissions", str(root / "missing.txt")], env),
            ("Missing compiler", base, env | {"PATH": str(Path(sys.executable).parent)})]:
            result = subprocess.run(arguments, env=environment, capture_output=True, text=True, encoding="utf-8", timeout=30)
            assert result.returncode != 0, label
            checks.append(label+" produces nonzero exit and diagnostic")
    report = {"success": True, "checks": checks}
    (output / "launcher-results.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
