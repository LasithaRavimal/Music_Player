from fastapi import APIRouter, Depends, HTTPException, status, Query
from bson import ObjectId
from datetime import datetime, timedelta
from typing import List, Optional
import logging

from app.db import get_db, SESSIONS_COLLECTION, SONGS_COLLECTION
from app.models import (
    SessionStart,
    SessionStartResponse,
    SessionEnd,
    SessionResponse,
    Message
)
from app.auth import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/sessions", tags=["sessions"])


# =========================
# START SESSION
# =========================
@router.post("/start", response_model=SessionStartResponse, status_code=status.HTTP_201_CREATED)
async def start_session(
    session_data: SessionStart,
    current_user: dict = Depends(get_current_user)
):

    if current_user.get("role") == "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Session tracking disabled for admin"
        )

    db = get_db()

    user_id = ObjectId(current_user["id"])
    started_at = datetime.utcnow()

    active_session = db[SESSIONS_COLLECTION].find_one({
        "user_id": user_id,
        "is_active": True
    })

    if active_session:

        last_event_at = active_session.get("last_event_at", active_session["started_at"])

        if datetime.utcnow() - last_event_at > timedelta(minutes=10):

            db[SESSIONS_COLLECTION].update_one(
                {"_id": active_session["_id"]},
                {"$set": {"is_active": False, "ended_at": datetime.utcnow()}}
            )

        else:

            return SessionStartResponse(
                session_id=str(active_session["_id"]),
                started_at=active_session["started_at"]
            )

    song_id = None

    if session_data.song_id:
        song = db[SONGS_COLLECTION].find_one({"_id": ObjectId(session_data.song_id)})

        if not song:
            raise HTTPException(status_code=404, detail="Song not found")

        song_id = ObjectId(session_data.song_id)

    session_doc = {
        "user_id": user_id,
        "song_id": song_id,
        "started_at": started_at,
        "last_event_at": started_at,
        "is_active": True,
        "events": [],
        "created_at": started_at
    }

    result = db[SESSIONS_COLLECTION].insert_one(session_doc)

    logger.info(f"Session started {result.inserted_id}")

    return SessionStartResponse(
        session_id=str(result.inserted_id),
        started_at=started_at
    )


# =========================
# END SESSION (SAVE DATASET)
# =========================
@router.post("/end", response_model=Message)
async def end_session(
    session_data: SessionEnd,
    current_user: dict = Depends(get_current_user)
):

    db = get_db()

    session_id = ObjectId(session_data.session_id)

    session_doc = db[SESSIONS_COLLECTION].find_one({"_id": session_id})

    if not session_doc:
        raise HTTPException(status_code=404, detail="Session not found")

    if str(session_doc["user_id"]) != current_user["id"]:
        raise HTTPException(status_code=403, detail="Access denied")

    ended_at = datetime.utcnow()

    events = [event.dict() for event in session_data.events]

    aggregated_data = session_data.aggregated_data.dict()

    logger.info("Saving listening behaviour dataset")
    logger.info(aggregated_data)

    db[SESSIONS_COLLECTION].update_one(
        {"_id": session_id},
        {
            "$set": {
                "ended_at": ended_at,
                "is_active": False,
                "events": events,
                "aggregated_data": aggregated_data,
                "updated_at": ended_at
            }
        }
    )

    return Message(message="Session saved successfully")


# =========================
# HEARTBEAT
# =========================
@router.post("/heartbeat", response_model=Message)
async def heartbeat_session(
    session_id: str = Query(...),
    current_user: dict = Depends(get_current_user)
):

    db = get_db()

    result = db[SESSIONS_COLLECTION].update_one(
        {
            "_id": ObjectId(session_id),
            "user_id": ObjectId(current_user["id"]),
            "is_active": True
        },
        {
            "$set": {
                "last_event_at": datetime.utcnow()
            }
        }
    )

    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Session not found")

    return Message(message="Heartbeat updated")


# =========================
# GET USER SESSIONS
# =========================
@router.get("", response_model=List[SessionResponse])
async def list_sessions(current_user: dict = Depends(get_current_user)):

    db = get_db()

    sessions = list(
        db[SESSIONS_COLLECTION].find(
            {"user_id": ObjectId(current_user["id"])}
        ).sort("started_at", -1).limit(50)
    )

    result = []

    for s in sessions:

        result.append(
            SessionResponse(
                id=str(s["_id"]),
                user_id=str(s["user_id"]),
                song_id=str(s["song_id"]) if s.get("song_id") else None,
                started_at=s["started_at"],
                ended_at=s.get("ended_at"),
                events=s.get("events", [])
            )
        )

    return result