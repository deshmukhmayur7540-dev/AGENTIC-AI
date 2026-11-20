"""Safe catalog of original knowledge files for listing, download, upload, preview, and folder navigation.

Downloads return the original bytes on disk. Extraction/indexing is independent.
"""

from __future__ import annotations

import hashlib
import mimetypes
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
from urllib.parse import quote

from pydantic import BaseModel, Field

from config import settings

SKIP_DIR_NAMES = {
    ".git",
    ".hg",
    ".svn",
    ".venv",
    "venv",
    "env",
    "__pycache__",
    "node_modules",
    ".pytest_cache",
    ".mypy_cache",
    "chrome-temp",
    "dist",
    "build",
}

SKIP_FILE_PREFIXES = ("~$", ".")
SKIP_FILE_NAMES = {".ds_store", "thumbs.db", "desktop.ini"}

ALLOWED_EXTENSIONS = {
    "pdf",
    "docx",
    "doc",
    "txt",
    "md",
    "markdown",
    "pptx",
    "ppt",
    "html",
    "htm",
    "csv",
}

MIME_BY_EXT = {
    "pdf": "application/pdf",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "doc": "application/msword",
    "txt": "text/plain",
    "md": "text/markdown",
    "markdown": "text/markdown",
    "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "ppt": "application/vnd.ms-powerpoint",
    "html": "text/html",
    "htm": "text/html",
    "csv": "text/csv",
}


class KnowledgeFileRecord(BaseModel):
    """Public metadata for a discoverable original knowledge file."""

    file_id: str
    filename: str
    relative_path: str
    folder: str
    chapter: Optional[int] = None
    format: str
    size_bytes: int
    last_modified: Optional[str] = None
    indexed: bool = False
    content_type: str
    sha256: Optional[str] = None


class KnowledgeFolderNode(BaseModel):
    """Hierarchical folder node representing a directory in the knowledge repository."""

    name: str
    relative_path: str
    file_count: int = 0
    subfolders: list[KnowledgeFolderNode] = Field(default_factory=list)


