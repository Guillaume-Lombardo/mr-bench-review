# AACR — provenance

Imported 2026-09-30 from [alibaba/aacr-bench](https://github.com/alibaba/aacr-bench) at commit
`68a569759289a83654a59d06db2a72910edf0a4a` (`dataset/positive_samples.json` and
`dataset/negative_samples.json`) by `tools/import_aacr.py`.

## Credit and licences

- Annotations: AACR-Bench © Alibaba, **Apache-2.0**.
- Code: each case snapshots an upstream project under its own licence, recorded in
  `origin.license` and checked against the licence file of the head snapshot: Apache-2.0 (71
  cases), MIT (54), AGPL-3.0-only OR SSPL-1.0 OR Elastic-2.0 (Elasticsearch, redistributed under
  the AGPL option, 14), LGPL-2.0-or-later (11), AGPL-3.0 (10), BSD-3-Clause (6), GPL-2.0-or-later
  OR LGPL-2.1-or-later (4), GPL-3.0 (3), Zlib (2), Apache-2.0 OR MIT (2).
- Excluded for licence reasons (see EXCLUDED.md): n8n (Sustainable Use License), timescaledb
  (Timescale License portions) and cherry-studio (user-segmented dual licence with a commercial
  licence for larger organisations).

## Base and head

The ticket assumed one of `source_commit`/`target_commit` would be the PR head. Checked on the
data: **`target_commit` is the PR head** (it lies on `refs/pull/N/head`; for PowerShell #24910 it
is the PR's last commit) and **`source_commit` is a commit of the branch the PR targets**,
often far ahead of the PR base. The base is therefore `merge-base(source_commit, target_commit)`,
computed from a treeless clone of the upstream history; with it, comment lines fall on the
changed lines and the diff sizes are close to (usually a little below) `change_line_count`.
Eleven PR heads were force-pushed away upstream and cannot be rebuilt; they are excluded.

## Mapping

| AACR | contract v1 |
| --- | --- |
| positive comment | expected issue; `note` → `source_text` (verbatim) and `description`, first sentence → `title` |
| Code Defect | `correctness` |
| Security Vulnerability | `security` |
| Maintainability and Readability, Performance | `maintainability` |
| `category` | `source_category` |
| no severity | `severity: null` |
| `path`, `from_line`, `to_line` (right side) | `file`, `line_start`, `line_end` (swapped when inverted) |
| lines not on a changed line | `outside_diff: true` (65 issues) |
| `side: "left"` (8 comments) or lines out of range at head | file-level issue (8 issues) |
| negative comment | `known_false_positives` (570 entries) |
| `is_ai_comment`, `source_model`, `context` | `annotator_notes` per issue |
| PR with only negative comments (4) | `kind: clean` with its `known_false_positives` |
| PR with positive comments | `kind: real` |

`comments` is parsed with `ast.literal_eval` when it is a string (it is already a list in this
revision); `eval` is never used. MR title: the subject of the PR's first commit; description:
the list of commit subjects (the PR title and body are not in the dataset). Case ids follow the
order of `positive_samples.json`, then negative-only PRs; excluded PRs keep their number.

## Figures

196 positive PRs + 4 negative-only PRs = 200 source PRs; 177 imported (173 real, 4 clean),
23 excluded. 1,297 expected issues (1,224 on changed lines) out of the 1,506 source comments;
the remainder belongs to excluded PRs.

## Strings flagged by secret scanning

The upstream snapshots of 23 cases contain strings that GitHub secret scanning classifies as
secrets: gemini-cli `oauth2.ts` (aacr-066 to 072), vLLM `registry.py` (aacr-109 to 112 and
aacr-200), uv `pip_install.rs` (aacr-113), DBeaver `plugin.xml` (aacr-115 to 118), Kestra
`Count.java` (aacr-128 to 130) and Symfony Twilio test fixtures (aacr-182 to 184). They are part
of the public upstream history (public client ids and test values). The owner reviewed them and
chose to keep these cases; the branches were pushed with GitHub push protection lifted.

## Known gaps

- No severity. Categories follow the source; Performance is folded into maintainability.
- Several comments can describe the same problem (different AI reviewers); they are kept as
  separate issues, as in the source.
