"""
Unit tests for enhanced layout_parser features:
- Column detection
- Block assignment to columns
- Heading hierarchy building
- Hierarchical chunking
"""

from dataclasses import dataclass
from pathlib import Path

import pytest

from rag.chunking.adaptive import hierarchical_chunk_text
from rag.deepdoc.layout_parser import (
    BBox,
    Block,
    BlockType,
    ColumnRegion,
    PageLayout,
    _assign_blocks_to_columns,
    _build_heading_hierarchy,
    _detect_columns,
)

# ----------------------------------------------------------------------
# Test helpers to construct synthetic layouts
# ----------------------------------------------------------------------


def make_block(
    text: str,
    page: int = 1,
    x0: float = 0.0,
    y0: float = 0.0,
    x1: float = 100.0,
    y1: float = 20.0,
    block_type: BlockType = BlockType.PARAGRAPH,
    avg_font_size: float = 12.0,
    column_index: int | None = None,
    level: int | None = None,
) -> Block:
    """Create a Block with minimal setup."""
    bbox = BBox(x0=x0, y0=y0, x1=x1, y1=y1)
    block = Block(
        block_type=block_type,
        bbox=bbox,
        text=text,
        page=page,
        order=0,
        children=[],
        metadata={
            "avg_font_size": avg_font_size,
        },
    )
    if column_index is not None:
        block.column_index = column_index
    if level is not None:
        block.level = level
    return block


def make_page_layout(
    blocks: list[Block], page_num: int = 1, width: float = 612.0, height: float = 792.0
) -> PageLayout:
    """Create a PageLayout with given blocks."""
    layout = PageLayout(
        page_num=page_num,
        width=width,
        height=height,
        rotation=0,
        blocks=blocks,
    )
    return layout


# ----------------------------------------------------------------------
# Column detection tests
# ----------------------------------------------------------------------


def test_column_detection_single_column():
    """Single column layout should return empty list (no columns detected)."""
    blocks = [
        make_block("Line 1", y0=100, x0=50, x1=500),
        make_block("Line 2", y0=120, x0=50, x1=500),
        make_block("Line 3", y0=140, x0=50, x1=500),
    ]
    page_width = 612.0
    columns = _detect_columns(page_width, blocks, bins=20, threshold=0.3)
    assert len(columns) == 0, "Single column should not be detected"


def test_column_detection_two_columns():
    """Two-column layout with blocks clustered on left and right."""
    page_width = 612.0
    # Left column: x0 ~ 50, x1 ~ 250
    # Right column: x0 ~ 350, x1 ~ 550
    blocks = []
    for i, y in enumerate(range(100, 300, 30)):
        blocks.append(make_block(f"Left {i}", y0=y, x0=50, x1=250))
        blocks.append(make_block(f"Right {i}", y0=y, x0=350, x1=550))

    columns = _detect_columns(page_width, blocks, bins=30, threshold=0.3)
    assert len(columns) == 2, "Should detect exactly 2 columns"
    # Left column should start near 0
    assert columns[0].x0 < 100
    assert columns[0].x1 < 350
    # Right column should start after 300
    assert columns[1].x0 > 300
    # Column indices
    assert columns[0].column_index == 0
    assert columns[1].column_index == 1


def test_column_detection_three_columns():
    """Three-column newspaper layout."""
    page_width = 612.0
    col_width = 150
    gap = 30
    # Columns at roughly 0-150, 180-330, 360-510
    blocks = []
    for y in range(100, 400, 40):
        for col_start in [30, 210, 390]:
            blocks.append(
                make_block(
                    f"Col@{col_start}", y0=y, x0=col_start, x1=col_start + col_width
                )
            )

    columns = _detect_columns(page_width, blocks, bins=30, threshold=0.3)
    assert len(columns) >= 3, "Should detect at least 3 columns"


# ----------------------------------------------------------------------
# Block assignment to columns
# ----------------------------------------------------------------------


def test_assign_blocks_to_columns():
    """Blocks should be assigned correct column_index based on x-center."""
    blocks = [
        make_block("Left 1", x0=50, x1=150, column_index=None),
        make_block("Right 1", x0=400, x1=500, column_index=None),
        make_block("Left 2", x0=60, x1=160, column_index=None),
    ]
    columns = [
        ColumnRegion(x0=0, x1=250, column_index=0),
        ColumnRegion(x0=300, x1=550, column_index=1),
    ]
    _assign_blocks_to_columns(blocks, columns)
    assert blocks[0].column_index == 0
    assert blocks[1].column_index == 1
    assert blocks[2].column_index == 0


def test_assign_blocks_margin_outside_columns():
    """Blocks in margin (outside all columns) should have column_index=None."""
    blocks = [
        make_block("Margin left", x0=10, x1=40, column_index=None),
        make_block("Margin right", x0=550, x1=600, column_index=None),
        make_block("Column", x0=200, x1=300, column_index=None),
    ]
    columns = [
        ColumnRegion(x0=100, x1=400, column_index=0),
    ]
    _assign_blocks_to_columns(blocks, columns)
    assert blocks[0].column_index is None
    assert blocks[1].column_index is None
    assert blocks[2].column_index == 0


# ----------------------------------------------------------------------
# Heading hierarchy tests
# ----------------------------------------------------------------------


