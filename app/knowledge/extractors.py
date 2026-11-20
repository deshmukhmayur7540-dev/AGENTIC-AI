"""Document extractors for Word (.docx) and PowerPoint (.pptx) course lecture files."""

import logging
import posixpath
import re
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional

from app.knowledge.models import DiscoveredDocument, ExtractedSection

logger = logging.getLogger(__name__)


class BaseDocumentExtractor:
    """Abstract interface for extracting sections and content from a document."""

    def extract(self, doc: DiscoveredDocument) -> list[ExtractedSection]:
        raise NotImplementedError


class DocxExtractor(BaseDocumentExtractor):
    """Extracts structured sections, headings, paragraphs, and tables from .docx documents."""

    RUNNING_HEADER_REGEX = re.compile(
        r"^Agentic AI\s*[\u2014\-–]\s*Chapter\s*\d+.*$",
        re.IGNORECASE,
    )
    SECTION_HEADER_REGEX = re.compile(
        r"^(?:(\d+\.\d+(?:\.\d+)?)\s+(.+)|Chapter Roadmap|Key Terms.*|Summary.*|Exercises.*)$",
        re.IGNORECASE,
    )

    def extract(self, doc: DiscoveredDocument) -> list[ExtractedSection]:
        fpath = Path(doc.source_path)
        if not fpath.exists():
            return []

        try:
            return self._extract_with_python_docx(doc, fpath)
        except Exception as exc:
            logger.warning("python-docx extraction failed for %s (%s). Attempting XML fallback.", fpath, exc)
            return self._extract_with_xml_fallback(doc, fpath)

    def _extract_with_python_docx(self, doc: DiscoveredDocument, fpath: Path) -> list[ExtractedSection]:
        import docx

        word_doc = docx.Document(str(fpath))
        sections: list[ExtractedSection] = []

        current_title = f"Chapter {doc.chapter} Introduction"
        current_location = f"Chapter {doc.chapter}"
        current_paragraphs: list[str] = []
        seq_idx = 0

        def flush_current_section():
            nonlocal seq_idx
            text = "\n\n".join(p for p in current_paragraphs if p.strip()).strip()
            if text:
                sections.append(
                    ExtractedSection(
                        title=current_title,
                        content=text,
                        source_location=current_location,
                        sequence_index=seq_idx,
                    )
                )
                seq_idx += 1
            current_paragraphs.clear()

        for p in word_doc.paragraphs:
            text = p.text.strip()
            if not text:
                continue

            # Filter out running document headers that repeat on every page
            if self.RUNNING_HEADER_REGEX.match(text):
                continue

            # Detect if this paragraph represents a new section heading
            is_heading = False
            heading_title = ""
            location_tag = ""

            style_name = p.style.name.lower() if p.style and p.style.name else ""
            if "heading" in style_name:
                is_heading = True
                heading_title = text
                sec_match = re.search(r"\b(\d+\.\d+(?:\.\d+)?)\b", text)
                location_tag = f"Section {sec_match.group(1)}" if sec_match else f"Chapter {doc.chapter}"
            else:
                match = self.SECTION_HEADER_REGEX.match(text)
                if match:
                    is_heading = True
                    heading_title = text
                    sec_num = match.group(1)
                    location_tag = f"Section {sec_num}" if sec_num else f"Chapter {doc.chapter}"

            if is_heading and len(text) < 120:
                flush_current_section()
                current_title = heading_title
                current_location = location_tag
            else:
                current_paragraphs.append(text)

        # Extract structured content from embedded tables
        for table_idx, table in enumerate(word_doc.tables):
            table_lines: list[str] = []
            for row in table.rows:
                row_cells = [cell.text.strip().replace("\n", " ") for cell in row.cells]
                # Filter out completely empty rows or duplicate cell texts
                if any(row_cells):
                    table_lines.append(" | ".join(row_cells))

            if table_lines:
                table_text = "\n".join(table_lines)
                current_paragraphs.append(f"[Table Reference {table_idx + 1}]\n{table_text}")

        flush_current_section()
        return sections

    def _extract_with_xml_fallback(self, doc: DiscoveredDocument, fpath: Path) -> list[ExtractedSection]:
        """Native fallback extracting paragraphs and sections from document.xml inside .docx ZIP container."""
        sections: list[ExtractedSection] = []
        try:
            with zipfile.ZipFile(fpath) as z:
                xml_content = z.read("word/document.xml")
                root = ET.fromstring(xml_content)
                namespaces = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
                body = root.find(".//w:body", namespaces)
                if body is None:
                    return sections

                current_title = f"Chapter {doc.chapter} Introduction"
                current_location = f"Chapter {doc.chapter}"
                current_paragraphs: list[str] = []
                seq_idx = 0

                def flush_current_section():
                    nonlocal seq_idx
                    text = "\n\n".join(p for p in current_paragraphs if p.strip()).strip()
                    if text:
                        # Normalize unicode dashes for consistency
                        normalized_text = (
                            text.replace("\u2014", " - ")
                            .replace("\u2013", " - ")
                            .replace("—", " - ")
                            .replace("–", " - ")
                        )
                        sections.append(
                            ExtractedSection(
                                title=current_title,
                                content=normalized_text,
                                source_location=current_location,
                                sequence_index=seq_idx,
                            )
                        )
                        seq_idx += 1
                    current_paragraphs.clear()

                for child in body:
                    tag = child.tag.split("}")[-1]
                    if tag == "p":
                        text = "".join(t.text for t in child.iterfind(".//w:t", namespaces) if t.text).strip()
                        if not text or self.RUNNING_HEADER_REGEX.match(text):
                            continue

                        pstyle = child.find(".//w:pPr/w:pStyle", namespaces)
                        sval = (
                            pstyle.attrib.get("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}val", "").lower()
                            if pstyle is not None
                            else ""
                        )
                        is_heading = False
                        heading_title = ""
                        loc = ""
                        if "heading" in sval:
                            is_heading = True
                            heading_title = text
                            m = re.search(r"\b(\d+\.\d+(?:\.\d+)?)\b", text)
                            loc = f"Section {m.group(1)}" if m else f"Chapter {doc.chapter}"
                        else:
                            m = self.SECTION_HEADER_REGEX.match(text)
                            if m:
                                is_heading = True
                                heading_title = text
                                sec_num = m.group(1)
                                loc = f"Section {sec_num}" if sec_num else f"Chapter {doc.chapter}"

                        if is_heading and len(text) < 120:
                            flush_current_section()
                            current_title = (
                                heading_title.replace("\u2014", " - ")
                                .replace("\u2013", " - ")
                                .replace("—", " - ")
                                .replace("–", " - ")
                            )
                            current_location = loc
                        else:
                            current_paragraphs.append(text)
                    elif tag == "tbl":
                        tbl_lines: list[str] = []
                        for tr in child.iterfind(".//w:tr", namespaces):
                            row_cells = [
                                "".join(t.text for t in tc.iterfind(".//w:t", namespaces) if t.text).strip().replace("\n", " ")
                                for tc in tr.iterfind(".//w:tc", namespaces)
                            ]
                            if any(row_cells):
                                tbl_lines.append(" | ".join(row_cells))
                        if tbl_lines:
                            current_paragraphs.append("[Table Reference]\n" + "\n".join(tbl_lines))

                flush_current_section()
        except Exception as err:
            logger.error("XML fallback failed for %s: %s", fpath, err)

        return sections


