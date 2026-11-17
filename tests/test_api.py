import hashlib
import http.cookiejar
import http.client
import json
from pathlib import Path
import tempfile
import threading
import socket
import unittest
from unittest.mock import Mock, patch
import urllib.error
import urllib.request

from backend.contest import App, APIError
from backend.server import Handler, Server
from test_core import fixture


class APITests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="ccpc space ")
        root = Path(self.temp.name)
        problems, history = fixture(root)
        self.now = 100000.0
        self.app = App(problems, history, root / "data", clock=lambda: self.now, start_worker=False)
        self.server = Server(("127.0.0.1", 0), self.app)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.url = f"http://127.0.0.1:{self.server.server_port}"
        self.jar = http.cookiejar.CookieJar()
        self.client = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.jar))
        self.csrf = self.request("/api/state")["csrf"]

    def tearDown(self):
        self.server.shutdown(); self.server.server_close(); self.thread.join()
        self.app.close(); self.temp.cleanup()

    def request(self, path, payload=None, headers=None, client=None):
        headers = dict(headers or {})
        if payload is not None:
            headers.setdefault("X-CSRF-Token", self.csrf)
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(self.url + path, data=json.dumps(payload).encode() if payload is not None else None, headers=headers)
        with (client or self.client).open(req) as response:
            return json.load(response) if response.headers.get_content_type() == "application/json" else response.read()

    def start(self): return self.request("/api/vp", {"name": "My team"})["session_id"]

    def submit(self, sid):
        return self.request("/api/submissions", {"session_id": sid, "problem": "A", "language": "cpp", "source": "int main(){}"})["id"]

    def test_begin_idempotency_and_submit_validation(self):
        sid = self.start()
        self.assertEqual(sid, self.start())
        sub_id = self.submit(sid)
        sub = self.request(f"/api/submissions/{sub_id}")
        self.assertEqual(sub["verdict"], "Queued")
        self.assertNotIn("time_ms", sub); self.assertNotIn("memory_kb", sub)
        with self.assertRaises(urllib.error.HTTPError) as result:
            self.request("/api/submissions", {"problem": "A", "language": "cpp", "source": "x"})
        self.assertEqual(result.exception.code, 400)

    def test_disconnect_does_not_send_500_or_stop_server(self):
        sid = self.start()
        sub_id = self.submit(sid)
        for stage in ("end_headers", "body"):
            for error in (ConnectionAbortedError, ConnectionResetError, BrokenPipeError, TimeoutError):
                with self.subTest(stage=stage, error=error):
                    handler = Handler.__new__(Handler)
                    handler.server = self.server
                    handler.path = f"/api/state?session_id={sid}"
                    handler.headers = {"Host": f"127.0.0.1:{self.server.server_port}"}
                    handler.identity = Mock(return_value=("owner", self.csrf))
                    handler.send_response = Mock()
                    handler.send_header = Mock()
                    handler.end_headers = Mock(side_effect=error() if stage == "end_headers" else None)
                    handler.wfile = Mock()
                    if stage == "body":
                        handler.wfile.write.side_effect = error()
                    with patch.object(self.app, "state", return_value={}), patch("backend.server.LOG") as log:
                        handler.dispatch(False)
                        handler.send_response.assert_called_once_with(200)
                        log.exception.assert_not_called()
                        self.assertTrue(handler.close_connection)
        # The queued submission survives and normal requests still work.
        self.assertEqual(self.request(f"/api/submissions/{sub_id}")["verdict"], "Queued")

    def test_owner_isolation(self):
        sid = self.start(); sub_id = self.submit(sid)
        other = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
        for path in (f"/api/state?session_id={sid}", f"/api/submissions/{sub_id}"):
            with self.assertRaises(urllib.error.HTTPError) as result: self.request(path, client=other)
            self.assertEqual(result.exception.code, 403)

    def test_submission_response_disconnect_preserves_one_queued_job(self):
        sid = self.start()
        with patch.object(Handler, "send_body", side_effect=ConnectionAbortedError()), patch("backend.server.LOG") as log:
            with self.assertRaises(http.client.RemoteDisconnected):
                self.submit(sid)
            log.exception.assert_not_called()
        subs = self.request(f"/api/state?session_id={sid}")["submissions"]
        self.assertEqual(len(subs), 1)
        self.assertEqual(subs[0]["verdict"], "Queued")
        self.assertEqual(self.app.judge.queue.qsize(), 1)

    def test_idle_and_partial_header_connections_expire(self):
        self.server.request_timeout = 0.2
        connections = [socket.create_connection(self.server.server_address, timeout=2) for _ in range(2)]
        try:
            connections[1].sendall(b"GET /api/state HTTP/1.1\r\nHost:")
            for connection in connections:
                # Blocking read waits for the server to close; no polling loop.
                self.assertEqual(connection.recv(1), b"")
            self.assertIn("csrf", self.request("/api/state"))
        finally:
            for connection in connections:
                connection.close()

    def test_csrf_origin_and_host(self):
        for headers in ({"X-CSRF-Token": "bad"}, {"Origin": "http://other.example"}, {"Host": "other.example"}):
            with self.assertRaises(urllib.error.HTTPError) as result: self.request("/api/vp", {"name": "X"}, headers=headers)
            self.assertEqual(result.exception.code, 403)

    def test_resources_are_allowlisted(self):
        self.assertIn(b"<!doctype html>", self.request("/"))
        self.assertIn("markdown", self.request("/api/problems/A"))
        self.assertEqual(self.request("/api/problems/A/assets/assets/toy.png"), b"toy fixture")
        for path in ("/AGENTS.md", "/tests/contest.txt", "/api/problems/A/assets/../config.json",
                     "/api/problems/A/assets/tutorial.md", "/vendor/../../AGENTS.md"):
            with self.assertRaises(urllib.error.HTTPError) as result: self.request(path)
            self.assertEqual(result.exception.code, 404)

    def test_filtering_pending_and_freeze(self):
        sid = self.start(); self.now += 14399; sub_id = self.submit(sid)
        self.now += 10
        state = self.request("/api/state")
        self.assertTrue(state["board"]["frozen"])
        self.assertEqual(state["board"]["pending"], 1)
        self.app.store.update(sub_id, verdict="AC", time_ms=9, memory_kb=80)
        state = self.request("/api/state")
        self.assertEqual(state["board"]["counts"]["A"], 2)
        self.assertNotIn("time_ms", state["submissions"][0])
        after_id = self.submit(sid); self.app.store.update(after_id, verdict="AC")
        self.assertEqual(self.request("/api/state")["board"]["rows"], state["board"]["rows"])

    def test_end_final_and_new_vp(self):
        sid = self.start(); sub_id = self.submit(sid)
        self.app.store.update(sub_id, verdict="AC", time_ms=10, memory_kb=30)
        with self.assertRaises(urllib.error.HTTPError): self.request("/api/state?final=1")
        self.now += 18000
        with self.assertRaises(urllib.error.HTTPError) as result: self.submit(sid)
        self.assertEqual(result.exception.code, 409)
        final = self.request("/api/state?final=1")
        self.assertTrue(final["board"]["final"])
        self.assertEqual(final["submissions"][0]["time_ms"], 10)
        new = self.start(); self.assertNotEqual(new, sid)
        self.assertEqual(len(self.request(f"/api/state?session_id={sid}")["submissions"]), 1)

    def test_invalid_code_and_problem(self):
        sid = self.start()
        for changes in ({"source": ""}, {"source": "x"*262145}, {"problem": "Z"}, {"language": "javascript"}):
            payload = {"session_id": sid, "problem": "A", "language": "cpp", "source": "x"} | changes
            with self.assertRaises(urllib.error.HTTPError): self.request("/api/submissions", payload)

    def test_restart_restores_state_and_requeues(self):
        sid = self.start(); sub_id = self.submit(sid)
        self.app.store.update(sub_id, verdict="Running")
        self.server.shutdown(); self.thread.join()
        self.app.close()
        root = Path(self.temp.name)
        problems, history = root / "problems", root / "contest.txt"
        self.now += 60
        self.app = App(problems, history, root / "data", clock=lambda: self.now, start_worker=False)
        self.server.app = self.app
        token = next(iter(self.jar)).value
        owner = hashlib.sha256(token.encode()).hexdigest()
        self.assertEqual(self.app.session(owner)["id"], sid)
        self.assertEqual(self.app.elapsed(self.app.session(owner)), 60)
        self.assertEqual(self.app.store.recover(self.app.input_id), [sub_id])
        self.assertEqual(self.app.store.get_submission(sub_id)["verdict"], "Queued")
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True); self.thread.start()
