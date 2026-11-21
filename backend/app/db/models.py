"""Database models for persisted analyses."""

from datetime import datetime
from sqlalchemy import ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, JSONType, UTCDateTime


class Repository(Base):
    __tablename__ = "repositories"
    id: Mapped[int] = mapped_column(primary_key=True)
    owner: Mapped[str] = mapped_column(String(100))
    name: Mapped[str] = mapped_column(String(100))
    full_name: Mapped[str] = mapped_column(String(201), unique=True, index=True)
    default_branch: Mapped[str] = mapped_column(String(200), default="main")
    created_at: Mapped[datetime] = mapped_column(UTCDateTime)
    last_analyzed_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    analyses: Mapped[list["Analysis"]] = relationship(back_populates="repository")


class Analysis(Base):
    __tablename__ = "analyses"
    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    repo_id: Mapped[int] = mapped_column(ForeignKey("repositories.id"), index=True)
    head_sha: Mapped[str | None] = mapped_column(String(40), nullable=True)
    params: Mapped[dict] = mapped_column(JSONType)
    params_hash: Mapped[str] = mapped_column(String(64), index=True)
    pipeline_version: Mapped[str] = mapped_column(String(50))
    status: Mapped[str] = mapped_column(String(20), index=True)
    stage: Mapped[str] = mapped_column(String(50), default="queued")
    progress: Mapped[float] = mapped_column(default=0.0)
    message: Mapped[str] = mapped_column(String(500), default="")
    error_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    cached_from: Mapped[str | None] = mapped_column(String(32), nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime)
    started_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    report_json: Mapped[dict | None] = mapped_column(JSONType, nullable=True)
    commit_count: Mapped[int] = mapped_column(default=0)
    repository: Mapped[Repository] = relationship(back_populates="analyses")
    scores: Mapped[list["ContributorScore"]] = relationship(cascade="all, delete-orphan")
    anomalies: Mapped[list["AnomalyRow"]] = relationship(cascade="all, delete-orphan")
    commits: Mapped[list["CommitRow"]] = relationship(cascade="all, delete-orphan")
    __table_args__ = (Index("ix_analysis_cache", "repo_id", "head_sha", "params_hash", "pipeline_version", "status"),)


class ContributorScore(Base):
    __tablename__ = "contributor_scores"
    id: Mapped[int] = mapped_column(primary_key=True)
    analysis_id: Mapped[str] = mapped_column(ForeignKey("analyses.id", ondelete="CASCADE"), index=True)
    author_key: Mapped[str] = mapped_column(String(300))
    display_name: Mapped[str] = mapped_column(String(300))
    display_email: Mapped[str] = mapped_column(String(300))
    rank: Mapped[int] = mapped_column()
    score: Mapped[float] = mapped_column()
    base_score: Mapped[float] = mapped_column()
    share_of_team: Mapped[float] = mapped_column()
    penalty_multiplier: Mapped[float] = mapped_column()
    commits: Mapped[int] = mapped_column()
    credited_lines: Mapped[int] = mapped_column()
    surviving_lines: Mapped[int] = mapped_column()
    signals: Mapped[dict] = mapped_column(JSONType)
    notes: Mapped[list] = mapped_column(JSONType)


class AnomalyRow(Base):
    __tablename__ = "anomalies"
    id: Mapped[int] = mapped_column(primary_key=True)
    analysis_id: Mapped[str] = mapped_column(ForeignKey("analyses.id", ondelete="CASCADE"), index=True)
    author_key: Mapped[str] = mapped_column(String(300))
    display_name: Mapped[str] = mapped_column(String(300))
    kind: Mapped[str] = mapped_column(String(100))
    severity: Mapped[str] = mapped_column(String(20))
    message: Mapped[str] = mapped_column(String(1000))
    evidence: Mapped[dict] = mapped_column(JSONType)
    penalty_multiplier: Mapped[float] = mapped_column()


class CommitRow(Base):
    __tablename__ = "commit_rows"
    id: Mapped[int] = mapped_column(primary_key=True)
    analysis_id: Mapped[str] = mapped_column(ForeignKey("analyses.id", ondelete="CASCADE"), index=True)
    hash: Mapped[str] = mapped_column(String(40))
    author_key: Mapped[str] = mapped_column(String(300))
    authored_at: Mapped[datetime] = mapped_column(UTCDateTime)
    meaningful_added: Mapped[int] = mapped_column()
    meaningful_credited: Mapped[int] = mapped_column()
    is_trivial: Mapped[bool] = mapped_column()
    is_merge: Mapped[bool] = mapped_column()
    is_bulk: Mapped[bool] = mapped_column()
    __table_args__ = (UniqueConstraint("analysis_id", "hash"),)
