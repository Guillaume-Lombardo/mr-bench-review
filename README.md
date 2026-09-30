# mr-bench-review

Merge-request review benchmark for [bdf-review](https://github.com/Guillaume-Lombardo/bdf-review).
It holds reviewable changes as Git branches and, for each one, the issues a good reviewer is
expected to raise. The bdf-review runner (`bdf-review bench run`, ticket T19) reads this
repository, fetches only the branches of the cases it runs, reviews each change and scores the
findings against the expected issues.

- **`curated`** (default corpus) — MRs selected for bdf-review from real public changes in
  Python, Java and Angular/TypeScript projects, annotated by hand.
- **Imported corpora** — public benchmarks converted to the same contract. They are never
  evaluated unless the runner is given `--corpus <name>`.

Everything is plain Git: branches and files. The repository can be mirrored with
`git push --mirror` (for example to an internal GitLab) and cloned over anonymous HTTPS.

## Corpora

<!-- stats:begin -->
| Corpus | Created | Default | Cases | Clean | Issues | Location | Severity | Licence |
| --- | --- | --- | ---: | ---: | ---: | --- | --- | --- |
| `aacr` | 2026-09-30 | no | 177 | 4 | 1297 | lines | no | Apache-2.0 annotations; upstream code per case, see cases/*.json |
| `curated` | 2026-09-30 | yes | 113 | 18 | 106 | lines | yes | Apache-2.0 annotations; upstream code per case, see cases/*.json |
| `martian-offline` | 2026-09-30 | no | 30 | 0 | 96 | none | yes | MIT golden comments; upstream code per case, see cases/*.json |
| `review-bench` | 2026-09-30 | no | 27 | 10 | 17 | lines | no | CC-BY-4.0 annotations; upstream code per case (MIT, BSD-3-Clause, Apache-2.0) |

### `aacr`

| Dimension | Distribution |
| --- | --- |
| language | cpp 32, java 25, go 22, typescript 21, python 20, c 15, javascript 12, php 11, csharp 10, rust 9 |
| size | small 83, medium 76, large 18 |
| kind | real 173, clean 4 |
| tier | none 177 |
| category | maintainability 639, correctness 607, security 51 |
| severity | null 1297 |

### `curated`

| Dimension | Distribution |
| --- | --- |
| language | python 42, java 35, typescript 35, javascript 1 |
| size | small 59, medium 44, large 10 |
| kind | real 95, clean 18 |
| tier | extended 78, core 30, pilot 5 |
| category | correctness 85, tests 10, maintainability 6, security 5 |
| severity | high 50, medium 45, low 9, critical 2 |

### `martian-offline`

| Dimension | Distribution |
| --- | --- |
| language | java 10, ruby 8, go 8, other 2, typescript 2 |
| size | medium 11, small 10, large 9 |
| kind | real 30 |
| tier | none 30 |
| category | correctness 68, maintainability 18, security 9, tests 1 |
| severity | medium 35, low 26, high 26, critical 9 |

### `review-bench`

| Dimension | Distribution |
| --- | --- |
| language | go 16, javascript 7, rust 2, typescript 1, python 1 |
| size | medium 16, small 11 |
| kind | real 17, clean 10 |
| tier | none 27 |
| category | correctness 17 |
| severity | null 17 |
<!-- stats:end -->

The curated target mix is roughly 40% Python, 30% Java and 30% Angular/TypeScript, 15–20%
clean cases, at least ten large cases and all four categories. The actual curated mix is 42
Python, 35 Java, 35 TypeScript (25 of them from Angular projects) and 1 JavaScript; 18 clean
cases (16%); 10 large cases. See each corpus's `SOURCE.md` for provenance, licences,
conversion choices and known gaps, and `EXCLUDED.md` for cases that were dropped and why.

The upstream snapshots of 24 imported cases (23 `aacr`, 1 `martian-offline`) contain public
client ids and test tokens that GitHub secret scanning classifies as secrets; the owner chose to
keep them. A mirror with push protection enabled needs a bypass for these branches; see the
corpus `SOURCE.md` files for the flagged paths.

Not imported:

- `qodo` (Hugging Face `Qodo/PR-Review-Bench`) and `swe-care` (Hugging Face
  `inclusionAI/SWE-CARE`): their data is only published on Hugging Face, which the build
  environment could not reach on 2026-09-30, so neither format nor licence has been checked.
  To be revisited from an environment with Hugging Face access.
- SWR-Bench (arXiv 2509.01494): no public data location found.

## Dataset contract v1

`dataset.json` holds `{"schema_version": 1, "dataset_version": "<semver>"}`. The executable
form of the contract is `tools/contract.py` (Pydantic, unknown fields rejected); bdf-review
carries an identical copy.

```
README.md, ANNOTATION_GUIDE.md, CHANGELOG.md, dataset.json
corpora/<corpus>/corpus.json                  corpus metadata
corpora/<corpus>/SOURCE.md                    provenance, licences, conversion notes, known gaps
corpora/<corpus>/EXCLUDED.md                  cases dropped, with reasons
corpora/<corpus>/cases/<case_id>.json         one file per case
corpora/<corpus>/labels/human/<case_id>.json  human judgments for judge calibration (later)
tools/                                        validator, converters, builders
```

### Branches

For each case: `bench/<corpus>/<case_id>/base` and `bench/<corpus>/<case_id>/head`.

- `base` is an **orphan** commit holding the code before the change (no upstream history).
- `head` is **one** commit on top of `base` holding the change under review.
- Commits use a neutral author (`mr-bench-review <bench@mr-bench-review.invalid>`), a fixed
  date (2026-01-01T00:00:00Z) and the messages `base snapshot` and `change`, so rebuilding a case
  reproduces the same SHAs.
- Trees are upstream snapshots with every text file: callers, definitions, tests, build files
  and the upstream licence file are all present. Only media and other binary files that the
  change does not touch are left out (images, audio, video, fonts, 3D models, PDFs, archives,
  compiled code and model weights; the list is `MEDIA_SUFFIXES` in `tools/gitsnap.py`). A
  reviewer cannot read them, and they made up more than half of the repository. Binary files the
  change adds, modifies or deletes are kept, so the diff is exactly the upstream diff.

A runner fetches one case with, for example:

```bash
git fetch --depth=1 https://github.com/Guillaume-Lombardo/mr-bench-review \
  refs/heads/bench/curated/case-017/base refs/heads/bench/curated/case-017/head
```

### `corpus.json`

```json
{
  "schema_version": 1,
  "name": "curated",
  "title": "Curated MRs selected for bdf-review",
  "origin": "internal selection",
  "source_url": null,
  "licence": "Apache-2.0 annotations; upstream code per case, see cases/*.json",
  "default": true,
  "annotation": "human",
  "location_precision": "lines",
  "severity_available": true,
  "created_at": "2026-09-30"
}
```

Exactly one corpus is `default`. `annotation` is `human | llm | mixed`;
`location_precision` is `lines | file | none`.

### `cases/<case_id>.json`

```json
{
  "schema_version": 1,
  "corpus": "curated",
  "id": "case-017",
  "language": "python",
  "size": "small",
  "kind": "real",
  "tier": "pilot",
  "base_branch": "bench/curated/case-017/base",
  "head_branch": "bench/curated/case-017/head",
  "base_sha": "<40 hex>",
  "head_sha": "<40 hex>",
  "mr_title": "Neutral title a developer would write",
  "mr_description": "Neutral description, never revealing expected issues",
  "origin": {"repository": "https://…", "commit": "<sha>", "license": "MIT",
             "source_case": null, "source_url": null},
  "expected_issues": [
    {
      "id": "i1",
      "file": "src/pkg/retry.py",
      "line_start": 42,
      "line_end": 47,
      "category": "correctness",
      "severity": "high",
      "title": "Retry writes twice after timeout",
      "description": "What is wrong, why, and how it manifests.",
      "outside_diff": false,
      "alternative_locations": [{"file": "src/pkg/client.py", "line_start": 10, "line_end": 12}],
      "source_category": null,
      "source_text": null
    }
  ],
  "known_false_positives": [
    {"file": "src/pkg/retry.py", "line_start": 50, "line_end": 52,
     "description": "Plausible but rejected comment, from the source annotations"}
  ],
  "annotator_notes": "free text, never sent to the reviewer"
}
```

- `id` is opaque (`case-017`, or `<source-slug>-NNN` for imports); nothing in ids, paths or
  branch names hints at an issue. `(corpus, id)` is unique.
- `language`: `python | java | typescript | javascript | go | ruby | rust | c | cpp | csharp | php | other`.
- `size`: `small` (< 100 changed lines) | `medium` (100–600) | `large` (> 600), counting added
  plus deleted text lines of the whole change (tests and documentation included).
- `kind`: `planted | reverted_fix | real | clean`; a `clean` case has `expected_issues: []` and
  only clean cases may have none.
- `tier`: `pilot | core | extended` for `curated` (required there); `null` allowed elsewhere.
- `category`: `security | correctness | maintainability | tests`; `source_category` keeps the
  original label of an imported annotation, `source_text` its original text verbatim.
- `severity`: `critical | high | medium | low | info`, or `null` when the source has none.
- `file`, `line_start`, `line_end`: new-side lines at `head_sha`. A changed line is an added
  line, or a head line next to a pure deletion (so an issue caused by deleted code can sit on
  the nearest surviving line). An issue with `file` and null lines is file-level; all three
  null means unlocated (matched on content only). Curated issues are always located.
- `outside_diff: true` marks an issue that cannot be placed on a changed line.
- `alternative_locations`: other places where the same issue may legitimately be reported
  (`file` with optional lines).
- `known_false_positives`: optional; comments the source explicitly rejected.
- `origin` is `null` for synthetic cases; `origin.source_case`/`source_url` identify the case in
  the source benchmark for imports.

## Tools

```bash
uv sync
uv run tools/validate.py                         # files + branches (refs/heads/bench/*)
uv run tools/validate.py --ref-prefix refs/remotes/origin/ --corpus curated
uv run tools/validate.py --skip-git              # files only
uv run tools/stats.py                            # distribution tables for this README
uv run tools/build_curated.py --work work/bench.git
uv run tools/import_review_bench.py --work work/bench.git
uv run tools/import_aacr.py --work work/bench.git
uv run tools/import_martian_offline.py --work work/bench.git
uv run pytest && uv run ruff check .
```

The validator fails, with one message per case, when a file does not match the contract, an id
is duplicated or more than one corpus is default; when a branch is missing or does not resolve to
the pinned SHA, `head` is not a single commit on an orphan `base`, the diff is empty, a
snapshot has no licence file or still holds a media file the change does not touch; when a located issue's file is missing at `head_sha`, its lines
are out of range, or it is not on a changed line while `outside_diff` is false; when a curated
issue is unlocated or a curated case has no tier; when the curated MR text, file names or added
lines match `tools/leak_denylist.txt`; and when `size` does not match the changed lines. It also
prints each corpus's distribution. CI runs it on every push after a blob-less fetch of the
benchmark branches.

Builders and converters write branches into a local bare repository (`--work`). Push them with
`git push <remote> 'refs/heads/bench/<corpus>/*:refs/heads/bench/<corpus>/*'` in batches.

## Versioning

`dataset.json` carries the dataset version. Once `v1.0.0` is tagged, case SHAs never change.
An annotation fix bumps the minor version; an added, removed or rebuilt case or corpus bumps the
major version. `CHANGELOG.md` records every change per corpus. `v1.0.0` is tagged once every
case passes validation and each curated case has been annotated by one person and checked by a
second.

## Credits and licences

- `curated`: annotations by the bdf-review project, Apache-2.0; code from the upstream projects named in
  each case, under their licences (MIT, Apache-2.0, BSD-3-Clause, EPL-2.0).
- `review-bench`: © review-bench contributors (hyperneolabs), CC BY 4.0.
- `aacr`: AACR-Bench © Alibaba, Apache-2.0.
- `martian-offline`: golden comments © 2025 Martian, MIT.

Upstream code keeps its own licence; the licence files are part of every snapshot. Cases whose
code cannot be publicly redistributed are excluded and listed in the corpus's `EXCLUDED.md`.
The repository's own content (tools, documentation and curated annotations) is licensed under
the Apache License 2.0; see `LICENSE`. It does not apply to the upstream code in the `bench/*`
branches, nor to the annotations of the imported corpora, which keep their source licences.
