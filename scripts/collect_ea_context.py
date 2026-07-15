#!/usr/bin/env python3
"""Collect read-only EA context for EA-feedback reports."""

from __future__ import annotations

import argparse
import importlib.metadata
import importlib.util
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
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

LITERATURE_READY_STATUSES = {
    "acquired",
    "cache_verified",
    "cached",
    "reused-cache",
    "reused_cache",
    "downloaded",
}
LITERATURE_BLOCKED_STATUSES = {
    "needs_login",
    "needs-login",
    "needs_subscription",
    "needs-subscription",
    "blocked",
    "invalid_pdf",
    "failed-nonpdf",
    "retryable_error",
}

EXECUTION_STATUSES = {"completed", "failed", "recovered", "partial"}


def _utf8_environment() -> dict[str, str]:
    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    return env


def _decode_utf8(value: bytes | str | None) -> str:
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value or ""


def run_command(args: list[str], cwd: Path, timeout: int = 10) -> dict[str, Any]:
    try:
        proc = subprocess.run(
            args,
            cwd=str(cwd),
            text=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            check=False,
            env=_utf8_environment(),
        )
        return {
            "command": args,
            "returncode": proc.returncode,
            "stdout": _decode_utf8(proc.stdout).strip(),
            "stderr": _decode_utf8(proc.stderr).strip(),
        }
    except FileNotFoundError:
        return {"command": args, "available": False}
    except subprocess.TimeoutExpired as exc:
        return {
            "command": args,
            "timeout": timeout,
            "stdout": _decode_utf8(exc.stdout).strip(),
            "stderr": _decode_utf8(exc.stderr).strip(),
        }


def discover_ea_cli(workspace: Path) -> dict[str, Any]:
    candidates: list[tuple[str, list[str], str]] = []
    explicit = os.environ.get("EA_BIN", "").strip()
    if explicit:
        parts = shlex.split(explicit, posix=os.name != "nt")
        if parts:
            candidates.append(("explicit_EA_BIN", parts, explicit))

    try:
        distribution = importlib.metadata.distribution("experimental-assistant")
    except importlib.metadata.PackageNotFoundError:
        distribution = None
    if distribution is not None:
        candidates.append(
            (
                "current_python_distribution_metadata",
                [sys.executable, "-m", "ea"],
                f"{sys.executable} -m ea (experimental-assistant {distribution.version})",
            )
        )

    if importlib.util.find_spec("ea") is not None:
        candidates.append(("current_python_module", [sys.executable, "-m", "ea"], f"{sys.executable} -m ea"))

    venv_candidates = [
        workspace / ".venv" / "Scripts" / "ea.exe",
        workspace / ".venv" / "bin" / "ea",
    ]
    for project in find_ea_projects(workspace):
        venv_candidates.extend([project / ".venv" / "Scripts" / "ea.exe", project / ".venv" / "bin" / "ea"])
    for path in venv_candidates:
        if path.is_file():
            candidates.append(("project_virtualenv", [str(path)], str(path)))

    path_ea = shutil.which("ea")
    if path_ea:
        candidates.append(("PATH", [path_ea], path_ea))

    attempts: list[dict[str, Any]] = []
    seen: set[tuple[str, ...]] = set()
    for source, command, executable_ref in candidates:
        key = tuple(command)
        if key in seen:
            continue
        seen.add(key)
        probe = run_command([*command, "version"], cwd=workspace)
        attempts.append({"source": source, "executable_ref": executable_ref, "probe": probe})
        if probe.get("returncode") == 0:
            return {
                "status": "available",
                "source": source,
                "command": command,
                "executable_ref": executable_ref,
                "probe": probe,
                "attempts": attempts,
            }
    return {"status": "unknown", "source": "unknown", "command": None, "executable_ref": None, "attempts": attempts}


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


def _literature_statuses_from_json(payload: Any) -> list[str]:
    if not isinstance(payload, dict):
        return []
    for key in ("targets", "items", "results", "records"):
        value = payload.get(key)
        if isinstance(value, dict):
            value = list(value.values())
        if isinstance(value, list):
            return [str(item.get("status") or "").strip().lower() for item in value if isinstance(item, dict)]
    nested = payload.get("external_acquisition_state")
    return _literature_statuses_from_json(nested) if isinstance(nested, dict) else []


def _literature_statuses_from_text(text: str) -> list[str]:
    statuses: list[str] = []
    for line in text.splitlines():
        table_match = re.match(r"^\|\s*[^|]+\|\s*[^|]+\|\s*([a-zA-Z0-9_-]+)\s*\|", line)
        yaml_match = re.match(r"^\s*-?\s*status:\s*['\"]?([a-zA-Z0-9_-]+)", line)
        match = table_match or yaml_match
        if match:
            statuses.append(match.group(1).strip().lower())
    return statuses


def summarize_literature_acquisition(project: Path, limit: int = 8) -> dict[str, Any]:
    literature = project / "literature"
    if not literature.exists():
        return {"status_file_count": 0, "acquired": 0, "blocked": 0, "status_refs": []}
    candidates: set[Path] = set()
    for pattern in (
        "**/acquisition_status*.json",
        "**/acquisition_status*.md",
        "**/zotero_codex_readiness.json",
        "**/zotero_codex_readiness.yml",
        "**/zotero_codex_readiness.yaml",
        "**/zotero_codex_readiness.md",
    ):
        candidates.update(path for path in literature.glob(pattern) if path.is_file())
    suffix_priority = {".json": 3, ".yml": 2, ".yaml": 2, ".md": 1}
    grouped: dict[tuple[Path, str], Path] = {}
    for path in candidates:
        key = (path.parent, path.stem)
        current = grouped.get(key)
        if current is None or suffix_priority.get(path.suffix.lower(), 0) > suffix_priority.get(current.suffix.lower(), 0):
            grouped[key] = path
    recent = sorted(grouped.values(), key=lambda path: path.stat().st_mtime, reverse=True)[:limit]
    acquired = 0
    blocked = 0
    refs: list[str] = []
    for path in recent:
        refs.append(str(path.relative_to(project)))
        text = read_text(path, limit=24000)
        statuses: list[str] = []
        if path.suffix.lower() == ".json":
            try:
                statuses = _literature_statuses_from_json(json.loads(text))
            except json.JSONDecodeError:
                statuses = []
        if not statuses:
            statuses = _literature_statuses_from_text(text)
        acquired += sum(status in LITERATURE_READY_STATUSES for status in statuses)
        blocked += sum(status in LITERATURE_BLOCKED_STATUSES for status in statuses)
    return {
        "status_file_count": len(recent),
        "acquired": acquired,
        "blocked": blocked,
        "status_refs": refs,
        "read_scope": "status sidecars only; no cookies, credentials, raw PDFs, or private full text",
    }


def _normalize_execution_event(item: dict[str, Any], ref: str, index: int) -> dict[str, Any] | None:
    status = str(item.get("status") or "").strip().lower()
    if status not in EXECUTION_STATUSES:
        return None
    stage = str(item.get("stage") or "unknown").strip() or "unknown"
    return {
        "event_id": str(item.get("event_id") or f"{Path(ref).stem}-{index + 1}"),
        "stage": stage,
        "scope_id": str(item.get("scope_id") or item.get("run_id") or stage),
        "status": status,
        "attempt": int(item.get("attempt") or 1),
        "artifact_count": int(item.get("artifact_count") or 0),
        "error_code": str(item.get("error_code") or "") or None,
        "next_action": str(item.get("next_action") or "") or None,
        "occurred_at": str(item.get("occurred_at") or item.get("created_at") or ""),
        "supersedes": [str(value) for value in item.get("supersedes") or []],
        "reconciliation": str(item.get("reconciliation") or "") or None,
        "evidence_ref": ref,
    }


