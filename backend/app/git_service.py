"""Git-based versioning service for note history.

Wraps GitPython to provide automatic commits on note CRUD operations
and history browsing. Git failures are logged but never block note ops.

Update commits are batched: at most one commit per note per day to avoid
excessive git overhead that causes input lag.
"""

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import git
from git import Repo
from git.exc import BadName, GitCommandError, InvalidGitRepositoryError

from app.config import get_settings

logger = logging.getLogger(__name__)


class GitService:
    """Manages a git repository at the vault root for note versioning."""

    def __init__(self, vault_path: str) -> None:
        self.vault = Path(vault_path)
        self.repo: Optional[Repo] = None
        # Track which notes have been committed today to batch updates
        # Key: (date_str, relative_path) -> True if already committed today
        self._committed_today: dict[tuple[str, str], bool] = {}

    def ensure_repo(self) -> None:
        """Initialise or open the git repo at the vault root."""
        try:
            self.repo = Repo(self.vault)
            logger.info("Opened existing git repo at %s", self.vault)
        except (InvalidGitRepositoryError, git.NoSuchPathError):
            self.vault.mkdir(parents=True, exist_ok=True)
            self.repo = Repo.init(self.vault)
            logger.info("Initialised new git repo at %s", self.vault)

            # Create initial commit with any existing .md files
            md_files = list(self.vault.rglob("*.md"))
            if md_files:
                rel_paths = [str(f.relative_to(self.vault)) for f in md_files]
                self.repo.index.add(rel_paths)
                self.repo.index.commit("[init] Initial version snapshot")
                logger.info("Initial commit with %d files", len(md_files))

    # ── Commit helpers ──────────────────────────────────────────────────

    def _rel(self, abs_path: Path) -> str:
        """Convert an absolute path to a vault-relative posix path."""
        return str(abs_path.relative_to(self.vault).as_posix())

    def _today_key(self, rel_path: str) -> tuple[str, str]:
        """Return a cache key for today + file path."""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        return (today, rel_path)

    def _has_staged_changes(self) -> bool:
        """Return True when the index contains staged changes."""
        if not self.repo:
            return False

        try:
            if self.repo.head.is_valid():
                return bool(self.repo.index.diff("HEAD"))
            # On a fresh repo (unborn HEAD), inspect index entries directly.
            return bool(self.repo.index.entries)
        except (BadName, GitCommandError, ValueError, OSError):
            logger.exception("Failed to inspect staged changes")
            return bool(self.repo.index.entries)

    def commit_note(self, abs_path: Path, message: str) -> Optional[str]:
        """Stage and commit a single note file. Returns the commit SHA."""
        if not self.repo:
            return None
        try:
            rel = self._rel(abs_path)
            self.repo.index.add([rel])
            commit = self.repo.index.commit(message)
            return commit.hexsha
        except (GitCommandError, ValueError, OSError):
            logger.exception("Git commit failed for %s", abs_path)
            return None

    def commit_note_batched(self, abs_path: Path, message: str) -> Optional[str]:
        """Stage and commit a note, but only once per day per file.

        For update operations, this avoids creating hundreds of commits
        from autosave. The note is still staged so changes aren't lost,
        but the actual commit only happens once per calendar day (UTC).
        """
        if not self.repo:
            return None
        try:
            rel = self._rel(abs_path)
            # Always stage the file so working tree stays clean
            self.repo.index.add([rel])

            key = self._today_key(rel)
            if key in self._committed_today:
                # Already committed today — just stage, skip commit
                logger.debug("Skipping commit for %s (already committed today)", rel)
                return None

            commit = self.repo.index.commit(message)
            self._committed_today[key] = True
            return commit.hexsha
        except (GitCommandError, ValueError, OSError):
            logger.exception("Git batched commit failed for %s", abs_path)
            return None

    def flush_staged(self) -> Optional[str]:
        """Commit any staged but uncommitted changes.

        Called during app shutdown or periodically to ensure no changes
        are lost when using batched commits.
        """
        if not self.repo:
            return None
        try:
            if not self._has_staged_changes():
                return None
            commit = self.repo.index.commit("[auto] Batch save")
            return commit.hexsha
        except (GitCommandError, ValueError, OSError):
            logger.exception("Git flush failed")
            return None

    def commit_delete(self, abs_path: Path, message: str) -> Optional[str]:
        """Stage a file deletion and commit. Returns the commit SHA."""
        if not self.repo:
            return None
        try:
            rel = self._rel(abs_path)
            self.repo.index.remove([rel], working_tree=False, ignore_unmatch=True)
            if not self._has_staged_changes():
                logger.info(
                    "Skipping delete commit for %s because no staged changes were detected",
                    rel,
                )
                return None
            commit = self.repo.index.commit(message)
            return commit.hexsha
        except (GitCommandError, ValueError, OSError):
            logger.exception("Git delete-commit failed for %s", abs_path)
            return None

    def commit_move(
        self,
        old_path: Path,
        new_path: Path,
        message: str,
    ) -> Optional[str]:
        """Stage a file move (delete old + add new) and commit."""
        if not self.repo:
            return None
        try:
            old_rel = self._rel(old_path)
            new_rel = self._rel(new_path)
            self.repo.index.remove([old_rel], working_tree=False, ignore_unmatch=True)
            self.repo.index.add([new_rel])
            if not self._has_staged_changes():
                logger.info(
                    "Skipping move commit for %s -> %s because no staged changes were detected",
                    old_rel,
                    new_rel,
                )
                return None
            commit = self.repo.index.commit(message)
            return commit.hexsha
        except (GitCommandError, ValueError, OSError):
            logger.exception("Git move-commit failed for %s -> %s", old_path, new_path)
            return None

    # ── History queries ─────────────────────────────────────────────────

    def get_file_history(
        self, abs_path: Path, max_count: int = 50
    ) -> list[dict]:
        """Return commit history for a file, following renames."""
        if not self.repo:
            return []
        try:
            rel = self._rel(abs_path)
            commits = list(
                self.repo.iter_commits(
                    paths=rel, max_count=max_count, follow=True
                )
            )
            return [
                {
                    "sha": c.hexsha,
                    "short_sha": c.hexsha[:7],
                    "message": c.message.strip(),
                    "author": str(c.author),
                    "timestamp": c.committed_datetime.isoformat(),
                }
                for c in commits
            ]
        except (GitCommandError, ValueError, OSError):
            logger.exception("Failed to get history for %s", abs_path)
            return []

    def get_file_at_commit(self, abs_path: Path, sha: str) -> Optional[str]:
        """Return the content of a file at a specific commit."""
        if not self.repo:
            return None
        try:
            rel = self._rel(abs_path)
            commit = self.repo.commit(sha)
            blob = commit.tree / rel
            return blob.data_stream.read().decode("utf-8")
        except (BadName, KeyError, GitCommandError, UnicodeDecodeError, ValueError, OSError):
            logger.exception("Failed to read %s at %s", abs_path, sha)
            return None

    def get_diff(self, abs_path: Path, sha: str) -> Optional[str]:
        """Return the unified diff for a file at a specific commit."""
        if not self.repo:
            return None
        try:
            rel = self._rel(abs_path)
            commit = self.repo.commit(sha)
            parents = commit.parents
            if not parents:
                diffs = commit.diff(
                    git.NULL_TREE, paths=[rel], create_patch=True
                )
            else:
                diffs = parents[0].diff(commit, paths=[rel], create_patch=True)
            if diffs:
                return diffs[0].diff.decode("utf-8", errors="replace")
            return None
        except (BadName, GitCommandError, UnicodeDecodeError, ValueError, OSError):
            logger.exception("Failed to get diff for %s at %s", abs_path, sha)
            return None


# ── Singleton ──────────────────────────────────────────────────────────────

_git_service: Optional[GitService] = None


def get_git_service() -> GitService:
    """Return the global GitService singleton."""
    global _git_service
    if _git_service is None:
        settings = get_settings()
        _git_service = GitService(settings.vault_path)
        _git_service.ensure_repo()
    return _git_service


def init_git_service() -> None:
    """Eagerly initialise the git service (called during app startup)."""
    get_git_service()