def test_build_heading_hierarchy_simple():
    """Simple three-level hierarchy: H1, H2, H3."""
    blocks = [
        make_block("Title", block_type=BlockType.TITLE, y0=100, avg_font_size=24.0),
        make_block(
            "Heading A", block_type=BlockType.HEADING, y0=200, avg_font_size=18.0
        ),
        make_block(
            "Heading B", block_type=BlockType.HEADING, y0=300, avg_font_size=16.0
        ),
        make_block("Paragraph 1", block_type=BlockType.PARAGRAPH, y0=320),
        make_block(
            "Heading C", block_type=BlockType.HEADING, y0=400, avg_font_size=18.0
        ),
        make_block("Paragraph 2", block_type=BlockType.PARAGRAPH, y0=420),
    ]
    blocks = _build_heading_hierarchy(blocks)

    # Find headings
    h1 = next(b for b in blocks if b.block_type == BlockType.TITLE)
    h2_a = next(b for b in blocks if b.text == "Heading A")
    h2_c = next(b for b in blocks if b.text == "Heading C")
    h3_b = next(b for b in blocks if b.text == "Heading B")

    assert h1.level == 1
    assert h2_a.level == 2
    assert h3_b.level == 3
    assert h2_c.level == 2

    # Parent-child relationships
    assert h2_a.parent == h1
    assert h3_b.parent == h2_a
    assert h2_c.parent == h1
    assert h1.parent is None
    assert h2_a in h1.children
    assert h3_b in h2_a.children
    assert h2_c in h1.children


def test_build_heading_hierarchy_no_headings():
    """If no headings, levels remain None and no parent set."""
    blocks = [
        make_block("Para 1", block_type=BlockType.PARAGRAPH),
        make_block("Para 2", block_type=BlockType.PARAGRAPH),
    ]
    blocks = _build_heading_hierarchy(blocks)
    for b in blocks:
        assert b.level is None
        assert b.parent is None


# ----------------------------------------------------------------------
# Hierarchical chunking tests
# ----------------------------------------------------------------------


def test_hierarchical_chunk_small_section():
    """A section with text less than chunk_size should become one chunk."""
    # Create a layout with one heading and one paragraph
    heading = make_block(
        "Section 1", block_type=BlockType.HEADING, y0=100, avg_font_size=18.0, level=2
    )
    para = make_block(
        "This is a short paragraph.", block_type=BlockType.PARAGRAPH, y0=150
    )
    layout = make_page_layout([heading, para])

    chunks = hierarchical_chunk_text(layout, chunk_size=500, chunk_overlap=50)
    assert len(chunks) == 1
    assert "Section 1" in chunks[0]
    assert "This is a short paragraph." in chunks[0]


def test_hierarchical_chunk_large_section():
    """A section larger than chunk_size should be split into multiple chunks."""
    long_text = " ".join(["word"] * 200)  # ~1000 chars
    heading = make_block(
        "Long Section",
        block_type=BlockType.HEADING,
        y0=100,
        avg_font_size=18.0,
        level=2,
    )
    para = make_block(long_text, block_type=BlockType.PARAGRAPH, y0=150)

    layout = make_page_layout([heading, para])
    chunks = hierarchical_chunk_text(layout, chunk_size=200, chunk_overlap=50)

    assert len(chunks) > 1, "Long section should be split"
    # First chunk should start with heading
    assert chunks[0].startswith("Long Section")
    # All chunks should contain some content
    for chunk in chunks:
        assert len(chunk.strip()) > 0


def test_hierarchical_chunk_multiple_sections():
    """Multiple sections should produce separate chunks."""
    h1 = make_block(
        "Chapter 1", block_type=BlockType.TITLE, y0=100, avg_font_size=24.0, level=1
    )
    p1 = make_block("First chapter content.", block_type=BlockType.PARAGRAPH, y0=150)

    h2 = make_block(
        "Section 2.1", block_type=BlockType.HEADING, y0=300, avg_font_size=18.0, level=2
    )
    p2 = make_block("Second section content.", block_type=BlockType.PARAGRAPH, y0=350)

    layout = make_page_layout([h1, p1, h2, p2])
    chunks = hierarchical_chunk_text(layout, chunk_size=500, chunk_overlap=50)

    # Should get at least 2 chunks (maybe more if section text is large)
    assert len(chunks) >= 2
    # First chunk should contain Chapter 1
    assert any("Chapter 1" in c for c in chunks)
    # Some chunk should contain Section 2.1
    assert any("Section 2.1" in c for c in chunks)


# ----------------------------------------------------------------------
# Integration test using real PDF
# ----------------------------------------------------------------------


@pytest.mark.integration
def test_enhanced_parsing_with_real_pdf():
    """Test enhanced parsing on a real PDF from test data."""
    pdf_path = Path("data/uploads/stream-e2e-test/tiny.pdf")
    if not pdf_path.exists():
        pytest.skip(f"Test PDF not found: {pdf_path}")

    from backend.config_loader import Settings
    from rag.ingestion.pipeline import run_deepdoc_ingestion

    # Override settings to enable features
    # We can temporarily patch settings if needed, or rely on defaults (enabled)
    result = run_deepdoc_ingestion(pdf_path)

    # Basic sanity checks
    assert "chunks" in result
    assert isinstance(result["chunks"], list)
    assert len(result["chunks"]) > 0

    # Check extraction metadata indicates enhanced if it's a PDF
    if pdf_path.suffix.lower() == ".pdf":
        extraction = result.get("extraction", {})
        # It might be enhanced or fallback depending on pdfplumber availability
        # We just check that we got some result
        assert "extractor" in extraction

    # Check quality report
    quality = result.get("quality_report", {})
    assert "quality_score" in quality
    assert 0.0 <= quality["quality_score"] <= 1.0

    # Check layout summary (should have columns_detected if enhanced parsing worked)
    layout_summary = result.get("layout_summary")
    if layout_summary:
        assert "pages" in layout_summary
        assert "total_blocks" in layout_summary
        assert "blocks_by_type" in layout_summary
