"""Application service, shared by HTTP handlers and deterministic acceptance tests."""
import hashlib
import threading
import time
from pathlib import Path

from .contest_parser import Event, parse_contest
from .problems import load_problems
from .scoreboard import PENDING, score, view
from .storage import Storage
from .judge import Judge


class APIError(Exception):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.status = status


class App:
    def __init__(self, problem_root, history_path, data_root, *, clock=time.time, start_worker=True):
        self.clock = clock
        self.lock = threading.RLock()
        self.contest = parse_contest(Path(history_path))
        self.problems, fingerprint = load_problems(Path(problem_root))
        if set(self.problems) != set(self.contest.problems):
            raise ValueError("题包题号集合与历史文件不匹配")
        self.input_id = hashlib.sha256((fingerprint + Path(history_path).read_text(encoding="utf-8-sig")).encode()).hexdigest()
        self.store = Storage(Path(data_root) / "state.sqlite3")
        try:
            self.judge = Judge(self.problems, Path(data_root) / "judge", self.store)
        except Exception:
            self.store.close()
            raise
        if start_worker:
            self.judge.start(self.input_id)

    def session(self, owner, sid=None):
        if sid:
            s = self.store.session(sid, owner, self.input_id)
            if not s:
                raise APIError("会话不存在或无权访问", 403)
            return s
        rows = self.store.sessions(owner, self.input_id)
        return rows[0] if rows else None

    def elapsed(self, session):
        return max(0, self.clock() - session["started"]) if session else 0

    def start(self, owner, name):
        if not isinstance(name, str) or not 1 <= len(name.strip()) <= 100:
            raise APIError("队伍名须为 1–100 个字符")
        with self.lock:
            previous = self.session(owner)
            if previous and self.elapsed(previous) < self.contest.duration:
                return previous
            return self.store.create_session(owner, self.input_id, name.strip(), self.clock(), len(self.contest.teams) + 1)

    def submit(self, owner, payload):
        with self.lock:
            sid = payload.get("session_id")
            if not isinstance(sid, str) or not sid:
                raise APIError("请先开始 VP")
            s = self.session(owner, sid)
            received = self.clock()
            elapsed = max(0, received - s["started"])
            if elapsed >= self.contest.duration:
                raise APIError("比赛已经结束，不能再提交", 409)
            problem, language, source = payload.get("problem"), payload.get("language"), payload.get("source")
            if problem not in self.problems or language not in {"cpp", "python"}:
                raise APIError("题号或语言非法")
            if not isinstance(source, str) or not source.strip() or len(source.encode("utf-8")) > 256 * 1024:
                raise APIError("代码不能为空，且不得超过 256 KiB")
            sid = self.store.add_submission(s["id"], problem, language, source, received, elapsed)
            self.judge.queue.put(sid)
            return {"id": sid}

    def public_submission(self, sub, session, *, source=False):
        result = {k: sub[k] for k in ("id", "problem", "language", "received", "elapsed", "verdict")}
        result["name"] = self.contest.problems[sub["problem"]]["name"]
        result["message"] = sub["message"] if sub["verdict"] in {"CE", "Judge Error"} else ""
        if source:
            result["source"] = sub["source"]
        if self.elapsed(session) >= self.contest.duration:
            result.update(time_ms=sub["time_ms"], memory_kb=sub["memory_kb"])
        return result

    def submission(self, owner, sub_id):
        sub = self.store.get_submission(sub_id)
        if not sub:
            raise APIError("提交不存在", 404)
        s = self.session(owner, sub["session_id"])
        return self.public_submission(sub, s, source=True)

    def state(self, owner, sid=None, final=False):
        s = self.session(owner, sid)
        elapsed = self.elapsed(s)
        local = self.store.submissions(s["id"]) if s else []
        try:
            board = view(self.contest, elapsed, s, local, final)
        except ValueError as exc:
            raise APIError(str(exc), 409) from exc
        own = {}
        if s:
            events = [Event(s["team_id"], x["problem"], x["elapsed"], x["verdict"], x["id"])
                      for x in local if x["elapsed"] < self.contest.duration and x["elapsed"] <= elapsed]
            own = score(self.contest, events, {s["team_id"]: {"name": s["name"]}})[0][0]["cells"]
        return {"contest": {"title": self.contest.title, "duration": self.contest.duration,
                            "historical_teams": len(self.contest.teams), "historical_submissions": len(self.contest.events),
                            "diagnostics": self.contest.diagnostics, "input_id": self.input_id},
                "session": {"id": s["id"], "name": s["name"], "started": s["started"], "team_id": s["team_id"]} if s else None,
                "sessions": [{"id": x["id"], "name": x["name"], "started": x["started"],
                              "ended": self.elapsed(x) >= self.contest.duration}
                             for x in self.store.sessions(owner, self.input_id)],
                "languages": self.judge.languages, "board": board,
                "problems": [p.public(self.contest.problems[pid]["name"]) | {"own": own.get(pid)}
                             for pid, p in self.problems.items()],
                "submissions": [self.public_submission(x, s) for x in local]}

    def close(self):
        self.judge.close()
        self.store.close()
