from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

import pymupdf

from rag.deepdoc.analyzer import classify_char


# ----------------------------------------------------------------------
# Original data models and classification (preserved from legacy)
# ----------------------------------------------------------------------


class BlockType(str, Enum):
    TITLE = "title"
    HEADING = "heading"
    PARAGRAPH = "paragraph"
    TABLE = "table"
    FIGURE_CAPTION = "figure_caption"
    FOOTER = "footer"
    HEADER = "header"
    PAGE_BREAK = "page_break"
    NOISE = "noise"
    LIST_ITEM = "list_item"
    QUOTE = "quote"
    CODE = "code"
    MATH = "math"
    UNKNOWN = "unknown"


@dataclass
class BBox:
    x0: float
    y0: float
    x1: float
    y1: float

    @property
    def width(self) -> float:
        return self.x1 - self.x0

    @property
    def height(self) -> float:
        return self.y1 - self.y0

    @property
    def area(self) -> float:
        return self.width * self.height

    @property
    def centroid_y(self) -> float:
        return (self.y0 + self.y1) / 2

    def overlaps_vertically(self, other: BBox, threshold: float = 10.0) -> bool:
        return abs(self.centroid_y - other.centroid_y) < threshold


@dataclass
class Block:
    block_type: BlockType
    bbox: BBox
    text: str
    page: int
    order: int
    children: list["Block"] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)
    # Enhanced fields
    column_index: int | None = None
    level: int | None = None
    parent: "Block | None" = field(default=None, compare=False)

    def to_dict(self) -> dict:
        return {
            "type": self.block_type.value,
            "bbox": {
                "x0": round(self.bbox.x0, 2),
                "y0": round(self.bbox.y0, 2),
                "x1": round(self.bbox.x1, 2),
                "y1": round(self.bbox.y1, 2),
            },
            "text": self.text,
            "page": self.page,
            "order": self.order,
            "metadata": self.metadata,
        }


@dataclass
class PageLayout:
    page_num: int
    width: float
    height: float
    blocks: list[Block] = field(default_factory=list)
    rotation: int = 0

    def to_dict(self) -> dict:
        return {
            "page_num": self.page_num,
            "width": round(self.width, 2),
            "height": round(self.height, 2),
            "rotation": self.rotation,
            "blocks": [b.to_dict() for b in self.blocks],
        }


# ----------------------------------------------------------------------
# Original heuristic classification
# ----------------------------------------------------------------------


# Font size thresholds (points) in PyMuPDF default scale
TITLE_SIZE_MIN = 18.0
HEADING_SIZE_MIN = 13.5
SMALL_SIZE_MAX = 9.0

# Common header/footer keywords
FOOTER_KEYWORDS = re.compile(
    r"^(page\s+\d+|©|\||-{5,}|\*{3,}|confidential|draft)",
    re.IGNORECASE,
)
HEADER_KEYWORDS = re.compile(
    r"^(chapter\s+\d|section\s+\d|\.{2,})",
    re.IGNORECASE,
)

# Table delimiters
TABLE_HINTS = re.compile(r"\|.*\|.*\|")


def _is_title_candidate(spans: list[dict], bbox: BBox) -> bool:
    if not spans:
        return False
    avg_size = sum(s["size"] for s in spans) / len(spans)
    return avg_size >= TITLE_SIZE_MIN


def _is_heading_candidate(spans: list[dict], bbox: BBox) -> bool:
    if not spans:
        return False
    avg_size = sum(s["size"] for s in spans) / len(spans)
    return HEADING_SIZE_MIN <= avg_size < TITLE_SIZE_MIN


def _is_noise(text: str, bbox: BBox) -> bool:
    stripped = text.strip()
    if not stripped:
        return True
    # Very short lines that appear at page edges (likely artifacts)
    if len(stripped) < 3:
        return True
    # Single characters repeated
    if len(stripped) == 1 and stripped in "|-_~^*":
        return True
    # Footers/headers
    if FOOTER_KEYWORDS.match(stripped) or HEADER_KEYWORDS.match(stripped):
        return True
    return False


def _classify_text_block(
    text: str,
    bbox: BBox,
    spans: list[dict],
    page_height: float,
    page_width: float,
) -> BlockType:
    if _is_noise(text, bbox):
        return BlockType.NOISE

    # Footer / header by position
    if bbox.y1 / page_height > 0.92:
        return BlockType.FOOTER
    if bbox.y0 / page_height < 0.08:
        return BlockType.HEADER

    # Title by font size
    if _is_title_candidate(spans, bbox):
        return BlockType.TITLE

    # Heading by font size
    if _is_heading_candidate(spans, bbox):
        return BlockType.HEADING

    # Table hint: text contains multiple pipe delimiters on same line
    if TABLE_HINTS.search(text):
        return BlockType.TABLE

    # Block-level list items
    stripped = text.strip()
    if re.match(r"^[\-\*\•]\s+", stripped) or re.match(r"^\d+[.)]\s+", stripped):
        return BlockType.LIST_ITEM

    # Quoted text
    if stripped.startswith('"') or stripped.startswith('"') or stripped.startswith('"'):
        return BlockType.QUOTE

    # Code blocks (indented, contains braces/brackets)
    if bbox.x0 > page_width * 0.05 and ("{" in text or "}" in text or "    " in text):
        return BlockType.CODE

    return BlockType.PARAGRAPH


