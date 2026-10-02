# Changelog

All changes per corpus. Versions follow the rules in README.md ("Versioning").

## 1.1.0 — unreleased (2026-10-02)

### curated
- Audit all 113 cases with AI-assisted annotation and snapshot-diff review; record the
  checker, per-case findings and limitations. Independent human release sign-off is pending.
- Correct inaccurate descriptions and examples, including cases 005, 021, 023, 029, 036,
  055, 082 and 106. Remove unsupported claims of executed upstream regression tests.
- Reclassify 064 and 095 as real and 066 as clean (its finding predates the snapshot diff).
- Add nine issues covering grouped-option sorting, skipped index checks, cookie flags,
  traceback source alignment, permission renaming, public typing compatibility, peer
  field fetching and srcset parsing; remove one misattributed finding.
- Corpus totals: 113 cases, 96 real, 17 clean, 114 issues. Snapshot SHAs and MR text unchanged.
- Add four executable source-level probes and refresh README statistics and reproduction
  guidance. Imported corpus annotations are unchanged.

## 1.0.0 — unreleased (not yet tagged)

Initial dataset, contract v1, validator, converters and CI.
- Validate alternative locations and known false-positive locations against snapshot files.
- Preserve trailing blank lines when counting file lines; empty files have zero lines.
- Add an Actions-suspended GitHub snapshot publisher and exclude snapshot branches from
  the project validation workflow. Existing imported workflows are disabled on GitHub.
- License original curated annotations, the annotation guide and original project documentation
  under CC BY 4.0; retain Apache-2.0 for tools, scripts and tests. Imported annotations and
  upstream snapshot licences are unchanged. See LICENSING.md.
Snapshots leave out the media and other binary files that the change does not touch (see
README.md, "Branches"); the repository shrinks from about 2.7 GB to about 1.2 GB and the diffs
are unchanged.

### curated (created 2026-09-30)
- 113 cases (95 real, 18 clean) from the selection made for bdf-review, with 5 pilot, 30 core
  and 78 extended cases. Eight large cases and six clean cases were added to the selection to
  reach the size and clean-share targets; one former control was reclassified as real.
- One selected case excluded (no upstream licence file in the snapshot), see EXCLUDED.md.
- Pilot and core annotated completely by the curator; second check pending.

### review-bench (created 2026-09-30)
- 27 cases (17 real, 10 clean) imported from hyperneolabs/review-bench corpus v0.1.

### aacr (created 2026-09-30)
- 177 cases (173 real, 4 clean) and 1,297 expected issues imported from alibaba/aacr-bench;
  23 PRs excluded (12 for licence reasons, 11 with an unreachable PR head).

### martian-offline (created 2026-09-30)
- 30 cases imported from withmartian/code-review-benchmark (Keycloak, Grafana, Discourse);
  20 Sentry and Cal.com PRs excluded for licence reasons.
