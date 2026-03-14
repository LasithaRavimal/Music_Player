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


    doc = {
        "user_id": user_id,
        "phq9_score": phq9_score,
        "dass21_stress_score": dass21_stress_score,
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