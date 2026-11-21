# CodeCourt

CodeCourt analyzes a public GitHub repository and fairly scores each contributor's contribution.

## Setup

From the project root, create and activate a virtual environment:

```powershell
python -m venv backend\.venv
backend\.venv\Scripts\Activate.ps1
```

On macOS/Linux:

```bash
python3 -m venv backend/.venv
source backend/.venv/bin/activate
```

Install requirements:

```bash
cd backend
pip install -r requirements.txt
```

Run the server from `backend/`:

```bash
uvicorn app.main:app --reload
```

Run tests from `backend/`:

```bash
pytest
```

Open the API documentation at http://127.0.0.1:8000/docs.
