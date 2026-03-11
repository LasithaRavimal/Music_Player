from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Query
from typing import List, Optional
from bson import ObjectId
from datetime import datetime
from pathlib import Path
import logging

from app.db import get_db, SONGS_COLLECTION, FAVORITES_COLLECTION
from app.models import SongResponse, SongUpdate, FavoriteResponse, Message
from app.auth import get_current_user, require_admin
from app.config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/songs", tags=["songs"])


# ===================================
# GET SONG LIST
# ===================================
@router.get("", response_model=List[SongResponse])
async def list_songs(
    q: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    current_user: dict = Depends(get_current_user)
):

    db = get_db()

    query = {"is_active": True}

    if q:
        query["$or"] = [
            {"title": {"$regex": q, "$options": "i"}},
            {"artist": {"$regex": q, "$options": "i"}}
        ]

    if category:
        query["category"] = category

    songs = list(db[SONGS_COLLECTION].find(query).sort("created_at", -1))

    return [
        SongResponse(
            id=str(song["_id"]),
            title=song["title"],
            artist=song["artist"],
            category=song["category"],
            audio_url=song.get("audio_url"),
            thumbnail_url=song.get("thumbnail_url"),
            description=song.get("description"),
            is_active=song.get("is_active", True),
            created_at=song.get("created_at").isoformat()
        )
        for song in songs
    ]


# ===================================
# UPLOAD SONG (ADMIN)
# ===================================
@router.post("/upload", response_model=SongResponse)
async def upload_song(
    title: str = Form(...),
    artist: str = Form(...),
    category: str = Form(...),
    description: Optional[str] = Form(None),
    file: UploadFile = File(...),
    admin_user: dict = Depends(require_admin)
):

    db = get_db()

    if not file.filename.endswith((".mp3", ".wav", ".m4a")):
        raise HTTPException(400, "Invalid audio format")

    file_ext = Path(file.filename).suffix
    file_id = ObjectId()

    file_name = f"{file_id}{file_ext}"
    file_path = settings.SONGS_DIR / file_name

    content = await file.read()

    with open(file_path, "wb") as f:
        f.write(content)

    audio_url = f"/media/songs/{file_name}"

    song_doc = {
        "title": title,
        "artist": artist,
        "category": category,
        "description": description,
        "audio_url": audio_url,
        "file_path": str(file_path),
        "is_active": True,
        "created_at": datetime.utcnow()
    }

    result = db[SONGS_COLLECTION].insert_one(song_doc)

    return SongResponse(
        id=str(result.inserted_id),
        title=title,
        artist=artist,
        category=category,
        audio_url=audio_url,
        description=description,
        is_active=True,
        created_at=song_doc["created_at"].isoformat()
    )


# ===================================
# FAVORITE SONG
# ===================================
@router.post("/{song_id}/favorite", response_model=Message)
async def toggle_favorite(
    song_id: str,
    current_user: dict = Depends(get_current_user)
):

    db = get_db()

    user_id = ObjectId(current_user["id"])
    song_oid = ObjectId(song_id)

    fav = db[FAVORITES_COLLECTION].find_one({
        "user_id": user_id,
        "song_id": song_oid
    })

    if fav:
        db[FAVORITES_COLLECTION].delete_one({
            "user_id": user_id,
            "song_id": song_oid
        })
        return Message(message="Favorite removed")

    db[FAVORITES_COLLECTION].insert_one({
        "user_id": user_id,
        "song_id": song_oid,
        "created_at": datetime.utcnow()
    })

    return Message(message="Favorite added")


# ===================================
# GET USER FAVORITES
# ===================================
@router.get("/favorites", response_model=FavoriteResponse)
async def get_favorites(current_user: dict = Depends(get_current_user)):

    db = get_db()

    user_id = ObjectId(current_user["id"])

    favorites = list(db[FAVORITES_COLLECTION].find({"user_id": user_id}))

    ids = [str(f["song_id"]) for f in favorites]

    return FavoriteResponse(song_ids=ids)


# ===================================
# GET SONG CATEGORIES
# ===================================
@router.get("/categories")
async def get_categories(current_user: dict = Depends(get_current_user)):

    db = get_db()

    categories = db[SONGS_COLLECTION].distinct("category", {"is_active": True})

    return {"categories": sorted(categories)}