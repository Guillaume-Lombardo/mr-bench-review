"""Convert alibaba/aacr-bench (pinned) into the ``aacr`` corpus.

    uv run tools/import_aacr.py --work work/bench.git [--source work/sources/aacr-bench]
        [--history work/history] [--only https://github.com/org/repo/pull/1 ...]

Base and head. ``target_commit`` is the PR head and ``source_commit`` a commit of the branch
the PR targets (checked on the source data: ``target_commit`` lies on ``refs/pull/N/head`` and
the merge-base diff matches ``change_line_count``). The base is the merge-base of the two,
computed from a treeless clone of the upstream history. PRs whose head is no longer reachable
upstream (force-pushed forks) cannot be rebuilt and are excluded.

Mapping. Positive comments become expected issues (Code Defect → correctness, Security
Vulnerability → security, Maintainability and Readability and Performance → maintainability;
the original label is kept in ``source_category``, the text in ``source_text``). Left-side
comments and comments whose lines do not exist at the head become file-level issues. Negative
comments become ``known_false_positives``. PRs with only negative comments are ``clean``.
The source has no severity (``null``). Cases whose upstream licence does not allow public
redistribution are skipped and listed in EXCLUDED.md.
"""

from __future__ import annotations

import argparse
import ast
import contextlib
import json
import os
import re
import shutil
import subprocess
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
    write_case,
)
from gitsnap import GitError, fetch_snapshots, file_line_count, git, init_bare

SOURCE_URL = "https://github.com/alibaba/aacr-bench"
SOURCE_COMMIT = "68a569759289a83654a59d06db2a72910edf0a4a"
CORPUS = "aacr"
CATEGORY = {
    "Code Defect": "correctness",
    "Security Vulnerability": "security",
    "Maintainability and Readability": "maintainability",
    "Performance": "maintainability",
}
# Licence per upstream project, checked against the head snapshot's licence file (marker).
LICENCES: dict[str, tuple[str | None, str]] = {
    "CherryHQ/cherry-studio": (
        None,
        "User-segmented dual licence: AGPL-3.0 only for individuals and organisations of up "
        "to 10 people, commercial licence otherwise",
    ),
    "n8n-io/n8n": (
        None,
        "Sustainable Use License and n8n Enterprise License (source-available, not an "
        "open-source licence)",
    ),
    "timescale/timescaledb": (
        None,
        "Portions under the Timescale License (source-available, not an open-source licence)",
    ),
    "elastic/elasticsearch": (
        "AGPL-3.0-only OR SSPL-1.0 OR Elastic-2.0",
        "GNU Affero General Public License",
    ),
    "FreeCAD/FreeCAD": ("LGPL-2.0-or-later", "GNU LIBRARY GENERAL PUBLIC LICENSE"),
    "bluewave-labs/Checkmate": ("AGPL-3.0", "GNU AFFERO GENERAL PUBLIC LICENSE"),
    "immich-app/immich": ("AGPL-3.0", "GNU AFFERO GENERAL PUBLIC LICENSE"),
    "nextcloud/server": ("AGPL-3.0", "GNU AFFERO GENERAL PUBLIC LICENSE"),
    "comfyanonymous/ComfyUI": ("GPL-3.0", "GNU GENERAL PUBLIC LICENSE"),
    "mpv-player/mpv": ("GPL-2.0-or-later OR LGPL-2.1-or-later", "GNU GENERAL PUBLIC LICENSE"),
    "appwrite/appwrite": ("BSD-3-Clause", "Redistribution and use in source and binary forms"),
    "valkey-io/valkey": ("BSD-3-Clause", "BSD 3-Clause"),
    "libsdl-org/SDL": ("Zlib", "provided 'as-is'"),
    "astral-sh/uv": ("Apache-2.0 OR MIT", "Apache License"),
    "unionlabs/union": ("Apache-2.0 OR MIT", "Apache License"),
}
APACHE = "Apache License"
MIT = "Permission is hereby granted, free of charge"
for _repo in (
    "ClickHouse/ClickHouse",
    "alibaba/spring-ai-alibaba",
    "cline/cline",
    "dbeaver/dbeaver",
    "gofr-dev/gofr",
    "google-gemini/gemini-cli",
    "infiniflow/ragflow",
    "juspay/hyperswitch",
    "kestra-io/kestra",
    "keycloak/keycloak",
    "linera-io/linera-protocol",
    "microsoft/typescript-go",
    "openai/codex",
    "opencv/opencv",
    "vllm-project/vllm",
    "wavetermdev/waveterm",
):
    LICENCES[_repo] = ("Apache-2.0", APACHE)
