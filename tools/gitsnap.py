"""Build benchmark base/head branches from upstream snapshots, and read them back.

Branches hold no upstream history: ``base`` is an orphan commit with the upstream tree before
the change and ``head`` is one commit on top of it with the tree after the change. Media and
other binary files the change does not touch (``MEDIA_SUFFIXES``) are left out of both trees;
every other file is kept, so the diff is the upstream diff. Commits use a neutral author,
neutral messages and a fixed date, so rebuilding a case gives the same SHAs.
"""

from __future__ import annotations

import os
import re
import subprocess
import tempfile
from collections import defaultdict
from pathlib import Path, PurePosixPath

NEUTRAL = {
    "GIT_AUTHOR_NAME": "mr-bench-review",
    "GIT_AUTHOR_EMAIL": "bench@mr-bench-review.invalid",
    "GIT_COMMITTER_NAME": "mr-bench-review",
    "GIT_COMMITTER_EMAIL": "bench@mr-bench-review.invalid",
    "GIT_AUTHOR_DATE": "2026-01-01T00:00:00+00:00",
    "GIT_COMMITTER_DATE": "2026-01-01T00:00:00+00:00",
}
BASE_MESSAGE = "base snapshot\n"
HEAD_MESSAGE = "change\n"
LICENSE_FILE = re.compile(r"^(licen[cs]e|copying|unlicense)([.-].*)?$", re.IGNORECASE)
# Binary files a reviewer cannot read: images, audio, video, fonts, 3D models, documents,
# archives, compiled code and model weights. Matched on the last suffix, case-insensitively.
MEDIA_SUFFIXES = frozenset(
    {
        # images
        ".png", ".gif", ".jpg", ".jpeg", ".webp", ".bmp", ".ico", ".tif", ".tiff", ".avif",
        ".psd", ".hdr", ".exr", ".ktx2", ".dds", ".basis",
        # audio and video
        ".mp4", ".webm", ".mov", ".avi", ".mkv", ".mp3", ".wav", ".ogg", ".flac", ".m4a",
        # fonts
        ".ttf", ".otf", ".woff", ".woff2", ".eot",
        # 3D models
        ".glb", ".fbx", ".blend", ".3ds", ".usdz", ".drc",
        # documents and archives
        ".pdf", ".gz", ".bz2", ".xz", ".zip", ".tgz", ".7z", ".jar", ".war",
        # compiled code and model weights
        ".so", ".dll", ".dylib", ".exe", ".class", ".pt", ".onnx", ".pb", ".npy", ".h5",
    }
)  # fmt: skip


class GitError(RuntimeError):
    """A git command failed."""


def git(repo: Path, *args: str, stdin: str | None = None, env: dict[str, str] | None = None) -> str:
    """Run git in ``repo`` and return stdout without the trailing newline."""
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        errors="replace",
        input=stdin,
        env={**os.environ, **(env or {})},
        check=False,
    )
    if result.returncode != 0:
        raise GitError(f"git {' '.join(args[:3])}: {result.stderr.strip()[:500]}")
    return result.stdout.rstrip("\n")


def init_bare(repo: Path) -> None:
    """Create the local build repository when missing."""
    if not (repo / "HEAD").exists():
        subprocess.run(["git", "init", "--quiet", "--bare", str(repo)], check=True)


def has_tree(repo: Path, rev: str) -> bool:
    result = subprocess.run(
        ["git", "-C", str(repo), "cat-file", "-e", f"{rev}^{{tree}}"],
        capture_output=True,
        check=False,
    )
    return result.returncode == 0


def fetch_snapshots(repo: Path, url: str, *shas: str, refs: tuple[str, ...] = ()) -> None:
    """Fetch the given commits (and optional refs) without history."""
    missing = [sha for sha in shas if not has_tree(repo, sha)]
    wanted = [*missing, *refs]
    if wanted:
        git(repo, "fetch", "--quiet", "--depth=1", "--no-tags", url, *wanted)


def is_media(path: str) -> bool:
    return PurePosixPath(path).suffix.lower() in MEDIA_SUFFIXES


def tree_paths(repo: Path, rev: str) -> list[str]:
    """Every file path of a tree (reads tree objects only, no blobs)."""
    return [p for p in git(repo, "ls-tree", "-r", "-z", "--name-only", rev).split("\0") if p]


