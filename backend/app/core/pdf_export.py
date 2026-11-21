"""PDF export for completed contribution reports."""

from io import BytesIO
from pathlib import Path
from typing import Any

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle


def report_to_pdf(report: dict[str, Any], ranking: list[dict[str, Any]] | None = None) -> bytes:
    """Render a score report dictionary as a PDF document."""
    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        title="CodeCourt Contribution Report",
        author="CodeCourt",
    )
    styles = getSampleStyleSheet()
    title_style = styles["Title"]
    title_style.alignment = TA_CENTER
    elements = [
        Paragraph("CodeCourt Contribution Report", title_style),
        Spacer(1, 12),
    ]

    meta = report.get("meta", {})
    if meta:
        elements.append(Paragraph(
            f"<b>Repository:</b> {meta.get('repo', 'N/A')}<br/>"
            f"<b>Head SHA:</b> {meta.get('head_sha', 'N/A')}<br/>"
            f"<b>Generated:</b> {meta.get('generated_at', 'N/A')}",
            styles["Normal"],
        ))
        elements.append(Spacer(1, 12))

    elements.append(Paragraph("Contributor Ranking", styles["Heading2"]))
    ranking = ranking or report.get("ranking") or report.get("authors", [])
    if ranking:
        table_data = [["Rank", "Contributor", "Score", "Team Share", "Commits", "Surviving Lines"]]
        for author in ranking:
            table_data.append([
                str(author.get("rank", "")),
                str(author.get("display_name") or author.get("author_key") or ""),
                f"{float(author.get('score', 0)):,.2f}",
                f"{float(author.get('share_of_team', 0)):,.2f}%",
                str(author.get("commits", 0)),
                str(author.get("surviving_lines", 0)),
            ])
        table = Table(table_data, repeatRows=1, hAlign="LEFT")
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f2937")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f3f4f6")]),
            ("ALIGN", (0, 0), (0, -1), "CENTER"),
            ("ALIGN", (2, 1), (-1, -1), "RIGHT"),
        ]))
        elements.append(table)
    else:
        elements.append(Paragraph("No contributor rankings available.", styles["Normal"]))

    elements.append(Spacer(1, 12))
    elements.append(Paragraph("Available and Effective Signals", styles["Heading2"]))
    effective = report.get("effective_weights", {})
    if effective:
        signal_data = [["Signal", "Effective Weight"]]
        signal_data.extend([
            [str(name), f"{float(weight) * 100:.2f}%"]
            for name, weight in effective.items()
        ])
        elements.append(Table(signal_data, hAlign="LEFT", colWidths=[180, 120]))
    else:
        elements.append(Paragraph("No signal breakdown available.", styles["Normal"]))

    dropped = report.get("dropped_signals", {})
    if dropped:
        elements.append(Spacer(1, 12))
        elements.append(Paragraph("Unavailable Signals", styles["Heading2"]))
        for name, reason in dropped.items():
            elements.append(Paragraph(f"<b>{name}:</b> {reason}", styles["Normal"]))

    anomalies = report.get("anomalies", [])
    if anomalies:
        elements.append(Spacer(1, 12))
        elements.append(Paragraph("Anomalies", styles["Heading2"]))
        anomaly_data = [["Severity", "Contributor", "Type", "Message"]]
        for anomaly in anomalies:
            anomaly_data.append([
                str(anomaly.get("severity", "")),
                str(anomaly.get("display_name") or anomaly.get("author_key") or ""),
                str(anomaly.get("kind", "")),
                str(anomaly.get("message", "")),
            ])
        elements.append(Table(anomaly_data, repeatRows=1, hAlign="LEFT", colWidths=[55, 100, 100, 230]))

    document.build(elements)
    return buffer.getvalue()


def write_report_pdf(report: dict[str, Any], path: Path, ranking: list[dict[str, Any]] | None = None) -> None:
    """Write a PDF report to disk."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(report_to_pdf(report, ranking))
