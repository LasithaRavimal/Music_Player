# app/main.py

import logging
import warnings

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import settings, API_V1_PREFIX
from app.db import connect_db, close_db

from app.routes import (
    auth_routes,
    music_admin_routes,
    song_routes,
    session_routes,
    playlist_routes,
)

# -------------------------
# Logging
# -------------------------
warnings.filterwarnings("ignore", message=".*bcrypt.*")
logging.getLogger("passlib").setLevel(logging.ERROR)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# -------------------------
# FastAPI App
# -------------------------
app = FastAPI(
    title="M_Track API",
    description="Music Listening Behaviour Data Collection Platform",
    version="1.0.0",
)

# -------------------------
# CORS Middleware
# -------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------
# Static Media
# -------------------------
settings.SONGS_DIR.mkdir(parents=True, exist_ok=True)
app.mount(
    "/media/songs",
    StaticFiles(directory=str(settings.SONGS_DIR)),
    name="songs"
)

settings.THUMBNAILS_DIR.mkdir(parents=True, exist_ok=True)
app.mount(
    "/media/thumbnails",
    StaticFiles(directory=str(settings.THUMBNAILS_DIR)),
    name="thumbnails"
)

# -------------------------
# Routers
# -------------------------
app.include_router(auth_routes.router, prefix=API_V1_PREFIX)
app.include_router(song_routes.router, prefix=API_V1_PREFIX)
app.include_router(session_routes.router, prefix=API_V1_PREFIX)
app.include_router(playlist_routes.router, prefix=API_V1_PREFIX)
app.include_router(music_admin_routes.router, prefix=API_V1_PREFIX)

# -------------------------
# Startup Event
# -------------------------
@app.on_event("startup")
async def startup_event():

    logger.info("Starting M_Track API...")

    try:
        connect_db()
        logger.info("Connected to MongoDB")

        if settings.EMAIL_ENABLED:
            logger.info("Email configuration loaded")

    except Exception as e:
        logger.error("Startup error: %s", e)
        raise


# -------------------------
# Shutdown Event
# -------------------------
@app.on_event("shutdown")
async def shutdown_event():

    logger.info("Shutting down M_Track API")

    try:
        close_db()
        logger.info("MongoDB connection closed")
    except Exception as e:
        logger.warning("Shutdown warning: %s", e)


# -------------------------
# Root Endpoint
# -------------------------
@app.get("/")
async def root():
    return {
        "message": "M_Track Listening Behaviour API",
        "version": "1.0.0",
        "docs": "/docs"
    }


# -------------------------
# Health Check
# -------------------------
@app.get("/health")
async def health_check():
    return {"status": "healthy"}


# -------------------------
# Run Server
# -------------------------
if __name__ == "__main__":

    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )