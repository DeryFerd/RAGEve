"use client";

import { useCallback, useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/Button";
import type { DiscoveredDataset } from "@/lib/types";
import type { ToastVariant } from "@/stores/useToastStore";
import styles from "./HuggingFacePage.module.css";

const fmtSize = (bytes: number) => {
  if (bytes < 1024 ** 2) return `${(bytes / 1024).toFixed(1)} KB`;
  if (bytes < 1024 ** 3) return `${(bytes / 1024 ** 2).toFixed(1)} MB`;
  return `${(bytes / 1024 ** 3).toFixed(2)} GB`;
};

type FilterType = "all" | "indexed" | "not_indexed";

interface LocalDatasetsLibraryProps {
  datasets: DiscoveredDataset[];
  discovering: boolean;
  downloadStatus: unknown;
  isDownloading: boolean;
  onDiscover: () => Promise<void>;
  onRestartPolling: (datasetId: string) => void;
  onIngestNow: (datasetId: string) => void;
  addToast: (msg: string, variant?: ToastVariant) => void;
  router: ReturnType<typeof useRouter>;
}

export function LocalDatasetsLibrary({
  datasets,
  discovering,
  downloadStatus,
  isDownloading,
  onDiscover,
  onRestartPolling,
  onIngestNow,
  addToast,
  router,
}: LocalDatasetsLibraryProps) {
  const [filter, setFilter] = useState<FilterType>("all");

  const indexedCount = datasets.filter((d) => d.is_ingested).length;
  const notIndexedCount = datasets.length - indexedCount;

  const filtered =
    filter === "all"
      ? datasets
      : filter === "indexed"
      ? datasets.filter((d) => d.is_ingested)
      : datasets.filter((d) => !d.is_ingested);

  const handleRefresh = useCallback(async () => {
    try {
      await onDiscover();
      const saved = window.localStorage.getItem("hf_active_download_dataset_id");
      if (saved) {
        onRestartPolling(saved);
      }
    } catch (err) {
      addToast(`Refresh failed: ${err instanceof Error ? err.message : String(err)}`, "error");
    }
  }, [onDiscover, onRestartPolling, addToast]);

  return (
    <div className={styles.localSection}>
      {/* ── Section Header ───────────────────────────────────── */}
      <div className={styles.libraryHeader}>
        <div>
          <h2 className={styles.libraryTitle}>Local Library</h2>
          <p style={{ fontSize: "var(--text-sm)", color: "var(--text-muted)", marginTop: "var(--space-1)" }}>
            {datasets.length} dataset{datasets.length !== 1 ? "s" : ""} • {indexedCount} indexed
          </p>
        </div>
        <div className={styles.libraryControls}>
          <div className={styles.libraryFilterTabs}>
            <button
              className={`${styles.libraryFilterTab} ${filter === "all" ? styles.libraryFilterTabActive : ""}`}
              onClick={() => setFilter("all")}
            >
              All <span className={styles.libraryCount}>{datasets.length}</span>
            </button>
            <button
              className={`${styles.libraryFilterTab} ${filter === "indexed" ? styles.libraryFilterTabActive : ""}`}
              onClick={() => setFilter("indexed")}
            >
              Indexed <span className={styles.libraryCount}>{indexedCount}</span>
            </button>
            <button
              className={`${styles.libraryFilterTab} ${filter === "not_indexed" ? styles.libraryFilterTabActive : ""}`}
              onClick={() => setFilter("not_indexed")}
            >
              Not Indexed <span className={styles.libraryCount}>{notIndexedCount}</span>
            </button>
          </div>
          <Button
            variant="secondary"
            size="sm"
            onClick={() => void handleRefresh()}
            loading={discovering}
          >
            ↻ Refresh
          </Button>
        </div>
      </div>

      {/* Active download banner */}
      {isDownloading && downloadStatus != null && (
        <div className={styles.activeDownloadBanner}>
          <span className={styles.bannerDot} />
          <span>Download in progress — see details above</span>
        </div>
      )}

      {/* ── Grid ─────────────────────────────────────────────── */}
      {datasets.length === 0 ? (
        <div className={styles.libraryCardEmptyState}>
          No local datasets found. Start a download to get started.
        </div>
      ) : filtered.length === 0 ? (
        <div className={styles.libraryCardEmptyState}>
          {filter === "indexed" ? "No indexed datasets yet." : "All datasets are indexed!"}
        </div>
      ) : (
        <>
          <div className={styles.libraryGrid}>
            {filtered.map((ds) => (
              <div key={ds.dataset_id} className={styles.libraryCard}>
                <div className={styles.libraryCardHeader}>
                  <div className={styles.libraryCardIcon}>⬡</div>
                  <div className={styles.libraryCardInfo}>
                    <div className={styles.libraryCardName}>
                      {ds.dataset_id}
                      {ds.is_ingested && <span className={styles.ingestedDot} title="Indexed in Qdrant" />}
                    </div>
                    <div className={styles.libraryCardMeta}>
                      <span>📁 {ds.file_count} file{ds.file_count !== 1 ? "s" : ""}</span>
                      <span>💾 {fmtSize(ds.total_size_bytes)}</span>
                      {ds.splits.length > 0 && (
                        <span>🏷️ {ds.splits.join(", ")}</span>
                      )}
                    </div>
                    <div className={styles.libraryCardBadges}>
                      {ds.is_ingested ? (
                        <span className={`${styles.libraryBadge} ${styles.badgeSuccess}`}>
                          Indexed
                        </span>
                      ) : (
                        <span className={`${styles.libraryBadge} ${styles.badgeDefault}`}>
                          Not Indexed
                        </span>
                      )}
                    </div>
                  </div>
                </div>
                <div className={styles.libraryCardActions}>
                  {ds.is_ingested ? (
                    <Button size="sm" onClick={() => router.push("/chat")}>
                      Chat
                    </Button>
                  ) : (
                    <Button size="sm" onClick={() => onIngestNow(ds.dataset_id)}>
                      Ingest Now
                    </Button>
                  )}
                </div>
              </div>
            ))}
          </div>
          {filtered.length < datasets.length && (
            <div className={styles.libraryCardCount}>
              Showing {filtered.length} of {datasets.length} datasets
            </div>
          )}
        </>
      )}
    </div>
  );
}