for _repo in (
    "PowerShell/PowerShell",
    "bitcoin/bitcoin",
    "browser-use/browser-use",
    "dotnet/aspnetcore",
    "electron/electron",
    "facebook/react",
    "filamentphp/filament",
    "langflow-ai/langflow",
    "laravel/framework",
    "lvgl/lvgl",
    "microsoft/PowerToys",
    "microsoft/semantic-kernel",
    "mrdoob/three.js",
    "mudler/LocalAI",
    "nodejs/node",
    "ollama/ollama",
    "ppy/osu",
    "sveltejs/svelte",
    "symfony/symfony",
):
    LICENCES[_repo] = ("MIT", MIT)
LICENSE_NAME = re.compile(r"^(licen[cs]e|copying)([.-].*)?$", re.IGNORECASE)


def comments_of(entry: dict[str, object]) -> list[dict[str, object]]:
    raw = entry["comments"]
    return ast.literal_eval(raw) if isinstance(raw, str) else list(raw)  # never eval()


def history(cache: Path, repo: str) -> Path:
    """Treeless bare clone of the upstream history, with a commit-graph."""
    path = cache / f"{repo.replace('/', '_')}.git"
    if not path.exists():
        cache.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            [
                "git",
                "clone",
                "--quiet",
                "--bare",
                "--filter=tree:0",
                "--no-tags",
                f"https://github.com/{repo}.git",
                str(path),
            ],
            check=True,
        )
        git(path, "commit-graph", "write", "--reachable")
    return path


def has_commit(repo: Path, sha: str) -> bool:
    # No lazy fetch: the treeless clone would otherwise try to download a missing commit.
    return (
        subprocess.run(
            ["git", "-C", str(repo), "cat-file", "-e", f"{sha}^{{commit}}"],
            capture_output=True,
            check=False,
            env={**os.environ, "GIT_NO_LAZY_FETCH": "1"},
        ).returncode
        == 0
    )


def resolve_base(hist: Path, pr: int, head: str, branch_tip: str) -> str:
    """Merge-base of the PR head with the target-branch commit; fetch missing commits first."""
    if not has_commit(hist, head):
        for ref in (head, f"+refs/pull/{pr}/head:refs/pr/{pr}"):
            with contextlib.suppress(GitError):
                git(hist, "fetch", "--quiet", "--filter=tree:0", "origin", ref)
    for sha, name in ((head, "PR head (target_commit)"), (branch_tip, "source_commit")):
        if not has_commit(hist, sha):
            if name.startswith("source"):
                git(hist, "fetch", "--quiet", "--filter=tree:0", "origin", sha)
            if not has_commit(hist, sha):
                raise GitError(f"{name} {sha} is no longer reachable upstream")
    return git(hist, "merge-base", branch_tip, head)


def licence_file_text(work: Path, commit: str) -> str:
    names = [
        n for n in git(work, "ls-tree", "--name-only", commit).splitlines() if LICENSE_NAME.match(n)
    ]
    return "\n".join(git(work, "show", f"{commit}:{name}")[:5000] for name in names)


def locate(
    work: Path, head: str, facts: dict[str, object], comment: dict[str, object]
) -> tuple[dict[str, object], bool, str | None]:
    """Contract location for a comment, whether it is outside the diff, and a note if remapped."""
    path = comment["path"]
    if comment.get("side") == "left":
        return {"file": path, "line_start": None, "line_end": None}, True, "left-side comment"
    start, end = sorted((int(comment["from_line"]), int(comment["to_line"])))
    length = file_line_count(work, head, path)
    if length is None:
        return {"file": None, "line_start": None, "line_end": None}, True, "file absent at head"
    if start < 1 or end > length:
        return (
            {"file": path, "line_start": None, "line_end": None},
            True,
            "lines out of range at head",
        )
    outside = not on_changed_lines(facts["new_lines"], path, start, end)
    return {"file": path, "line_start": start, "line_end": end}, outside, None


def mr_text(hist: Path, base: str, head: str) -> tuple[str, str]:
    subjects = git(hist, "log", "--reverse", "--format=%s", f"{base}..{head}").splitlines()
    first = subjects[0] if subjects else git(hist, "log", "-1", "--format=%s", head)
    title, _ = neutral_title(first)
    if len(subjects) > 1:
        body = "\n".join(f"- {neutral_title(subject)[0]}" for subject in subjects)
        return title, neutral_description(body)
    return title, neutral_description(git(hist, "log", "-1", "--format=%b", head))


