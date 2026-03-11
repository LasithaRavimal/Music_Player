from fastapi import APIRouter, Depends, HTTPException, status
from bson import ObjectId
from datetime import datetime
from typing import List

from app.db import get_db, PLAYLISTS_COLLECTION, SONGS_COLLECTION
from app.models import (
    PlaylistCreate,
    PlaylistUpdate,
    PlaylistResponse,
    PlaylistAddSong,
    Message
)
from app.auth import get_current_user

router = APIRouter(prefix="/playlists", tags=["playlists"])


# =========================
# GET USER PLAYLISTS
# =========================
@router.get("", response_model=List[PlaylistResponse])
async def list_playlists(current_user: dict = Depends(get_current_user)):

    db = get_db()
    user_id = ObjectId(current_user["id"])

    playlists = list(
        db[PLAYLISTS_COLLECTION]
        .find({"user_id": user_id})
        .sort("created_at", -1)
    )

    return [
        PlaylistResponse(
            id=str(p["_id"]),
            user_id=str(p["user_id"]),
            name=p["name"],
            description=p.get("description"),
            song_ids=[str(sid) for sid in p.get("song_ids", [])],
            created_at=p.get("created_at", datetime.utcnow()).isoformat()
        )
        for p in playlists
    ]


# =========================
# CREATE PLAYLIST
# =========================
@router.post("", response_model=PlaylistResponse, status_code=status.HTTP_201_CREATED)
async def create_playlist(
    playlist_data: PlaylistCreate,
    current_user: dict = Depends(get_current_user)
):

    db = get_db()
    user_id = ObjectId(current_user["id"])

    playlist_doc = {
        "user_id": user_id,
        "name": playlist_data.name,
        "description": playlist_data.description,
        "song_ids": [],
        "created_at": datetime.utcnow(),
    }

    result = db[PLAYLISTS_COLLECTION].insert_one(playlist_doc)

    return PlaylistResponse(
        id=str(result.inserted_id),
        user_id=current_user["id"],
        name=playlist_data.name,
        description=playlist_data.description,
        song_ids=[],
        created_at=playlist_doc["created_at"].isoformat()
    )


# =========================
# GET SINGLE PLAYLIST
# =========================
@router.get("/{playlist_id}", response_model=PlaylistResponse)
async def get_playlist(
    playlist_id: str,
    current_user: dict = Depends(get_current_user)
):

    db = get_db()

    playlist = db[PLAYLISTS_COLLECTION].find_one({
        "_id": ObjectId(playlist_id),
        "user_id": ObjectId(current_user["id"])
    })

    if not playlist:
        raise HTTPException(status_code=404, detail="Playlist not found")

    return PlaylistResponse(
        id=str(playlist["_id"]),
        user_id=str(playlist["user_id"]),
        name=playlist["name"],
        description=playlist.get("description"),
        song_ids=[str(sid) for sid in playlist.get("song_ids", [])],
        created_at=playlist.get("created_at", datetime.utcnow()).isoformat()
    )


# =========================
# UPDATE PLAYLIST
# =========================
@router.put("/{playlist_id}", response_model=PlaylistResponse)
async def update_playlist(
    playlist_id: str,
    playlist_data: PlaylistUpdate,
    current_user: dict = Depends(get_current_user)
):

    db = get_db()
    playlist_oid = ObjectId(playlist_id)
    user_id = ObjectId(current_user["id"])

    playlist = db[PLAYLISTS_COLLECTION].find_one({
        "_id": playlist_oid,
        "user_id": user_id
    })

    if not playlist:
        raise HTTPException(status_code=404, detail="Playlist not found")

    update_data = {}

    if playlist_data.name is not None:
        update_data["name"] = playlist_data.name

    if playlist_data.description is not None:
        update_data["description"] = playlist_data.description

    if update_data:
        update_data["updated_at"] = datetime.utcnow()

        db[PLAYLISTS_COLLECTION].update_one(
            {"_id": playlist_oid},
            {"$set": update_data}
        )

        playlist.update(update_data)

    return PlaylistResponse(
        id=str(playlist["_id"]),
        user_id=str(playlist["user_id"]),
        name=playlist["name"],
        description=playlist.get("description"),
        song_ids=[str(sid) for sid in playlist.get("song_ids", [])],
        created_at=playlist.get("created_at", datetime.utcnow()).isoformat()
    )


# =========================
# DELETE PLAYLIST
# =========================
@router.delete("/{playlist_id}", response_model=Message)
async def delete_playlist(
    playlist_id: str,
    current_user: dict = Depends(get_current_user)
):

    db = get_db()

    result = db[PLAYLISTS_COLLECTION].delete_one({
        "_id": ObjectId(playlist_id),
        "user_id": ObjectId(current_user["id"])
    })

    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Playlist not found")

    return Message(message="Playlist deleted successfully")


# =========================
# ADD SONG TO PLAYLIST
# =========================
@router.post("/{playlist_id}/songs", response_model=Message)
async def add_song_to_playlist(
    playlist_id: str,
    song_data: PlaylistAddSong,
    current_user: dict = Depends(get_current_user)
):

    db = get_db()

    playlist = db[PLAYLISTS_COLLECTION].find_one({
        "_id": ObjectId(playlist_id),
        "user_id": ObjectId(current_user["id"])
    })

    if not playlist:
        raise HTTPException(status_code=404, detail="Playlist not found")

    song = db[SONGS_COLLECTION].find_one({"_id": ObjectId(song_data.song_id)})

    if not song:
        raise HTTPException(status_code=404, detail="Song not found")

    if ObjectId(song_data.song_id) not in playlist.get("song_ids", []):
        db[PLAYLISTS_COLLECTION].update_one(
            {"_id": ObjectId(playlist_id)},
            {
                "$push": {"song_ids": ObjectId(song_data.song_id)},
                "$set": {"updated_at": datetime.utcnow()}
            }
        )

    return Message(message="Song added to playlist")


# =========================
# REMOVE SONG FROM PLAYLIST
# =========================
@router.delete("/{playlist_id}/songs/{song_id}", response_model=Message)
async def remove_song_from_playlist(
    playlist_id: str,
    song_id: str,
    current_user: dict = Depends(get_current_user)
):

    db = get_db()

    db[PLAYLISTS_COLLECTION].update_one(
        {
            "_id": ObjectId(playlist_id),
            "user_id": ObjectId(current_user["id"])
        },
        {
            "$pull": {"song_ids": ObjectId(song_id)},
            "$set": {"updated_at": datetime.utcnow()}
        }
    )

    return Message(message="Song removed from playlist")