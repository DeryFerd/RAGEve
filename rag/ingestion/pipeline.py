from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import pandas as pd
import pymupdf
from docx import Document
from PIL import Image

from backend.config import settings
from rag.chunking.adaptive import ChunkProfile  # for type hint
from rag.deepdoc.layout_parser import PageLayout  # for type hint
from rag.ingestion.doc_converter import ConversionResult, convert_doc_to_docx
from rag.ingestion.ocr import get_ocr_engine, ocr_pdf

_log = logging.getLogger(__name__)

# Supported file extensions for ingestion
SUPPORTED_EXTENSIONS = {
    ".pdf",
    ".doc",
    ".docx",
    ".xlsx",
    ".png",
    ".jpg",
    ".jpeg",
    ".bmp",
    ".tiff",
}


class Extractors:
    @staticmethod
    def from_pdf(file_path: Path) -> str:
        """Extract text from PDF using PyMuPDF, with OCR fallback for scanned PDFs."""
        lines: list[str] = []
        with pymupdf.open(file_path) as doc:
            for page in doc:
                lines.append(page.get_text("text"))
        text = "\n".join(lines).strip()

        if len(text) < settings.ocr_threshold_chars:
            _log.info(
                "PDF %s appears scanned (only %d chars), applying OCR",
                file_path.name,
                len(text),
            )
            engine = get_ocr_engine(settings.ocr_engine)
            ocr_text = ocr_pdf(file_path, engine)
            if ocr_text:
                return ocr_text
            _log.warning(
                "OCR returned no text for %s; using original extraction", file_path.name
            )

        return text

    @staticmethod
    def from_docx(file_path: Path) -> str:
        doc = Document(str(file_path))
        paragraphs = [p.text for p in doc.paragraphs if p.text and p.text.strip()]
        return "\n".join(paragraphs).strip()

    @staticmethod
    def from_doc(file_path: Path) -> tuple[str, ConversionResult]:
        """
        Convert .doc -> .docx using available toolchain, then extract text.
        Returns (extracted_text, conversion_result).
        """
        result = convert_doc_to_docx(file_path)

        if result.success and result.output_path:
            # LibreOffice succeeded: read the produced .docx
            text = Extractors.from_docx(result.output_path)
            return text, result

        if result.success and result.output_path is None:
            # catdoc or antiword succeeded: text already in message / we need to re-extract
            # Re-run the tool to get the actual text
            text = _re_extract_with_fallback_tool(file_path, result.converter)
            return text, result

        # All failed
        return "", result

    @staticmethod
    def from_xlsx(file_path: Path) -> str:
        book = pd.read_excel(file_path, sheet_name=None)
        chunks: list[str] = []
        for sheet_name, frame in book.items():
            chunks.append(f"[Sheet: {sheet_name}]")
            chunks.append(frame.fillna("").to_csv(index=False))
        return "\n".join(chunks).strip()

    @staticmethod
    def from_image(file_path: Path) -> str:
        image = Image.open(file_path)
        engine = get_ocr_engine(settings.ocr_engine)
        return engine.image_to_string(image)


def _re_extract_with_fallback_tool(src: Path, converter) -> str:
    """
    Re-run the fallback tool (catdoc/antiword) to get text since
    convert_doc_to_docx already validated success but did not return text.
    """
    import subprocess

    tool_map = {
        "catdoc": ["catdoc", "-d", "utf-8", str(src)],
        "antiword": ["antiword", "-f", str(src)],
    }

    tool_cmd = tool_map.get(converter.value)
    if not tool_cmd:
        return ""

    try:
        result = subprocess.run(
            tool_cmd,
            capture_output=True,
            timeout=30,
        )
        if result.returncode == 0:
            return result.stdout.decode("utf-8", errors="replace").strip()
    except Exception:
        pass

    return ""


