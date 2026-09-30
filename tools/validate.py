"""Validate every corpus against dataset contract v1 and print its distribution.

    uv run tools/validate.py                      # schema and Git checks on refs/heads/bench/*
    uv run tools/validate.py --ref-prefix refs/remotes/origin/
    uv run tools/validate.py --skip-git           # files only, no branches needed
    uv run tools/validate.py --corpus curated

Exit status 1 when any error is found; every error names its corpus and case.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from contract import Case, Corpus, Dataset, Kind, size_for
from gitsnap import (
    GitError,
    added_text,
    changed_new_lines,
    changed_paths,
    file_line_count,
    git,
    has_license_file,
    numstat_changed_lines,
    untouched_media,
)
from pydantic import ValidationError

ROOT = Path(__file__).resolve().parents[1]
DENYLIST = Path(__file__).with_name("leak_denylist.txt")


@dataclass
class Report:
    errors: list[str] = field(default_factory=list)

    def error(self, where: str, message: str) -> None:
        self.errors.append(f"{where}: {message}")


def load_denylist(path: Path) -> list[re.Pattern[str]]:
    patterns = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip() and not line.lstrip().startswith("#"):
            patterns.append(re.compile(line.strip()))
    return patterns


def load_corpora(root: Path, report: Report, only: set[str] | None) -> dict[str, list[Case]]:
    """Validate dataset.json, corpus.json and case files; return valid cases per corpus."""
    try:
        Dataset.model_validate_json((root / "dataset.json").read_text())
    except (OSError, ValidationError) as error:
        report.error("dataset.json", str(error))
    corpora: dict[str, list[Case]] = {}
    defaults = []
    for corpus_dir in sorted(path for path in (root / "corpora").iterdir() if path.is_dir()):
        where = f"corpora/{corpus_dir.name}"
        try:
            corpus = Corpus.model_validate_json((corpus_dir / "corpus.json").read_text())
        except (OSError, ValidationError) as error:
            report.error(f"{where}/corpus.json", str(error))
            continue
        if corpus.name != corpus_dir.name:
            report.error(f"{where}/corpus.json", f"name {corpus.name!r} != directory name")
        if corpus.default:
            defaults.append(corpus.name)
        for required in ("SOURCE.md", "EXCLUDED.md"):
            if not (corpus_dir / required).is_file():
                report.error(where, f"missing {required}")
        if only and corpus.name not in only:
            continue
        cases = []
        seen: set[str] = set()
        for path in sorted((corpus_dir / "cases").glob("*.json")):
            try:
                case = Case.model_validate_json(path.read_text())
            except ValidationError as error:
                report.error(f"{where}/cases/{path.name}", str(error).replace("\n", " "))
                continue
            if case.corpus != corpus.name:
                report.error(f"{where}/{case.id}", f"corpus field is {case.corpus!r}")
            if path.stem != case.id:
                report.error(f"{where}/cases/{path.name}", f"file name does not match id {case.id}")
            if case.id in seen:
                report.error(f"{where}/{case.id}", "duplicate case id")
            seen.add(case.id)
            if corpus.name == "curated":
                check_curated_rules(case, report)
            cases.append(case)
        corpora[corpus.name] = cases
    if len(defaults) != 1:
        report.error("corpora", f"exactly one corpus must be default, found {defaults or 'none'}")
    return corpora


def check_curated_rules(case: Case, report: Report) -> None:
    where = f"curated/{case.id}"
    if case.tier is None:
        report.error(where, "curated cases need a tier")
    if case.kind is not Kind.PLANTED and case.origin is None:
        report.error(where, "non-synthetic curated cases need an origin")
    for issue in case.expected_issues:
        if not issue.located:
            report.error(where, f"{issue.id} is not located (curated issues need file and lines)")


def check_git(
    case: Case, repo: Path, prefix: str, report: Report, deny: list[re.Pattern[str]] | None
) -> None:
    """Branch, diff and location checks for one case."""
    where = f"{case.corpus}/{case.id}"
    try:
        base = git(repo, "rev-parse", "--verify", "-q", f"{prefix}{case.base_branch}^{{commit}}")
        head = git(repo, "rev-parse", "--verify", "-q", f"{prefix}{case.head_branch}^{{commit}}")
    except GitError:
        report.error(where, f"branch {prefix}{case.base_branch} or head branch is missing")
        return
    if base != case.base_sha:
        report.error(where, f"base branch is {base}, pinned {case.base_sha}")
    if head != case.head_sha:
        report.error(where, f"head branch is {head}, pinned {case.head_sha}")
    if git(repo, "rev-list", "--parents", "-n1", case.base_sha).split()[1:]:
        report.error(where, "base is not an orphan commit")
    if git(repo, "rev-list", "--parents", "-n1", case.head_sha).split()[1:] != [case.base_sha]:
        report.error(where, "head is not a single commit on base")
    for rev, name in ((case.base_sha, "base"), (case.head_sha, "head")):
        if not has_license_file(repo, rev):
            report.error(where, f"no upstream licence file in {name}")
    for rev, extra in untouched_media(repo, case.base_sha, case.head_sha).items():
        if extra:
            name = "base" if rev == case.base_sha else "head"
            report.error(where, f"{len(extra)} untouched media file(s) in {name}, e.g. {extra[0]}")
    changed = numstat_changed_lines(repo, case.base_sha, case.head_sha)
    paths = changed_paths(repo, case.base_sha, case.head_sha)
    if not paths:
        report.error(where, "empty diff")
        return
    if size_for(changed) is not case.size:
        report.error(where, f"size {case.size} but {changed} changed lines")
    new_lines = changed_new_lines(repo, case.base_sha, case.head_sha)
    for issue in case.expected_issues:
        if issue.file is None:
            continue
        length = file_line_count(repo, case.head_sha, issue.file)
        if length is None:
            if (
                issue.line_start is not None
                or file_line_count(repo, case.base_sha, issue.file) is None
            ):
                report.error(where, f"{issue.id}: {issue.file} does not exist at head")
            continue
        if issue.line_start is None or issue.line_end is None:
            continue
        if issue.line_end > length:
            report.error(where, f"{issue.id}: lines {issue.line_end} > {length} in {issue.file}")
        on_change = any(
            n in new_lines.get(issue.file, ()) for n in range(issue.line_start, issue.line_end + 1)
        )
        if not on_change and not issue.outside_diff:
            report.error(
                where,
                f"{issue.id}: {issue.file}:{issue.line_start}-{issue.line_end} is not on a "
                "changed line and outside_diff is false",
            )
    if deny is not None:
        text = "\n".join([case.mr_title, case.mr_description, *paths])
        added = added_text(repo, case.base_sha, case.head_sha)
        for pattern in deny:
            for source, name in ((text, "MR text or file names"), (added, "added lines")):
                hit = pattern.search(source)
                if hit:
                    report.error(where, f"leak pattern {pattern.pattern!r} in {name}: {hit[0]!r}")


def distribution(corpora: dict[str, list[Case]]) -> str:
    lines = []
    for name, cases in corpora.items():
        issues = [issue for case in cases for issue in case.expected_issues]
        lines.append(f"\n== {name}: {len(cases)} cases, {len(issues)} expected issues")
        for label, counter in (
            ("language", Counter(case.language.value for case in cases)),
            ("size", Counter(case.size.value for case in cases)),
            ("kind", Counter(case.kind.value for case in cases)),
            ("tier", Counter(str(case.tier.value if case.tier else None) for case in cases)),
            ("category", Counter(issue.category.value for issue in issues)),
            (
                "severity",
                Counter(str(issue.severity.value if issue.severity else None) for issue in issues),
            ),
        ):
            lines.append(f"  {label:9} " + ", ".join(f"{k} {v}" for k, v in counter.most_common()))
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", type=Path, default=ROOT, help="dataset repository root")
    parser.add_argument("--repo", type=Path, default=None, help="Git repository with the branches")
    parser.add_argument("--ref-prefix", default="refs/heads/", help="prefix of bench branches")
    parser.add_argument("--corpus", action="append", help="validate only these corpora")
    parser.add_argument("--skip-git", action="store_true", help="only validate files")
    parser.add_argument(
        "--denylist", type=Path, default=DENYLIST, help="leak patterns, one regex per line"
    )
    parser.add_argument("--json", action="store_true", help="print errors as a JSON list")
    args = parser.parse_args(argv)

    report = Report()
    corpora = load_corpora(args.root, report, set(args.corpus) if args.corpus else None)
    if not args.skip_git:
        repo = args.repo or args.root
        deny = load_denylist(args.denylist)
        for name, cases in corpora.items():
            for case in cases:
                try:
                    check_git(
                        case, repo, args.ref_prefix, report, deny if name == "curated" else None
                    )
                except GitError as error:
                    report.error(f"{name}/{case.id}", str(error))
    print(distribution(corpora))
    if args.json:
        print(json.dumps(report.errors, indent=2))
    elif report.errors:
        print(f"\n{len(report.errors)} error(s):", file=sys.stderr)
        for message in report.errors:
            print(f"  {message}", file=sys.stderr)
    else:
        print("\nall corpora valid")
    return 1 if report.errors else 0


if __name__ == "__main__":
    sys.exit(main())
