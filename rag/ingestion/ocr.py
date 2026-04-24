from __future__ import annotations

import logging
from pathlib import Path
from typing import Protocol, runtime_checkable

from PIL import Image

_log = logging.getLogger("rag.ingestion.ocr")


@runtime_checkable
class OCREngine(Protocol):
    """Protocol for OCR engines."""

    def image_to_string(self, image: Image.Image) -> str: ...


class TesseractOCR:
    """Wrapper for pytesseract."""

    def image_to_string(self, image: Image.Image) -> str:
        import pytesseract

        return pytesseract.image_to_string(image).strip()


class PaddleOCR:
    """Wrapper for PaddleOCR with lazy initialization."""

    def __init__(self, use_angle_cls: bool = True, lang: str = "en", **kwargs) -> None:
        self.use_angle_cls = use_angle_cls
        self.lang = lang
        self.kwargs = kwargs
        self._ocr = None
        self._fallback = None

    def _ensure_initialized(self) -> None:
        if self._ocr is not None:
            return
        try:
            from paddleocr import PaddleOCR as _PaddleOCR

            self._ocr = _PaddleOCR(
                use_angle_cls=self.use_angle_cls, lang=self.lang, **self.kwargs
            )
            _log.info("PaddleOCR initialized (lang=%s)", self.lang)
        except ImportError as e:
            _log.error("PaddleOCR not available: %s", e)
            raise

    def image_to_string(self, image: Image.Image) -> str:
        try:
            self._ensure_initialized()
            # PaddleOCR expects numpy array or file path
            import numpy as np

            img_array = np.array(image)
            result = self._ocr.ocr(img_array)
            # result is list of pages; each page is list of lines with (bbox, (text, confidence))
            if not result or not result[0]:
                return ""
            lines = []
            for line in result[0]:
                text = line[1][0]
                lines.append(text)
            return "\n".join(lines).strip()
        except Exception as e:
            # PaddleOCR may fail due to environment/version issues.
            # Fall back to Tesseract if available.
            _log.warning("PaddleOCR failed (%s), falling back to Tesseract", e)
            if self._fallback is None:
                self._fallback = TesseractOCR()
            return self._fallback.image_to_string(image)


def get_ocr_engine(engine: str = "paddle", **kwargs) -> OCREngine:
    """
    Factory for OCR engines.

    Args:
        engine: "paddle" or "tesseract" (case-insensitive)
        **kwargs: passed to engine constructor

    Returns:
        OCREngine instance
    """
    engine = engine.lower()
    if engine == "paddle":
        return PaddleOCR(**kwargs)
    elif engine == "tesseract":
        return TesseractOCR()
    else:
        raise ValueError(f"Unknown OCR engine: {engine}")


def ocr_pdf(file_path: Path, engine: OCREngine) -> str:
    """Render each PDF page to image and run OCR, returning concatenated text."""
    import pymupdf
    from PIL import Image

    doc = pymupdf.open(file_path)
    all_text = []
    for page in doc:
        try:
            # Render at 2x resolution for better OCR accuracy
            mat = pymupdf.Matrix(2.0, 2.0)
            pix = page.get_pixmap(matrix=mat, colorspace=pymupdf.csRGB)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            text = engine.image_to_string(img)
            if text:
                all_text.append(text)
        except Exception as e:
            _log.warning("Failed to OCR page: %s", e)
            continue
    return "\n".join(all_text).strip()
