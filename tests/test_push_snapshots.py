"""Actions must be disabled before any snapshot push, and restored on failure."""

from pathlib import Path
from unittest.mock import patch

import pytest
from push_snapshots import push_snapshots


@pytest.mark.parametrize("enabled", [False, True])
@pytest.mark.parametrize("fails", [False, True])
def test_push_restores_actions(enabled: bool, fails: bool) -> None:
    events = []

    def push(*args, **kwargs):
        events.append("push")
        if fails:
            raise RuntimeError("push failed")

    with (
        patch("push_snapshots.actions_enabled", return_value=enabled),
        patch("push_snapshots.set_actions", side_effect=lambda repo, value: events.append(value)),
        patch("push_snapshots.subprocess.run", side_effect=push),
    ):
        if fails:
            with pytest.raises(RuntimeError, match="push failed"):
                push_snapshots(Path("work"), "owner/repo", "curated")
        else:
            push_snapshots(Path("work"), "owner/repo", "curated")
    assert events == ([False, "push", True] if enabled else ["push"])


def test_failed_disable_prevents_push() -> None:
    with (
        patch("push_snapshots.actions_enabled", return_value=True),
        patch("push_snapshots.set_actions", side_effect=RuntimeError("denied")),
        patch("push_snapshots.subprocess.run") as push,
    ):
        with pytest.raises(RuntimeError, match="denied"):
            push_snapshots(Path("work"), "owner/repo", "curated")
        push.assert_not_called()
