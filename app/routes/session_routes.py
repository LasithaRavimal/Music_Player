from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from bson import ObjectId
from datetime import datetime, timedelta
from typing import List, Optional

# IMPORT USERS_COLLECTION and the email service
from app.db import get_db, SESSIONS_COLLECTION, SONGS_COLLECTION, USERS_COLLECTION
from app.utils.email_service import send_questionnaire_alert

from app.models import (
    SessionStart, SessionStartResponse,
    SessionEnd, SessionEndResponse,
    SessionResponse, Message
)
from app.auth import get_current_user
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/sessions", tags=["sessions"])


# ----------------------------
# START SESSION
# ----------------------------
@router.post("/start", response_model=SessionStartResponse, status_code=status.HTTP_201_CREATED)
async def start_session(
    session_data: SessionStart,
    current_user: dict = Depends(get_current_user)
):
    """Start a new listening session"""

    if current_user.get("role") == "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Session tracking disabled for admin"
        )

    db = get_db()
    user_id = ObjectId(current_user["id"])
    started_at = datetime.utcnow()

    # Check existing active session
    active_session = db[SESSIONS_COLLECTION].find_one({
        "user_id": user_id,
        "is_active": True
    })

    if active_session:
        last_event_at = active_session.get("last_event_at", active_session["started_at"])
        if started_at - last_event_at > timedelta(minutes=10):
            db[SESSIONS_COLLECTION].update_one(
                {"_id": active_session["_id"]},
                {"$set": {"is_active": False, "ended_at": started_at}}
            )
        else:
            return SessionStartResponse(
                session_id=str(active_session["_id"]),
                started_at=active_session["started_at"]
            )

    # Validate song
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
        "created_at": started_at,
    }

    result = db[SESSIONS_COLLECTION].insert_one(session_doc)

    return SessionStartResponse(
        session_id=str(result.inserted_id),
        started_at=started_at
    )


# ----------------------------
# END SESSION (TRIGGERS EMAIL IF RESULT IS HIGH)
# ----------------------------
@router.post("/end", response_model=SessionEndResponse)
async def end_session(
    session_data: SessionEnd,
    background_tasks: BackgroundTasks, 
    current_user: dict = Depends(get_current_user)
):
    """End listening session, save behavior data, and send email if risk is high"""

    db = get_db()
    session_id = ObjectId(session_data.session_id)
    session_doc = db[SESSIONS_COLLECTION].find_one({"_id": session_id})

    if not session_doc:
        raise HTTPException(status_code=404, detail="Session not found")

    ended_at = datetime.utcnow()
    events = [event.dict() for event in session_data.events]
    aggregated_data = session_data.aggregated_data.dict()

    # 1. Update session document
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

    # 2. Check questionnaire scores and trigger email
    try:
        print("\n=== EMAIL TRIGGER CHECK ===")
        latest_q = db["questionnaire_results"].find_one(
            {"user_id": ObjectId(current_user["id"])},
            sort=[("created_at", -1)]
        )

        if latest_q:
            phq9_score = latest_q.get("phq9_score", 0)
            stress_score = latest_q.get("dass21_stress_score", 0)
            
            print(f"Found Questionnaire -> Depression Score: {phq9_score}, Stress Score: {stress_score}")

            if phq9_score >= 15 or stress_score >= 13:
                # Fetch user email
                user_doc = db[USERS_COLLECTION].find_one({"_id": ObjectId(current_user["id"])})
                user_email = user_doc.get("email") if user_doc else current_user.get("email")

                if user_email:
                    print(f"🚨 HIGH RISK DETECTED! Queueing email to: {user_email}")
                    background_tasks.add_task(
                        send_questionnaire_alert,
                        user_email,
                        stress_score,
                        phq9_score
                    )
                else:
                    print("❌ Error: Could not find user's email address in database.")
            else:
                print("✅ Scores are normal/low. No email will be sent.")
        else:
            print("❌ Error: No questionnaire found for this user!")
            
        print("===========================\n")

    except Exception as e:
        print(f"❌ CRITICAL EMAIL ERROR: {e}")

    return SessionEndResponse(
        session_id=session_data.session_id
    )

# ----------------------------
# ACTIVE SESSION
# ----------------------------
@router.get("/active", response_model=Optional[SessionStartResponse])
async def get_active_session(
    current_user: dict = Depends(get_current_user)
):
    db = get_db()

    active_session = db[SESSIONS_COLLECTION].find_one({
        "user_id": ObjectId(current_user["id"]),
        "is_active": True
    })

    if not active_session:
        return None

    return SessionStartResponse(
        session_id=str(active_session["_id"]),
        started_at=active_session["started_at"]
    )


# ----------------------------
# HEARTBEAT
# ----------------------------
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
        raise HTTPException(status_code=404, detail="Active session not found")

    return Message(message="Heartbeat updated")


# ----------------------------
# LIST SESSIONS
# ----------------------------
@router.get("", response_model=List[SessionResponse])
async def list_sessions(
    current_user: dict = Depends(get_current_user)
):
    db = get_db()

    sessions = list(db[SESSIONS_COLLECTION].find(
        {"user_id": ObjectId(current_user["id"])}
    ).sort("started_at", -1).limit(50))

    result = []

    for s in sessions:
        s["id"] = str(s["_id"])
        s["user_id"] = str(s["user_id"])

        if s.get("song_id"):
            s["song_id"] = str(s["song_id"])

        result.append(SessionResponse(**s))

    return result


# ----------------------------
# GET SESSION
# ----------------------------
@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(
    session_id: str,
    current_user: dict = Depends(get_current_user)
):
    db = get_db()

    session = db[SESSIONS_COLLECTION].find_one({"_id": ObjectId(session_id)})

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if str(session["user_id"]) != current_user["id"]:
        raise HTTPException(status_code=403, detail="Access denied")

    session["id"] = str(session["_id"])
    session["user_id"] = str(session["user_id"])

    if session.get("song_id"):
        session["song_id"] = str(session["song_id"])

    return SessionResponse(**session)