#!/usr/bin/env python3
"""Fail closed when development-only ExactScope material would enter a public tree."""
from __future__ import annotations

from pathlib import Path
import subprocess
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]

BLOCKED_BASENAMES = {
    "CODEX_CONTEXT.md",
    "NEXT_SESSION_PROMPT.md",
    "NEXT_AGENT_HANDOFF.md",
    "GROUNDING_BENCHMARK_HANDOFF.md",
    "GROUNDING_IMPLEMENTATION_FREEZE.md",
    "QUALIFICATION_HANDOFF.md",
    "MARKETING_CLAIMS.md",
    "OPTIMIZATION_EXPERIMENTS.md",
    "PUBLICATION_BOUNDARY.md",
}
BLOCKED_PARTS = {".agents", ".ai-bridge", "raw-results", "preregistrations"}
BLOCKED_PREFIXES = ("docs/internal/",)
BLOCKED_MARKDOWN_NAME_TOKENS = ("HANDOFF", "PROMPT")
BLOCKED_PUBLIC_DOC_LINKS = {"OPTIMIZATION_EXPERIMENTS.md", "PUBLICATION_BOUNDARY.md"}
LOCAL_MARKERS = (
    b"C:\\Users\\",
    b"C:\\AIProjects\\",
    b"C:/Users/",
    b"C:/AIProjects/",
    b"/mnt/c/Users/",
    b"/mnt/c/AIProjects/",
)
TEXT_SUFFIXES = {".md", ".txt", ".json", ".jsonl", ".toml", ".yaml", ".yml", ".py", ".ps1", ".sh", ".cmd"}


def public_candidate_files() -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
        cwd=ROOT,
        check=True,
        stdout=subprocess.PIPE,
    )
    return [Path(value.decode("utf-8")) for value in result.stdout.split(b"\0") if value]


def main() -> int:
    failures: list[str] = []
    candidates = public_candidate_files()
    for relative in candidates:
        relative_posix = relative.as_posix()
        markdown_internal_name = (
            relative.suffix.lower() == ".md"
            and any(token in relative.name.upper() for token in BLOCKED_MARKDOWN_NAME_TOKENS)
        )
        if relative.name in BLOCKED_BASENAMES or markdown_internal_name:
            failures.append(f"blocked internal file is a public candidate: {relative_posix}")
        if any(part in BLOCKED_PARTS for part in relative.parts) or any(relative_posix.startswith(prefix) for prefix in BLOCKED_PREFIXES):
            failures.append(f"blocked internal/evidence path is a public candidate: {relative_posix}")
        path = ROOT / relative
        if path.is_file() and path.suffix.lower() in TEXT_SUFFIXES:
            data = path.read_bytes()
            if relative_posix != "tools/audit_publication.py" and any(marker in data for marker in LOCAL_MARKERS):
                failures.append(f"local absolute path marker in public-candidate text: {relative_posix}")
            if path.suffix.lower() == ".md":
                for blocked_name in BLOCKED_PUBLIC_DOC_LINKS:
                    name = blocked_name.encode("utf-8")
                    if (b"](" + name) in data or (b"](docs/" + name) in data:
                        failures.append(f"public markdown links to blocked internal document {blocked_name}: {relative_posix}")

    audit_self = (ROOT / "tools/audit_publication.py").resolve()
    for package_script in sorted((ROOT / "tools").glob("package*.py")):
        if package_script.resolve() == audit_self:
            continue
        text = package_script.read_text(encoding="utf-8", errors="strict")
        for name in BLOCKED_BASENAMES:
            if name in text:
                failures.append(f"packager references blocked internal file {name}: {package_script.relative_to(ROOT).as_posix()}")

    if failures:
        print("ExactScope publication audit: FAIL")
        for failure in sorted(set(failures)):
            print(f"- {failure}")
        return 1
    print(f"ExactScope publication audit: PASS ({len(candidates)} tracked/untracked public-candidate files checked)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
