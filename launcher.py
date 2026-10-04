"""One-command local CCPC OJ launcher."""
import argparse
import importlib.util
import logging
import os
import signal
import subprocess
from pathlib import Path
import sys
import threading
import webbrowser

ROOT = Path(__file__).resolve().parent


def main():
    if hasattr(signal, "SIGBREAK"):
        signal.signal(signal.SIGBREAK, lambda *_: (_ for _ in ()).throw(KeyboardInterrupt()))
    parser = argparse.ArgumentParser(description="CCPC 新榜单机制本地 OJ")
    parser.add_argument("--problem-list", type=Path, required=True, help="含 A、B…题目目录的集合")
    parser.add_argument("--submissions", type=Path, required=True, help="@ 格式历史提交文件")
    parser.add_argument("--port", type=int, default=8765, help="localhost 端口，0 表示自动分配")
    parser.add_argument("--data-dir", type=Path, default=ROOT / "tmp" / "ccpc-local", help="状态、缓存和日志目录")
    parser.add_argument("--no-browser", action="store_true", help="不自动打开浏览器")
    args = parser.parse_args()
    if not 0 <= args.port <= 65535:
        parser.error("端口须为 0–65535")
    if importlib.util.find_spec("psutil") is None:
        venv = ROOT / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        if venv.is_file() and venv.resolve() != Path(sys.executable).resolve():
            # Windows exec starts a new PID and can orphan the service from a
            # caller supervising this launcher. Keep a forwarding parent alive.
            child = subprocess.Popen([str(venv), str(Path(__file__).resolve()), *sys.argv[1:]])
            try:
                return child.wait()
            except KeyboardInterrupt:
                try:
                    return child.wait(timeout=15)
                except subprocess.TimeoutExpired:
                    child.terminate()
                    child.wait()
                    return 130
        parser.error("缺少 psutil。请执行 python -m pip install -r requirements.txt")
    args.data_dir = args.data_dir.resolve()
    args.data_dir.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(filename=args.data_dir / "server.log", level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s", encoding="utf-8")
    from backend.contest import App
    from backend.server import Server
    app, server = None, None
    try:
        if not args.submissions.is_file():
            raise ValueError(f"历史文件不存在: {args.submissions}")
        for file in ["vendor/marked/lib/marked.umd.js", "vendor/dompurify/dist/purify.min.js",
                     "vendor/katex/dist/katex.min.js", "vendor/katex/dist/contrib/auto-render.min.js"]:
            if not (ROOT / "frontend" / file).is_file():
                raise ValueError(f"缺少离线前端资源 {file}，请恢复交付文件")
        print("正在校验题包与历史记录…", flush=True)
        app = App(args.problem_list.resolve(), args.submissions.resolve(), args.data_dir)
        try:
            server = Server(("127.0.0.1", args.port), app)
        except OSError:
            if not args.port:
                raise
            print(f"端口 {args.port} 不可用，正在分配其他端口。", flush=True)
            server = Server(("127.0.0.1", 0), app)
        print(f"已加载 {len(app.problems)} 题、{len(app.contest.teams)} 队、{len(app.contest.events)} 条提交。", flush=True)
        for diagnostic in app.contest.diagnostics:
            print(diagnostic, flush=True)
        url = f"http://127.0.0.1:{server.server_port}/"
        print(f"本地 OJ 已就绪：{url}\n数据目录：{args.data_dir}\n按 Ctrl+C 停止；刷新或重启可恢复 VP。", flush=True)
        if not args.no_browser:
            threading.Timer(0.5, lambda: webbrowser.open(url)).start()
        server.serve_forever(poll_interval=0.2)
    except KeyboardInterrupt:
        print("\n正在停止服务和判题进程…", flush=True)
    except (ValueError, OSError, RuntimeError) as exc:
        print(f"启动失败：{exc}", file=sys.stderr)
        return 1
    finally:
        if server:
            server.server_close()
        if app:
            app.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
