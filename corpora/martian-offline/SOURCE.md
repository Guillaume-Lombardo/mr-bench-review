# martian-offline — provenance

Imported 2026-09-30 from [withmartian/code-review-benchmark](https://github.com/withmartian/code-review-benchmark)
at commit `e616e849755441da38f18bf3adba2c9583b03803`, `offline/golden_comments/*.json`, by
`tools/import_martian_offline.py`.

## Credit and licences

- Golden comments: © 2025 Martian (withmartian.com), **MIT** licence. Many PRs come from the
  Greptile evaluation forks (`github.com/ai-code-review-evaluation/*`).
- Code: Keycloak (Apache-2.0), Grafana (AGPL-3.0), Discourse (GPL-2.0-or-later). Upstream
  licence files are kept on both branches. Sentry (Functional Source License, source-available)
  and Cal.com (enterprise code under the Cal.com Commercial License) are excluded; see
  EXCLUDED.md.
- `discourse-graphite` PR 3 (`martian-offline-013`) is excluded because GitHub push protection
  flags strings in its snapshot as secrets (`tools/sources/martian-offline.push-protection.json`);
  re-including it needs the owner's confirmation that they are public test values.

## Figures

50 source PRs; 29 imported (all real, 93 unlocated expected issues), 21 excluded: 20 Sentry and
Cal.com PRs for licence reasons and one blocked by push protection.

## Rebuilding base and head

`head` is the PR head (`refs/pull/N/head`) of the repository named in the golden file, which is
either the upstream project or an evaluation fork. `base` is:

1. the merge-base with the first parent of `refs/pull/N/merge` when GitHub still has that ref
   (open PRs; this is the PR's real target branch);
2. otherwise the merge-base with the default branch, taken before the merge commit for PRs
   that were merged;
3. for evaluation forks whose PRs target per-PR branches (`*-baseline`, `*-pre`, …), the
   closest branch that does not contain the head.

The resolved `(base, head)` upstream SHAs are pinned in `tools/sources/martian-offline.lock.json`
so that later runs rebuild identical cases even if a PR changes.

## Mapping

| Martian | contract v1 |
| --- | --- |
| golden comment (no file, no line) | unlocated issue: `file`, `line_start`, `line_end` all `null` |
| `comment` | `source_text` (verbatim) and `description`; first sentence → `title` |
| `category` bug, data, concurrency, api | `correctness` |
| `category` security | `security` |
| `category` test_gap | `tests` |
| `category` perf, doc_defect, style, speculative | `maintainability` |
| `severity` Low/Medium/High/Critical | `low`/`medium`/`high`/`critical` |
| scoring profile | `annotator_notes` (`Strict`: bug, security, concurrency, data, api; `Core`: + perf, test_gap, doc_defect; `All`: + style, speculative) |
| `pr_title` | `mr_title`; the description lists the PR's commit subjects |

## Known gaps

- Issues are unlocated; a location could be proposed with an LLM and confirmed by a human in
  a later minor version.
- Case ids keep the order of the golden files; the numbers of excluded PRs are reserved.
