# review-bench — provenance

Imported 2026-09-30 from [hyperneolabs/review-bench](https://github.com/hyperneolabs/review-bench)
at commit `93f31c224448e453c00768780795bd6bf6ab4234` (corpus `corpus/v0.1`, frozen 2026-09-25)
by `tools/import_review_bench.py`.

## Credit and licences

- Ground truth, case selection and methodology: review-bench contributors, licensed
  **CC BY 4.0**. Attribution: "review-bench corpus v0.1, hyperneolabs,
  https://github.com/hyperneolabs/review-bench, CC BY 4.0". Changes made here: format
  conversion only (see mapping), described below.
- Code: each case snapshots an upstream project under its own licence, recorded in
  `origin.license` (MIT, BSD-3-Clause or Apache-2.0). Upstream licence files are kept on both
  branches.

## Mapping

| review-bench | contract v1 |
| --- | --- |
| `kind: bug` / `control` | `kind: real` / `clean` |
| `source.review_base_sha` / `review_head_sha` | upstream trees of `base` / `head` |
| `defect.ground_truth[0]` | issue location; further ranges → `alternative_locations` |
| `defect.description` | `source_text` (verbatim), first sentence → `title`, full text + provenance → `description` |
| no category | `category: correctness` (to be reviewed) |
| no severity | `severity: null` |
| `case_id` | `origin.source_case`; cases numbered `review-bench-NNN` in `case_id` order |

MR title and description come from the upstream head commit message, without issue numbers
and trailers. Fix PR, fix commit and ground-truth notes are kept in `annotator_notes`.

## Known gaps

- Categories are a default, not an annotation; severities are absent.
- The source has one defect per bug case; other issues a reviewer might raise are not listed.
