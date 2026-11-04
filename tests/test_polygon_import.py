"""Importer regressions: real generated I/O, unsafe ZIPs, and shifted time windows."""
import json
import hashlib
from pathlib import Path
import shutil
import tempfile
import unittest
import zipfile

from backend.problems import load_problems
from scripts.polygon_to_workspace import convert, extract_zip, problem_map
from scripts.standings_to_history import (accepted_minute, normalize_ac, rejected_count, insert_times,
                                         reconstruct_events, convert as convert_standings)
from backend.contest_parser import parse_contest
from backend.contest_parser import Contest, Event
from backend.scoreboard import score


class PolygonImportTests(unittest.TestCase):
    def test_zip_traversal_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name in ['../escape', 'C:/escape', '/escape', 'ok/../../escape', '..\\escape']:
                with self.subTest(name=name):
                    with zipfile.ZipFile(root / 'bad.zip', 'w') as z:
                        z.writestr(name, 'unsafe')
                    with self.assertRaises(ValueError):
                        extract_zip(root / 'bad.zip', root / 'out')
            self.assertFalse((root / 'escape').exists())

    def test_zip_symlink_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with zipfile.ZipFile(root / 'bad.zip', 'w') as z:
                entry = zipfile.ZipInfo('link')
                entry.create_system = 3
                entry.external_attr = (0o120777 << 16)
                z.writestr(entry, '../outside')
            with self.assertRaises(ValueError):
                extract_zip(root / 'bad.zip', root / 'out')

    def test_contest_order_comes_from_xml_not_folder_names(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for slug in ['zebra', 'alpha']:
                folder = root / slug
                folder.mkdir()
                (folder / 'problem.xml').write_text(f'<problem url="/{slug}"><names><name value="{slug}"/></names></problem>')
            (root / 'contest.xml').write_text('<contest><names><name value="contest"/></names><problems>'
                                             '<problem index="a" url="/zebra"/><problem index="b" url="/alpha"/>'
                                             '</problems></contest>')
            _, mapping = problem_map(root)
            self.assertEqual([(pid, p.name) for pid, p, _ in mapping], [('A', 'zebra'), ('B', 'alpha')])

    @unittest.skipUnless(shutil.which('g++'), 'g++ is required for the end-to-end importer test')
    def test_generated_input_and_answer_are_materialized_and_loadable(self):
        with tempfile.TemporaryDirectory(prefix='polygon import spaces ') as tmp:
            root = Path(tmp)
            xml = '''<problem short-name="fixture" url="/fixture"><names><name language="english" value="Fixture"/></names>
              <judging input-file="" output-file=""><testset name="tests"><time-limit>1000</time-limit>
              <memory-limit>268435456</memory-limit><test-count>2</test-count><input-path-pattern>tests/%02d</input-path-pattern>
              <answer-path-pattern>tests/%02d.a</answer-path-pattern><tests><test method="manual" sample="true"/>
              <test method="generated" sample="true" cmd='gen 7 "a b"'/></tests></testset></judging>
              <files><executables><executable><source path="files/gen.cpp" type="cpp.g++17"/></executable></executables></files>
              <assets><checker><source path="files/check.cpp" type="cpp.g++17"/></checker><solutions>
              <solution tag="main"><source path="solutions/main.cpp" type="cpp.g++17"/></solution></solutions></assets></problem>'''
            with zipfile.ZipFile(root / 'package.zip', 'w') as z:
                z.writestr('problem.xml', xml)
                z.writestr('files/testlib.h', '// Fixture has a standalone checker.\n')
                z.writestr('files/gen.cpp', '#include <iostream>\n#include <string>\nint main(int c,char**v){'
                                           'if(c!=3 || std::string(v[2])!="a b")return 1;std::cout<<v[1]<<"\\n";}')
                z.writestr('files/check.cpp', '#include <fstream>\nint main(int c,char**v){int a,b;'
                                             'std::ifstream(v[2])>>a;std::ifstream(v[3])>>b;return a!=b;}')
                z.writestr('solutions/main.cpp', '#include <iostream>\nint main(){int n;std::cin>>n;std::cout<<2*n<<"\\n";}')
                z.writestr('tests/01', '3\n')
                z.writestr('tests/01.a', '6\n')
                # A shipped executable must never be invoked.
                z.writestr('files/gen.exe', 'this is not an executable')
            output = root / 'workspaces'
            report = convert(root / 'package.zip', output)
            problems, _ = load_problems(output / 'problems')
            self.assertTrue(report['success'])
            self.assertEqual(report['loadableCaseCount'], 2)
            self.assertEqual(problems['A'].cases[1].input.read_text().strip(), '7')
            self.assertEqual(problems['A'].cases[1].answer.read_text().strip(), '14')
            for fence, value in [('input1', '3'), ('output1', '6'), ('input2', '7'), ('output2', '14')]:
                self.assertIn(f'```{fence}\n{value}\n```', problems['A'].statement)
            self.assertFalse((output / 'problems/A/polygon/files/gen.exe').exists())
            manifest = json.loads((output / 'problems/A/exported-tests/manifest.json').read_text())
            self.assertEqual(manifest['cases'][0]['group'], 'sample')
            self.assertEqual(report['problems'][0]['generatedInputs'], 1)
            self.assertEqual(report['problems'][0]['generatedAnswers'], 1)
            with self.assertRaises(ValueError):
                convert(root / 'package.zip', output)


class StandingsTimeTests(unittest.TestCase):
    def test_pdf_verified_history_preserves_merged_names_and_skips_continuation_rows(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            p = root / 'workspace/problems/A'
            for folder in ['docs', 'src/checker', 'include', 'exported-tests/secret']:
                (p / folder).mkdir(parents=True, exist_ok=True)
            for name, text in [('docs/statement.md', '# Fixture'), ('src/checker/checker.cpp', '// checker'),
                               ('include/testlib.h', '// testlib'), ('exported-tests/secret/one.in', '1'),
                               ('exported-tests/secret/one.ans', '2')]:
                (p / name).write_text(text)
            (p / 'config.json').write_text(json.dumps({'title': 'Fixture', 'interactive': False, 'standard': 'gnu++23',
                'timeLimitMs': 1000, 'memoryLimitMb': 256, 'statement': 'docs/statement.md', 'checker': 'src/checker/checker.cpp'}))
            (p / 'exported-tests/manifest.json').write_text(json.dumps({'interactive': False, 'caseCount': 1, 'cases': [
                {'name': 'one', 'group': 'secret', 'input': 'secret/one.in', 'answer': 'secret/one.ans'}]}))
            (root / 'workspace/conversion-report.json').write_text(json.dumps({'title': 'Fixture'}))
            with zipfile.ZipFile(root / 'board.xlsx', 'w') as z:
                z.writestr('xl/workbook.xml', '<workbook xmlns:r="urn:relationships"><sheets><sheet name="Sheet1" r:id="rId1"/></sheets></workbook>')
                z.writestr('xl/_rels/workbook.xml.rels', '<Relationships><Relationship Id="rId1" Target="worksheets/sheet1.xml"/></Relationships>')
                z.writestr('xl/styles.xml', '<styleSheet><fills><fill/><fill><patternFill><fgColor rgb="0060E760"/></patternFill></fill></fills>'
                                          '<cellXfs><xf fillId="0"/><xf fillId="1"/></cellXfs></styleSheet>')
                z.writestr('xl/worksheets/sheet1.xml', '<worksheet><sheetData>'
                    '<row r="1"><c r="B1" t="inlineStr"><is><t>TEAM</t></is></c></row>'
                    '<row r="2"><c r="B2" t="inlineStr"><is><t>Alpha</t></is></c><c r="H2" s="1"><v>10</v></c></row>'
                    '<row r="3"><c r="B3" t="inlineStr"><is><t>TEAM</t></is></c></row>'
                    '<row r="4"><c r="A4" t="inlineStr"><is><t>Beta\n2\nUESTC</t></is></c><c r="H4" s="1"><v>100</v></c></row>'
                    '<row r="5"><c r="A5" t="inlineStr"><is><t>UESTC</t></is></c></row>'
                    '<row r="6"><c r="A6" t="inlineStr"><is><t>1\n3\nUESTC</t></is></c><c r="H6" s="1"><v>490</v></c></row>'
                    '<row r="7"><c r="B7" t="inlineStr"><is><t>SUMMARY</t></is></c></row>'
                    '</sheetData></worksheet>')
            layout = {'firstTeamRow': 2, 'headerRows': [1, 3], 'ignoredRows': [5], 'teamColumns': ['B:F'],
                      'mergedTeamAndRankColumn': 'A', 'stopText': 'SUMMARY', 'acceptedColors': ['60E760'], 'problemColumns': {'A': 'H:I'}}
            verified = {'teamCount': 3, 'workbookSha256': hashlib.sha256((root / 'board.xlsx').read_bytes()).hexdigest(),
                        'accepted': [{'sourceRow': row, 'problem': 'A', 'acceptedMinute': minute, 'pdfPage': 1}
                                     for row, minute in [(2, 10), (4, 100), (6, 500)]]}
            result = convert_standings(root / 'board.xlsx', root / 'workspace', layout, verified_ac=verified)
            contest = parse_contest(root / 'workspace/contest.txt')
            self.assertEqual(result['teamCount'], 3)
            self.assertEqual(result['pdfCorrectionCount'], 1)
            self.assertEqual(set(contest.teams), {'xlsx-0002', 'xlsx-0004', 'xlsx-0006'})
            self.assertEqual(contest.teams['xlsx-0006']['name'], '1 | UESTC')
            self.assertEqual([e.at for e in contest.events], [1200, 1200, 1200])
            for record, tries in zip(verified['accepted'], [3, 2, 1]):
                record['reportedTries'] = tries
            result = convert_standings(root / 'board.xlsx', root / 'workspace', layout, verified_ac=verified,
                                       rj_distribution='uniform')
            contest = parse_contest(root / 'workspace/contest.txt')
            self.assertEqual(result['exportedACCount'], 3)
            self.assertEqual(result['exportedRJCount'], 3)
            rows, _ = score(contest, contest.events, contest.teams)
            self.assertEqual({r['id']: r['penalty'] for r in rows},
                             {'xlsx-0002': 60, 'xlsx-0004': 40, 'xlsx-0006': 20})
            verified['workbookSha256'] = 'incorrect'
            with self.assertRaises(ValueError):
                convert_standings(root / 'board.xlsx', root / 'workspace', layout, verified_ac=verified)

    def test_elapsed_window_is_relative_to_each_team(self):
        start, records = normalize_ac([{'acceptedMinute': m} for m in [719, 440, 441, 500]])
        self.assertEqual(start, 420)
        self.assertEqual([r['elapsedSeconds'] for r in records], [299 * 60, 20 * 60, 21 * 60, 80 * 60])
        self.assertTrue(all(r['withinWindow'] for r in records))

    def test_five_hour_boundary_excluded(self):
        _, records = normalize_ac([{'acceptedMinute': m} for m in [100, 379, 380, 381]])
        self.assertEqual([r['withinWindow'] for r in records], [True, True, False, False])

    def test_early_first_ac_keeps_requested_formula(self):
        start, records = normalize_ac([{'acceptedMinute': 4}])
        self.assertEqual(start, -16)
        self.assertEqual(records[0]['elapsedSeconds'], 1200)

    def test_unsolved_team_has_unknown_start(self):
        self.assertEqual(normalize_ac([]), (None, []))

    def test_noisy_or_merged_minutes_are_not_guessed(self):
        self.assertEqual(accepted_minute('  529\n8 tries'), (529, 8))
        self.assertEqual(accepted_minute('565\ntries'), (565, None))
        for value in ['445      634\n2 tries 3 tries', '1 try', '52S\n1 try', 'white 19']:
            self.assertIsNone(accepted_minute(value))


class RejectedReconstructionTests(unittest.TestCase):
    def test_uniform_failures_restore_scoring_penalty(self):
        accepted = [{'problem': 'A', 'elapsedSeconds': 1200, 'reportedTries': 3},
                    {'problem': 'B', 'elapsedSeconds': 3600, 'reportedTries': 4}]
        events, unknown = reconstruct_events(accepted, [], {'A', 'B'}, distribution='uniform')
        self.assertFalse(unknown)
        self.assertEqual([e['at'] for e in events if e['problem'] == 'A'], [400, 800, 1200])
        self.assertEqual([e['at'] for e in events if e['problem'] == 'B'], [1800, 2400, 3000, 3600])
        contest = Contest('test', 18000, {p: {'penalty': 20} for p in ['A', 'B']}, {'t': {'name': 'Team'}}, [], [])
        rows, _ = score(contest, [Event('t', e['problem'], e['at'], e['verdict'], i) for i, e in enumerate(events)], contest.teams)
        self.assertEqual(rows[0]['penalty'], 180)
        self.assertEqual(rows[0]['cells']['B']['wrong'], 3)

    def test_exponential_changes_timing_but_keeps_rejection_count(self):
        uniform = insert_times(1200, 3600, 4)
        exponential = insert_times(1200, 3600, 4, 'exponential')
        self.assertEqual(len(exponential), 4)
        self.assertEqual(exponential, sorted(exponential))
        self.assertTrue(all(1200 <= t < 3600 for t in exponential))
        self.assertNotEqual(uniform, exponential)

    def test_simultaneous_ac_use_previous_strictly_earlier_ac(self):
        events, _ = reconstruct_events([{'problem': p, 'elapsedSeconds': 1200, 'reportedTries': n}
                                        for p, n in [('A', 2), ('B', 3)]], [], {'A', 'B'}, distribution='uniform')
        self.assertEqual([e['at'] for e in events if e['verdict'] == 'RJ'], [400, 600, 800])

    def test_failures_before_late_ac_are_cropped_after_interpolation(self):
        events, _ = reconstruct_events([{'problem': 'A', 'elapsedSeconds': 1200, 'reportedTries': 1},
                                        {'problem': 'B', 'elapsedSeconds': 18000, 'reportedTries': 3}], [],
                                       {'A', 'B'}, distribution='uniform')
        inside = [e for e in events if e['withinWindow']]
        self.assertEqual([e['verdict'] for e in inside], ['AC', 'RJ', 'RJ'])
        self.assertFalse(events[-1]['withinWindow'])
        self.assertEqual(events[-1]['verdict'], 'AC')

    def test_unsolved_attempts_pile_at_end_without_solved_penalty(self):
        events, unknown = reconstruct_events([], [{'problem': 'A', 'reportedTries': 4}], {'A'}, distribution='uniform')
        self.assertFalse(unknown)
        self.assertEqual([e['at'] for e in events], [17999] * 4)
        contest = Contest('test', 18000, {'A': {'penalty': 20}}, {'t': {'name': 'Team'}}, [], [])
        rows, _ = score(contest, [Event('t', 'A', e['at'], 'RJ', i) for i, e in enumerate(events)], contest.teams)
        self.assertEqual(rows[0]['penalty'], 0)
        self.assertEqual(rows[0]['cells']['A']['wrong'], 4)

    def test_zero_second_ac_preserves_failure_order(self):
        events, _ = reconstruct_events([{'problem': 'A', 'elapsedSeconds': 0, 'reportedTries': 4}], [], {'A'}, distribution='uniform')
        self.assertEqual([e['at'] for e in events], [0] * 4)
        self.assertEqual([e['verdict'] for e in events], ['RJ', 'RJ', 'RJ', 'AC'])

    def test_missing_counts_and_unsupported_problem_are_not_fabricated(self):
        events, missing = reconstruct_events([{'problem': 'A', 'elapsedSeconds': 1200, 'reportedTries': None}],
                                             [{'problem': 'B', 'reportedTries': None}, {'problem': 'M', 'reportedTries': 10}],
                                             {'A', 'B'}, distribution='uniform')
        self.assertEqual(len(events), 1)
        self.assertEqual(len(missing), 2)
        self.assertEqual(events[0]['verdict'], 'AC')
        self.assertEqual(rejected_count('12 tries'), 12)
        self.assertIsNone(rejected_count('2 tries 3 tries'))


if __name__ == '__main__':
    unittest.main()
