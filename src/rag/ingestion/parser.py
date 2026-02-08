from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path

from rag.config import Settings, get_settings

logger = logging.getLogger(__name__)


@dataclass
class Block:
    doc_id: str
    page: int
    chunk_type: str
    text: str
    confidence: float
    section: str | None = None
    table_id: str | None = None


@dataclass
class DocumentParseResult:
    blocks: list[Block]
    parse_meta: dict[str, object] = field(default_factory=dict)


class OCRConfigurationError(RuntimeError):
    code = "OCR_CONFIG_INVALID"

    def __init__(self, missing_fields: list[str], missing_paths: list[str]):
        self.missing_fields = missing_fields
        self.missing_paths = missing_paths
        problems: list[str] = []
        if missing_fields:
            problems.append(f"missing env vars: {', '.join(missing_fields)}")
        if missing_paths:
            problems.append(f"missing files: {', '.join(missing_paths)}")
        message = (
            "Docling OCR configuration is invalid. "
            + " | ".join(problems)
            + ". Configure valid OCR model asset paths in .env."
        )
        super().__init__(message)


class DoclingParseError(RuntimeError):
    code = "DOCLING_PARSE_FAILED"


class PDFParseError(RuntimeError):
    code = "PDF_PARSE_FAILED"


def _with_meta(result: DocumentParseResult, **meta: object) -> DocumentParseResult:
    result.parse_meta.update(meta)
    return result


def _text_block_chars(result: DocumentParseResult) -> int:
    return sum(len((block.text or "").strip()) for block in result.blocks)


def _parse_with_pymupdf(path: Path) -> DocumentParseResult:
    import fitz

    blocks: list[Block] = []
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
    blocks: list[Block] = []
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
            text = "\n".join([line[1] for line in result])

        confidence = 0.9 if text else 0.0

        blocks: list[Block] = [
            Block(
                doc_id=path.name,
                page=1,
                chunk_type="image_text",
                text=text or f"[IMAGE_FILE:{path.name} (No text detected)]",
                confidence=confidence,
            )
        ]
        return DocumentParseResult(blocks=blocks)
    except Exception as exc:
        logger.warning("OCR failed for %s: %s", path, exc)
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


def _required_ocr_paths(settings: Settings) -> dict[str, str]:
    return {
        "DOCLING_OCR_DET_MODEL_PATH": settings.docling_ocr_det_model_path,
        "DOCLING_OCR_CLS_MODEL_PATH": settings.docling_ocr_cls_model_path,
        "DOCLING_OCR_REC_MODEL_PATH": settings.docling_ocr_rec_model_path,
        "DOCLING_OCR_REC_KEYS_PATH": settings.docling_ocr_rec_keys_path,
        "DOCLING_OCR_FONT_PATH": settings.docling_ocr_font_path,
    }


def validate_docling_ocr_assets(settings: Settings | None = None) -> dict[str, object]:
    runtime_settings = settings or get_settings()
    required = _required_ocr_paths(runtime_settings)

    missing_fields = [name for name, value in required.items() if not str(value).strip()]
    missing_paths = [
        str(Path(value).expanduser())
        for value in required.values()
        if str(value).strip() and not Path(value).expanduser().exists()
    ]

    if missing_fields or missing_paths:
        raise OCRConfigurationError(missing_fields=missing_fields, missing_paths=missing_paths)

    resolved_paths = {
        name: str(Path(value).expanduser().resolve())
        for name, value in required.items()
    }
    return {"valid": True, "model_paths": resolved_paths}


