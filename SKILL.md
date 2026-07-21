---
name: ea-feedback
description: Audit Experimental Assistant (EA) test runs, manual trials, user-experience sessions, and package/check outputs to find developer-actionable issues and generate or submit a feedback report. Use when the user asks to review EA usage/testing, create EA feedback, summarize EA problems, prepare an EA optimization issue, upload/submit EA feedback to GitHub/email/developers, or evaluate EA version-update readiness from recent Codex runs.
---

# EA Feedback

## Purpose

Use this skill as a read-only reviewer for Experimental Assistant (EA) usage. It turns EA test runs, manual trials, package checks, user complaints, and available project artifacts into a developer-facing feedback report with evidence, likely root causes, safe optimization suggestions, and submission-ready text.

This skill must not modify EA projects, EA skill files, raw research data, or EA runtime behavior. It may write feedback artifacts outside the EA project or in a user-approved feedback output directory.

## Workflow

1. Identify the scope: current thread, selected EA project, package test output, manual trial, or user-supplied notes.
2. Read `references/feedback-workflow.md` for the full operating procedure.
3. Run `scripts/collect_ea_context.py` to collect read-only evidence into a JSON file. It discovers the actual EA executable in the order `EA_BIN` → current Python distribution/module → project `.venv` → `PATH`, uses active EA Skill installs only by default, records structured execution events, and may summarize recent EA literature acquisition status sidecars and Zotero readiness files. Do not pass `--include-skill-backups` unless historical comparison is explicitly requested. Collection must not read cookies, credentials, raw PDFs, private full text, or probe GitHub authentication.
4. Combine the user's subjective feedback with collected evidence. Use `references/issue-taxonomy.md` to classify issues.
5. Run `scripts/render_feedback_report.py` to create a draft Markdown feedback report.
6. Improve the report with agent judgment: merge duplicates, add root-cause hypotheses, add safe recommendations, and mark confidence.
7. Read `references/submission-policy.md` before any submission. Treat an explicit user request to upload/submit/send the finished feedback to developers as submission confirmation; do not ask again unless redaction risk, target ambiguity, or unavailable tooling blocks safe submission.
8. Use `scripts/submit_feedback.py` for submission whenever possible. Only this authorized submission step checks GitHub readiness. It validates UTF-8/render/redaction, checks duplicate feedback IDs by GitHub issue title metadata only, submits once through GitHub when available, and otherwise prepares either a verified email draft or an explicitly requested public-safe browser handoff. It emits `submission_failed` instead of retrying account/login flows.
9. End by reporting the feedback file status: submitted URL, email draft path, local report path, or submission-failed reason with concise recovery guidance.

## Report Rules

- One feedback file can contain multiple issues.
- Merge equivalent findings across projects or repeated artifacts; retain distinct evidence under one canonical issue.
- Treat structured warnings as warnings, not runtime failures; escalate only explicit errors, failed current validation, or unreconciled failed execution events.
- Include EA version, feedback ID, creation time, evidence sources, issue severity, confidence, safe recommendations, and acceptance criteria.
- Keep recommendations conservative: reduce waste and friction without removing EA's core protections such as raw-data safety, review gates, provenance, traceability, and public-user boundaries.
- Redact credentials, tokens, private emails, and sensitive local paths before public submission. See `references/redaction-policy.md`.

## Submission Triggers

Suggest submission when any of these are true:

- The user explicitly asks to submit, upload, send, or publish the finished feedback to developers.
- The report contains several actionable issues.
- The report is complete enough for developer action.
- The feedback file is older than 24 hours and still unsubmitted.
- The user says they are updating, releasing, or testing another EA version.

If the current or earlier user instruction already contains explicit submission authorization, submit after redaction without a second confirmation. If submission is only recommended by heuristics, ask once before creating a GitHub issue or sending email.

## Resources

- `references/feedback-workflow.md`: end-to-end process and design plan.
- `references/issue-taxonomy.md`: issue classes, severity, and evidence expectations.
- `references/report-schema.md`: report structure and fields.
- `references/submission-policy.md`: GitHub issue and email fallback rules.
- `references/redaction-policy.md`: public-safe redaction guidance.
- `scripts/collect_ea_context.py`: read-only EA context collector.
- `scripts/render_feedback_report.py`: deterministic draft report renderer.
- `scripts/resolve_submission_intent.py`: classify whether the user already authorized submission or should only be asked/suggested.
- `scripts/submit_feedback.py`: bounded GitHub/email-draft submission helper with failure-channel output.
