"""Authenticated course material library endpoints."""

from __future__ import annotations

from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from app.auth import AuthenticatedUser, get_current_user, require_course_access, require_roles
from app.knowledge.service import knowledge_service
from app.models.common import APIEnvelope
from app.services import course_materials

router = APIRouter(prefix="/api/course-materials", tags=["Course Materials"])
_DEFAULT_COURSE = "26ECAC401"


class FolderCreate(BaseModel):
    course_id: str = Field(default=_DEFAULT_COURSE, min_length=1, max_length=80)
    category_id: str = Field(min_length=1, max_length=80)
    parent_folder_id: str | None = None
    name: str = Field(min_length=1, max_length=120)


class FolderUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    parent_folder_id: str | None = None


class MaterialUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=4000)
    category_id: str | None = None
    folder_id: str | None = None
    chapter: int | None = Field(default=None, ge=1, le=14)
    lab: int | None = Field(default=None, ge=1, le=14)


def _read_access(user: AuthenticatedUser, course_id: str) -> None:
    require_course_access(user, course_id)


def _write_access(user: AuthenticatedUser, course_id: str) -> None:
    if user.role != "FACULTY":
        raise HTTPException(status_code=403, detail="Only authorized faculty can manage course materials.")
    require_course_access(user, course_id)


def _material_or_404(material_id: str, course_id: str) -> dict:
    material = course_materials.get_material(material_id, course_id)
    if material is None:
        raise HTTPException(status_code=404, detail="Course material was not found.")
    return material


def _api_material(material: dict) -> dict:
    result = dict(material)
    result.pop("storage_key", None)
    return result


def _service_error(exc: Exception) -> HTTPException:
    if isinstance(exc, LookupError):
        return HTTPException(status_code=404, detail=str(exc))
    if isinstance(exc, ValueError):
        return HTTPException(status_code=400, detail=str(exc))
    if isinstance(exc, FileNotFoundError):
        return HTTPException(status_code=404, detail=str(exc))
    if isinstance(exc, OSError):
        return HTTPException(status_code=500, detail=str(exc))
    raise exc


def _refresh_knowledge_index() -> None:
    knowledge_service.initialize(force_reload=True)


@router.get("/categories", response_model=APIEnvelope)
async def categories(
    course_id: str = Query(default=_DEFAULT_COURSE, min_length=1, max_length=80),
    user: AuthenticatedUser = Depends(get_current_user),
):
    _read_access(user, course_id)
    return APIEnvelope(success=True, data=course_materials.list_categories(course_id), trace_id="materials-categories")


@router.get("/folders", response_model=APIEnvelope)
async def folders(
    category_id: str = Query(min_length=1, max_length=80),
    course_id: str = Query(default=_DEFAULT_COURSE, min_length=1, max_length=80),
    user: AuthenticatedUser = Depends(get_current_user),
):
    _read_access(user, course_id)
    try:
        data = course_materials.list_folder_tree(course_id, category_id)
    except ValueError as exc:
        raise _service_error(exc)
    return APIEnvelope(success=True, data=data, trace_id="materials-folders")


@router.post("/folders", response_model=APIEnvelope)
async def create_folder(
    request: FolderCreate,
    user: AuthenticatedUser = Depends(get_current_user),
):
    _write_access(user, request.course_id)
    try:
        data = course_materials.create_folder(
            course_id=request.course_id,
            category_id=request.category_id,
            parent_folder_id=request.parent_folder_id,
            name=request.name,
            actor_id=user.user_id,
            actor_role=user.role,
        )
    except (ValueError, LookupError) as exc:
        raise _service_error(exc)
    return APIEnvelope(success=True, data=data, trace_id=f"folder-created-{data['folder_id']}")


@router.patch("/folders/{folder_id}", response_model=APIEnvelope)
async def update_folder(
    folder_id: str,
    request: FolderUpdate,
    course_id: str = Query(default=_DEFAULT_COURSE, min_length=1, max_length=80),
    user: AuthenticatedUser = Depends(get_current_user),
):
    _write_access(user, course_id)
    if not request.model_fields_set:
        raise HTTPException(status_code=400, detail="Provide a folder name or parent folder.")
    try:
        data = course_materials.update_folder(
            folder_id=folder_id,
            course_id=course_id,
            name=request.name,
            parent_folder_id=request.parent_folder_id,
            move_requested="parent_folder_id" in request.model_fields_set,
            actor_id=user.user_id,
            actor_role=user.role,
        )
        _refresh_knowledge_index()
    except (ValueError, LookupError) as exc:
        raise _service_error(exc)
    return APIEnvelope(success=True, data=data, trace_id=f"folder-updated-{folder_id}")


