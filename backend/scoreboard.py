"""The public scoreboard is a projection, never raw contest events."""
import math
from .contest_parser import Contest, Event

PENDING = {"Queued", "Compiling", "Running"}
PENALIZED = {"RJ", "WA", "TLE", "MLE", "RE", "OLE"}
FREEZE = 14400


def threshold(total: int) -> int:
    return min(50, math.ceil(total / 5))


def score(contest: Contest, events: list[Event], teams: dict) -> tuple[list[dict], dict]:
    cells = {tid: {} for tid in teams}
    counts = {pid: 0 for pid in contest.problems}
    for e in sorted(events, key=lambda e: (e.at, e.order)):
        if e.verdict in PENDING:
            continue
        cell = cells[e.team].setdefault(e.problem, {"solved": False, "wrong": 0, "at": None})
        if cell["solved"]:
            continue
        if e.verdict == "AC":
            cell.update(solved=True, at=int(e.at))
            counts[e.problem] += 1
        elif e.verdict in PENALIZED:
            cell["wrong"] += 1
    rows = []
    for tid, team in teams.items():
        penalty = sum(c["at"] // 60 + c["wrong"] * contest.problems[p]["penalty"]
                      for p, c in cells[tid].items() if c["solved"])
        rows.append({"id": tid, "name": team["name"], "solved": sum(c["solved"] for c in cells[tid].values()),
                     "penalty": penalty, "cells": cells[tid]})
    rows.sort(key=lambda r: (-r["solved"], r["penalty"], r["id"]))
    prev, rank = None, 0
    for i, row in enumerate(rows, 1):
        key = (row["solved"], row["penalty"])
        if key != prev:
            rank = i
        row["rank"], prev = rank, key
    return rows, counts


def view(contest: Contest, elapsed: float, session: dict | None, local: list[dict], final=False) -> dict:
    if final and (not session or elapsed < contest.duration):
        raise ValueError("比赛结束后才能查看最终结果")
    ended = elapsed >= contest.duration and session is not None
    frozen = elapsed >= FREEZE and contest.duration >= FREEZE and session is not None
    snapshot = contest.duration if final else min(elapsed, FREEZE if frozen else contest.duration)
    historical = [e for e in contest.events if e.at < contest.duration and
                  (e.at < snapshot if (frozen or final or ended) else e.at <= snapshot)]
    teams = dict(contest.teams)
    events = list(historical)
    pending = 0
    if session:
        teams[session["team_id"]] = {"name": session["name"]}
        for sub in local:
            if sub["elapsed"] < contest.duration and (
                    sub["elapsed"] < snapshot if (frozen or final or ended) else sub["elapsed"] <= snapshot):
                if sub["verdict"] in PENDING:
                    pending += 1
                events.append(Event(session["team_id"], sub["problem"], sub["elapsed"], sub["verdict"],
                                    1_000_000_000 + sub["id"]))
    rows, counts = score(contest, events, teams)
    total = session["total"] if session else len(contest.teams) + 1
    visible = list(contest.problems) if frozen or final else [p for p, n in counts.items() if n >= threshold(total)]
    visible_set = set(visible)
    for row in rows:
        row["other"] = sum(c["solved"] for p, c in row["cells"].items() if p not in visible_set)
        row["cells"] = {p: c for p, c in row["cells"].items() if p in visible_set}
        row["local"] = bool(session and row["id"] == session["team_id"])
    return {"session_id": session["id"] if session else None, "elapsed": int(elapsed),
            "snapshot": int(snapshot), "frozen": frozen and not final, "final": final,
            "ended": ended, "pending": pending, "threshold": threshold(total), "total": total,
            "visible": visible, "counts": {p: n if p in visible_set else None for p, n in counts.items()},
            "rows": rows}
