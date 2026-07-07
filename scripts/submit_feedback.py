#!/usr/bin/env python3
"""Bounded EA-feedback submission helper.

The helper intentionally does not read GitHub issue bodies or comments. It only
checks issue title metadata for the exact feedback ID, then submits once through
GitHub or prepares one local email draft fallback.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_REPO = "gongchenisbusy/Experimental-Assistant"
DEFAULT_EMAIL = "ea_feedback@163.com"
FEEDBACK_ID_RE = re.compile(r"\bEA-FB-\d{8}-\d{6}-[A-Za-z0-9-]+\b")
TOKEN_PATTERNS = [
    re.compile(r"gho_[A-Za-z0-9_]+"),
    re.compile(r"ghp_[A-Za-z0-9_]+"),
    re.compile(r"(?i)(api[_-]?key|token|password|secret)\s*[:=]\s*['\"]?[^'\"\s]+"),
]


def run_command(args: list[str], timeout: int = 20) -> dict[str, Any]:
    try:
        completed = subprocess.run(
            args,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            check=False,
        )
        return {
            "command": args,
            "returncode": completed.returncode,
            "stdout": redact(completed.stdout.strip()),
            "stderr": redact(completed.stderr.strip()),
        }
    except FileNotFoundError:
        return {"command": args, "available": False, "returncode": 127, "stderr": f"{args[0]} not found"}
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout if isinstance(exc.stdout, str) else ""
        stderr = exc.stderr if isinstance(exc.stderr, str) else ""
        return {
            "command": args,
            "timeout": timeout,
            "returncode": 124,
            "stdout": redact(stdout.strip()),
            "stderr": redact(stderr.strip()) or "command timed out",
        }


def redact(text: str) -> str:
    marker = "__EA_FEEDBACK_EMAIL__"
    text = text.replace(DEFAULT_EMAIL, marker)
    text = re.sub(r"/Users/[^/\s]+", "/Users/<user>", text)
    text = re.sub(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", "<email-redacted>", text)
    text = text.replace(marker, DEFAULT_EMAIL)
    for pattern in TOKEN_PATTERNS:
        text = pattern.sub("<token-redacted>", text)
    return text


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def extract_feedback_id(text: str, fallback: str | None = None) -> str:
    match = FEEDBACK_ID_RE.search(text)
    if match:
        return match.group(0)
    if fallback:
        return fallback
    raise ValueError("Could not find a feedback ID like EA-FB-YYYYMMDD-HHMMSS-slug in the report.")


def derive_title(report_text: str, feedback_id: str, override: str | None = None) -> str:
    if override:
        return override
    for line in report_text.splitlines():
        if line.startswith("# "):
            title = line[2:].strip()
            if title:
                return f"[EA-feedback] {title}"
    return f"[EA-feedback] {feedback_id}"


def existing_issue_by_title(feedback_id: str, repo: str, timeout: int) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    command = [
        "gh",
        "issue",
        "list",
        "--repo",
        repo,
        "--state",
        "all",
        "--limit",
        "100",
        "--json",
        "number,title,url,state",
    ]
    result = run_command(command, timeout=timeout)
    if result.get("returncode") != 0:
        return None, result
    try:
        issues = json.loads(result.get("stdout") or "[]")
    except json.JSONDecodeError as exc:
        result["returncode"] = 2
        result["stderr"] = f"could not parse gh issue list JSON: {exc}"
        return None, result
    for issue in issues:
        if feedback_id in str(issue.get("title", "")):
            return issue, result
    return None, result


def write_temp_body(body: str) -> str:
    temp = tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".md", delete=False)
    with temp:
        temp.write(body)
    return temp.name


def create_github_issue(title: str, body: str, repo: str, timeout: int) -> dict[str, Any]:
    body_file = write_temp_body(body)
    return run_command(["gh", "issue", "create", "--repo", repo, "--title", title, "--body-file", body_file], timeout=timeout)


def write_email_draft(
    *,
    feedback_id: str,
    title: str,
    body: str,
    draft_dir: Path,
    recipient: str = DEFAULT_EMAIL,
) -> dict[str, Any]:
    draft_dir.mkdir(parents=True, exist_ok=True)
    draft_path = draft_dir / f"{feedback_id}-email-draft.md"
    content = "\n".join(
        [
            f"To: {recipient}",
            f"Subject: {title}",
            "",
            body.rstrip(),
            "",
        ]
    )
    draft_path.write_text(content, encoding="utf-8")
    return {"status": "email_draft_prepared", "path": str(draft_path), "recipient": recipient}


def failure_message(github_failure: dict[str, Any] | None, email_failure: dict[str, Any] | None) -> str:
    reasons: list[str] = []
    if github_failure:
        reasons.append(f"GitHub submission failed: {github_failure.get('reason') or github_failure.get('stderr') or 'unknown error'}")
    if email_failure:
        reasons.append(f"Email draft fallback failed: {email_failure.get('reason') or email_failure.get('stderr') or 'unknown error'}")
    reason_text = "; ".join(reasons) if reasons else "Submission failed for an unknown reason."
    return (
        f"{reason_text}. You can run `gh auth login` and ask Codex to retry submission, "
        "or manually open the repository Issues page and paste the suggested issue body. "
        "If you prefer email, copy the report body into your email client and send it to "
        f"{DEFAULT_EMAIL}. EA-feedback will not attempt browser login or email account setup automatically."
    )


def write_submission_record(path: Path | None, payload: dict[str, Any]) -> None:
    if path is None:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def submit(args: argparse.Namespace) -> dict[str, Any]:
    report_path = Path(args.report)
    report_text = read_text(report_path)
    body_text = read_text(Path(args.body_file)) if args.body_file else report_text
    if not args.no_redact:
        body_text = redact(body_text)
    feedback_id = extract_feedback_id(report_text, fallback=args.feedback_id)
    title = derive_title(report_text, feedback_id, override=args.title)
    created_at = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
    base: dict[str, Any] = {
        "feedback_id": feedback_id,
        "created_at": created_at,
        "repo": args.repo,
        "title": title,
        "report_path": str(report_path),
        "dry_run": args.dry_run,
        "github": {"attempted": False},
        "email": {"attempted": False},
    }

    if args.dry_run:
        return {**base, "status": "dry_run", "message": "No submission attempted."}

    github_failure: dict[str, Any] | None = None
    if args.github_mode != "disabled":
        base["github"]["attempted"] = True
        auth = run_command(["gh", "auth", "status"], timeout=args.timeout)
        base["github"]["auth"] = auth
        if auth.get("returncode") != 0:
            github_failure = {"stage": "auth", "reason": auth.get("stderr") or auth.get("stdout") or "gh auth status failed"}
        else:
            existing, list_result = existing_issue_by_title(feedback_id, args.repo, timeout=args.timeout)
            base["github"]["duplicate_check"] = {
                "method": "issue_title_metadata_only",
                "returncode": list_result.get("returncode"),
            }
            if list_result.get("returncode") != 0:
                github_failure = {"stage": "duplicate_check", "reason": list_result.get("stderr") or "could not list issue metadata"}
            elif existing:
                return {
                    **base,
                    "status": "already_submitted",
                    "channel": "github_issue",
                    "url": existing.get("url"),
                    "issue": existing,
                    "message": f"Feedback ID {feedback_id} is already present in an issue title.",
                }
            else:
                created = create_github_issue(title, body_text, args.repo, timeout=args.timeout)
                base["github"]["create"] = created
                if created.get("returncode") == 0:
                    url = (created.get("stdout") or "").splitlines()[-1] if created.get("stdout") else ""
                    return {
                        **base,
                        "status": "submitted_github",
                        "channel": "github_issue",
                        "url": url,
                        "message": "Feedback submitted to GitHub.",
                    }
                github_failure = {"stage": "create", "reason": created.get("stderr") or created.get("stdout") or "gh issue create failed"}
    else:
        github_failure = {"stage": "disabled", "reason": "GitHub submission disabled by --github-mode disabled"}

    email_failure: dict[str, Any] | None = None
    if args.email_mode != "disabled":
        base["email"]["attempted"] = True
        try:
            draft = write_email_draft(
                feedback_id=feedback_id,
                title=title,
                body=body_text,
                draft_dir=Path(args.email_draft_dir or report_path.parent),
                recipient=args.email_to,
            )
            return {
                **base,
                "status": "email_draft_prepared",
                "channel": "email_draft",
                "email": {**base["email"], **draft},
                "github_failure": github_failure,
                "message": "GitHub submission failed or was unavailable; a local email draft was prepared instead.",
            }
        except OSError as exc:
            email_failure = {"stage": "draft", "reason": str(exc)}
    else:
        email_failure = {"stage": "disabled", "reason": "Email fallback disabled by --email-mode disabled"}

    message = failure_message(github_failure, email_failure)
    return {
        **base,
        "status": "submission_failed",
        "channel": "submission_failed",
        "github_failure": github_failure,
        "email_failure": email_failure,
        "message": message,
        "recommended_recovery": [
            "Run `gh auth login`, then retry this submission helper.",
            "Manually open https://github.com/gongchenisbusy/Experimental-Assistant/issues and paste the suggested issue body.",
            f"Copy the report body into an email client and send it to {DEFAULT_EMAIL}.",
            "Ask Codex in a separate task to help connect GitHub or open the browser for manual issue creation.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Submit an EA-feedback report with bounded GitHub/email fallback behavior.")
    parser.add_argument("--report", required=True, help="Feedback report Markdown path.")
    parser.add_argument("--body-file", help="Optional public-safe issue/email body Markdown path. Defaults to --report.")
    parser.add_argument("--title", help="Override issue/email title.")
    parser.add_argument("--feedback-id", help="Fallback feedback ID if the report does not contain one.")
    parser.add_argument("--repo", default=DEFAULT_REPO)
    parser.add_argument("--email-to", default=DEFAULT_EMAIL)
    parser.add_argument("--email-draft-dir")
    parser.add_argument("--submission-record", help="Optional JSON sidecar path for the submission result.")
    parser.add_argument("--github-mode", choices=["auto", "disabled"], default="auto")
    parser.add_argument("--email-mode", choices=["draft", "disabled"], default="draft")
    parser.add_argument("--timeout", type=int, default=20)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--no-redact", action="store_true")
    args = parser.parse_args()

    try:
        result = submit(args)
    except (OSError, ValueError) as exc:
        result = {
            "status": "submission_failed",
            "channel": "submission_failed",
            "message": str(exc),
            "recommended_recovery": [
                "Check that the feedback report path exists and is readable.",
                "Manually open the repository Issues page and paste the suggested issue body if available.",
            ],
        }
    write_submission_record(Path(args.submission_record) if args.submission_record else None, result)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 2 if result.get("status") == "submission_failed" else 0


if __name__ == "__main__":
    raise SystemExit(main())
