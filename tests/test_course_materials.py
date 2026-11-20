"""Database-backed course materials library and retrieval integration tests."""

from io import BytesIO
from zipfile import ZipFile
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.data.db import get_db_connection
from app.main import app
from app.services.auth_service import create_user
from app.knowledge.service import knowledge_service
from app.knowledge.service import KnowledgeService

_PASSWORD = "materials-test-password"
_COURSE = "26ECAC401"


@pytest.fixture(scope="module", autouse=True)
def material_test_accounts():
    with get_db_connection(immediate=True) as conn:
        conn.execute(
            """
            INSERT OR IGNORE INTO students (id, name, email, course_id, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            ("cm-outside-student", "Outside Student", "outside@test.invalid", "OTHER-COURSE",
             datetime.now(timezone.utc).isoformat()),
        )
    accounts = (
        ("cm-faculty", "cm-faculty@test.invalid", "FACULTY", None, [_COURSE]),
        ("cm-outside-faculty", "cm-outside-faculty@test.invalid", "FACULTY", None, ["OTHER-COURSE"]),
        ("cm-admin", "cm-admin@test.invalid", "ADMIN", None, []),
        ("cm-student", "cm-student@test.invalid", "STUDENT", "std-004", []),
        ("cm-outside-student", "cm-outside-student@test.invalid", "STUDENT", "cm-outside-student", []),
    )
    for user_id, email, role, student_id, scopes in accounts:
        create_user(
            user_id=user_id,
            email=email,
            display_name=user_id,
            password=_PASSWORD,
            role=role,
            student_id=student_id,
            course_scopes=scopes,
        )


def _client(email: str | None = None) -> TestClient:
    client = TestClient(app)
    if email:
        response = client.post("/api/auth/login", json={"email": email, "password": _PASSWORD})
        assert response.status_code == 200, response.text
    return client


def _faculty() -> TestClient:
    return _client("cm-faculty@test.invalid")


def _upload(client: TestClient, *, filename="notes.txt", content=None, folder_id=None, category_id="notes"):
    payload = content or (
        b"Astrovivarium agent orchestration preserves precise evidence in a nested course material library. "
        b"Astrovivarium describes a unique retrieval concept for testing source citations."
    )
    data = {"category_id": category_id, "title": "Astrovivarium notes", "description": "Astrovivarium retrieval reference"}
    if folder_id:
        data["folder_id"] = folder_id
    return client.post(
        "/api/course-materials/materials",
        data=data,
        files=[("files", (filename, payload, "text/plain"))],
    )


def test_categories_nested_folders_and_upload_persist_with_source_metadata():
    faculty = _faculty()
    categories = faculty.get("/api/course-materials/categories")
    assert categories.status_code == 200
    assert [item["category_id"] for item in categories.json()["data"]] == [
        "notes", "lab-manuals", "lesson-plans", "presentations",
        "assignments", "question-banks", "reference-materials", "syllabus",
    ]

    parent = faculty.post(
        "/api/course-materials/folders",
        json={"category_id": "notes", "name": "Chapter 2"},
    )
    assert parent.status_code == 200
    child = faculty.post(
        "/api/course-materials/folders",
        json={"category_id": "notes", "name": "Lecture notes", "parent_folder_id": parent.json()["data"]["folder_id"]},
    )
    assert child.status_code == 200
    uploaded = _upload(faculty, folder_id=child.json()["data"]["folder_id"])
    assert uploaded.status_code == 200, uploaded.text
    item = uploaded.json()["data"]["items"][0]
    assert item["folder_path"] == "Chapter 2/Lecture notes"
    assert "storage_key" not in item

    listing = faculty.get(
        "/api/course-materials/materials",
        params={"category_id": "notes", "folder_id": child.json()["data"]["folder_id"], "recursive": False},
    )
    assert listing.status_code == 200
    persisted = listing.json()["data"]["items"][0]
    assert persisted["material_id"] == item["material_id"]
    assert persisted["title"] == "Astrovivarium notes"

    chunks = [chunk for chunk in knowledge_service.get_chunks() if chunk.material_id == item["material_id"]]
    assert chunks
    assert all(chunk.category == "Notes" and chunk.folder_path == "Chapter 2/Lecture notes" for chunk in chunks)
    assert all("Astrovivarium" in chunk.content for chunk in chunks)
    citations = knowledge_service.search("Astrovivarium retrieval reference", course_id=_COURSE, top_k=5)
    assert any(match.material_id == item["material_id"] and "Notes" in match.source_document for match in citations.matches)
    restarted_index = KnowledgeService()
    restarted_index.initialize(force_reload=True)
    assert any(chunk.material_id == item["material_id"] for chunk in restarted_index.get_chunks())
    with get_db_connection() as conn:
        audit = conn.execute(
            "SELECT actor, actor_role, action FROM audit_events WHERE resource = ? AND action = 'FILE_UPLOADED'",
            (f"material:{item['material_id']}",),
        ).fetchone()
    assert audit and audit["actor"] == "cm-faculty" and audit["actor_role"] == "FACULTY"


def test_students_can_browse_preview_and_download_but_cannot_manage_materials():
    faculty = _faculty()
    uploaded = _upload(faculty)
    assert uploaded.status_code == 200
    item = uploaded.json()["data"]["items"][0]
    student = _client("cm-student@test.invalid")

    listed = student.get("/api/course-materials/materials", params={"category_id": "notes"})
    assert listed.status_code == 200, listed.text
    assert any(material["material_id"] == item["material_id"] for material in listed.json()["data"]["items"])
    preview = student.get(f"/api/course-materials/materials/{item['material_id']}/preview")
    assert preview.status_code == 200
    assert "Astrovivarium" in preview.json()["data"]["text"]
    download = student.get(f"/api/course-materials/materials/{item['material_id']}/content?download=true")
    assert download.status_code == 200
    assert b"Astrovivarium" in download.content
    assert download.headers["content-disposition"].startswith("attachment;")

    assert student.post("/api/course-materials/folders", json={"category_id": "notes", "name": "Student folder"}).status_code == 403
    assert student.patch(f"/api/course-materials/materials/{item['material_id']}", json={"title": "No"}).status_code == 403
    assert student.delete(f"/api/course-materials/materials/{item['material_id']}").status_code == 403
    assert student.post(
        "/api/course-materials/materials",
        data={"category_id": "notes"},
        files=[("files", ("try.txt", b"no", "text/plain"))],
    ).status_code == 403


def test_admin_and_out_of_scope_users_cannot_manage_or_access_course_files():
    faculty = _faculty()
    uploaded = _upload(faculty)
    assert uploaded.status_code == 200
    material_id = uploaded.json()["data"]["items"][0]["material_id"]

    admin = _client("cm-admin@test.invalid")
    assert admin.post("/api/course-materials/folders", json={"category_id": "notes", "name": "Admin folder"}).status_code == 403
    assert admin.delete(f"/api/course-materials/materials/{material_id}").status_code == 403

    out_of_scope_faculty = _client("cm-outside-faculty@test.invalid")
    assert out_of_scope_faculty.get("/api/course-materials/categories", params={"course_id": _COURSE}).status_code == 403
    assert out_of_scope_faculty.patch(
        f"/api/course-materials/materials/{material_id}", params={"course_id": _COURSE}, json={"title": "No"}
    ).status_code == 403

    out_of_scope_student = _client("cm-outside-student@test.invalid")
    assert out_of_scope_student.get(f"/api/course-materials/materials/{material_id}").status_code == 403
    assert out_of_scope_student.get(f"/api/course-materials/materials/{material_id}/content").status_code == 403
    assert out_of_scope_student.post(
        "/api/knowledge/search",
        json={"query": "Astrovivarium", "course_id": _COURSE},
    ).status_code == 403
    assert out_of_scope_student.post(
        "/api/lab2/query",
        json={"request": "Search course notes for Astrovivarium", "course_id": _COURSE},
    ).status_code == 403
    assert out_of_scope_student.post(
        "/api/lab3/execute",
        json={"skill_name": "research_summary_skill", "parameters": {"course_code": _COURSE, "topic": "Astrovivarium"}},
    ).status_code == 403
    assert out_of_scope_student.post(
        "/api/lab9/grounding/verify",
        json={"claims": ["Astrovivarium is in course notes"]},
    ).status_code == 403

    anonymous = TestClient(app)
    assert anonymous.get(f"/api/course-materials/materials/{material_id}/content").status_code == 401
    assert anonymous.post(
        "/api/knowledge/search",
        json={"query": "Astrovivarium", "course_id": _COURSE},
    ).status_code == 401


def test_search_filters_replacement_and_deletion_update_rag_index():
    faculty = _faculty()
    uploaded = _upload(faculty)
    assert uploaded.status_code == 200
    material = uploaded.json()["data"]["items"][0]
    material_id = material["material_id"]

    filtered = faculty.get(
        "/api/course-materials/materials",
        params={"query": "Astrovivarium", "category_id": "notes", "file_type": "txt"},
    )
    assert filtered.status_code == 200, filtered.text
    assert filtered.json()["data"]["count"] >= 1
    assert any(item["material_id"] == material_id for item in filtered.json()["data"]["items"])
    assert faculty.get(
        "/api/course-materials/materials",
        params={"category_id": "notes", "chapter": 3},
    ).status_code == 200

    replacement = faculty.put(
        f"/api/course-materials/materials/{material_id}/file",
        files={"file": ("revised.txt", b"Xylophonic revision evidence is stored and indexed.", "text/plain")},
    )
    assert replacement.status_code == 200, replacement.text
    chunks = [chunk for chunk in knowledge_service.get_chunks() if chunk.material_id == material_id]
    assert chunks and any("Xylophonic" in chunk.content for chunk in chunks)
    assert all("unique retrieval concept" not in chunk.content for chunk in chunks)

    deleted = faculty.delete(f"/api/course-materials/materials/{material_id}")
    assert deleted.status_code == 200
    assert not any(chunk.material_id == material_id for chunk in knowledge_service.get_chunks())
    assert faculty.get(f"/api/course-materials/materials/{material_id}").status_code == 404


def test_upload_content_is_validated_and_folder_cycles_are_rejected():
    faculty = _faculty()
    bad = faculty.post(
        "/api/course-materials/materials",
        data={"category_id": "notes"},
        files=[("files", ("fake.pdf", b"not a PDF", "application/pdf"))],
    )
    assert bad.status_code == 400

    parent = faculty.post("/api/course-materials/folders", json={"category_id": "notes", "name": "Cycle parent"})
    child = faculty.post(
        "/api/course-materials/folders",
        json={"category_id": "notes", "name": "Cycle child", "parent_folder_id": parent.json()["data"]["folder_id"]},
    )
    response = faculty.patch(
        f"/api/course-materials/folders/{parent.json()['data']['folder_id']}",
        json={"parent_folder_id": child.json()["data"]["folder_id"]},
    )
    assert response.status_code == 400


def test_xlsx_upload_is_extracted_and_indexed_from_nested_material_storage():
    faculty = _faculty()
    package = BytesIO()
    with ZipFile(package, "w") as archive:
        archive.writestr(
            "[Content_Types].xml",
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"></Types>',
        )
        archive.writestr(
            "xl/workbook.xml",
            '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
            'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
            '<sheets><sheet name="Milestones" sheetId="1" r:id="rId1"/></sheets></workbook>',
        )
        archive.writestr(
            "xl/_rels/workbook.xml.rels",
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="worksheet" Target="worksheets/sheet1.xml"/>'
            '</Relationships>',
        )
        archive.writestr(
            "xl/sharedStrings.xml",
            '<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
            '<si><t>MilestoneValue</t></si></sst>',
        )
        archive.writestr(
            "xl/worksheets/sheet1.xml",
            '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
            '<sheetData><row r="1"><c r="A1" t="s"><v>0</v></c></row></sheetData></worksheet>',
        )
    response = faculty.post(
        "/api/course-materials/materials",
        data={"category_id": "assignments", "title": "Milestone sheet"},
        files=[("files", ("milestones.xlsx", package.getvalue(),
                          "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"))],
    )
    assert response.status_code == 200, response.text
    material_id = response.json()["data"]["items"][0]["material_id"]
    chunks = [chunk for chunk in knowledge_service.get_chunks() if chunk.material_id == material_id]
    assert chunks and any("MilestoneValue" in chunk.content for chunk in chunks)
