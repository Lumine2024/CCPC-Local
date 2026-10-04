"""Loopback-only same-origin HTTP API; no workspace directory is served."""
import hashlib
import hmac
import json
import logging
import mimetypes
import re
import secrets
from http import cookies
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlsplit

from .contest import APIError

FRONTEND = Path(__file__).resolve().parents[1] / "frontend"
LOG = logging.getLogger("ccpc.http")


class Server(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address, app):
        self.app = app
        super().__init__(address, Handler)


class Handler(BaseHTTPRequestHandler):
    server_version = "CCPC-Local/1.0"

    def log_message(self, fmt, *args):
        LOG.info(fmt, *args)

    def identity(self):
        jar = cookies.SimpleCookie()
        try:
            jar.load(self.headers.get("Cookie", ""))
            token = jar["ccpc_client"].value if "ccpc_client" in jar else ""
        except cookies.CookieError:
            token = ""
        if not re.fullmatch(r"[a-f0-9]{64}", token):
            token = secrets.token_hex(32)
            self.new_cookie = f"ccpc_client={token}; Path=/; HttpOnly; SameSite=Strict; Max-Age=31536000"
        owner = hashlib.sha256(token.encode()).hexdigest()
        csrf = hmac.new(self.server.app.store.secret.encode(), token.encode(), hashlib.sha256).hexdigest()
        return owner, csrf

    def send(self, data, status=200, mime="application/json; charset=utf-8"):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8") if isinstance(data, (dict, list)) else data
        self.send_response(status)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "same-origin")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self'; font-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'")
        if getattr(self, "new_cookie", None):
            self.send_header("Set-Cookie", self.new_cookie)
        self.end_headers()
        try:
            self.wfile.write(body)
        except (ConnectionResetError, BrokenPipeError):
            pass

    def do_GET(self):
        self.dispatch(False)

    def do_POST(self):
        self.dispatch(True)

    def dispatch(self, write):
        self.new_cookie = None
        try:
            port = self.server.server_port
            allowed = {f"127.0.0.1:{port}", f"localhost:{port}"}
            host = self.headers.get("Host", "")
            if host not in allowed:
                raise APIError("拒绝非本机 Host", 403)
            origin = self.headers.get("Origin")
            if origin and origin != f"http://{host}":
                raise APIError("拒绝跨来源请求", 403)
            owner, csrf = self.identity()
            url = urlsplit(self.path)
            path = unquote(url.path)
            query = parse_qs(url.query)
            app = self.server.app
            if write:
                if not hmac.compare_digest(self.headers.get("X-CSRF-Token", ""), csrf):
                    raise APIError("缺少或无效的请求令牌，请刷新页面", 403)
                try:
                    length = int(self.headers.get("Content-Length", "0"))
                except ValueError:
                    raise APIError("无效请求长度")
                if not 0 < length <= 2 * 1024 * 1024:
                    raise APIError("请求为空或过大", 413)
                self.connection.settimeout(15)
                payload = json.loads(self.rfile.read(length))
                if not isinstance(payload, dict):
                    raise APIError("请求须为 JSON 对象")
                if path == "/api/vp":
                    session = app.start(owner, payload.get("name", ""))
                    return self.send({"session_id": session["id"]})
                if path == "/api/submissions":
                    return self.send(app.submit(owner, payload), 201)
                raise APIError("接口不存在", 404)
            if path == "/api/state":
                state = app.state(owner, query.get("session_id", [None])[0], query.get("final", ["0"])[0] == "1")
                state["csrf"] = csrf
                return self.send(state)
            match = re.fullmatch(r"/api/submissions/(\d+)", path)
            if match:
                return self.send(app.submission(owner, int(match[1])))
            match = re.fullmatch(r"/api/problems/([^/]+)(?:/assets/(.+))?", path)
            if match:
                pid, asset = match.groups()
                if pid not in app.problems:
                    raise APIError("题目不存在", 404)
                p = app.problems[pid]
                if asset:
                    if asset not in p.assets:
                        raise APIError("资源不存在", 404)
                    return self.file(p.assets[asset])
                return self.send({"id": pid, "markdown": p.statement})
            if path.startswith("/api/"):
                raise APIError("接口不存在", 404)
            if path == "/":
                return self.file(FRONTEND / "index.html")
            relative = path.removeprefix("/")
            file = (FRONTEND / relative).resolve()
            if ".." in Path(relative).parts or not file.is_relative_to(FRONTEND.resolve()):
                raise APIError("资源不存在", 404)
            if relative not in {"app.js", "style.css", "icon.svg"} and not relative.startswith("vendor/"):
                raise APIError("资源不存在", 404)
            if file.suffix.lower() not in {".js", ".css", ".svg", ".woff", ".woff2", ".ttf", ".txt", ".md"}:
                raise APIError("资源不存在", 404)
            return self.file(file)
        except APIError as exc:
            self.send({"error": str(exc)}, exc.status)
        except (json.JSONDecodeError, UnicodeError, TypeError, ValueError) as exc:
            self.send({"error": "请求格式错误"}, 400)
        except Exception:
            LOG.exception("HTTP handler failed")
            self.send({"error": "服务异常，请查看本地日志"}, 500)

    def file(self, file):
        if not file.is_file():
            raise APIError("资源不存在", 404)
        mime = mimetypes.guess_type(file.name)[0] or "application/octet-stream"
        if file.suffix == ".js":
            mime = "text/javascript"
        return self.send(file.read_bytes(), mime=mime)
