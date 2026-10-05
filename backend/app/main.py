from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config.settings import get_settings
from app.database.init_db import create_tables
from app.routes.analysis import router as analysis_router
from app.routes.auth import router as auth_router
from app.routes.repositories import router as repositories_router


settings = get_settings()

app = FastAPI(
    title="Code-Court Backend",
    version="0.1.0",
)

create_tables()
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(repositories_router)
app.include_router(analysis_router)


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}