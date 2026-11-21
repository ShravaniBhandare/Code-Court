"""Pydantic API schemas."""

from datetime import date, datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator
from app.core.scoring_config import make_config


class AnalyzeRequestModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    repo_url: str = Field(max_length=300)
    max_commits: int | None = Field(default=None, ge=1)
    since: date | None = None
    until: date | None = None
    deadline: date | None = None
    weights: dict[str, float] | None = Field(default=None, max_length=10)
    scaling: Literal["log", "sqrt", "linear"] | None = None
    use_github: bool = True
    enable_penalties: bool = True
    force: bool = False

    @field_validator("weights")
    @classmethod
    def validate_weights(cls, value):
        if value is not None:
            make_config(value, "log")
        return value


class AnalyzeResponse(BaseModel):
    analysis_id: str
    status: str
    cached: bool
    deduplicated: bool
    status_url: str
    results_url: str


class ErrorResponse(BaseModel):
    error: dict
