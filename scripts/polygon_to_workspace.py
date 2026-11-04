"""Materialize Polygon contest/problem ZIPs as CCPC Local workspaces.

Run from any directory; requires this repository's psutil dependency and g++.
Only sources are compiled: shipped executables and shell scripts are never run.
Generated tests use the XML command verbatim (no extra test-index seed).
Interactive problems are archived separately, without invented static answers.
"""
import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
from html.parser import HTMLParser
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import shlex
import shutil
import sys
import tempfile
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.problems import load_problems
from backend.runner import run


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def file_sha256(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def relative_file(root, name):
    """Reject absolute/traversal paths in XML as well as in ZIP members."""
    clean = PurePosixPath(name.replace("\\", "/"))
    if clean.is_absolute() or ".." in clean.parts or ":" in name or not clean.parts:
        raise ValueError(f"Unsafe package path: {name}")
    path = root.joinpath(*clean.parts).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError(f"Path escapes package: {name}")
    return path


def extract_zip(archive, dest):
    with zipfile.ZipFile(archive) as z:
        seen = set()
        for entry in z.infolist():
            if (entry.external_attr >> 16) & 0o170000 == 0o120000:
                raise ValueError(f"ZIP symlink is unsupported: {entry.filename}")
            target = relative_file(dest, entry.filename)
            key = str(target).casefold() if os.name == "nt" else str(target)
            if key in seen:
                raise ValueError(f"Duplicate ZIP member: {entry.filename}")
            seen.add(key)
            if entry.is_dir():
                target.mkdir(parents=True, exist_ok=True)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                with z.open(entry) as src, target.open("wb") as out:
                    shutil.copyfileobj(src, out)


def problem_map(package):
    xmls = sorted(package.rglob("problem.xml"))
    problems = [(p.parent, ET.parse(p).getroot()) for p in xmls]
    contests = list(package.rglob("contest.xml"))
    if contests:
        if len(contests) != 1:
            raise ValueError("ZIP contains multiple contest.xml files")
        contest = ET.parse(contests[0]).getroot()
        by_url = {x.get("url"): (p, x) for p, x in problems}
        mapping = []
        for item in contest.findall("problems/problem"):
            pid = item.get("index", "").upper()
            if not re.fullmatch(r"[A-Z][A-Z0-9_-]*", pid):
                raise ValueError(f"Invalid contest problem index: {pid}")
            if item.get("url") not in by_url:
                raise ValueError(f"Problem missing from ZIP: {item.get('url')}")
            p, x = by_url[item.get("url")]
            mapping.append((pid, p, x))
        if len({i for i, _, _ in mapping}) != len(mapping):
            raise ValueError("Duplicate problem index")
        return contest.find("names/name").get("value"), mapping
    if len(problems) != 1:
        raise ValueError("ZIP must contain contest.xml or exactly one problem.xml")
    p, x = problems[0]
    return x.find("names/name").get("value"), [("A", p, x)]


class StatementHTML(HTMLParser):
    """Convert the statement body, dropping online scripts and sample duplicates."""
    def __init__(self, package, document, dest):
        super().__init__(convert_charrefs=True)
        self.package, self.document, self.dest = package, document, dest
        self.parts, self.stack, self.active = [], [], False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        classes = attrs.get("class", "").split()
        if tag == "div" and "problem-statement" in classes:
            self.active = True
        inherited = self.stack[-1][1] if self.stack else False
        skip = inherited or tag in {"script", "style"} or bool(set(classes) & {"header", "sample-tests"})
        if tag not in {"br", "img", "meta", "link", "hr", "input"}:
            self.stack.append((tag, skip))
        if not self.active or skip:
            return
        if tag in {"p", "div", "ol", "ul", "table", "tr"}:
            self.parts.append("\n\n" if tag != "tr" else "\n")
        if "section-title" in classes:
            self.parts.append("### ")
        if tag == "li":
            self.parts.append("\n- ")
        if tag == "br":
            self.parts.append("\n")
        if tag in {"b", "strong"}:
            self.parts.append("**")
        if tag in {"i", "em"}:
            self.parts.append("*")
        if tag == "img":
            source = attrs.get("src", "")
            if re.match(r"(?:https?:|data:|//)", source):
                raise ValueError(f"Statement requires offline image: {source}")
            asset = self.document.parent / source
            if not asset.is_file():
                candidates = list((self.package / "statement-sections").rglob(Path(source).name))
                if len(candidates) != 1:
                    raise ValueError(f"Missing/ambiguous statement asset: {source}")
                asset = candidates[0]
            if not asset.resolve().is_relative_to(self.package.resolve()):
                raise ValueError("Statement image escapes problem package")
            name = hashlib.sha256(asset.read_bytes()).hexdigest()[:12] + asset.suffix.lower()
            target = self.dest / "assets" / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(asset, target)
            self.parts.append(f"\n\n![](assets/{name})\n\n")

    def handle_endtag(self, tag):
        if not self.stack:
            return
        # Polygon's HTML sometimes contains unbalanced paragraph tags.
        positions = [i for i, (t, _) in enumerate(self.stack) if t == tag]
        if not positions:
            return
        index = positions[-1]
        skip = self.stack[index][1]
        if self.active and not skip:
            if tag in {"b", "strong"}:
                self.parts.append("**")
            if tag in {"i", "em"}:
                self.parts.append("*")
        del self.stack[index:]

    def handle_data(self, text):
        if self.active and not (self.stack and self.stack[-1][1]):
            self.parts.append(text)


def tex_fragment(text, source_dir, dest):
    """Best-effort conversion; original LaTeX is retained in polygon/."""
    def image(match):
        asset = relative_file(source_dir, match.group(1))
        if not asset.is_file():
            raise ValueError(f"Missing LaTeX image: {asset}")
        target = dest / "assets" / asset.name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(asset, target)
        return f"\n\n![](assets/{asset.name})\n\n"
    text = re.sub(r"\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}", image, text)
    text = re.sub(r"\\(?:begin|end)\{(?:center|itemize|enumerate)\}", "\n", text)
    text = re.sub(r"\\textbf\{([^{}]*)\}", r"**\1**", text)
    text = re.sub(r"\\texttt\{([^{}]*)\}", r"`\1`", text)
    text = re.sub(r"\\textit\{([^{}]*)\}", r"*\1*", text)
    text = text.replace(r"\item", "\n- ")
    text = text.replace(r"\leqslant", r"\leq").replace(r"\geqslant", r"\geq")
    return text.strip()


def render_statement(package, xml, dest, title, cases):
    docs = dest / "docs"
    docs.mkdir(parents=True, exist_ok=True)
    statements = xml.findall("statements/statement")
    statements.sort(key=lambda s: (s.get("language") != "chinese", s.get("type") != "text/html"))
    html = next((s for s in statements if s.get("type") == "text/html"), None)
    mode = "html" if html is not None else "latex-sections"
    if html is not None:
        source = relative_file(package, html.get("path"))
        parser = StatementHTML(package, source, docs)
        parser.feed(source.read_text(encoding=html.get("charset", "utf-8")))
        body = "".join(parser.parts).replace("$$$$$$", "$$").replace("$$$", "$")
        body = re.sub(r"\n[ \t]+", "\n", body)
        body = re.sub(r"\n{3,}", "\n\n", body).strip()
    else:
        language = statements[0].get("language", "english") if statements else "english"
        sections = package / "statement-sections" / language
        chunks = []
        for filename, heading in [("legend", ""), ("input", "输入"), ("output", "输出"), ("notes", "说明")]:
            file = sections / f"{filename}.tex"
            if file.is_file():
                chunks.append((f"### {heading}\n\n" if heading else "") +
                              tex_fragment(file.read_text(encoding="utf-8"), sections, docs))
        body = "\n\n".join(chunks) or "题面尚未转换，请参阅原始 Polygon 包。"
    text = f"# {title}\n\n{body}\n\n"
    for i, case in enumerate((c for c in cases if c["group"] == "sample"), 1):
        data = dest / "exported-tests"
        text += f"### 样例 {i}\n\n```input{i}\n{(data / case['input']).read_text(encoding='utf-8').rstrip()}\n```\n\n"
        if case.get("answer"):
            text += f"```output{i}\n{(data / case['answer']).read_text(encoding='utf-8').rstrip()}\n```\n\n"
    (docs / "statement.md").write_text(text, encoding="utf-8")
    return mode


class Builder:
    def __init__(self, work, compiler, timeout, regenerate=False, workspace_compiler="g++"):
        self.work, self.compiler, self.timeout = work, compiler, timeout
        self.regenerate, self.cache = regenerate, {}
        self.workspace_compiler = workspace_compiler

    def execute(self, command, cwd, output, label, input_file=None, timeout=None):
        output.parent.mkdir(parents=True, exist_ok=True)
        log = self.work / "logs" / f"{label}.err"
        log.parent.mkdir(parents=True, exist_ok=True)
        result = run(command, cwd, output, log, input_file=input_file,
                     timeout_ms=(timeout or self.timeout) * 1000, memory_mb=0,
                     output_limit=512 * 1024 * 1024)
        if result.verdict != "OK":
            raise RuntimeError(f"{label}: {result.verdict} (exit {result.exit_code}); {log}\n" +
                               log.read_text(encoding="utf-8", errors="replace")[-3000:])
        return asdict(result)

    def compile(self, package, source):
        path = relative_file(package, source.get("path"))
        if not path.is_file():
            raise ValueError(f"Missing source: {path}")
        if path in self.cache:
            return self.cache[path]
        if path.suffix == ".py":
            command = [sys.executable, "-I", str(path)]
        elif path.suffix in {".cpp", ".cc", ".cxx", ".c"}:
            key = hashlib.sha256(str(path).encode()).hexdigest()[:16]
            binary = self.work / "bin" / (key + (".exe" if os.name == "nt" else ""))
            binary.parent.mkdir(parents=True, exist_ok=True)
            flags = [self.compiler, "-std=gnu++23", "-O2", "-pipe", "-DONLINE_JUDGE",
                     "-I", str(package / "files"), str(path), "-o", str(binary)]
            if os.name == "nt":
                flags.append("-Wl,--stack,268435456")
            self.execute(flags, package, self.work / "logs" / f"compile-{key}.out", f"compile-{key}", timeout=120)
            command = [str(binary)]
        else:
            raise ValueError(f"Unsupported source language: {source.attrib}")
        self.cache[path] = command
        return command

    def materialize(self, pid, package, xml, dest):
        title = xml.find("names/name").get("value")
        judging = xml.find("judging")
        interactive = xml.find("assets/interactor") is not None
        if judging.get("input-file", "") or judging.get("output-file", ""):
            raise ValueError(f"{pid}: file-based submission I/O is unsupported by CCPC Local")
        sets = judging.findall("testset")
        if len(sets) != 1:
            raise ValueError(f"{pid}: select/merge multiple testsets explicitly before conversion")
        testset = sets[0]
        tests = testset.findall("tests/test")
        if len(tests) != int(testset.findtext("test-count")) or not tests:
            raise ValueError(f"{pid}: invalid/empty test count")
        dest.mkdir(parents=True, exist_ok=True)
        # Keep the original XML, statements, all source siblings and resources.
        # Tests are exported once below; executables are rebuilt locally.
        archive = dest / "polygon"
        shutil.copytree(package, archive, ignore=shutil.ignore_patterns("*.exe", "*.jar", "tests"))
        checker_source = xml.find("assets/checker/source")
        if checker_source is None or checker_source.get("type", "").startswith("java"):
            raise ValueError(f"{pid}: a C++ testlib checker source is required")
        checker_original = relative_file(package, checker_source.get("path"))
        checker_dest = dest / "src/checker/checker.cpp"
        checker_dest.parent.mkdir(parents=True, exist_ok=True)
        # Copy sibling headers/resources too, preserving local checker includes.
        for f in checker_original.parent.iterdir():
            if f.is_file() and f.suffix.lower() in {".h", ".hpp", ".inc"}:
                shutil.copyfile(f, checker_dest.parent / f.name)
        shutil.copyfile(checker_original, checker_dest)
        header = package / "files/testlib.h"
        if not header.is_file():
            found = list(package.rglob("testlib.h"))
            if len(found) != 1:
                raise ValueError(f"{pid}: missing/ambiguous testlib.h")
            header = found[0]
        (dest / "include").mkdir()
        shutil.copyfile(header, dest / "include/testlib.h")
        checker = self.compile(package, checker_source)
        validator_node = xml.find("assets/validators/validator/source")
        validator = self.compile(package, validator_node) if validator_node is not None else None
        main = next((s.find("source") for s in xml.findall("assets/solutions/solution") if s.get("tag") == "main"), None)
        solution = self.compile(package, main) if main is not None and not interactive else None
        executables = {}
        for source in xml.findall("files/executables/executable/source"):
            stem = PurePosixPath(source.get("path")).stem
            if stem in executables:
                raise ValueError(f"{pid}: duplicate executable stem: {stem}")
            executables[stem] = source
        cases, details = [], []
        generated, answers = 0, 0
        for number, test in enumerate(tests, 1):
            group = "sample" if test.get("sample") == "true" else "secret"
            name = f"test-{number:03d}"
            exported = dest / "exported-tests" / group
            exported.mkdir(parents=True, exist_ok=True)
            input_path, answer_path = exported / f"{name}.in", exported / f"{name}.ans"
            original = relative_file(package, testset.findtext("input-path-pattern") % number)
            original_answer = relative_file(package, testset.findtext("answer-path-pattern") % number)
            detail = {"index": number, "method": test.get("method"), "command": test.get("cmd"), "runs": {}}
            if original.is_file() and not (self.regenerate and test.get("method") == "generated"):
                shutil.copyfile(original, input_path)
                detail["inputOrigin"] = "package"
            else:
                if test.get("method") != "generated" or not test.get("cmd"):
                    raise ValueError(f"{pid} test {number}: missing manual input")
                argv = shlex.split(test.get("cmd"), posix=True)
                # Resolve just the program identifier; never use shell=True/eval.
                program = PurePosixPath(argv[0].replace("\\", "/")).name
                if program.endswith(".exe"):
                    program = program[:-4]
                if program not in executables:
                    raise ValueError(f"{pid}: unknown generator {argv[0]}")
                command = self.compile(package, executables[program]) + argv[1:]
                detail["runs"]["generator"] = self.execute(command, package, input_path, f"{pid}-{name}-generator")
                detail["inputOrigin"] = "generator"
                generated += 1
            if input_path.stat().st_size == 0:
                raise ValueError(f"{pid} test {number}: empty input")
            if validator:
                # Polygon validators generally expect strict CRLF on Windows.
                validation_input = input_path
                if os.name == "nt":
                    validation_input = self.work / "validation.in"
                    raw = input_path.read_bytes().replace(b"\r\n", b"\n").replace(b"\r\r\n", b"\n")
                    validation_input.write_bytes(raw.replace(b"\n", b"\r\n"))
                args = ["--testset", testset.get("name", "tests"), "--group", test.get("group", "")]
                detail["runs"]["validator"] = self.execute(validator + args, package, self.work / "logs" / "validator.out",
                                                          f"{pid}-{name}-validator", validation_input)
            case = {"name": name, "group": group, "input": f"{group}/{name}.in", "polygonIndex": number,
                    "method": test.get("method"), "generatorCommand": test.get("cmd")}
            if not interactive:
                if original_answer.is_file() and not (self.regenerate and test.get("method") == "generated"):
                    shutil.copyfile(original_answer, answer_path)
                    detail["answerOrigin"] = "package"
                else:
                    if solution is None:
                        raise ValueError(f"{pid}: missing answer and main solution")
                    detail["runs"]["solution"] = self.execute(solution, package, answer_path, f"{pid}-{name}-answer", input_path)
                    detail["answerOrigin"] = "main-solution"
                    answers += 1
                detail["runs"]["checker"] = self.execute(checker + [str(input_path), str(answer_path), str(answer_path)], package,
                                                        self.work / "logs" / "checker.out", f"{pid}-{name}-checker", timeout=10)
                case["answer"] = f"{group}/{name}.ans"
                case["answerSha256"] = hashlib.sha256(answer_path.read_bytes()).hexdigest()
            case["inputSha256"] = hashlib.sha256(input_path.read_bytes()).hexdigest()
            cases.append(case)
            details.append(detail)
            if number % 10 == 0 or number == len(tests):
                print(f"{pid} {title}: {number}/{len(tests)} tests", flush=True)
        mode = render_statement(package, xml, dest, title, cases)
        config = {"slug": xml.get("short-name"), "title": title, "interactive": interactive,
                  "timeLimitMs": int(testset.findtext("time-limit")),
                  "memoryLimitMb": math.ceil(int(testset.findtext("memory-limit")) / 1024**2),
                  "standard": "gnu++23", "statement": "docs/statement.md", "checker": "src/checker/checker.cpp",
                  "build": {"cppCompiler": self.workspace_compiler, "cppFlags": ["-std={{standard}}", "-O2", "-pipe", "-DONLINE_JUDGE"]},
                  "solutions": [{"name": "main", "path": "polygon/" + main.get("path"),
                                 "language": "python" if main.get("path").endswith('.py') else "cpp", "role": "main"}] if main is not None else [],
                  "polygon": {"url": xml.get("url"), "revision": xml.get("revision"), "index": pid}}
        if interactive:
            config["interactor"] = "polygon/" + xml.find("assets/interactor/source").get("path")
        write_json(dest / "config.json", config)
        write_json(dest / "exported-tests/manifest.json", {"interactive": interactive, "exportMode": "static",
                   "title": title, "caseCount": len(cases), "cases": cases})
        write_json(dest / "conversion.json", {"problem": pid, "title": title, "interactive": interactive,
                   "generatedInputs": generated, "generatedAnswers": answers, "statementConversion": mode, "tests": details})
        (dest / "readme.md").write_text(f"# {pid}. {title}\n\n由 Polygon 包转换，原始源文件见 polygon/。\n\n" +
            ("交互题：保存完整输入、checker、interactor；没有伪造静态答案，当前 CCPC Local 无法加载。\n" if interactive else
             "exported-tests/ 中的输入和答案已物化，运行 OJ 不需要再执行生成器。\n") +
            "题面为尽力转换，原始 HTML / LaTeX 保留；转换与验证记录见 conversion.json。\n", encoding="utf-8")
        return {"id": pid, "title": title, "interactive": interactive, "cases": len(cases),
                "generatedInputs": generated, "generatedAnswers": answers}


def convert(archive, output, compiler="g++", timeout=120, regenerate=False):
    archive, output = Path(archive).resolve(), Path(output).resolve()
    if output.exists():
        raise ValueError(f"Output already exists; choose a new directory: {output}")
    resolved = shutil.which(compiler)
    if not resolved:
        raise ValueError(f"Compiler not found: {compiler}")
    output.parent.mkdir(parents=True, exist_ok=True)
    # Publish only a fully verified output; failed builds stay in a named staging
    # directory for diagnostics and never masquerade as loadable workspaces.
    stage = Path(tempfile.mkdtemp(prefix=output.name + ".building-", dir=output.parent))
    (stage / '.gitignore').write_text('build/\n', encoding='utf-8')
    try:
        with tempfile.TemporaryDirectory(prefix="polygon-") as tmp:
            scratch = Path(tmp)
            package = scratch / "package"
            extract_zip(archive, package)
            title, mapping = problem_map(package)
            builder = Builder(stage / "build", resolved, timeout, regenerate, compiler)
            report = {"success": False, "archive": archive.name, "archiveSha256": file_sha256(archive),
                      "title": title, "exportedAt": datetime.now(timezone.utc).isoformat(), "problems": []}
            for pid, folder, xml in mapping:
                interactive = xml.find("assets/interactor") is not None
                dest = stage / ("unsupported" if interactive else "problems") / pid
                report["problems"].append(builder.materialize(pid, folder, xml, dest))
                write_json(stage / "conversion-report.json", report)
            loaded, digest = load_problems(stage / "problems")
            report.update(success=True, loadableProblems=list(loaded), inputDigest=digest,
                          loadableCaseCount=sum(len(p.cases) for p in loaded.values()))
            write_json(stage / "conversion-report.json", report)
        stage.rename(output)
        return report
    except Exception as exc:
        (stage / "FAILED.txt").write_text(str(exc), encoding="utf-8")
        raise RuntimeError(f"Conversion failed; diagnostics retained at {stage}: {exc}") from exc


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path, help="Polygon contest or problem ZIP")
    parser.add_argument("--output", required=True, type=Path, help="New output directory (must not exist)")
    parser.add_argument("--compiler", default="g++")
    parser.add_argument("--timeout", type=int, default=120, help="Generator/validator/answer timeout in seconds")
    parser.add_argument("--regenerate", action="store_true", help="Regenerate even generated inputs already present in ZIP")
    args = parser.parse_args()
    if args.timeout <= 0:
        parser.error("--timeout must be positive")
    report = convert(args.archive, args.output, args.compiler, args.timeout, args.regenerate)
    print(f"Ready: {args.output} ({len(report['loadableProblems'])} problems, {report['loadableCaseCount']} cases)")


if __name__ == "__main__":
    main()
