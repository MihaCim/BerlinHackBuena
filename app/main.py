from pathlib import Path

from fastapi import FastAPI, HTTPException, Query

from app.ingestion import IngestionService


ROOT_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT_DIR / "data"
DB_PATH = ROOT_DIR / ".local" / "ingestion.sqlite3"

app = FastAPI(title="BerlinHackBuena Ingestion API")
service = IngestionService(data_dir=DATA_DIR, db_path=DB_PATH)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/ingest/base")
def ingest_base(reprocess: bool = Query(default=False)) -> dict[str, object]:
    if not DATA_DIR.exists():
        raise HTTPException(status_code=404, detail=f"Data directory not found: {DATA_DIR}")
    return service.ingest_base(reprocess=reprocess)


@app.post("/ingest/incremental/{day}")
def ingest_incremental_day(day: str, reprocess: bool = Query(default=False)) -> dict[str, object]:
    try:
        return service.ingest_incremental_day(day=day, reprocess=reprocess)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/ingest/incremental")
def ingest_all_incremental(reprocess: bool = Query(default=False)) -> dict[str, object]:
    return service.ingest_all_incremental(reprocess=reprocess)


@app.get("/ingest/status")
def ingest_status() -> dict[str, object]:
    return service.status()
