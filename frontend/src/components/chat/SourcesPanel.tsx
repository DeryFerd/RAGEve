"use client";

import { useState } from "react";
import type { SourceChunk } from "@/lib/types";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import PDFPreviewWithHighlights from "@/components/PDFPreviewWithHighlights";
import styles from "./SourcesPanel.module.css";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface SourcesPanelProps {
  sources: SourceChunk[];
  rerankerModel?: string | null;
}

export function SourcesPanel({ sources, rerankerModel }: SourcesPanelProps) {
  const [previewSource, setPreviewSource] = useState<SourceChunk | null>(null);

  const canPreview = (s: SourceChunk) => {
    return !!(
      s.blocks &&
      s.blocks.length > 0 &&
      s.datasetId &&
      s.source
    );
  };

  const getPdfUrl = (s: SourceChunk) => {
    return `${API_BASE}/datasets/${s.datasetId}/download/${encodeURIComponent(s.source!)}`;
  };

  return (
    <div className={styles.panel}>
      <div className={styles.header}>
        <span className={styles.title}>Sources</span>
        <div className={styles.headerRight}>
          {rerankerModel && (
            <span className={styles.rerankerBadge} title={`Reranked with ${rerankerModel}`}>
              &#x1F504; {rerankerModel.split("/").pop()}
            </span>
          )}
          <span className={styles.count}>{sources.length} chunk{sources.length !== 1 ? "s" : ""}</span>
        </div>
      </div>

      {sources.length === 0 ? (
        <div className={styles.empty}>
          No sources yet.<br />Send a message to see retrieved chunks.
        </div>
      ) : (
        <div className={styles.list}>
          {sources.map((s, i) => (
            <div key={String(s.chunk_id ?? `source-${i}`)} className={styles.sourceCard}>
              <div className={styles.sourceMeta}>
                <div className={styles.sourceHeaderLeft}>
                  <span className={styles.sourceName} title={s.source || "unknown"}>
                    {s.source || "unknown"}
                  </span>
                  {s.search_type === "hybrid" && (
                    <Badge variant="info" title="Retrieved by hybrid search (dense + sparse)">
                      HYBRID
                    </Badge>
                  )}
                </div>
                <div className={styles.scoreRow}>
                  {rerankerModel && s.cosine_score != null ? (
                    <>
                      <Badge variant="muted" title="Bi-encoder cosine similarity">
                        &#x2191; {(s.cosine_score * 100).toFixed(1)}%
                      </Badge>
                      <Badge variant={s.score > 0.85 ? "success" : s.score > 0.7 ? "warning" : "default"} title="Cross-encoder relevance score">
                        &#x1F504; {(s.score * 100).toFixed(1)}%
                      </Badge>
                    </>
                  ) : (
                    <Badge variant={s.score > 0.85 ? "success" : s.score > 0.7 ? "warning" : "default"}>
                      {(s.score * 100).toFixed(1)}%
                    </Badge>
                  )}
                  {canPreview(s) && (
                    <Button
                      size="sm"
                      variant="secondary"
                      onClick={() => setPreviewSource(s)}
                      title="View PDF with highlights"
                    >
                      Preview
                    </Button>
                  )}
                </div>
              </div>
              <div className={styles.sourceText}>{s.text}</div>
            </div>
          ))}
        </div>
      )}

      {previewSource && (
        <Modal
          open={!!previewSource}
          onClose={() => setPreviewSource(null)}
          title={`PDF Preview: ${previewSource.source}`}
        >
          <div style={{ height: "80vh", overflow: "auto" }}>
            <PDFPreviewWithHighlights
              pdfUrl={getPdfUrl(previewSource)}
              highlights={previewSource.blocks || undefined}
            />
          </div>
        </Modal>
      )}
    </div>
  );
}