class PptxExtractor(BaseDocumentExtractor):
    """Extracts slide titles, body bullet points, tables, and notes from .pptx presentations."""

    def extract(self, doc: DiscoveredDocument) -> list[ExtractedSection]:
        fpath = Path(doc.source_path)
        if not fpath.exists():
            return []

        try:
            return self._extract_with_python_pptx(doc, fpath)
        except Exception as exc:
            logger.warning("python-pptx extraction failed for %s (%s). Attempting XML fallback.", fpath, exc)
            return self._extract_with_xml_fallback(doc, fpath)

    def _extract_with_python_pptx(self, doc: DiscoveredDocument, fpath: Path) -> list[ExtractedSection]:
        import pptx

        prs = pptx.Presentation(str(fpath))
        sections: list[ExtractedSection] = []

        for i, slide in enumerate(prs.slides):
            slide_num = i + 1
            title_text = ""
            body_parts: list[str] = []

            # 1. Inspect title if present
            if slide.shapes.title and slide.shapes.title.has_text_frame:
                title_candidate = slide.shapes.title.text.strip()
                if title_candidate:
                    title_text = title_candidate

            # 2. Inspect all shape text frames and tables
            for shape in slide.shapes:
                # Shape is not the title
                if shape.has_text_frame and shape != slide.shapes.title:
                    raw_text = shape.text.strip()
                    if raw_text:
                        # If title wasn't set by title shape, check if this is the first short line
                        if not title_text and len(raw_text.splitlines()[0]) < 80:
                            lines = raw_text.splitlines()
                            title_text = lines[0].strip()
                            rest = "\n".join(lines[1:]).strip()
                            if rest:
                                body_parts.append(rest)
                        else:
                            body_parts.append(raw_text)

                elif shape.has_table:
                    table_lines: list[str] = []
                    for row in shape.table.rows:
                        row_vals = [cell.text.strip().replace("\n", " ") for cell in row.cells]
                        if any(row_vals):
                            table_lines.append(" | ".join(row_vals))
                    if table_lines:
                        body_parts.append("\n".join(table_lines))

            # 3. Inspect slide notes if available
            if slide.has_notes_slide and slide.notes_slide.notes_text_frame:
                notes_text = slide.notes_slide.notes_text_frame.text.strip()
                if notes_text and not notes_text.lower().startswith("speaker"):
                    body_parts.append(f"[Slide Notes]: {notes_text}")

            content_text = "\n\n".join(body_parts).strip()
            if not title_text:
                title_text = f"Chapter {doc.chapter} Presentation - Slide {slide_num}"

            # Only record non-empty slides
            if content_text or title_text:
                full_slide_content = f"{title_text}\n\n{content_text}" if content_text else title_text
                sections.append(
                    ExtractedSection(
                        title=title_text,
                        content=full_slide_content,
                        source_location=f"Slide {slide_num}",
                        sequence_index=i,
                    )
                )

        return sections

    def _extract_with_xml_fallback(self, doc: DiscoveredDocument, fpath: Path) -> list[ExtractedSection]:
        """Native fallback extracting slide texts directly from ppt/slides/slide*.xml containers."""
        sections: list[ExtractedSection] = []
        try:
            with zipfile.ZipFile(fpath) as z:
                slide_names = sorted(
                    [n for n in z.namelist() if n.startswith("ppt/slides/slide") and n.endswith(".xml")],
                    key=lambda s: int(re.search(r"\d+", s.split("/")[-1]).group(0)),
                )
                namespaces = {"a": "http://schemas.openxmlformats.org/drawingml/2006/main"}

                for idx, slide_name in enumerate(slide_names):
                    slide_num = idx + 1
                    xml_content = z.read(slide_name)
                    root = ET.fromstring(xml_content)
                    texts = [t.text for t in root.iterfind(".//a:t", namespaces) if t.text]
                    slide_text = "\n".join(t.strip() for t in texts if t.strip()).strip()
                    slide_text = (
                        slide_text.replace("\u2014", " - ")
                        .replace("\u2013", " - ")
                        .replace("—", " - ")
                        .replace("–", " - ")
                        .replace("\xa0", " ")
                        .replace("\ufffd", "-")
                    )

                    if slide_text:
                        first_line = slide_text.splitlines()[0]
                        title = first_line if len(first_line) < 80 else f"Slide {slide_num}"
                        sections.append(
                            ExtractedSection(
                                title=title,
                                content=slide_text,
                                source_location=f"Slide {slide_num}",
                                sequence_index=idx,
                            )
                        )
        except Exception as err:
            logger.error("PPTX XML fallback failed for %s: %s", fpath, err)

        return sections


