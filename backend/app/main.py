"""StudyOS API entry point.  Run:  uvicorn app.main:app --reload"""
import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.routers import auth, dashboard, exams, planner, sessions, subjects, tasks

settings = get_settings()
logger = logging.getLogger("studyos")

app = FastAPI(title="StudyOS API", version="1.0.0",
              description="Academic planning and missed-work recovery for students.")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,  # explicit list, never "*" with cookies
    allow_credentials=True,  # needed so the browser sends the session cookie
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Content-Type"],
)

for module in (auth, subjects, tasks, exams, sessions, planner, dashboard):
    app.include_router(module.router)


@app.get("/api/health", tags=["meta"])
def health():
    return {"status": "ok"}


@app.exception_handler(Exception)
async def unhandled(request: Request, exc: Exception):
    # Log details on the server; tell the client nothing sensitive.
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})
