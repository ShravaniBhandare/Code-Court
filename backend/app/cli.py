"""Command-line runner for repository ingestion."""

from collections import Counter
import argparse
from pathlib import Path
import sys

from app.core.cloner import ensure_clone, get_head_sha
from app.core.commits import CommitInfo, list_commits
from app.core.diff_analysis import CommitDiffStats, analyze_repo, analyze_repo_full
from app.core.errors import CodeCourtError
from app.core.github_meta import fetch_repo_meta
from app.core.quality_signal import adjusted_size, compute_quality_signal
from app.core.size_signal import compute_size_signal
from app.core.repo_url import parse_repo_url
from app.core.score_export import write_report_json
from app.core.pdf_export import write_report_pdf
from app.core.scoring import ScoreReport, compute_scores
from app.core.scoring_config import load_config
from app.core.survival import SurvivalResult, compute_survival
from app.core.pipeline import AnalysisRequest, run_pipeline
from app.core.activity import ActivityData, collect_activity
from app.core.activity_signals import compute_activity_signals
from app.core.anomalies import build_penalties, detect_anomalies
from app.core.consistency import compute_consistency
from app.core.login_map import build_login_map
from datetime import datetime, timezone
from app.core.score_export import anomalies_to_list


def _print_report(commits: list[CommitInfo]) -> None:
    """Print a concise commit summary."""
    merges = sum(commit.is_merge for commit in commits)
    print(f"total commits: {len(commits)}")
    print(f"merge commits: {merges}")
    if commits:
        print(f"first commit date: {commits[0].authored_at.isoformat()}")
        print(f"last commit date: {commits[-1].authored_at.isoformat()}")
    else:
        print("first commit date: n/a")
        print("last commit date: n/a")
    authors = Counter((commit.author_name, commit.author_email) for commit in commits)
    print("top authors:")
    print("name | email | count")
    for (name, email), count in authors.most_common(10):
        print(f"{name} | {email} | {count}")
    print(f"total insertions: {sum(commit.insertions for commit in commits)}")
    print(f"total deletions: {sum(commit.deletions for commit in commits)}")


def _print_size_report(stats: list[CommitDiffStats]) -> None:
    """Print the meaningful-lines contribution report."""
    from app.core.size_signal import compute_size_signal

    humans, bots = compute_size_signal(stats)
    print("author | email | commits | trivial commits (%) | raw added | meaningful added | credited | size score")
    for author in humans:
        percentage = author.trivial_ratio * 100
        print(
            f"{author.display_name} | {author.display_email} | {author.commits} | "
            f"{author.trivial_commits} ({percentage:.1f}%) | {author.raw_added} | "
            f"{author.meaningful_added} | {author.meaningful_credited} | {author.size_score:.4f}"
        )
    bulk = sum(item.is_bulk for item in stats)
    skipped = Counter(reason for item in stats for reason in item.skipped_files)
    print(f"bulk commits: {bulk}")
    print("skipped files by reason:")
    for reason, count in sorted(skipped.items()):
        print(f"{reason}: {count}")
    print("bots:")
    for bot in bots:
        print(bot.display_name)


def _run_size(args: argparse.Namespace) -> int:
    """Run the size-signal command."""
    try:
        if args.local is not None:
            repo_path = args.local.resolve()
        else:
            if args.repo is None:
                raise CodeCourtError("repo URL is required unless --local is used")
            owner, repo = parse_repo_url(args.repo)
            metadata = fetch_repo_meta(owner, repo)
            repo_path = ensure_clone(owner, repo, metadata["clone_url"])
        def progress(done: int, total: int) -> None:
            print(f"analyzing commits: {done}/{total}")
        _print_size_report(analyze_repo(repo_path, args.max_commits, progress=progress))
        return 0
    except CodeCourtError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1


