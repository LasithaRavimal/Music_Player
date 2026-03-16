from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Query
from typing import List, Optional
from bson import ObjectId
from datetime import datetime
import os
import logging
from pathlib import Path
from app.db import get_db, SONGS_COLLECTION, FAVORITES_COLLECTION
from app.models import SongResponse, SongCreate, SongUpdate, FavoriteResponse, Message
from app.auth import get_current_user, require_admin
from app.config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/songs", tags=["songs"])

@router.get("", response_model=List[SongResponse])
async def list_songs(
    q: Optional[str] = Query(None, description="Search query"),
    category: Optional[str] = Query(None, description="Filter by category"),
    is_active: Optional[bool] = Query(None, description="Filter by active status (admin only)"),
    current_user: dict = Depends(get_current_user)
):
    """List songs with optional search and category filter. Regular users only see active songs."""
    db = get_db()
    
    query = {}
    
    # Regular users only see active songs, admins can see all or filter
    if current_user.get("role") != "admin":
        query["is_active"] = True
    elif is_active is not None:
        query["is_active"] = is_active
    
    if q:
        query["$or"] = [
            {"title": {"$regex": q, "$options": "i"}},
            {"artist": {"$regex": q, "$options": "i"}},
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
            created_at=song.get("created_at", datetime.utcnow()).isoformat()
        )
        for song in songs
    ]


@router.post("/upload", response_model=SongResponse, status_code=status.HTTP_201_CREATED)
async def upload_song(
    title: str = Form(...),
    artist: str = Form(...),
    category: str = Form(...),
    description: Optional[str] = Form(None),
    audio_url: str = Form(...),          # 🔥 Supabase audio URL
    thumbnail_url: Optional[str] = Form(None),  # 🔥 Supabase image URL
    admin_user: dict = Depends(require_admin)
):
    """Save song URLs uploaded to Supabase (admin only)"""

    db = get_db()

    song_doc = {
        "title": title,
        "artist": artist,
        "category": category,
        "description": description,
        "audio_url": audio_url,
        "thumbnail_url": thumbnail_url,
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
        thumbnail_url=thumbnail_url,
        description=description,
        is_active=True,
        created_at=song_doc["created_at"].isoformat()
    )


@router.post("/{song_id}/favorite", response_model=Message)
async def toggle_favorite(
    song_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Toggle favorite status for a song"""
    db = get_db()
    
    # Validate song exists
    song = db[SONGS_COLLECTION].find_one({"_id": ObjectId(song_id)})
    if not song:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Song not found"
        )
    
    user_id = ObjectId(current_user["id"])
    song_oid = ObjectId(song_id)
    
    # Check if already favorited
    existing = db[FAVORITES_COLLECTION].find_one({
        "user_id": user_id,
        "song_id": song_oid
    })
    
    if existing:
        # Remove favorite
        db[FAVORITES_COLLECTION].delete_one({
            "user_id": user_id,
            "song_id": song_oid
        })
        return Message(message="Favorite removed")
    else:
        # Add favorite
        db[FAVORITES_COLLECTION].insert_one({
            "user_id": user_id,
            "song_id": song_oid,
            "created_at": datetime.utcnow()
        })
        return Message(message="Favorite added")


@router.get("/favorites", response_model=FavoriteResponse)
async def get_favorites(
    current_user: dict = Depends(get_current_user)
):
    """Get user's favorite song IDs"""
    db = get_db()
    
    user_id = ObjectId(current_user["id"])
    favorites = list(db[FAVORITES_COLLECTION].find({"user_id": user_id}))
    
    favorite_ids = [str(fav["song_id"]) for fav in favorites]
    
    return FavoriteResponse(song_ids=favorite_ids)


@router.put("/{song_id}", response_model=SongResponse)
async def update_song(
    song_id: str,
    song_data: SongUpdate,
    admin_user: dict = Depends(require_admin)
):
    """Update song details (admin only)"""
    db = get_db()
    song_oid = ObjectId(song_id)
    
    # Verify song exists
    song = db[SONGS_COLLECTION].find_one({"_id": song_oid})
    if not song:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Song not found"
        )
    
    # Update fields
    update_data = {}
    if song_data.title is not None:
        update_data["title"] = song_data.title
    if song_data.artist is not None:
        update_data["artist"] = song_data.artist
    if song_data.category is not None:
        update_data["category"] = song_data.category
    if song_data.description is not None:
        update_data["description"] = song_data.description
    if song_data.is_active is not None:
        update_data["is_active"] = song_data.is_active
    
    if update_data:
        update_data["updated_at"] = datetime.utcnow()
        db[SONGS_COLLECTION].update_one(
            {"_id": song_oid},
            {"$set": update_data}
        )
        song.update(update_data)
    
    return SongResponse(
        id=str(song["_id"]),
        title=song["title"],
        artist=song["artist"],
        category=song["category"],
        audio_url=song.get("audio_url"),
        thumbnail_url=song.get("thumbnail_url"),
        description=song.get("description"),
        is_active=song.get("is_active", True),
        created_at=song.get("created_at", datetime.utcnow()).isoformat()
    )


