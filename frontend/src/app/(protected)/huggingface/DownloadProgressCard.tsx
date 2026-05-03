"use client";

import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/Button";
import type {
  HuggingFaceDownloadStatusResponse,
  HuggingFacePreviewResponse,
} from "@/lib/types";
import styles from "./HuggingFacePage.module.css";

const TERMINAL_STATES = new Set(["completed", "failed", "cancelled"]);

// Stage progress thresholds (heuristic, based on backend progress reporting)
const STAGE_PROGRESS_THRESHOLDS = {
  extracting: 30, // Show extracting as active when progress > 30%
  embedding: 60, // Show embedding as active when progress > 60%
} as const;

const _fmtBytes = (n: number | null | undefined): string => {
  if (n == null) return "—";
  if (n < 1024 ** 2) return `${(n / 1024).toFixed(1)} KB`;
  if (n < 1024 ** 3) return `${(n / 1024 ** 2).toFixed(1)} MB`;
  return `${(n / 1024 ** 3).toFixed(2)} GB`;
};

const _fmtSpeed = (bytesPerSecond: number): string => {
  if (bytesPerSecond < 1024) return `${bytesPerSecond.toFixed(0)} B/s`;
  if (bytesPerSecond < 1024 ** 2)
    return `${(bytesPerSecond / 1024).toFixed(1)} KB/s`;
  if (bytesPerSecond < 1024 ** 3)
    return `${(bytesPerSecond / 1024 ** 2).toFixed(1)} MB/s`;
  return `${(bytesPerSecond / 1024 ** 3).toFixed(2)} GB/s`;
};

const _fmtETA = (seconds: number): string => {
  if (seconds < 60) return `${Math.ceil(seconds)}s`;
  if (seconds < 3600) return `${Math.ceil(seconds / 60)}m`;
  return `${Math.ceil(seconds / 3600)}h`;
};

interface DownloadProgressCardProps {
  downloadStatus: HuggingFaceDownloadStatusResponse;
  preview: HuggingFacePreviewResponse | null;
  autoIngestEnabled: boolean;
  ingestCompleted: boolean;
  ingestFailed: boolean;
  isIngesting: boolean;
  datasets: { dataset_id: string }[];
  setActiveIngestDatasetId: (id: string) => void;
  onPanelUpdate: (id: string, updates: Record<string, unknown>) => void;
  onCancel: () => void;
}

