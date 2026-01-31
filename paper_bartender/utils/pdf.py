"""PDF reading utilities."""

import os
from pathlib import Path
from typing import Optional


def read_pdf(pdf_path: str, max_pages: Optional[int] = None) -> str:
    """Read text content from a PDF file.

    Args:
        pdf_path: Path to the PDF file.
        max_pages: Maximum number of pages to read (None for all).

    Returns:
        Extracted text content from the PDF.

    Raises:
        FileNotFoundError: If the PDF file doesn't exist.
        ValueError: If the file is not a valid PDF.
    """
    path = Path(pdf_path).expanduser().resolve()

    if not path.exists():
        raise FileNotFoundError(f'PDF file not found: {pdf_path}')

    if not path.suffix.lower() == '.pdf':
        raise ValueError(f'Not a PDF file: {pdf_path}')

    import fitz  # pymupdf

    try:
        doc = fitz.open(str(path))
    except Exception as e:
        raise ValueError(f'Failed to open PDF: {e}') from e

    text_parts = []
    pages_to_read = min(len(doc), max_pages) if max_pages else len(doc)

    for page_num in range(pages_to_read):
        page = doc[page_num]
        text = page.get_text()
        if text.strip():
            text_parts.append(f'--- Page {page_num + 1} ---\n{text}')

    doc.close()

    return '\n\n'.join(text_parts)


def get_pdf_summary(pdf_path: str, max_chars: int = 8000) -> str:
    """Get a summary of PDF content suitable for LLM context.

    Args:
        pdf_path: Path to the PDF file.
        max_chars: Maximum characters to return.

    Returns:
        Truncated text content from the PDF.
    """
    text = read_pdf(pdf_path, max_pages=10)

    if len(text) > max_chars:
        # Truncate but try to end at a sentence
        text = text[:max_chars]
        last_period = text.rfind('.')
        if last_period > max_chars * 0.8:
            text = text[:last_period + 1]
        text += '\n\n[... content truncated ...]'

    return text


def analyze_paper_sections(pdf_path: str) -> dict[str, bool]:
    """Analyze which sections exist in the paper.

    Args:
        pdf_path: Path to the PDF file.

    Returns:
        Dictionary indicating presence of common sections.
    """
    text = read_pdf(pdf_path).lower()

    sections = {
        'abstract': any(kw in text for kw in ['abstract']),
        'introduction': any(kw in text for kw in ['introduction', '1 introduction', '1. introduction']),
        'related_work': any(kw in text for kw in ['related work', 'background', 'literature review']),
        'methodology': any(kw in text for kw in ['method', 'approach', 'methodology', 'our approach']),
        'experiments': any(kw in text for kw in ['experiment', 'evaluation', 'results', 'empirical']),
        'discussion': any(kw in text for kw in ['discussion', 'analysis']),
        'conclusion': any(kw in text for kw in ['conclusion', 'summary', 'future work']),
        'references': any(kw in text for kw in ['references', 'bibliography']),
    }

    return sections
