"""Knowledge listing, folder navigation, original-file download, upload, preview, and retrieval endpoints."""

from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from app.auth import AuthenticatedUser, get_current_user, require_course_access, require_roles
from app.knowledge.catalog import KnowledgeFileCatalog, KnowledgeSearchRequest
from app.knowledge.service import knowledge_service
from app.models.common import APIEnvelope, ErrorDetail
from app.services.audit_service import audit_service
from config import settings

router = APIRouter(prefix="/api/knowledge", tags=["Knowledge & Notes"])
_catalog = KnowledgeFileCatalog(Path(settings.knowledge_root))


def _require_knowledge_course_access(
    user: AuthenticatedUser = Depends(get_current_user),
) -> AuthenticatedUser:
    require_course_access(user, "26ECAC401")
    return user


class MoveFileRequest(BaseModel):
    destination_folder: str = Field(min_length=1)


class RenameFileRequest(BaseModel):
    new_filename: str = Field(min_length=1)


class CreateFolderRequest(BaseModel):
    folder_path: str = Field(min_length=1)


@router.get("/tree", response_model=APIEnvelope)
async def get_knowledge_tree(user: AuthenticatedUser = Depends(_require_knowledge_course_access)):
    """Retrieve full hierarchical folder tree of directories and file counts."""
    tree = _catalog.get_folder_tree()
    return APIEnvelope(success=True, data=tree, trace_id="knowledge-tree")


@router.get("/files", response_model=APIEnvelope)
async def list_knowledge_files(
    q: Optional[str] = Query(default=None),
    folder: Optional[str] = Query(default=None),
    file_format: Optional[str] = Query(default=None, alias="format"),
    chapter: Optional[int] = Query(default=None),
    user: AuthenticatedUser = Depends(_require_knowledge_course_access),
):
    """List files with optional text query, folder filter, file extension filter, or chapter filter."""
    files = _catalog.list_files(query=q, folder=folder, format_filter=file_format, chapter=chapter)
    return APIEnvelope(
        success=True,
        data={
            "knowledge_root": str(Path(settings.knowledge_root).resolve()),
            "count": len(files),
            "files": [f.model_dump() for f in files],
        },
        trace_id="knowledge-files",
    )


@router.get("/files/{file_id}", response_model=APIEnvelope)
async def get_knowledge_file(
    file_id: str,
    user: AuthenticatedUser = Depends(_require_knowledge_course_access),
):
    """Retrieve metadata for a specific knowledge file."""
    found = _catalog.get_file(file_id)
    if not found:
        raise HTTPException(status_code=404, detail="Knowledge file was not found or is outside the approved knowledge folder.")
    record, _path = found
    return APIEnvelope(success=True, data=record.model_dump(), trace_id=f"knowledge-{file_id}")


@router.get("/files/{file_id}/preview", response_model=APIEnvelope)
async def preview_knowledge_file(
    file_id: str,
    user: AuthenticatedUser = Depends(_require_knowledge_course_access),
):
    """Generate preview content and excerpt for the document preview drawer."""
    try:
        preview = _catalog.preview_file(file_id)
        return APIEnvelope(success=True, data=preview, trace_id=f"preview-{file_id}")
    except ValueError as val_err:
        raise HTTPException(status_code=404, detail=str(val_err))


@router.get("/files/{file_id}/download")
async def download_knowledge_file(
    file_id: str,
    user: AuthenticatedUser = Depends(_require_knowledge_course_access),
):
    """Stream original binary bytes of the file with secure Content-Disposition header."""
    if "/" in file_id or "\\" in file_id or ".." in file_id:
        raise HTTPException(status_code=400, detail="Invalid file identifier.")
    found = _catalog.get_file(file_id)
    if not found:
        raise HTTPException(status_code=404, detail="Knowledge file was not found or is no longer available.")
    record, path = found
    if not path.is_file():
        raise HTTPException(status_code=404, detail="The original file is missing from disk.")
    return FileResponse(
        path=str(path),
        media_type=record.content_type,
        filename=record.filename,
        headers={"Content-Disposition": _catalog.content_disposition(record.filename)},
    )


@router.post("/files/upload", response_model=APIEnvelope)
async def upload_knowledge_file(
    file: UploadFile = File(...),
    folder: str = Form(default="01_Notes/Chapter_1"),
    user: AuthenticatedUser = Depends(require_roles("FACULTY", "ADMIN")),
):
    """Faculty upload a new course material into the designated knowledge folder."""
    require_course_access(user, "26ECAC401")
    content = await file.read()
    try:
        record, is_duplicate, duplicate_of = _catalog.save_file(folder=folder, filename=file.filename, content=content)
        # Re-index to include newly added content
        knowledge_service.initialize(force_reload=True)

        audit_service.log_event(
            event_type="KNOWLEDGE_FILE_UPLOADED",
            actor=user.user_id,
            actor_role=user.role,
            resource=f"file:{record.relative_path}",
            action="UPLOAD_FILE",
            outcome="SUCCESS",
            details={"filename": record.filename, "size": record.size_bytes, "is_duplicate": is_duplicate},
        )

        return APIEnvelope(
            success=True,
            data={
                "record": record.model_dump(),
                "is_duplicate": is_duplicate,
                "duplicate_of": duplicate_of,
                "notice": "File uploaded and indexed for course knowledge retrieval.",
            },
            trace_id=f"upload-{record.file_id}",
        )
    except ValueError as val_err:
        raise HTTPException(status_code=400, detail=str(val_err))


