# EA-feedback Workflow and Build Design

## Design Intent

EA-feedback is an independent Codex skill for auditing Experimental Assistant (EA) runs. It should help developers understand what went wrong or what felt bad during EA package tests, manual trials, user-experience sessions, and version-update checks.

It is deliberately separate from EA. It must not ask EA to add bulky feedback-only artifacts, and it must not mutate EA project files. It reads whatever evidence already exists: current visible conversation, EA project files, health/eval/brief outputs, planning files, terminal logs, user notes, package test output, git state, and installed skill metadata.

## Core Use Cases

1. A user tries EA for a while, then asks for feedback collection.
2. A developer runs EA tests or release checks, then asks for issue discovery.
3. A user describes a subjective UX problem; EA-feedback maps it to likely workflow, CLI, documentation, or skill-design causes.
4. A feedback report has accumulated enough issues and should be submitted to the EA repository.
5. GitHub submission is unavailable; EA-feedback prepares an email draft for the developer mailbox.

## Evidence Collection

Collect evidence without modifying EA state:

- EA CLI version from `ea version` when available.
- Installed EA skill paths and `SKILL.md` size/line counts.
- Candidate EA project roots containing `EA_PROJECT.md`.
- Project config, rule card, latest briefs, latest eval files, open items, progress, reviews, and provenance summaries.
- Existing planning files such as `task_plan.md`, `progress.md`, `findings.md`, and `.planning/*` when present.
- Git status and recent changed files for the workspace.
- User-provided notes and visible conversation summary.
- Existing logs or command outputs supplied by the user.
- Recent `literature/**/acquisition_status*.{md,json}` and `zotero_codex_readiness.*` sidecars, summarized as acquired/blocked counts only.

Do not run mutating EA commands such as `ea eval project` or `ea brief project` unless the user explicitly requests it. Prefer reading existing artifacts.
Do not read cookies, credentials, raw PDFs, or private full text while collecting literature status.

## Analysis Procedure

1. Separate facts, user perception, and agent inference.
2. Create candidate issues from:
   - explicit user complaints,
   - command failures,
   - health/eval findings,
   - repeated or redundant actions,
   - confusing user-visible output,
   - missing submission or literature guidance,
   - file proliferation,
   - strict review/provenance state conflicts,
   - context/token pressure.
3. For each candidate issue, classify it with `issue-taxonomy.md`.
4. Identify likely causes with confidence labels:
   - high: direct command output or file evidence,
   - medium: consistent pattern from artifacts and user report,
   - low: plausible hypothesis requiring developer validation.
5. Propose safe optimizations that preserve EA's core architecture.
6. Add acceptance criteria that developers can test.
7. Mark non-goals and dangerous shortcuts when relevant.

## Feedback File Lifecycle

Feedback is aggregated into one report rather than one issue per problem. A report may grow across a testing period.

Recommended file naming:

```text
EA-FB-YYYYMMDD-HHMMSS-<slug>.md
```

Recommended output directory:

```text
ea-feedback-reports/
```

Submission should be suggested when:

- the user explicitly asks,
- issue count is high enough to be actionable,
- the report is mature and coherent,
- the report is older than 24 hours and unsubmitted,
- the user is about to test or update another EA version.

If the user already says to upload/submit/send the finished feedback to developers, treat that instruction as submission authorization and do not ask again after generating the file. This is especially important for feedback UX: the skill should reduce user effort rather than add another confirmation loop.

## Public Submission

Default target:

```text
https://github.com/gongchenisbusy/Experimental-Assistant/issues
```

Fallback email:

```text
ea_feedback@163.com
```

Before submission, produce a public-safe issue/email body and redact sensitive data. Use the current user instruction to choose the submission path:

- explicit upload/submit/send instruction: submit directly after redaction and report the URL or email result.
- actionable report without explicit authorization: tell the user the file is ready and ask once whether to upload.
- local-only or negative instruction: do not submit; report the local path.

Use `scripts/submit_feedback.py` as the default submission helper when possible. It keeps submission token-light by checking duplicate feedback IDs through issue title metadata only, without reading issue bodies or comments.

Submission is bounded:

1. Try GitHub once when `gh` is available/authenticated.
2. If GitHub fails, prepare one local email draft fallback.
3. If both channels fail, report `submission_failed` with the immediate reason and concise recovery guidance. Do not try browser login, GitHub account connection, email account setup, or repeated network retries inside EA-feedback.

## What Not To Do

- Do not modify EA project files or EA skill files.
- Do not write feedback-only logging requirements into EA unless the recommendation is justified by EA's own UX/context-management needs.
- Do not recommend removing raw data protection, review gates, provenance, traceability, or public-user safety boundaries just to reduce tokens or files.
- Do not expose private local paths, tokens, browser profiles, institution access details, or raw research data in public issues.
- Do not submit to GitHub or email when the user has not authorized it. An explicit instruction such as "生成后上传开发者端" counts as authorization.
- Do not read existing issue bodies/comments to decide whether a feedback report is duplicated; exact feedback-ID metadata checks are enough before submission.
- Do not keep retrying failed GitHub/email channels. Stop at the submission-failed channel and tell the user how to resolve it manually or in a separate Codex task.