def _run_quality(args: argparse.Namespace) -> int:
    """Run the combined size and quality analysis command."""
    try:
        if args.local is not None:
            repo_path = args.local.resolve()
        else:
            if args.repo is None:
                raise CodeCourtError("repo URL is required unless --local is used")
            owner, repo = parse_repo_url(args.repo)
            metadata = fetch_repo_meta(owner, repo)
            repo_path = ensure_clone(owner, repo, metadata["clone_url"])

        def progress(done: int, total: int) -> None:
            print(f"analyzing commits: {done}/{total}")

        diff_stats, quality_stats = analyze_repo_full(
            repo_path, args.max_commits, progress=progress
        )
        size_humans, _ = compute_size_signal(diff_stats)
        quality_humans, _ = compute_quality_signal(quality_stats)
        size_by_key = {item.author_key: item for item in size_humans}
        print(
            "author | email | commits | credited lines | functions analyzed | "
            "avg complexity | max complexity | long functions | quality score | "
            "modifier | adjusted size | flag"
        )
        for quality in quality_humans:
            size = size_by_key.get(quality.author_key)
            credited = size.meaningful_credited if size else 0
            flag = "LOW-CONF" if quality.low_confidence else ""
            print(
                f"{quality.display_name} | {quality.display_email} | "
                f"{size.commits if size else 0} | {credited} | "
                f"{quality.functions_analyzed} | {quality.avg_complexity:.2f} | "
                f"{quality.max_complexity} | {quality.long_functions} | "
                f"{quality.quality_score:.4f} | {quality.quality_modifier:.4f} | "
                f"{adjusted_size(credited, quality.quality_modifier):.2f} | {flag}"
            )
        all_functions = [
            (quality, function)
            for quality in quality_humans
            for item in quality_stats
            if item.author_key == quality.author_key
            for function in item.functions
        ]
        skipped = Counter(
            reason
            for item in quality_stats
            for reason, count in item.skipped_files.items()
            for _ in range(count)
        )
        print(f"total functions analyzed: {sum(len(item.functions) for item in quality_stats)}")
        print("files skipped by reason:")
        for reason, count in sorted(skipped.items()):
            print(f"{reason}: {count}")
        print("most complex touched functions:")
        for quality, function in sorted(
            all_functions,
            key=lambda pair: (-pair[1].cyclomatic_complexity, pair[1].path, pair[1].function_name),
        )[:5]:
            print(
                f"{quality.display_name} | {function.path} | "
                f"{function.function_name} | {function.cyclomatic_complexity}"
            )
        return 0
    except CodeCourtError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1


def _print_survival_report(stats: list[CommitDiffStats], result: SurvivalResult) -> None:
    """Print the survival-signal report."""
    commits_by_key = Counter(
        item.author_key for item in stats if not item.is_merge and not item.is_bot
    )
    print(
        "author | email | commits | meaningful added | surviving lines | "
        "survival rate | survival score | ownership share | flag"
    )
    for author in result.authors:
        rate = "n/a" if author.survival_rate is None else f"{author.survival_rate * 100:.1f}%"
        score = "n/a" if author.survival_score is None else f"{author.survival_score:.4f}"
        flag = "LOW-CONF" if author.low_confidence else ""
        print(
            f"{author.display_name} | {author.display_email} | "
            f"{commits_by_key[author.author_key]} | {author.meaningful_added} | "
            f"{author.surviving_lines} | {rate} | {score} | "
            f"{author.ownership_share * 100:.1f}% | {flag}"
        )
    print(f"coverage: {result.coverage * 100:.1f}%")
    print(f"files blamed: {result.files_blamed}")
    print("skipped files by reason:")
    for reason, count in result.files_skipped.items():
        print(f"{reason}: {count}")
    repo_rate = "n/a" if result.repo_survival_rate is None else f"{result.repo_survival_rate * 100:.1f}%"
    print(f"repo survival rate: {repo_rate}")
    accounting = result.accounting
    print(
        "accounting: "
        f"meaningful_lines_at_head={accounting['meaningful_lines_at_head']} "
        f"attributed_to_humans={accounting['attributed_to_humans']} "
        f"attributed_to_bots={accounting['attributed_to_bots']} "
        f"outside_window={accounting['outside_window']} "
        f"unattributed={accounting['unattributed']}"
    )
    print("top directory owners:")
    directories = sorted(
        result.ownership_by_dir.items(),
        key=lambda item: (-sum(item[1].values()), item[0]),
    )
    for directory, owners in directories[:8]:
        top_owners = sorted(owners.items(), key=lambda item: (-item[1], item[0]))[:3]
        print(f"{directory}: " + ", ".join(f"{key}={count}" for key, count in top_owners))
    if result.partial:
        print(
            "WARNING: survival scores are unavailable because blame coverage is too low; "
            "consider lowering the file limits."
        )