@router.patch("/{song_id}/toggle-visibility", response_model=SongResponse)
async def toggle_song_visibility(
    song_id: str,
    admin_user: dict = Depends(require_admin)
):
    """Toggle song visibility/active status (admin only)"""
    db = get_db()
    song_oid = ObjectId(song_id)
    
    # Verify song exists
    song = db[SONGS_COLLECTION].find_one({"_id": song_oid})
    if not song:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Song not found"
        )
    
    # Toggle is_active
    new_status = not song.get("is_active", True)
    db[SONGS_COLLECTION].update_one(
        {"_id": song_oid},
        {"$set": {"is_active": new_status, "updated_at": datetime.utcnow()}}
    )
    song["is_active"] = new_status
    
    return SongResponse(
        id=str(song["_id"]),
        title=song["title"],
        artist=song["artist"],
        category=song["category"],
        audio_url=song.get("audio_url"),
        thumbnail_url=song.get("thumbnail_url"),
        description=song.get("description"),
        is_active=song.get("is_active", True),
        created_at=song.get("created_at", datetime.utcnow()).isoformat()
    )


@router.delete("/{song_id}", response_model=Message)
async def delete_song(
    song_id: str,
    admin_user: dict = Depends(require_admin)
):
    """Delete a song (admin only)"""
    db = get_db()
    song_oid = ObjectId(song_id)
    
    # Get song info
    song = db[SONGS_COLLECTION].find_one({"_id": song_oid})
    if not song:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Song not found"
        )
    
    # Delete files
    try:
        if song.get("file_path") and Path(song["file_path"]).exists():
            Path(song["file_path"]).unlink()
        if song.get("thumbnail_url"):
            thumb_path = settings.THUMBNAILS_DIR / Path(song["thumbnail_url"]).name
            if thumb_path.exists():
                thumb_path.unlink()
    except Exception as e:
        logger.warning(f"Failed to delete files: {e}")
    
    # Delete from database
    db[SONGS_COLLECTION].delete_one({"_id": song_oid})
    
    return Message(message="Song deleted successfully")


@router.get("/categories")
async def get_categories(
    current_user: dict = Depends(get_current_user)
):
    """Get all available categories from active songs"""
    db = get_db()
    
    # Regular users only see categories from active songs
    query = {"is_active": True} if current_user.get("role") != "admin" else {}
    
    # Get distinct categories from songs
    categories = db[SONGS_COLLECTION].distinct("category", query)
    
    # Return sorted list of categories
    return {"categories": sorted([cat for cat in categories if cat])}

from fastapi import APIRouter, Depends, HTTPException, status, Form, Query
from typing import List, Optional
from bson import ObjectId
from datetime import datetime
import logging

from app.db import get_db, SONGS_COLLECTION, FAVORITES_COLLECTION
from app.models import SongResponse, SongUpdate, FavoriteResponse, Message
from app.auth import get_current_user, require_admin

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/songs", tags=["songs"])


# --------------------------------------------------
# LIST SONGS
# --------------------------------------------------

@router.get("", response_model=List[SongResponse])
async def list_songs(
    q: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    current_user: dict = Depends(get_current_user)
):

    db = get_db()
    query = {}

    # Normal users see only active songs
    if current_user.get("role") != "admin":
        query["is_active"] = True
    elif is_active is not None:
        query["is_active"] = is_active

    if q:
        query["$or"] = [
            {"title": {"$regex": q, "$options": "i"}},
            {"artist": {"$regex": q, "$options": "i"}}
        ]

    if category:
        query["category"] = category

    songs = list(
        db[SONGS_COLLECTION]
        .find(query)
        .sort("created_at", -1)
    )

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
            created_at=song.get("created_at", datetime.utcnow()).isoformat()
        )
        for song in songs
    ]


# --------------------------------------------------
# UPLOAD SONG (SUPABASE URL SAVE)
# --------------------------------------------------

@router.post("/upload", response_model=SongResponse, status_code=status.HTTP_201_CREATED)
async def upload_song(
    title: str = Form(...),
    artist: str = Form(...),
    category: str = Form(...),
    description: Optional[str] = Form(None),
    audio_url: str = Form(...),      # Supabase audio URL
    thumbnail_url: Optional[str] = Form(None),
    admin_user: dict = Depends(require_admin)
):

    db = get_db()

    song_doc = {
        "title": title,
        "artist": artist,
        "category": category,
        "description": description,
        "audio_url": audio_url,
        "thumbnail_url": thumbnail_url,
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
        thumbnail_url=thumbnail_url,
        description=description,
        is_active=True,
        created_at=song_doc["created_at"].isoformat()
    )