def extract_text(
    file_path: Path,
    *,
    enable_column_detection: bool = True,
    enable_structured_tables: bool = True,
) -> tuple[str, dict]:
    """
    Extract text from a file, routing to the correct extractor.
    Returns (extracted_text, extraction_metadata).

    For PDFs, uses enhanced layout-aware parsing if either column detection
    or structured tables is enabled.
    """
    ext = file_path.suffix.lower()

    if ext == ".pdf":
        text = ""
        meta: dict = {}

        # Try enhanced parsing if at least one feature is enabled
        if enable_column_detection or enable_structured_tables:
            try:
                from rag.deepdoc.layout_parser import (
                    layout_to_readable_text,
                    parse_pdf_layout,
                )

                layouts = parse_pdf_layout(
                    file_path,
                    enable_column_detection=enable_column_detection,
                    enable_structured_tables=enable_structured_tables,
                )
                text = layout_to_readable_text(layouts, include_hierarchy=True)
                meta = {
                    "extractor": "enhanced_pdf",
                    "layout_aware": True,
                    "pages": len(layouts),
                }
                # Count columns detected
                column_counts = set()
                for page in layouts:
                    for block in page.blocks:
                        if block.column_index is not None:
                            column_counts.add(block.column_index)
                meta["columns_detected"] = len(column_counts)
            except Exception as e:
                logging.getLogger("rag.ingestion.pipeline").warning(
                    "Enhanced PDF parsing failed, falling back to basic: %s", e
                )
                # Reset to ensure fallback runs
                text = ""
                meta = {}

        # If enhanced parsing was not attempted or produced insufficient text, fallback
        if not text or len(text) < settings.ocr_threshold_chars:
            text = Extractors.from_pdf(file_path)
            # Determine if OCR was used: from_pdf returns either pure pymupdf or OCR text
            # We can't easily know; but we can hint based on length: if original pymupdf extraction would be tiny
            # Simpler: just report fallback
            meta = {"extractor": f"{settings.ocr_engine}-ocr", "layout_aware": False}
        return text, meta

    if ext == ".doc":
        text, conv_result = Extractors.from_doc(file_path)
        meta = {
            "extractor": "doc_converter",
            "converter": conv_result.converter.value,
            "converted": conv_result.success,
            "message": conv_result.message,
            "error": conv_result.error,
        }
        return text, meta

    if ext == ".docx":
        text = Extractors.from_docx(file_path)
        return text, {"extractor": "python-docx"}

    if ext == ".xlsx":
        text = Extractors.from_xlsx(file_path)
        return text, {"extractor": "pandas"}

    if ext in {".png", ".jpg", ".jpeg", ".bmp", ".tiff"}:
        text = Extractors.from_image(file_path)
        engine_name = settings.ocr_engine
        return text, {"extractor": f"{engine_name}-ocr"}

    raise ValueError(f"Unsupported file extension: {ext}")