# ----------------------------------------------------------------------
# Chunk profile definitions (quality scorer)
# ----------------------------------------------------------------------


class ChunkProfile(str, Enum):
    CLEAN_TEXT = "clean_text"
    OCR_NOISY = "ocr_noisy"
    TABLE_HEAVY = "table_heavy"
    CODE_MIXED = "code_mixed"
    GENERAL = "general"


@dataclass
class ChunkProfileConfig:
    profile: ChunkProfile
    chunk_size: int
    chunk_overlap: int
    max_tokens_per_chunk: int
    reason: str


PROFILE_PRESETS: dict[ChunkProfile, ChunkProfileConfig] = {
    ChunkProfile.CLEAN_TEXT: ChunkProfileConfig(
        profile=ChunkProfile.CLEAN_TEXT,
        chunk_size=1500,
        chunk_overlap=200,
        max_tokens_per_chunk=600,
        reason="High alpha ratio, consistent script, natural punctuation.",
    ),
    ChunkProfile.OCR_NOISY: ChunkProfileConfig(
        profile=ChunkProfile.OCR_NOISY,
        chunk_size=600,
        chunk_overlap=150,
        max_tokens_per_chunk=250,
        reason="High noise signals detected — using smaller chunks with higher overlap.",
    ),
    ChunkProfile.TABLE_HEAVY: ChunkProfileConfig(
        profile=ChunkProfile.TABLE_HEAVY,
        chunk_size=800,
        chunk_overlap=100,
        max_tokens_per_chunk=350,
        reason="Dense tabular structure detected — preserving row/section boundaries.",
    ),
    ChunkProfile.CODE_MIXED: ChunkProfileConfig(
        profile=ChunkProfile.CODE_MIXED,
        chunk_size=700,
        chunk_overlap=120,
        max_tokens_per_chunk=300,
        reason="Code or mixed content detected — delimiter-aware chunking.",
    ),
    ChunkProfile.GENERAL: ChunkProfileConfig(
        profile=ChunkProfile.GENERAL,
        chunk_size=1200,
        chunk_overlap=180,
        max_tokens_per_chunk=500,
        reason="Mixed content or standard document — balanced settings.",
    ),
}


# ----------------------------------------------------------------------
# Quality signals
# ----------------------------------------------------------------------


@dataclass
class QualitySignals:
    alpha_ratio: float
    ocr_noise_ratio: float  # garbled / symbol-heavy ratio
    broken_line_ratio: float  # lines split mid-sentence
    header_footer_ratio: float  # repeated header/footer
    table_density: float  # 0-1: fraction of text in table-like lines
    avg_sentence_length: float
    language_script_changes: int  # number of script switches (latin <-> cjk etc)
    repeated_word_ratio: float  # high repeat = likely OCR garbage
    code_delimiter_ratio: float  # braces, brackets, indentation
    issue_tags: list[str]


# ----------------------------------------------------------------------
# Signal extraction
# ----------------------------------------------------------------------


# Regex patterns for signal detection
BROKEN_LINE_RE = re.compile(r"\w{3,}$")  # ends mid-word
OCR_NOISE_RE = re.compile(r"[_]{5,}|\.{4,}|[~]{3,}|[\^]{3,}")
# Only match alphanumeric char repetition (OCR garbage), not punctuation
REPEATED_CHAR_RE = re.compile(r"([a-zA-Z0-9])\1{4,}")
# Matches markdown pipe tables and CSV-like lines with 2+ columns
TABLE_LINE_RE = re.compile(r"^\s*\|.*\|.*\|")
CODE_DELIM_RE = re.compile(r"[\{\}\[\]\(\)]|    +|  {2}|^\s{0,4}(if|else|for|while|def|class|import|return)\b")
HEADER_FOOTER_RE = re.compile(
    r"^(page\s+\d+|chapter\s+\d|section\s+\d|©|\||\*{3,}|confidential|draft)",
    re.IGNORECASE,
)


