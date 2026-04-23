from rag.deepdoc.layout_parser import parse_pdf_layout
from rag.chunking.adaptive import hierarchical_chunk_text
from pathlib import Path

# Find a PDF in uploads or data
pdf_path = Path("data/uploads") / next(Path("data/uploads").glob("*/**/*.pdf"), None)
if pdf_path and pdf_path.exists():
    print(f"Testing with {pdf_path}")
    layouts = parse_pdf_layout(pdf_path)
    chunks = hierarchical_chunk_text(layouts, chunk_size=500, chunk_overlap=50)
    print(f"Got {len(chunks)} chunks")
    if chunks:
        text, blocks = chunks[0]
        print(f"First chunk: {len(text)} chars, {len(blocks)} source blocks")
        if blocks:
            print(f"Block 0: page={blocks[0].page}, bbox=({blocks[0].bbox.x0:.1f},{blocks[0].bbox.y0:.1f},{blocks[0].bbox.x1:.1f},{blocks[0].bbox.y1:.1f}), type={blocks[0].block_type}")
else:
    print("No PDF found in data/uploads to test")
