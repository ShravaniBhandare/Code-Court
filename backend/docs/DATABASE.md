# Database

CodeCourt uses SQLAlchemy 2.0 with SQLite by default and PostgreSQL in
production. The schema contains repositories, analyses, contributor scores,
anomaly rows, and analyzed commit rows. Scores, anomalies, and commits belong
to an analysis and are deleted with it. Cache lookup is indexed by repository,
HEAD SHA, normalized parameters, pipeline version, and status.

There is deliberately no users table and no raw pull-request/issues tables:
this phase analyzes public repositories without accounts, and the aggregated
GitHub activity remains in the report JSON. Raw GitHub data is re-queryable.

Set PostgreSQL with:

```text
DATABASE_URL=postgresql+psycopg2://user:password@host:5432/dbname
```

For local PostgreSQL 16 development:

```powershell
docker run --name codecourt-postgres -e POSTGRES_PASSWORD=codecourt -e POSTGRES_DB=codecourt -p 5432:5432 -d postgres:16
```