def _run_survival(args: argparse.Namespace) -> int:
    """Run the Git-blame survival analysis command."""
    try:
        if args.local is not None:
            repo_path = args.local.resolve()
        else:
            if args.repo is None:
                raise CodeCourtError("repo URL is required unless --local is used")
            owner, repo = parse_repo_url(args.repo)
            metadata = fetch_repo_meta(owner, repo)
            repo_path = ensure_clone(owner, repo, metadata["clone_url"])

        def progress(done: int, total: int) -> None:
            print(f"blaming files: {done}/{total}")

        stats = analyze_repo(repo_path, args.max_commits)
        _print_survival_report(stats, compute_survival(repo_path, stats, progress=progress))
        return 0
    except CodeCourtError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1


def _print_score_report(report: ScoreReport) -> None:
    """Print the contribution score report."""
    extra_columns = [
        name for name in ("review", "issues", "consistency")
        if name in report.available_signals
    ]
    columns = ["rank", "author", "email", "score", "base", "share", "work", "survival", "ownership"]
    columns.extend(extra_columns)
    columns.append("notes")
    print(" | ".join(columns))
    for author in report.authors:
        signal_scores = [f"{author.signals[name].points:.2f}" for name in ("work", "survival", "ownership")]
        points = signal_scores + [f"{author.signals[name].points:.2f}" for name in extra_columns]
        print(
            f"{author.rank} | {author.display_name} | {author.display_email} | "
            f"{author.score:.2f} | {author.base_score:.2f} | "
            f"{author.share_of_team:.2f}% | {' | '.join(points)} | "
            f"{'; '.join(author.notes)}"
        )
    print(f"available signals: {', '.join(report.available_signals) or 'none'}")
    print("effective weights:")
    for name, weight in report.effective_weights.items():
        print(f"{name}: {weight:.4f}")
    for note in report.repo_notes:
        print(f"note: {note}")


