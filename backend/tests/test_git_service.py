"""Regression tests for git history service behavior."""

from __future__ import annotations

from app.git_service import GitService


def test_flush_staged_commits_when_head_is_unborn(tmp_path) -> None:
    """flush_staged should commit staged files even before the first commit exists."""
    vault = tmp_path / "vault"
    vault.mkdir(parents=True, exist_ok=True)

    service = GitService(str(vault))
    service.ensure_repo()
    assert service.repo is not None
    assert not service.repo.head.is_valid()

    note_path = vault / "first.md"
    note_path.write_text("Initial content", encoding="utf-8")

    service.repo.index.add([service._rel(note_path)])
    commit_sha = service.flush_staged()

    assert commit_sha is not None
    assert service.repo.head.is_valid()
    assert service.repo.head.commit.message.strip() == "[auto] Batch save"