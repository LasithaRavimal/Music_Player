from pymongo import MongoClient
from pymongo.database import Database
from app.config import settings


client: MongoClient | None = None
db: Database | None = None


# ==================================
# CONNECT DATABASE
# ==================================

def connect_db() -> Database:
    """Initialize MongoDB connection"""

    global client, db

    client = MongoClient(settings.MONGO_URI)

    db = client[settings.DB_NAME]

    return db


# ==================================
# CLOSE DATABASE
# ==================================

def close_db():
    """Close MongoDB connection"""

    global client

    if client:
        client.close()


# ==================================
# GET DATABASE INSTANCE
# ==================================

def get_db() -> Database:
    """Return active database connection"""

    if db is None:
        return connect_db()

    return db


# ==================================
# COLLECTION NAMES
# ==================================

USERS_COLLECTION = "users"

SONGS_COLLECTION = "songs"

SESSIONS_COLLECTION = "listening_sessions"

FAVORITES_COLLECTION = "favorites"

PLAYLISTS_COLLECTION = "playlists"

EMAIL_CONFIG_COLLECTION = "email_config"

# NEW COLLECTION FOR QUESTIONNAIRE DATA

QUESTIONNAIRE_COLLECTION = "questionnaire_results"