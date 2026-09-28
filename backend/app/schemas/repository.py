from pydantic import BaseModel


class RepositoryResponse(BaseModel):
    id: int
    name: str
    owner: str
    url: str


class RepositoryListResponse(BaseModel):
    repositories: list[RepositoryResponse]