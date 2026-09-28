from datetime import date

from pydantic import BaseModel

from app.schemas.repository import RepositoryResponse


class AnalysisSummary(BaseModel):
    total_commits: int
    total_contributors: int
    total_additions: int
    total_deletions: int


class ContributorAnalysis(BaseModel):
    github_id: int
    username: str
    commits: int
    additions: int
    deletions: int
    files_changed: int


class ActivityPoint(BaseModel):
    date: date
    commits: int


class AnalysisResponse(BaseModel):
    repository: RepositoryResponse
    summary: AnalysisSummary
    contributors: list[ContributorAnalysis]
    activity: list[ActivityPoint]