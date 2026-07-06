# Submission Policy

## Default GitHub Target

Default repository:

```text
gongchenisbusy/Experimental-Assistant
```

Default issue URL:

```text
https://github.com/gongchenisbusy/Experimental-Assistant/issues
```

Use GitHub issue submission when:

- the user explicitly asks to submit/upload/send/publish the finished feedback to the developer side, or
- the report meets an automatic submission trigger and the user confirms after being asked, and
- GitHub authentication/tooling is available.

Suggested labels when available:

- `feedback`
- `ea-feedback`
- `ux`
- `developer-experience`

Do not assume labels exist; issue creation should still work without labels.

## Submission Triggers

Suggest submission when:

- report has at least 3 actionable issues,
- any issue is `P0`,
- report file age exceeds 24 hours and submission status is still local draft,
- user says they are testing/updating another EA version,
- user explicitly requests submission.

## Submission Intent Levels

Classify the latest relevant user instruction before deciding whether to ask again. Use `scripts/resolve_submission_intent.py` when the wording is not obvious.

### `explicit_submit`

Treat this as already confirmed. Generate the feedback file, redact the public body, submit to GitHub when available, then report the URL.

Examples:

- "把这个反馈文件上传开发者端"
- "修改好就可以上传开发者端了"
- "生成优化建议并提交到 GitHub issue"
- "整理完直接发给开发者"
- "Please submit this EA feedback after creating the file"

Do not ask for another confirmation in this state. Ask only when:

- redaction cannot safely remove private data,
- the target is ambiguous or differs from the default repository/mailbox,
- GitHub/email tooling is unavailable,
- the requested action would expose raw research data or credentials.

### `suggest_submit`

Use this when the report is actionable but the user has not authorized submission. Tell the user the file status and ask once whether to upload.

### `defer_or_local`

Use this when the user asks only for a local file, says not to submit, or the feedback is still exploratory. Report the local path and, if appropriate, suggest upload as a next step.

## GitHub Issue Body

Use a concise public-safe body:

- Summary.
- EA version.
- Top issues with severity and evidence.
- Link or mention local feedback file path if private.
- Redaction note.

Avoid dumping raw logs unless they are short and safe.

## Email Fallback

Fallback recipient:

```text
ea_feedback@163.com
```

Use email fallback when:

- GitHub is unavailable,
- user lacks GitHub permission,
- the repository issue tracker is unavailable,
- user prefers email.

By default, prepare an email draft file when GitHub is unavailable. Send email only if a trusted mail connector is available and the user has explicitly authorized sending; the authorization may come from the original request and does not need to be repeated.

Suggested email subject:

```text
[EA-feedback] <Feedback ID> <short summary>
```

## Submission Record

After submission, update the local feedback report or create a sidecar record outside the EA project:

```yaml
feedback_id: EA-FB-...
submitted_at: ...
channel: github_issue | email_draft | email_sent
target: ...
url_or_file: ...
confirmed_by_user: true
```

Do not write this record into an EA experiment project unless the user explicitly chooses that storage location.

## User-Facing Status

Always close with one clear status line:

- submitted: include the GitHub issue URL or sent-email destination.
- email draft only: include the draft path and say it was not sent.
- local only: include the report path and whether upload is recommended.
