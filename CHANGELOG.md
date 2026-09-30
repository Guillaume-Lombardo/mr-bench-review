# Changelog

All changes per corpus. Versions follow the rules in README.md ("Versioning").

## 1.0.0 — unreleased (not yet tagged)

Initial dataset, contract v1, validator, converters and CI.
The repository's own content (tools, documentation, curated annotations) is licensed
under Apache-2.0.

### curated (created 2026-09-30)
- 113 cases (95 real, 18 clean) from the selection made for bdf-review, with 5 pilot, 30 core
  and 78 extended cases. Eight large cases and six clean cases were added to the selection to
  reach the size and clean-share targets; one former control was reclassified as real.
- One selected case excluded (no upstream licence file in the snapshot), see EXCLUDED.md.
- Pilot and core annotated completely by the curator; second check pending.

### review-bench (created 2026-09-30)
- 27 cases (17 real, 10 clean) imported from hyperneolabs/review-bench corpus v0.1.

### aacr (created 2026-09-30)
- 154 cases (151 real, 3 clean) and 1,156 expected issues imported from alibaba/aacr-bench;
  46 PRs excluded (12 for licence reasons, 11 with an unreachable PR head, 23 rejected by
  GitHub push protection as containing secrets).

### martian-offline (created 2026-09-30)
- 29 cases imported from withmartian/code-review-benchmark (Keycloak, Grafana, Discourse);
  20 Sentry and Cal.com PRs excluded for licence reasons and one rejected by GitHub push
  protection.
