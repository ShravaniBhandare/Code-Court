from fastapi import FastAPI

from app.routes.analysis import router as analysis_router
from app.routes.auth import router as auth_router
from app.routes.repositories import router as repositories_router


app = FastAPI(
    title="Code-Court Backend",
    version="0.1.0",
)

app.include_router(auth_router)
app.include_router(repositories_router)
app.include_router(analysis_router)


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}