def _script_family(ch: str) -> str:
    name = unicodedata.name(ch, "")
    if "CJK" in name or "IDEOGRAPH" in name or "HIRAGANA" in name or "KATAKANA" in name:
        return "cjk"
    if "LATIN" in name:
        return "latin"
    if "ARABIC" in name:
        return "arabic"
    if "CYRILLIC" in name:
        return "cyrillic"
    if "HANGUL" in name:
        return "hangul"
    return "other"


def _count_script_changes(text: str) -> int:
    prev_script = ""
    changes = 0
    for ch in text:
        if ch.isspace():
            continue
        current_script = _script_family(ch)
        if prev_script and current_script != prev_script:
            changes += 1
        prev_script = current_script
    return changes


def compute_quality_signals(text: str) -> QualitySignals:
    if not text:
        return QualitySignals(
            alpha_ratio=0.0,
            ocr_noise_ratio=0.0,
            broken_line_ratio=0.0,
            header_footer_ratio=0.0,
            table_density=0.0,
            avg_sentence_length=0.0,
            language_script_changes=0,
            repeated_word_ratio=0.0,
            code_delimiter_ratio=0.0,
            issue_tags=["empty"],
        )

    lines = text.split("\n")
    total_chars = len(text)
    total_lines = len(lines)

    # 1. Alpha ratio (from analyzer)
    alpha_chars = sum(1 for ch in text if classify_char(ch) != "whitespace" and classify_char(ch) != "other")
    alpha_ratio = alpha_chars / max(total_chars, 1)

    # 2. OCR noise ratio
    noise_matches = sum(1 for _ in OCR_NOISE_RE.finditer(text))
    ocr_noise_ratio = noise_matches / max(total_chars, 1)

    # 3. Broken line ratio (lines ending mid-word)
    broken_lines = sum(1 for line in lines if BROKEN_LINE_RE.search(line.rstrip()))
    broken_line_ratio = broken_lines / max(total_lines, 1)

    # 4. Header/footer ratio
    hf_lines = sum(1 for line in lines if HEADER_FOOTER_RE.match(line.strip()))
    header_footer_ratio = hf_lines / max(total_lines, 1)

    # 5. Table density
    table_lines = sum(1 for line in lines if TABLE_LINE_RE.search(line))
    table_density = table_lines / max(total_lines, 1)

    # 6. Average sentence length
    sentences = re.split(r"[.!?。！？]+", text)
    sentence_lengths = [len(s.split()) for s in sentences if s.strip()]
    avg_sentence_length = sum(sentence_lengths) / max(len(sentence_lengths), 1)

    # 7. Script changes (latin <-> cjk etc)
    language_script_changes = _count_script_changes(text)

    # 8. Repeated char ratio (OCR garbage indicator)
    repeated_chars = sum(1 for _ in REPEATED_CHAR_RE.finditer(text))
    repeated_word_ratio = repeated_chars / max(total_chars, 1)

    # 9. Code delimiter ratio (curly braces, square brackets, 4-space indents)
    import re as _re

    code_delim_chars = (
        sum(1 for ch in text if ch in "{}[")
        + len(_re.findall(r"    +", text))  # 4+ space indentation
    )
    code_delimiter_ratio = code_delim_chars / max(total_chars, 1)

    # 10. Issue tags
    issue_tags: list[str] = []
    if ocr_noise_ratio > 0.01:
        issue_tags.append("ocr_noise")
    if broken_line_ratio > 0.25:
        issue_tags.append("broken_lines")
    if table_density > 0.05:
        issue_tags.append("table_heavy")
    if header_footer_ratio > 0.1:
        issue_tags.append("header_footer_noise")
    if repeated_word_ratio > 0.005:
        issue_tags.append("repeated_chars")
    if code_delimiter_ratio > 0.03:
        issue_tags.append("code_delimiters")
    if language_script_changes > 10:
        issue_tags.append("mixed_scripts")

    return QualitySignals(
        alpha_ratio=round(alpha_ratio, 4),
        ocr_noise_ratio=round(ocr_noise_ratio, 4),
        broken_line_ratio=round(broken_line_ratio, 4),
        header_footer_ratio=round(header_footer_ratio, 4),
        table_density=round(table_density, 4),
        avg_sentence_length=round(avg_sentence_length, 2),
        language_script_changes=language_script_changes,
        repeated_word_ratio=round(repeated_word_ratio, 4),
        code_delimiter_ratio=round(code_delimiter_ratio, 4),
        issue_tags=issue_tags,
    )


# ----------------------------------------------------------------------
# Quality score calculation
# ----------------------------------------------------------------------