# --------------------------------------------------
# TOGGLE FAVORITE
# --------------------------------------------------

@router.post("/{song_id}/favorite", response_model=Message)
async def toggle_favorite(
    song_id: str,
    current_user: dict = Depends(get_current_user)
):

    db = get_db()

    try:
        song_oid = ObjectId(song_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid song ID")

    song = db[SONGS_COLLECTION].find_one({"_id": song_oid})

    if not song:
        raise HTTPException(status_code=404, detail="Song not found")

    user_id = ObjectId(current_user["id"])

    existing = db[FAVORITES_COLLECTION].find_one({
        "user_id": user_id,
        "song_id": song_oid
    })

    if existing:

        db[FAVORITES_COLLECTION].delete_one({
            "user_id": user_id,
            "song_id": song_oid
        })

        return Message(message="Favorite removed")

    else:

        db[FAVORITES_COLLECTION].insert_one({
            "user_id": user_id,
            "song_id": song_oid,
            "created_at": datetime.utcnow()
        })

        return Message(message="Favorite added")


# --------------------------------------------------
# GET FAVORITES
# --------------------------------------------------

@router.get("/favorites", response_model=FavoriteResponse)
async def get_favorites(
    current_user: dict = Depends(get_current_user)
):

    db = get_db()

    user_id = ObjectId(current_user["id"])

    favorites = list(
        db[FAVORITES_COLLECTION].find({"user_id": user_id})
    )

    favorite_ids = [str(fav["song_id"]) for fav in favorites]

    return FavoriteResponse(song_ids=favorite_ids)


# --------------------------------------------------
# UPDATE SONG
# --------------------------------------------------

@router.put("/{song_id}", response_model=SongResponse)
async def update_song(
    song_id: str,
    song_data: SongUpdate,
    admin_user: dict = Depends(require_admin)
):

    db = get_db()

    try:
        song_oid = ObjectId(song_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid song ID")

    song = db[SONGS_COLLECTION].find_one({"_id": song_oid})

    if not song:
        raise HTTPException(status_code=404, detail="Song not found")

    update_data = {}

    if song_data.title is not None:
        update_data["title"] = song_data.title

    if song_data.artist is not None:
        update_data["artist"] = song_data.artist

    if song_data.category is not None:
        update_data["category"] = song_data.category

    if song_data.description is not None:
        update_data["description"] = song_data.description

    if song_data.is_active is not None:
        update_data["is_active"] = song_data.is_active

    if update_data:
        update_data["updated_at"] = datetime.utcnow()

        db[SONGS_COLLECTION].update_one(
            {"_id": song_oid},
            {"$set": update_data}
        )

        song.update(update_data)

    return SongResponse(
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


# --------------------------------------------------
# TOGGLE SONG VISIBILITY
# --------------------------------------------------

@router.patch("/{song_id}/toggle-visibility", response_model=SongResponse)
async def toggle_song_visibility(
    song_id: str,
    admin_user: dict = Depends(require_admin)
):

    db = get_db()

    song_oid = ObjectId(song_id)

    song = db[SONGS_COLLECTION].find_one({"_id": song_oid})

    if not song:
        raise HTTPException(status_code=404, detail="Song not found")

    new_status = not song.get("is_active", True)

    db[SONGS_COLLECTION].update_one(
        {"_id": song_oid},
        {"$set": {
            "is_active": new_status,
            "updated_at": datetime.utcnow()
        }}
    )

    song["is_active"] = new_status

    return SongResponse(
        id=str(song["_id"]),
        title=song["title"],
        artist=song["artist"],
        category=song["category"],
        audio_url=song.get("audio_url"),
        thumbnail_url=song.get("thumbnail_url"),
        description=song.get("description"),
        is_active=new_status,
        created_at=song.get("created_at").isoformat()
    )


# --------------------------------------------------
# DELETE SONG
# --------------------------------------------------

@router.delete("/{song_id}", response_model=Message)
async def delete_song(
    song_id: str,
    admin_user: dict = Depends(require_admin)
):

    db = get_db()

    song_oid = ObjectId(song_id)

    song = db[SONGS_COLLECTION].find_one({"_id": song_oid})

    if not song:
        raise HTTPException(status_code=404, detail="Song not found")

    db[SONGS_COLLECTION].delete_one({"_id": song_oid})

    return Message(message="Song deleted successfully")


# --------------------------------------------------
# GET SONG CATEGORIES
# --------------------------------------------------

@router.get("/categories")
async def get_categories(
    current_user: dict = Depends(get_current_user)
):

    db = get_db()

    query = {}

    if current_user.get("role") != "admin":
        query["is_active"] = True

    categories = db[SONGS_COLLECTION].distinct("category", query)

    return {
        "categories": sorted([cat for cat in categories if cat])
    }