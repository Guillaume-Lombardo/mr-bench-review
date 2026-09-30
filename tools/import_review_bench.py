"""Convert hyperneolabs/review-bench (pinned) into the ``review-bench`` corpus.

    uv run tools/import_review_bench.py --work work/bench.git [--source work/sources/review-bench]

Every source case is imported. Bugs become ``real`` cases with one expected issue whose first
ground-truth range is the location and the others ``alternative_locations``; controls become
``clean`` cases. The source has no category or severity: category is set to ``correctness``
(to be reviewed) and severity to ``null``.
"""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

from convert_common import (
    ROOT,
    build_case_branches,
    language_from_name,
    neutral_description,
    neutral_title,
    on_changed_lines,
    pinned_checkout,
    short_title,
    upstream_message,
    write_case,
)
from gitsnap import fetch_snapshots, init_bare

SOURCE_URL = "https://github.com/hyperneolabs/review-bench"
SOURCE_COMMIT = "93f31c224448e453c00768780795bd6bf6ab4234"
CORPUS = "review-bench"


def convert_case(work: Path, corpus_dir: Path, number: int, source: dict[str, object]) -> str:
    info = source["source"]
    upstream = f"https://github.com/{info['repo']}"
    base_up, head_up = info["review_base_sha"], info["review_head_sha"]
    fetch_snapshots(work, upstream, base_up, head_up)
    case_id = f"{CORPUS}-{number:03d}"
    facts = build_case_branches(work, CORPUS, case_id, base_up, head_up)
    title, body = neutral_title(*upstream_message(work, head_up))
    issues = []
    notes = [
        f"Imported from review-bench {source['case_id']} (corpus {source['corpus_version']}).",
        f"Introducing PR {upstream}/pull/{info['introducing_pr']}.",
    ]
    if source["kind"] == "bug":
        defect = source["defect"]
        ranges = [
            {"file": r["file"], "line_start": r["line_start"], "line_end": r["line_end"]}
            for r in defect["ground_truth"]
        ]
        first = ranges[0]
        outside = not any(
            on_changed_lines(facts["new_lines"], r["file"], r["line_start"], r["line_end"])
            for r in ranges
        )
        issues.append(
            {
                "id": "i1",
                **first,
                "category": "correctness",
                "severity": None,
                "title": short_title(defect["description"]),
                "description": f"{defect['description']}\n\nProvenance: {defect['provenance']}.",
                "outside_diff": outside,
                "alternative_locations": ranges[1:],
                "source_category": None,
                "source_text": defect["description"],
            }
        )
        notes.append(
            f"Fix {upstream}/commit/{info['fix_sha']} (PR #{info['fix_pr']}). "
            "Category defaulted to "
            "correctness and severity left null because the source has neither; to be reviewed."
        )
        notes += [f"Ground truth note: {r['note']}" for r in defect["ground_truth"]]
    case = {
        "schema_version": 1,
        "corpus": CORPUS,
        "id": case_id,
        "language": language_from_name(source["language"][0]),
        "size": facts["size"],
        "kind": "real" if source["kind"] == "bug" else "clean",
        "tier": None,
        "base_branch": facts["base_branch"],
        "head_branch": facts["head_branch"],
        "base_sha": facts["base_sha"],
        "head_sha": facts["head_sha"],
        "mr_title": title,
        "mr_description": neutral_description(body),
        "origin": {
            "repository": upstream,
            "commit": head_up,
            "license": info["license"],
            "source_case": source["case_id"],
            "source_url": f"{SOURCE_URL}/tree/{SOURCE_COMMIT}/cases/{source['case_id']}",
        },
        "expected_issues": issues,
        "known_false_positives": [],
        "annotator_notes": " ".join(notes),
    }
    write_case(corpus_dir, case)
    return case_id


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--work", type=Path, required=True, help="local bare build repository")
    parser.add_argument("--source", type=Path, default=ROOT / "work" / "sources" / "review-bench")
    args = parser.parse_args(argv)

    source = pinned_checkout(f"{SOURCE_URL}.git", SOURCE_COMMIT, args.source)
    init_bare(args.work)
    corpus_dir = ROOT / "corpora" / CORPUS
    shutil.rmtree(corpus_dir / "cases", ignore_errors=True)
    paths = sorted((source / "cases").glob("*/case.json"))
    for number, path in enumerate(paths, 1):
        data = json.loads(path.read_text())
        case_id = convert_case(args.work, corpus_dir, number, data)
        print(f"{case_id} <- {data['case_id']} ({data['kind']})", flush=True)


if __name__ == "__main__":
    main()
