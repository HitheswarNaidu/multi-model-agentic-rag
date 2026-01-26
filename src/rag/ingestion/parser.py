import logging
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

import fitz
from docling.document_converter import DocumentConverter

logger = logging.getLogger(__name__)


@dataclass
class Block:
    doc_id: str
    page: int
    chunk_type: str
    text: str
    confidence: float
    section: Optional[str] = None
    table_id: Optional[str] = None


@dataclass
class DocumentParseResult:
    blocks: List[Block]


def _parse_with_pymupdf(path: Path) -> DocumentParseResult:
    blocks: List[Block] = []
    with fitz.open(path) as doc:
        for page_index, page in enumerate(doc, start=1):
            text = page.get_text("text") or ""
            if text.strip():
                blocks.append(
                    Block(
                        doc_id=path.name,
                        page=page_index,
                        chunk_type="paragraph",
                        text=text.strip(),
                        confidence=1.0,
                    )
                )
    return DocumentParseResult(blocks=blocks)


def _parse_docx(path: Path) -> DocumentParseResult:
    from docx import Document

    doc = Document(str(path))
    text_parts = [p.text.strip() for p in doc.paragraphs if p.text and p.text.strip()]
    text = "\n".join(text_parts).strip()
    blocks: List[Block] = []
    if text:
        blocks.append(
            Block(
                doc_id=path.name,
                page=1,
                chunk_type="paragraph",
                text=text,
                confidence=1.0,
            )
        )
    return DocumentParseResult(blocks=blocks)


def _parse_image(path: Path) -> DocumentParseResult:
    try:
        from rapidocr_onnxruntime import RapidOCR
        engine = RapidOCR()
        result, _ = engine(str(path))
        if not result:
            text = ""
        else:
            # result is list of [coords, text, score]
            text = "\n".join([line[1] for line in result])
            
        confidence = 0.9 if text else 0.0
        
        blocks: List[Block] = [
            Block(
                doc_id=path.name,
                page=1,
                chunk_type="image_text", # Distinct type for OCR content
                text=text or f"[IMAGE_FILE:{path.name} (No text detected)]",
                confidence=confidence,
            )
        ]
        return DocumentParseResult(blocks=blocks)
    except Exception as e:
        logger.warning(f"OCR failed for {path}: {e}")
        # Fallback to placeholder
        blocks = [
            Block(
                doc_id=path.name,
                page=1,
                chunk_type="figure",
                text=f"[IMAGE_FILE:{path.name}]",
                confidence=0.2,
            )
        ]
        return DocumentParseResult(blocks=blocks)


def parse_document(path: Path) -> DocumentParseResult:
    path = path.resolve()
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")
    # Primary: docling conversion
    try:
        converter = DocumentConverter()
        result = converter.convert(path)
        blocks: List[Block] = []
        for page_idx, page in enumerate(result.document.pages, start=1):
            for element in page.elements:
                text = getattr(element, "text", "") or ""
                if not text.strip():
                    continue
                chunk_type = getattr(element, "category", "paragraph") or "paragraph"
                blocks.append(
                    Block(
                        doc_id=path.name,
                        page=page_idx,
                        chunk_type=str(chunk_type),
                        text=text.strip(),
                        confidence=getattr(element, "confidence", 0.8) or 0.8,
                    )
                )
        if blocks:
            return DocumentParseResult(blocks=blocks)
    except Exception as e:
        logger.warning(f"Docling parsing failed for {path}, falling back to simple parsers. Error: {e}")
        # Fall back to lightweight parsers
        pass

    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return _parse_with_pymupdf(path)
    if suffix == ".docx":
        return _parse_docx(path)
    if suffix in {".png", ".jpg", ".jpeg"}:
        return _parse_image(path)
    return DocumentParseResult(blocks=[])
