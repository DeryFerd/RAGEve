#!/usr/bin/env python
"""Test PaddleOCR integration."""

from __future__ import annotations

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

import tempfile

from PIL import Image, ImageDraw, ImageFont

from backend.config_loader import settings
from rag.ingestion.extractors import Extractors
from rag.ingestion.ocr import get_ocr_engine, ocr_pdf


def create_test_image(text: str, output_path: Path) -> None:
    """Create a simple image with text for OCR testing."""
    img = Image.new("RGB", (400, 200), color="white")
    draw = ImageDraw.Draw(img)
    # Use default font
    try:
        # Try to use a truetype font if available
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 24)
    except Exception:
        font = ImageFont.load_default()
    draw.text((20, 80), text, fill="black", font=font)
    img.save(output_path)
    print(f"Created test image: {output_path}")


def create_test_pdf_with_text(output_path: Path) -> None:
    """Create a PDF with embedded text (non-scanned)."""
    import pymupdf

    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text(
        (50, 100), "This is a regular PDF with embedded text.", fontsize=12
    )
    doc.save(output_path)
    doc.close()
    print(f"Created test PDF (text-based): {output_path}")


def create_scanned_pdf_simulation(output_path: Path) -> None:
    """Create a PDF by converting an image to PDF (simulates scanned PDF)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        img_path = Path(tmpdir) / "scan.png"
        create_test_image("This is a scanned document with text for OCR.", img_path)
        # Convert image to PDF
        image = Image.open(img_path)
        image.save(output_path, "PDF", resolution=100.0)
        print(f"Created simulated scanned PDF: {output_path}")


def test_ocr_engine() -> None:
    print("\n=== Testing PaddleOCR Integration ===\n")

    # 1. Test engine selection
    print("1. Testing engine selection...")
    engine = get_ocr_engine(settings.ocr_engine)
    print(f"   Selected engine: {type(engine).__name__}")

    # 2. Test image OCR
    print("\n2. Testing image OCR...")
    with tempfile.TemporaryDirectory() as tmpdir:
        img_path = Path(tmpdir) / "test.png"
        create_test_image("Hello, PaddleOCR! This is a test.", img_path)

        # Direct engine test
        from PIL import Image

        image = Image.open(img_path)
        text = engine.image_to_string(image)
        print(f"   OCR result: '{text.strip()[:50]}...'")

        # Through Extractors.from_image
        extracted = Extractors.from_image(img_path)
        print(f"   Extractors.from_image result: '{extracted.strip()[:50]}...'")

    # 3. Test PDF (text-based) - should not trigger OCR
    print("\n3. Testing text-based PDF...")
    with tempfile.TemporaryDirectory() as tmpdir:
        pdf_path = Path(tmpdir) / "text.pdf"
        create_test_pdf_with_text(pdf_path)

        text = Extractors.from_pdf(pdf_path)
        print(f"   Extracted text length: {len(text)} chars")
        print(f"   Text preview: '{text.strip()[:50]}...'")
        assert len(text) > 0, "Should extract text from regular PDF"

    # 4. Test scanned PDF (should trigger OCR)
    print("\n4. Testing scanned PDF (OCR fallback)...")
    with tempfile.TemporaryDirectory() as tmpdir:
        pdf_path = Path(tmpdir) / "scanned.pdf"
        create_scanned_pdf_simulation(pdf_path)

        # First, check what from_pdf returns
        text = Extractors.from_pdf(pdf_path)
        print(f"   Extracted text length: {len(text)} chars")
        print(f"   Text: '{text.strip()[:50]}...'")

        # Direct OCR on PDF
        ocr_text = ocr_pdf(pdf_path, engine)
        print(f"   OCR-only text length: {len(ocr_text)} chars")
        print(f"   OCR text: '{ocr_text.strip()[:50]}...'")

    # 5. Test configuration
    print("\n5. Current OCR configuration:")
    print(f"   OCR_ENGINE: {settings.ocr_engine}")
    print(f"   OCR_THRESHOLD_CHARS: {settings.ocr_threshold_chars}")

    print("\n=== All tests completed successfully ===\n")


if __name__ == "__main__":
    try:
        test_ocr_engine()
    except Exception as e:
        print(f"\nTest failed: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        sys.exit(1)
