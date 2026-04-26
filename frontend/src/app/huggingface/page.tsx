"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import {
  discoverHFDatasets,
  downloadHFDataset,
  getHFDownloadStatus,
  cancelHFDownload,
  previewHFDataset,
  submitHFIngest,
} from "@/lib/api/datasets";
import { useToastStore } from "@/stores/useToastStore";
import type {
  DiscoveredDataset,
  HuggingFaceDownloadStatusResponse,
  HuggingFacePreviewResponse,
} from "@/lib/types";
import { HubSearch } from "./HubSearch";
import { DatasetCard } from "./DatasetCard";
import { DownloadProgressCard } from "./DownloadProgressCard";
import { LocalDatasetsLibrary } from "./LocalDatasetsLibrary";
import styles from "./HuggingFacePage.module.css";

const ACTIVE_DOWNLOAD_KEY = "hf_active_download_dataset_id";
const TERMINAL_STATES = new Set(["completed", "failed", "cancelled"]);

export default function HuggingFacePage() {
  const router = useRouter();
  const { addToast } = useToastStore();

  // Input + preview state
  const [datasetIdInput, setDatasetIdInput] = useState("");
  const firstMountRef = useRef(true);
  const previewTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const downloadPollRef = useRef<number | null>(null);
  const prevIngestStatusRef = useRef<string | null>(null);

  const [preview, setPreview] = useState<HuggingFacePreviewResponse | null>(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewError, setPreviewError] = useState<string | null>(null);
  const [selectedConfig, setSelectedConfig] = useState("");
  const [autoIngest, setAutoIngest] = useState(false);
  const [autoIngestTextCols, setAutoIngestTextCols] = useState<string[]>([]);
  const [rowLimitInput, setRowLimitInput] = useState("");

  // Download state
  const [downloadingDatasetId, setDownloadingDatasetId] = useState<string | null>(null);
  const [downloadStatus, setDownloadStatus] = useState<HuggingFaceDownloadStatusResponse | null>(null);

  // Local datasets
  const [discovering, setDiscovering] = useState(false);
  const [datasets, setDatasets] = useState<DiscoveredDataset[]>([]);

  // Polling helpers
  const stopDownloadPolling = useCallback(() => {
    if (downloadPollRef.current != null) {
      window.clearInterval(downloadPollRef.current);
      downloadPollRef.current = null;
    }
  }, []);

  // Handlers
  const handleDiscover = useCallback(async () => {
    setDiscovering(true);
    try {
      const result = await discoverHFDatasets();
      setDatasets(result.datasets);
    } catch (err) {
      addToast(`Discovery failed: ${err instanceof Error ? err.message : String(err)}`, "error");
    } finally {
      setDiscovering(false);
    }
  }, [addToast]);

  const startDownloadPolling = useCallback(
    (datasetId: string) => {
      stopDownloadPolling();
      setDownloadingDatasetId(datasetId);
      prevIngestStatusRef.current = null;

      const poll = async () => {
        try {
          const st = await getHFDownloadStatus(datasetId);
          setDownloadStatus(st);

          // Detect ingest status changes
          if (st.ingest_status && prevIngestStatusRef.current !== st.ingest_status) {
            if (TERMINAL_STATES.has(st.ingest_status)) {
              if (st.ingest_status === "completed") {
                addToast(
                  st.auto_ingest && st.ingested
                    ? `✓ Downloaded & indexed! Ready to chat.`
                    : `✓ ${st.dataset_id} ingestion completed.`,
                  "success"
                );
                void handleDiscover();
              } else if (st.ingest_status === "failed") {
                addToast(`Ingestion failed: ${st.ingest_error || st.message}`, "error");
              }
            }
            prevIngestStatusRef.current = st.ingest_status;
          }

          const downloadTerminal = TERMINAL_STATES.has(st.status);
          const ingestTerminal = st.ingest_status ? TERMINAL_STATES.has(st.ingest_status) : true;

          if (downloadTerminal && ingestTerminal) {
            stopDownloadPolling();
            window.localStorage.removeItem(ACTIVE_DOWNLOAD_KEY);

            if (st.status === "completed") {
              addToast(
                st.auto_ingest && st.ingested
                  ? `✓ Downloaded & indexed! Ready to chat.`
                  : `✓ ${st.dataset_id} downloaded successfully.`,
                "success"
              );
              void handleDiscover();
              setDownloadingDatasetId(null);
            } else if (st.status === "cancelled") {
              addToast(`Download cancelled.`, "info");
              void handleDiscover();
              setDownloadingDatasetId(null);
            } else if (st.status === "failed") {
              addToast(`Download failed: ${st.error || st.message}`, "error");
              setDownloadingDatasetId(null);
            }
          }
        } catch {
          // Keep polling through transient errors
        }
      };

      poll();
      downloadPollRef.current = window.setInterval(poll, 1500);
    },
    [stopDownloadPolling, addToast, handleDiscover]
  );

  // Lifecycle
  useEffect(() => {
    if (firstMountRef.current) {
      firstMountRef.current = false;
      void handleDiscover();
      const saved = window.localStorage.getItem(ACTIVE_DOWNLOAD_KEY);
      if (saved) {
        void startDownloadPolling(saved);
      }
    }
  }, [handleDiscover, startDownloadPolling]);

  useEffect(() => {
    return () => {
      if (previewTimerRef.current) clearTimeout(previewTimerRef.current);
      stopDownloadPolling();
      setDatasetIdInput("");
      setPreview(null);
      setPreviewError(null);
    };
  }, [stopDownloadPolling]);

  // Debounced preview fetch
  const fetchPreview = useCallback(
    async (id: string) => {
      if (!id.trim() || id.trim().length < 2) {
        setPreview(null);
        setPreviewError(null);
        return;
      }
      setPreviewLoading(true);
      setPreviewError(null);
      try {
        const data = await previewHFDataset(id.trim());
        setPreview(data);
        if (data.default_config && !selectedConfig) {
          setSelectedConfig(data.default_config);
        }
        if (Object.keys(data.columns).length > 0) {
          const firstStringCol =
            Object.entries(data.columns).find(([, t]) => t === "string")?.[0] ??
            Object.keys(data.columns)[0];
          if (firstStringCol) {
            setAutoIngestTextCols([firstStringCol]);
          }
        }
      } catch (err) {
        setPreviewError(err instanceof Error ? err.message : "Could not load preview");
        setPreview(null);
      } finally {
        setPreviewLoading(false);
      }
    },
    [selectedConfig]
  );

  // Handlers
  const handleDatasetIdChange = useCallback(
    (val: string) => {
      setDatasetIdInput(val);
      setSelectedConfig("");
      setAutoIngestTextCols([]);
      if (previewTimerRef.current) clearTimeout(previewTimerRef.current);
      if (val.trim().length >= 2) {
        previewTimerRef.current = setTimeout(() => void fetchPreview(val), 600);
      } else {
        setPreview(null);
        setPreviewError(null);
      }
    },
    [fetchPreview]
  );

  const handleChipClick = useCallback(
    (id: string) => {
      setDatasetIdInput(id);
      setSelectedConfig("");
      setAutoIngestTextCols([]);
      if (previewTimerRef.current) clearTimeout(previewTimerRef.current);
      previewTimerRef.current = setTimeout(() => void fetchPreview(id), 600);
    },
    [fetchPreview]
  );

  const handleDownload = useCallback(async (overrideDatasetId?: string): Promise<void> => {
    const datasetId = (overrideDatasetId ?? datasetIdInput).trim();
    if (!datasetId) return;
    try {
      window.localStorage.setItem(ACTIVE_DOWNLOAD_KEY, datasetId);
      setDownloadStatus(null);
      await downloadHFDataset({
        dataset_id: datasetId,
        split: undefined,
        config: selectedConfig || undefined,
        auto_ingest: autoIngest,
        row_limit: rowLimitInput ? parseInt(rowLimitInput, 10) : undefined,
        text_columns: autoIngestTextCols.length > 0 ? autoIngestTextCols : undefined,
      });
      void startDownloadPolling(datasetId);
      addToast(`Download started for "${datasetId}"`, "info");
    } catch (err) {
      addToast(`Failed to start download: ${err instanceof Error ? err.message : String(err)}`, "error");
    }
  }, [datasetIdInput, selectedConfig, autoIngest, rowLimitInput, autoIngestTextCols, startDownloadPolling, addToast]);

  const handleCancelDownload = useCallback(async (): Promise<void> => {
    const datasetId = downloadingDatasetId ?? datasetIdInput.trim();
    if (!datasetId) return;
    try {
      await cancelHFDownload(datasetId);
      addToast(`Cancel requested for "${datasetId}"`, "info");
    } catch (err) {
      addToast(`Cancel failed: ${err instanceof Error ? err.message : String(err)}`, "error");
    }
  }, [downloadingDatasetId, datasetIdInput, addToast]);

  // Ingest handler
  const handleStartIngest = useCallback(async (datasetId?: string): Promise<void> => {
    const id = datasetId ?? downloadStatus?.dataset_id ?? datasetIdInput.trim();
    if (!id) return;
    try {
      await submitHFIngest(id, {
        split: undefined,
        text_columns: autoIngestTextCols.length > 0 ? autoIngestTextCols : undefined,
        row_limit: rowLimitInput ? parseInt(rowLimitInput, 10) : undefined,
        force: false,
      });
      void startDownloadPolling(id);
      addToast(`Ingestion started for "${id}"`, "info");
    } catch (err) {
      addToast(`Failed to start ingestion: ${err instanceof Error ? err.message : String(err)}`, "error");
    }
  }, [downloadStatus, datasetIdInput, autoIngestTextCols, rowLimitInput, startDownloadPolling, addToast]);

  const handleLibraryIngestNow = useCallback((datasetId: string) => {
    handleDatasetIdChange(datasetId);
    window.scrollTo({ top: 0, behavior: "smooth" });
    void handleStartIngest(datasetId);
  }, [handleDatasetIdChange, handleStartIngest]);

  // Derived state
  const isDownloading =
    downloadStatus != null && !TERMINAL_STATES.has(downloadStatus.status);

  const ingestStatus = downloadStatus?.ingest_status;
  const ingestCompleted = ingestStatus === "completed";
  const ingestFailed = ingestStatus === "failed";
  const isIngesting = ingestStatus === "ingesting";

  const autoIngestEnabled = downloadStatus?.auto_ingest === true;

  const textColumnOptions: Array<{ value: string; label: string; typeHint?: string }> =
    preview?.columns
      ? Object.entries(preview.columns).map(([name, type]) => ({
          value: name,
          label: name,
          typeHint: type === "string" ? undefined : type,
        }))
      : [];

  // Skeleton loader for preview card
  const renderPreviewSkeleton = () => (
    <div className={styles.previewCard}>
      <div className={styles.previewHeader}>
        <div className={styles.previewMain}>
          <div className={`${styles.skeleton} ${styles.skeletonAvatar}`} />
          <div className={styles.previewInfo}>
            <div className={`${styles.skeleton} ${styles.skeletonTitle}`} />
            <div style={{ display: "flex", gap: "var(--space-2)", marginTop: "var(--space-2)" }}>
              <div className={`${styles.skeleton}`} style={{ width: 80, height: 20 }} />
              <div className={`${styles.skeleton}`} style={{ width: 60, height: 20 }} />
            </div>
          </div>
        </div>
      </div>
      <div className={styles.previewDescription}>
        <div className={`${styles.skeleton} ${styles.skeletonText}`} style={{ width: "100%" }} />
        <div className={`${styles.skeleton} ${styles.skeletonText}`} style={{ width: "80%" }} />
      </div>
    </div>
  );

  return (
    <div className={styles.page}>
      {/* ── Zone 1: Discovery ──────────────────────────────────────── */}
      <HubSearch
        datasetId={datasetIdInput}
        onDatasetIdChange={handleDatasetIdChange}
        onChipClick={handleChipClick}
      />

      {/* Preview / Loading / Error */}
      {previewLoading && renderPreviewSkeleton()}
      {previewError && !previewLoading && (
        <div className={styles.previewCard} style={{ padding: "var(--space-4)", textAlign: "center" }}>
          <p style={{ color: "var(--text-primary)" }}>{previewError}</p>
        </div>
      )}

      {preview && !previewLoading && (
        <DatasetCard
          preview={preview}
          selectedConfig={selectedConfig}
          onConfigChange={setSelectedConfig}
          autoIngest={autoIngest}
          rowLimitInput={rowLimitInput}
          textColumnOptions={textColumnOptions}
          autoIngestTextCols={autoIngestTextCols}
          isDownloading={isDownloading}
          isIngesting={isIngesting}
          onAutoIngestChange={setAutoIngest}
          onAutoIngestTextColsChange={setAutoIngestTextCols}
          onRowLimitChange={setRowLimitInput}
          onDownload={handleDownload}
          onCancel={handleCancelDownload}
        />
      )}

      {/* Active download progress */}
      {downloadStatus && (
        <div style={{ marginTop: preview && !previewLoading ? "var(--space-6)" : "var(--space-8)" }}>
          <DownloadProgressCard
            downloadStatus={downloadStatus}
            preview={preview}
            autoIngestEnabled={autoIngestEnabled}
            ingestCompleted={ingestCompleted}
            ingestFailed={ingestFailed}
            isIngesting={isIngesting}
            onStartIngest={() => void handleStartIngest()}
            onCancel={() => void handleCancelDownload()}
          />
        </div>
      )}

      {/* ── Zone 3: Local Library ───────────────────────────────────── */}
      <LocalDatasetsLibrary
        datasets={datasets}
        discovering={discovering}
        downloadStatus={downloadStatus}
        isDownloading={isDownloading}
        onDiscover={handleDiscover}
        onRestartPolling={startDownloadPolling}
        onIngestNow={handleLibraryIngestNow}
        addToast={addToast}
        router={router}
      />
    </div>
  );
}
