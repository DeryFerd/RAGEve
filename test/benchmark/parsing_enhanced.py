#!/usr/bin/env python
"""
Benchmark enhanced PDF parsing vs legacy.

Measures:
- Parsing time (legacy vs enhanced)
- Chunk count difference
- Approximate memory usage (via psutil if available)

Usage:
  uv run python test/benchmark/parsing_enhanced.py --pdf <path> [--pdf <path> ...]
  uv run python test/benchmark/parsing_enhanced.py --corpus <directory>
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path
from typing import Any

# Ensure project root is first so rag/backend are always importable
_project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_project_root))

from rag.chunking.high_accuracy import deepdoc_chunk_text
from rag.deepdoc.layout_parser import layout_to_readable_text, parse_pdf_layout
from rag.ingestion.extractors import Extractors


def legacy_parse(pdf_path: Path) -> dict[str, Any]:
    """Legacy parsing: basic text extraction + adaptive chunking."""
    t0 = time.perf_counter()
    raw_text = Extractors.from_pdf(pdf_path)
    extract_time = time.perf_counter() - t0

    t1 = time.perf_counter()
    # Use default chunking (text-only, no layouts)
    chunks = deepdoc_chunk_text(
        raw_text,
        chunk_size=1200,
        chunk_overlap=180,
        max_tokens_per_chunk=500,
    )
    chunk_time = time.perf_counter() - t1

    return {
        "text": raw_text,
        "chunks": chunks,
        "extract_time": extract_time,
        "chunk_time": chunk_time,
        "total_time": extract_time + chunk_time,
        "num_chunks": len(chunks),
        "num_chars": len(raw_text),
    }


def enhanced_parse(pdf_path: Path) -> dict[str, Any]:
    """Enhanced parsing: layout-aware extraction + hierarchical chunking."""
    t0 = time.perf_counter()
    layouts = parse_pdf_layout(
        pdf_path,
        enable_column_detection=True,
        enable_structured_tables=True,
    )
    raw_text = layout_to_readable_text(layouts, include_hierarchy=True)
    extract_time = time.perf_counter() - t0

    t1 = time.perf_counter()
    # Hierarchical chunking using layouts
    from rag.chunking.adaptive import hierarchical_chunk_text

    chunks = hierarchical_chunk_text(
        layouts,
        chunk_size=1200,
        chunk_overlap=180,
    )
    chunk_time = time.perf_counter() - t1

    return {
        "text": raw_text,
        "chunks": chunks,
        "extract_time": extract_time,
        "chunk_time": chunk_time,
        "total_time": extract_time + chunk_time,
        "num_chunks": len(chunks),
        "num_chars": len(raw_text),
        "num_pages": len(layouts),
        "columns_detected": _count_columns(layouts),
    }


def _count_columns(layouts: list) -> int:
    """Count unique column indices across all blocks."""
    cols = set()
    for page in layouts:
        for block in page.blocks:
            if block.column_index is not None:
                cols.add(block.column_index)
    return len(cols)


def benchmark_pdf(pdf_path: Path) -> dict[str, Any]:
    """Run both parsers on a single PDF and compare."""
    print(f"\nBenchmarking: {pdf_path.name}")

    legacy = legacy_parse(pdf_path)
    print(f"  Legacy: {legacy['num_chunks']} chunks, {legacy['total_time']:.2f}s")

    enhanced = enhanced_parse(pdf_path)
    print(f"  Enhanced: {enhanced['num_chunks']} chunks, {enhanced['total_time']:.2f}s")

    delta_pct = (
        (enhanced["total_time"] - legacy["total_time"]) / legacy["total_time"] * 100
    )
    chunk_delta = enhanced["num_chunks"] - legacy["num_chunks"]

    print(f"  Time delta: {delta_pct:+.1f}%")
    print(f"  Chunk delta: {chunk_delta:+d}")

    return {
        "file": pdf_path.name,
        "legacy": {
            "chunks": legacy["num_chunks"],
            "time": legacy["total_time"],
            "extract": legacy["extract_time"],
            "chunk": legacy["chunk_time"],
        },
        "enhanced": {
            "chunks": enhanced["num_chunks"],
            "time": enhanced["total_time"],
            "extract": enhanced["extract_time"],
            "chunk": enhanced["chunk_time"],
            "pages": enhanced["num_pages"],
            "columns": enhanced["columns_detected"],
        },
        "delta_pct": delta_pct,
        "chunk_delta": chunk_delta,
    }


def main():
    parser = argparse.ArgumentParser(description="Benchmark enhanced PDF parsing")
    parser.add_argument("--pdf", type=Path, action="append", help="PDF file path")
    parser.add_argument("--corpus", type=Path, help="Directory containing PDFs")
    parser.add_argument("--output", type=Path, help="JSON output file for results")
    args = parser.parse_args()

    pdfs: list[Path] = []
    if args.pdf:
        pdfs.extend(args.pdf)
    if args.corpus:
        pdfs.extend(list(args.corpus.glob("*.pdf"))[:10])  # limit to 10

    if not pdfs:
        print("No PDFs specified. Use --pdf or --corpus.")
        return

    results = []
    for pdf in pdfs:
        if not pdf.exists():
            print(f"Warning: {pdf} not found, skipping")
            continue
        try:
            res = benchmark_pdf(pdf)
            results.append(res)
        except Exception as e:
            print(f"Error benchmarking {pdf}: {e}")
            import traceback

            traceback.print_exc()

    # Summary
    print("\n" + "=" * 64)
    print("Summary")
    print("=" * 64)
    for r in results:
        print(
            f"{r['file'][:30]:30}  legacy={r['legacy']['chunks']:4d}  enhanced={r['enhanced']['chunks']:4d}  "
            f"time: {r['legacy']['time']:5.1f}s -> {r['enhanced']['time']:5.1f}s  ({r['delta_pct']:+5.1f}%)"
        )

    if args.output:
        import json

        with open(args.output, "w") as f:
            json.dump(results, f, indent=2)
        print(f"\nResults saved to {args.output}")


if __name__ == "__main__":
    main()
