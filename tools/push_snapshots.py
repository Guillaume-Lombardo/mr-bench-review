"""Push benchmark branches to GitHub with Actions suspended during the push.

Requires gh repository-administration access. Run without concurrent repository pushes or
Actions-setting changes. Snapshot trees remain unchanged, including upstream workflow files.
"""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path


def actions_enabled(repository: str) -> bool:
    result = subprocess.run(
        ["gh", "api", f"repos/{repository}/actions/permissions"],
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(result.stdout)["enabled"]


def set_actions(repository: str, enabled: bool) -> None:
    subprocess.run(
        [
            "gh",
            "api",
            "--method",
            "PUT",
            f"repos/{repository}/actions/permissions",
            "-F",
            f"enabled={str(enabled).lower()}",
        ],
        check=True,
    )


def push_snapshots(work: Path, repository: str, corpus: str) -> None:
    enabled = actions_enabled(repository)
    if enabled:
        set_actions(repository, False)
    try:
        subprocess.run(
            [
                "git",
                "-C",
                str(work),
                "push",
                f"https://github.com/{repository}.git",
                f"refs/heads/bench/{corpus}/*:refs/heads/bench/{corpus}/*",
            ],
            check=True,
        )
    finally:
        if enabled:
            set_actions(repository, True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--work", type=Path, required=True)
    parser.add_argument("--repository", required=True, help="GitHub owner/repository")
    parser.add_argument("--corpus", required=True)
    args = parser.parse_args()
    push_snapshots(args.work, args.repository, args.corpus)


if __name__ == "__main__":
    main()
