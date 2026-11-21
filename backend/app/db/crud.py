"""Database query helpers used by services and routes."""

from datetime import datetime
from uuid import uuid4
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.db.models import Analysis, AnomalyRow, CommitRow, ContributorScore, Repository


def get_or_create_repository(session: Session, owner: str, name: str, default_branch: str = "main") -> Repository:
    full_name = f"{owner}/{name}".lower()
    repo = session.scalar(select(Repository).where(Repository.full_name == full_name))
    if repo:
        return repo
    repo = Repository(owner=owner, name=name, full_name=full_name, default_branch=default_branch, created_at=datetime.now().astimezone())
    session.add(repo)
    session.flush()
    return repo


def create_analysis(session: Session, repo_id: int, head_sha: str, params: dict, params_hash: str, pipeline_version: str) -> Analysis:
    analysis = Analysis(
        id=uuid4().hex, repo_id=repo_id, head_sha=head_sha, params=params,
        params_hash=params_hash, pipeline_version=pipeline_version,
        status="queued", stage="queued", progress=0.0, message="Queued",
        created_at=datetime.now().astimezone(),
    )
    session.add(analysis)
    session.flush()
    return analysis


def get_analysis(session: Session, analysis_id: str) -> Analysis | None:
    return session.get(Analysis, analysis_id)


def find_cached_analysis(session: Session, repo_id: int, head_sha: str, params_hash: str, pipeline_version: str, ttl_cutoff: datetime) -> Analysis | None:
    return session.scalar(select(Analysis).where(
        Analysis.repo_id == repo_id, Analysis.head_sha == head_sha,
        Analysis.params_hash == params_hash, Analysis.pipeline_version == pipeline_version,
        Analysis.status == "succeeded", Analysis.finished_at >= ttl_cutoff,
    ).order_by(Analysis.finished_at.desc()))


def find_inflight_analysis(session: Session, repo_id: int, params_hash: str, pipeline_version: str) -> Analysis | None:
    return session.scalar(select(Analysis).where(
        Analysis.repo_id == repo_id, Analysis.params_hash == params_hash,
        Analysis.pipeline_version == pipeline_version, Analysis.status.in_(("queued", "running")),
    ).order_by(Analysis.created_at.asc()))


def update_progress(session: Session, analysis_id: str, stage: str, progress: float, message: str) -> None:
    session.execute(update(Analysis).where(Analysis.id == analysis_id).values(stage=stage, progress=progress, message=message))
    session.commit()


def mark_running(session: Session, analysis_id: str) -> None:
    session.execute(update(Analysis).where(Analysis.id == analysis_id).values(status="running", started_at=datetime.now().astimezone(), stage="validating"))
    session.commit()


def mark_succeeded(session: Session, analysis_id: str, report_json: dict, commit_count: int, head_sha: str) -> None:
    session.execute(update(Analysis).where(Analysis.id == analysis_id).values(
        status="succeeded", progress=1.0, stage="complete", message="Complete",
        finished_at=datetime.now().astimezone(), report_json=report_json, commit_count=commit_count, head_sha=head_sha,
    ))
    session.commit()


def mark_failed(session: Session, analysis_id: str, code: str, message: str) -> None:
    session.execute(update(Analysis).where(Analysis.id == analysis_id).values(
        status="failed", stage="failed", finished_at=datetime.now().astimezone(),
        error_code=code, error_message=message, message=message,
    ))
    session.commit()


def save_results(session: Session, analysis_id: str, scores: list[dict], anomalies: list[dict], commits: list[dict]) -> None:
    session.query(ContributorScore).filter_by(analysis_id=analysis_id).delete()
    session.query(AnomalyRow).filter_by(analysis_id=analysis_id).delete()
    session.query(CommitRow).filter_by(analysis_id=analysis_id).delete()
    session.add_all([ContributorScore(analysis_id=analysis_id, **row) for row in scores])
    session.add_all([AnomalyRow(analysis_id=analysis_id, **row) for row in anomalies])
    session.add_all([CommitRow(analysis_id=analysis_id, **row) for row in commits])
    session.flush()


def list_analyses(session: Session, limit: int, offset: int) -> list[Analysis]:
    return list(session.scalars(select(Analysis).order_by(Analysis.created_at.desc()).limit(limit).offset(offset)))


def latest_succeeded_for_repo(session: Session, repo_id: int) -> Analysis | None:
    return session.scalar(select(Analysis).where(Analysis.repo_id == repo_id, Analysis.status == "succeeded").order_by(Analysis.finished_at.desc()))


def get_scores(session: Session, analysis_id: str) -> list[ContributorScore]:
    return list(session.scalars(select(ContributorScore).where(ContributorScore.analysis_id == analysis_id).order_by(ContributorScore.rank)))


def get_anomalies(session: Session, analysis_id: str) -> list[AnomalyRow]:
    return list(session.scalars(select(AnomalyRow).where(AnomalyRow.analysis_id == analysis_id)))


def get_commits(session: Session, analysis_id: str) -> list[CommitRow]:
    return list(session.scalars(select(CommitRow).where(CommitRow.analysis_id == analysis_id).order_by(CommitRow.authored_at)))


def count_queued(session: Session) -> int:
    return int(session.scalar(select(func.count()).select_from(Analysis).where(Analysis.status.in_(("queued", "running")))) or 0)


def fail_stale_analyses(session: Session, message: str) -> int:
    result = session.execute(update(Analysis).where(Analysis.status.in_(("queued", "running"))).values(status="failed", stage="failed", error_code="server_restarted", error_message=message, message=message, finished_at=datetime.now().astimezone()))
    session.commit()
    return result.rowcount