class KnowledgeFileCatalog:
    """Recursive, path-confined catalog of files and folders under the knowledge root."""

    def __init__(self, root: Path) -> None:
        self.root = root.resolve()

    def list_files(
        self,
        query: Optional[str] = None,
        folder: Optional[str] = None,
        format_filter: Optional[str] = None,
        chapter: Optional[int] = None,
    ) -> list[KnowledgeFileRecord]:
        """List files with optional query search, folder filter, format filter, or chapter filter."""
        records = list(self._scan().values())
        records.sort(key=lambda r: (r.chapter or 99, r.relative_path.lower()))

        if folder and folder.strip():
            target_f = folder.strip().replace("\\", "/").strip("/")
            records = [r for r in records if r.folder == target_f or r.folder.startswith(target_f + "/")]

        if format_filter and format_filter.strip():
            fmt = format_filter.strip().lower().lstrip(".")
            records = [r for r in records if r.format.lower() == fmt]

        if chapter is not None:
            records = [r for r in records if r.chapter == chapter]

        if query:
            q = query.strip().lower()
            records = [
                r
                for r in records
                if q in r.filename.lower()
                or q in r.relative_path.lower()
                or q in r.folder.lower()
                or q in r.format.lower()
            ]

        return records

    def get_folder_tree(self) -> list[dict[str, Any]]:
        """Construct hierarchical folder tree of directories and subdirectories."""
        all_files = self._scan().values()
        folder_counts: dict[str, int] = {}
        for f in all_files:
            folder_counts[f.folder] = folder_counts.get(f.folder, 0) + 1

        tree: dict[str, Any] = {}

        for dirpath, dirnames, _ in os.walk(self.root):
            dirnames[:] = sorted([d for d in dirnames if d.lower() not in SKIP_DIR_NAMES])
            rel = os.path.relpath(dirpath, self.root).replace("\\", "/")
            if rel == ".":
                continue

            parts = rel.split("/")
            curr = tree
            accum_path = ""
            for part in parts:
                accum_path = f"{accum_path}/{part}" if accum_path else part
                if part not in curr:
                    curr[part] = {
                        "name": part,
                        "path": accum_path,
                        "file_count": folder_counts.get(accum_path, 0),
                        "children": {},
                    }
                curr = curr[part]["children"]

        def _format_nodes(node_dict: dict[str, Any]) -> list[dict[str, Any]]:
            res = []
            for k in sorted(node_dict.keys()):
                node = node_dict[k]
                res.append({
                    "name": node["name"],
                    "path": node["path"],
                    "file_count": node["file_count"],
                    "subfolders": _format_nodes(node["children"]),
                })
            return res

        return _format_nodes(tree)

    def get_file(self, file_id: str) -> Optional[tuple[KnowledgeFileRecord, Path]]:
        """Retrieve file record and verified path by unique ID."""
        if not file_id or not isinstance(file_id, str):
            return None
        if "/" in file_id or "\\" in file_id or ".." in file_id:
            return None
        catalog = self._scan()
        record = catalog.get(file_id)
        if not record:
            return None
        path = self._safe_path(record.relative_path)
        if path is None or not path.is_file():
            return None
        return record, path

    def save_file(
        self,
        folder: str,
        filename: str,
        content: bytes,
    ) -> tuple[KnowledgeFileRecord, bool, str]:
        """Save a new file safely under the specified folder with duplicate detection."""
        # Sanitize filename
        safe_name = Path(filename).name.strip()
        ext = safe_name.rsplit(".", 1)[-1].lower() if "." in safe_name else ""
        if ext not in ALLOWED_EXTENSIONS:
            raise ValueError(f"File extension '.{ext}' is not permitted. Allowed: {sorted(ALLOWED_EXTENSIONS)}")

        # Validate target folder
        clean_folder = folder.replace("\\", "/").strip("/")
        target_dir = (self.root / clean_folder).resolve()
        try:
            target_dir.relative_to(self.root)
        except ValueError:
            raise ValueError("Target folder path is outside knowledge root.")

        target_dir.mkdir(parents=True, exist_ok=True)
        target_file = target_dir / safe_name

        # Duplicate detection by SHA-256
        content_hash = hashlib.sha256(content).hexdigest()
        is_duplicate = False
        duplicate_of = ""
        for rec in self._scan().values():
            if rec.sha256 == content_hash:
                is_duplicate = True
                duplicate_of = rec.relative_path
                break

        # Save to disk
        target_file.write_bytes(content)

        rel = self._relative_posix(target_file)
        if not rel:
            raise RuntimeError("Failed to resolve relative posix path for saved file.")

        file_id = hashlib.sha256(rel.encode("utf-8")).hexdigest()[:24]
        stat = target_file.stat()
        record = KnowledgeFileRecord(
            file_id=file_id,
            filename=safe_name,
            relative_path=rel,
            folder=clean_folder,
            chapter=self._chapter_from_rel(rel),
            format=ext,
            size_bytes=int(stat.st_size),
            last_modified=datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
            indexed=self._is_live_indexed(target_file),
            content_type=MIME_BY_EXT.get(ext) or "application/octet-stream",
            sha256=content_hash,
        )
        return record, is_duplicate, duplicate_of

    def preview_file(self, file_id: str) -> dict[str, Any]:
        """Generate formatted preview excerpt for a file."""
        found = self.get_file(file_id)
        if not found:
            raise ValueError(f"File '{file_id}' not found.")
        record, path = found

        ext = record.format.lower()
        preview_text = ""

        try:
            if ext in ("txt", "md", "markdown", "csv"):
                text = path.read_text(encoding="utf-8", errors="replace")
                lines = text.splitlines()
                preview_text = "\n".join(lines[:120])
                if len(lines) > 120:
                    preview_text += f"\n\n[... truncated {len(lines) - 120} more lines ...]"

            elif ext == "pdf":
                from pypdf import PdfReader
                reader = PdfReader(str(path))
                num_pages = len(reader.pages)
                first_page = reader.pages[0].extract_text() if num_pages > 0 else ""
                preview_text = f"PDF Document ({num_pages} pages)\n\nPage 1 Excerpt:\n{first_page[:1500]}"

            elif ext == "docx":
                import docx
                doc = docx.Document(str(path))
                paras = [p.text for p in doc.paragraphs if p.text.strip()]
                preview_text = f"Word Document ({len(paras)} paragraphs)\n\n" + "\n\n".join(paras[:15])

            elif ext == "pptx":
                from pptx import Presentation
                prs = Presentation(str(path))
                num_slides = len(prs.slides)
                slide_texts = []
                for s in prs.slides[:5]:
                    for shape in s.shapes:
                        if hasattr(shape, "text") and shape.text.strip():
                            slide_texts.append(shape.text.strip())
                preview_text = f"PowerPoint Presentation ({num_slides} slides)\n\nSample Slide Content:\n" + "\n\n".join(slide_texts[:12])

            else:
                preview_text = f"Binary file ({record.format.upper()}) &bull; {record.size_bytes} bytes."

        except Exception as exc:
            preview_text = f"Preview generation error: {exc}"

        return {
            "file_id": record.file_id,
            "filename": record.filename,
            "relative_path": record.relative_path,
            "folder": record.folder,
            "format": record.format,
            "size_bytes": record.size_bytes,
            "last_modified": record.last_modified,
            "preview_text": preview_text,
        }

    def delete_file(self, file_id: str) -> bool:
        """Delete a file safely."""
        found = self.get_file(file_id)
        if not found:
            return False
        _, path = found
        try:
            path.unlink()
            return True
        except OSError:
            return False

    def rename_file(self, file_id: str, new_name: str) -> KnowledgeFileRecord:
        """Rename an existing file safely within its folder."""
        found = self.get_file(file_id)
        if not found:
            raise ValueError(f"File '{file_id}' not found.")
        record, old_path = found

        safe_new_name = Path(new_name).name.strip()
        new_path = old_path.parent / safe_new_name
        if new_path.exists():
            raise ValueError(f"File '{safe_new_name}' already exists in folder.")

        old_path.rename(new_path)
        rel = self._relative_posix(new_path)
        stat = new_path.stat()
        new_id = hashlib.sha256(rel.encode("utf-8")).hexdigest()[:24]

        return KnowledgeFileRecord(
            file_id=new_id,
            filename=safe_new_name,
            relative_path=rel,
            folder=record.folder,
            chapter=record.chapter,
            format=new_path.suffix.lower().lstrip("."),
            size_bytes=int(stat.st_size),
            last_modified=datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
            indexed=self._is_live_indexed(new_path),
            content_type=MIME_BY_EXT.get(new_path.suffix.lower().lstrip(".")) or "application/octet-stream",
        )

    def move_file(self, file_id: str, dest_folder: str) -> KnowledgeFileRecord:
        """Move a file to another folder in the knowledge root."""
        found = self.get_file(file_id)
        if not found:
            raise ValueError(f"File '{file_id}' not found.")
        record, old_path = found

        clean_dest = dest_folder.replace("\\", "/").strip("/")
        dest_dir = (self.root / clean_dest).resolve()
        try:
            dest_dir.relative_to(self.root)
        except ValueError:
            raise ValueError("Target folder is outside knowledge root.")

        dest_dir.mkdir(parents=True, exist_ok=True)
        new_path = dest_dir / record.filename
        if new_path.exists() and new_path != old_path:
            raise ValueError(f"File '{record.filename}' already exists in target folder.")

        shutil.move(str(old_path), str(new_path))
        rel = self._relative_posix(new_path)
        stat = new_path.stat()
        new_id = hashlib.sha256(rel.encode("utf-8")).hexdigest()[:24]

        return KnowledgeFileRecord(
            file_id=new_id,
            filename=record.filename,
            relative_path=rel,
            folder=clean_dest,
            chapter=self._chapter_from_rel(rel),
            format=record.format,
            size_bytes=int(stat.st_size),
            last_modified=datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
            indexed=self._is_live_indexed(new_path),
            content_type=record.content_type,
        )

    def content_disposition(self, filename: str) -> str:
        safe = filename.replace('"', "").replace("\r", "").replace("\n", "")
        encoded = quote(safe)
        return f'attachment; filename="{safe}"; filename*=UTF-8\'\'{encoded}'

    def _scan(self) -> dict[str, KnowledgeFileRecord]:
        found: dict[str, KnowledgeFileRecord] = {}
        if not self.root.exists():
            return found

        for dirpath, dirnames, filenames in os.walk(self.root):
            dirnames[:] = [d for d in dirnames if d.lower() not in SKIP_DIR_NAMES]
            for name in filenames:
                if name.startswith(SKIP_FILE_PREFIXES) or name.lower() in SKIP_FILE_NAMES:
                    continue
                path = Path(dirpath) / name
                ext = path.suffix.lower().lstrip(".")
                if ext not in ALLOWED_EXTENSIONS:
                    continue
                rel = self._relative_posix(path)
                if rel is None:
                    continue
                try:
                    stat = path.stat()
                except OSError:
                    continue
                file_id = hashlib.sha256(rel.encode("utf-8")).hexdigest()[:24]
                chapter = self._chapter_from_rel(rel)
                folder = str(Path(rel).parent).replace("\\", "/")
                found[file_id] = KnowledgeFileRecord(
                    file_id=file_id,
                    filename=name,
                    relative_path=rel,
                    folder=folder,
                    chapter=chapter,
                    format=ext,
                    size_bytes=int(stat.st_size),
                    last_modified=datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
                    indexed=self._is_live_indexed(path),
                    content_type=MIME_BY_EXT.get(ext) or mimetypes.guess_type(name)[0] or "application/octet-stream",
                )
        return found

    def _relative_posix(self, path: Path) -> Optional[str]:
        try:
            resolved = path.resolve()
            resolved.relative_to(self.root)
        except (OSError, ValueError):
            return None
        rel = os.path.relpath(resolved, self.root)
        return rel.replace("\\", "/")

    def _is_live_indexed(self, path: Path) -> bool:
        """Report indexed only when this configured Knowledge file is in the live RAG index."""
        if self.root != Path(settings.knowledge_root).resolve():
            return False
        try:
            from app.knowledge.service import knowledge_service

            indexed_hash = knowledge_service.get_indexed_source_hashes().get(str(path.resolve()))
            return bool(indexed_hash) and hashlib.sha256(path.read_bytes()).hexdigest() == indexed_hash
        except (OSError, RuntimeError):
            return False

    def _safe_path(self, relative_path: str) -> Optional[Path]:
        if not relative_path or relative_path.startswith("/") or ":" in relative_path:
            return None
        candidate = (self.root / relative_path).resolve()
        try:
            candidate.relative_to(self.root)
        except ValueError:
            return None
        return candidate

    @staticmethod
    def _chapter_from_rel(relative_path: str) -> Optional[int]:
        parts = relative_path.replace("\\", "/").split("/")
        for part in parts:
            lower = part.lower()
            if lower.startswith("chapter_"):
                tail = lower.replace("chapter_", "", 1)
                if tail.isdigit():
                    return int(tail)
            elif lower.startswith("chapter") and lower[7:].isdigit():
                return int(lower[7:])
        return None


class KnowledgeSearchRequest(BaseModel):
    query: str = Field(min_length=1)
    course_id: str = "26ECAC401"
    chapter: Optional[int] = None
    top_k: int = Field(default=5, ge=1, le=20)