def compute_quality_score(signals: QualitySignals) -> float:
    """
    Compute a 0-1 quality score from quality signals.
    Higher = cleaner, more reliable for retrieval.
    """
    score = 1.0

    # Penalise OCR noise heavily
    score -= signals.ocr_noise_ratio * 0.4

    # Penalise broken lines
    score -= signals.broken_line_ratio * 0.15

    # Penalise header/footer noise
    score -= signals.header_footer_ratio * 0.1

    # Penalise very short avg sentences (fragmented/OCR)
    if signals.avg_sentence_length < 5:
        score -= 0.1

    # Penalise high repeated char ratio
    score -= signals.repeated_word_ratio * 0.3

    return max(0.0, min(1.0, round(score, 4)))


# ----------------------------------------------------------------------
# Adaptive profile selector
# ----------------------------------------------------------------------


def select_chunk_profile(signals: QualitySignals, score: float) -> ChunkProfileConfig:
    """
    Select the most appropriate chunk profile based on quality signals.
    More specific profiles are checked before more general ones.
    """
    # Table heavy — specific structural profile
    if signals.table_density > 0.05:
        return PROFILE_PRESETS[ChunkProfile.TABLE_HEAVY]

    # Code / mixed — specific structural profile
    if signals.code_delimiter_ratio > 0.03:
        return PROFILE_PRESETS[ChunkProfile.CODE_MIXED]

    # OCR noisy — heavy noise only (separate repeated_char check below)
    if signals.ocr_noise_ratio > 0.005:
        return PROFILE_PRESETS[ChunkProfile.OCR_NOISY]

    # Repeated chars — standalone OCR garbage indicator
    if signals.repeated_word_ratio > 0.002:
        return PROFILE_PRESETS[ChunkProfile.OCR_NOISY]

    # Clean text
    if score >= 0.85 and not signals.issue_tags:
        return PROFILE_PRESETS[ChunkProfile.CLEAN_TEXT]

    # Default to general
    return PROFILE_PRESETS[ChunkProfile.GENERAL]


# ----------------------------------------------------------------------
# High-level scorer
# ----------------------------------------------------------------------


@dataclass
class QualityReport:
    quality_score: float
    profile: ChunkProfileConfig
    signals: QualitySignals


def score_and_select_profile(text: str) -> QualityReport:
    signals = compute_quality_signals(text)
    score = compute_quality_score(signals)
    profile = select_chunk_profile(signals, score)
    return QualityReport(quality_score=score, profile=profile, signals=signals)


# ----------------------------------------------------------------------
# Data models for enhanced layout parsing
# ----------------------------------------------------------------------


@dataclass
class ColumnRegion:
    """Represents a detected column region on a page."""
    x0: float
    x1: float
    column_index: int

    @property
    def width(self) -> float:
        return self.x1 - self.x0

    def contains_x(self, x: float) -> bool:
        """Check if x-coordinate falls within this column."""
        return self.x0 <= x <= self.x1


@dataclass
class TableStructure:
    """Structured table data extracted by pdfplumber."""
    rows: list[list[str]]  # Each row is a list of cell strings
    bbox: Any  # BBox from layout_parser (will be constructed from pdfplumber)


def _bbox_overlap(bbox1: Any, bbox2: Any, threshold: float = 0.5) -> bool:
    """Check if two bounding boxes overlap by at least threshold fraction of area."""
    # Simple intersection over union
    x0 = max(bbox1.x0, bbox2.x0)
    y0 = max(bbox1.y0, bbox2.y0)
    x1 = min(bbox1.x1, bbox2.x1)
    y1 = min(bbox1.y1, bbox2.y1)

    if x1 <= x0 or y1 <= y0:
        return False

    intersection = (x1 - x0) * (y1 - y0)
    area1 = (bbox1.x1 - bbox1.x0) * (bbox1.y1 - bbox1.y0)
    area2 = (bbox2.x1 - bbox2.x0) * (bbox2.y1 - bbox2.y0)
    union = area1 + area2 - intersection

    return intersection / max(union, 1e-9) >= threshold


# ----------------------------------------------------------------------
# Column detection
# ----------------------------------------------------------------------


