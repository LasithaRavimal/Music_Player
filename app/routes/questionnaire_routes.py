from fastapi import APIRouter, Depends, HTTPException
from bson import ObjectId
from datetime import datetime

from app.db import get_db, QUESTIONNAIRE_COLLECTION, USERS_COLLECTION
from app.models import QuestionnaireSubmit, QuestionnaireResponse
from app.auth import get_current_user
from app.utils.email_service import send_questionnaire_alert


router = APIRouter(prefix="/questionnaire", tags=["questionnaire"])


# ----------------------------------------
# SUBMIT QUESTIONNAIRE
# ----------------------------------------

@router.post("/submit", response_model=QuestionnaireResponse)
async def submit_questionnaire(
    data: QuestionnaireSubmit,
    current_user: dict = Depends(get_current_user)
):

    db = get_db()
    user_id = ObjectId(current_user["id"])

    phq9_score = sum(data.phq9_answers)
    dass21_stress_score = sum(data.dass21_answers)

    # Calculate severity levels for the database
    dep_level = "High" if phq9_score >= 15 else "Moderate" if phq9_score >= 8 else "Low"
    stress_level = "High" if dass21_stress_score >= 15 else "Moderate" if dass21_stress_score >= 8 else "Low"

    doc = {
        "user_id": user_id,
        "phq9_score": phq9_score,
        "dass21_stress_score": dass21_stress_score,
        "depression_level": dep_level,
        "stress_level": stress_level,
        "created_at": datetime.utcnow()
    }

    db[QUESTIONNAIRE_COLLECTION].insert_one(doc)

    # --------------------------------
    # EMAIL ALERT IF HIGH SCORE
    # --------------------------------

    if phq9_score >= 15 or dass21_stress_score >= 13:
        await send_questionnaire_alert(
            current_user["email"],
            dass21_stress_score,
            phq9_score
        )

    return QuestionnaireResponse(
        phq9_score=phq9_score,
        dass21_stress_score=dass21_stress_score
    )


# ----------------------------------------
# GET LATEST QUESTIONNAIRE
# ----------------------------------------

@router.get("/latest")
async def get_latest_questionnaire(current_user: dict = Depends(get_current_user)):
    db = get_db()
    user_id = ObjectId(current_user["id"])

    # Find the most recent questionnaire submitted by this specific user
    latest = db[QUESTIONNAIRE_COLLECTION].find_one(
        {"user_id": user_id},
        sort=[("created_at", -1)]
    )

    if not latest:
        return None

    # Convert MongoDB ObjectIds to strings so they can be sent as JSON to the frontend
    latest["_id"] = str(latest["_id"])
    latest["user_id"] = str(latest["user_id"])

    return latest



@router.get("/check-today")
async def check_today_assessment(current_user: dict = Depends(get_current_user)):
    """Check if the logged-in user has completed the assessment today"""
    db = get_db()
    
   
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    
    
    count = db["questionnaire_results"].count_documents({
        "user_id": ObjectId(current_user["id"]),
        "created_at": {"$gte": today_start}
    })
    
    return {"has_done_today": count > 0}