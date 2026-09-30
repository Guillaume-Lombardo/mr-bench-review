"""Helpers shared by the corpus converters: pinned sources, neutral MR text, case files."""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

from contract import Case, size_for
from gitsnap import build_branches, changed_new_lines, changed_paths, git, numstat_changed_lines

ROOT = Path(__file__).resolve().parents[1]

LANGUAGE_BY_EXTENSION = {
    ".py": "python",
    ".java": "java",
    ".kt": "other",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".js": "javascript",
    ".jsx": "javascript",
    ".mjs": "javascript",
    ".cjs": "javascript",
    ".go": "go",
    ".rb": "ruby",
    ".rs": "rust",
    ".c": "c",
    ".h": "c",
    ".cc": "cpp",
    ".cpp": "cpp",
    ".cxx": "cpp",
    ".hpp": "cpp",
    ".hh": "cpp",
    ".cs": "csharp",
    ".php": "php",
}
LANGUAGE_BY_NAME = {
    "python": "python",
    "java": "java",
    "typescript": "typescript",
    "javascript": "javascript",
    "go": "go",
    "ruby": "ruby",
    "rust": "rust",
    "c": "c",
    "c++": "cpp",
    "cpp": "cpp",
    "c#": "csharp",
    "csharp": "csharp",
    "php": "php",
}
_DROP_LINE = re.compile(
    r"^\s*(fixes|fixed|fix|closes|closed|close|refs|see|resolves|relates to)\b.*(#\d+|gh-\d+|https?://)"
    r"|^\s*(pr close|regression in|co-authored-by|signed-off-by|reviewed-by|reviewers:|change-id:"
    r"|pull-request|\(cherry picked|backport of|closes:|fixes:)"
    r"|https?://github\.com/\S+/(issues|pull)/\d+\s*$",
    re.IGNORECASE,
)


def pinned_checkout(url: str, commit: str, destination: Path) -> Path:
    """Clone ``url`` once and check out the pinned ``commit`` (detached)."""
    if not (destination / ".git").exists():
        destination.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["git", "clone", "--quiet", url, str(destination)], check=True)
    subprocess.run(["git", "-C", str(destination), "checkout", "--quiet", commit], check=True)
    head = subprocess.run(
        ["git", "-C", str(destination), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    if head != commit:
        raise SystemExit(f"{url}: checked out {head}, pinned {commit}")
    return destination


def language_from_name(name: str) -> str:
    return LANGUAGE_BY_NAME.get(name.strip().lower(), "other")


def language_from_paths(paths: list[str]) -> str:
    counts: dict[str, int] = {}
    for path in paths:
        language = LANGUAGE_BY_EXTENSION.get(Path(path).suffix.lower())
        if language and language != "other":
            counts[language] = counts.get(language, 0) + 1
    return max(counts, key=lambda key: counts[key]) if counts else "other"


def neutral_title(subject: str, body: str = "") -> tuple[str, str]:
    """Upstream subject without issue numbers or ticket prefixes; merge commits use the body."""
    if subject.startswith("Merge pull request"):
        lines = [line for line in body.splitlines() if line.strip()]
        if lines:
            subject, body = lines[0], "\n".join(lines[1:])
        else:
            subject = re.sub(r"[-_]+", " ", subject.rsplit("/", 1)[-1]).strip().capitalize()
    title = re.sub(r"(\s*\(#\d+\))+\s*$", "", subject)
    title = re.sub(r"^\[[\d.x]+\]\s*", "", title)
    title = re.sub(r"^(Fixed|Refs)\s+#\d+(,\s*(Refs\s+)?#\d+)*\s*--\s*", "", title)
    title = re.sub(r"^\[[A-Z]+-\d+\]\s*", "", title)
    title = re.sub(r"^[A-Z]+-\d+:?\s*", "", title)
    title = re.sub(r"\s*#\d{3,}\b", "", title)
    return title.strip() or "Update", body


def neutral_description(body: str) -> str:
    """Upstream body without trailers, issue references and links to issues."""
    lines = [line for line in body.splitlines() if not _DROP_LINE.search(line)]
    text = re.sub(r"\s*\(#\d+\)", "", "\n".join(lines))
    text = re.sub(r"\s?#\d{3,}\b", "", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def short_title(text: str, limit: int = 90) -> str:
    """First sentence of an annotation, shortened to a title."""
    first = re.split(r"(?<=[.!?])\s|\n", text.strip(), maxsplit=1)[0].strip().rstrip(".")
    first = re.sub(r"\s+", " ", first)
    return first if len(first) <= limit else first[: limit - 1].rstrip() + "…"


def on_changed_lines(new_lines: dict[str, set[int]], path: str, start: int, end: int) -> bool:
    return any(n in new_lines.get(path, ()) for n in range(start, end + 1))


def build_case_branches(
    work: Path, corpus: str, case_id: str, base_up: str, head_up: str
) -> dict[str, object]:
    """Create the branches and return the Git facts a case file needs."""
    base_ref = f"bench/{corpus}/{case_id}/base"
    head_ref = f"bench/{corpus}/{case_id}/head"
    base, head = build_branches(work, base_ref, head_ref, base_up, head_up)
    return {
        "base_branch": base_ref,
        "head_branch": head_ref,
        "base_sha": base,
        "head_sha": head,
        "size": size_for(numstat_changed_lines(work, base, head)).value,
        "paths": changed_paths(work, base, head),
        "new_lines": changed_new_lines(work, base, head),
    }


def upstream_message(work: Path, commit: str) -> tuple[str, str]:
    return git(work, "log", "-1", "--format=%s", commit), git(
        work, "log", "-1", "--format=%b", commit
    )


def write_case(corpus_dir: Path, case: dict[str, object]) -> None:
    """Validate against contract v1 and write ``cases/<id>.json``."""
    Case.model_validate(case)
    cases = corpus_dir / "cases"
    cases.mkdir(parents=True, exist_ok=True)
    (cases / f"{case['id']}.json").write_text(json.dumps(case, indent=2, ensure_ascii=False) + "\n")


def treeless_history(cache: Path, repo: str) -> Path:
    """Bare clone of an upstream history without trees or blobs, with a commit-graph."""
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


def is_ancestor(repo: Path, ancestor: str, commit: str) -> bool:
    return (
        subprocess.run(
            ["git", "-C", str(repo), "merge-base", "--is-ancestor", ancestor, commit],
            capture_output=True,
            check=False,
        ).returncode
        == 0
    )


def base_before_merge(hist: Path, head: str, tip: str) -> str:
    """PR base: merge-base of ``head`` with the newest first-parent commit of ``tip`` without it.

    The first-parent commits of ``tip`` that contain ``head`` (a merged PR) form a prefix from
    ``tip`` back to the merge commit; a binary search finds its end. For an unmerged PR this is
    simply the merge-base with ``tip``.
    """
    chain = git(hist, "rev-list", "--first-parent", tip, "--not", head).split()
    low, high = 0, len(chain)
    while low < high:
        middle = (low + high) // 2
        if is_ancestor(hist, head, chain[middle]):
            low = middle + 1
        else:
            high = middle
    stop = chain[low] if low < len(chain) else f"{chain[-1]}^1" if chain else tip
    return git(hist, "merge-base", stop, head)


def secret_reason(paths: list[str]) -> str:
    """Exclusion reason for a snapshot that GitHub push protection rejects."""
    return (
        "GitHub push protection flags strings in the upstream snapshot as secrets ("
        + ", ".join(f"`{path}`" for path in paths)
        + "); the public repository must not contain secrets. Re-include only after the owner "
        "confirms they are public test values and allows them."
    )
