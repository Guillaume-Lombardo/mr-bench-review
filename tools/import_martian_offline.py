"""Convert withmartian/code-review-benchmark offline golden comments into ``martian-offline``.

    uv run tools/import_martian_offline.py --work work/bench.git [--source DIR] [--history DIR]

Golden comments have no file or line: they become unlocated issues (``file`` and lines null),
matched on content only. Heads are the PR refs (``refs/pull/N/head``) of the listed repository
(upstream or evaluation fork); the resolved head SHAs are pinned in
``tools/sources/martian-offline.lock.json`` on the first run so that later runs rebuild the
same cases even if a PR is updated. The base is the merge-base with the default branch, taken
before the merge commit for merged PRs.
"""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

from convert_common import (
    ROOT,
    base_before_merge,
    build_case_branches,
    language_from_paths,
    neutral_description,
    neutral_title,
    pinned_checkout,
    secret_reason,
    short_title,
    treeless_history,
    write_case,
)
from gitsnap import GitError, fetch_snapshots, git, init_bare

SOURCE_URL = "https://github.com/withmartian/code-review-benchmark"
SOURCE_COMMIT = "e616e849755441da38f18bf3adba2c9583b03803"
CORPUS = "martian-offline"
LOCK = ROOT / "tools" / "sources" / "martian-offline.lock.json"
PUSH_PROTECTION = json.loads(
    (ROOT / "tools" / "sources" / "martian-offline.push-protection.json").read_text()
)
FILES = ("cal_dot_com", "discourse", "grafana", "keycloak", "sentry")
CATEGORY = {
    "bug": "correctness",
    "data": "correctness",
    "concurrency": "correctness",
    "api": "correctness",
    "security": "security",
    "test_gap": "tests",
    "perf": "maintainability",
    "doc_defect": "maintainability",
    "style": "maintainability",
    "speculative": "maintainability",
}
PROFILE = {
    **dict.fromkeys(("bug", "security", "concurrency", "data", "api"), "Strict"),
    **dict.fromkeys(("perf", "test_gap", "doc_defect"), "Core"),
    **dict.fromkeys(("style", "speculative"), "All"),
}
# Licence of the reviewed code per golden file; None excludes the file's cases.
LICENCES = {
    "keycloak": ("Apache-2.0", None),
    "grafana": ("AGPL-3.0", None),
    "discourse": ("GPL-2.0-or-later", None),
    "sentry": (
        None,
        "Sentry is distributed under the Functional Source License (FSL-1.1, "
        "source-available, formerly BSL), not an open-source licence",
    ),
    "cal_dot_com": (
        None,
        "Cal.com includes code under the Cal.com Commercial License "
        "(enterprise directories), which does not allow public redistribution",
    ),
}


def resolve(hist: Path, pr: int) -> tuple[str, str]:
    """(base, head) of a PR: base from the test-merge ref when GitHub still has it."""
    git(hist, "fetch", "--quiet", "--filter=tree:0", "origin", f"+refs/pull/{pr}/head:refs/pr/{pr}")
    head = git(hist, "rev-parse", f"refs/pr/{pr}")
    try:
        git(
            hist,
            "fetch",
            "--quiet",
            "--filter=tree:0",
            "origin",
            f"+refs/pull/{pr}/merge:refs/pr/{pr}-merge",
        )
        return git(hist, "merge-base", f"refs/pr/{pr}-merge^1", head), head
    except GitError:
        pass
    base = base_before_merge(hist, head, "HEAD")
    if base != head:
        return base, head
    # Evaluation forks target per-PR base branches: take the closest branch not containing head.
    best = None
    for tip in git(hist, "for-each-ref", "--format=%(objectname)", "refs/heads").split():
        candidate = git(hist, "merge-base", tip, head)
        if candidate == head:
            continue
        distance = int(git(hist, "rev-list", "--count", f"{candidate}..{head}"))
        if best is None or distance < best[0]:
            best = (distance, candidate)
    if best is None:
        raise GitError("no base branch found")
    return best[1], head