def _detect_columns(
    page_width: float,
    blocks: list[Block],
    *,
    bins: int = 50,
    threshold: float = 0.3,
    min_gap: float = 20.0,
) -> list[ColumnRegion]:
    """
    Detect multi-column layout using x-position histogram.

    Args:
        page_width: Width of the page in points
        blocks: List of blocks (must have bbox)
        bins: Number of histogram bins
        threshold: Peak detection threshold as fraction of max height
        min_gap: Minimum gap (points) between columns

    Returns:
        List of ColumnRegion objects (sorted left to right)
    """
    if len(blocks) < 5:
        # Not enough blocks to reliably detect columns
        return []

    # Build histogram of block x-centers
    hist = [0] * bins
    bin_width = page_width / bins

    for block in blocks:
        x_center = (block.bbox.x0 + block.bbox.x1) / 2
        bin_idx = min(int(x_center / bin_width), bins - 1)
        hist[bin_idx] += 1

    # Find peaks in raw histogram (no smoothing to preserve sharp peaks)
    max_val = max(hist)
    if max_val == 0:
        return []

    peaks = []
    for i in range(1, len(hist) - 1):
        if (
            hist[i] > hist[i - 1]
            and hist[i] > hist[i + 1]
            and hist[i] >= max_val * threshold
        ):
            peaks.append(i)

    if len(peaks) <= 1:
        return []  # Single column

    # Convert peak bin indices to x positions (use bin center)
    peak_x_positions = [(p + 0.5) * bin_width for p in peaks]

    # Sort peaks by x position
    peak_x_positions.sort()

    # Derive column boundaries as midpoints between peaks
    boundaries = []
    for i in range(len(peak_x_positions) - 1):
        mid = (peak_x_positions[i] + peak_x_positions[i + 1]) / 2
        boundaries.append(mid)

    # Create ColumnRegion objects
    columns = []
    left_edge = 0.0
    for boundary in boundaries:
        columns.append(
            ColumnRegion(x0=left_edge, x1=boundary, column_index=len(columns))
        )
        left_edge = boundary
    columns.append(
        ColumnRegion(x0=left_edge, x1=page_width, column_index=len(columns))
    )

    # Filter out narrow columns (less than min_gap)
    columns = [c for c in columns if c.width >= min_gap]

    return columns


def _assign_blocks_to_columns(
    blocks: list[Block],
    columns: list[ColumnRegion],
) -> None:
    """
    Assign column_index to each block based on x-center.
    Modifies blocks in-place.
    """
    for block in blocks:
        x_center = (block.bbox.x0 + block.bbox.x1) / 2
        # Find the column whose range contains this x_center
        assigned = False
        for col in columns:
            if col.contains_x(x_center):
                block.column_index = col.column_index
                assigned = True
                break
        if not assigned:
            # Block falls outside any column (margin, etc.)
            block.column_index = None


# ----------------------------------------------------------------------
# Table extraction with pdfplumber
# ----------------------------------------------------------------------


def _extract_tables_with_pdfplumber(
    file_path: Path,
    page_num: int,
    *,
    table_strategy: str = "text",
    snap_tolerance: float = 3.0,
    join_tolerance: float = 3.0,
) -> list[TableStructure]:
    """
    Extract structured tables from a specific page using pdfplumber.

    Args:
        file_path: Path to PDF
        page_num: 1-indexed page number
        table_strategy: "text", "lines", or "explicit"
        snap_tolerance: Snap tolerance for pdfplumber
        join_tolerance: Join tolerance for pdfplumber

    Returns:
        List of TableStructure objects
    """
    try:
        import pdfplumber
    except ImportError:
        # pdfplumber not installed, return empty list
        return []

    tables = []
    try:
        with pdfplumber.open(file_path) as pdf:
            # pdfplumber uses 0-indexed pages
            pdf_page = pdf.pages[page_num - 1]
            raw_tables = pdf_page.extract_tables(
                {
                    "vertical_strategy": table_strategy,
                    "horizontal_strategy": table_strategy,
                    "explicit_vertical_lines": [],
                    "explicit_horizontal_lines": [],
                    "snap_tolerance": snap_tolerance,
                    "join_tolerance": join_tolerance,
                }
            )

            for raw_table in raw_tables:
                if not raw_table:
                    continue

                # Clean cells
                cleaned_rows = [
                    [str(cell).strip() if cell is not None else "" for cell in row]
                    for row in raw_table
                ]

                # Remove completely empty rows
                cleaned_rows = [
                    row for row in cleaned_rows if any(cell.strip() for cell in row)
                ]

                if not cleaned_rows:
                    continue

                # Get table bounding box
                # pdfplumber's table object has a bbox attribute
                table_bbox = None
                # Find the table object that corresponds to this extracted data
                # Unfortunately pdfplumber doesn't directly return table objects with bbox
                # We'll need to reconstruct or skip bbox for now
                # For now, we'll create a dummy bbox from the first cell's position
                # In practice, we might need to use pdf_page.debug_tablefinder for bbox
                # Simpler: skip bbox and let merge logic use approximate block overlap

                tables.append(
                    TableStructure(
                        rows=cleaned_rows,
                        bbox=None,  # Will be determined by overlap during merge
                    )
                )
    except Exception as e:
        # Log warning but don't fail
        import logging
        logging.getLogger("rag.deepdoc.layout_parser").warning(
            "pdfplumber extraction failed on %s page %d: %s", file_path, page_num, e
        )

    return tables


