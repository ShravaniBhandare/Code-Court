# Code-Court

Code-Court analyzes commit activity and contributor contributions in GitHub
repositories. GitHub OAuth and GitHub API requests are handled by the backend;
the React frontend uses the backend API and a signed, 24-hour JWT session cookie
that is HTTP-only.

## Architecture

```text
React + Vite frontend
        | API requests with session cookie
        v
FastAPI backend ---- GitHub OAuth/API
        |
        v
   PostgreSQL
```

The Stage 1 response shapes and authentication contract are documented in
[docs/API_CONTRACT.md](docs/API_CONTRACT.md).

## Local setup

Requirements: Python 3.11+, Node.js, npm, PostgreSQL, and a GitHub OAuth app.

1. Create a PostgreSQL database, then copy `backend/.env.example` to
   `backend/.env`. Set `DATABASE_URL`, `GITHUB_CLIENT_ID`,
   `GITHUB_CLIENT_SECRET`, `GITHUB_REDIRECT_URI`, `FRONTEND_URL`, and a
   long random `SESSION_SECRET`. Register the same callback URL with the
   GitHub OAuth app.
2. From `backend/`, create and activate a virtual environment, install
   `requirements.txt`, and start the API:

   ```powershell
   cd backend
   py -3.11 -m venv venv
   .\venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   uvicorn app.main:app --reload
   ```

   The backend creates its database tables at startup.
3. Copy `frontend/.env.example` to `frontend/.env`. From `frontend/`, install
   dependencies and start Vite:

   ```powershell
   cd frontend
   npm install
   npm run dev
   ```

   Set `VITE_API_BASE_URL` to the backend origin used by the browser.

## Validation

Run the backend tests from `backend/` with `python -m pytest`. Run
`npm run lint` and `npm run build` from `frontend/`.

Do not commit `.env` files, virtual environments, or `node_modules`. Work on a
feature branch and open a pull request to merge changes into `main`.
