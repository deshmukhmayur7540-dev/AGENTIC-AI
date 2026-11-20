"""Create one application account using credentials supplied only through environment variables."""

import os
import sqlite3
import sys

from app.data.db import init_database
from app.services.auth_service import create_user


def main() -> int:
    email = os.getenv("COURSEAGENTAI_INIT_EMAIL", "")
    password = os.getenv("COURSEAGENTAI_INIT_PASSWORD", "")
    role = os.getenv("COURSEAGENTAI_INIT_ROLE", "")
    user_id = os.getenv("COURSEAGENTAI_INIT_USER_ID", "")
    display_name = os.getenv("COURSEAGENTAI_INIT_DISPLAY_NAME", "")
    student_id = os.getenv("COURSEAGENTAI_INIT_STUDENT_ID") or None
    course_scopes = [
        item.strip()
        for item in os.getenv("COURSEAGENTAI_INIT_COURSE_SCOPES", "").split(",")
        if item.strip()
    ]
    if not all((email, password, role, user_id, display_name)):
        print(
            "Set COURSEAGENTAI_INIT_EMAIL, COURSEAGENTAI_INIT_PASSWORD, "
            "COURSEAGENTAI_INIT_ROLE, COURSEAGENTAI_INIT_USER_ID, and "
            "COURSEAGENTAI_INIT_DISPLAY_NAME.",
            file=sys.stderr,
        )
        return 2
    try:
        init_database()
        create_user(
            user_id=user_id,
            email=email,
            display_name=display_name,
            password=password,
            role=role,
            student_id=student_id,
            course_scopes=course_scopes,
        )
    except (ValueError, sqlite3.IntegrityError) as exc:
        print(f"Account initialization failed: {exc}", file=sys.stderr)
        return 1
    print(f"Initialized {role.upper()} account {email.lower()}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
