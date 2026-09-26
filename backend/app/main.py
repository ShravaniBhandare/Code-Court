from fastapi import FastAPI


app = FastAPI(
    title="CodeCourt Backend",
    version="0.1.0",
)


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}