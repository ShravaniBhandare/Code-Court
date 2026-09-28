from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.repository import Repository
from app.services.github_service import GitHubService


class RepositoryService:
    def __init__(self) -> None:
        self.github_service = GitHubService()

    async def list_repositories(
        self,
        db: Session,
        access_token: str,
    ) -> list[dict[str, Any]]:
        github_repositories = await self.github_service.get_user_repositories(
            access_token
        )

        repositories: list[dict[str, Any]] = []

        for github_repository in github_repositories:
            github_repo_id = github_repository.get("id")
            name = github_repository.get("name")
            owner_data = github_repository.get("owner", {})
            owner = owner_data.get("login") if isinstance(owner_data, dict) else None
            url = github_repository.get("html_url")

            if (
                not isinstance(github_repo_id, int)
                or not isinstance(name, str)
                or not isinstance(owner, str)
                or not isinstance(url, str)
            ):
                continue

            repository = db.scalar(
                select(Repository).where(
                    Repository.github_repo_id == github_repo_id
                )
            )

            if repository is None:
                repository = Repository(
                    github_repo_id=github_repo_id,
                    name=name,
                    owner=owner,
                    url=url,
                )
                db.add(repository)
            else:
                repository.name = name
                repository.owner = owner
                repository.url = url

            repositories.append(
                {
                    "id": github_repo_id,
                    "name": name,
                    "owner": owner,
                    "url": url,
                }
            )

        db.commit()
        return repositories