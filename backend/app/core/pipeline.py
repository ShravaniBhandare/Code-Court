"""Shared analysis pipeline for the CLI and HTTP API."""

from dataclasses import dataclass
from datetime import date, datetime, timezone
import hashlib
import json
from pathlib import Path
from collections.abc import Callable

from app.config import settings
from app.core.activity import collect_activity
from app.core.activity_signals import compute_activity_signals
from app.core.anomalies import build_penalties, detect_anomalies
from app.core.cloner import ensure_clone, get_head_sha
from app.core.commits import list_commits
from app.core.consistency import compute_consistency
from app.core.diff_analysis import analyze_repo_full
from app.core.github_meta import fetch_repo_meta
from app.core.login_map import build_login_map
from app.core.quality_signal import compute_quality_signal
from app.core.score_export import anomalies_to_list, report_to_dict
from app.core.scoring import compute_scores
from app.core.scoring_config import DEFAULT_WEIGHTS, make_config
from app.core.size_signal import compute_size_signal
from app.core.survival import compute_survival


@dataclass(frozen=True)
class AnalysisRequest:
    source: str | Path
    max_commits: int | None = None
    since: datetime | None = None
    until: datetime | None = None
    deadline: datetime | None = None
    weights: dict | None = None
    scaling: str = "log"
    use_github: bool = True
    enable_penalties: bool = True
    github_repo: str | None = None


@dataclass(frozen=True)
class PipelineOutput:
    head_sha: str
    repo_full_name: str
    default_branch: str
    report: object
    report_dict: dict
    anomalies: list
    commit_rows: list[dict]
    warnings: list[str]


def normalized_params(request: AnalysisRequest) -> dict:
    config = make_config(request.weights, request.scaling)
    return {
        "source": str(request.source),
        "max_commits": request.max_commits,
        "since": request.since.isoformat() if request.since else None,
        "until": request.until.isoformat() if request.until else None,
        "deadline": request.deadline.isoformat() if request.deadline else None,
        "weights": {key: config.weights[key] for key in sorted(config.weights)},
        "scaling": config.scaling,
        "use_github": request.use_github,
        "enable_penalties": request.enable_penalties,
        "github_repo": request.github_repo,
    }


def params_hash(request: AnalysisRequest) -> str:
    payload = json.dumps(normalized_params(request), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()


def run_pipeline(
    request: AnalysisRequest,
    progress: Callable[[str, float, str], None] | None = None,
    should_stop: Callable[[], None] | None = None,
) -> PipelineOutput:
    """Run all analysis stages without printing."""
    stop = should_stop or (lambda: None)
    config = make_config(request.weights, request.scaling)
    repo_full_name = request.github_repo or (str(request.source) if isinstance(request.source, str) else "")
    default_branch = "main"
    stop()
    if isinstance(request.source, Path):
        repo_path = request.source.resolve()
    else:
        owner, name = request.source.split("/", 1)
        metadata = fetch_repo_meta(owner, name)
        default_branch = metadata["default_branch"]
        repo_path = ensure_clone(owner, name, metadata["clone_url"])
        repo_full_name = metadata["full_name"]
    if progress:
        progress("validating", 0.05, "Repository validated")
    stop()
    head_sha = get_head_sha(repo_path)
    if progress:
        progress("cloning", 0.10, "Repository ready")
    stop()
    diff_stats, quality_stats = analyze_repo_full(repo_path, request.max_commits)
    if progress:
        progress("commits", 0.50, f"Analyzed {len(diff_stats)} commits")
    stop()
    sizes, _ = compute_size_signal(diff_stats)
    qualities, _ = compute_quality_signal(quality_stats)
    survival = compute_survival(repo_path, diff_stats, progress=lambda d, t: progress("blame", 0.50 + 0.25 * d / max(t, 1), f"Blamed {d}/{t} files") if progress else None)
    stop()
    human_keys = [item.author_key for item in sizes]
    extra: dict[str, dict[str, float]] = {}
    dropped: dict[str, str] = {}
    warnings: list[str] = []
    if request.use_github and request.github_repo:
        owner, name = request.github_repo.split("/", 1)
        activity = collect_activity(owner, name, request.since, progress=lambda step: progress("github", 0.75, f"Collecting GitHub {step}") if progress else None)
        login_map, _ = build_login_map(activity.commit_logins, human_keys)
        activity_signals = compute_activity_signals(activity, login_map, human_keys, config.scaling)
        if activity_signals.review is not None:
            extra["review"] = activity_signals.review
        if activity_signals.issues is not None:
            extra["issues"] = activity_signals.issues
        dropped.update(activity_signals.dropped_reasons)
        warnings.extend(activity.warnings)
    else:
        dropped.update({"review": "PR/issue signals unavailable (no GitHub repository given)", "issues": "PR/issue signals unavailable (no GitHub repository given)"})
    consistency = compute_consistency(diff_stats, human_keys, config.scaling)
    if consistency.values is not None:
        extra["consistency"] = consistency.values
    else:
        dropped["consistency"] = consistency.dropped_reason or "not collected yet"
    anomalies = detect_anomalies(diff_stats, sizes, survival, deadline=request.deadline)
    penalties = build_penalties(anomalies) if request.enable_penalties else {}
    report = compute_scores(sizes, qualities, survival, config, penalties, extra, dropped)
    if progress:
        progress("scoring", 1.0, "Scoring complete")
    commit_rows = [
        {"hash": item.hash, "author_key": item.author_key, "authored_at": item.authored_at, "meaningful_added": item.meaningful_added, "meaningful_credited": item.meaningful_credited, "is_trivial": item.is_trivial, "is_merge": item.is_merge, "is_bulk": item.is_bulk}
        for item in diff_stats
    ]
    report_dict = report_to_dict(report, {
        "anomalies": anomalies_to_list(anomalies),
        "ownership_by_dir": survival.ownership_by_dir,
        "meta": {"head_sha": head_sha, "repo": repo_full_name, "generated_at": datetime.now(timezone.utc).isoformat(), "pipeline_version": settings.PIPELINE_VERSION, "commits_analyzed": len(diff_stats), "window": {"since": request.since.isoformat() if request.since else None, "until": request.until.isoformat() if request.until else None}},
    })
    return PipelineOutput(head_sha, repo_full_name, default_branch, report, report_dict, anomalies, commit_rows, warnings)
