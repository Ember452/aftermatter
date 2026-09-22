# Security Policy

## Reporting a vulnerability

Use GitHub's private vulnerability reporting:
<https://github.com/Ember452/aftermatter/security/advisories/new>.

Please do **not** open a public issue for anything that could let one user read another
person's agent sessions, prompts, credentials or local paths — those are the data classes
this project is explicitly designed to keep on the machine.

Reports are triaged as soon as possible. Fixed issues are credited in the release notes
unless you ask not to be.

## Boundaries this project commits to

The normative statement is `docs/architecture/overview.md` section 8 ("安全与隐私边界");
in short:

- **Local first.** Raw session files never leave the machine. Only findings and metric
  summaries are uploaded, and the outbound pipeline has a redaction level floor
  (`standard`: path normalisation, secret/PII stripping, prompts reduced to semantic
  facets).
- **No original text in artifacts.** Raw sessions, full prompts and real absolute paths
  must not appear in uploaded payloads or in test fixtures.
- **Bounded writes.** Repairs are restricted to a path whitelist with a diff-size limit,
  run dry-run first, require explicit confirmation to apply, and snapshot content hashes
  before writing so an intervention can be reverted.
- **Sandbox by default.** Replaying validation commands uses no network, CPU/memory
  limits, a hard timeout and read-only repository mounts.

## Implementation status

As of the M0 skeleton there is **no released functionality**: the boundaries above are
design contracts, and each one becomes enforceable only with the milestone that implements
it (M1 evidence kernel and redaction, M4 bounded repair, M5 sandbox replay). If you find a
gap between what the documentation promises and what the current code actually does, that
is a defect — please report it through the channel above.
