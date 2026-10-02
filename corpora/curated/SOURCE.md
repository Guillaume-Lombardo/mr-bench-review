# Curated corpus — provenance

Created 2026-09-30. Selected for bdf-review and moved here unchanged in substance.
Every case reproduces a public upstream commit; no code was
written or modified for the benchmark.

## Selection method

- **Originally selected `real` cases (95).** Mined from about sixty open-source repositories: upstream fix commits
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
- **Originally selected `clean` cases (18).** Merged changes with tests whose added source lines were at least 90%
  unchanged upstream on 2026-09-30 and that no later commit reports as faulty. Six were added
  for BENCH-01 to reach the 15–20% target. "Clean" means *no known defect*, not proven correct.
  One former control (the singleton-callback change) was reclassified as `real` because the
  curator would raise an API-compatibility remark on it.
- **Annotation.** Pilot and core cases were reviewed completely by the curator: besides the
  primary issue, every point a senior reviewer would raise was added (mostly missing tests for
  behaviour changes, one API-compatibility remark, one error-handling remark). Extended cases
  initially carried the primary issue only. On 2026-10-02, Codex performed an AI-assisted
  annotation and snapshot-diff audit of all 113 cases, recording a case-specific result in
  `annotator_notes` and [the audit log](audit/2026-10-02.json). The corpus now has 97 real
  cases, 16 clean cases and 115 issues: cases 064 and 095 were reclassified as real, and
  case 066 remains real with a newly reproduced Enter-activation issue replacing the
  pre-existing Space finding. Ten new issues were added and one misattributed issue
  removed. This is not the independent human second-person sign-off required for release.
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

Original annotations by the bdf-review project are licensed under
[CC BY 4.0](../../LICENSE-CC-BY-4.0); see [LICENSING.md](../../LICENSING.md).
This grant excludes upstream MR titles, descriptions, quoted material and code, which retain
their existing licences.

All upstream projects allow public redistribution: MIT (50 cases), Apache-2.0 (32),
BSD-3-Clause (30), EPL-2.0 (1). Each snapshot keeps its upstream licence file (at the root, or
for one older Spring Framework tree under `src/docs/dist/license.txt`).

## Known gaps

- The current 16/113 clean cases (14.2%) fall below the 15–20% selection target.
- The AI-assisted annotation check covers all tiers; independent human release sign-off
  remains pending for every case.
- Full upstream test suites were not run. The four focused source-level probes can be rerun
  with `uv run python corpora/curated/audit/reproduce.py` (Node.js and Git snapshot objects
  required). Upstream fix links are evidence, not proof that a regression test was run.
- Upstream code and fixes are public, so models may have seen them; results compare reviewers
  relative to each other.
- Size is counted on the whole change, tests and documentation included.

## Native Enter follow-up for case 066

Generate the browser fixture with:

```sh
uv run python corpora/curated/audit/reproduce.py --browser-fixture /tmp/curated-case066.html
uv run python -m http.server 8766 --bind 127.0.0.1 --directory /tmp
```

Open `http://127.0.0.1:8766/curated-case066.html` in Chromium. Focus each tab and press
Enter once (a real key press, not `dispatchEvent`). The displayed click counts should be
`base-href: 1`, `head-href: 2`, `base-no-href: 0`, `head-no-href: 1`, and zero for both
disabled controls. The fixture cancels native navigation in its click listeners, as routed
links do, so focus remains on the anchor. Without that cancellation, fragment navigation
can move focus and mask the second activation. This tests native DOM behavior with the
snapshot handlers; it is not a full Angular integration test.
