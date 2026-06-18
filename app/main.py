from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlmodel import Session

from app.config import get_settings
from app.database import create_db_and_tables, engine
from app.routers.forum import router as forum_router
from app.seed import seed_forum_boards

settings = get_settings()

app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.frontend_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    create_db_and_tables()
    Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
    with Session(engine) as session:
        seed_forum_boards(session)


@app.exception_handler(HTTPException)
async def http_exception_handler(_: Request, exc: HTTPException) -> JSONResponse:
    if isinstance(exc.detail, dict) and {"code", "message", "data"} <= set(exc.detail):
        return JSONResponse(status_code=exc.status_code, content=exc.detail)
    return JSONResponse(
        status_code=exc.status_code,
        content={"code": exc.status_code, "message": str(exc.detail), "data": None},
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=400,
        content={"code": 50001, "message": "INVALID_PARAMS", "data": exc.errors()},
    )


@app.get("/healthz")
def root_healthz() -> dict:
    return {"code": 0, "message": "OK", "data": {"status": "ok", "service": "forum"}}


app.include_router(forum_router)
app.mount(settings.public_upload_prefix, StaticFiles(directory=settings.upload_dir), name="uploads")