def _run_score(args: argparse.Namespace) -> int:
    """Run the combined contribution scoring command."""
    try:
        github_target = None
        if args.local is not None:
            repo_path = args.local.resolve()
            github_target = args.github_repo
        else:
            if args.repo is None:
                raise CodeCourtError("repo URL is required unless --local is used")
            owner, repo = parse_repo_url(args.repo)
            metadata = fetch_repo_meta(owner, repo)
            repo_path = ensure_clone(owner, repo, metadata["clone_url"])
            github_target = f"{owner}/{repo}"

        deadline = None
        if args.deadline:
            deadline = datetime.strptime(args.deadline, "%Y-%m-%d").replace(
                hour=23, minute=59, second=59, tzinfo=timezone.utc
            )
        config = load_config(args.weights) if args.weights else None
        request = AnalysisRequest(
            source=github_target if args.local is None else repo_path,
            max_commits=args.max_commits,
            deadline=deadline,
            weights=config.weights if config else None,
            scaling=config.scaling if config else "log",
            use_github=not args.no_github,
            enable_penalties=not args.no_penalties,
            github_repo=github_target,
        )
        output = run_pipeline(
            request,
            progress=lambda stage, fraction, message: print(
                f"{stage}: {message}"
            ),
        )
        _print_score_report(output.report)
        if args.json is not None:
            write_report_json(output.report, args.json, output.report_dict)
            print(f"JSON report: {args.json}")
        if args.pdf is not None:
            write_report_pdf(output.report_dict, args.pdf)
            print(f"PDF report: {args.pdf}")
        print("Anomalies")
        for anomaly in output.anomalies:
            print(f"{anomaly.severity} | {anomaly.display_name} | {anomaly.kind} | {anomaly.message}")
        for warning in output.warnings:
            print(f"GitHub warning: {warning}")
        return 0
    except (CodeCourtError, ValueError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1


def main(argv: list[str] | None = None) -> int:
    """Run repository ingestion or the size-signal command."""
    arguments = sys.argv[1:] if argv is None else argv
    if arguments and arguments[0] == "size":
        size_parser = argparse.ArgumentParser(prog="python -m app.cli size")
        size_parser.add_argument("command", choices=["size"], help=argparse.SUPPRESS)
        size_parser.add_argument("repo", nargs="?")
        size_parser.add_argument("--max-commits", type=int)
        size_parser.add_argument("--local", type=Path)
        return _run_size(size_parser.parse_args(arguments))
    if arguments and arguments[0] == "quality":
        quality_parser = argparse.ArgumentParser(prog="python -m app.cli quality")
        quality_parser.add_argument("command", choices=["quality"], help=argparse.SUPPRESS)
        quality_parser.add_argument("repo", nargs="?")
        quality_parser.add_argument("--max-commits", type=int)
        quality_parser.add_argument("--local", type=Path)
        return _run_quality(quality_parser.parse_args(arguments))
    if arguments and arguments[0] == "survival":
        survival_parser = argparse.ArgumentParser(prog="python -m app.cli survival")
        survival_parser.add_argument("command", choices=["survival"], help=argparse.SUPPRESS)
        survival_parser.add_argument("repo", nargs="?")
        survival_parser.add_argument("--max-commits", type=int)
        survival_parser.add_argument("--local", type=Path)
        return _run_survival(survival_parser.parse_args(arguments))
    if arguments and arguments[0] == "score":
        score_parser = argparse.ArgumentParser(prog="python -m app.cli score")
        score_parser.add_argument("command", choices=["score"], help=argparse.SUPPRESS)
        score_parser.add_argument("repo", nargs="?")
        score_parser.add_argument("--max-commits", type=int)
        score_parser.add_argument("--local", type=Path)
        score_parser.add_argument("--weights", type=Path)
        score_parser.add_argument("--json", type=Path)
        score_parser.add_argument("--pdf", type=Path)
        score_parser.add_argument("--repo", dest="github_repo")
        score_parser.add_argument("--no-github", action="store_true")
        score_parser.add_argument("--deadline")
        score_parser.add_argument("--no-penalties", action="store_true")
        return _run_score(score_parser.parse_args(arguments))

    parser = argparse.ArgumentParser()
    parser.add_argument("repo", nargs="?")
    parser.add_argument("--max-commits", type=int)
    parser.add_argument("--local", type=Path)
    args = parser.parse_args(arguments)
    try:
        if args.local is not None:
            repo_path = args.local.resolve()
            commits = list_commits(repo_path, args.max_commits)
        else:
            if args.repo is None:
                parser.error("repo URL is required unless --local is used")
            owner, repo = parse_repo_url(args.repo)
            metadata = fetch_repo_meta(owner, repo)
            repo_path = ensure_clone(owner, repo, metadata["clone_url"])
            print(f"repo: {metadata['full_name']}")
            print(f"default branch: {metadata['default_branch']}")
            print(f"size: {metadata['size_kb']} KB")
            print(f"HEAD sha: {get_head_sha(repo_path)}")
            commits = list_commits(repo_path, args.max_commits)
        _print_report(commits)
        return 0
    except CodeCourtError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
