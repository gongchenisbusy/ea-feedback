#!/usr/bin/env python3
"""Classify whether EA-feedback should submit now or only suggest upload."""

from __future__ import annotations

import argparse
import json
import re
from typing import Any


NEGATIVE_PATTERNS = [
    r"(不要|别|先不要|暂不|不用|无需|不需要|别自动|不要自动).{0,24}(上传|提交|发送|发给|创建\s*issue|邮件|github|GitHub|开发者)",
    r"(只|仅).{0,12}(生成|保存|写|形成).{0,12}(文件|本地|草稿)",
    r"(local only|draft only|do not submit|don't submit|do not upload|don't upload|without submitting|no need to submit)",
]

EXPLICIT_SUBMIT_PATTERNS = [
    r"(上传|提交|发给|发送|创建|发布).{0,24}(开发者端|开发者|github|GitHub|issue|Issue|仓库|邮箱|邮件)",
    r"(开发者端|开发者|github|GitHub|issue|Issue|仓库|邮箱|邮件).{0,24}(上传|提交|发送|发给|创建|发布)",
    r"(做完|完成|生成|修改好|整理好|形成|写好).{0,24}(就可以|可以|直接|自动).{0,24}(上传|提交|发给|发送|发布)",
    r"(上传|提交|发送|发给|发布).{0,16}(即可|就行|就可以|就好)",
    r"(submit|upload|send|publish|create an issue|open an issue).{0,40}(developer|GitHub|github|issue|email|repo|repository)",
    r"(after|once).{0,30}(create|generate|finish|update).{0,40}(submit|upload|send|publish|create an issue|open an issue)",
]

SUGGEST_ONLY_PATTERNS = [
    r"(建议|可以|是否|要不要|需不需要).{0,24}(上传|提交|发送|发给|创建\s*issue)",
    r"(suggest|recommend|should).{0,40}(submit|upload|send|publish)",
]


def find_matches(patterns: list[str], text: str) -> list[str]:
    matches: list[str] = []
    for pattern in patterns:
        if re.search(pattern, text, re.IGNORECASE):
            matches.append(pattern)
    return matches


def classify(text: str, issue_count: int = 0, has_p0: bool = False, report_age_hours: float = 0.0) -> dict[str, Any]:
    normalized = " ".join(text.split())
    negative = find_matches(NEGATIVE_PATTERNS, normalized)
    explicit = [] if negative else find_matches(EXPLICIT_SUBMIT_PATTERNS, normalized)
    suggest_words = [] if negative or explicit else find_matches(SUGGEST_ONLY_PATTERNS, normalized)

    if negative:
        intent = "defer_or_local"
        reason = "User wording asks to keep feedback local or not submit."
        submit_now = False
        ask_before_submit = False
    elif explicit:
        intent = "explicit_submit"
        reason = "User wording already authorizes uploading/submitting feedback."
        submit_now = True
        ask_before_submit = False
    elif suggest_words or issue_count >= 3 or has_p0 or report_age_hours >= 24:
        intent = "suggest_submit"
        reason = "Feedback appears actionable, but submission is not explicitly authorized."
        submit_now = False
        ask_before_submit = True
    else:
        intent = "defer_or_local"
        reason = "No explicit submission authorization or strong submission trigger detected."
        submit_now = False
        ask_before_submit = False

    return {
        "intent": intent,
        "submit_now": submit_now,
        "ask_before_submit": ask_before_submit,
        "reason": reason,
        "matched": {
            "negative": negative,
            "explicit_submit": explicit,
            "suggest_only": suggest_words,
        },
        "status_rule": "Always tell the user whether the feedback file was submitted; include URL/email result when submitted, or local path plus upload recommendation when not submitted.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Resolve EA-feedback submission intent from user wording.")
    parser.add_argument("--user-request", required=True, help="Latest relevant user request or combined request text.")
    parser.add_argument("--issue-count", type=int, default=0, help="Detected actionable issue count.")
    parser.add_argument("--has-p0", action="store_true", help="Report contains at least one P0 issue.")
    parser.add_argument("--report-age-hours", type=float, default=0.0, help="Age of report in hours.")
    args = parser.parse_args()

    print(
        json.dumps(
            classify(
                args.user_request,
                issue_count=args.issue_count,
                has_p0=args.has_p0,
                report_age_hours=args.report_age_hours,
            ),
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
