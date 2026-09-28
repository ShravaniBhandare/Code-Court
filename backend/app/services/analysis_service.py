from collections import defaultdict
from datetime import date
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.commit import Commit
from app.models.contributor import Contributor
from app.models.repository import Repository
from app.services.commit_service import CommitService


class AnalysisService:
    def __init__(self) -> None:
        self.commit_service = CommitService()

    async def analyze_repository(
        self,
        db: Session,
        access_token: str,
        repository_id: int,
    ) -> dict[str, Any]:
        repository = db.get(Repository, repository_id)

        if repository is None:
            raise ValueError("Repository not found")

        await self.commit_service.fetch_and_store_commits(
            db=db,
            access_token=access_token,
            repository=repository,
        )

        contributors = db.scalars(
            select(Contributor).where(
                Contributor.repository_id == repository.id
            )
        ).all()

        total_commits = db.scalar(
            select(func.count(Commit.id)).where(
                Commit.repository_id == repository.id
            )
        ) or 0

        total_additions = db.scalar(
            select(func.coalesce(func.sum(Commit.additions), 0)).where(
                Commit.repository_id == repository.id
            )
        ) or 0

        total_deletions = db.scalar(
            select(func.coalesce(func.sum(Commit.deletions), 0)).where(
                Commit.repository_id == repository.id
            )
        ) or 0

        contributor_metrics: list[dict[str, Any]] = []

        for contributor in contributors:
            contributor_commits = db.scalars(
                select(Commit).where(
                    Commit.repository_id == repository.id,
                    Commit.contributor_id == contributor.id,
                )
            ).all()

            contributor_metrics.append(
                {
                    "github_id": contributor.github_id,
                    "username": contributor.username,
                    "commits": len(contributor_commits),
                    "additions": sum(
                        commit.additions for commit in contributor_commits
                    ),
                    "deletions": sum(
                        commit.deletions for commit in contributor_commits
                    ),
                    "files_changed": sum(
                        commit.files_changed for commit in contributor_commits
                    ),
                }
            )

        activity_counts: defaultdict[date, int] = defaultdict(int)
        repository_commits = db.scalars(
            select(Commit).where(Commit.repository_id == repository.id)
        ).all()

        for commit in repository_commits:
            activity_counts[commit.commit_date.date()] += 1

        activity = [
            {"date": activity_date, "commits": commits}
            for activity_date, commits in sorted(activity_counts.items())
        ]

        return {
            "repository": {
                "id": repository.github_repo_id,
                "name": repository.name,
                "owner": repository.owner,
                "url": repository.url,
            },
            "summary": {
                "total_commits": total_commits,
                "total_contributors": len(contributors),
                "total_additions": total_additions,
                "total_deletions": total_deletions,
            },
            "contributors": contributor_metrics,
            "activity": activity,
        }