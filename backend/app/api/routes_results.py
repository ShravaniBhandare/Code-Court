"""Analysis result routes."""

from fastapi import APIRouter, Depends, Response
from app.api.dependencies import get_service
from app.core.errors import AnalysisNotReady

router = APIRouter()


@router.get("/scores/{analysis_id}")
def scores(analysis_id: str, service=Depends(get_service)):
    analysis, rows = service.get_scores(analysis_id)
    ranking = [
        {
            "author_key": row.author_key, "display_name": row.display_name,
            "display_email": row.display_email, "rank": row.rank,
            "score": row.score, "base_score": row.base_score,
            "share_of_team": row.share_of_team,
            "penalty_multiplier": row.penalty_multiplier,
            "commits": row.commits, "credited_lines": row.credited_lines,
            "surviving_lines": row.surviving_lines, "signals": row.signals,
            "notes": row.notes,
        }
        for row in rows
    ]
    return {"ranking": ranking, **(analysis.report_json or {})}


@router.get("/anomalies/{analysis_id}")
def anomalies(analysis_id: str, service=Depends(get_service)):
    analysis = service.get_analysis(analysis_id)
    if analysis.status != "succeeded":
        raise AnalysisNotReady(f"Analysis is {analysis.status}")
    session = service.session_factory()
    try:
        rows = sorted(__import__("app.db.crud", fromlist=["get_anomalies"]).get_anomalies(session, analysis_id), key=lambda row: (0 if row.severity == "warning" else 1, row.display_name, row.kind))
        return {"anomalies": [
            {"author_key": row.author_key, "display_name": row.display_name,
             "kind": row.kind, "severity": row.severity, "message": row.message,
             "evidence": row.evidence, "penalty_multiplier": row.penalty_multiplier}
            for row in rows
        ], "counts": {"warning": sum(row.severity == "warning" for row in rows), "info": sum(row.severity == "info" for row in rows)}}
    finally:
        session.close()


@router.get("/timeline/{analysis_id}")
def timeline(analysis_id: str, service=Depends(get_service)):
    analysis = service.get_analysis(analysis_id)
    if analysis.status != "succeeded":
        raise AnalysisNotReady(f"Analysis is {analysis.status}")
    session = service.session_factory()
    try:
        from app.db import crud
        rows = [row for row in crud.get_commits(session, analysis_id) if not row.is_merge]
        if not rows:
            return {"weeks": [], "authors": []}
        weeks = sorted({row.authored_at.date() - __import__("datetime").timedelta(days=row.authored_at.weekday()) for row in rows})
        names = {row.author_key: row.author_key for row in rows}
        result = []
        for key in sorted(names):
            result.append({"author_key": key, "display_name": names[key],
                           "meaningful_lines": [sum(row.meaningful_added for row in rows if row.author_key == key and row.authored_at.date() - __import__("datetime").timedelta(days=row.authored_at.weekday()) == week) for week in weeks],
                           "commits": [sum(row.author_key == key and row.authored_at.date() - __import__("datetime").timedelta(days=row.authored_at.weekday()) == week for row in rows) for week in weeks]})
        return {"weeks": [week.isoformat() for week in weeks], "authors": result}
    finally:
        session.close()


@router.get("/ownership/{analysis_id}")
def ownership(analysis_id: str, service=Depends(get_service)):
    analysis = service.get_analysis(analysis_id)
    if analysis.status != "succeeded":
        raise AnalysisNotReady(f"Analysis is {analysis.status}")
    ownership_data = (analysis.report_json or {}).get("ownership_by_dir", {})
    directories = []
    for path, owners in ownership_data.items():
        total = sum(owners.values())
        directories.append({"path": path, "total_lines": total, "owners": [
            {"author_key": key, "display_name": key, "lines": lines, "share": lines / total if total else 0}
            for key, lines in sorted(owners.items(), key=lambda item: (-item[1], item[0]))
        ]})
    return {"directories": sorted(directories, key=lambda item: (-item["total_lines"], item["path"]))}


@router.get("/reports/{analysis_id}/pdf")
def report_pdf(analysis_id: str, service=Depends(get_service)):
    analysis, rows = service.get_scores(analysis_id)
    report = analysis.report_json or {}
    ranking = [
        {
            "rank": row.rank,
            "display_name": row.display_name,
            "author_key": row.author_key,
            "score": row.score,
            "share_of_team": row.share_of_team,
            "commits": row.commits,
            "surviving_lines": row.surviving_lines,
        }
        for row in rows
    ]
    session = service.session_factory()
    try:
        from app.db import crud
        anomalies = crud.get_anomalies(session, analysis_id)
        pdf_report = dict(report)
        pdf_report["anomalies"] = [
            {
                "severity": item.severity,
                "display_name": item.display_name,
                "author_key": item.author_key,
                "kind": item.kind,
                "message": item.message,
            }
            for item in anomalies
        ]
    finally:
        session.close()

    from app.core.pdf_export import report_to_pdf
    pdf = report_to_pdf(pdf_report, ranking)
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="codecourt-{analysis_id}.pdf"'},
    )
