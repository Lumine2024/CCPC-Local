import hashlib
import http.cookiejar
import json
from pathlib import Path
import tempfile
import threading
import unittest
import urllib.error
import urllib.request

from backend.contest import App, APIError
from backend.server import Server
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

    def test_owner_isolation(self):
        sid = self.start(); sub_id = self.submit(sid)
        other = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
        for path in (f"/api/state?session_id={sid}", f"/api/submissions/{sub_id}"):
            with self.assertRaises(urllib.error.HTTPError) as result: self.request(path, client=other)
            self.assertEqual(result.exception.code, 403)

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
