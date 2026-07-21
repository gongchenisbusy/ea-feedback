# Issue Taxonomy

Use this taxonomy to classify EA feedback issues.

## Severity

- `P0`: Blocks ordinary use, causes data-risk behavior, prevents installation, breaks core workflow, or creates severe public-user confusion.
- `P1`: Significant UX/runtime/workflow problem that slows users, causes repeated repair work, or undermines confidence.
- `P2`: Noticeable friction, documentation gap, naming inconsistency, or improvement opportunity.
- `P3`: Nice-to-have polish or future enhancement.

## Confidence

- `high`: Direct evidence from command output, file state, health/eval finding, or reproducible steps.
- `medium`: Strongly supported by user feedback plus artifact pattern.
- `low`: Plausible hypothesis that needs developer validation.

## Categories

1. `runtime-error`
   - Tracebacks, failed commands, health/eval failures, schema mismatches, invalid references.
2. `review-provenance`
   - Duplicate review records, overly strict review state, provenance schema friction, confusing confirmation flow.
3. `ux-friction`
   - Confusing questions, excessive internal terminology, unclear next step, user-visible noise.
4. `token-context`
   - Large skill loading, repeated file reads, excessive JSON output, context compaction pressure.
5. `over-execution`
   - Agent writes projects/reports/files when user only asked for advice.
6. `under-execution`
   - Agent only talks when user asked for concrete project, report, or processing output.
7. `file-proliferation`
   - Too many files for small interaction, duplicated records, hard-to-follow project state.
8. `literature-workflow`
   - Hidden literature library, unclear Zotero/browser/institution boundary, unsafe acquisition assumptions.
9. `submission-workflow`
   - Feedback cannot be submitted, issue body lacks evidence, email/GitHub path unclear.
10. `install-version`
    - EA version identity confusion, package/skill naming mismatch, install-check failure.
11. `documentation`
    - Missing public docs, stale examples, CLI help mismatch, unclear recovery path.
12. `feature-request`
    - User needs a new capability or workflow not currently supported.
13. `safety-boundary`
    - Risk of leaking credentials, raw data, institution access, private paths, or unsupported scientific claims.

## Evidence Expectations

Each issue should include at least one evidence item:

- command output excerpt,
- file path and summarized content,
- user-visible answer snippet,
- count or metric,
- reproduction step,
- existing EA report/eval/health finding,
- user-provided complaint.

Avoid unsupported claims. If evidence is weak, mark confidence `low` and phrase as a hypothesis.

Structured `warning_codes`, `warning_count`, and `severity: warning` records are not runtime failures by themselves. Promote a finding to P0/P1 only when current validation fails, an explicit error/traceback is present, or a failed/partial execution event remains current or unreconciled.

## Safe Recommendation Rules

Good recommendations:

- reduce unnecessary context loading,
- improve progressive disclosure,
- add explicit user confirmation before high-impact writes/submissions,
- provide CLI helpers for repetitive schema-safe operations,
- improve wording or output shape,
- add tests around the failing workflow.

Dangerous recommendations:

- remove raw data protection,
- remove review gates globally,
- remove provenance/traceability entirely,
- default to Zotero/browser/institution login,
- submit public issues without redaction,
- silently apply scientific interpretations.