def _build_docling_converter(settings: Settings, enable_ocr: bool | None = None):
    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.pipeline_options import PdfPipelineOptions, RapidOcrOptions
    from docling.document_converter import DocumentConverter, ImageFormatOption, PdfFormatOption

    if settings.docling_ocr_force:
        validate_docling_ocr_assets(settings)
        det_path = str(Path(settings.docling_ocr_det_model_path).expanduser().resolve())
        cls_path = str(Path(settings.docling_ocr_cls_model_path).expanduser().resolve())
        rec_path = str(Path(settings.docling_ocr_rec_model_path).expanduser().resolve())
        keys_path = str(Path(settings.docling_ocr_rec_keys_path).expanduser().resolve())
        font_path = str(Path(settings.docling_ocr_font_path).expanduser().resolve())

        ocr_options = RapidOcrOptions(
            det_model_path=det_path,
            cls_model_path=cls_path,
            rec_model_path=rec_path,
            rec_keys_path=keys_path,
            font_path=font_path,
            rec_font_path=font_path,
            print_verbose=False,
        )
        pipeline_options = PdfPipelineOptions(do_ocr=True, ocr_options=ocr_options)
        format_options = {
            InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options),
            InputFormat.IMAGE: ImageFormatOption(pipeline_options=pipeline_options),
        }
        return DocumentConverter(format_options=format_options)

    auto_ocr = bool(settings.docling_ocr_auto) if enable_ocr is None else bool(enable_ocr)
    if auto_ocr:
        pipeline_options = PdfPipelineOptions(do_ocr=True)
    else:
        pipeline_options = PdfPipelineOptions(do_ocr=False)
    format_options = {
        InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options),
        InputFormat.IMAGE: ImageFormatOption(pipeline_options=pipeline_options),
    }
    return DocumentConverter(format_options=format_options)


def _extract_docling_blocks(path: Path, conversion_result) -> list[Block]:
    blocks: list[Block] = []

    document = getattr(conversion_result, "document", None)
    pages = getattr(document, "pages", []) if document else []
    for page_idx, page in enumerate(pages, start=1):
        elements = getattr(page, "elements", []) or []
        for element in elements:
            text = str(getattr(element, "text", "") or "").strip()
            if not text:
                continue
            category = str(
                getattr(element, "category", "")
                or getattr(element, "label", "")
                or "paragraph"
            )
            confidence = float(getattr(element, "confidence", 0.85) or 0.85)
            section = getattr(element, "section", None)
            blocks.append(
                Block(
                    doc_id=path.name,
                    page=page_idx,
                    chunk_type=category,
                    text=text,
                    confidence=confidence,
                    section=str(section) if section else None,
                )
            )

    if blocks:
        return blocks

    if document is not None:
        export_to_markdown = getattr(document, "export_to_markdown", None)
        if callable(export_to_markdown):
            markdown = str(export_to_markdown() or "").strip()
            if markdown:
                return [
                    Block(
                        doc_id=path.name,
                        page=1,
                        chunk_type="paragraph",
                        text=markdown,
                        confidence=0.8,
                    )
                ]

    return []


def _parse_with_docling(
    path: Path, settings: Settings, enable_ocr: bool | None = None
) -> DocumentParseResult:
    converter = _build_docling_converter(settings, enable_ocr=enable_ocr)
    result = converter.convert(path)
    blocks = _extract_docling_blocks(path, result)
    if not blocks:
        raise DoclingParseError(f"Docling parsed no text blocks for {path}")
    return DocumentParseResult(blocks=blocks)


