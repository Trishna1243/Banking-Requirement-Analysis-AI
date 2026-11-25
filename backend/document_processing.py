import re
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO

from docx import Document
from docx.table import Table
from docx.text.paragraph import Paragraph
from pypdf import PdfReader


_SECTION_HEADING_NAMES = (
    "Non-Functional Requirements",
    "Functional Requirements",
    "Business Rules",
    "Additional Information",
    "Constraints",
)
_SECTION_HEADING_ALTERNATION = "|".join(
    re.escape(heading) for heading in _SECTION_HEADING_NAMES
)
_NUMBERED_SECTION_HEADING = re.compile(
    rf"(?<!\w)\d{{1,3}}(?:\.\d+)*[.)]?\s+(?:{_SECTION_HEADING_ALTERNATION})(?=$|[\s:])",
    flags=re.IGNORECASE,
)
_UNNUMBERED_SECTION_HEADING = re.compile(
    rf"(?m)^[ \t]*(?:{_SECTION_HEADING_ALTERNATION})(?:[ \t]*:[ \t]*|[ \t]*$)",
    flags=re.IGNORECASE,
)


@dataclass(frozen=True)
class DocumentSegment:
    text: str
    page_number: int | None
    source_location: str


@dataclass(frozen=True)
class DocumentChunk:
    chunk_id: str
    text: str
    document_id: str
    source_document: str
    page_number: int | None
    source_location: str
    chunk_index: int


def extract_document_segments(file_object: BinaryIO, filename: str) -> tuple[list[DocumentSegment], int | None]:
    extension = Path(filename).suffix.lower()
    if extension == ".pdf":
        reader = PdfReader(file_object)
        segments = [
            DocumentSegment(
                text=page.extract_text() or "",
                page_number=page_number,
                source_location=f"page:{page_number}",
            )
            for page_number, page in enumerate(reader.pages, start=1)
        ]
        return segments, len(reader.pages)

    if extension == ".docx":
        document = Document(file_object)
        segments = []
        paragraph_index = 0
        table_index = 0

        for block in document.element.body.iterchildren():
            if block.tag.endswith("}p"):
                paragraph_index += 1
                paragraph = Paragraph(block, document)
                text = paragraph.text.strip()
                if text:
                    segments.append(
                        DocumentSegment(
                            text=text,
                            page_number=None,
                            source_location=f"paragraph:{paragraph_index}",
                        )
                    )
            elif block.tag.endswith("}tbl"):
                table_index += 1
                table = Table(block, document)
                for row_index, row in enumerate(table.rows, start=1):
                    cells = [re.sub(r"\s+", " ", cell.text).strip() for cell in row.cells]
                    text = " | ".join(cell for cell in cells if cell)
                    if text:
                        segments.append(
                            DocumentSegment(
                                text=text,
                                page_number=None,
                                source_location=f"table:{table_index}:row:{row_index}",
                            )
                        )
        return segments, None

    raise ValueError("Unsupported document type. Upload a PDF or DOCX file.")


def chunk_document(
    segments: list[DocumentSegment],
    document_id: str,
    filename: str,
    max_chars: int = 1200,
    overlap_chars: int = 160,
) -> list[DocumentChunk]:
    if max_chars < 1 or overlap_chars < 0 or overlap_chars >= max_chars:
        raise ValueError("Chunk size must be positive and overlap smaller than chunk size.")

    chunks = []
    for segment in segments:
        text = re.sub(r"[ \t]+", " ", segment.text).strip()
        start = 0
        while start < len(text):
            end = min(start + max_chars, len(text))
            if end < len(text):
                boundary = text.rfind(" ", start, end)
                if boundary > start + max_chars // 2:
                    end = boundary

            chunk_text = text[start:end].strip()
            if chunk_text:
                index = len(chunks)
                chunks.append(
                    DocumentChunk(
                        chunk_id=f"{document_id}:{index}",
                        text=chunk_text,
                        document_id=document_id,
                        source_document=filename,
                        page_number=segment.page_number,
                        source_location=segment.source_location,
                        chunk_index=index,
                    )
                )

            if end >= len(text):
                break
            start = max(start + 1, end - overlap_chars)

    return chunks


