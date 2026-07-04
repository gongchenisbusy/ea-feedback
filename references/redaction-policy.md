# Redaction Policy

EA-feedback reports may be submitted publicly. Apply redaction before GitHub or email submission.

## Always Redact

- API keys, tokens, passwords, cookies, session IDs.
- Browser profile paths.
- Institution login URLs containing user/session data.
- Private Zotero credentials or local API secrets.
- Raw research data contents unless the user explicitly approves sharing.
- Private emails other than the configured feedback mailbox.

## Usually Redact

- Absolute home paths such as `/Users/alice/...`; replace username with `<user>`.
- Local cache paths.
- Machine-specific temporary directories.
- Full terminal logs when a short excerpt is enough.

## Usually Keep

- EA public version string.
- Package compatibility name such as `ea-v0-2`.
- Relative project paths.
- Command names.
- Error codes.
- Non-sensitive file counts and status summaries.
- Public repository names and public documentation links.

## Redaction Markers

Use clear placeholders:

- `<user>`
- `<token-redacted>`
- `<email-redacted>`
- `<path-redacted>`
- `<raw-data-redacted>`

## Rule

If a detail is useful for local debugging but risky for a public issue, keep it in the local report appendix and omit or summarize it in the GitHub issue body.