@router.delete("/folders/{folder_id}", response_model=APIEnvelope)
async def delete_folder(
    folder_id: str,
    course_id: str = Query(default=_DEFAULT_COURSE, min_length=1, max_length=80),
    user: AuthenticatedUser = Depends(get_current_user),
):
    _write_access(user, course_id)
    try:
        course_materials.delete_folder(
            folder_id=folder_id,
            course_id=course_id,
            actor_id=user.user_id,
            actor_role=user.role,
        )
    except (ValueError, LookupError) as exc:
        raise _service_error(exc)
    return APIEnvelope(success=True, data={"deleted": True, "folder_id": folder_id}, trace_id=f"folder-deleted-{folder_id}")


@router.get("/materials", response_model=APIEnvelope)
async def list_materials(
    course_id: str = Query(default=_DEFAULT_COURSE, min_length=1, max_length=80),
    query: str | None = Query(default=None, max_length=200),
    category_id: str | None = Query(default=None, max_length=80),
    folder_id: str | None = Query(default=None, max_length=80),
    recursive: bool = True,
    root_only: bool = False,
    chapter: int | None = Query(default=None, ge=1, le=14),
    lab: int | None = Query(default=None, ge=1, le=14),
    file_type: str | None = Query(default=None, max_length=10),
    limit: int = Query(default=100, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    user: AuthenticatedUser = Depends(get_current_user),
):
    _read_access(user, course_id)
    try:
        data = course_materials.list_materials(
            course_id=course_id,
            query=query,
            category_id=category_id,
            folder_id=folder_id,
            recursive=recursive,
            root_only=root_only,
            chapter=chapter,
            lab=lab,
            file_type=file_type,
            limit=limit,
            offset=offset,
        )
    except (ValueError, LookupError) as exc:
        raise _service_error(exc)
    data["items"] = [_api_material(item) for item in data["items"]]
    return APIEnvelope(success=True, data=data, trace_id="materials-list")


@router.post("/materials", response_model=APIEnvelope)
async def upload_materials(
    course_id: str = Form(default=_DEFAULT_COURSE, min_length=1, max_length=80),
    category_id: str = Form(..., min_length=1, max_length=80),
    folder_id: str | None = Form(default=None),
    title: str | None = Form(default=None, max_length=200),
    description: str = Form(default="", max_length=4000),
    chapter: int | None = Form(default=None, ge=1, le=14),
    lab: int | None = Form(default=None, ge=1, le=14),
    files: list[UploadFile] = File(...),
    user: AuthenticatedUser = Depends(get_current_user),
):
    _write_access(user, course_id)
    if len(files) > course_materials.MAX_BATCH_FILES:
        raise HTTPException(status_code=413, detail=f"Upload no more than {course_materials.MAX_BATCH_FILES} files at once.")
    uploads: list[tuple[str | None, bytes]] = []
    try:
        for upload in files:
            content = await upload.read(course_materials.MAX_UPLOAD_BYTES + 1)
            if len(content) > course_materials.MAX_UPLOAD_BYTES:
                raise HTTPException(
                    status_code=413,
                    detail=f"Each file must be {course_materials.MAX_UPLOAD_BYTES // (1024 * 1024)} MB or smaller.",
                )
            uploads.append((upload.filename, content))
            if sum(len(item[1]) for item in uploads) > course_materials.MAX_BATCH_BYTES:
                raise HTTPException(
                    status_code=413,
                    detail=f"The total upload must be no larger than {course_materials.MAX_BATCH_BYTES // (1024 * 1024)} MB.",
                )
    finally:
        for upload in files:
            await upload.close()
    try:
        items = course_materials.create_materials(
            course_id=course_id,
            category_id=category_id,
            folder_id=folder_id,
            title=title,
            description=description,
            chapter=chapter,
            lab=lab,
            uploads=uploads,
            actor_id=user.user_id,
            actor_role=user.role,
        )
        _refresh_knowledge_index()
    except (ValueError, LookupError, OSError) as exc:
        raise _service_error(exc)
    return APIEnvelope(
        success=True,
        data={"items": [_api_material(item) for item in items], "count": len(items)},
        trace_id="materials-uploaded",
    )


@router.get("/materials/{material_id}", response_model=APIEnvelope)
async def get_material(
    material_id: str,
    course_id: str = Query(default=_DEFAULT_COURSE, min_length=1, max_length=80),
    user: AuthenticatedUser = Depends(get_current_user),
):
    _read_access(user, course_id)
    return APIEnvelope(
        success=True,
        data=_api_material(_material_or_404(material_id, course_id)),
        trace_id=f"material-{material_id}",
    )


@router.patch("/materials/{material_id}", response_model=APIEnvelope)
async def update_material(
    material_id: str,
    request: MaterialUpdate,
    course_id: str = Query(default=_DEFAULT_COURSE, min_length=1, max_length=80),
    user: AuthenticatedUser = Depends(get_current_user),
):
    _write_access(user, course_id)
    fields = request.model_fields_set
    if not fields:
        raise HTTPException(status_code=400, detail="Provide at least one material field to update.")
    try:
        data = course_materials.update_material(
            material_id=material_id,
            course_id=course_id,
            actor_id=user.user_id,
            actor_role=user.role,
            title=request.title,
            description=request.description,
            category_id=request.category_id,
            folder_id=request.folder_id,
            folder_supplied="folder_id" in fields,
            chapter=request.chapter,
            chapter_supplied="chapter" in fields,
            lab=request.lab,
            lab_supplied="lab" in fields,
        )
        _refresh_knowledge_index()
    except (ValueError, LookupError, OSError) as exc:
        raise _service_error(exc)
    return APIEnvelope(success=True, data=_api_material(data), trace_id=f"material-updated-{material_id}")


@router.put("/materials/{material_id}/file", response_model=APIEnvelope)
async def replace_material_file(
    material_id: str,
    file: UploadFile = File(...),
    course_id: str = Query(default=_DEFAULT_COURSE, min_length=1, max_length=80),
    user: AuthenticatedUser = Depends(get_current_user),
):
    _write_access(user, course_id)
    try:
        content = await file.read(course_materials.MAX_UPLOAD_BYTES + 1)
        if len(content) > course_materials.MAX_UPLOAD_BYTES:
            raise HTTPException(
                status_code=413,
                detail=f"Each file must be {course_materials.MAX_UPLOAD_BYTES // (1024 * 1024)} MB or smaller.",
            )
        data = course_materials.replace_material_file(
            material_id=material_id,
            course_id=course_id,
            filename=file.filename,
            content=content,
            actor_id=user.user_id,
            actor_role=user.role,
        )
        _refresh_knowledge_index()
    except (ValueError, LookupError, FileNotFoundError, OSError) as exc:
        raise _service_error(exc)
    finally:
        await file.close()
    return APIEnvelope(success=True, data=_api_material(data), trace_id=f"material-replaced-{material_id}")


@router.delete("/materials/{material_id}", response_model=APIEnvelope)
async def delete_material(
    material_id: str,
    course_id: str = Query(default=_DEFAULT_COURSE, min_length=1, max_length=80),
    user: AuthenticatedUser = Depends(get_current_user),
):
    _write_access(user, course_id)
    try:
        course_materials.delete_material(
            material_id=material_id,
            course_id=course_id,
            actor_id=user.user_id,
            actor_role=user.role,
        )
    except OSError as exc:
        _refresh_knowledge_index()
        raise _service_error(exc)
    except LookupError as exc:
        raise _service_error(exc)
    _refresh_knowledge_index()
    return APIEnvelope(success=True, data={"deleted": True, "material_id": material_id}, trace_id=f"material-deleted-{material_id}")


@router.get("/materials/{material_id}/preview", response_model=APIEnvelope)
async def preview_material(
    material_id: str,
    course_id: str = Query(default=_DEFAULT_COURSE, min_length=1, max_length=80),
    user: AuthenticatedUser = Depends(get_current_user),
):
    _read_access(user, course_id)
    material = _material_or_404(material_id, course_id)
    try:
        data = course_materials.material_preview(material)
    except (ValueError, FileNotFoundError, OSError) as exc:
        raise _service_error(exc)
    return APIEnvelope(success=True, data=data, trace_id=f"material-preview-{material_id}")


@router.get("/materials/{material_id}/content")
async def material_content(
    material_id: str,
    download: bool = False,
    course_id: str = Query(default=_DEFAULT_COURSE, min_length=1, max_length=80),
    user: AuthenticatedUser = Depends(get_current_user),
):
    _read_access(user, course_id)
    material = _material_or_404(material_id, course_id)
    try:
        path = course_materials.material_file_path(material)
    except (ValueError, FileNotFoundError, OSError) as exc:
        raise _service_error(exc)
    disposition = "attachment" if download else "inline"
    encoded_name = quote(material["original_filename"], safe="")
    return FileResponse(
        path=str(path),
        media_type=course_materials.safe_content_type(material["extension"]),
        headers={"Content-Disposition": f"{disposition}; filename*=UTF-8''{encoded_name}"},
        filename=None,
    )
