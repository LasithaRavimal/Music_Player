from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from bson import ObjectId
from datetime import datetime
from google.oauth2 import id_token
from google.auth.transport import requests
import asyncio

from app.db import get_db, USERS_COLLECTION
from app.models import UserCreate, UserLogin, UserResponse, Token, Message, GoogleAuthRequest
from app.utils.security import verify_password, get_password_hash, create_access_token
from app.utils.email_service import send_welcome_email
from app.auth import get_current_user
from app.config import settings

router = APIRouter(prefix="/auth", tags=["auth"])


# =========================
# REGISTER
# =========================
@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserCreate, background_tasks: BackgroundTasks):
    """Register new user and send welcome email"""
    
    db = get_db()

    existing_user = db[USERS_COLLECTION].find_one({"email": user_data.email.lower()})
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    user_doc = {
        "email": user_data.email.lower(),
        "password_hash": get_password_hash(user_data.password),
        "role": "user",
        "created_at": datetime.utcnow(),
    }

    result = db[USERS_COLLECTION].insert_one(user_doc)
    user_id = str(result.inserted_id)

    # Send welcome email
    background_tasks.add_task(send_welcome_email, user_doc["email"], None)

    access_token = create_access_token(data={"sub": user_id})

    return Token(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse(
            id=user_id,
            email=user_doc["email"],
            role=user_doc["role"]
        )
    )


# =========================
# LOGIN
# =========================
@router.post("/login", response_model=Token)
async def login(credentials: UserLogin):

    db = get_db()

    if not credentials.email or '@' not in credentials.email:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid email format"
        )

    user = db[USERS_COLLECTION].find_one({"email": credentials.email.lower()})
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    if not verify_password(credentials.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    user_id = str(user["_id"])
    access_token = create_access_token(data={"sub": user_id})

    return Token(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse(
            id=user_id,
            email=user["email"],
            role=user.get("role", "user")
        )
    )


# =========================
# GET CURRENT USER
# =========================
@router.get("/me", response_model=UserResponse)
async def get_me(current_user: dict = Depends(get_current_user)):
    return UserResponse(**current_user)


# =========================
# LOGOUT
# =========================
@router.post("/logout", response_model=Message)
async def logout(current_user: dict = Depends(get_current_user)):
    """Logout user (no prediction email now)"""
    
    return Message(message="Logged out successfully")


# =========================
# INIT ADMIN
# =========================
@router.get("/init-admin", response_model=Message)
async def init_admin():

    db = get_db()

    admin_count = db[USERS_COLLECTION].count_documents({"role": "admin"})
    if admin_count > 0:
        return Message(message="Admin user already exists")

    admin_email = "admin@mtrack.local"

    admin_doc = {
        "email": admin_email,
        "password_hash": get_password_hash("admin123"),
        "role": "admin",
        "created_at": datetime.utcnow(),
    }

    db[USERS_COLLECTION].insert_one(admin_doc)

    return Message(message=f"Admin user created: {admin_email} / admin123")


# =========================
# GOOGLE LOGIN
# =========================
@router.post("/google", response_model=Token)
async def google_auth(auth_data: GoogleAuthRequest):

    db = get_db()

    try:
        idinfo = id_token.verify_oauth2_token(
            auth_data.token,
            requests.Request(),
            settings.GOOGLE_CLIENT_ID if settings.GOOGLE_CLIENT_ID else None
        )

        google_id = idinfo.get('sub')
        email = idinfo.get('email')
        name = idinfo.get('name', '')
        picture = idinfo.get('picture')

        if not email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email not provided by Google"
            )

        user = db[USERS_COLLECTION].find_one({
            "$or": [
                {"email": email.lower()},
                {"google_id": google_id}
            ]
        })

        is_new_user = False

        if user:
            user_id = str(user["_id"])
        else:
            is_new_user = True

            user_doc = {
                "email": email.lower(),
                "google_id": google_id,
                "profile_picture": picture,
                "role": "user",
                "created_at": datetime.utcnow(),
                "name": name
            }

            result = db[USERS_COLLECTION].insert_one(user_doc)

            user_id = str(result.inserted_id)

        # Send welcome email for new user
        if is_new_user:
            asyncio.create_task(send_welcome_email(email.lower(), name))

        access_token = create_access_token(data={"sub": user_id})

        return Token(
            access_token=access_token,
            token_type="bearer",
            user=UserResponse(
                id=user_id,
                email=email.lower(),
                role="user",
                profile_picture=picture
            )
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Google authentication failed: {str(e)}"
        )