def mr_description(hist: Path, base: str, head: str) -> str:
    subjects = git(hist, "log", "--reverse", "--format=%s", f"{base}..{head}").splitlines()
    if len(subjects) > 1:
        return neutral_description("\n".join(f"- {neutral_title(s)[0]}" for s in subjects))
    return neutral_description(git(hist, "log", "-1", "--format=%b", head))


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--work", type=Path, required=True, help="local bare build repository")
    parser.add_argument("--source", type=Path, default=ROOT / "work" / "sources" / "martian")
    parser.add_argument("--history", type=Path, default=ROOT / "work" / "history")
    args = parser.parse_args(argv)

    source = pinned_checkout(f"{SOURCE_URL}.git", SOURCE_COMMIT, args.source)
    lock = json.loads(LOCK.read_text()) if LOCK.exists() else {}
    init_bare(args.work)
    corpus_dir = ROOT / "corpora" / CORPUS
    shutil.rmtree(corpus_dir / "cases", ignore_errors=True)
    excluded = []
    number = 0
    for name in FILES:
        prs = json.loads((source / "offline" / "golden_comments" / f"{name}.json").read_text())
        spdx, reason = LICENCES[name]
        for pr in prs:
            number += 1
            case_id = f"{CORPUS}-{number:03d}"
            url = pr["url"]
            if spdx is None or url in PUSH_PROTECTION:
                if spdx is not None:
                    reason = secret_reason(PUSH_PROTECTION[url])
                excluded.append((case_id, url, reason))
                print(f"{case_id} {url}: EXCLUDED", flush=True)
                continue
            repo = url.split("github.com/")[1].split("/pull/")[0]
            hist = treeless_history(args.history, repo)
            try:
                if url in lock:
                    base_up, head_up = lock[url]["base"], lock[url]["head"]
                else:
                    base_up, head_up = resolve(hist, int(url.rsplit("/", 1)[1]))
                    lock[url] = {"base": base_up, "head": head_up}
                upstream = f"https://github.com/{repo}"
                fetch_snapshots(args.work, upstream, base_up, head_up)
                facts = build_case_branches(args.work, CORPUS, case_id, base_up, head_up)
            except GitError as error:
                excluded.append((case_id, url, f"could not rebuild from upstream: {error}"))
                print(f"{case_id} {url}: EXCLUDED ({error})", flush=True)
                continue
            issues, notes = [], []
            for comment in pr["comments"]:
                issue_id = f"i{len(issues) + 1}"
                issues.append(
                    {
                        "id": issue_id,
                        "file": None,
                        "line_start": None,
                        "line_end": None,
                        "category": CATEGORY[comment["category"]],
                        "severity": comment["severity"].lower(),
                        "title": short_title(comment["comment"]),
                        "description": comment["comment"].strip(),
                        "outside_diff": False,
                        "alternative_locations": [],
                        "source_category": comment["category"],
                        "source_text": comment["comment"],
                    }
                )
                notes.append(f"{issue_id}: Martian profile {PROFILE[comment['category']]}")
            case = {
                "schema_version": 1,
                "corpus": CORPUS,
                "id": case_id,
                "language": language_from_paths(facts["paths"]),
                "size": facts["size"],
                "kind": "real",
                "tier": None,
                "base_branch": facts["base_branch"],
                "head_branch": facts["head_branch"],
                "base_sha": facts["base_sha"],
                "head_sha": facts["head_sha"],
                "mr_title": neutral_title(pr["pr_title"])[0],
                "mr_description": mr_description(hist, base_up, head_up),
                "origin": {
                    "repository": upstream,
                    "commit": head_up,
                    "license": spdx,
                    "source_case": url,
                    "source_url": (
                        f"{SOURCE_URL}/blob/{SOURCE_COMMIT}/offline/golden_comments/{name}.json"
                    ),
                },
                "expected_issues": issues,
                "known_false_positives": [],
                "annotator_notes": (
                    "Imported from Martian code-review-benchmark offline golden comments "
                    f"({url}). "
                    f"Upstream base {base_up} (resolved as described in SOURCE.md). "
                    "Golden comments are unlocated. " + "; ".join(notes)
                ),
            }
            write_case(corpus_dir, case)
            print(f"{case_id} {url}: {len(issues)} issues", flush=True)
    LOCK.parent.mkdir(parents=True, exist_ok=True)
    LOCK.write_text(json.dumps(lock, indent=2, sort_keys=True) + "\n")
    lines = [
        "# martian-offline — excluded cases",
        "",
        "Numbers are reserved: an excluded PR keeps its position so that case ids stay stable.",
        "",
        "| Id | Source PR | Reason |",
        "| --- | --- | --- |",
    ]
    lines += [f"| {case_id} | {url} | {reason} |" for case_id, url, reason in excluded]
    (corpus_dir / "EXCLUDED.md").write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
