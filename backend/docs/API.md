# HTTP API

Start the service with `uvicorn app.main:app --reload`. All errors use:

```json
{"error":{"code":"analysis_not_found","message":"Analysis not found"}}
```

`POST /analyze` accepts a GitHub URL, optional commit/date/weight parameters,
and returns an analysis id immediately. Repeated requests use a succeeded
analysis from the last 24 hours when repository HEAD, normalized parameters,
and `PIPELINE_VERSION` match. `force=true` skips the completed cache but still
deduplicates queued work.

Endpoints:

- `POST /analyze`
- `GET /analyses/{id}`
- `GET /analyses?limit=20&offset=0`
- `GET /repos/{owner}/{repo}/latest`
- `GET /scores/{id}`
- `GET /anomalies/{id}`
- `GET /timeline/{id}`
- `GET /ownership/{id}`
- `GET /reports/{id}/pdf`
- `GET /health`

Bash:

```bash
id=$(curl -s -X POST http://localhost:8000/analyze \
  -H 'content-type: application/json' \
  -d '{"repo_url":"https://github.com/octocat/Hello-World","max_commits":300}' | jq -r .analysis_id)
curl http://localhost:8000/analyses/$id
curl http://localhost:8000/scores/$id
curl http://localhost:8000/anomalies/$id
curl http://localhost:8000/timeline/$id
curl http://localhost:8000/ownership/$id
curl -o codecourt-$id.pdf http://localhost:8000/reports/$id/pdf
```

PowerShell:

```powershell
$body = @{ repo_url = "https://github.com/octocat/Hello-World"; max_commits = 300 } | ConvertTo-Json
$ticket = Invoke-RestMethod http://localhost:8000/analyze -Method Post -ContentType "application/json" -Body $body
Invoke-RestMethod "http://localhost:8000/analyses/$($ticket.analysis_id)"
Invoke-RestMethod "http://localhost:8000/scores/$($ticket.analysis_id)"
Invoke-RestMethod "http://localhost:8000/anomalies/$($ticket.analysis_id)"
Invoke-RestMethod "http://localhost:8000/timeline/$($ticket.analysis_id)"
Invoke-RestMethod "http://localhost:8000/ownership/$($ticket.analysis_id)"
Invoke-WebRequest "http://localhost:8000/reports/$($ticket.analysis_id)/pdf" -OutFile "codecourt-$($ticket.analysis_id).pdf"
```