class TextExtractor(BaseDocumentExtractor):
    """Extracts plain text and markdown notes for retrieval (download still uses original bytes)."""

    def extract(self, doc: DiscoveredDocument) -> list[ExtractedSection]:
        fpath = Path(doc.source_path)
        if not fpath.exists():
            return []
        try:
            text = fpath.read_text(encoding="utf-8", errors="replace").strip()
        except OSError:
            return []
        if not text:
            return []
        return [
            ExtractedSection(
                title=doc.source_filename,
                content=text,
                source_location="Full document",
                sequence_index=0,
            )
        ]


class PdfExtractor(BaseDocumentExtractor):
    """Extracts text sections page by page from PDF documents."""

    def extract(self, doc: DiscoveredDocument) -> list[ExtractedSection]:
        fpath = Path(doc.source_path)
        if not fpath.exists():
            return []
        try:
            from pypdf import PdfReader
            reader = PdfReader(str(fpath))
            sections: list[ExtractedSection] = []
            for idx, page in enumerate(reader.pages):
                page_text = (page.extract_text() or "").strip()
                if page_text:
                    sections.append(
                        ExtractedSection(
                            title=f"{doc.source_filename} - Page {idx+1}",
                            content=page_text,
                            source_location=f"Page {idx+1}",
                            sequence_index=idx,
                        )
                    )
            return sections
        except Exception as exc:
            logger.warning("PDF extraction failed for %s: %s", fpath, exc)
            return []


