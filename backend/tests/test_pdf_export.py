from app.core.pdf_export import report_to_pdf


def test_report_to_pdf_returns_valid_document():
    pdf = report_to_pdf(
        {
            "meta": {
                "repo": "owner/repository",
                "head_sha": "abc123",
                "generated_at": "2026-11-21T00:00:00+00:00",
            },
            "effective_weights": {"work": 0.45, "survival": 0.25},
            "dropped_signals": {"review": "not collected"},
            "anomalies": [],
        },
        [
            {
                "rank": 1,
                "display_name": "Contributor",
                "score": 95.5,
                "share_of_team": 100.0,
                "commits": 10,
                "surviving_lines": 300,
            }
        ],
    )
    assert pdf.startswith(b"%PDF")
    assert len(pdf) > 1000
