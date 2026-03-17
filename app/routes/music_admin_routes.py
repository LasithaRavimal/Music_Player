from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List
from bson import ObjectId
from datetime import datetime, timedelta
from collections import defaultdict

from app.db import get_db, USERS_COLLECTION, SONGS_COLLECTION, SESSIONS_COLLECTION, EMAIL_CONFIG_COLLECTION
from app.auth import require_admin
from app.models import Message, UserResponse, EmailConfigCreate, EmailConfigUpdate, EmailConfigResponse
from app.config import refresh_email_config

router = APIRouter(prefix="/admin", tags=["admin"])


# -------------------------
# LIST USERS
# -------------------------
@router.get("/users", response_model=List[UserResponse])
async def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    admin_user: dict = Depends(require_admin)
):
    """List all users (admin only)"""
    db = get_db()

    users = list(
        db[USERS_COLLECTION]
        .find()
        .skip(skip)
        .limit(limit)
        .sort("created_at", -1)
    )

    return [
        UserResponse(
            id=str(user["_id"]),
            email=user["email"],
            role=user.get("role", "user"),
            profile_picture=user.get("profile_picture"),
        )
        for user in users
    ]


# -------------------------
# USER DETAILS
# -------------------------
@router.get("/users/{user_id}")
async def get_user_details(
    user_id: str,
    admin_user: dict = Depends(require_admin)
):
    """Get user details with listening metrics"""
    db = get_db()
    user_oid = ObjectId(user_id)

    user = db[USERS_COLLECTION].find_one({"_id": user_oid})

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    sessions = list(db[SESSIONS_COLLECTION].find({"user_id": user_oid}))

    total_sessions = len(sessions)
    total_listening_time = 0

    for s in sessions:
        started_at = s.get("started_at")
        ended_at = s.get("ended_at")

        if started_at and ended_at:
            duration = (ended_at - started_at).total_seconds() / 60
            total_listening_time += duration

    return {
        "user": {
            "id": str(user["_id"]),
            "email": user["email"],
            "role": user.get("role", "user"),
            "profile_picture": user.get("profile_picture"),
            "created_at": user.get("created_at").isoformat()
        },
        "metrics": {
            "total_sessions": total_sessions,
            "total_listening_time_minutes": total_listening_time,
            "average_session_duration": total_listening_time / total_sessions if total_sessions else 0
        }
    }


# -------------------------
# ADMIN ANALYTICS
# -------------------------
@router.get("/analytics")
async def get_analytics(
    admin_user: dict = Depends(require_admin)
):
    """Get system analytics"""
    db = get_db()

    total_users = db[USERS_COLLECTION].count_documents({})
    total_songs = db[SONGS_COLLECTION].count_documents({})
    total_sessions = db[SESSIONS_COLLECTION].count_documents({})

    # new users
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)

    new_users = db[USERS_COLLECTION].count_documents({
        "created_at": {"$gte": thirty_days_ago}
    })

    # active users
    seven_days_ago = datetime.utcnow() - timedelta(days=7)

    active_users = len(db[SESSIONS_COLLECTION].distinct(
        "user_id",
        {"created_at": {"$gte": seven_days_ago}}
    ))

    # category distribution
    songs = list(db[SONGS_COLLECTION].find({}, {"category": 1}))

    category_counts = defaultdict(int)

    for song in songs:
        category_counts[song.get("category", "Unknown")] += 1

    return {
        "overview": {
            "total_users": total_users,
            "total_songs": total_songs,
            "total_sessions": total_sessions,
            "new_users_30d": new_users,
            "active_users_7d": active_users,
        },
        "song_category_distribution": dict(category_counts),
    }


# -------------------------
# EMAIL CONFIG GET
# -------------------------
@router.get("/email-config", response_model=EmailConfigResponse)
async def get_email_config(
    admin_user: dict = Depends(require_admin)
):
    """Get email configuration"""
    db = get_db()

    config = db[EMAIL_CONFIG_COLLECTION].find_one(sort=[("updated_at", -1)])

    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Email configuration not found"
        )

    return EmailConfigResponse(
        smtp_host=config["smtp_host"],
        smtp_port=config["smtp_port"],
        smtp_user=config["smtp_user"],
        smtp_from=config.get("smtp_from", config["smtp_user"]),
        enabled=config.get("enabled", True),
        updated_at=config.get("updated_at", datetime.utcnow())
    )


