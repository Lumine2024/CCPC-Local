"""Parse the repository's @-record export without guessing unknown fields."""
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Event:
    team: str
    problem: str
    at: float
    verdict: str
    order: int


@dataclass
class Contest:
    title: str
    duration: int
    problems: dict
    teams: dict
    events: list[Event]
    diagnostics: list[str]


def parse_contest(path: Path) -> Contest:
    declarations, problems, teams, events, attempts = {}, {}, {}, [], set()
    text = path.read_text(encoding="utf-8-sig")
    for line_no, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if not line:
            continue
        try:
            kind, value = line.split(None, 1)
            if kind in {"@contest", "@contlen", "@problems", "@teams", "@submissions"}:
                if kind in declarations:
                    raise ValueError("重复声明")
                declarations[kind] = value.strip('"') if kind == "@contest" else int(value)
            elif kind == "@p":
                pid, rest = value.split(",", 1)
                name, penalty, extra = rest.rsplit(",", 2)
                if not pid or pid in problems or int(penalty) < 0 or not name:
                    raise ValueError("题号重复或题目字段非法")
                problems[pid] = {"id": pid, "name": name, "penalty": int(penalty), "extra": extra}
            elif kind == "@t":
                tid, field1, field2, name = value.split(",", 3)
                if not tid or tid in teams or not name:
                    raise ValueError("队伍 ID 重复或名称为空")
                teams[tid] = {"id": tid, "name": name, "extra": [field1, field2]}
            elif kind == "@s":
                tid, pid, attempt, seconds, verdict = value.split(",")
                attempt, seconds = int(attempt), int(seconds)
                if attempt < 1 or seconds < 0 or verdict not in {"OK", "RJ"}:
                    raise ValueError("非法时间、提交序号或未知判定")
                key = (tid, pid, attempt)
                if key in attempts:
                    raise ValueError("重复提交事件")
                attempts.add(key)
                events.append(Event(tid, pid, seconds, "AC" if verdict == "OK" else "RJ", line_no))
            else:
                raise ValueError(f"不支持的记录 {kind}")
        except (ValueError, TypeError) as exc:
            raise ValueError(f"{path}:{line_no}: {exc}") from exc
    required = {"@contest", "@contlen", "@problems", "@teams", "@submissions"}
    if required - declarations.keys():
        raise ValueError(f"{path}: 缺少声明 {sorted(required - declarations.keys())}")
    if not declarations["@contest"] or declarations["@contlen"] <= 0 or not teams or not problems:
        raise ValueError(f"{path}: 比赛名称、时长、题目或队伍为空")
    for key, actual in [("@problems", len(problems)), ("@teams", len(teams)), ("@submissions", len(events))]:
        if declarations[key] != actual:
            raise ValueError(f"{path}: {key} 声明 {declarations[key]}，实际 {actual}")
    for e in events:
        if e.team not in teams or e.problem not in problems:
            raise ValueError(f"{path}:{e.order}: 提交引用未知队伍或题目")
    duration = declarations["@contlen"] * 60
    excluded = sum(e.at >= duration for e in events)
    diagnostics = [f"保留 {excluded} 条结束时或之后的历史事件，不计入比赛成绩。"] if excluded else []
    return Contest(declarations["@contest"], duration, problems, teams,
                   sorted(events, key=lambda e: (e.at, e.order)), diagnostics)
