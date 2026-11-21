# CodeCourt

CodeCourt analyzes public GitHub repositories and scores contributor contributions with
transparent work, survival, ownership, review, issue, and consistency signals.

The backend provides repository ingestion, Git analysis, GitHub activity collection,
scoring, persistence, background jobs, REST endpoints, and PDF/JSON report export.
The frontend can be developed separately against the API.

## Backend setup

```powershell
cd backend
py -3.11 -m venv .venv
.\\.venv\\Scripts\\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000/docs.

## Validation

```powershell
cd backend
python -m pytest -q
```
