"""Implement fixed-size and structure-aware chunking."""
from .models import Chunk, DocumentPage
import hashlib
import re

def fixed_size(page: DocumentPage, size: int, overlap: int) -> list[Chunk]:
    """TODO: split text into overlapping windows and retain page metadata."""

    if size <= 0:
        raise ValueError("size phải lớn hơn 0")
    if overlap < 0 or overlap >= size:
        raise ValueError("overlap phải nằm trong khoảng 0 đến size - 1")

    text = page.text
    chunks = []
    step = size - overlap

    def section_for(start_char: int) -> str | None:
        section = page.metadata.get("section")
        for span in page.metadata.get("section_spans", []):
            if span["start_char"] <= start_char:
                section = span["section"]
            else:
                break
        return section

    for start in range(0, len(text), step):
        end = min(start + size, len(text))
        chunk_text = text[start:end]

        if not chunk_text.strip():
            continue

        section = section_for(start)
        identity = (
            f"{page.document_id}|fixed|{page.page}|{start}|{end}"
        )
        chunk_id = hashlib.sha1(identity.encode("utf-8")).hexdigest()

        metadata = {
            key: value
            for key, value in page.metadata.items()
            if key != "section_spans"
        }
        metadata["section"] = section
        metadata["start_char"] = start
        metadata["end_char"] = end

        chunks.append(
            Chunk(
                chunk_id=f"A-{chunk_id}",
                document_id=page.document_id,
                source=page.source,
                page=page.page,
                text=chunk_text,
                metadata=metadata,
            )
        )

        if end == len(text):
            break

    return chunks

def by_paragraph(page: DocumentPage, max_size: int) -> list[Chunk]:
    """TODO: group paragraphs, split oversized paragraphs and retain metadata."""
    if max_size <= 0:
        raise ValueError("max_size phải lớn hơn 0")

    text = page.text
    chunks = []

    def section_for(start_char: int) -> str | None:
        section = page.metadata.get("section")
        for span in page.metadata.get("section_spans", []):
            if span["start_char"] <= start_char:
                section = span["section"]
            else:
                break
        return section

    # Tách đoạn văn theo dòng trống, đồng thời giữ vị trí trong trang.
    paragraphs = []
    cursor = 0

    for paragraph in re.split(r"\n\s*\n", text):
        if not paragraph.strip():
            cursor += len(paragraph) + 2
            continue

        start = text.find(paragraph, cursor)
        if start < 0:
            start = cursor

        end = start + len(paragraph)
        paragraphs.append((start, end, paragraph.strip()))
        cursor = end

    # Chia đoạn quá dài tại khoảng trắng gần giới hạn nhất.
    units = []
    for start, end, paragraph in paragraphs:
        remaining = paragraph
        current_start = start

        while len(remaining) > max_size:
            cut = remaining.rfind(" ", 0, max_size + 1)
            if cut <= 0:
                cut = max_size

            part = remaining[:cut].strip()
            if part:
                units.append((current_start, current_start + len(part), part))

            consumed = len(remaining[:cut])
            remaining = remaining[cut:].lstrip()
            current_start += consumed

        if remaining.strip():
            part = remaining.strip()
            units.append((current_start, end, part))

    # Gom các đoạn liền nhau cho đến khi đạt max_size.
    groups = []
    current_parts = []
    current_start = None
    current_end = None
    current_length = 0

    for start, end, part in units:
        separator_length = 2 if current_parts else 0
        proposed_length = current_length + separator_length + len(part)

        if current_parts and proposed_length > max_size:
            groups.append((current_start, current_end, "\n\n".join(current_parts)))
            current_parts = []
            current_start = None
            current_end = None
            current_length = 0
            separator_length = 0

        if not current_parts:
            current_start = start
        current_parts.append(part)
        current_end = end
        current_length += separator_length + len(part)

    if current_parts:
        groups.append((current_start, current_end, "\n\n".join(current_parts)))

    for start, end, chunk_text in groups:
        section = section_for(start)
        identity = (
            f"{page.document_id}|paragraph|{page.page}|{start}|{end}"
        )
        chunk_id = hashlib.sha1(identity.encode("utf-8")).hexdigest()

        metadata = {
            key: value
            for key, value in page.metadata.items()
            if key != "section_spans"
        }
        metadata["section"] = section
        metadata["start_char"] = start
        metadata["end_char"] = end

        chunks.append(
            Chunk(
                chunk_id=f"B-{chunk_id}",
                document_id=page.document_id,
                source=page.source,
                page=page.page,
                text=chunk_text,
                metadata=metadata,
            )
        )

    return chunks