export function DownloadProgressCard({
  downloadStatus,
  preview,
  autoIngestEnabled,
  ingestCompleted,
  ingestFailed,
  isIngesting,
  datasets,
  setActiveIngestDatasetId,
  onPanelUpdate,
  onCancel,
}: DownloadProgressCardProps) {
  const router = useRouter();

  // Track previous values for speed calculation
  const prevBytesRef = useRef<number>(downloadStatus.bytes_downloaded ?? 0);
  const prevTimeRef = useRef<number>(Date.now());
  const [speed, setSpeed] = useState<number>(0);
  const [eta, setEta] = useState<number | null>(null);

  // Calculate speed and ETA on each update
  useEffect(() => {
    const now = Date.now();
    const elapsedMs = now - prevTimeRef.current;
    if (elapsedMs > 500) {
      const bytesDelta =
        (downloadStatus.bytes_downloaded ?? 0) - prevBytesRef.current;
      if (bytesDelta > 0) {
        const bytesPerSecond = (bytesDelta / elapsedMs) * 1000;
        setSpeed(bytesPerSecond);

        // Calculate ETA
        const remainingBytes =
          (downloadStatus.total_bytes ?? 0) -
          (downloadStatus.bytes_downloaded ?? 0);
        if (remainingBytes > 0 && bytesPerSecond > 0) {
          setEta(remainingBytes / bytesPerSecond);
        } else {
          setEta(null);
        }
      }
      prevBytesRef.current = downloadStatus.bytes_downloaded ?? 0;
      prevTimeRef.current = now;
    }
  }, [downloadStatus.bytes_downloaded, downloadStatus.total_bytes]);

  // Prefer preview's full_dataset_id when available; fall back to raw dataset_id
  const datasetName = preview?.full_dataset_id ?? downloadStatus.dataset_id;

  const isCompleted = downloadStatus.status === "completed";
  const isFailed = downloadStatus.status === "failed";
  const isCancelled = downloadStatus.status === "cancelled";
  const isDownloading = !TERMINAL_STATES.has(downloadStatus.status);
  const showSuccessState = isCompleted && !isDownloading;

  // Stage computation
  const stages = [
    { key: "downloading", label: "Downloading" },
    { key: "extracting", label: "Extracting" },
    { key: "embedding", label: "Embedding" },
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
      if (
        isDownloading &&
        downloadStatus.progress > STAGE_PROGRESS_THRESHOLDS.extracting
      )
        return "active";
      return "pending";
    }
    if (key === "embedding") {
      if (isCompleted) return "done";
      if (isIngesting) return "active";
      if (
        isDownloading &&
        downloadStatus.progress > STAGE_PROGRESS_THRESHOLDS.embedding
      )
        return "active";
      return "pending";
    }
    return "pending";
  };

  const handleIngestNow = () => {
    const id = downloadStatus.dataset_id;
    setActiveIngestDatasetId(id);
    const ds = datasets.find((d) => d.dataset_id === id);
    if (ds) {
      onPanelUpdate(id, { expanded: true });
    }
  };

  return (
    <div className={styles.progressCard}>
      {/* Header */}
      <div className={styles.dlProgressHeader}>
        <div className={styles.dlProgressHeaderLeft}>
          <span className={styles.dlProgressDatasetName}>
            {isCompleted ? "✓ " : isFailed ? "✗ " : isCancelled ? "— " : ""}
            {datasetName}
            {downloadStatus.config && ` › ${downloadStatus.config}`}
          </span>
          <span className={styles.dlProgressSub}>
            {isIngesting
              ? "Indexing…"
              : ingestCompleted
                ? "Indexed!"
                : ingestFailed
                  ? "Indexing failed"
                  : ""}
          </span>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <span
            className={`${styles.dlProgressPct} ${
              isCompleted
                ? styles.dlProgressPctDone
                : isFailed
                  ? styles.dlProgressPctError
                  : ""
            }`}
          >
            {isCompleted
              ? "✓ Done"
              : isFailed
                ? "✗ Failed"
                : isCancelled
                  ? "— Cancelled"
                  : `${downloadStatus.progress}%`}
          </span>
          {isDownloading && (
            <Button variant="danger" size="sm" onClick={onCancel}>
              Cancel
            </Button>
          )}
        </div>
      </div>

      {/* Stage dots strip */}
      {!isCompleted && !isFailed && !isCancelled && (
        <div className={styles.dlProgressStages}>
          {stages.map((s) => {
            const state = getStageState(s.key);
            return (
              <div
                key={s.key}
                className={`${styles.dlStage} ${styles[`dlStage${state.charAt(0).toUpperCase() + state.slice(1)}`]}`}
              >
                <span className={styles.dlStageDot} />
                <span>{s.label}</span>
              </div>
            );
          })}
        </div>
      )}

      {/* Progress bar — hidden on terminal states */}
      {!isCompleted && !isFailed && !isCancelled && (
        <>
          <div className={styles.progressBarWrap}>
            <div
              className={`${styles.progressFill} ${
                isIngesting ? "" : styles.progressFillAnimating
              }`}
              style={{
                width: `${Math.max(0, Math.min(100, downloadStatus.progress))}%`,
              }}
            />
          </div>
          <div className={styles.dlProgressMeta}>
            <span>
              {downloadStatus.bytes_downloaded != null
                ? _fmtBytes(downloadStatus.bytes_downloaded)
                : "—"}
            </span>
            <span>
              {downloadStatus.total_bytes != null
                ? `/ ${_fmtBytes(downloadStatus.total_bytes)}`
                : "downloading…"}
            </span>
            {/* Speed and ETA */}
            {speed > 0 && (
              <span style={{ color: "var(--text-muted)" }}>
                {_fmtSpeed(speed)}
                {eta != null && eta > 0 && ` • ETA: ${_fmtETA(eta)}`}
              </span>
            )}
          </div>
        </>
      )}

      {/* Terminal-state full bar */}
      {(isCompleted || isFailed || isCancelled) && (
        <div className={styles.progressBarWrap}>
          <div
            className={`${styles.progressFill} ${
              isCompleted
                ? styles.progressFillSuccess
                : isFailed
                  ? styles.progressFillError
                  : ""
            }`}
            style={{ width: "100%" }}
          />
        </div>
      )}

      {/* Ingest sub-bar */}
      {isCompleted && autoIngestEnabled && (
        <div className={styles.ingestSubRow}>
          <div className={styles.ingestSubLabel}>
            {isIngesting
              ? "Indexing…"
              : ingestCompleted
                ? "✓ Indexed & ready to chat!"
                : ingestFailed
                  ? "✗ Indexing failed"
                  : "Indexing…"}
          </div>
          <div className={styles.ingestSubBar}>
            <div
              className={`${styles.ingestSubFill} ${
                ingestCompleted
                  ? styles.ingestSubFillDone
                  : ingestFailed
                    ? styles.ingestSubFillError
                    : ""
              }`}
              style={{
                width: isIngesting
                  ? "80%"
                  : ingestCompleted
                    ? "100%"
                    : ingestFailed
                      ? "100%"
                      : "0%",
              }}
            />
          </div>
        </div>
      )}

      {/* Message */}
      <div className={styles.progressMsg}>{downloadStatus.message}</div>

      {/* Ingest error */}
      {isIngesting && downloadStatus.ingest_message && (
        <div className={styles.progressSubMsg}>
          {downloadStatus.ingest_message}
        </div>
      )}

      {/* Errors */}
      {isFailed && downloadStatus.error && (
        <div className={styles.progressError}>
          Error: {downloadStatus.error}
        </div>
      )}
      {ingestFailed && downloadStatus.ingest_error && (
        <div className={styles.progressError}>
          Indexing error: {downloadStatus.ingest_error}
        </div>
      )}

      {/* Success CTA */}
      {showSuccessState && (
        <div className={styles.dlProgressCta}>
          {!autoIngestEnabled && !ingestCompleted && (
            <Button onClick={handleIngestNow}>Ingest Now</Button>
          )}
          {ingestCompleted && (
            <Button onClick={() => router.push("/chat")}>Go to Chat</Button>
          )}
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
