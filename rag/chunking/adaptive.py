from __future__ import annotations

import re

from rag.chunking.high_accuracy import deepdoc_chunk_text
from rag.deepdoc.layout_parser import Block, PageLayout, BlockType, _build_heading_hierarchy
from rag.deepdoc.quality_scorer import ChunkProfile, PROFILE_PRESETS

PARAGRAPH_SPLIT_RE = re.compile(r"\n\s*\n+")
SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?。！？])\s+")
TABLE_SPLIT_RE = re.compile(r"\n(?=\[Sheet:|\||\d+,)")
CODE_BLOCK_RE = re.compile(r"(?s)```[\s\S]*?```|`[^`\n]+`")


def _split_by_tables(text: str) -> list[str]:
    """Split text preserving table blocks as single units."""
    parts = TABLE_SPLIT_RE.split(text)
    return [p.strip() for p in parts if p.strip()]


def _split_by_code_blocks(text: str) -> list[str]:
    """Split text preserving code blocks as single units."""
    parts = CODE_BLOCK_RE.split(text)
    return [p.strip() for p in parts if p.strip()]


def hierarchical_chunk_text(
    layouts: PageLayout | list[PageLayout],
    chunk_size: int,
    chunk_overlap: int,
) -> list[str]:
    """
    Chunk text respecting heading hierarchy.

    Strategy:
    1. Flatten all blocks from all pages
    2. Build heading hierarchy (parent-child relationships)
    3. Group blocks into sections (from one heading to next)
    4. For each section:
       - If section text fits in chunk_size, use as single chunk
       - If too large, recursively chunk using deepdoc_chunk_text
       - Prepend section heading to first sub-chunk for context
    5. Return flat list of chunks

    Args:
        layouts: Single PageLayout or list of PageLayout with blocks (should have column_index, level set)
        chunk_size: Target max characters per chunk
        chunk_overlap: Overlap between chunks

    Returns:
        List of chunk strings
    """
    # Normalize to list
    if isinstance(layouts, PageLayout):
        layouts = [layouts]

    # Flatten all blocks
    all_blocks: list[Block] = []
    for page in layouts:
        all_blocks.extend(page.blocks)

    if not all_blocks:
        return []

    # Ensure hierarchy is built (in case parse_pdf_layout skipped it)
    all_blocks = _build_heading_hierarchy(all_blocks)

    # Sort by reading order (page, y, x)
    all_blocks.sort(key=lambda b: (b.page, b.bbox.y0, b.bbox.x0))

    # Group into sections
    sections: list[dict] = []
    current_section_blocks: list[Block] = []
    current_heading: Block | None = None

    for block in all_blocks:
        is_heading = block.block_type in (BlockType.TITLE, BlockType.HEADING)

        if is_heading:
            # Save previous section
            if current_section_blocks:
                sections.append({
                    "heading": current_heading,
                    "blocks": current_section_blocks.copy(),
                })
            # Start new section with this heading
            current_heading = block
            current_section_blocks = [block]
        else:
            current_section_blocks.append(block)

    # Save last section
    if current_section_blocks:
        sections.append({
            "heading": current_heading,
            "blocks": current_section_blocks.copy(),
        })

    # Chunk each section
    chunks: list[str] = []
    for section in sections:
        # Build section text (including heading if present)
        section_text_parts = []
        if section["heading"]:
            section_text_parts.append(section["heading"].text)
            section_text_parts.append("")  # blank line

        section_text_parts.extend(b.text for b in section["blocks"] if b != section["heading"])
        section_text = "\n".join(section_text_parts).strip()

        if not section_text:
            continue

        if len(section_text) <= chunk_size:
            chunks.append(section_text)
        else:
            # Section too large: chunk within it using deepdoc
            # Note: we chunk the text-only representation, not the blocks
            sub_chunks = deepdoc_chunk_text(
                section_text,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                max_tokens_per_chunk=500,  # default from PROFILE_PRESETS[GENERAL]
            )

            # Prepend heading to first sub-chunk to maintain context
            if section["heading"] and sub_chunks:
                sub_chunks[0] = f"{section['heading'].text}\n\n{sub_chunks[0]}"

            chunks.extend(sub_chunks)

    return chunks


def adaptive_chunk_text(
    text: str,
    profile: ChunkProfile,
    *,
    override_size: int | None = None,
    override_overlap: int | None = None,
    override_tokens: int | None = None,
    layouts: list[PageLayout] | None = None,
) -> list[str]:
    """
    Adaptive chunking that respects document structure when layout is available.
    """
    text = (text or "").strip()
    if not text:
        return []

    config = PROFILE_PRESETS[profile]
    chunk_size = override_size or config.chunk_size
    chunk_overlap = override_overlap or config.chunk_overlap
    max_tokens = override_tokens or config.max_tokens_per_chunk

    # If we have layout data, use hierarchical chunking
    if layouts is not None:
        try:
            return hierarchical_chunk_text(layouts, chunk_size, chunk_overlap)
        except Exception as e:
            # Fallback to text-only if hierarchical fails
            import logging
            logging.getLogger("rag.chunking.adaptive").warning(
                "Hierarchical chunking failed, falling back to text-only: %s", e
            )

    # Profile-specific pre-processing
    if profile == ChunkProfile.TABLE_HEAVY:
        # Split by table boundaries first, then run standard chunking
        table_parts = _split_by_tables(text)
        all_chunks: list[str] = []
        for part in table_parts:
            chunks = deepdoc_chunk_text(
                part,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                max_tokens_per_chunk=max_tokens,
            )
            all_chunks.extend(chunks)
        return _dedupe_chunks(all_chunks)

    if profile == ChunkProfile.CODE_MIXED:
        # Split by code blocks, chunk code parts smaller, text parts normally
        code_parts = _split_by_code_blocks(text)
        all_chunks: list[str] = []
        for part in code_parts:
            if CODE_BLOCK_RE.search(part):
                # This is a code block — treat as one chunk if small enough
                if len(part) <= chunk_size * 2:
                    all_chunks.append(part)
                else:
                    sub_chunks = deepdoc_chunk_text(
                        part,
                        chunk_size=max(chunk_size // 2, 300),
                        chunk_overlap=chunk_overlap,
                        max_tokens_per_chunk=max(max_tokens // 2, 150),
                    )
                    all_chunks.extend(sub_chunks)
            else:
                chunks = deepdoc_chunk_text(
                    part,
                    chunk_size=chunk_size,
                    chunk_overlap=chunk_overlap,
                    max_tokens_per_chunk=max_tokens,
                )
                all_chunks.extend(chunks)
        return _dedupe_chunks(all_chunks)

    # Standard profiles (CLEAN_TEXT, OCR_NOISY, GENERAL)
    return deepdoc_chunk_text(
        text,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        max_tokens_per_chunk=max_tokens,
    )


def _dedupe_chunks(chunks: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for chunk in chunks:
        key = chunk.strip()
        if key and key not in seen:
            seen.add(key)
            result.append(key)
    return result
