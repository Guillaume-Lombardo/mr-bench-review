# Curated corpus — provenance

Created 2026-09-30. Selected for bdf-review and moved here unchanged in substance.
Every case reproduces a public upstream commit; no code was
written or modified for the benchmark.

## Selection method

- **`real` cases (95).** Mined from about sixty open-source repositories: upstream fix commits
  that name the change that introduced the problem ("Regression in <sha>", "regressed in #N",
  "introduced by …"). For angular-cli and angular/components, which do not name it, the lines
  changed by the fix were blamed (SZZ). A candidate was kept when the fix touches lines added
  or changed by the introducing change, the introducing change is a reviewable unit (a squashed
  PR, a merge of a PR or a self-contained commit) and the problem has a user-visible effect.
  Cherry-picks and build-, documentation- or style-only fixes were dropped. The MR is the
  introducing change; the primary expected issue is what the later fix corrects.
- **Additions for the size mix (BENCH-01).** Eight large introducing changes (> 600 changed
  lines) were added from the same mined candidates so that at least ten cases force a
  multi-batch review.
- **`clean` cases (18).** Merged changes with tests whose added source lines were at least 90%
  unchanged upstream on 2026-09-30 and that no later commit reports as faulty. Six were added
  for BENCH-01 to reach the 15–20% target. "Clean" means *no known defect*, not proven correct.
  One former control (the singleton-callback change) was reclassified as `real` because the
  curator would raise an API-compatibility remark on it.
- **Annotation.** Pilot and core cases were reviewed completely by the curator: besides the
  primary issue, every point a senior reviewer would raise was added (mostly missing tests for
  behaviour changes, one API-compatibility remark, one error-handling remark). Extended cases
  carry the primary issue only. Every case still needs the second check required before
  `v1.0.0`; the status is recorded in each case's `annotator_notes`.
- **Neutral MR text.** Titles and descriptions are the upstream commit subject and body without
  issue numbers, trailers, links to issues and ticket prefixes. They are the developer's own
  words and never mention the expected issues. Merge commits use the PR title from the body.
- **Identifiers.** Cases were shuffled with a fixed seed before numbering, so `case-NNN` says
  nothing about project, language, kind or tier.

## Branches

`bench/curated/<id>/base` is an orphan commit holding the upstream tree at the introducing
commit's first parent; `bench/curated/<id>/head` is one commit on top holding the tree at the
introducing commit. Author `mr-bench-review <bench@mr-bench-review.invalid>`, date
2026-01-01T00:00:00Z, messages `base snapshot` and `change`. Rebuild with
`uv run tools/build_curated.py --work <bare repo>`; it checks that the SHAs match.

## Licences

All upstream projects allow public redistribution: MIT (50 cases), Apache-2.0 (32),
BSD-3-Clause (30), EPL-2.0 (1). Each snapshot keeps its upstream licence file (at the root, or
for one older Spring Framework tree under `src/docs/dist/license.txt`).

## Known gaps

- Complete annotation and second check are pending for the 78 extended cases.
- Upstream code and fixes are public, so models may have seen them; results compare reviewers
  relative to each other.
- Size is counted on the whole change, tests and documentation included.