def _tables_to_markdown(tables: list[TableStructure]) -> list[str]:
    """Convert TableStructure objects to markdown strings."""
    markdown_tables = []
    for table in tables:
        if not table.rows:
            continue

        md_rows = []
        for row in table.rows:
            md_rows.append("| " + " | ".join(row) + " |")

        # Check if first row looks like header (all caps or contains common headers)
        header_keywords = {"NAME", "TITLE", "DATE", "ID", "VALUE", "PRICE", "QTY", "TOTAL"}
        first_row_text = " ".join(table.rows[0]).upper()
        is_header = any(keyword in first_row_text for keyword in header_keywords)

        if is_header and len(table.rows) > 1:
            # Insert separator line
            num_cols = len(table.rows[0])
            separator = "|" + "|".join([" --- "] * num_cols) + "|"
            md_rows.insert(1, separator)

        markdown_tables.append("\n".join(md_rows))

    return markdown_tables


def _merge_table_blocks_with_pdfplumber(
    blocks: list[Block],
    tables: list[TableStructure],
    overlap_threshold: float = 0.3,
) -> list[Block]:
    """
    Replace heuristic table blocks with structured tables from pdfplumber.
    Returns a new list of blocks.
    """
    if not tables:
        return blocks

    # Convert tables to markdown strings
    table_markdowns = _tables_to_markdown(tables)

    # Find blocks that overlap significantly with each table
    # We'll use a simple heuristic: if table is on same page and roughly same Y range
    new_blocks = []
    used_block_indices = set()

    for table_idx, table in enumerate(tables):
        # Find blocks that might be part of this table
        overlapping_indices = []
        for idx, block in enumerate(blocks):
            if idx in used_block_indices:
                continue
            if block.bbox is None or table.bbox is None:
                # Without bbox, we can't reliably match; skip merging
                continue
            if _bbox_overlap(block.bbox, table.bbox, threshold=overlap_threshold):
                overlapping_indices.append(idx)

        if overlapping_indices:
            # All overlapping blocks are part of this table
            # Compute merged bbox
            min_x0 = min(blocks[i].bbox.x0 for i in overlapping_indices)
            min_y0 = min(blocks[i].bbox.y0 for i in overlapping_indices)
            max_x1 = max(blocks[i].bbox.x1 for i in overlapping_indices)
            max_y1 = max(blocks[i].bbox.y1 for i in overlapping_indices)
            merged_bbox = type(block.bbox)(x0=min_x0, y0=min_y0, x1=max_x1, y1=max_y1)

            # Determine page and order (use first overlapping block)
            first_block = blocks[overlapping_indices[0]]

            # Mark these blocks as used
            used_block_indices.update(overlapping_indices)

            # Create new TABLE block
            new_block = Block(
                block_type=BlockType.TABLE,
                bbox=merged_bbox,
                text=table_markdowns[table_idx],
                page=first_block.page,
                order=first_block.order,
                children=[],
                metadata={
                    "table_rows": len(table.rows),
                    "table_cols": len(table.rows[0]) if table.rows else 0,
                    "structured": True,
                    "source": "pdfplumber",
                },
            )
            new_blocks.append(new_block)

    # Add all non-overlapping blocks
    for idx, block in enumerate(blocks):
        if idx not in used_block_indices:
            new_blocks.append(block)

    return new_blocks


# ----------------------------------------------------------------------
# Heading hierarchy building
# ----------------------------------------------------------------------


def _estimate_heading_level(
    block: Block,
    font_sizes: list[float],
    size_thresholds: list[float],
) -> int:
    """
    Estimate heading level (1=H1, 2=H2, ...) based on font size.
    """
    avg_size = block.metadata.get("avg_font_size", 0) if block.metadata else 0

    # If we have size thresholds from sorted unique sizes
    for level, threshold in enumerate(size_thresholds, start=1):
        if avg_size >= threshold:
            return level

    # Default: if it's a heading but doesn't match thresholds, return appropriate level
    if block.block_type == BlockType.HEADING:
        return 2  # Assume H2
    if block.block_type == BlockType.TITLE:
        return 1  # Assume H1

    return 0  # Not a heading


