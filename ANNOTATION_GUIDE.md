# Annotation guide

Licensed under [CC BY 4.0](LICENSE-CC-BY-4.0); see [LICENSING.md](LICENSING.md).

How to write and check `expected_issues` for a case. The reviewer under test never sees case
files; it sees the `head` branch, the diff against `base`, and `mr_title`/`mr_description`.

## What counts as an expected issue

List every point a senior reviewer would raise on this MR and expect the author to act on:

- a defect: wrong result, crash, data loss, resource leak, race, broken compatibility;
- a security problem: missing or wrong authorisation, injection, unsafe defaults, secrets;
- a maintainability problem with a concrete cost: duplicated logic, misleading API, breaking a
  public extension point, deprecated API, dead or unreachable code;
- a tests problem: a behaviour change without a test, or a test that cannot fail for the bug
  it is meant to cover.

Do **not** list pure style preferences (naming taste, formatting, import order) or remarks the
project's conventions contradict.

Good:

> **Body read is capped at the buffer size instead of the requested maximum** —
> `readToByteBuffer(max)` starts with `remaining = bufferSize` and stops after one buffer, so
> documents larger than the buffer are truncated without error. The cap must use `max`.

Bad (vague, no consequence, not actionable):

> Possible issue with the buffer handling here; consider reviewing.

Bad (style only):

> Rename `remaining` to `bytesLeft` for clarity.

## Fields

- `title`: one line naming the problem, not the fix. No more than about 80 characters.
- `description`: what is wrong, why, and how it shows (input, symptom). Mention what a
  correct fix must preserve when it is not obvious.
- `category`: `security | correctness | maintainability | tests`. A security consequence wins
  over correctness; a missing test for a real defect is a separate `tests` issue.
- `severity`: `critical` (data loss, memory corruption, security breach), `high` (crash or wrong
  result in a common path), `medium` (wrong result in a less common path, degraded feature),
  `low` (minor impact, maintainability), `info` (worth mentioning only).
- `file`, `line_start`, `line_end`: new-side lines at `head_sha` where a reviewer would put the
  comment. Keep ranges tight (the statement or the few lines that are wrong). For an issue
  caused by deleted code, use the nearest surviving line. Use `alternative_locations` when the
  same issue is visible in several places (the same mistake repeated, or the call site and the
  definition).
- `outside_diff`: `true` only when the issue cannot be placed on a changed line (for example a
  caller that must change but did not). Curated issues must be located.

## MR text and leaks

`mr_title` and `mr_description` must read like what the developer wrote. Never mention the
expected issues, never add hints, and remove issue numbers and links that identify the upstream
fix. The validator rejects diffs, file names and MR text matching `tools/leak_denylist.txt`
(`# BUG`, `TODO: fix`, `FIXME`, `unsafe_…`, …). Tests that would expose a planted issue are
removed from `head` or kept only as a developer would realistically have written them.

## Clean cases

A `clean` case has `expected_issues: []`. Use it only after reviewing the diff with the same
standard: if you would raise anything, the case is not clean. Record judgement calls (a
plausible remark you decided is not an issue) in `annotator_notes` so judges can use them.

## Reproduction

- `planted`: `annotator_notes` must contain a reproduction (failing test or command).
- `real` and `reverted_fix`: link the upstream fix when available. Identify its regression
  test if one exists, and say whether it was actually run against the snapshot. An upstream
  fix alone is supporting evidence, not an executed reproduction. For a newly discovered
  defect without a known upstream fix, record the source-level evidence and an executable
  reproducer when feasible. Never invent a test or claim an unexecuted test passed/failed.

## Imported corpora

Keep the source annotation verbatim in `source_text` and its label in `source_category`. Do
not edit imported ground truth in place: corrections go in a separate, documented step with a
minor version bump.

## Second check

Every curated case is annotated by one person and checked by a second before `v1.0.0`. The
checker re-reads the diff, confirms each issue (real, located, correctly categorised), looks
for missing issues, and records the result at the end of `annotator_notes` ("Second check: …").

An AI-assisted check must identify the checker as AI and state its scope and execution limits.
It can complete the annotation audit, but does not count as the independent second person
required for release sign-off. Record any focused reproductions separately from full upstream
test-suite execution.
