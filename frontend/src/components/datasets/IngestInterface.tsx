"use client";

import { useState, useRef } from "react";
import { uploadFilesStreaming } from "@/lib/api/datasets";
import { useDatasetsStore } from "@/stores/useDatasetsStore";
import { Button } from "@/components/ui/Button";
import styles from "./IngestInterface.module.css";

interface IngestInterfaceProps {
  datasetId: string;
  onDone?: () => void;
}

export function IngestInterface({ datasetId, onDone }: IngestInterfaceProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [ingestProgress, setIngestProgress] = useState<{
    active: boolean;
    progress: number;
    message: string;
    stage: string;
    file?: string;
    fileIndex?: number;
    fileTotal?: number;
  }>({ active: false, progress: 0, message: "", stage: "" });

  const toggleDetail = useDatasetsStore((s) => s.toggleDetail);
  const setIngestProgressStore = useDatasetsStore((s) => s.setIngestProgress);

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files) return;
    setSelectedFiles((prev) => [...prev, ...Array.from(files)]);
    e.target.value = "";
  };

  const removeFile = (index: number) => {
    setSelectedFiles((prev) => prev.filter((_, i) => i !== index));
  };

  const handleIngest = async () => {
    if (selectedFiles.length === 0) return;

    setIngestProgress({
      active: true,
      progress: 0,
      message: "Starting ingestion...",
      stage: "uploading",
    });
    setIngestProgressStore(datasetId, {
      active: true,
      progress: 0,
      message: "Starting ingestion...",
      stage: "uploading",
    });

    try {
      await uploadFilesStreaming(
        datasetId,
        selectedFiles,
        {
          onStatus: (event) => {
            const progress = {
              active: true,
              progress: event.progress,
              message: event.message,
              stage: event.stage,
              file: event.file,
              fileIndex: event.file_index,
              fileTotal: event.file_total,
            };
            setIngestProgress(progress);
            setIngestProgressStore(datasetId, progress);
          },
          onFileDone: (event) => {
            const msg = `Completed ${event.file} (${event.file_index}/${event.file_total})`;
            setIngestProgress((prev) => ({
              ...prev,
              message: msg,
              progress: event.progress,
            }));
          },
          onDone: () => {
            setIngestProgress({
              active: false,
              progress: 100,
              message: "Ingestion complete",
              stage: "completed",
            });
            setIngestProgressStore(datasetId, {
              active: false,
              progress: 100,
              message: "Ingestion complete",
              stage: "completed",
            });
            setSelectedFiles([]);
            // Collapse and re-expand to refetch documents
            toggleDetail(datasetId);
            setTimeout(() => toggleDetail(datasetId), 100);
            onDone?.();
          },
          onError: (event) => {
            setIngestProgress({
              active: false,
              progress: 0,
              message: event.message,
              stage: "failed",
            });
            setIngestProgressStore(datasetId, {
              active: false,
              progress: 0,
              message: event.message,
              stage: "failed",
            });
          },
        }
      );
    } catch {
      setIngestProgress({
        active: false,
        progress: 0,
        message: "Ingestion failed",
        stage: "failed",
      });
      setIngestProgressStore(datasetId, {
        active: false,
        progress: 0,
        message: "Ingestion failed",
        stage: "failed",
      });
    }
  };

  return (
    <div className={styles.container}>
      <input
        ref={fileInputRef}
        type="file"
        multiple
        className={styles.hiddenInput}
        onChange={handleFileSelect}
      />

      <div className={styles.uploadRow}>
        <Button
          variant="secondary"
          size="sm"
          onClick={() => fileInputRef.current?.click()}
        >
          Upload More Files
        </Button>
        {selectedFiles.length > 0 && (
          <Button
            variant="primary"
            size="sm"
            onClick={handleIngest}
            disabled={ingestProgress.active}
          >
            Ingest All ({selectedFiles.length})
          </Button>
        )}
      </div>

      {selectedFiles.length > 0 && (
        <ul className={styles.fileList}>
          {selectedFiles.map((file, idx) => (
            <li key={`${file.name}-${idx}`} className={styles.fileItem}>
              <span className={styles.fileName}>{file.name}</span>
              <span className={styles.fileSize}>
                {(file.size / 1024).toFixed(1)} KB
              </span>
              <button
                className={styles.removeBtn}
                onClick={() => removeFile(idx)}
                disabled={ingestProgress.active}
                aria-label={`Remove ${file.name}`}
              >
                <svg width="12" height="12" viewBox="0 0 12 12" fill="none" stroke="currentColor" strokeWidth="1.5">
                  <path d="M1 1l10 10M11 1L1 11" />
                </svg>
              </button>
            </li>
          ))}
        </ul>
      )}

      {ingestProgress.active && (
        <div className={styles.progressSection}>
          <div className={styles.progressHeader}>
            <span className={styles.progressStage}>
              {ingestProgress.stage}
            </span>
            <span className={styles.progressPct}>
              {Math.round(ingestProgress.progress)}%
            </span>
          </div>
          <div className={styles.progressBar}>
            <div
              className={styles.progressFill}
              style={{ width: `${ingestProgress.progress}%` }}
            />
          </div>
          {ingestProgress.message && (
            <div className={styles.progressMessage}>
              {ingestProgress.file && (
                <span className={styles.progressFile}>
                  {ingestProgress.file}
                  {ingestProgress.fileIndex && ingestProgress.fileTotal
                    ? ` (${ingestProgress.fileIndex}/${ingestProgress.fileTotal})`
                    : ""}
                  :{" "}
                </span>
              )}
              {ingestProgress.message}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
