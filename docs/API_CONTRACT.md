# CodeCourt — Stage 1 API Contract

Frozen for Stage 1 MVP. Do not add/rename fields without both developers agreeing.

## Auth

`GET /auth/github/login`
Redirects the browser to GitHub OAuth. No request/response body — frontend just links/redirects here.

After GitHub auth, the backend redirects to `FRONTEND_URL/repositories` and sets an
httpOnly `session` cookie. The frontend never sees or stores this token directly.

Frontend must send `credentials: "include"` on every fetch/axios call so the cookie
is attached. A `401` response means "not logged in" → redirect to `/login`.

## GET /api/repositories

```json
{
  "repositories": [
    { "id": 12345, "name": "CodeCourt", "owner": "rahul", "url": "https://github.com/rahul/CodeCourt" }
  ]
}
```

## GET /api/repositories/{repository_id}/analysis

```json
{
  "repository": { "id": 12345, "name": "CodeCourt", "owner": "rahul", "url": "https://..." },
  "summary": {
    "total_commits": 127,
    "total_contributors": 4,
    "total_additions": 5400,
    "total_deletions": 1800
  },
  "contributors": [
    { "github_id": 101, "username": "rahul", "commits": 42, "additions": 1200, "deletions": 450, "files_changed": 38 }
  ],
  "activity": [
    { "date": "2026-09-01", "commits": 5 }
  ]
}
```

## Rules

- Frontend never calls the GitHub API directly — only these two endpoints + the login redirect.
- Field names above are final for Stage 1. If something's missing, ask before inventing a field.
- Auth is a signed session cookie (JWT inside an httpOnly cookie), not a token the frontend stores.
