# Feedback Report Schema

A developer-facing EA feedback report should be Markdown and structured enough to paste into a GitHub issue.

## Header

Required fields:

- `Feedback ID`
- `Created`
- `Status`
- `EA version`
- `EA skill path`
- `EA project roots inspected`
- `Testing scenario`
- `Submission status`

## Sections

Recommended structure:

```markdown
# EA Feedback Report: <Feedback ID>

## Summary

## Environment

## User-Reported Concerns

## Automatically Detected Issues

### <P0/P1/P2> <short title>

- Category:
- Severity:
- Confidence:
- Evidence:
- Likely cause:
- Impact:
- Safe recommendation:
- Acceptance criteria:
- Non-goals / risks:

## Cross-Cutting Recommendations

## Submission Recommendation

## Appendix: Evidence Inventory
```

## Feedback ID

Use:

```text
EA-FB-YYYYMMDD-HHMMSS-<short-slug>
```

The ID should be stable once the report is created. If a report is updated later, keep the same ID and add an update note.

## Submission States

- `draft_local`
- `ready_for_user_review`
- `submitted_github`
- `email_draft_prepared`
- `deferred_by_user`

## Issue Writing Style

- Lead with developer-actionable findings.
- Preserve user experience language, but add technical root-cause hypotheses.
- Separate observations from inferences.
- Use concrete acceptance criteria.
- Keep public issue bodies concise; put bulky evidence in local report attachments when needed.