def convert(
    work: Path, cache: Path, number: int, url: str, positive: dict | None, negative: dict | None
) -> tuple[str | None, str | None]:
    """Build one case; return (case id, None) or (None, exclusion reason)."""
    entry = positive or negative
    repo = url.split("github.com/")[1].split("/pull/")[0]
    pr = int(url.rsplit("/", 1)[1])
    spdx, marker = LICENCES.get(repo, (None, "unknown licence"))
    if spdx is None:
        return None, marker
    upstream = f"https://github.com/{repo}"
    hist = history(cache, repo)
    head_up = entry["target_commit"]
    base_up = resolve_base(hist, pr, head_up, entry["source_commit"])
    if base_up == head_up:
        return None, "PR head is contained in the target-branch commit; empty diff"
    fetch_snapshots(work, upstream, base_up, head_up)
    if marker not in licence_file_text(work, head_up):
        return None, f"licence file at head does not match the expected {spdx}"
    case_id = f"{CORPUS}-{number:03d}"
    facts = build_case_branches(work, CORPUS, case_id, base_up, head_up)
    issues, notes = [], []
    for comment in comments_of(positive) if positive else []:
        location, outside, remap = locate(work, head_up, facts, comment)
        issue_id = f"i{len(issues) + 1}"
        issues.append(
            {
                "id": issue_id,
                **location,
                "category": CATEGORY[comment["category"]],
                "severity": None,
                "title": short_title(comment["note"]),
                "description": comment["note"].strip(),
                "outside_diff": outside,
                "alternative_locations": [],
                "source_category": comment["category"],
                "source_text": comment["note"],
            }
        )
        origin = "AI" if comment.get("is_ai_comment") else "human"
        model = f" ({comment['source_model']})" if comment.get("source_model") else ""
        detail = f"{issue_id}: {origin} comment{model}, {comment.get('context', 'n/a')}"
        if remap:
            lines = f"{comment['from_line']}-{comment['to_line']}"
            detail += f", {remap} (source lines {lines}, side {comment.get('side')})"
        notes.append(detail)
    false_positives = []
    for comment in comments_of(negative) if negative else []:
        location, _, _ = locate(work, head_up, facts, comment)
        if location["file"] is None:
            location = {"file": comment["path"], "line_start": None, "line_end": None}
        false_positives.append({**location, "description": comment["note"].strip()})
    declared = int(entry["change_line_count"])
    case = {
        "schema_version": 1,
        "corpus": CORPUS,
        "id": case_id,
        "language": language_from_name(entry["project_main_language"]),
        "size": facts["size"],
        "kind": "real" if issues else "clean",
        "tier": None,
        "base_branch": facts["base_branch"],
        "head_branch": facts["head_branch"],
        "base_sha": facts["base_sha"],
        "head_sha": facts["head_sha"],
        "mr_title": mr_text(hist, base_up, head_up)[0],
        "mr_description": mr_text(hist, base_up, head_up)[1],
        "origin": {
            "repository": upstream,
            "commit": head_up,
            "license": spdx,
            "source_case": url,
            "source_url": f"{SOURCE_URL}/blob/{SOURCE_COMMIT}/dataset",
        },
        "expected_issues": issues,
        "known_false_positives": false_positives,
        "annotator_notes": (
            f"Imported from AACR-Bench ({url}). Upstream base {base_up} = merge-base of "
            "source_commit "
            f"(target branch) and target_commit (PR head); declared "
            f"change_line_count {declared}. Severity absent in the source. " + "; ".join(notes)
        ).strip(),
    }
    write_case(ROOT / "corpora" / CORPUS, case)
    return case_id, None


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--work", type=Path, required=True, help="local bare build repository")
    parser.add_argument("--source", type=Path, default=ROOT / "work" / "sources" / "aacr-bench")
    parser.add_argument("--history", type=Path, default=ROOT / "work" / "history")
    parser.add_argument("--only", nargs="*", help="PR URLs to convert")
    args = parser.parse_args(argv)

    source = pinned_checkout(f"{SOURCE_URL}.git", SOURCE_COMMIT, args.source)
    positives = {
        e["githubPrUrl"]: e
        for e in json.loads((source / "dataset/positive_samples.json").read_text())
    }
    negatives = {
        e["githubPrUrl"]: e
        for e in json.loads((source / "dataset/negative_samples.json").read_text())
    }
    urls = list(positives) + [url for url in negatives if url not in positives]
    init_bare(args.work)
    corpus_dir = ROOT / "corpora" / CORPUS
    if not args.only:
        shutil.rmtree(corpus_dir / "cases", ignore_errors=True)
    excluded = []
    for number, url in enumerate(urls, 1):
        if args.only and url not in args.only:
            continue
        try:
            case_id, reason = convert(
                args.work, args.history, number, url, positives.get(url), negatives.get(url)
            )
        except GitError as error:
            case_id, reason = None, f"could not rebuild from upstream: {error}"
        print(f"{number:03d} {url}: {case_id or 'EXCLUDED - ' + reason}", flush=True)
        if reason:
            excluded.append((f"{CORPUS}-{number:03d}", url, reason))
    lines = [
        "# AACR — excluded cases",
        "",
        "Numbers are reserved: an excluded PR keeps its position so that case ids stay stable.",
        "",
        "| Id | Source PR | Reason |",
        "| --- | --- | --- |",
    ]
    lines += [f"| {case_id} | {url} | {reason} |" for case_id, url, reason in excluded]
    if not args.only:
        (corpus_dir / "EXCLUDED.md").write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
