import logging
from datetime import datetime, timedelta
from app.db import get_db, SESSIONS_COLLECTION

logger = logging.getLogger(__name__)


def cleanup_inactive_sessions():
    """
    Background task to auto-end inactive sessions (>10 minutes since last event).
    Only ends the session and saves listening behaviour data.
    No ML prediction or email alerts.
    """
    db = get_db()
    now = datetime.utcnow()
    inactive_threshold = now - timedelta(minutes=10)

    # Find active sessions inactive for more than 10 minutes
    inactive_sessions = list(db[SESSIONS_COLLECTION].find({
        "is_active": True,
        "last_event_at": {"$lt": inactive_threshold}
    }))

    if not inactive_sessions:
        logger.debug("No inactive sessions to clean up")
        return

    logger.info(f"Auto-ending {len(inactive_sessions)} inactive sessions")

    for session in inactive_sessions:
        try:
            session_id = str(session["_id"])
            user_id = session["user_id"]

            # Preserve existing aggregated data if available
            aggregated_data = session.get("aggregated_data", {})

            # Calculate session length
            session_length_bucket = _calculate_session_length_bucket(
                session.get("started_at"),
                now
            )

            aggregated_data["session_length_bucket"] = session_length_bucket
            aggregated_data["listening_time_of_day"] = _get_listening_time_of_day(now)

            # Update session document
            db[SESSIONS_COLLECTION].update_one(
                {"_id": session["_id"]},
                {
                    "$set": {
                        "ended_at": now,
                        "is_active": False,
                        "aggregated_data": aggregated_data,
                        "updated_at": now,
                        "auto_ended": True
                    }
                }
            )

            logger.info(f"Auto-ended session {session_id} for user {user_id}")

        except Exception as e:
            logger.error(f"Error auto-ending session {session.get('_id')}: {str(e)}")


def _calculate_session_length_bucket(started_at: datetime, ended_at: datetime) -> str:
    """Calculate session length bucket based on duration"""
    if not started_at:
        return "Unknown"

    duration = ended_at - started_at
    duration_minutes = duration.total_seconds() / 60

    if duration_minutes < 10:
        return "Less than 10 min"
    elif duration_minutes < 30:
        return "10-30 min"
    elif duration_minutes < 60:
        return "30-60 min"
    else:
        return "More than 1 hour"


def _get_listening_time_of_day(dt: datetime) -> str:
    """Get listening time of day bucket"""
    hour = dt.hour

    if 5 <= hour < 11:
        return "Morning (5am-11am)"
    elif 11 <= hour < 15:
        return "Afternoon (11am-3pm)"
    elif 15 <= hour < 20:
        return "Evening (3pm-8pm)"
    elif 20 <= hour < 24:
        return "Night (8pm-12am)"
    else:
        return "Midnight (12am-5am)"