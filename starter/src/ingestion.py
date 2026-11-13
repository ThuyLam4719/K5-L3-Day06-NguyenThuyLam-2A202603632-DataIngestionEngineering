"""Read and normalize source data. TODO: implement functions."""
from pathlib import Path
from .models import DocumentPage
import re
from pypdf import PdfReader
import unicodedata

def load_pdf(path: Path, document_id: str, source: str) -> list[DocumentPage]:
    """TODO: extract each physical page; keep its page number and source.

    Detect and record pages with no text. OCR, when needed, is a separate step.
    """
    reader = PdfReader(path)
    pages = []
    active_section = None

    chapter_pattern = re.compile(r"^\s*CHƯƠNG\s+(\d+)\b(.*)$", re.IGNORECASE)
    section_pattern = re.compile(
        r"^\s*(\d+(?:\.\d+){0,3})\.?\s+([^\d].+?)\s*$"
    )

    for page_number, pdf_page in enumerate(reader.pages, start=1):
        extraction_error = None

        try:
            text = normalize_text(pdf_page.extract_text() or "")
        except Exception as exc:
            text = ""
            extraction_error = str(exc)

        section_spans = []
        offset = 0

        for line in text.splitlines(keepends=True):
            line_text = line.strip()

            chapter_match = chapter_pattern.match(line_text)
            section_match = section_pattern.match(line_text)

            if chapter_match:
                active_section = f"CHƯƠNG {chapter_match.group(1)}"
                section_spans.append({
                    "start_char": offset,
                    "section": active_section,
                })
            elif section_match:
                active_section = section_match.group(1)
                section_spans.append({
                    "start_char": offset,
                    "section": active_section,
                })

            offset += len(line)

        if active_section and (
            not section_spans or section_spans[0]["start_char"] != 0
        ):
            section_spans.insert(0, {
                "start_char": 0,
                "section": active_section,
            })

        if extraction_error:
            status = "error"
            print(
                f"[INGEST][ERROR] page={page_number} "
                f"source={source} reason={extraction_error}"
            )
        elif not text:
            status = "empty"
            print(f"[INGEST][EMPTY] page={page_number} source={source}")
        else:
            status = "ok"

        pages.append(
            DocumentPage(
                document_id=document_id,
                source=source,
                page=page_number,
                text=text,
                metadata={
                    "status": status,
                    "extraction_error": extraction_error,
                    "section": active_section,
                    "section_spans": section_spans,
                    "character_count": len(text),
                },
            )
        )

    return pages
    


def normalize_text(text: str) -> str:
    """TODO: normalize Unicode and whitespace without discarding useful structure."""
    text = unicodedata.normalize("NFC", text or "")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t\f\v]+", " ", text)
    text = re.sub(r"\n[ \t]*\n(?:[ \t]*\n)+", "\n\n", text)

    return text.strip()