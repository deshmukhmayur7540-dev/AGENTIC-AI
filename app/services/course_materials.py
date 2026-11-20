"""Database-backed course folders and safely stored learning materials."""

from __future__ import annotations

import hashlib
import json
import logging
import mimetypes
import re
import sqlite3
import unicodedata
import uuid
import zipfile
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path, PureWindowsPath
from typing import Any

from app.data.db import get_db_connection
from config import settings

logger = logging.getLogger(__name__)

MAX_UPLOAD_BYTES = settings.course_material_max_upload_bytes
MAX_BATCH_BYTES = MAX_UPLOAD_BYTES * 5
MAX_BATCH_FILES = 10
_MIME_TYPES = {
    "pdf": "application/pdf",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "txt": "text/plain",
    "md": "text/markdown",
    "png": "image/png",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "gif": "image/gif",
    "webp": "image/webp",
}
_CATEGORY_IDS = {
    "notes",
    "lab-manuals",
    "lesson-plans",
    "presentations",
    "assignments",
    "question-banks",
    "reference-materials",
    "syllabus",
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _materials_root() -> Path:
    return Path(settings.course_materials_root).resolve()


def _stored_path(storage_key: str) -> Path:
    root = _materials_root()
    if not re.fullmatch(r"[a-f0-9]{32}\.[a-z0-9]+", storage_key):
        raise ValueError("Invalid stored file reference.")
    path = (root / storage_key).resolve()
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise ValueError("Stored file reference is outside the materials directory.") from exc
    return path


def sanitize_filename(filename: str | None) -> tuple[str, str]:
    original = PureWindowsPath(filename or "").name
    original = Path(original).name
    original = unicodedata.normalize("NFC", original).strip()
    if not original or original in {".", ".."} or any(ord(char) < 32 for char in original):
        raise ValueError("Provide a valid filename.")
    extension = original.rsplit(".", 1)[-1].lower() if "." in original else ""
    if extension not in _MIME_TYPES:
        raise ValueError(f"Unsupported file type '.{extension}'.")
    if len(original) > 240:
        raise ValueError("Filename must be 240 characters or fewer.")
    return original, extension


def validate_upload(filename: str | None, content: bytes) -> tuple[str, str, str]:
    safe_name, extension = sanitize_filename(filename)
    if not content:
        raise ValueError("Empty files cannot be uploaded.")
    if len(content) > MAX_UPLOAD_BYTES:
        raise ValueError(f"Each file must be {MAX_UPLOAD_BYTES // (1024 * 1024)} MB or smaller.")

    detected_type: str
    if extension == "pdf":
        if not content.startswith(b"%PDF-"):
            raise ValueError("The file content does not match a PDF document.")
        detected_type = "application/pdf"
    elif extension in {"docx", "pptx", "xlsx"}:
        expected = {
            "docx": ("[Content_Types].xml", "word/document.xml"),
            "pptx": ("[Content_Types].xml", "ppt/presentation.xml"),
            "xlsx": ("[Content_Types].xml", "xl/workbook.xml"),
        }[extension]
        try:
            with zipfile.ZipFile(BytesIO(content)) as archive:
                names = archive.namelist()
                if len(names) > 2000 or sum(item.file_size for item in archive.infolist()) > 100 * 1024 * 1024:
                    raise ValueError("Office document expands beyond the permitted size.")
                if not set(expected).issubset(names) or archive.testzip() is not None:
                    raise ValueError(f"The file content does not match a valid {extension.upper()} document.")
                if any(name.startswith(("/", "\\")) or ".." in Path(name).parts for name in names):
                    raise ValueError("The Office document contains unsafe internal paths.")
        except zipfile.BadZipFile as exc:
            raise ValueError(f"The file content does not match a valid {extension.upper()} document.") from exc
        detected_type = _MIME_TYPES[extension]
    elif extension in {"txt", "md"}:
        if b"\x00" in content[:4096]:
            raise ValueError("The file content does not match a UTF-8 text document.")
        try:
            content.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise ValueError("Text files must use UTF-8 encoding.") from exc
        detected_type = "text/plain"
    elif extension in {"jpg", "jpeg"}:
        if not content.startswith(b"\xff\xd8\xff"):
            raise ValueError("The file content does not match a JPEG image.")
        detected_type = "image/jpeg"
    elif extension == "png":
        if not content.startswith(b"\x89PNG\r\n\x1a\n"):
            raise ValueError("The file content does not match a PNG image.")
        detected_type = "image/png"
    elif extension == "gif":
        if not content.startswith((b"GIF87a", b"GIF89a")):
            raise ValueError("The file content does not match a GIF image.")
        detected_type = "image/gif"
    else:
        if len(content) < 12 or content[0:4] != b"RIFF" or content[8:12] != b"WEBP":
            raise ValueError("The file content does not match a WebP image.")
        detected_type = "image/webp"
    return safe_name, extension, detected_type


def _clean_label(value: str, label: str, maximum: int = 120) -> str:
    value = unicodedata.normalize("NFC", value).strip()
    if not value or value in {".", ".."} or len(value) > maximum:
        raise ValueError(f"{label} must contain 1 to {maximum} characters.")
    if any(ord(char) < 32 for char in value) or "/" in value or "\\" in value:
        raise ValueError(f"{label} cannot contain path separators or control characters.")
    return value


def _audit(
    conn: sqlite3.Connection,
    *,
    actor_id: str,
    actor_role: str,
    action: str,
    resource: str,
    details: dict[str, Any],
) -> None:
    conn.execute(
        """
        INSERT INTO audit_events
            (event_type, actor, actor_role, resource, action, outcome, details, trace_id, timestamp)
        VALUES (?, ?, ?, ?, ?, 'SUCCESS', ?, ?, ?)
        """,
        (
            f"COURSE_MATERIAL_{action}",
            actor_id,
            actor_role,
            resource,
            action,
            json.dumps(details, ensure_ascii=False),
            f"materials-{uuid.uuid4().hex}",
            _now(),
        ),
    )


def _category(conn: sqlite3.Connection, category_id: str) -> sqlite3.Row:
    row = conn.execute(
        "SELECT category_id, name, sort_order FROM material_categories WHERE category_id = ?",
        (category_id,),
    ).fetchone()
    if not row:
        raise ValueError("Select one of the available course material categories.")
    return row


def _folder(
    conn: sqlite3.Connection,
    folder_id: str | None,
    course_id: str,
    category_id: str,
) -> sqlite3.Row | None:
    if folder_id is None:
        return None
    row = conn.execute(
        """
        SELECT folder_id, course_id, category_id, parent_folder_id, name, created_by, created_at, updated_at
        FROM material_folders WHERE folder_id = ? AND course_id = ? AND category_id = ?
        """,
        (folder_id, course_id, category_id),
    ).fetchone()
    if not row:
        raise ValueError("The selected folder does not belong to this course category.")
    return row


def _folder_path(conn: sqlite3.Connection, folder_id: str | None) -> str:
    if folder_id is None:
        return ""
    names: list[str] = []
    current_id = folder_id
    while current_id:
        row = conn.execute(
            "SELECT name, parent_folder_id FROM material_folders WHERE folder_id = ?",
            (current_id,),
        ).fetchone()
        if not row:
            break
        names.append(row["name"])
        current_id = row["parent_folder_id"]
    return "/".join(reversed(names))


def _public_material(conn: sqlite3.Connection, row: sqlite3.Row) -> dict[str, Any]:
    data = dict(row)
    data["folder_path"] = _folder_path(conn, data.get("folder_id"))
    return data


def list_categories(course_id: str) -> list[dict[str, Any]]:
    with get_db_connection() as conn:
        rows = conn.execute(
            """
            SELECT c.category_id, c.name, c.sort_order,
                   COUNT(m.material_id) AS material_count
            FROM material_categories c
            LEFT JOIN course_materials m
              ON m.category_id = c.category_id AND m.course_id = ?
            GROUP BY c.category_id
            ORDER BY c.sort_order
            """,
            (course_id,),
        ).fetchall()
    return [dict(row) for row in rows]


def list_folder_tree(course_id: str, category_id: str) -> dict[str, Any]:
    with get_db_connection() as conn:
        category = _category(conn, category_id)
        rows = conn.execute(
            """
            SELECT f.folder_id, f.course_id, f.category_id, f.parent_folder_id, f.name,
                   COUNT(m.material_id) AS material_count
            FROM material_folders f
            LEFT JOIN course_materials m ON m.folder_id = f.folder_id
            WHERE f.course_id = ? AND f.category_id = ?
            GROUP BY f.folder_id
            ORDER BY lower(f.name), f.folder_id
            """,
            (course_id, category_id),
        ).fetchall()
        root_count = conn.execute(
            "SELECT COUNT(*) FROM course_materials WHERE course_id = ? AND category_id = ? AND folder_id IS NULL",
            (course_id, category_id),
        ).fetchone()[0]
        by_parent: dict[str | None, list[dict[str, Any]]] = {}
        for row in rows:
            item = dict(row)
            item["children"] = []
            by_parent.setdefault(row["parent_folder_id"], []).append(item)

        def branch(parent_id: str | None) -> list[dict[str, Any]]:
            result = by_parent.get(parent_id, [])
            for item in result:
                item["children"] = branch(item["folder_id"])
            return result

        return {
            "category_id": category["category_id"],
            "category_name": category["name"],
            "root_material_count": root_count,
            "folders": branch(None),
        }


def create_folder(
    *,
    course_id: str,
    category_id: str,
    parent_folder_id: str | None,
    name: str,
    actor_id: str,
    actor_role: str,
) -> dict[str, Any]:
    clean_name = _clean_label(name, "Folder name")
    folder_id = uuid.uuid4().hex
    now = _now()
    with get_db_connection(immediate=True) as conn:
        _category(conn, category_id)
        _folder(conn, parent_folder_id, course_id, category_id)
        duplicate = conn.execute(
            """
            SELECT 1 FROM material_folders
            WHERE course_id = ? AND category_id = ? AND parent_folder_id IS ? AND lower(name) = lower(?)
            """,
            (course_id, category_id, parent_folder_id, clean_name),
        ).fetchone()
        if duplicate:
            raise ValueError("A folder with that name already exists at this location.")
        conn.execute(
            """
            INSERT INTO material_folders
                (folder_id, course_id, category_id, parent_folder_id, name, created_by, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (folder_id, course_id, category_id, parent_folder_id, clean_name, actor_id, now, now),
        )
        _audit(conn, actor_id=actor_id, actor_role=actor_role, action="FOLDER_CREATED",
               resource=f"folder:{folder_id}", details={"name": clean_name, "category_id": category_id})
        return dict(conn.execute("SELECT * FROM material_folders WHERE folder_id = ?", (folder_id,)).fetchone())


def update_folder(
    *,
    folder_id: str,
    course_id: str,
    name: str | None,
    parent_folder_id: str | None,
    move_requested: bool,
    actor_id: str,
    actor_role: str,
) -> dict[str, Any]:
    with get_db_connection(immediate=True) as conn:
        current = conn.execute(
            "SELECT * FROM material_folders WHERE folder_id = ? AND course_id = ?",
            (folder_id, course_id),
        ).fetchone()
        if not current:
            raise LookupError("Folder was not found.")
        clean_name = _clean_label(name, "Folder name") if name is not None else current["name"]
        target_parent = parent_folder_id if move_requested else current["parent_folder_id"]
        if target_parent == folder_id:
            raise ValueError("A folder cannot be moved inside itself.")
        if target_parent is not None:
            _folder(conn, target_parent, course_id, current["category_id"])
            descendants = conn.execute(
                """
                WITH RECURSIVE descendants(folder_id) AS (
                    SELECT folder_id FROM material_folders WHERE parent_folder_id = ?
                    UNION ALL
                    SELECT f.folder_id FROM material_folders f
                    JOIN descendants d ON f.parent_folder_id = d.folder_id
                )
                SELECT folder_id FROM descendants
                """,
                (folder_id,),
            ).fetchall()
            if target_parent in {row["folder_id"] for row in descendants}:
                raise ValueError("A folder cannot be moved inside one of its subfolders.")
        duplicate = conn.execute(
            """
            SELECT 1 FROM material_folders
            WHERE course_id = ? AND category_id = ? AND parent_folder_id IS ?
              AND lower(name) = lower(?) AND folder_id != ?
            """,
            (course_id, current["category_id"], target_parent, clean_name, folder_id),
        ).fetchone()
        if duplicate:
            raise ValueError("A folder with that name already exists at this location.")
        conn.execute(
            "UPDATE material_folders SET name = ?, parent_folder_id = ?, updated_at = ? WHERE folder_id = ?",
            (clean_name, target_parent, _now(), folder_id),
        )
        _audit(conn, actor_id=actor_id, actor_role=actor_role, action="FOLDER_UPDATED",
               resource=f"folder:{folder_id}",
               details={"name": clean_name, "parent_folder_id": target_parent})
        return dict(conn.execute("SELECT * FROM material_folders WHERE folder_id = ?", (folder_id,)).fetchone())


def delete_folder(*, folder_id: str, course_id: str, actor_id: str, actor_role: str) -> None:
    with get_db_connection(immediate=True) as conn:
        row = conn.execute(
            "SELECT category_id FROM material_folders WHERE folder_id = ? AND course_id = ?",
            (folder_id, course_id),
        ).fetchone()
        if not row:
            raise LookupError("Folder was not found.")
        child = conn.execute("SELECT 1 FROM material_folders WHERE parent_folder_id = ? LIMIT 1", (folder_id,)).fetchone()
        material = conn.execute("SELECT 1 FROM course_materials WHERE folder_id = ? LIMIT 1", (folder_id,)).fetchone()
        if child or material:
            raise ValueError("Move or delete this folder's contents before deleting it.")
        conn.execute("DELETE FROM material_folders WHERE folder_id = ?", (folder_id,))
        _audit(conn, actor_id=actor_id, actor_role=actor_role, action="FOLDER_DELETED",
               resource=f"folder:{folder_id}", details={})


def list_materials(
    *,
    course_id: str,
    query: str | None = None,
    category_id: str | None = None,
    folder_id: str | None = None,
    recursive: bool = True,
    root_only: bool = False,
    chapter: int | None = None,
    lab: int | None = None,
    file_type: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> dict[str, Any]:
    clauses = ["m.course_id = ?"]
    params: list[Any] = [course_id]
    if query:
        clauses.append("(m.title LIKE ? ESCAPE '\\' OR m.description LIKE ? ESCAPE '\\')")
        escaped = query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        params.extend((f"%{escaped}%", f"%{escaped}%"))
    if folder_id:
        with get_db_connection() as conn:
            folder = conn.execute(
                "SELECT category_id FROM material_folders WHERE folder_id = ? AND course_id = ?",
                (folder_id, course_id),
            ).fetchone()
            if not folder:
                raise LookupError("Folder was not found.")
            if category_id and folder["category_id"] != category_id:
                raise ValueError("The selected folder does not belong to this category.")
    if category_id:
        with get_db_connection() as conn:
            _category(conn, category_id)
        clauses.append("m.category_id = ?")
        params.append(category_id)
    if chapter is not None:
        clauses.append("m.chapter = ?")
        params.append(chapter)
    if lab is not None:
        clauses.append("m.lab = ?")
        params.append(lab)
    if file_type:
        clauses.append("lower(m.extension) = ?")
        params.append(file_type.lower().lstrip("."))
    if folder_id:
        if recursive:
            clauses.append(
                """(m.folder_id IN (
                    WITH RECURSIVE descendants(folder_id) AS (
                        SELECT folder_id FROM material_folders WHERE folder_id = ? AND course_id = ?
                        UNION ALL
                        SELECT f.folder_id FROM material_folders f
                        JOIN descendants d ON f.parent_folder_id = d.folder_id
                    )
                    SELECT folder_id FROM descendants
                ) OR m.folder_id = ?)"""
            )
            params.extend((folder_id, course_id, folder_id))
        else:
            clauses.append("m.folder_id = ?")
            params.append(folder_id)
    elif root_only:
        clauses.append("m.folder_id IS NULL")
    where_sql = " AND ".join(clauses)
    with get_db_connection() as conn:
        rows = conn.execute(
            f"""
            SELECT m.*, c.name AS category_name, u.display_name AS uploader_name
            FROM course_materials m
            JOIN material_categories c ON c.category_id = m.category_id
            LEFT JOIN auth_users u ON u.user_id = m.uploader_id
            WHERE {where_sql}
            ORDER BY m.uploaded_at DESC, m.material_id
            LIMIT ? OFFSET ?
            """,
            (*params, limit, offset),
        ).fetchall()
        for row in rows:
            if row["folder_id"] and not conn.execute(
                "SELECT 1 FROM material_folders WHERE folder_id = ? AND course_id = ?",
                (row["folder_id"], course_id),
            ).fetchone():
                raise RuntimeError("Material folder relationship is inconsistent.")
        count = conn.execute(
            f"SELECT COUNT(*) FROM course_materials m WHERE {where_sql}",
            params,
        ).fetchone()[0]
        items = [_public_material(conn, row) for row in rows]
    return {"items": items, "count": count, "limit": limit, "offset": offset}


def get_material(material_id: str, course_id: str) -> dict[str, Any] | None:
    with get_db_connection() as conn:
        row = conn.execute(
            """
            SELECT m.*, c.name AS category_name, u.display_name AS uploader_name
            FROM course_materials m
            JOIN material_categories c ON c.category_id = m.category_id
            LEFT JOIN auth_users u ON u.user_id = m.uploader_id
            WHERE m.material_id = ? AND m.course_id = ?
            """,
            (material_id, course_id),
        ).fetchone()
        return _public_material(conn, row) if row else None


def material_file_path(material: dict[str, Any]) -> Path:
    path = _stored_path(material["storage_key"])
    if not path.is_file():
        raise FileNotFoundError("The stored course material is missing.")
    return path


def create_materials(
    *,
    course_id: str,
    category_id: str,
    folder_id: str | None,
    title: str | None,
    description: str,
    chapter: int | None,
    lab: int | None,
    uploads: list[tuple[str | None, bytes]],
    actor_id: str,
    actor_role: str,
) -> list[dict[str, Any]]:
    if not uploads or len(uploads) > MAX_BATCH_FILES:
        raise ValueError(f"Select between 1 and {MAX_BATCH_FILES} files per upload.")
    if sum(len(content) for _, content in uploads) > MAX_BATCH_BYTES:
        raise ValueError(f"The total upload must be no larger than {MAX_BATCH_BYTES // (1024 * 1024)} MB.")
    if chapter is not None and not 1 <= chapter <= 14:
        raise ValueError("Chapter must be between 1 and 14.")
    if lab is not None and not 1 <= lab <= 14:
        raise ValueError("Lab must be between 1 and 14.")
    clean_description = description.strip()
    if len(clean_description) > 4000:
        raise ValueError("Description must be 4000 characters or fewer.")

    entries: list[dict[str, Any]] = []
    root = _materials_root()
    root.mkdir(parents=True, exist_ok=True)
    try:
        for upload_name, content in uploads:
            safe_name, extension, detected_type = validate_upload(upload_name, content)
            item_title = title.strip() if title and len(uploads) == 1 else Path(safe_name).stem
            item_title = _clean_label(item_title, "Title", 200)
            material_id = uuid.uuid4().hex
            storage_key = f"{uuid.uuid4().hex}.{extension}"
            path = _stored_path(storage_key)
            with path.open("xb") as target:
                target.write(content)
            entries.append({
                "material_id": material_id,
                "course_id": course_id,
                "title": item_title,
                "description": clean_description,
                "category_id": category_id,
                "folder_id": folder_id,
                "chapter": chapter,
                "lab": lab,
                "storage_key": storage_key,
                "original_filename": safe_name,
                "file_type": detected_type,
                "extension": extension,
                "size_bytes": len(content),
                "checksum_sha256": hashlib.sha256(content).hexdigest(),
                "uploader_id": actor_id,
                "uploaded_at": _now(),
                "updated_at": _now(),
            })
        with get_db_connection(immediate=True) as conn:
            _category(conn, category_id)
            _folder(conn, folder_id, course_id, category_id)
            for item in entries:
                conn.execute(
                    """
                    INSERT INTO course_materials
                        (material_id, course_id, title, description, category_id, folder_id,
                         chapter, lab, storage_key, original_filename, file_type, extension,
                         size_bytes, checksum_sha256, uploader_id, uploaded_at, updated_at)
                    VALUES (:material_id, :course_id, :title, :description, :category_id, :folder_id,
                            :chapter, :lab, :storage_key, :original_filename, :file_type, :extension,
                            :size_bytes, :checksum_sha256, :uploader_id, :uploaded_at, :updated_at)
                    """,
                    item,
                )
                _audit(conn, actor_id=actor_id, actor_role=actor_role, action="FILE_UPLOADED",
                       resource=f"material:{item['material_id']}",
                       details={"title": item["title"], "filename": item["original_filename"],
                                "category_id": category_id, "checksum_sha256": item["checksum_sha256"]})
            rows = [
                _public_material(conn, conn.execute(
                    """
                    SELECT m.*, c.name AS category_name, u.display_name AS uploader_name
                    FROM course_materials m JOIN material_categories c ON c.category_id = m.category_id
                    LEFT JOIN auth_users u ON u.user_id = m.uploader_id WHERE m.material_id = ?
                    """,
                    (item["material_id"],),
                ).fetchone())
                for item in entries
            ]
        return rows
    except Exception:
        for item in entries:
            try:
                _stored_path(item["storage_key"]).unlink(missing_ok=True)
            except OSError:
                logger.exception("Could not clean staged course material %s", item["storage_key"])
        raise


def update_material(
    *,
    material_id: str,
    course_id: str,
    actor_id: str,
    actor_role: str,
    title: str | None = None,
    description: str | None = None,
    category_id: str | None = None,
    folder_id: str | None = None,
    folder_supplied: bool = False,
    chapter: int | None = None,
    chapter_supplied: bool = False,
    lab: int | None = None,
    lab_supplied: bool = False,
) -> dict[str, Any]:
    with get_db_connection(immediate=True) as conn:
        row = conn.execute(
            "SELECT * FROM course_materials WHERE material_id = ? AND course_id = ?",
            (material_id, course_id),
        ).fetchone()
        if not row:
            raise LookupError("Course material was not found.")
        new_category = category_id or row["category_id"]
        _category(conn, new_category)
        new_folder = folder_id if folder_supplied else row["folder_id"]
        _folder(conn, new_folder, course_id, new_category)
        new_title = _clean_label(title, "Title", 200) if title is not None else row["title"]
        new_description = description.strip() if description is not None else row["description"]
        if len(new_description) > 4000:
            raise ValueError("Description must be 4000 characters or fewer.")
        new_chapter = chapter if chapter_supplied else row["chapter"]
        new_lab = lab if lab_supplied else row["lab"]
        if new_chapter is not None and not 1 <= new_chapter <= 14:
            raise ValueError("Chapter must be between 1 and 14.")
        if new_lab is not None and not 1 <= new_lab <= 14:
            raise ValueError("Lab must be between 1 and 14.")
        conn.execute(
            """
            UPDATE course_materials SET title = ?, description = ?, category_id = ?, folder_id = ?,
                chapter = ?, lab = ?, updated_at = ?
            WHERE material_id = ? AND course_id = ?
            """,
            (new_title, new_description, new_category, new_folder, new_chapter, new_lab, _now(), material_id, course_id),
        )
        _audit(conn, actor_id=actor_id, actor_role=actor_role, action="FILE_METADATA_UPDATED",
               resource=f"material:{material_id}",
               details={"title": new_title, "category_id": new_category, "folder_id": new_folder})
        updated = conn.execute(
            """
            SELECT m.*, c.name AS category_name, u.display_name AS uploader_name
            FROM course_materials m JOIN material_categories c ON c.category_id = m.category_id
            LEFT JOIN auth_users u ON u.user_id = m.uploader_id
            WHERE m.material_id = ?
            """,
            (material_id,),
        ).fetchone()
        return _public_material(conn, updated)


def replace_material_file(
    *,
    material_id: str,
    course_id: str,
    filename: str | None,
    content: bytes,
    actor_id: str,
    actor_role: str,
) -> dict[str, Any]:
    safe_name, extension, detected_type = validate_upload(filename, content)
    new_key = f"{uuid.uuid4().hex}.{extension}"
    new_path = _stored_path(new_key)
    _materials_root().mkdir(parents=True, exist_ok=True)
    with new_path.open("xb") as target:
        target.write(content)
    old_key: str | None = None
    committed = False
    try:
        with get_db_connection(immediate=True) as conn:
            old = conn.execute(
                "SELECT storage_key FROM course_materials WHERE material_id = ? AND course_id = ?",
                (material_id, course_id),
            ).fetchone()
            if not old:
                raise LookupError("Course material was not found.")
            old_key = old["storage_key"]
            conn.execute(
                """
                UPDATE course_materials SET storage_key = ?, original_filename = ?, file_type = ?,
                    extension = ?, size_bytes = ?, checksum_sha256 = ?, updated_at = ?
                WHERE material_id = ? AND course_id = ?
                """,
                (new_key, safe_name, detected_type, extension, len(content),
                 hashlib.sha256(content).hexdigest(), _now(), material_id, course_id),
            )
            _audit(conn, actor_id=actor_id, actor_role=actor_role, action="FILE_REPLACED",
                   resource=f"material:{material_id}",
                   details={"filename": safe_name, "checksum_sha256": hashlib.sha256(content).hexdigest()})
            updated = conn.execute(
                """
                SELECT m.*, c.name AS category_name, u.display_name AS uploader_name
                FROM course_materials m JOIN material_categories c ON c.category_id = m.category_id
                LEFT JOIN auth_users u ON u.user_id = m.uploader_id WHERE m.material_id = ?
                """,
                (material_id,),
            ).fetchone()
        committed = True
        if old_key and old_key != new_key:
            try:
                _stored_path(old_key).unlink(missing_ok=True)
            except OSError:
                logger.exception("Replacement committed, but old course material cleanup failed: %s", old_key)
        material = get_material(material_id, course_id)
        if material is None:
            raise RuntimeError("Replaced course material was not found after its update.")
        return material
    except Exception:
        if not committed:
            try:
                new_path.unlink(missing_ok=True)
            except OSError:
                logger.exception("Could not clean replaced course material %s", new_key)
        raise


def delete_material(
    *,
    material_id: str,
    course_id: str,
    actor_id: str,
    actor_role: str,
) -> str:
    with get_db_connection(immediate=True) as conn:
        row = conn.execute(
            "SELECT storage_key FROM course_materials WHERE material_id = ? AND course_id = ?",
            (material_id, course_id),
        ).fetchone()
        if not row:
            raise LookupError("Course material was not found.")
        conn.execute(
            "DELETE FROM course_materials WHERE material_id = ? AND course_id = ?",
            (material_id, course_id),
        )
        _audit(conn, actor_id=actor_id, actor_role=actor_role, action="FILE_DELETED",
               resource=f"material:{material_id}", details={})
        storage_key = row["storage_key"]
    path = _stored_path(storage_key)
    try:
        path.unlink(missing_ok=True)
    except OSError as exc:
        logger.exception("Course material metadata deleted but stored file cleanup failed: %s", storage_key)
        raise OSError("Material was removed from the library, but its stored file needs administrator cleanup.") from exc
    return storage_key


def material_preview(material: dict[str, Any]) -> dict[str, Any]:
    extension = material["extension"]
    if extension in {"pdf", "png", "jpg", "jpeg", "gif", "webp"}:
        return {"kind": "inline", "url": f"/api/course-materials/{material['material_id']}/content"}
    if extension not in {"docx", "pptx", "txt", "md"}:
        return {"kind": "download", "text": "Preview is not available for this file type. Download the original file."}
    try:
        from app.knowledge.extractors import DocumentExtractorRegistry
        from app.knowledge.models import DiscoveredDocument

        path = material_file_path(material)
        document = DiscoveredDocument(
            document_id=material["material_id"],
            course_code=material["course_id"],
            course_name=material["course_id"],
            chapter=material.get("chapter"),
            source_filename=material["original_filename"],
            source_relative_path=material["folder_path"],
            source_path=str(path),
            document_type=extension,
            file_size_bytes=material["size_bytes"],
            content_hash=material["checksum_sha256"],
            last_modified=path.stat().st_mtime,
            category=material["category_name"],
            lab=material.get("lab"),
        )
        sections = DocumentExtractorRegistry().extract(document)
        text = "\n\n".join(section.content for section in sections)
        return {"kind": "text", "text": text[:20000] or "No text could be extracted for preview."}
    except Exception as exc:
        logger.exception("Course material preview failed for %s.", material["material_id"])
        raise RuntimeError("Could not generate the course material preview.") from exc


def safe_content_type(extension: str) -> str:
    return _MIME_TYPES.get(extension) or mimetypes.guess_type(f"file.{extension}")[0] or "application/octet-stream"
