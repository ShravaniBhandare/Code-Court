from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.database.base import Base
from app.models.commit import Commit
from app.models.contributor import Contributor
from app.models.repository import Repository
from app.services import commit_service as commit_service_module
from app.services.commit_service import CommitService


@pytest.mark.asyncio
async def test_fetch_and_store_commits_uses_github_commit_stats(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    github_service = SimpleNamespace(
        get_repository_commits=AsyncMock(
            return_value=[
                {
                    "sha": "abc123",
                    "commit": {
                        "message": "Initial commit",
                        "author": {
                            "name": "Contributor",
                            "date": "2026-10-05T12:00:00Z",
                        },
                    },
                    "author": {"id": 123, "login": "contributor"},
                }
            ]
        ),
        get_repository_commit=AsyncMock(
            return_value={
                "stats": {
                    "additions": 12,
                    "deletions": 3,
                    "total": 4,
                }
            }
        ),
    )
    monkeypatch.setattr(
        commit_service_module,
        "GitHubService",
        lambda: github_service,
    )
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)

    with Session(engine) as db:
        repository = Repository(
            github_repo_id=12345,
            name="Code-Court",
            owner="rahul",
            url="https://github.com/rahul/Code-Court",
        )
        db.add(repository)
        db.commit()

        service = CommitService()
        await service.fetch_and_store_commits(
            db=db,
            access_token="test-token",
            repository=repository,
        )

        stored_commit = db.scalar(select(Commit))
        assert stored_commit is not None
        assert stored_commit.additions == 12
        assert stored_commit.deletions == 3
        assert stored_commit.files_changed == 4
        github_service.get_repository_commit.assert_awaited_once_with(
            access_token="test-token",
            owner="rahul",
            repository_name="Code-Court",
            commit_sha="abc123",
        )
