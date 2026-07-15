#!/usr/bin/env python3
"""Render a draft EA feedback report from collected context."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


TOKEN_PATTERNS = [
    re.compile(r"gho_[A-Za-z0-9_]+"),
    re.compile(r"ghp_[A-Za-z0-9_]+"),
    re.compile(r"(?i)(api[_-]?key|token|password|secret)\s*[:=]\s*['\"]?[^'\"\s]+"),
]


def redact(text: str) -> str:
    feedback_email_marker = "__EA_FEEDBACK_EMAIL__"
    text = text.replace("ea_feedback@163.com", feedback_email_marker)
    text = re.sub(r"/Users/[^/\s]+", "/Users/<user>", text)
    text = re.sub(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", "<email-redacted>", text)
    text = text.replace(feedback_email_marker, "ea_feedback@163.com")
    for pattern in TOKEN_PATTERNS:
        text = pattern.sub("<token-redacted>", text)
    return text


def command_text(context: dict[str, Any], name: str) -> str:
    cmd = context.get("commands", {}).get(name, {})
    parts = []
    for key in ["stdout", "stderr"]:
        if cmd.get(key):
            parts.append(str(cmd[key]))
    return "\n".join(parts)


def extract_ea_version(context: dict[str, Any]) -> str:
    text = command_text(context, "ea_version")
    return text.splitlines()[0] if text else "unknown"


def issue(
    severity: str,
    title: str,
    category: str,
    confidence: str,
    evidence: list[str],
    likely_cause: str,
    impact: str,
    recommendation: str,
    acceptance: str,
) -> dict[str, Any]:
    return {
        "severity": severity,
        "title": title,
        "category": category,
        "confidence": confidence,
        "evidence": evidence,
        "likely_cause": likely_cause,
        "impact": impact,
        "recommendation": recommendation,
        "acceptance": acceptance,
    }


def detect_issues(context: dict[str, Any]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    user_notes = context.get("user_notes", "")

    for skill in context.get("installed_ea_skills", []):
        if skill.get("bytes", 0) > 25000 or skill.get("lines", 0) > 300:
            issues.append(
                issue(
                    "P1",
                    "EA top-level skill instructions are heavy for routine invocation",
                    "token-context",
                    "medium",
                    [f"{skill.get('path')} has {skill.get('lines')} lines and {skill.get('bytes')} bytes."],
                    "The top-level skill appears to include broad command catalogs and workflow details that could be progressively disclosed.",
                    "Users and agents may hit context pressure early and may over-execute because too much workflow detail is loaded up front.",
                    "Move long command catalogs and method-specific details into references; keep SKILL.md as a routing layer.",
                    "A lightweight EA advice request loads only the routing layer and task-relevant reference files.",
                )
            )

    for project in context.get("ea_projects", []):
        counts = project.get("counts", {})
        total_state = sum(counts.get(k, 0) for k in ["experiments", "samples", "references", "reviews", "provenance", "progress", "open_items"])
        if total_state >= 12 and counts.get("reports", 0) == 0:
            issues.append(
                issue(
                    "P1",
                    "EA project state can grow quickly before first report",
                    "file-proliferation",
                    "medium",
                    [f"{project.get('root')} has state-file counts {counts} before any reports."],
                    "Early consult/plan interactions may be written as multiple formal artifacts instead of staying in a lightweight draft phase.",
                    "Users may feel the project becomes heavy after only a few turns, and developers must inspect many files for one feedback point.",
                    "Introduce consult/record/execute modes or a lightweight draft bundle before formal review/provenance expansion.",
                    "A short advice session does not create formal project artifacts unless the user asks to record it.",
                )
            )

        review_statuses = project.get("reviews", {}).get("statuses", {})
        if any(status != "user_confirmed" for status in review_statuses):
            issues.append(
                issue(
                    "P1",
                    "Review states may create duplicate confirmation work",
                    "review-provenance",
                    "medium",
                    [f"{project.get('root')} review status counts: {review_statuses}."],
                    "Natural user replies can be classified as edited/deferred instead of confirmed, while downstream health gates may require confirmed reviews.",
                    "Agents may create multiple review files for one user confirmation, making the project harder to maintain.",
                    "Add explicit review promotion or `review add --confirm`; allow parameter-type accepted edits to satisfy health gates when appropriate.",
                    "One natural numbered parameter reply can become one healthcheck-valid review record.",
                )
            )

        execution_events = project.get("execution_events", {}).get("events", [])
        active_problem_events = [
            event
            for event in execution_events
            if event.get("history_state") in {"current", "unreconciled"}
            and event.get("status") in {"failed", "partial"}
        ]
        if active_problem_events:
            issues.append(
                issue(
                    "P1",
                    "Current or unreconciled EA execution events need attention",
                    "runtime-error",
                    "high",
                    [
                        (
                            f"{event.get('stage')} attempt {event.get('attempt')}: {event.get('status')} "
                            f"({event.get('error_code') or 'no error code'}); next: {event.get('next_action') or 'unspecified'}"
                        )
                        for event in active_problem_events[:5]
                    ],
                    "Structured execution history contains a failure or partial stage that has not been superseded or reconciled.",
                    "The current run may be incomplete even when older artifacts contain unrelated status text.",
                    "Resolve the recorded next action and append a recovered/completed event that supersedes the failed attempt.",
                    "Collector classifies the old event as resolved_historical and reports the recovered/completed event as current.",
                )
            )

        potential = project.get("potential_findings", [])
        validation_status = project.get("current_validation", {}).get("status")
        if potential and not (validation_status == "pass" and not active_problem_events):
            evidence = [f"{p['path']}: {p['line']}" for p in potential[:5]]
            issues.append(
                issue(
                    "P0" if any("traceback" in p["line"].lower() for p in potential) else "P1",
                    "Existing EA artifacts contain error or warning signals",
                    "runtime-error",
                    "high",
                    evidence,
                    "Existing project artifacts include failure/warning/error markers that should be reviewed by developers.",
                    "Errors or warnings in health/eval/provenance/review paths can block handoff and reduce trust.",
                    "Inspect the listed artifacts, reproduce the triggering workflow, and add a regression test or friendlier repair path.",
                    "The same workflow completes without error markers or emits a clear recovery command.",
                )
            )

        config = project.get("config_excerpt", "")
        if "literature:\n  enabled: false" in config:
            issues.append(
                issue(
                    "P2",
                    "Literature library capability may be hidden after initialization",
                    "literature-workflow",
                    "medium",
                    [f"{project.get('root')} config has literature.enabled=false."],
                    "Initialization safely disables literature features but may rely on open items rather than a user-visible recommendation.",
                    "Users may not discover literature-library support unless the agent explicitly explains it.",
                    "After initialization, recommend index-only or open-access-only literature setup while keeping Zotero/browser/institution access opt-in.",
                    "New project initialization produces a concise user-visible literature-library recommendation.",
                )
            )

    if re.search(r"token|context|上下文|太多|臃肿", user_notes, re.IGNORECASE):
        issues.append(
            issue(
                "P1",
                "User reported context or token pressure",
                "token-context",
                "medium",
                ["User notes mention token/context heaviness."],
                "The workflow likely loads or emits more detail than the user expects for the task stage.",
                "Users may perceive EA as heavy even when the underlying audit model is valuable.",
                "Add progressive disclosure, reduce default command catalogs, and avoid formal writes during consult-only exchanges.",
                "A comparable session completes with shorter visible output and fewer loaded references.",
            )
        )

    cli_discovery = context.get("ea_cli_discovery", {})
    if cli_discovery.get("status") != "available":
        issues.append(
            issue(
                "P1",
                "EA CLI executable could not be discovered",
                "install-version",
                "high",
                [f"Discovery attempts: {len(cli_discovery.get('attempts') or [])}; selected source: unknown."],
                "No explicit EA_BIN, current-Python installation, project virtualenv executable, or PATH command passed `ea version`.",
                "The report cannot reliably identify the tested EA runtime.",
                "Install EA in the active project virtualenv or set EA_BIN to the intended executable before collecting feedback.",
                "Collector reports an available source and the exact executable reference used for `ea version`.",
            )
        )

    if not issues:
        issues.append(
            issue(
                "P3",
                "No high-confidence issue detected from available artifacts",
                "documentation",
                "low",
                ["Collector found no explicit errors; user notes may still contain qualitative feedback."],
                "Available evidence may be incomplete, especially after context compaction or if no logs were provided.",
                "Developers may need richer artifacts to act on feedback.",
                "Ask user for a short visible-conversation summary or terminal log if they expect deeper diagnosis.",
                "Future reports include at least one concrete artifact or command-output evidence item.",
            )
        )
    return issues


def make_feedback_id(context: dict[str, Any], slug: str) -> str:
    now = datetime.now(timezone.utc).astimezone()
    clean = re.sub(r"[^A-Za-z0-9-]+", "-", slug).strip("-").lower() or "ea-run"
    return f"EA-FB-{now:%Y%m%d-%H%M%S}-{clean[:32]}"


def render_issue(issue_data: dict[str, Any]) -> str:
    lines = [
        f"### {issue_data['severity']} {issue_data['title']}",
        "",
        f"- Category: `{issue_data['category']}`",
        f"- Confidence: `{issue_data['confidence']}`",
        "- Evidence:",
    ]
    lines.extend(f"  - {item}" for item in issue_data["evidence"])
    lines.extend(
        [
            f"- Likely cause: {issue_data['likely_cause']}",
            f"- Impact: {issue_data['impact']}",
            f"- Safe recommendation: {issue_data['recommendation']}",
            f"- Acceptance criteria: {issue_data['acceptance']}",
            "",
        ]
    )
    return "\n".join(lines)


def render_report(context: dict[str, Any], feedback_id: str, slug: str) -> str:
    issues = detect_issues(context)
    ea_projects = context.get("ea_projects", [])
    issue_count = len([i for i in issues if i["severity"] != "P3"])
    submit_recommendation = "recommended" if issue_count >= 3 or any(i["severity"] == "P0" for i in issues) else "defer until user review"
    lines = [
        f"# EA Feedback Report: {feedback_id}",
        "",
        "## Summary",
        "",
        f"- Status: `ready_for_user_review`",
        f"- Created: `{context.get('created_at', '')}`",
        f"- EA version: `{extract_ea_version(context)}`",
        f"- EA executable source: `{context.get('ea_cli_discovery', {}).get('source', 'unknown')}`",
        f"- EA executable ref: `{context.get('ea_cli_discovery', {}).get('executable_ref') or 'unknown'}`",
        f"- Workspace: `{context.get('workspace', '')}`",
        f"- EA project roots inspected: {len(ea_projects)}",
        f"- Detected actionable issue count: {issue_count}",
        f"- Submission recommendation: `{submit_recommendation}`",
        "",
        "## User-Reported Concerns",
        "",
        context.get("user_notes", "").strip() or "_No explicit user notes were provided._",
        "",
        "## Automatically Detected Issues",
        "",
    ]
    lines.extend(render_issue(item) for item in issues)
    lines.extend(
        [
            "## Cross-Cutting Recommendations",
            "",
            "- Keep EA-feedback independent and read-only toward EA runtime and EA project files.",
            "- Prefer progressive disclosure and consult/record/execute separation when addressing EA UX friction.",
            "- Preserve EA core protections: raw-data safety, review gates, provenance, traceability, memory boundaries, and public-user initialization safety.",
            "- Add targeted CLI helpers or tests rather than removing safety mechanisms.",
            "",
            "## Submission Draft",
            "",
            "Default GitHub target: `gongchenisbusy/Experimental-Assistant`.",
            "",
            "Suggested issue title:",
            "",
            f"`[EA-feedback] {feedback_id}: {issue_count} actionable issues from {slug}`",
            "",
            "Suggested email fallback:",
            "",
            "- To: `ea_feedback@163.com`",
            f"- Subject: `[EA-feedback] {feedback_id} {slug}`",
            "",
            "## Appendix: Evidence Inventory",
            "",
            "### Commands",
            "",
        ]
    )
    for name, payload in context.get("commands", {}).items():
        lines.extend(
            [
                f"#### {name}",
                "",
                "```text",
                json.dumps(payload, ensure_ascii=False, indent=2)[:4000],
                "```",
                "",
            ]
        )
    lines.append("### EA Projects")
    lines.append("")
    for project in ea_projects:
        lines.extend(
            [
                f"- `{project.get('root')}` counts: `{project.get('counts')}`",
                f"  - latest eval files: `{project.get('latest_eval_files')}`",
                f"  - latest brief files: `{project.get('latest_brief_files')}`",
                f"  - review statuses: `{project.get('reviews', {}).get('statuses')}`",
                f"  - current validation: `{project.get('current_validation')}`",
                f"  - execution event summary: `{project.get('execution_events', {}).get('summary')}`",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Render EA feedback report from context JSON.")
    parser.add_argument("--context", required=True, help="Context JSON from collect_ea_context.py.")
    parser.add_argument("--output", required=True, help="Markdown report output path.")
    parser.add_argument("--slug", default="ea-run", help="Short slug for feedback ID and title.")
    parser.add_argument("--no-redact", action="store_true", help="Do not redact public-sensitive values.")
    args = parser.parse_args()

    context = json.loads(Path(args.context).read_text(encoding="utf-8"))
    feedback_id = make_feedback_id(context, args.slug)
    report = render_report(context, feedback_id, args.slug)
    if not args.no_redact:
        report = redact(report)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(report, encoding="utf-8")
    print(str(output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
