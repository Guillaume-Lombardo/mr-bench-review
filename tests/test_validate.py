"""Contract and validator behaviour on a tiny synthetic corpus."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
import validate
from contract import Case, size_for
from convert_common import neutral_description, neutral_title, short_title
from gitsnap import (
    NEUTRAL,
    build_branches,
    changed_new_lines,
    changed_paths,
    git,
    init_bare,
    tree_paths,
)
from pydantic import ValidationError

CORPUS = {
    "schema_version": 1,
    "name": "demo",
    "title": "Demo",
    "origin": "test",
    "source_url": None,
    "licence": "MIT",
    "default": True,
    "annotation": "human",
    "location_precision": "lines",
    "severity_available": True,
    "created_at": "2026-09-30",
}


def make_upstream(tmp_path: Path) -> tuple[Path, str, str]:
    """Upstream repository with two commits: a base file and a one-line change."""
    upstream = tmp_path / "upstream"
    subprocess.run(["git", "init", "-q", str(upstream)], check=True)
    env = {
        "GIT_AUTHOR_NAME": "a",
        "GIT_AUTHOR_EMAIL": "a@a",
        "GIT_COMMITTER_NAME": "a",
        "GIT_COMMITTER_EMAIL": "a@a",
    }
    (upstream / "LICENSE").write_text("MIT\n")
    (upstream / "app.py").write_text("def f(x):\n    return x\n\n\nprint(f(1))\n")
    (upstream / "docs").mkdir()
    (upstream / "docs" / "logo.PNG").write_bytes(b"\x89PNG\x00logo")
    (upstream / "icon.png").write_bytes(b"\x89PNG\x00old")
    git(upstream, "add", ".")
    git(upstream, "commit", "-q", "-m", "one", env=env)
    base = git(upstream, "rev-parse", "HEAD")
    (upstream / "app.py").write_text("def f(x):\n    return x + 1\n\n\nprint(f(1))\n")
    (upstream / "icon.png").write_bytes(b"\x89PNG\x00new")
    git(upstream, "commit", "-q", "-am", "two", env=env)
    return upstream, base, git(upstream, "rev-parse", "HEAD")


def make_case(repo: Path, base: str, head: str, **issue: object) -> dict[str, object]:
    return {
        "schema_version": 1,
        "corpus": "demo",
        "id": "case-001",
        "language": "python",
        "size": "small",
        "kind": "real",
        "tier": "pilot",
        "base_branch": "bench/demo/case-001/base",
        "head_branch": "bench/demo/case-001/head",
        "base_sha": base,
        "head_sha": head,
        "mr_title": "Increment result",
        "mr_description": "",
        "origin": None,
        "expected_issues": [
            {
                "id": "i1",
                "file": "app.py",
                "line_start": 2,
                "line_end": 2,
                "category": "correctness",
                "severity": "high",
                "title": "Off by one",
                "description": "Returns x + 1.",
                "outside_diff": False,
                "alternative_locations": [],
                "source_category": None,
                "source_text": None,
                **issue,
            }
        ],
        "known_false_positives": [],
        "annotator_notes": "",
    }


@pytest.fixture
def dataset(tmp_path: Path) -> tuple[Path, Path]:
    upstream, base_up, head_up = make_upstream(tmp_path)
    work = tmp_path / "bench.git"
    init_bare(work)
    git(work, "fetch", "-q", str(upstream), "HEAD")
    base, head = build_branches(
        work, "bench/demo/case-001/base", "bench/demo/case-001/head", base_up, head_up
    )
    root = tmp_path / "root"
    (root / "corpora" / "demo" / "cases").mkdir(parents=True)
    (root / "dataset.json").write_text('{"schema_version": 1, "dataset_version": "1.0.0"}')
    (root / "corpora" / "demo" / "corpus.json").write_text(json.dumps(CORPUS))
    for name in ("SOURCE.md", "EXCLUDED.md"):
        (root / "corpora" / "demo" / name).write_text("")
    case = make_case(work, base, head)
    (root / "corpora" / "demo" / "cases" / "case-001.json").write_text(json.dumps(case))
    return root, work


def run(root: Path, work: Path, *extra: str) -> int:
    return validate.main(["--root", str(root), "--repo", str(work), *extra])


def test_valid_dataset_passes(dataset: tuple[Path, Path]) -> None:
    assert run(*dataset) == 0


def test_untouched_media_left_out(dataset: tuple[Path, Path]) -> None:
    root, work = dataset
    case = json.loads((root / "corpora/demo/cases/case-001.json").read_text())
    for sha in (case["base_sha"], case["head_sha"]):
        assert tree_paths(work, sha) == ["LICENSE", "app.py", "icon.png"]
    assert changed_paths(work, case["base_sha"], case["head_sha"]) == ["app.py", "icon.png"]


def test_untrimmed_snapshot_rejected(dataset: tuple[Path, Path]) -> None:
    root, work = dataset
    path = root / "corpora/demo/cases/case-001.json"
    case = json.loads(path.read_text())
    upstream_head = git(work, "rev-parse", "FETCH_HEAD")
    base = git(
        work, "commit-tree", f"{upstream_head}^^{{tree}}", stdin="base snapshot\n", env=NEUTRAL
    )
    head = git(
        work, "commit-tree", f"{upstream_head}^{{tree}}", "-p", base, stdin="change\n", env=NEUTRAL
    )
    git(work, "update-ref", "refs/heads/bench/demo/case-001/base", base)
    git(work, "update-ref", "refs/heads/bench/demo/case-001/head", head)
    path.write_text(json.dumps({**case, "base_sha": base, "head_sha": head}))
    assert run(root, work) == 1


def test_branches_are_deterministic(dataset: tuple[Path, Path], tmp_path: Path) -> None:
    root, work = dataset
    case = json.loads((root / "corpora/demo/cases/case-001.json").read_text())
    again = build_branches(work, "x/base", "x/head", f"{case['base_sha']}", f"{case['head_sha']}")
    assert again == (case["base_sha"], case["head_sha"])


def test_issue_off_changed_lines_fails(
    dataset: tuple[Path, Path], capsys: pytest.CaptureFixture[str]
) -> None:
    root, work = dataset
    path = root / "corpora/demo/cases/case-001.json"
    case = json.loads(path.read_text())
    case["expected_issues"][0].update(line_start=5, line_end=5)
    path.write_text(json.dumps(case))
    assert run(root, work) == 1
    assert "not on a changed line" in capsys.readouterr().err


def test_pinned_sha_mismatch_fails(
    dataset: tuple[Path, Path], capsys: pytest.CaptureFixture[str]
) -> None:
    root, work = dataset
    path = root / "corpora/demo/cases/case-001.json"
    case = json.loads(path.read_text())
    case["head_sha"] = "0" * 40
    path.write_text(json.dumps(case))
    assert run(root, work) == 1
    assert "pinned" in capsys.readouterr().err


def test_leak_in_mr_text_fails(
    dataset: tuple[Path, Path], capsys: pytest.CaptureFixture[str]
) -> None:
    root, work = dataset
    corpus = json.loads((root / "corpora/demo/corpus.json").read_text())
    corpus["name"] = "curated"
    (root / "corpora/demo").rename(root / "corpora/curated")
    (root / "corpora/curated/corpus.json").write_text(json.dumps(corpus))
    path = root / "corpora/curated/cases/case-001.json"
    case = json.loads(path.read_text())
    case.update(
        corpus="curated",
        base_branch="bench/curated/case-001/base",
        head_branch="bench/curated/case-001/head",
        mr_title="FIXME off by one",
    )
    path.write_text(json.dumps(case))
    build_branches(
        work,
        "bench/curated/case-001/base",
        "bench/curated/case-001/head",
        case["base_sha"],
        case["head_sha"],
    )
    assert run(root, work) == 1
    assert "leak pattern" in capsys.readouterr().err


def test_unknown_field_rejected(dataset: tuple[Path, Path]) -> None:
    root, _ = dataset
    case = json.loads((root / "corpora/demo/cases/case-001.json").read_text())
    case["hint"] = "no"
    with pytest.raises(ValidationError):
        Case.model_validate(case)


def test_clean_case_cannot_list_issues(dataset: tuple[Path, Path]) -> None:
    root, _ = dataset
    case = json.loads((root / "corpora/demo/cases/case-001.json").read_text())
    case["kind"] = "clean"
    with pytest.raises(ValidationError, match="clean case"):
        Case.model_validate(case)


def test_size_boundaries() -> None:
    assert (size_for(99), size_for(100), size_for(600), size_for(601)) == (
        "small",
        "medium",
        "medium",
        "large",
    )


def test_pure_deletion_marks_neighbouring_lines(tmp_path: Path) -> None:
    upstream, _, head_up = make_upstream(tmp_path)
    (upstream / "app.py").write_text("def f(x):\n    return x + 1\n")
    git(
        upstream,
        "commit",
        "-q",
        "-am",
        "three",
        env={
            "GIT_AUTHOR_NAME": "a",
            "GIT_AUTHOR_EMAIL": "a@a",
            "GIT_COMMITTER_NAME": "a",
            "GIT_COMMITTER_EMAIL": "a@a",
        },
    )
    lines = changed_new_lines(upstream, head_up, "HEAD")
    assert lines["app.py"] == {2, 3}


def test_neutral_text() -> None:
    title, _ = neutral_title("Fixed #36140 -- Allowed optional passwords (#123)")
    assert title == "Allowed optional passwords"
    assert neutral_description("Improve X.\n\nFixes #12\nCo-authored-by: A <a@a>") == "Improve X."
    assert short_title("First sentence. Second one.") == "First sentence"


@pytest.mark.parametrize("kind", ["alternative", "false_positive"])
@pytest.mark.parametrize("file,end", [("missing.py", 2), ("app.py", 99999)])
def test_extra_locations_rejected(
    dataset: tuple[Path, Path], kind: str, file: str, end: int
) -> None:
    root, work = dataset
    path = root / "corpora/demo/cases/case-001.json"
    case = json.loads(path.read_text())
    location = {"file": file, "line_start": end, "line_end": end}
    if kind == "alternative":
        case["expected_issues"][0]["alternative_locations"] = [location]
    else:
        case["known_false_positives"] = [{**location, "description": "Rejected"}]
    path.write_text(json.dumps(case))
    assert run(root, work) == 1


def test_extra_locations_allow_context(dataset: tuple[Path, Path]) -> None:
    root, work = dataset
    path = root / "corpora/demo/cases/case-001.json"
    case = json.loads(path.read_text())
    case["expected_issues"][0]["alternative_locations"] = [
        {"file": "app.py", "line_start": 5, "line_end": 5}
    ]
    case["known_false_positives"] = [
        {"file": "app.py", "line_start": None, "line_end": None, "description": "Rejected"},
        {"file": None, "line_start": None, "line_end": None, "description": "Unlocated"},
    ]
    path.write_text(json.dumps(case))
    assert run(root, work) == 0


@pytest.mark.parametrize(
    "content,count", [("", 0), ("a", 1), ("a\n", 1), ("a\n\n\n", 3), ("\n\n", 2), ("a\nb", 2)]
)
def test_line_count_preserves_blank_lines(tmp_path: Path, content: str, count: int) -> None:
    from gitsnap import file_line_count

    repo, _, _ = make_upstream(tmp_path)
    (repo / "app.py").write_text(content)
    git(repo, "add", "app.py")
    tree = git(repo, "write-tree")
    assert file_line_count(repo, tree, "app.py") == count
    assert file_line_count(repo, tree, "missing.py") is None


@pytest.mark.parametrize("kind", ["alternative", "false_positive"])
def test_extra_file_level_location_can_reference_deleted_file(
    dataset: tuple[Path, Path], kind: str
) -> None:
    from gitsnap import without_paths

    root, work = dataset
    path = root / "corpora/demo/cases/case-001.json"
    case = json.loads(path.read_text())
    tree = without_paths(work, case["head_sha"], ["app.py"])
    base, head = build_branches(
        work, case["base_branch"], case["head_branch"], case["base_sha"], tree
    )
    case.update(base_sha=base, head_sha=head)
    case["expected_issues"][0].update(line_start=None, line_end=None, outside_diff=True)
    location = {"file": "app.py", "line_start": None, "line_end": None}
    if kind == "alternative":
        case["expected_issues"][0]["alternative_locations"] = [location]
    else:
        case["known_false_positives"] = [{**location, "description": "Rejected"}]
    path.write_text(json.dumps(case))
    assert run(root, work) == 0
    if kind == "alternative":
        case["expected_issues"][0]["alternative_locations"][0].update(line_start=2, line_end=2)
    else:
        case["known_false_positives"][0].update(line_start=2, line_end=2)
    path.write_text(json.dumps(case))
    assert run(root, work) == 1
