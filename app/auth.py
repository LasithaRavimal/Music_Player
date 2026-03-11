from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from bson import ObjectId

from app.db import get_db, USERS_COLLECTION
from app.utils.security import decode_access_token

# Bearer token authentication
security = HTTPBearer()


# =====================================
# GET USER ID FROM TOKEN
# =====================================
def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> str:
    """
    Extract user ID from JWT token
    """

    token = credentials.credentials

    payload = decode_access_token(token)

    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials"
        )

    user_id = payload.get("sub")

    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials"
        )

    return user_id


# =====================================
# GET CURRENT USER
# =====================================
def get_current_user(user_id: str = Depends(get_current_user_id)):
    """
    Get authenticated user from database
    """

    db = get_db()

    user = db[USERS_COLLECTION].find_one({"_id": ObjectId(user_id)})

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )

    return {
        "id": str(user["_id"]),
        "email": user["email"],
        "role": user.get("role", "user")
    }


# =====================================
# ADMIN AUTHORIZATION
# =====================================
def require_admin(current_user: dict = Depends(get_current_user)):
    """
    Allow access only for admin users
    """

    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )

    return current_user