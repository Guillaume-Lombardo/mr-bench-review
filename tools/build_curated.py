"""Rebuild the curated corpus branches from the case files alone.

Each curated case pins its upstream change in ``origin`` (repository and commit). The base
snapshot is the commit's first parent. The script fetches both snapshots without history,
recreates ``base``/``head`` with the neutral author, messages and date, and checks that the
resulting commits match the pinned ``base_sha``/``head_sha``.

    uv run tools/build_curated.py --work work/bench.git [--only case-001 case-002]
    git -C work/bench.git push <remote> 'refs/heads/bench/curated/*:refs/heads/bench/curated/*'
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from contract import Case
from gitsnap import build_branches, fetch_snapshots, git, has_tree, init_bare

ROOT = Path(__file__).resolve().parents[1]


def upstream_base(work: Path, url: str, commit: str) -> str:
    """First parent of the upstream commit, fetched with a depth of two."""
    if not has_tree(work, commit) or not has_tree(work, f"{commit}^1"):
        git(work, "fetch", "--quiet", "--depth=2", "--no-tags", url, commit)
    return git(work, "rev-parse", f"{commit}^1")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--work", type=Path, required=True, help="local bare build repository")
    parser.add_argument("--only", nargs="*", help="case ids to rebuild")
    args = parser.parse_args(argv)

    init_bare(args.work)
    failures = 0
    paths = sorted((ROOT / "corpora" / "curated" / "cases").glob("*.json"))
    for path in paths:
        case = Case.model_validate_json(path.read_text())
        if args.only and case.id not in args.only:
            continue
        if case.origin is None:
            print(f"{case.id}: synthetic case, nothing to fetch", file=sys.stderr)
            continue
        url = case.origin.repository
        base_up = upstream_base(args.work, url, case.origin.commit)
        fetch_snapshots(args.work, url, base_up, case.origin.commit)
        base, head = build_branches(
            args.work, case.base_branch, case.head_branch, base_up, case.origin.commit
        )
        ok = (base, head) == (case.base_sha, case.head_sha)
        failures += not ok
        print(f"{case.id}: {'ok' if ok else 'SHA MISMATCH'} base {base[:10]} head {head[:10]}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
