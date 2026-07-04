---
name: ea-feedback
description: Audit Experimental Assistant (EA) test runs, manual trials, user-experience sessions, and package/check outputs to find developer-actionable issues and generate a feedback report. Use when the user asks to review EA usage/testing, create EA feedback, summarize EA problems, prepare an EA optimization issue, submit EA feedback to GitHub/email, or evaluate EA version-update readiness from recent Codex runs.
---

# EA Feedback

## Purpose

Use this skill as a read-only reviewer for Experimental Assistant (EA) usage. It turns EA test runs, manual trials, package checks, user complaints, and available project artifacts into a developer-facing feedback report with evidence, likely root causes, safe optimization suggestions, and submission-ready text.

This skill must not modify EA projects, EA skill files, raw research data, or EA runtime behavior. It may write feedback artifacts outside the EA project or in a user-approved feedback output directory.

## Workflow

1. Identify the scope: current thread, selected EA project, package test output, manual trial, or user-supplied notes.
2. Read `references/feedback-workflow.md` for the full operating procedure.
3. Run `scripts/collect_ea_context.py` to collect read-only evidence into a JSON file.
4. Combine the user's subjective feedback with collected evidence. Use `references/issue-taxonomy.md` to classify issues.
5. Run `scripts/render_feedback_report.py` to create a draft Markdown feedback report.
6. Improve the report with agent judgment: merge duplicates, add root-cause hypotheses, add safe recommendations, and mark confidence.
7. Read `references/submission-policy.md` before any submission. Submit only after user confirmation.
8. Use GitHub issue submission as the default path when authenticated and available. Use email draft fallback for `ea_feedback@163.com` when GitHub is unavailable or the user prefers email.

## Report Rules

- One feedback file can contain multiple issues.
- Include EA version, feedback ID, creation time, evidence sources, issue severity, confidence, safe recommendations, and acceptance criteria.
- Keep recommendations conservative: reduce waste and friction without removing EA's core protections such as raw-data safety, review gates, provenance, traceability, and public-user boundaries.
- Redact credentials, tokens, private emails, and sensitive local paths before public submission. See `references/redaction-policy.md`.

## Submission Triggers

Suggest submission when any of these are true:

- The user explicitly asks to submit.
- The report contains several actionable issues.
- The report is complete enough for developer action.
- The feedback file is older than 24 hours and still unsubmitted.
- The user says they are updating, releasing, or testing another EA version.

Even when a trigger fires, preview the report or issue body and ask for user confirmation before creating a GitHub issue or sending email.

## Resources

- `references/feedback-workflow.md`: end-to-end process and design plan.
- `references/issue-taxonomy.md`: issue classes, severity, and evidence expectations.
- `references/report-schema.md`: report structure and fields.
- `references/submission-policy.md`: GitHub issue and email fallback rules.
- `references/redaction-policy.md`: public-safe redaction guidance.
- `scripts/collect_ea_context.py`: read-only EA context collector.
- `scripts/render_feedback_report.py`: deterministic draft report renderer.