def collect_execution_events(project: Path, limit: int = 200) -> dict[str, Any]:
    candidates: set[Path] = set()
    for pattern in (
        ".ea/execution_events*.json",
        "evaluation/**/execution_events*.json",
        "provenance/**/execution_events*.json",
        "literature/**/execution_events*.json",
    ):
        candidates.update(path for path in project.glob(pattern) if path.is_file())
    events: list[dict[str, Any]] = []
    for path in sorted(candidates, key=lambda value: (value.stat().st_mtime, str(value)))[:limit]:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            continue
        raw_events = payload.get("events") if isinstance(payload, dict) else payload
        if not isinstance(raw_events, list):
            continue
        ref = str(path.relative_to(project))
        for index, item in enumerate(raw_events):
            normalized = _normalize_execution_event(item, ref, index) if isinstance(item, dict) else None
            if normalized:
                events.append(normalized)

    by_id = {event["event_id"]: event for event in events}
    resolved_ids: set[str] = set()
    for event in events:
        resolved_ids.update(value for value in event["supersedes"] if value in by_id)
        if event.get("reconciliation") in {"resolved", "reconciled", "superseded"}:
            resolved_ids.add(event["event_id"])

    by_scope: dict[str, list[dict[str, Any]]] = {}
    for event in events:
        by_scope.setdefault(event["scope_id"], []).append(event)
    for scoped in by_scope.values():
        scoped.sort(key=lambda event: (event.get("occurred_at") or "", event["attempt"], event["event_id"]))
        latest = scoped[-1]
        if latest["status"] in {"completed", "recovered"}:
            resolved_ids.update(event["event_id"] for event in scoped[:-1] if event["status"] in {"failed", "partial"})
        for event in scoped:
            if event["event_id"] in resolved_ids:
                event["history_state"] = "resolved_historical"
            elif event is latest:
                event["history_state"] = "current"
            else:
                event["history_state"] = "unreconciled"

    summary = {"current": 0, "unreconciled": 0, "resolved_historical": 0}
    for event in events:
        summary[event["history_state"]] += 1
    return {
        "schema_version": "ea-feedback-execution-events-v1",
        "event_count": len(events),
        "summary": summary,
        "events": events,
        "read_scope": "structured execution-event JSON only",
    }


def summarize_current_validation(project: Path) -> dict[str, Any]:
    candidates: list[Path] = []
    for pattern in ("evaluation/**/*", ".ea/health*", "health*", "eval*"):
        candidates.extend(
            path
            for path in project.glob(pattern)
            if path.is_file() and path.suffix.lower() in {".json", ".yml", ".yaml", ".md", ".txt"}
        )
    if not candidates:
        return {"status": "unknown", "ref": None}
    latest = max(candidates, key=lambda path: path.stat().st_mtime)
    text = read_text(latest, limit=12000)
    status_match = re.search(r"(?im)^\s*(?:overall_)?status\s*[:=]\s*['\"]?([a-z_-]+)", text)
    status = status_match.group(1).lower() if status_match else "unknown"
    if status in {"passed", "success", "complete", "completed", "healthy"}:
        status = "pass"
    elif status in {"failed", "error", "unhealthy"}:
        status = "fail"
    return {"status": status, "ref": str(latest.relative_to(project)), "modified_at": latest.stat().st_mtime}


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
        "literature_acquisition": summarize_literature_acquisition(project),
        "execution_events": collect_execution_events(project),
        "current_validation": summarize_current_validation(project),
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
    ea_cli = discover_ea_cli(workspace)
    return {
        "feedback_context_schema": "ea-feedback-context-v2",
        "created_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "workspace": str(workspace),
        "user_notes": user_notes or "",
        "commands": {
            "ea_version": ea_cli.get("probe")
            or {"available": False, "returncode": 127, "stderr": "EA CLI not found"},
            "git_status": run_command(["git", "status", "--short"], cwd=workspace),
            "gh_auth_status": run_command(["gh", "auth", "status"], cwd=workspace),
        },
        "ea_cli_discovery": ea_cli,
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
