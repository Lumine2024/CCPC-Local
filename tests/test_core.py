import json
from pathlib import Path
import tempfile
import unittest

from backend.contest_parser import Contest, Event, parse_contest
from backend.problems import inside, load_problems
from backend.scoreboard import score, threshold, view

ROOT = Path(__file__).resolve().parents[1]


def fixture(root):
    """Tiny portable skill package for API and import tests, never a fake judge."""
    p = root / "problems" / "A"
    for d in ("docs/assets", "src/checker", "include", "exported-tests/sample"):
        (p / d).mkdir(parents=True, exist_ok=True)
    cfg = {"interactive": False, "title": "A toy", "timeLimitMs": 1000, "memoryLimitMb": 256,
           "standard": "gnu++20", "statement": "docs/statement.md", "checker": "src/checker/checker.cpp"}
    (p / "config.json").write_text(json.dumps(cfg))
    (p / "docs/statement.md").write_text("# A\n\n![toy](assets/toy.png)\n\n```input1\n1\n```\n\n```output1\n1\n```\n")
    (p / "docs/assets/toy.png").write_bytes(b"toy fixture")
    (p / "include/testlib.h").write_text("fixture")
    (p / "src/checker/checker.cpp").write_text("int main(){return 0;}")
    (p / "exported-tests/sample/one.in").write_text("1\n")
    (p / "exported-tests/sample/one.ans").write_text("1\n")
    (p / "exported-tests/manifest.json").write_text(json.dumps({"interactive": False, "caseCount": 1,
        "workspace": "C:/old/machine", "outputRoot": "C:/old/output", "cases": [{"name": "one", "group": "sample",
        "input": "sample\\one.in", "answer": "sample\\one.ans"}]}))
    history = root / "contest.txt"
    history.write_text('@contest "Toy, with comma"\n@contlen 300\n@problems 1\n@teams 1\n@submissions 1\n@p A,A, comma,20,0\n@t 1,0,1,队伍, one\n@s 1,A,1,300,OK\n', encoding="utf-8")
    return p.parent, history


def contest(n=250, duration=18000, problems="ABCDEFGHIJKL"):
    return Contest("Synthetic", duration, {p: {"id": p, "name": p, "penalty": 20} for p in problems},
                   {str(i): {"name": f"Team {i}"} for i in range(n)}, [], [])


class RulesTests(unittest.TestCase):
    def test_threshold_rounding_and_cap(self):
        self.assertEqual([threshold(n) for n in (1, 5, 6, 249, 250, 389)], [1, 1, 2, 50, 50, 50])

    def test_exact_threshold_and_deduplicate(self):
        c = contest(problems="AB")
        c.events = [Event(str(i), "A", 60, "AC", i) for i in range(49)]
        c.events += [Event("0", "A", 61, "AC", 100)]
        self.assertIsNone(view(c, 100, None, [])["counts"]["A"])
        c.events.append(Event("49", "A", 101, "AC", 101))
        b = view(c, 101, None, [])
        self.assertEqual(b["visible"], ["A"])
        self.assertEqual(b["counts"], {"A": 50, "B": None})

    def test_original_five_problem_example(self):
        c = contest(n=300)
        counts = dict(zip(c.problems, [5, 20, 100, 170, 42, 38, 220, 300, 72, 68, 12, 0]))
        for p, n in counts.items():
            c.events.extend(Event(str(i), p, 100, "AC", len(c.events) + i) for i in range(n))
        # Team zero also solves C/D; A/B/E remain hidden.
        b = view(c, 7200, None, [])
        row = next(r for r in b["rows"] if r["id"] == "0")
        self.assertEqual(b["visible"], list("CDGHIJ"))
        self.assertEqual(row["other"], 5)  # A/B/E/F/K in this complete generated table
        self.assertFalse(set(row["cells"]) & set("ABEFKL"))
        c.events = [e for e in c.events if e.team != "299"]
        c.events += [Event("299", p, 100, "AC", 9999+i) for i, p in enumerate("ABCDE")]
        row = next(r for r in view(c, 7200, None, [])["rows"] if r["id"] == "299")
        self.assertEqual(row["solved"], 5)
        self.assertEqual(row["other"], 3)
        self.assertEqual(set(row["cells"]), {"C", "D"})

    def test_icpc_penalty_and_ce_exemption(self):
        c = contest(n=2, problems="AB")
        c.problems["A"]["penalty"] = 30
        events = [Event("0", "A", 30, "CE", 1), Event("0", "A", 40, "WA", 2),
                  Event("0", "A", 50, "Judge Error", 3), Event("0", "A", 179, "AC", 4),
                  Event("0", "A", 200, "AC", 5), Event("0", "B", 300, "RJ", 6)]
        rows, counts = score(c, events, c.teams)
        self.assertEqual((rows[0]["solved"], rows[0]["penalty"], counts["A"]), (1, 32, 1))
        self.assertEqual(rows[0]["cells"]["A"]["wrong"], 1)

    def test_ties_share_rank(self):
        c = contest(n=3, problems="A")
        rows, _ = score(c, [Event("0", "A", 60, "AC", 1), Event("1", "A", 60, "AC", 2)], c.teams)
        self.assertEqual([r["rank"] for r in rows], [1, 1, 3])

    def test_freeze_boundary_and_final(self):
        c = contest(n=2, problems="AB")
        c.events = [Event("0", "A", 14399, "AC", 1), Event("1", "B", 14400, "AC", 2),
                    Event("1", "A", 18000, "AC", 3)]
        s = {"id": "session", "name": "VP", "team_id": "vp", "total": 3}
        local = [{"id": 1, "problem": "B", "elapsed": 14400, "verdict": "AC"}]
        before = view(c, 14399, s, local)
        frozen = view(c, 14400, s, local)
        after = view(c, 17999, s, local)
        self.assertFalse(before["frozen"])
        self.assertEqual(frozen["counts"], {"A": 1, "B": 0})
        self.assertEqual(after["rows"], frozen["rows"])
        self.assertEqual(view(c, 18000, s, local, True)["counts"], {"A": 1, "B": 2})
        with self.assertRaises(ValueError): view(c, 17999, s, local, True)

    def test_delayed_prefreeze_judgement(self):
        c = contest(n=1, problems="A")
        s = {"id": "session", "name": "VP", "team_id": "vp", "total": 2}
        local = [{"id": 1, "problem": "A", "elapsed": 14399, "verdict": "Running"}]
        self.assertEqual(view(c, 15000, s, local)["pending"], 1)
        local[0]["verdict"] = "AC"
        b = view(c, 15000, s, local)
        self.assertEqual((b["pending"], b["counts"]["A"]), (0, 1))

    def test_short_contest_and_future_events(self):
        c = contest(n=1, duration=600, problems="A")
        c.events = [Event("0", "A", 599, "AC", 1)]
        s = {"id": "session", "name": "VP", "team_id": "vp", "total": 2}
        self.assertIsNone(view(c, 300, s, [])["counts"]["A"])
        self.assertFalse(view(c, 600, s, [])["frozen"])
        self.assertEqual(view(c, 600, s, [], True)["counts"]["A"], 1)


class ImportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.problems, self.history = fixture(self.root)

    def tearDown(self): self.temp.cleanup()

    def test_commas_bom_crlf(self):
        self.history.write_text('\ufeff' + self.history.read_text(encoding="utf-8").replace("\n", "\r\n"), encoding="utf-8")
        c = parse_contest(self.history)
        self.assertEqual(c.teams["1"]["name"], "队伍, one")
        self.assertEqual(c.problems["A"]["name"], "A, comma")

    def test_count_mismatch(self):
        self.history.write_text(self.history.read_text(encoding="utf-8").replace("@teams 1", "@teams 2"), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "@teams"): parse_contest(self.history)

    def test_unknown_verdict_and_reference(self):
        original = self.history.read_text(encoding="utf-8")
        for replacement in ("@s 1,A,1,300,AC", "@s 2,A,1,300,OK"):
            self.history.write_text(original.replace("@s 1,A,1,300,OK", replacement), encoding="utf-8")
            with self.assertRaises(ValueError): parse_contest(self.history)

    def test_duplicate_event(self):
        text = self.history.read_text(encoding="utf-8").replace("@submissions 1", "@submissions 2")
        self.history.write_text(text + "@s 1,A,1,300,OK\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "重复提交"): parse_contest(self.history)

    def test_windows_manifest_and_assets(self):
        loaded, fingerprint = load_problems(self.problems)
        self.assertEqual(len(loaded["A"].cases), 1)
        self.assertTrue(loaded["A"].cases[0].input.is_file())
        self.assertIn("assets/toy.png", loaded["A"].assets)
        self.assertEqual(len(fingerprint), 64)

    def test_traversal_missing_and_interactive(self):
        for rel in ("../contest.txt", "/contest.txt", "C:/secret", "missing.txt"):
            with self.assertRaises(ValueError): inside(self.problems, rel)
        cfg = self.problems / "A/config.json"
        data = json.loads(cfg.read_text()); data["interactive"] = True; cfg.write_text(json.dumps(data))
        with self.assertRaisesRegex(ValueError, "非交互"): load_problems(self.problems)

    def test_input_identity_changes_with_answers(self):
        _, first = load_problems(self.problems)
        (self.problems / "A/exported-tests/sample/one.ans").write_text("2\n")
        _, second = load_problems(self.problems)
        self.assertNotEqual(first, second)


class RealDataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.c = parse_contest(ROOT / "tests/contest.txt")
        cls.problems, _ = load_problems(ROOT / "tests/ICPC-Shaanxi-2025-National-Invitational-Contest")

    def test_import_counts(self):
        self.assertEqual((len(self.c.problems), len(self.c.teams), len(self.c.events)), (13, 388, 3537))
        self.assertEqual(sum(e.at >= self.c.duration for e in self.c.events), 186)
        self.assertEqual(sum(len(p.cases) for p in self.problems.values()), 352)

    def test_four_hour_baseline(self):
        s = {"id": "s", "team_id": "vp", "name": "VP", "total": 389}
        self.assertEqual(view(self.c, 14400, s, [])["counts"], dict(zip("ABCDEFGHIJKLM", [290, 6, 0, 0, 1, 2, 253, 0, 182, 108, 14, 386, 83])))

    def test_samples_match_markdown(self):
        import re
        for pid, p in self.problems.items():
            blocks = dict(re.findall(r"^```((?:input|output)\d*)\s*\n(.*?)^```", p.statement, re.M | re.S))
            for i, case in enumerate(c for c in p.cases if c.group == "sample"):
                for kind, file in [("input", case.input), ("output", case.answer)]:
                    self.assertEqual(blocks[kind+str(i+1)].strip(), file.read_text().strip(), (pid, kind))