def _build_heading_hierarchy(blocks: list[Block]) -> list[Block]:
    """
    Assign heading levels and parent-child relationships to heading blocks.
    Modifies blocks in-place by setting block.level and building parent/children links.
    """
    # Extract headings only
    headings = [b for b in blocks if b.block_type in (BlockType.TITLE, BlockType.HEADING)]

    if not headings:
        return blocks

    # Sort headings by reading order (page, y)
    headings.sort(key=lambda b: (b.page, b.bbox.y0))

    # Collect unique font sizes from headings
    font_sizes = sorted(
        {h.metadata.get("avg_font_size", 0) if h.metadata else 0 for h in headings},
        reverse=True,
    )

    # Determine size thresholds for H1, H2, H3...
    # Heuristic: each level is ~15-20% smaller than previous
    size_thresholds = []
    if len(font_sizes) > 1:
        # Add a size as a threshold if the gap to the next size is >=10%
        # This indicates a distinct level boundary
        for i in range(len(font_sizes) - 1):
            larger = font_sizes[i]
            smaller = font_sizes[i + 1]
            if larger - smaller >= larger * 0.1:
                size_thresholds.append(larger)
        # If the gap between second-smallest and smallest was sufficient,
        # add the smallest size as the final threshold to give it its own level
        if len(font_sizes) >= 2 and font_sizes[-2] in size_thresholds:
            size_thresholds.append(font_sizes[-1])
    else:
        # Single size: only one threshold
        size_thresholds = [font_sizes[0]] if font_sizes else []
    # Fallback: if no thresholds added (all gaps too small), use largest as sole threshold
    if not size_thresholds and font_sizes:
        size_thresholds = [font_sizes[0]]

    # Assign levels to headings
    for heading in headings:
        level = _estimate_heading_level(heading, font_sizes, size_thresholds)
        # Clamp level: TITLE should be level 1, HEADING min level 2
        if heading.block_type == BlockType.TITLE:
            level = 1
        elif heading.block_type == BlockType.HEADING:
            level = max(2, level)
        heading.level = level

    # Build parent-child tree using a stack
    stack: list[Block] = []  # holds current ancestor chain

    for heading in headings:
        level = heading.level or 1

        # Pop stack to find parent (lower level number)
        while stack and (stack[-1].level or 1) >= level:
            stack.pop()

        if stack:
            # Current heading's parent is top of stack
            heading.parent = stack[-1]
            stack[-1].children.append(heading)
        else:
            heading.parent = None

        stack.append(heading)

    return blocks


# ----------------------------------------------------------------------
# Reading order sorting
# ----------------------------------------------------------------------


def _sort_reading_order(blocks: list[Block]) -> list[Block]:
    """
    Sort blocks for correct reading order considering columns.
    Primary: page
    Secondary: column_index (0, 1, 2...)
    Tertiary: y0 (top to bottom)
    Quaternary: x0 (left to right within same line)
    """
    # blocks with column_index=None are treated as single column or full-width
    # Assign them column_index = 0 for sorting
    def sort_key(block: Block):
        col = block.column_index if block.column_index is not None else 0
        return (block.page, col, block.bbox.y0, block.bbox.x0)

    return sorted(blocks, key=sort_key)


# ----------------------------------------------------------------------
# Main layout parser
# ----------------------------------------------------------------------


