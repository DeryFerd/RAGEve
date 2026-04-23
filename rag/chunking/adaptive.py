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
) -> list[tuple[str, list[Block]]]:
    """
    Chunk text respecting heading hierarchy.

    Strategy:
    1. Flatten all blocks from all pages
    2. Build heading hierarchy (parent-child relationships)
    3. Group blocks into sections (from one heading to next)
    4. For each section:
       - If section text fits in chunk_size, use as single chunk
       - If too large, split blocks into batches respecting chunk_size
       - Prepend section heading to first sub-chunk for context
    5. Return list of (chunk_text, source_blocks) tuples

    Args:
        layouts: Single PageLayout or list of PageLayout with blocks (should have column_index, level set)
        chunk_size: Target max characters per chunk
        chunk_overlap: Overlap between chunks (used for text splitting within blocks if needed)

    Returns:
        List of (chunk_text, source_blocks) tuples
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
    chunks: list[tuple[str, list[Block]]] = []

    def _split_blocks_into_chunks(blocks: list[Block], max_size: int) -> list[list[Block]]:
        """Split a list of blocks into batches where each batch's total text length <= max_size."""
        batches: list[list[Block]] = []
        current_batch: list[Block] = []
        current_len = 0

        for block in blocks:
            block_len = len(block.text)
            # If block itself is larger than max_size, we need to split it internally
            if block_len > max_size and not current_batch:
                # Single oversized block: split its text using deepdoc_chunk_text
                # We'll create artificial mini-blocks for each text chunk
                sub_texts = deepdoc_chunk_text(
                    block.text,
                    chunk_size=max_size,
                    chunk_overlap=chunk_overlap,
                    max_tokens_per_chunk=500,
                )
                for sub_text in sub_texts:
                    # Create a synthetic block that references the original block's bbox
                    sub_block = Block(
                        block_type=block.block_type,
                        bbox=block.bbox,
                        text=sub_text,
                        page=block.page,
                        order=block.order,
                        children=[],
                        metadata=block.metadata.copy(),
                        column_index=block.column_index,
                        level=block.level,
                        parent=block.parent,
                    )
                    batches.append([sub_block])
                continue

            if current_len + block_len <= max_size:
                current_batch.append(block)
                current_len += block_len
            else:
                if current_batch:
                    batches.append(current_batch)
                current_batch = [block]
                current_len = block_len

        if current_batch:
            batches.append(current_batch)

        return batches

    for section in sections:
        section_blocks = section["blocks"]
        if not section_blocks:
            continue

        section_text = " ".join(b.text for b in section_blocks if b != section["heading"])
        heading_block = section["heading"]

        if len(section_text) <= chunk_size:
            # Whole section fits as one chunk
            chunk_text_parts = []
            if heading_block:
                chunk_text_parts.append(heading_block.text)
                chunk_text_parts.append("")
            chunk_text_parts.extend(b.text for b in section_blocks if b != heading_block)
            chunk_text = "\n".join(chunk_text_parts).strip()
            if chunk_text:
                chunks.append((chunk_text, section_blocks.copy()))
        else:
            # Section too large: split blocks into batches
            # Exclude heading from automatic splitting; we'll prepend it to first batch
            non_heading_blocks = [b for b in section_blocks if b != heading_block]
            block_batches = _split_blocks_into_chunks(non_heading_blocks, chunk_size)

            for batch_idx, batch_blocks in enumerate(block_batches):
                chunk_text_parts = []
                if heading_block and batch_idx == 0:
                    chunk_text_parts.append(heading_block.text)
                    chunk_text_parts.append("")

                chunk_text_parts.extend(b.text for b in batch_blocks)
                chunk_text = "\n".join(chunk_text_parts).strip()
                if chunk_text:
                    # Include heading in the first batch's block list if present
                    source_blocks = batch_blocks.copy()
                    if heading_block and batch_idx == 0:
                        source_blocks = [heading_block] + batch_blocks
                    chunks.append((chunk_text, source_blocks))

    return chunks


def adaptive_chunk_text(
    text: str,
    profile: ChunkProfile,
    *,
    override_size: int | None = None,
    override_overlap: int | None = None,
    override_tokens: int | None = None,
    layouts: list[PageLayout] | None = None,
) -> list[tuple[str, list[Block]]]:
    """
    Adaptive chunking that respects document structure when layout is available.

    Returns:
        List of (chunk_text, source_blocks) tuples. When layouts are provided,
        source_blocks are the original Block objects from the layout. When layouts
        are not available (text-only), source_blocks is an empty list.
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
        all_chunks: list[tuple[str, list]] = []
        for part in table_parts:
            chunks = deepdoc_chunk_text(
                part,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                max_tokens_per_chunk=max_tokens,
            )
            # No block references available for text-only chunking
            all_chunks.extend((chunk, []) for chunk in chunks)
        return _dedupe_chunks_with_blocks(all_chunks)

    if profile == ChunkProfile.CODE_MIXED:
        # Split by code blocks, chunk code parts smaller, text parts normally
        code_parts = _split_by_code_blocks(text)
        all_chunks: list[tuple[str, list]] = []
        for part in code_parts:
            if CODE_BLOCK_RE.search(part):
                # This is a code block — treat as one chunk if small enough
                if len(part) <= chunk_size * 2:
                    all_chunks.append((part, []))
                else:
                    sub_chunks = deepdoc_chunk_text(
                        part,
                        chunk_size=max(chunk_size // 2, 300),
                        chunk_overlap=chunk_overlap,
                        max_tokens_per_chunk=max(max_tokens // 2, 150),
                    )
                    all_chunks.extend((sc, []) for sc in sub_chunks)
            else:
                chunks = deepdoc_chunk_text(
                    part,
                    chunk_size=chunk_size,
                    chunk_overlap=chunk_overlap,
                    max_tokens_per_chunk=max_tokens,
                )
                all_chunks.extend((c, []) for c in chunks)
        return _dedupe_chunks_with_blocks(all_chunks)

    # Standard profiles (CLEAN_TEXT, OCR_NOISY, GENERAL)
    chunks = deepdoc_chunk_text(
        text,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        max_tokens_per_chunk=max_tokens,
    )
    # No block references available for text-only chunking
    return [(chunk, []) for chunk in chunks]


def _dedupe_chunks_with_blocks(
    chunks: list[tuple[str, list[Block]]],
) -> list[tuple[str, list[Block]]]:
    """Deduplicate chunks while preserving block lists."""
    seen: set[str] = set()
    result: list[tuple[str, list[Block]]] = []
    for text, blocks in chunks:
        key = text.strip()
        if key and key not in seen:
            seen.add(key)
            result.append((text, blocks))
    return result