def run_deepdoc_ingestion(
    file_path: Path,
    *,
    chunk_size: int | None = None,
    chunk_overlap: int | None = None,
    max_tokens_per_chunk: int | None = None,
    force_profile: "ChunkProfile | None" = None,
) -> dict:
    """
    Full deepdoc ingestion pipeline for a single file.

    Steps:
      1. Extract text using format-specific extractor (with enhanced PDF if enabled)
      2. If PDF: layout parsing included if features enabled
      3. Compute quality signals and score
      4. Select chunk profile (auto or forced)
      5. Run adaptive chunking (hierarchical if enabled and layouts available)
      6. Return structured report with analysis

    Args:
      file_path: path to uploaded file
      chunk_size / chunk_overlap / max_tokens_per_chunk: override auto settings
      force_profile: bypass auto-selection and force a specific chunk profile

    Returns:
      Dict with ingestion results, chunks, quality report, etc.
    """
    from backend.config import settings
    from rag.chunking.adaptive import adaptive_chunk_text
    from rag.deepdoc.quality_scorer import score_and_select_profile

    if file_path.suffix.lower() not in {
        ".pdf",
        ".doc",
        ".docx",
        ".xlsx",
        ".png",
        ".jpg",
        ".jpeg",
        ".bmp",
        ".tiff",
    }:
        raise ValueError(f"Unsupported file type: {file_path.suffix}")

    t0 = __import__("time").monotonic()
    _log = __import__("logging").getLogger("rag.ingestion.pipeline")

    # 1. Text extraction + metadata (use config flags)
    text, extraction_meta = extract_text(
        file_path,
        enable_column_detection=settings.enable_column_detection,
        enable_structured_tables=settings.enable_structured_tables,
    )
    _log.info("Extracted text: %d chars", len(text))

    # 2. Layout parsing (if enhanced PDF and layouts were extracted)
    layouts: list[PageLayout] = []
    raw_text = text
    # Check if extraction used enhanced layout (includes layouts in metadata implicitly)
    # We can't easily get layouts from extract_text, so we re-run layout parsing if needed?
    # Actually extract_text already did parse_pdf_layout and returned text from layouts.
    # But we need the layouts object for hierarchical chunking. We could have extract_text return it.
    # For now, re-run parse_pdf_layout if it's a PDF and hierarchical chunking is enabled.
    # This is slightly inefficient but keeps functions pure.
    if file_path.suffix.lower() == ".pdf":
        if settings.enable_hierarchical_chunking:
            try:
                from rag.deepdoc.layout_parser import (
                    layout_to_readable_text,
                    parse_pdf_layout,
                )

                # We already have raw_text from extract_text; but we need layouts.
                # Re-run parse_pdf_layout to get layouts (it's fast)
                layouts = parse_pdf_layout(
                    file_path,
                    enable_column_detection=settings.enable_column_detection,
                    enable_structured_tables=settings.enable_structured_tables,
                )
                # Sanity check: raw_text should match layout_to_readable_text(layouts)
                # If not, use layouts to regenerate raw_text
                generated_text = layout_to_readable_text(
                    layouts, include_hierarchy=True
                )
                if (
                    abs(len(generated_text) - len(raw_text)) < len(raw_text) * 0.1
                ):  # within 10%
                    raw_text = generated_text
                # else keep raw_text from extract_text to avoid discrepancy
            except Exception as e:
                _log.warning("Layout parsing for hierarchical chunking failed: %s", e)
                layouts = []
        # else: we don't need layouts, raw_text is already from extract_text

    # 3. Quality scoring
    quality_report = score_and_select_profile(raw_text)
    signals = quality_report.signals
    selected_profile = force_profile or quality_report.profile.profile
    config = quality_report.profile

    _log.info(
        "Profile=%s quality_score=%.3f",
        selected_profile.value,
        quality_report.quality_score,
    )

    eff_chunk_size = chunk_size if chunk_size is not None else config.chunk_size
    eff_overlap = chunk_overlap if chunk_overlap is not None else config.chunk_overlap
    eff_tokens = (
        max_tokens_per_chunk
        if max_tokens_per_chunk is not None
        else config.max_tokens_per_chunk
    )

    # 4. Adaptive chunking with layouts if hierarchical chunking enabled
    chunks_with_blocks = adaptive_chunk_text(
        raw_text,
        profile=selected_profile,
        override_size=eff_chunk_size,
        override_overlap=eff_overlap,
        override_tokens=eff_tokens,
        layouts=(
            layouts if (layouts and settings.enable_hierarchical_chunking) else None
        ),
    )
    chunks = chunks_with_blocks  # list[tuple[str, list[Block]]]
    chunk_count = len(chunks)
    _log.info("Created %d chunks", chunk_count)

    # 5. Chunk analysis (optional)
    chunk_analysis: list[dict] = []

    # 6. Document-level analysis (optional)
    doc_analysis: dict = {}

    # 7. Build quality report dict
    quality_dict = {
        "quality_score": quality_report.quality_score,
        "selected_profile": selected_profile.value,
        "profile_reason": config.reason,
        "signals": {
            "alpha_ratio": signals.alpha_ratio,
            "ocr_noise_ratio": signals.ocr_noise_ratio,
            "broken_line_ratio": signals.broken_line_ratio,
            "header_footer_ratio": signals.header_footer_ratio,
            "table_density": signals.table_density,
            "avg_sentence_length": signals.avg_sentence_length,
            "language_script_changes": signals.language_script_changes,
            "repeated_word_ratio": signals.repeated_word_ratio,
            "code_delimiter_ratio": signals.code_delimiter_ratio,
            "issue_tags": signals.issue_tags,
        },
    }

    # 8. Layout summary
    layout_summary = None
    if layouts:
        block_counts: dict[str, int] = {}
        column_dist: dict[int, int] = {}
        for page in layouts:
            for block in page.blocks:
                block_counts[block.block_type.value] = (
                    block_counts.get(block.block_type.value, 0) + 1
                )
                if block.column_index is not None:
                    column_dist[block.column_index] = (
                        column_dist.get(block.column_index, 0) + 1
                    )

        layout_summary = {
            "pages": len(layouts),
            "total_blocks": sum(block_counts.values()),
            "blocks_by_type": block_counts,
            "columns_detected": len(column_dist),
            "column_distribution": column_dist,
        }

    elapsed = __import__("time").monotonic() - t0
    _log.info("Ingestion completed in %.2fs: %s", elapsed, file_path.name)

    return {
        "text": raw_text,
        "chunks": chunks,
        "extraction": extraction_meta,
        "document_analysis": doc_analysis,
        "chunk_analysis": chunk_analysis,
        "quality_report": quality_dict,
        "layout_summary": layout_summary,
        "chunk_params": {
            "chunk_size": eff_chunk_size,
            "chunk_overlap": eff_overlap,
            "max_tokens_per_chunk": eff_tokens,
        },
    }