def parse_pdf_layout(
    file_path: Path,
    *,
    enable_column_detection: bool = True,
    enable_structured_tables: bool = True,
    column_bins: int = 50,
    column_threshold: float = 0.3,
    column_min_gap: float = 20.0,
    table_strategy: str = "text",
) -> list[PageLayout]:
    """
    Parse a PDF with layout awareness, returning structured pages and blocks.
    Optionally performs column detection and structured table extraction.
    """
    layouts: list[PageLayout] = []

    with pymupdf.open(file_path) as doc:
        for page_num, page in enumerate(doc, start=1):
            page_rect = page.rect
            blocks_raw = page.get_text("dict")["blocks"]

            page_layout = PageLayout(
                page_num=page_num,
                width=page_rect.width,
                height=page_rect.height,
                rotation=page.rotation,
            )

            order = 0
            for raw in blocks_raw:
                # Skip empty blocks
                if raw.get("type") == 0 and not raw.get("lines"):
                    continue

                if raw["type"] == 0:
                    # Text block
                    bbox_data = raw["bbox"]
                    bbox = BBox(
                        x0=bbox_data[0],
                        y0=bbox_data[1],
                        x1=bbox_data[2],
                        y1=bbox_data[3],
                    )

                    lines = raw.get("lines", [])
                    block_text_parts: list[str] = []
                    all_spans: list[dict] = []

                    for line in lines:
                        for span in line.get("spans", []):
                            all_spans.append({
                                "size": span.get("size", 0),
                                "font": span.get("font", ""),
                                "flags": span.get("flags", 0),
                                "color": span.get("color", 0),
                                "text": span.get("text", ""),
                            })
                        line_text = " ".join(span["text"] for span in line.get("spans", []))
                        block_text_parts.append(line_text)

                    block_text = "\n".join(block_text_parts).strip()
                    if not block_text:
                        continue

                    block_type = _classify_text_block(
                        text=block_text,
                        bbox=bbox,
                        spans=all_spans,
                        page_height=page_rect.height,
                        page_width=page_rect.width,
                    )

                    block = Block(
                        block_type=block_type,
                        bbox=bbox,
                        text=block_text,
                        page=page_num,
                        order=order,
                        children=[],
                        metadata={
                            "fonts": list({s["font"] for s in all_spans}),
                            "avg_font_size": round(sum(s["size"] for s in all_spans) / len(all_spans), 2)
                            if all_spans
                            else 0.0,
                        },
                    )
                    page_layout.blocks.append(block)

                elif raw["type"] == 1:
                    # Image block
                    bbox_data = raw["bbox"]
                    bbox = BBox(
                        x0=bbox_data[0],
                        y0=bbox_data[1],
                        x1=bbox_data[2],
                        y1=bbox_data[3],
                    )
                    block = Block(
                        block_type=BlockType.FIGURE_CAPTION,
                        bbox=bbox,
                        text="[image]",
                        page=page_num,
                        order=order,
                        children=[],
                        metadata={
                            "image_extent": raw.get("ext", "unknown"),
                            "width": raw.get("width", 0),
                            "height": raw.get("height", 0),
                        },
                    )
                    page_layout.blocks.append(block)

                order += 1

            # Sort blocks initially by reading order
            page_layout.blocks.sort(key=lambda b: (b.page, b.bbox.y0, b.bbox.x0))
            for idx, block in enumerate(page_layout.blocks):
                block.order = idx

            # Apply enhanced parsing if enabled
            if enable_column_detection or enable_structured_tables:
                # Column detection
                if enable_column_detection:
                    columns = _detect_columns(
                        page_rect.width,
                        page_layout.blocks,
                        bins=column_bins,
                        threshold=column_threshold,
                        min_gap=column_min_gap,
                    )
                    _assign_blocks_to_columns(page_layout.blocks, columns)

                # Structured table extraction
                if enable_structured_tables:
                    tables = _extract_tables_with_pdfplumber(
                        file_path,
                        page_num,
                        table_strategy=table_strategy,
                        snap_tolerance=3.0,
                        join_tolerance=3.0,
                    )
                    if tables:
                        page_layout.blocks = _merge_table_blocks_with_pdfplumber(
                            page_layout.blocks, tables
                        )

                # Re-sort with column-aware order
                page_layout.blocks = _sort_reading_order(page_layout.blocks)
                for idx, block in enumerate(page_layout.blocks):
                    block.order = idx

            # Build heading hierarchy across all blocks (not just this page)
            # We'll do it after processing all pages to get proper ordering
            layouts.append(page_layout)

    # Build hierarchy across entire document (all pages)
    all_blocks = []
    for page_layout in layouts:
        all_blocks.extend(page_layout.blocks)
    all_blocks = _build_heading_hierarchy(all_blocks)

    # Re-assign to pages
    block_idx = 0
    for page_layout in layouts:
        page_block_count = len(page_layout.blocks)
        page_layout.blocks = all_blocks[block_idx : block_idx + page_block_count]
        block_idx += page_block_count

    return layouts


def layout_to_readable_text(
    layouts: list[PageLayout],
    *,
    include_hierarchy: bool = False,
) -> str:
    """
    Convert parsed layout back to clean reading-order text.
    Preserves section separators.

    Args:
        layouts: List of PageLayout objects
        include_hierarchy: If True, prepend headings with markdown levels (H1, H2, ...)

    Returns:
        Plain text with structural markers
    """
    parts: list[str] = []

    for page in layouts:
        for block in page.blocks:
            if block.block_type == BlockType.NOISE:
                continue
            if block.block_type == BlockType.FOOTER:
                continue
            if block.block_type == BlockType.HEADER:
                continue
            if block.block_type == BlockType.PAGE_BREAK:
                parts.append("\n--- PAGE BREAK ---\n")
                continue

            prefix = ""
            suffix = ""

            # Heading hierarchy markers
            if include_hierarchy and block.level:
                prefix = "\n" + "#" * block.level + " "
            elif include_hierarchy and block.block_type == BlockType.TITLE:
                prefix = "\n# "
            elif include_hierarchy and block.block_type == BlockType.HEADING:
                # Try to determine level from metadata if available
                level = block.metadata.get("heading_level", 2) if block.metadata else 2
                prefix = "\n" + "#" * level + " "

            # Table markers
            if block.block_type == BlockType.TABLE:
                prefix = "\n[TABLE]\n"

            # Figure markers
            if block.block_type == BlockType.FIGURE_CAPTION:
                prefix = "\n[FIGURE]\n"

            # Code blocks
            if block.block_type == BlockType.CODE:
                prefix = "\n```\n"
                suffix = "\n```\n"

            # Quote blocks
            if block.block_type == BlockType.QUOTE:
                prefix = "\n> "
                suffix = "\n"

            parts.append(f"{prefix}{block.text}{suffix}\n")

    return "\n".join(parts).strip()
