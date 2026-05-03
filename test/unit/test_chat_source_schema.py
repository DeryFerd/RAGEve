from __future__ import annotations

import sys
from pathlib import Path

_project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_project_root))

from backend.schemas.chat import SourceChunkSchema


def test_source_chunk_schema_includes_pdf_location_metadata():
    source = SourceChunkSchema(
        chunk_id="chunk-1",
        text="A useful passage",
        score=0.91,
        source="paper.pdf",
        pages=[2, 3],
        blocks=[{"page": 2, "bbox": {"x0": 1, "y0": 2, "x1": 3, "y1": 4}}],
        datasetId="kb-123",
    )

    data = source.model_dump()

    assert data["pages"] == [2, 3]
    assert data["blocks"][0]["page"] == 2
    assert data["datasetId"] == "kb-123"
