"""Authenticated in-app notifications and course announcements."""

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.auth import AuthenticatedUser, get_current_user, require_course_access
from app.data.db import get_db_connection
from app.models.common import APIEnvelope

router = APIRouter(prefix="/api", tags=["Notifications & Announcements"])

_NOTIFICATION_COLUMNS = "id, title, message, category, is_read, link, created_at"


def _recipient(user: AuthenticatedUser) -> tuple[str, str]:
    if user.role == "STUDENT":
        if not user.student_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Student identity is unavailable.")
        return user.student_id, user.role
    return user.user_id, user.role


def _notification_list(user: AuthenticatedUser, *, unread_only: bool, limit: int) -> list[dict]:
    recipient_id, recipient_role = _recipient(user)
    unread_clause = " AND is_read = 0" if unread_only else ""
    with get_db_connection() as conn:
        rows = conn.execute(
            f"""
            SELECT {_NOTIFICATION_COLUMNS}
            FROM notifications
            WHERE user_id = ? AND user_role = ?{unread_clause}
            ORDER BY created_at DESC, id DESC
            LIMIT ?
            """,
            (recipient_id, recipient_role, limit),
        ).fetchall()
    return [dict(row) for row in rows]


@router.get("/notifications", response_model=APIEnvelope[list[dict]])
async def list_notifications(
    limit: int = Query(default=50, ge=1, le=100),
    user: AuthenticatedUser = Depends(get_current_user),
):
    """List only notifications addressed to the verified session identity."""
    return APIEnvelope(success=True, data=_notification_list(user, unread_only=False, limit=limit), trace_id="notifications-list")


@router.get("/notifications/unread", response_model=APIEnvelope[list[dict]])
async def list_unread_notifications(
    limit: int = Query(default=50, ge=1, le=100),
    user: AuthenticatedUser = Depends(get_current_user),
):
    """List unread notifications for the verified session identity."""
    return APIEnvelope(success=True, data=_notification_list(user, unread_only=True, limit=limit), trace_id="notifications-unread")


@router.get("/notifications/unread-count", response_model=APIEnvelope[dict[str, int]])
async def count_unread_notifications(user: AuthenticatedUser = Depends(get_current_user)):
    """Return the unread count for the verified session identity."""
    recipient_id, recipient_role = _recipient(user)
    with get_db_connection() as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS count FROM notifications WHERE user_id = ? AND user_role = ? AND is_read = 0",
            (recipient_id, recipient_role),
        ).fetchone()
    return APIEnvelope(success=True, data={"count": row["count"]}, trace_id="notifications-unread-count")


@router.post("/notifications/{notification_id}/read", response_model=APIEnvelope[dict])
async def mark_notification_read(
    notification_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
):
    """Mark one of the verified session's notifications read; hide other recipients' IDs."""
    recipient_id, recipient_role = _recipient(user)
    with get_db_connection(immediate=True) as conn:
        conn.execute(
            """
            UPDATE notifications SET is_read = 1
            WHERE id = ? AND user_id = ? AND user_role = ?
            """,
            (notification_id, recipient_id, recipient_role),
        )
        row = conn.execute(
            f"""
            SELECT {_NOTIFICATION_COLUMNS}
            FROM notifications
            WHERE id = ? AND user_id = ? AND user_role = ?
            """,
            (notification_id, recipient_id, recipient_role),
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification was not found.")
    return APIEnvelope(success=True, data=dict(row), trace_id="notification-mark-read")


@router.get("/announcements", response_model=APIEnvelope[list[dict]])
async def list_course_announcements(
    course_id: str = Query(default="26ECAC401"),
    user: AuthenticatedUser = Depends(get_current_user),
):
    """Expose existing announcements only to members authorized for their course."""
    require_course_access(user, course_id)
    with get_db_connection() as conn:
        rows = conn.execute(
            """
            SELECT id, course_id, title, content, posted_by, priority, created_at
            FROM announcements
            WHERE course_id = ?
            ORDER BY created_at DESC, id DESC
            """,
            (course_id,),
        ).fetchall()
    return APIEnvelope(success=True, data=[dict(row) for row in rows], trace_id="announcements-list")
