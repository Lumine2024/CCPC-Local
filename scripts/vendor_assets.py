"""Maintenance-only: fetch pinned npm distributions and verify registry integrity."""
import base64
import hashlib
import io
import json
import tarfile
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "frontend" / "vendor"
PACKAGES = {"marked": "15.0.12", "dompurify": "3.3.1", "katex": "0.16.33"}


def main():
    ROOT.mkdir(parents=True, exist_ok=True)
    records = []
    for name, version in PACKAGES.items():
        metadata = json.load(urllib.request.urlopen(f"https://registry.npmjs.org/{name}/{version}", timeout=30))
        dist = metadata["dist"]
        data = urllib.request.urlopen(dist["tarball"], timeout=60).read()
        algo, expected = dist["integrity"].split("-", 1)
        assert base64.b64encode(hashlib.new(algo, data).digest()).decode() == expected
        with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as archive:
            for member in archive.getmembers():
                relative = member.name.removeprefix("package/")
                keep = (name == "marked" and relative in {"lib/marked.umd.js", "LICENSE.md"}) or \
                       (name == "dompurify" and relative in {"dist/purify.min.js", "LICENSE"}) or \
                       (name == "katex" and (relative.startswith("dist/") and not relative.endswith(".map") or relative == "LICENSE"))
                if not keep or not member.isfile():
                    continue
                output = ROOT / name / relative
                if not output.resolve().is_relative_to(ROOT.resolve()):
                    raise ValueError("unsafe archive path")
                output.parent.mkdir(parents=True, exist_ok=True)
                output.write_bytes(archive.extractfile(member).read())
        records.append({"package": name, "version": version, "source": dist["tarball"], "integrity": dist["integrity"]})
        print(f"Vendored {name} {version}", flush=True)
    (ROOT / "manifest.json").write_text(json.dumps(records, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