# -------------------------
# CREATE EMAIL CONFIG
# -------------------------
@router.post("/email-config", response_model=EmailConfigResponse)
async def create_email_config(
    config_data: EmailConfigCreate,
    admin_user: dict = Depends(require_admin)
):
    db = get_db()
    now = datetime.utcnow()

    config_doc = {
        "smtp_host": config_data.smtp_host,
        "smtp_port": config_data.smtp_port,
        "smtp_user": config_data.smtp_user,
        "smtp_password": config_data.smtp_password,
        "smtp_from": config_data.smtp_from or config_data.smtp_user,
        "enabled": config_data.enabled,
        "created_at": now,
        "updated_at": now,
    }

    result = db[EMAIL_CONFIG_COLLECTION].insert_one(config_doc)

    refresh_email_config()

    return EmailConfigResponse(
        smtp_host=config_doc["smtp_host"],
        smtp_port=config_doc["smtp_port"],
        smtp_user=config_doc["smtp_user"],
        smtp_from=config_doc["smtp_from"],
        enabled=config_doc["enabled"],
        updated_at=config_doc["updated_at"]
    )


# -------------------------
# UPDATE EMAIL CONFIG
# -------------------------
@router.put("/email-config", response_model=EmailConfigResponse)
async def update_email_config(
    config_data: EmailConfigUpdate,
    admin_user: dict = Depends(require_admin)
):
    db = get_db()

    existing = db[EMAIL_CONFIG_COLLECTION].find_one()

    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Email configuration not found"
        )

    update_doc = {"updated_at": datetime.utcnow()}

    for key, value in config_data.dict(exclude_none=True).items():
        update_doc[key] = value

    db[EMAIL_CONFIG_COLLECTION].update_one(
        {"_id": existing["_id"]},
        {"$set": update_doc}
    )

    refresh_email_config()

    updated = db[EMAIL_CONFIG_COLLECTION].find_one({"_id": existing["_id"]})

    return EmailConfigResponse(
        smtp_host=updated["smtp_host"],
        smtp_port=updated["smtp_port"],
        smtp_user=updated["smtp_user"],
        smtp_from=updated.get("smtp_from", updated["smtp_user"]),
        enabled=updated["enabled"],
        updated_at=updated["updated_at"]
    )


# -------------------------
# DELETE EMAIL CONFIG
# -------------------------
@router.delete("/email-config", response_model=Message)
async def delete_email_config(
    admin_user: dict = Depends(require_admin)
):
    db = get_db()

    result = db[EMAIL_CONFIG_COLLECTION].delete_many({})

    if result.deleted_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Email configuration not found"
        )

    refresh_email_config()

    return Message(message="Email configuration deleted")


# -------------------------
# ADMIN: RESEARCH DATA
# -------------------------
@router.get("/research-data")
async def get_all_research_data(admin_user: dict = Depends(require_admin)):
    """Fetch all completed sessions mapped to their exact questionnaire result"""
    db = get_db()
    
    # 1. Get all completed sessions
    sessions = list(db[SESSIONS_COLLECTION].find({"is_active": False}).sort("ended_at", -1))
    
    # 2. Get users map
    users = list(db[USERS_COLLECTION].find({}, {"email": 1}))
    user_map = {str(u["_id"]): u.get("email", "Unknown User") for u in users}
    
    # 3. Get ALL Questionnaire Results (Sorted by newest first)
    questionnaires = list(db["questionnaire_results"].find({}).sort("created_at", -1))
    
    # 4. Combine everything logically
    research_data = []
    for s in sessions:
        uid = str(s.get("user_id"))
        session_end_time = s.get("ended_at")
        
         
        matched_q = None
        for q in questionnaires:
            if str(q.get("user_id")) == uid:
                q_time = q.get("created_at")
                 
                if q_time and session_end_time and q_time <= session_end_time:
                    matched_q = q
                    break
        
        
        if not matched_q:
            for q in questionnaires:
                if str(q.get("user_id")) == uid:
                    matched_q = q
                    break

        
        screening_data = {
            "depression_level": matched_q.get("depression_level", "N/A") if matched_q else "N/A",
            "stress_level": matched_q.get("stress_level", "N/A") if matched_q else "N/A"
        }

        if "aggregated_data" in s:
            research_data.append({
                "session_id": str(s["_id"]),
                "email": user_map.get(uid, "Unknown User"),
                "date": session_end_time,
                "behavior": s.get("aggregated_data", {}),
                "screening": screening_data 
            })
            
    return research_data