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

- the user explicitly asks to submit, or
- the report meets an automatic submission trigger and the user confirms, and
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

Always ask for user confirmation before creating the issue.

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

By default, prepare an email draft file instead of sending automatically. Only send email if a trusted mail connector is available and the user explicitly confirms.

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
