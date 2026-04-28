"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { useState } from "react";
import dynamic from "next/dynamic";
import type { ChatMessageItem, SourceChunk } from "@/lib/types";
import { StreamingCursor } from "./StreamingCursor";
import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import styles from "./ChatMessage.module.css";

// Dynamically import PDFPreviewWithHighlights with SSR disabled
const PDFPreviewWithHighlights = dynamic(
  () => import("@/components/PDFPreviewWithHighlights").then(mod => mod.default),
  { ssr: false, loading: () => <div>Loading PDF preview...</div> }
);

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// Only show PDF preview for chunks with relevance score >= this threshold
const PREVIEW_SCORE_THRESHOLD = 0.7;

interface ChatMessageProps {
  message: ChatMessageItem;
  isStreaming?: boolean;
  sources?: SourceChunk[];
}

export function ChatMessage({ message, isStreaming = false, sources = [] }: ChatMessageProps) {
  const isUser = message.role === "user";
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
    <div className={`${styles.message} ${isUser ? styles.user : styles.assistant}`}>
      <div className={`${styles.avatar} ${isUser ? styles.userAvatar : styles.assistantAvatar}`}>
        {isUser ? (
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="1.5">
            <circle cx="7" cy="5" r="2.5" />
            <path d="M2 12c0-2.8 2.2-5 5-5s5 2.2 5 5" />
          </svg>
        ) : (
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="1.5">
            <path d="M2 2h10v7H8l-2 2V9H2V2z" />
          </svg>
        )}
      </div>
      <div className={styles.bubble}>
        <div className={styles.content}>
          <ReactMarkdown remarkPlugins={[remarkGfm]}>
            {message.content}
          </ReactMarkdown>
          {isStreaming && message.role === "assistant" && <StreamingCursor />}
        </div>
        {!isUser && sources.length > 0 && (
          <div className={styles.sources}>
            {sources.map((s, i) => (
              <div key={String(s.chunk_id ?? `source-${i}`)} className={styles.sourceCard}>
                <div className={styles.sourceMeta}>
                  <span className={styles.sourceName} title={s.source || "unknown"}>
                    {s.source || "unknown"}
                  </span>
                  <div className={styles.scoreRow}>
                    <span className={styles.score}>{(s.score * 100).toFixed(1)}%</span>
                    {canPreview(s) && s.score >= PREVIEW_SCORE_THRESHOLD && (
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
        <div className={styles.timestamp}>
          {new Date(message.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
        </div>
      </div>

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