def _parse_pdf_by_strategy(path: Path, settings: Settings) -> DocumentParseResult:
    strategy = str(getattr(settings, "pdf_parse_strategy", "fast_text_first") or "fast_text_first")
    min_chars = max(1, int(getattr(settings, "pdf_text_min_chars", 300) or 300))

    def _pymupdf_result() -> DocumentParseResult:
        result = _parse_with_pymupdf(path)
        chars = _text_block_chars(result)
        return _with_meta(result, parser_used="pymupdf", text_chars=chars)

    if strategy == "docling_first":
        try:
            result = _parse_with_docling(path, settings, enable_ocr=True)
            return _with_meta(
                result,
                parser_used="docling",
                parser_strategy=strategy,
                ocr_enabled=True,
            )
        except Exception as exc:
            fallback = _pymupdf_result()
            return _with_meta(
                fallback,
                parser_strategy=strategy,
                fallback_used=True,
                fallback_from="docling",
                fallback_error_code=DoclingParseError.code,
                fallback_error=str(exc),
            )

    if strategy == "race":
        with ThreadPoolExecutor(max_workers=2) as ex:
            future_docling = ex.submit(_parse_with_docling, path, settings, True)
            future_pymupdf = ex.submit(_pymupdf_result)
            docling_result: DocumentParseResult | None = None
            pymupdf_result: DocumentParseResult | None = None
            docling_exc: Exception | None = None
            try:
                docling_result = future_docling.result()
            except Exception as exc:
                docling_exc = exc
            try:
                pymupdf_result = future_pymupdf.result()
            except Exception:
                pymupdf_result = DocumentParseResult(blocks=[])

        chars = _text_block_chars(pymupdf_result)
        if chars >= min_chars and pymupdf_result.blocks:
            return _with_meta(
                pymupdf_result,
                parser_strategy=strategy,
                parser_used="pymupdf",
                text_chars=chars,
                fallback_used=docling_result is None,
            )
        if docling_result and docling_result.blocks:
            return _with_meta(
                docling_result,
                parser_strategy=strategy,
                parser_used="docling",
                fallback_used=True,
                fallback_from="pymupdf",
                ocr_enabled=True,
            )
        if pymupdf_result.blocks:
            return _with_meta(
                pymupdf_result,
                parser_strategy=strategy,
                parser_used="pymupdf",
                text_chars=chars,
                fallback_used=True,
                fallback_from="docling",
                fallback_error_code=getattr(docling_exc, "code", DoclingParseError.code),
            )
        raise PDFParseError(f"No parser could extract text from {path}")

    pymupdf_result = _pymupdf_result()
    chars = int(pymupdf_result.parse_meta.get("text_chars", 0) or 0)
    if chars >= min_chars and pymupdf_result.blocks:
        return _with_meta(
            pymupdf_result,
            parser_strategy="fast_text_first",
            parser_used="pymupdf",
            text_chars=chars,
        )

    try:
        docling_result = _parse_with_docling(path, settings, enable_ocr=True)
        return _with_meta(
            docling_result,
            parser_strategy="fast_text_first",
            parser_used="docling",
            fallback_used=True,
            fallback_from="pymupdf",
            text_chars=chars,
            ocr_enabled=True,
        )
    except Exception as exc:
        if pymupdf_result.blocks:
            return _with_meta(
                pymupdf_result,
                parser_strategy="fast_text_first",
                parser_used="pymupdf",
                text_chars=chars,
                fallback_used=True,
                fallback_from="docling",
                fallback_error_code=DoclingParseError.code,
                fallback_error=str(exc),
            )
        raise DoclingParseError(f"Docling parsing failed for {path}: {exc}") from exc


def parse_document(path: Path, settings: Settings | None = None) -> DocumentParseResult:
    path = path.resolve()
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    runtime_settings = settings or get_settings()
    suffix = path.suffix.lower()

    if runtime_settings.docling_ocr_force:
        try:
            result = _parse_with_docling(path, runtime_settings, enable_ocr=True)
            return _with_meta(
                result,
                parser_used="docling",
                parser_strategy="docling_forced",
                ocr_enabled=True,
            )
        except OCRConfigurationError:
            raise
        except Exception as exc:
            raise DoclingParseError(f"Docling parsing failed for {path}: {exc}") from exc

    if suffix == ".pdf":
        return _parse_pdf_by_strategy(path, runtime_settings)

    try:
        result = _parse_with_docling(path, runtime_settings, enable_ocr=True)
        return _with_meta(
            result,
            parser_used="docling",
            parser_strategy="docling_first",
            ocr_enabled=True,
        )
    except Exception as exc:
        logger.warning(
            "Docling parsing failed for %s, falling back to simple parsers. Error: %s",
            path,
            exc,
        )

    if suffix == ".docx":
        return _with_meta(_parse_docx(path), parser_used="python-docx", parser_strategy="fallback")
    if suffix in {".png", ".jpg", ".jpeg"}:
        return _with_meta(_parse_image(path), parser_used="rapidocr", parser_strategy="fallback")
    return _with_meta(
        DocumentParseResult(blocks=[]),
        parser_used="none",
        parser_strategy="fallback",
    )