@router.post("/files/{file_id}/move", response_model=APIEnvelope)
async def move_knowledge_file(
    file_id: str,
    request: MoveFileRequest,
    user: AuthenticatedUser = Depends(require_roles("FACULTY", "ADMIN")),
):
    """Faculty move a file between folders."""
    require_course_access(user, "26ECAC401")
    try:
        record = _catalog.move_file(file_id=file_id, dest_folder=request.destination_folder)
        knowledge_service.initialize(force_reload=True)
        return APIEnvelope(success=True, data=record.model_dump(), trace_id=f"move-{file_id}")
    except ValueError as val_err:
        raise HTTPException(status_code=400, detail=str(val_err))


@router.post("/files/{file_id}/rename", response_model=APIEnvelope)
async def rename_knowledge_file(
    file_id: str,
    request: RenameFileRequest,
    user: AuthenticatedUser = Depends(require_roles("FACULTY", "ADMIN")),
):
    """Faculty rename a file."""
    require_course_access(user, "26ECAC401")
    try:
        record = _catalog.rename_file(file_id=file_id, new_name=request.new_filename)
        knowledge_service.initialize(force_reload=True)
        return APIEnvelope(success=True, data=record.model_dump(), trace_id=f"rename-{file_id}")
    except ValueError as val_err:
        raise HTTPException(status_code=400, detail=str(val_err))


@router.delete("/files/{file_id}", response_model=APIEnvelope)
async def delete_knowledge_file(
    file_id: str,
    user: AuthenticatedUser = Depends(require_roles("FACULTY", "ADMIN")),
):
    """Faculty delete a file (immediately removed from disk and retrieval index)."""
    require_course_access(user, "26ECAC401")
    found = _catalog.get_file(file_id)
    if not found:
        raise HTTPException(status_code=404, detail="File not found.")
    record, _ = found

    success = _catalog.delete_file(file_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete file from disk.")

    # Re-index to ensure deleted document does not remain as misleading search results (Requirement 17)
    knowledge_service.initialize(force_reload=True)

    audit_service.log_event(
        event_type="KNOWLEDGE_FILE_DELETED",
        actor=user.user_id,
        actor_role=user.role,
        resource=f"file:{record.relative_path}",
        action="DELETE_FILE",
        outcome="DELETED",
        details={"filename": record.filename},
    )

    return APIEnvelope(
        success=True,
        data={"deleted": True, "file_id": file_id, "filename": record.filename},
        trace_id=f"del-{file_id}",
    )


@router.post("/reindex", response_model=APIEnvelope)
async def reindex_knowledge(user: AuthenticatedUser = Depends(require_roles("FACULTY", "ADMIN"))):
    """Force re-indexing of all documents across the knowledge folder structure."""
    require_course_access(user, "26ECAC401")
    stats = knowledge_service.initialize(force_reload=True)
    return APIEnvelope(
        success=True,
        data={
            "indexed_documents": stats.total_documents,
            "indexed_chunks": stats.total_chunks,
            "chapters_indexed": stats.chapters_indexed,
            "total_words": stats.total_words,
        },
        trace_id="reindex-complete",
    )


@router.get("/stats", response_model=APIEnvelope)
async def knowledge_stats(user: AuthenticatedUser = Depends(_require_knowledge_course_access)):
    """Retrieve index statistics and downloadable file counts."""
    stats = knowledge_service.get_stats()
    files = _catalog.list_files()
    return APIEnvelope(
        success=True,
        data={
            "downloadable_files": len(files),
            "indexed_documents": stats.total_documents,
            "indexed_chunks": stats.total_chunks,
            "chapters_indexed": stats.chapters_indexed,
            "total_words": stats.total_words,
            "knowledge_root": str(Path(settings.knowledge_root).resolve()),
        },
        trace_id="knowledge-stats",
    )


@router.post("/search", response_model=APIEnvelope)
async def search_knowledge(
    request: KnowledgeSearchRequest,
    user: AuthenticatedUser = Depends(get_current_user),
):
    """Retrieve high-precision grounded passages from course materials."""
    require_course_access(user, request.course_id)
    result = knowledge_service.search(
        query=request.query,
        course_id=request.course_id,
        chapter=request.chapter,
        top_k=request.top_k,
    )
    payload = result.model_dump()
    if result.match_count == 0:
        payload["notice"] = (
            "The available course notes do not establish an answer to this query. "
            "No lecture content was invented."
        )
    return APIEnvelope(success=True, data=payload, trace_id="knowledge-search")


@router.get("/health-detail", response_model=APIEnvelope)
async def knowledge_health(user: AuthenticatedUser = Depends(_require_knowledge_course_access)):
    """Detailed health check of knowledge repository root and index."""
    root = Path(settings.knowledge_root)
    return APIEnvelope(
        success=True,
        data={
            "root_exists": root.exists(),
            "file_count": len(_catalog.list_files()),
        },
        trace_id="knowledge-health",
        error=None if root.exists() else ErrorDetail(
            code="KNOWLEDGE_ROOT_MISSING",
            message=f"Knowledge folder not found at {root}",
        ),
    )
