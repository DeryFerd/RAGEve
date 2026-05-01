from __future__ import annotations

import logging
import tempfile
from pathlib import Path
from typing import Optional

import pandas as pd
import pymupdf
from docx import Document
from PIL import Image

from backend.config_loader import settings
from rag.ingestion.doc_converter import ConversionResult, convert_doc_to_docx
from rag.ingestion.ocr import get_ocr_engine, ocr_pdf

_log = logging.getLogger(__name__)


class Extractors:
    @staticmethod
    def from_pdf(file_path: Path) -> str:
        """Extract text from PDF using PyMuPDF, with OCR fallback for scanned PDFs."""
        # Basic extraction via PyMuPDF
        lines: list[str] = []
        with pymupdf.open(file_path) as doc:
            for page in doc:
                lines.append(page.get_text("text"))
        text = "\n".join(lines).strip()

        # If very little text, assume scanned PDF → OCR each page
        if len(text) < settings.ocr_threshold_chars:
            _log.info(
                "PDF %s appears scanned (only %d chars), applying OCR",
                file_path.name,
                len(text),
            )
            from rag.ingestion.ocr import get_ocr_engine, ocr_pdf

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
        doc = Document(file_path)
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
