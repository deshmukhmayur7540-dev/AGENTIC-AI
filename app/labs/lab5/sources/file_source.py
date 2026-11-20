"""FileStoreDataSource: Governed access to filesystem documents and exported handouts."""

from pathlib import Path
from typing import Any
from app.labs.lab5.sources.base_source import BaseDataSource
from app.models.lab5_models import ConnectorOperation, ConnectorRole


class FileStoreDataSource(BaseDataSource):
    """Governed filesystem connector for syllabus documents and generated course handouts."""

    source_id = "file_source"
    name = "Course Files & Handouts Repository"
    source_type = "FILE_STORE"
    description = (
        "Governed access to syllabus documents, lab handouts, and generated PDF/Markdown guides. "
        "Enforces authorization on file generation and modifications."
    )
    supported_operations = [
        ConnectorOperation.READ,
        ConnectorOperation.WRITE,
        ConnectorOperation.LIST,
    ]
    is_read_only = False
    requires_auth = True

    def __init__(self) -> None:
        self._in_memory_files: dict[str, str] = {
            "26ECAC401_Syllabus.md": (
                "# 26ECAC401: Agentic AI Syllabus\n\n"
                "**Credits:** 4.0\n**Prerequisites:** Python 3.10+, Generative AI Foundations\n"
                "**Chapters:** 1 (Foundations), 2 (Tools & Memory), 3 (Multi-Agent), 4 (Governance)"
            ),
            "Lab1_Specification.md": (
                "# Lab 1: Clarify -> Plan -> Revise\n"
                "Design an agentic workflow that identifies missing inputs and asks questions."
            ),
            "Lab2_ToolHarness.md": (
                "# Lab 2: Tool-Using Agent\n"
                "Construct typed tools with Pydantic validation and audit traces."
            ),
        }

    def execute(
        self,
        operation: ConnectorOperation,
        resource_path: str,
        parameters: dict[str, Any],
        role: ConnectorRole,
    ) -> tuple[Any, str]:
        # Role authorization
        if operation == ConnectorOperation.WRITE and role == ConnectorRole.STUDENT:
            raise PermissionError(
                f"Access Denied: Role '{role.value}' is unauthorized to write files to '{self.source_id}'. "
                f"File authoring requires FACULTY or SYSTEM authority."
            )

        filename = resource_path or parameters.get("filename", "")

        if operation == ConnectorOperation.LIST:
            file_summaries = [
                {"filename": fn, "size_chars": len(content), "type": "markdown"}
                for fn, content in self._in_memory_files.items()
            ]
            return file_summaries, "File Store Directory Index"

        elif operation == ConnectorOperation.READ:
            if not filename or filename not in self._in_memory_files:
                raise FileNotFoundError(f"File '{filename}' not found in course file store.")
            content = self._in_memory_files[filename]
            return {
                "filename": filename,
                "content": content,
                "line_count": len(content.splitlines()),
            }, f"File Store Path: course_files/{filename}"

        elif operation == ConnectorOperation.WRITE:
            content = parameters.get("content", "")
            if not filename:
                raise ValueError("WRITE operation requires 'filename'.")
            self._in_memory_files[filename] = content
            return {
                "status": "FILE_WRITTEN",
                "filename": filename,
                "size_chars": len(content),
            }, f"File Store Write: course_files/{filename}"

        raise ValueError(f"Operation '{operation}' not supported by FileStoreDataSource.")