class CsvExtractor(BaseDocumentExtractor):
    """Extracts tabular records from CSV documents."""

    def extract(self, doc: DiscoveredDocument) -> list[ExtractedSection]:
        import csv
        fpath = Path(doc.source_path)
        if not fpath.exists():
            return []
        try:
            with open(fpath, mode="r", encoding="utf-8", errors="replace") as f:
                reader = csv.reader(f)
                rows = list(reader)
            if not rows:
                return []
            header = ", ".join(rows[0])
            body_rows = [" | ".join(row) for row in rows[1:] if row]
            text = f"Header: {header}\n" + "\n".join(body_rows)
            return [
                ExtractedSection(
                    title=doc.source_filename,
                    content=text,
                    source_location="CSV Table",
                    sequence_index=0,
                )
            ]
        except Exception as exc:
            logger.warning("CSV extraction failed for %s: %s", fpath, exc)
            return []


class XlsxExtractor(BaseDocumentExtractor):
    """Extract worksheet cell values from Office Open XML spreadsheets."""

    def extract(self, doc: DiscoveredDocument) -> list[ExtractedSection]:
        path = Path(doc.source_path)
        if not path.is_file():
            return []
        namespace = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
        relationship_namespace = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
        package_relationship_namespace = "{http://schemas.openxmlformats.org/package/2006/relationships}"
        sections: list[ExtractedSection] = []
        try:
            with zipfile.ZipFile(path) as archive:
                names = set(archive.namelist())
                shared_strings: list[str] = []
                if "xl/sharedStrings.xml" in names:
                    root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
                    for item in root.findall(f"{namespace}si"):
                        shared_strings.append("".join(node.text or "" for node in item.iter(f"{namespace}t")))

                workbook = ET.fromstring(archive.read("xl/workbook.xml"))
                relationships = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
                targets = {
                    item.attrib["Id"]: item.attrib["Target"]
                    for item in relationships.findall(f"{package_relationship_namespace}Relationship")
                }
                for index, sheet in enumerate(workbook.findall(f".//{namespace}sheet")):
                    rel_id = sheet.attrib.get(f"{relationship_namespace}id")
                    target = targets.get(rel_id or "")
                    if not target:
                        continue
                    sheet_path = posixpath.normpath(posixpath.join("xl", target.lstrip("/")))
                    if target.startswith("/") or sheet_path.startswith("../") or sheet_path not in names:
                        continue
                    sheet_root = ET.fromstring(archive.read(sheet_path))
                    lines: list[str] = []
                    for cell in sheet_root.findall(f".//{namespace}c"):
                        cell_value = cell.find(f"{namespace}v")
                        value = cell_value.text if cell_value is not None else ""
                        if cell.attrib.get("t") == "s" and value.isdigit():
                            shared_index = int(value)
                            value = shared_strings[shared_index] if shared_index < len(shared_strings) else ""
                        elif cell.attrib.get("t") == "inlineStr":
                            inline = cell.find(f"{namespace}is")
                            value = "".join(node.text or "" for node in inline.iter(f"{namespace}t")) if inline is not None else ""
                        if value:
                            lines.append(f"{cell.attrib.get('r', '')}: {value}")
                    if lines:
                        sections.append(
                            ExtractedSection(
                                title=sheet.attrib.get("name", f"Sheet {index + 1}"),
                                content="\n".join(lines)[:500_000],
                                source_location=f"Worksheet: {sheet.attrib.get('name', f'Sheet {index + 1}')}",
                                sequence_index=index,
                            )
                        )
            return sections
        except (OSError, KeyError, ValueError, ET.ParseError, zipfile.BadZipFile) as exc:
            logger.warning("XLSX extraction failed for %s: %s", path, exc)
            return []


class DocumentExtractorRegistry:
    """Dispatches document extraction to the appropriate extractor based on document type."""

    def __init__(self) -> None:
        self._extractors: dict[str, BaseDocumentExtractor] = {
            "docx": DocxExtractor(),
            "pptx": PptxExtractor(),
            "txt": TextExtractor(),
            "md": TextExtractor(),
            "markdown": TextExtractor(),
            "pdf": PdfExtractor(),
            "csv": CsvExtractor(),
            "xlsx": XlsxExtractor(),
        }

    def extract(self, doc: DiscoveredDocument) -> list[ExtractedSection]:
        extractor = self._extractors.get(doc.document_type.lower())
        if not extractor:
            logger.warning("No extractor registered for document type: %s", doc.document_type)
            return []
        return extractor.extract(doc)
