from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.commit import Commit
from app.models.contributor import Contributor
from app.models.repository import Repository
from app.services.github_service import GitHubService


class CommitService:
    def __init__(self) -> None:
        self.github_service = GitHubService()

    async def fetch_and_store_commits(
        self,
        db: Session,
        access_token: str,
        repository: Repository,
    ) -> None:
        github_commits = await self.github_service.get_repository_commits(
            access_token=access_token,
            owner=repository.owner,
            repository_name=repository.name,
        )

        for github_commit in github_commits:
            commit_data = github_commit.get("commit", {})
            author_data = commit_data.get("author", {})
            github_author = github_commit.get("author")

            commit_sha = github_commit.get("sha")
            message = commit_data.get("message")
            commit_date_value = author_data.get("date")

            if (
                not isinstance(commit_sha, str)
                or not isinstance(message, str)
                or not isinstance(commit_date_value, str)
            ):
                continue

            existing_commit = db.scalar(
                select(Commit).where(
                    Commit.repository_id == repository.id,
                    Commit.commit_sha == commit_sha,
                )
            )

            if existing_commit is not None:
                continue

            github_id = (
                github_author.get("id")
                if isinstance(github_author, dict)
                else None
            )
            username = (
                github_author.get("login")
                if isinstance(github_author, dict)
                else author_data.get("name")
            )

            if not isinstance(github_id, int) or not isinstance(username, str):
                continue

            commit_details = await self.github_service.get_repository_commit(
                access_token=access_token,
                owner=repository.owner,
                repository_name=repository.name,
                commit_sha=commit_sha,
            )

            contributor = db.scalar(
                select(Contributor).where(
                    Contributor.repository_id == repository.id,
                    Contributor.github_id == github_id,
                )
            )

            if contributor is None:
                contributor = Contributor(
                    repository_id=repository.id,
                    github_id=github_id,
                    username=username,
                    email=author_data.get("email"),
                )
                db.add(contributor)
                db.flush()

            commit_date = datetime.fromisoformat(
                commit_date_value.replace("Z", "+00:00")
            )

            stats = commit_details.get("stats", {})
            if not isinstance(stats, dict):
                raise RuntimeError(
                    "GitHub commit response is missing commit statistics"
                )

            additions = stats.get("additions")
            deletions = stats.get("deletions")
            files_changed = stats.get("total")
            if any(
                not isinstance(value, int) or isinstance(value, bool) or value < 0
                for value in (additions, deletions, files_changed)
            ):
                raise RuntimeError(
                    "GitHub commit response contains invalid commit statistics"
                )

            db.add(
                Commit(
                    repository_id=repository.id,
                    contributor_id=contributor.id,
                    commit_sha=commit_sha,
                    message=message,
                    commit_date=commit_date,
                    additions=additions,
                    deletions=deletions,
                    files_changed=files_changed,
                )
            )

        db.commit()