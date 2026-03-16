from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, EmailStr, Field


# --------------------------------------------------
# USER MODELS
# --------------------------------------------------

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    role: Optional[str] = "user"


class UserLogin(BaseModel):
    email: str
    password: str


class GoogleAuthRequest(BaseModel):
    token: str


class UserResponse(BaseModel):
    id: str
    email: str
    role: str
    profile_picture: Optional[str] = None

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


# --------------------------------------------------
# SONG MODELS
# --------------------------------------------------

class SongCreate(BaseModel):
    title: str
    artist: str
    category: str
    description: Optional[str] = None
    audio_url: Optional[str] = None
    thumbnail_url: Optional[str] = None


class SongUpdate(BaseModel):
    title: Optional[str] = None
    artist: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


class SongResponse(BaseModel):
    id: str
    title: str
    artist: str
    category: str
    audio_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    description: Optional[str] = None
    is_active: bool = True
    created_at: datetime

    class Config:
        from_attributes = True


# --------------------------------------------------
# SESSION MODELS
# --------------------------------------------------

class SessionEvent(BaseModel):
    type: str
    timestamp: datetime
    song_id: Optional[str] = None
    duration: Optional[float] = None
    volume: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None


class SessionStart(BaseModel):
    song_id: Optional[str] = None


class SessionAggregatedData(BaseModel):
    song_category_mode: str
    skip_rate_bucket: str
    repeat_bucket: str
    duration_ratio_bucket: str
    session_length_bucket: str
    volume_level_bucket: str
    song_diversity_bucket: str
    listening_time_of_day: str


class SessionEnd(BaseModel):
    session_id: str
    events: List[SessionEvent]
    aggregated_data: SessionAggregatedData


class SessionStartResponse(BaseModel):
    session_id: str
    started_at: datetime


class SessionEndResponse(BaseModel):
    session_id: str
    message: str


class SessionResponse(BaseModel):
    id: str
    user_id: str
    song_id: Optional[str] = None
    started_at: datetime
    ended_at: Optional[datetime] = None
    events: List[Dict[str, Any]]

    class Config:
        from_attributes = True


# --------------------------------------------------
# PLAYLIST MODELS
# --------------------------------------------------

class PlaylistCreate(BaseModel):
    name: str
    description: Optional[str] = None


class PlaylistUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class PlaylistResponse(BaseModel):
    id: str
    user_id: str
    name: str
    description: Optional[str] = None
    song_ids: List[str] = Field(default_factory=list)
    created_at: datetime

    class Config:
        from_attributes = True


class PlaylistAddSong(BaseModel):
    song_id: str


# --------------------------------------------------
# FAVORITE MODELS
# --------------------------------------------------

class FavoriteResponse(BaseModel):
    song_ids: List[str]


# --------------------------------------------------
# QUESTIONNAIRE MODELS
# --------------------------------------------------

class QuestionnaireSubmit(BaseModel):
    phq9_answers: List[int]
    dass21_answers: List[int]


class QuestionnaireResponse(BaseModel):
    phq9_score: int
    dass21_stress_score: int


# --------------------------------------------------
# EMAIL CONFIG MODELS
# --------------------------------------------------

class EmailConfigCreate(BaseModel):
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str
    smtp_password: str
    smtp_from: Optional[str] = None
    enabled: bool = True


class EmailConfigUpdate(BaseModel):
    smtp_host: Optional[str] = None
    smtp_port: Optional[int] = None
    smtp_user: Optional[str] = None
    smtp_password: Optional[str] = None
    smtp_from: Optional[str] = None
    enabled: Optional[bool] = None


class EmailConfigResponse(BaseModel):
    smtp_host: str
    smtp_port: int
    smtp_user: str
    smtp_from: str
    enabled: bool
    updated_at: datetime

    class Config:
        from_attributes = True


# --------------------------------------------------
# COMMON MESSAGE MODEL
# --------------------------------------------------

class Message(BaseModel):
    message: str