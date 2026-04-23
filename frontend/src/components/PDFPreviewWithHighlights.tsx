"use client";

import { useEffect, useRef, useState } from "react";
import * as pdfjsLib from "pdfjs-dist";
import "pdfjs-dist/web/pdf_viewer.css";

// Set worker source to the bundled worker
pdfjsLib.GlobalWorkerOptions.workerSrc = `//cdnjs.cloudflare.com/ajax/libs/pdf.js/${pdfjsLib.version}/pdf.worker.min.mjs`;

// Type definitions for block metadata
interface BBox {
  x0: number;
  y0: number;
  x1: number;
  y1: number;
}

interface Block {
  page: number;
  bbox: BBox;
  type: string;
}

interface PDFPreviewWithHighlightsProps {
  /** URL to fetch the PDF from */
  pdfUrl: string;
  /** List of blocks to highlight (from chunk metadata) */
  highlights: Block[] | null | undefined;
  /** Optional className */
  className?: string;
}

/**
 * PDFPreviewWithHighlights renders a PDF document with highlighted regions.
 *
 * Highlights are drawn as semi-transparent yellow rectangles over the
 * corresponding text blocks. The component uses PDF.js for rendering.
 */
export default function PDFPreviewWithHighlights({
  pdfUrl,
  highlights,
  className,
}: PDFPreviewWithHighlightsProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [pdfDoc, setPdfDoc] = useState<pdfjsLib.PDFDocumentProxy | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [numPages, setNumPages] = useState(0);

  // Load PDF
  useEffect(() => {
    let cancelled = false;

    async function loadPdf() {
      setLoading(true);
      setError(null);
      try {
        const apiKey = process.env.NEXT_PUBLIC_API_KEY;
        let loadingTask: pdfjsLib.PDFDocumentLoadingTask;
        if (apiKey) {
          loadingTask = pdfjsLib.getDocument({
            url: pdfUrl,
            httpHeaders: { "X-API-Key": apiKey },
          });
        } else {
          loadingTask = pdfjsLib.getDocument(pdfUrl);
        }
        const doc = await loadingTask.promise;
        if (cancelled) {
          doc.destroy();
          return;
        }
        setPdfDoc(doc);
        setNumPages(doc.numPages);
        setLoading(false);
      } catch (err: any) {
        if (!cancelled) {
          console.error("Failed to load PDF:", err);
          setError(err.message || "Failed to load PDF");
          setLoading(false);
        }
      }
    }

    loadPdf();

    return () => {
      cancelled = true;
      if (pdfDoc) {
        pdfDoc.destroy();
      }
    };
  }, [pdfUrl]);

  // Render a single page with highlights
  const renderPage = async (pageNum: number, canvas: HTMLCanvasElement) => {
    if (!pdfDoc) return;

    const page = await pdfDoc.getPage(pageNum);

    // Render at high scale for crisp text (2.5x)
    const RENDER_SCALE = 2.5;
    const viewport = page.getViewport({ scale: RENDER_SCALE });

    const context = canvas.getContext("2d");
    if (!context) return;

    canvas.width = viewport.width;
    canvas.height = viewport.height;

    // Render PDF page
    const renderContext = {
      canvasContext: context,
      viewport: viewport,
    };
    await page.render(renderContext).promise;

    // Draw highlights for blocks on this page
    if (highlights) {
      context.save();
      context.fillStyle = "rgba(255, 255, 0, 0.5)";
      context.strokeStyle = "rgba(255, 200, 0, 0.9)";
      context.lineWidth = 2;

      for (const block of highlights) {
        if (block.page !== pageNum) continue;

        const { x0, y0, x1, y1 } = block.bbox;
        // Scale coordinates to match render scale
        const sx = x0 * RENDER_SCALE;
        const sy = y0 * RENDER_SCALE;
        const sw = (x1 - x0) * RENDER_SCALE;
        const sh = (y1 - y0) * RENDER_SCALE;

        const cyTop = viewport.height - (y1 * RENDER_SCALE);
        const cyBottom = viewport.height - (y0 * RENDER_SCALE);
        const ch = cyBottom - cyTop;

        context.fillRect(sx, cyTop, sw, ch);
        context.strokeRect(sx, cyTop, sw, ch);
      }

      context.restore();
    }
  };

  if (loading) {
    return <div className={className}>Loading PDF…</div>;
  }

  if (error) {
    return <div className={className}>Error: {error}</div>;
  }

  if (!pdfDoc || numPages === 0) {
    return <div className={className}>No PDF to display</div>;
  }

  return (
    <div ref={containerRef} className={className} style={{ overflow: "auto" }}>
      {Array.from({ length: numPages }, (_, i) => i + 1).map((num) => (
        <div key={num} style={{ marginBottom: "20px", position: "relative" }}>
          <canvas
            id={`page-${num}`}
            style={{
              width: "100%",
              height: "auto",
              border: "1px solid #ccc",
              display: "block",
            }}
            ref={(canvas) => {
              if (canvas) {
                renderPage(num, canvas);
              }
            }}
          />
          <div style={{ textAlign: "center", marginTop: "4px" }}>Page {num}</div>
        </div>
      ))}
    </div>
  );
}
