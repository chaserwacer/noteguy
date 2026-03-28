"""Git-based versioning service for note history.

Wraps GitPython to provide automatic commits on note CRUD operations
and history browsing. Git failures are logged but never block note ops.
"""

import logging
from pathlib import Path
from typing import Optional

import git
from git import Repo, InvalidGitRepositoryError

from app.config import get_settings

logger = logging.getLogger(__name__)


class GitService:
    """Manages a git repository at the vault root for note versioning."""

    def __init__(self, vault_path: str) -> None:
        self.vault = Path(vault_path)
        self.repo: Optional[Repo] = None

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

    def commit_note(self, abs_path: Path, message: str) -> Optional[str]:
        """Stage and commit a single note file. Returns the commit SHA."""
        if not self.repo:
            return None
        try:
            rel = self._rel(abs_path)
            self.repo.index.add([rel])
            commit = self.repo.index.commit(message)
            return commit.hexsha
        except Exception:
            logger.exception("Git commit failed for %s", abs_path)
            return None

    def commit_delete(self, abs_path: Path, message: str) -> Optional[str]:
        """Stage a file deletion and commit. Returns the commit SHA."""
        if not self.repo:
            return None
        try:
            rel = self._rel(abs_path)
            # Only remove from index if git is tracking the file
            try:
                self.repo.index.remove([rel])
            except Exception:
                # File may not be tracked yet — that's fine
                return None
            commit = self.repo.index.commit(message)
            return commit.hexsha
        except Exception:
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
            try:
                self.repo.index.remove([old_rel])
            except Exception:
                pass
            self.repo.index.add([new_rel])
            commit = self.repo.index.commit(message)
            return commit.hexsha
        except Exception:
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
        except Exception:
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
        except Exception:
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
                # First commit — diff against empty tree
                diffs = commit.diff(
                    git.NULL_TREE, paths=[rel], create_patch=True
                )
            else:
                diffs = parents[0].diff(commit, paths=[rel], create_patch=True)
            if diffs:
                return diffs[0].diff.decode("utf-8", errors="replace")
            return None
        except Exception:
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
