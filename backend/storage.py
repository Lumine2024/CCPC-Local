"""SQLite persistence; every read or mutation is serialized and transactional."""
import sqlite3
import threading
import uuid
from pathlib import Path


class Storage:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.lock = threading.RLock()
        self.db = sqlite3.connect(path, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA foreign_keys=ON")
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS sessions (
              id TEXT PRIMARY KEY, owner TEXT NOT NULL, input_id TEXT NOT NULL,
              name TEXT NOT NULL, team_id TEXT NOT NULL, started REAL NOT NULL, total INTEGER NOT NULL);
            CREATE INDEX IF NOT EXISTS sessions_owner ON sessions(owner,input_id,started);
            CREATE TABLE IF NOT EXISTS submissions (
              id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT NOT NULL REFERENCES sessions(id),
              problem TEXT NOT NULL, language TEXT NOT NULL, source TEXT NOT NULL,
              received REAL NOT NULL, elapsed REAL NOT NULL, verdict TEXT NOT NULL,
              message TEXT NOT NULL DEFAULT '', time_ms INTEGER, memory_kb INTEGER,
              checked INTEGER NOT NULL DEFAULT 0);
        """)
        with self.db:
            self.db.execute("INSERT OR IGNORE INTO settings VALUES ('secret', ?)", (uuid.uuid4().hex + uuid.uuid4().hex,))
        self.secret = self.db.execute("SELECT value FROM settings WHERE key='secret'").fetchone()[0]

    def sessions(self, owner, input_id):
        with self.lock:
            return [dict(r) for r in self.db.execute(
                "SELECT * FROM sessions WHERE owner=? AND input_id=? ORDER BY started DESC", (owner, input_id))]

    def session(self, sid, owner, input_id):
        with self.lock:
            row = self.db.execute("SELECT * FROM sessions WHERE id=? AND owner=? AND input_id=?", (sid, owner, input_id)).fetchone()
            return dict(row) if row else None

    def create_session(self, owner, input_id, name, started, total):
        sid = uuid.uuid4().hex
        with self.lock, self.db:
            self.db.execute("INSERT INTO sessions VALUES (?,?,?,?,?,?,?)",
                            (sid, owner, input_id, name, f"vp:{sid}", started, total))
        return self.session(sid, owner, input_id)

    def submissions(self, sid):
        with self.lock:
            return [dict(r) for r in self.db.execute("SELECT * FROM submissions WHERE session_id=? ORDER BY id DESC", (sid,))]

    def get_submission(self, sub_id):
        with self.lock:
            row = self.db.execute("SELECT * FROM submissions WHERE id=?", (sub_id,)).fetchone()
            return dict(row) if row else None

    def add_submission(self, sid, problem, language, source, received, elapsed):
        with self.lock, self.db:
            cursor = self.db.execute("""INSERT INTO submissions
                (session_id,problem,language,source,received,elapsed,verdict) VALUES (?,?,?,?,?,?,'Queued')""",
                (sid, problem, language, source, received, elapsed))
            return cursor.lastrowid

    def update(self, sub_id, **fields):
        assert set(fields) <= {"verdict", "message", "time_ms", "memory_kb", "checked"}
        with self.lock, self.db:
            self.db.execute("UPDATE submissions SET " + ",".join(f"{k}=?" for k in fields) + " WHERE id=?",
                            (*fields.values(), sub_id))

    def recover(self, input_id):
        with self.lock, self.db:
            rows = self.db.execute("""SELECT s.id FROM submissions s JOIN sessions v ON s.session_id=v.id
                WHERE v.input_id=? AND s.verdict IN ('Queued','Compiling','Running') ORDER BY s.id""", (input_id,)).fetchall()
            ids = [r[0] for r in rows]
            for sid in ids:
                self.db.execute("UPDATE submissions SET verdict='Queued',message='',checked=0 WHERE id=?", (sid,))
            return ids

    def close(self):
        with self.lock:
            self.db.close()
