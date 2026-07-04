#!/usr/bin/env python3
"""Collect read-only EA context for EA-feedback reports."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SKIP_DIRS = {
    ".git",
    ".venv",
    "node_modules",
    "__pycache__",
    "exports",
    "raw",
    "processed",
    "figures",
}

ERROR_PATTERNS = re.compile(
    r"(traceback|error|fail|failed|warning|review_ref_not_confirmed|exception)",
    re.IGNORECASE,
)


def run_command(args: list[str], cwd: Path, timeout: int = 10) -> dict[str, Any]:
    try:
        proc = subprocess.run(
            args,
            cwd=str(cwd),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            check=False,
        )
        return {
            "command": args,
            "returncode": proc.returncode,
            "stdout": proc.stdout.strip(),
            "stderr": proc.stderr.strip(),
        }
    except FileNotFoundError:
        return {"command": args, "available": False}
    except subprocess.TimeoutExpired as exc:
        return {
            "command": args,
            "timeout": timeout,
            "stdout": (exc.stdout or "").strip() if isinstance(exc.stdout, str) else "",
            "stderr": (exc.stderr or "").strip() if isinstance(exc.stderr, str) else "",
        }


def read_text(path: Path, limit: int = 12000) -> str:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    if len(text) > limit:
        return text[:limit] + "\n...[truncated]..."
    return text


def latest_files(root: Path, pattern: str, limit: int = 3) -> list[str]:
    files = sorted(root.glob(pattern), key=lambda p: p.stat().st_mtime if p.exists() else 0, reverse=True)
    return [str(p.relative_to(root)) for p in files[:limit] if p.is_file()]


def count_files(root: Path, rel: str) -> int:
    path = root / rel
    if not path.exists():
        return 0
    return sum(1 for p in path.rglob("*") if p.is_file())


def find_ea_projects(workspace: Path, max_depth: int = 4) -> list[Path]:
    projects: list[Path] = []
    workspace = workspace.resolve()
    for dirpath, dirnames, filenames in os.walk(workspace):
        current = Path(dirpath)
        depth = len(current.relative_to(workspace).parts)
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".cache")]
        if depth > max_depth:
            dirnames[:] = []
            continue
        if "EA_PROJECT.md" in filenames:
            projects.append(current)
            dirnames[:] = []
    return projects


def summarize_reviews(project: Path) -> dict[str, Any]:
    statuses: dict[str, int] = {}
    samples: list[dict[str, str]] = []
    for path in sorted((project / "reviews").glob("*.yml"))[:50]:
        text = read_text(path, limit=4000)
        match = re.search(r"review_status:\s*([^\n]+)", text)
        status = match.group(1).strip() if match else "unknown"
        statuses[status] = statuses.get(status, 0) + 1
        if len(samples) < 8:
            samples.append({"path": str(path.relative_to(project)), "status": status})
    return {"count": sum(statuses.values()), "statuses": statuses, "samples": samples}


def scan_findings(project: Path, limit: int = 20) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    scan_dirs = ["evaluation", "briefs", "open-items", "progress", "provenance", "reviews", "reports"]
    for rel in scan_dirs:
        base = project / rel
        if not base.exists():
            continue
        for path in sorted(base.rglob("*")):
            if not path.is_file() or path.suffix.lower() not in {".md", ".yml", ".yaml", ".json", ".txt"}:
                continue
            text = read_text(path, limit=8000)
            for line in text.splitlines():
                normalized = line.strip().lower()
                if not ERROR_PATTERNS.search(line):
                    continue
                benign = (
                    normalized in {"warnings: []", "errors: []", "findings: []"}
                    or normalized in {"warnings:", "errors:", "doctor_errors:", "doctor_warnings:"}
                    or re.search(r"\b(doctor_)?(error|warning)s?:\s*\[\]", normalized)
                    or re.search(r"\b(error|warning)_count:\s*0\b", normalized)
                    or re.search(r"\b0 errors?\b", normalized)
                    or re.search(r"\b0 warnings?\b", normalized)
                    or normalized == "status: pass"
                )
                if not benign:
                    findings.append({"path": str(path.relative_to(project)), "line": line[:300]})
                    break
            if len(findings) >= limit:
                return findings
    return findings


def summarize_project(project: Path) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "root": str(project),
        "project_file_excerpt": read_text(project / "EA_PROJECT.md", limit=5000),
        "config_excerpt": read_text(project / ".ea" / "project_config.yml", limit=4000),
        "latest_eval_files": latest_files(project, "evaluation/*.yml", limit=3),
        "latest_brief_files": latest_files(project, "briefs/*.*", limit=4),
        "open_items": latest_files(project, "open-items/*.*", limit=20),
        "counts": {
            "experiments": count_files(project, "experiments"),
            "samples": count_files(project, "samples"),
            "reports": count_files(project, "reports"),
            "references": count_files(project, "literature/references"),
            "reviews": count_files(project, "reviews"),
            "provenance": count_files(project, "provenance"),
            "progress": count_files(project, "progress"),
            "open_items": count_files(project, "open-items"),
        },
        "reviews": summarize_reviews(project),
        "potential_findings": scan_findings(project),
    }
    for rel in summary["latest_eval_files"][:1] + summary["latest_brief_files"][:2]:
        summary.setdefault("latest_artifact_excerpts", {})[rel] = read_text(project / rel, limit=7000)
    return summary


def find_installed_ea_skills() -> list[dict[str, Any]]:
    roots = [
        Path.home() / ".codex" / "skills",
        Path.home() / ".agents" / "skills",
    ]
    results: list[dict[str, Any]] = []
    for root in roots:
        if not root.exists():
            continue
        for path in root.rglob("SKILL.md"):
            text = read_text(path, limit=2000)
            if "Experimental Assistant" not in text and "ea-v0-2" not in str(path):
                continue
            try:
                full_text = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                full_text = text
            results.append(
                {
                    "path": str(path),
                    "bytes": len(full_text.encode("utf-8", errors="replace")),
                    "lines": full_text.count("\n") + 1,
                    "excerpt": text,
                }
            )
    return results


def collect_planning_files(workspace: Path) -> list[dict[str, str]]:
    files: list[Path] = []
    for name in ["task_plan.md", "findings.md", "progress.md"]:
        p = workspace / name
        if p.exists():
            files.append(p)
    planning = workspace / ".planning"
    if planning.exists():
        for p in sorted(planning.glob("*/progress.md"))[-5:]:
            files.append(p)
        for p in sorted(planning.glob("*/findings.md"))[-5:]:
            files.append(p)
    return [{"path": str(p), "excerpt": read_text(p, limit=5000)} for p in files if p.is_file()]


def build_context(workspace: Path, user_notes: str | None = None) -> dict[str, Any]:
    workspace = workspace.resolve()
    projects = find_ea_projects(workspace)
    return {
        "feedback_context_schema": "ea-feedback-context-v1",
        "created_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "workspace": str(workspace),
        "user_notes": user_notes or "",
        "commands": {
            "ea_version": run_command(["ea", "version"], cwd=workspace),
            "git_status": run_command(["git", "status", "--short"], cwd=workspace),
            "gh_auth_status": run_command(["gh", "auth", "status"], cwd=workspace),
        },
        "installed_ea_skills": find_installed_ea_skills(),
        "ea_projects": [summarize_project(p) for p in projects],
        "planning_files": collect_planning_files(workspace),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Collect read-only EA context for feedback.")
    parser.add_argument("--workspace", default=".", help="Workspace to inspect.")
    parser.add_argument("--output", required=True, help="JSON output path.")
    parser.add_argument("--user-notes", default="", help="Optional user feedback notes.")
    args = parser.parse_args()

    context = build_context(Path(args.workspace), user_notes=args.user_notes)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(context, ensure_ascii=False, indent=2), encoding="utf-8")
    print(str(output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
