"use client";

import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/Button";
import type {
  HuggingFaceDownloadStatusResponse,
  HuggingFacePreviewResponse,
} from "@/lib/types";
import styles from "./HuggingFacePage.module.css";

const TERMINAL_STATES = new Set(["completed", "failed", "cancelled"]);

const fmtBytes = (n: number | null | undefined): string => {
  if (n == null) return "—";
  if (n < 1024 ** 2) return `${(n / 1024).toFixed(1)} KB`;
  if (n < 1024 ** 3) return `${(n / 1024 ** 2).toFixed(1)} MB`;
  return `${(n / 1024 ** 3).toFixed(2)} GB`;
};

interface DownloadProgressCardProps {
  downloadStatus: HuggingFaceDownloadStatusResponse;
  preview: HuggingFacePreviewResponse | null;
  autoIngestEnabled: boolean;
  ingestCompleted: boolean;
  ingestFailed: boolean;
  isIngesting: boolean;
  onStartIngest: () => void;
  onCancel: () => void;
}

export function DownloadProgressCard({
  downloadStatus,
  preview,
  autoIngestEnabled,
  ingestCompleted,
  ingestFailed,
  isIngesting,
  onStartIngest,
  onCancel,
}: DownloadProgressCardProps) {
  const router = useRouter();

  const datasetName = preview?.full_dataset_id ?? downloadStatus.dataset_id;

  const isCompleted = downloadStatus.status === "completed";
  const isFailed = downloadStatus.status === "failed";
  const isCancelled = downloadStatus.status === "cancelled";
  const isDownloading = !TERMINAL_STATES.has(downloadStatus.status);

  const stages = [
    { key: "downloading", label: "Download" },
    { key: "extracting", label: "Extract" },
    { key: "embedding", label: "Index" },
    { key: "ready", label: "Ready" },
  ];

  const getStageState = (key: string) => {
    if (isFailed) return "error";
    if (isCancelled) return "pending";
    if (key === "ready") {
      if (isCompleted) return "done";
      if (isDownloading) return "pending";
    }
    if (key === "downloading") {
      if (isCompleted) return "done";
      if (isDownloading) return "active";
      return "pending";
    }
    if (key === "extracting") {
      if (isCompleted) return "done";
      if (isDownloading && downloadStatus.progress > 30) return "active";
      return "pending";
    }
    if (key === "embedding") {
      if (isCompleted) return "done";
      if (isIngesting) return "active";
      if (isDownloading && downloadStatus.progress > 60) return "active";
      return "pending";
    }
    return "pending";
  };

  return (
    <div className={styles.progressCard}>
      {/* ── Header ───────────────────────────────────────────── */}
      <div className={styles.progressHeader}>
        <div className={styles.progressTitleRow}>
          <span className={styles.progressDatasetName}>
            {isCompleted ? "✓ " : isFailed ? "✗ " : isCancelled ? "— " : ""}
            {datasetName}
            {downloadStatus.config && ` › ${downloadStatus.config}`}
          </span>
          {isIngesting && <span className={styles.progressStatus}>Indexing…</span>}
          {ingestCompleted && <span className={styles.progressStatus} style={{ color: "var(--text-primary)" }}>✓ Ready</span>}
          {ingestFailed && <span className={styles.progressStatus} style={{ color: "var(--text-primary)" }}>✗ Index failed</span>}
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: "var(--space-2)" }}>
          <span
            className={styles.progressPct}
          >
            {isCompleted ? "✓ Done" : isFailed ? "✗ Failed" : isCancelled ? "— Cancelled" : `${downloadStatus.progress}%`}
          </span>
          {isDownloading && (
            <Button variant="danger" size="sm" onClick={onCancel}>
              Cancel
            </Button>
          )}
        </div>
      </div>

      {/* ── Stage Indicators ─────────────────────────────────── */}
      {!isCompleted && !isFailed && !isCancelled && (
        <div className={styles.progressStages}>
          {stages.map((s) => {
            const state = getStageState(s.key);
            return (
              <div key={s.key} className={`${styles.progressStage} ${styles[`progressStage${state.charAt(0).toUpperCase() + state.slice(1)}`]}`}>
                <div className={styles.stageDot} />
                <span className={styles.stageLabel}>{s.label}</span>
              </div>
            );
          })}
        </div>
      )}

      {/* ── Progress Bar ─────────────────────────────────────── */}
      {!isCompleted && !isFailed && !isCancelled && (
        <>
          <div className={styles.progressBarWrap}>
            <div
              className={`${styles.progressFill} ${isIngesting ? "" : styles.progressFillAnimating}`}
              style={{ width: `${Math.max(0, Math.min(100, downloadStatus.progress))}%` }}
            />
          </div>
          <div className={styles.progressMeta}>
            <span>{downloadStatus.bytes_downloaded != null ? fmtBytes(downloadStatus.bytes_downloaded) : "—"}</span>
            <span>{downloadStatus.total_bytes != null ? `/ ${fmtBytes(downloadStatus.total_bytes)}` : "downloading…"}</span>
          </div>
        </>
      )}

      {/* ── Terminal State Bar ───────────────────────────────── */}
      {(isCompleted || isFailed || isCancelled) && (
        <div className={styles.progressBarWrap}>
          <div
            className={`${styles.progressFill} ${isCompleted ? styles.progressFillSuccess : isFailed ? styles.progressFillError : ""}`}
            style={{ width: "100%" }}
          />
        </div>
      )}

      {/* ── Ingest Progress ──────────────────────────────────── */}
      {isCompleted && autoIngestEnabled && (
        <div className={styles.progressIngest}>
          <span className={styles.progressIngestLabel}>
            {isIngesting ? "Indexing…" : ingestCompleted ? "✓ Indexed & ready to chat!" : "Indexing…"}
          </span>
          <div className={styles.progressIngestBar}>
            <div
              className={`${styles.progressIngestFill} ${ingestCompleted ? styles.progressIngestFillDone : ingestFailed ? styles.progressIngestFillError : ""}`}
              style={{
                width: isIngesting ? "80%" : ingestCompleted ? "100%" : ingestFailed ? "100%" : "0%",
              }}
            />
          </div>
        </div>
      )}

      {/* ── Message / Details ────────────────────────────────── */}
      <div className={styles.progressDetails}>{downloadStatus.message}</div>

      {isIngesting && downloadStatus.ingest_message && (
        <div className={styles.progressDetails}>{downloadStatus.ingest_message}</div>
      )}

      {isFailed && downloadStatus.error && (
        <div className={styles.progressError}>Error: {downloadStatus.error}</div>
      )}
      {ingestFailed && downloadStatus.ingest_error && (
        <div className={styles.progressError}>Indexing error: {downloadStatus.ingest_error}</div>
      )}

      {/* ── CTAs ─────────────────────────────────────────────── */}
      {isCompleted && (
        <div className={styles.progressCta}>
          {!autoIngestEnabled && !ingestCompleted && !isIngesting && (
            <Button onClick={onStartIngest}>Ingest Now</Button>
          )}
          {ingestCompleted && <Button onClick={() => router.push("/chat")}>Go to Chat</Button>}
          {!ingestCompleted && (
            <Button variant="secondary" onClick={() => router.push("/chat")}>
              Go to Chat
            </Button>
          )}
        </div>
      )}
    </div>
  );
}