def extract_requirement_candidates(segments: list[DocumentSegment]) -> list[dict]:
    candidates = []
    seen = set()
    requirement_terms = re.compile(
        r"\b(shall|must|should|will|required to|is required to|are required to|needs to)\b",
        flags=re.IGNORECASE,
    )
    explicit_requirement_id = re.compile(
        r"((?:NFR|FR|BR)-\d{1,3})\b"
        r"(?P<separator>[ \t]*[:\-–—][ \t]*|[ \t]+)",
        flags=re.IGNORECASE,
    )
    numbered_item = re.compile(r"(?m)^\s*(?:\(?\d{1,3}[.)]|\([a-z]\))\s+")

    for segment in segments:
        source_text = segment.text.strip()
        if not source_text:
            continue
        section_boundaries = sorted(
            {
                match.start()
                for pattern in (
                    _NUMBERED_SECTION_HEADING,
                    _UNNUMBERED_SECTION_HEADING,
                )
                for match in pattern.finditer(source_text)
            }
        )

        explicit_matches = []
        for match in explicit_requirement_id.finditer(source_text):
            line_start = source_text.rfind("\n", 0, match.start()) + 1
            line_prefix = source_text[line_start:match.start()].strip()
            previous_text = source_text[:match.start()]
            strong_label_separator = bool(
                re.search(r"[:\-–—]", match.group("separator"))
            )
            if (
                not line_prefix
                or line_prefix in {"-", "*", "•", "●", "▪", "◦"}
                or (previous_text and previous_text[-1] in "\r\n")
                or previous_text.rstrip().endswith((".", ";", ":", "!", "?"))
                or strong_label_separator
            ):
                explicit_matches.append(match)
        if explicit_matches:
            for index, match in enumerate(explicit_matches):
                next_requirement = (
                    explicit_matches[index + 1].start()
                    if index + 1 < len(explicit_matches)
                    else len(source_text)
                )
                next_section = next(
                    (
                        boundary
                        for boundary in section_boundaries
                        if boundary > match.start()
                    ),
                    len(source_text),
                )
                stop = min(next_requirement, next_section)
                evidence = re.sub(r"\s+", " ", source_text[match.start():stop]).strip()
                statement = re.sub(r"\s+", " ", source_text[match.end():stop]).strip()
                if not statement:
                    continue
                candidates.append(
                    {
                        "requirement_id": match.group(1),
                        "requirement_statement": statement,
                        "source_page": segment.page_number,
                        "source_evidence": evidence,
                        "source_location": segment.source_location,
                    }
                )
            continue

        numbered_matches = list(numbered_item.finditer(source_text))
        statements = []
        if numbered_matches:
            for index, match in enumerate(numbered_matches):
                stop = numbered_matches[index + 1].start() if index + 1 < len(numbered_matches) else len(source_text)
                evidence = re.sub(r"\s+", " ", source_text[match.start():stop]).strip()
                statement = numbered_item.sub("", evidence, count=1).strip()
                if statement:
                    statements.append((statement, evidence))
        else:
            for line in source_text.splitlines():
                for sentence in re.split(r"(?<=[.!?])\s+", line.strip()):
                    sentence = re.sub(r"\s+", " ", sentence).strip()
                    if sentence and requirement_terms.search(sentence):
                        statements.append((sentence, sentence))

        for statement, evidence in statements:
            normalized = statement.casefold()
            if normalized in seen:
                continue
            seen.add(normalized)
            candidates.append(
                {
                    "requirement_id": f"REQ-{len(candidates) + 1:03d}",
                    "requirement_statement": statement,
                    "source_page": segment.page_number,
                    "source_evidence": evidence,
                    "source_location": segment.source_location,
                }
            )

    return candidates