def untouched_media(repo: Path, base: str, head: str) -> dict[str, list[str]]:
    """Media paths of each side that the change between ``base`` and ``head`` does not touch."""
    changed = set(changed_paths(repo, base, head))
    return {
        rev: [p for p in tree_paths(repo, rev) if is_media(p) and p not in changed]
        for rev in (base, head)
    }


def without_paths(repo: Path, rev: str, paths: list[str]) -> str:
    """Tree of ``rev`` minus ``paths``, written through a temporary index.

    ``update-index`` insists on a work tree even for removals; an empty one is given and never
    read.
    """
    if not paths:
        return git(repo, "rev-parse", f"{rev}^{{tree}}")
    with tempfile.TemporaryDirectory() as tmp:
        env = {"GIT_INDEX_FILE": str(Path(tmp) / "index"), "GIT_WORK_TREE": tmp}
        git(repo, "read-tree", f"{rev}^{{tree}}", env=env)
        git(
            repo,
            "update-index",
            "--force-remove",
            "-z",
            "--stdin",
            stdin="\0".join(paths) + "\0",
            env=env,
        )
        return git(repo, "write-tree", env=env)


def build_branches(
    repo: Path, base_ref: str, head_ref: str, base_tree_of: str, head_tree_of: str
) -> tuple[str, str]:
    """Create the orphan base commit and the single head commit; point both branches at them."""
    drop = untouched_media(repo, base_tree_of, head_tree_of)
    base_tree = without_paths(repo, base_tree_of, drop[base_tree_of])
    head_tree = without_paths(repo, head_tree_of, drop[head_tree_of])
    base = git(repo, "commit-tree", base_tree, stdin=BASE_MESSAGE, env=NEUTRAL)
    head = git(repo, "commit-tree", head_tree, "-p", base, stdin=HEAD_MESSAGE, env=NEUTRAL)
    git(repo, "update-ref", f"refs/heads/{base_ref}", base)
    git(repo, "update-ref", f"refs/heads/{head_ref}", head)
    return base, head


def numstat_changed_lines(repo: Path, base: str, head: str) -> int:
    """Added plus deleted text lines between two commits; binary files count zero."""
    total = 0
    for line in git(repo, "diff", "--numstat", "--no-renames", base, head).splitlines():
        added, deleted, _ = line.split("\t", 2)
        if added != "-":
            total += int(added) + int(deleted)
    return total


def changed_new_lines(repo: Path, base: str, head: str) -> dict[str, set[int]]:
    """New-side lines that count as changed, per head path.

    Added lines count, and so do the head lines on each side of a pure deletion, so an issue
    caused by deleted code can sit on the nearest surviving line.
    """
    diff = git(repo, "diff", "-U0", "--no-color", "--no-renames", base, head)
    lines: dict[str, set[int]] = defaultdict(set)
    path: str | None = None
    for row in diff.splitlines():
        if row.startswith("+++ "):
            path = row[6:] if row.startswith("+++ b/") else None
            continue
        match = re.match(r"@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@", row)
        if match and path is not None:
            start = int(match.group(1))
            count = int(match.group(2)) if match.group(2) is not None else 1
            if count:
                lines[path].update(range(start, start + count))
            else:
                lines[path].update(n for n in (start, start + 1) if n > 0)
    return lines


def changed_paths(repo: Path, base: str, head: str) -> list[str]:
    return git(repo, "diff", "--name-only", "--no-renames", base, head).splitlines()


def added_text(repo: Path, base: str, head: str) -> str:
    """Added lines of the diff, without markers."""
    diff = git(repo, "diff", "-U0", "--no-color", "--no-renames", base, head)
    return "\n".join(
        row[1:] for row in diff.splitlines() if row.startswith("+") and not row.startswith("+++")
    )


def file_line_count(repo: Path, rev: str, path: str) -> int | None:
    """Number of lines of a file at ``rev``, or None when absent."""
    try:
        content = git(repo, "show", f"{rev}:{path}")
    except GitError:
        return None
    return len(content.split("\n"))


def has_license_file(repo: Path, rev: str) -> bool:
    """Whether the snapshot carries a licence file, at its root or (older trees) deeper."""
    if any(
        LICENSE_FILE.match(name) for name in git(repo, "ls-tree", "--name-only", rev).splitlines()
    ):
        return True
    paths = git(repo, "ls-tree", "-r", "--name-only", rev).splitlines()
    return any(LICENSE_FILE.match(path.rsplit("/", 1)[-1]) for path in paths)
