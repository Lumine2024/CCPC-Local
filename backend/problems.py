"""Read-only loading of skill-compatible problem workspaces."""
import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path, PurePosixPath


def inside(root: Path, relative: str) -> Path:
    if not isinstance(relative, str) or not relative or ":" in relative:
        raise ValueError("非法相对路径")
    clean = PurePosixPath(relative.replace("\\", "/"))
    if clean.is_absolute() or ".." in clean.parts:
        raise ValueError("路径越界")
    candidate = (root / str(clean)).resolve()
    if not candidate.is_relative_to(root.resolve()) or not candidate.is_file():
        raise ValueError(f"缺少文件或路径越界: {relative}")
    return candidate


@dataclass(frozen=True)
class Case:
    name: str
    group: str
    input: Path
    answer: Path


@dataclass
class Problem:
    id: str
    root: Path
    config: dict
    statement: str
    cases: list[Case]
    assets: dict[str, Path]
    checker: Path
    include: Path

    def public(self, name: str) -> dict:
        return {"id": self.id, "name": name, "title": self.config["title"],
                "time_limit_ms": self.config["timeLimitMs"],
                "memory_limit_mb": self.config["memoryLimitMb"], "standard": self.config["standard"]}


def load_problems(root: Path) -> tuple[dict[str, Problem], str]:
    root = root.resolve()
    if not root.is_dir():
        raise ValueError(f"题目集合目录不存在: {root}")
    problems, digest = {}, hashlib.sha256()
    for folder in sorted(root.iterdir()):
        if not folder.is_dir() or not (folder / "config.json").is_file():
            continue
        try:
            cfg_path = folder / "config.json"
            cfg = json.loads(cfg_path.read_text(encoding="utf-8-sig"))
            if cfg.get("interactive") is not False:
                raise ValueError("首版只支持非交互题，interactive 必须为 false")
            for field in ("timeLimitMs", "memoryLimitMb"):
                if type(cfg.get(field)) is not int or cfg[field] <= 0:
                    raise ValueError(f"非法 {field}")
            if not cfg.get("title") or not cfg.get("standard"):
                raise ValueError("缺少 title / standard")
            statement_path = inside(folder, cfg["statement"])
            statement = statement_path.read_text(encoding="utf-8-sig")
            checker = inside(folder, cfg["checker"])
            include = inside(folder, "include/testlib.h").parent
            manifest_path = inside(folder, "exported-tests/manifest.json")
            manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
            if manifest.get("interactive") is not False:
                raise ValueError("manifest 题型不匹配")
            if not manifest.get("cases") or manifest.get("caseCount") != len(manifest["cases"]):
                raise ValueError("manifest caseCount 不匹配或测试为空")
            cases, seen = [], set()
            for item in manifest["cases"]:
                if not item["name"] or item["name"] in seen:
                    raise ValueError("case 名称为空或重复")
                seen.add(item["name"])
                cases.append(Case(item["name"], item["group"],
                                  inside(folder / "exported-tests", item["input"]),
                                  inside(folder / "exported-tests", item["answer"])))
            assets = {}
            for reference in re.findall(r"!\[[^\]]*\]\(([^)]+)\)", statement):
                if reference.startswith(("https://", "http://")):
                    raise ValueError("题面图片须提供本地副本，保证离线使用")
                asset = inside(statement_path.parent, reference)
                if asset.suffix.lower() not in {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg"}:
                    raise ValueError("不支持的题面资源类型")
                assets[reference.replace("\\", "/")] = asset
            for file in [cfg_path, manifest_path, statement_path, checker, include / "testlib.h",
                         *assets.values(), *(f for case in cases for f in (case.input, case.answer))]:
                digest.update(str(file.relative_to(root)).replace("\\", "/").encode())
                with file.open("rb") as stream:
                    for block in iter(lambda: stream.read(1024 * 1024), b""):
                        digest.update(block)
            problems[folder.name] = Problem(folder.name, folder, cfg, statement, cases, assets, checker, include)
        except (KeyError, ValueError, TypeError, OSError) as exc:
            raise ValueError(f"{folder}: {exc}") from exc
    if not problems:
        raise ValueError("没有找到包含 config.json 的题目子目录")
    return problems, digest.hexdigest()
