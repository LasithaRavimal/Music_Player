import logging
import warnings

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.config import (
    settings,
    API_V1_PREFIX,
    load_email_config_from_db,
)

from app.db import connect_db, close_db
from app.music.session_cleanup import cleanup_inactive_sessions

from app.routes import (
    auth_routes,
    music_admin_routes,
    song_routes,
    session_routes,
    playlist_routes,
)

# --------------------------------------------------
# Logging Configuration
# --------------------------------------------------

warnings.filterwarnings("ignore", message=".*bcrypt.*")
logging.getLogger("passlib").setLevel(logging.ERROR)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --------------------------------------------------
# FastAPI App
# --------------------------------------------------

app = FastAPI(
    title="M_Track API",
    description="Music Listening Behaviour Research Platform",
    version="2.0.0",
)

# --------------------------------------------------
# Scheduler
# --------------------------------------------------

scheduler = AsyncIOScheduler()

# --------------------------------------------------
# CORS Middleware
# --------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        "https://mp-frontend-beta.vercel.app"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --------------------------------------------------
# Routers
# --------------------------------------------------

app.include_router(auth_routes.router, prefix=API_V1_PREFIX)
app.include_router(song_routes.router, prefix=API_V1_PREFIX)
app.include_router(session_routes.router, prefix=API_V1_PREFIX)
app.include_router(playlist_routes.router, prefix=API_V1_PREFIX)
app.include_router(music_admin_routes.router, prefix=API_V1_PREFIX)

# --------------------------------------------------
# Startup Event
# --------------------------------------------------

@app.on_event("startup")
async def startup_event():

    logger.info("Starting M_Track API...")

    try:

        # Connect MongoDB
        connect_db()
        logger.info("MongoDB connected")

        # Load email configuration
        load_email_config_from_db()

        if settings.EMAIL_ENABLED:
            logger.info("Email service enabled")
        else:
            logger.warning("Email service disabled")

    except Exception as e:
        logger.error("Startup failed: %s", e)
        raise

    # Scheduler Job for cleaning inactive sessions
    scheduler.add_job(
        cleanup_inactive_sessions,
        trigger=IntervalTrigger(minutes=5),
        id="session_cleanup",
        replace_existing=True,
    )

    scheduler.start()

    logger.info("Session cleanup scheduler started")


# --------------------------------------------------
# Shutdown Event
# --------------------------------------------------

@app.on_event("shutdown")
async def shutdown_event():

    logger.info("Shutting down M_Track API")

    try:
        if scheduler.running:
            scheduler.shutdown(wait=False)
    except Exception as e:
        logger.warning("Scheduler shutdown issue: %s", e)

    close_db()


# --------------------------------------------------
# Root Endpoint
# --------------------------------------------------

@app.get("/")
async def root():

    return {
        "message": "M_Track API",
        "version": "2.0.0",
        "system": "Music Behaviour + Questionnaire Research Platform",
    }


# --------------------------------------------------
# Health Check
# --------------------------------------------------

@app.get("/health")
async def health_check():

    return {
        "status": "healthy"
    }


# --------------------------------------------------
# Local Development Run
# --------------------------------------------------

if __name__ == "__main__":

    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )