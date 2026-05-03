"use client";

import { useState } from "react";
import { MultiSelect } from "@/components/ui/MultiSelect";
import { Button } from "@/components/ui/Button";
import type { HuggingFacePreviewResponse } from "@/lib/types";
import styles from "./HuggingFacePage.module.css";

interface DatasetCardProps {
  preview: HuggingFacePreviewResponse;
  selectedConfig: string;
  onConfigChange: (config: string) => void;
  autoIngest: boolean;
  rowLimitInput: string;
  textColumnOptions: Array<{ value: string; label: string; typeHint?: string }>;
  autoIngestTextCols: string[];
  isDownloading: boolean;
  isIngesting: boolean;
  onAutoIngestChange: (v: boolean) => void;
  onAutoIngestTextColsChange: (cols: string[]) => void;
  onRowLimitChange: (v: string) => void;
  onDownload: () => Promise<void>;
  onCancel: () => Promise<void>;
}

export function DatasetCard({
  preview,
  selectedConfig,
  onConfigChange,
  autoIngest,
  rowLimitInput,
  textColumnOptions,
  autoIngestTextCols,
  isDownloading,
  isIngesting: _isIngesting,
  onAutoIngestChange,
  onAutoIngestTextColsChange,
  onRowLimitChange,
  onDownload,
  onCancel,
}: DatasetCardProps) {
  const [expanded, setExpanded] = useState(false);
  const [showFullDesc, setShowFullDesc] = useState(false);

  const hasConfigs = preview.configs.length > 0;
  const hasTextColumns = textColumnOptions.length > 0;
  const showIngestOptions = autoIngest && !isDownloading;
  const isDisabled = isDownloading || (hasConfigs && !selectedConfig);

  const sourceClass =
    preview.source === "hf-hub"
      ? styles.sourceBadgeBlue
      : preview.source === "datasets-server"
        ? styles.sourceBadgeOrange
        : styles.sourceBadgeGray;

  const sourceLabel =
    preview.source === "hf-hub"
      ? "HF Hub"
      : preview.source === "datasets-server"
        ? "datasets-server"
        : "Hub API";

  // Determine if description needs truncation (2 lines ≈ 200 chars)
  const needsTruncate = preview.description && preview.description.length > 200;

  return (
    <div className={styles.previewCard}>
      {/* ── Header ───────────────────────────────────────────── */}
      <div className={styles.previewHeader}>
        <div className={styles.previewMain}>
          <div className={styles.previewIcon}>⬡</div>
          <div className={styles.previewInfo}>
            <div className={styles.previewName}>{preview.full_dataset_id}</div>
            <div className={styles.previewBadges}>
              {preview.estimated_size_human && (
                <span className={`${styles.sourceBadge} ${sourceClass}`}>
                  {preview.estimated_size_human}
                </span>
              )}
              {preview.splits.length > 0 && (
                <span className={`${styles.sourceBadge} ${sourceClass}`}>
                  {preview.splits.length} split
                  {preview.splits.length !== 1 ? "s" : ""}
                </span>
              )}
              {preview.license && (
                <span className={`${styles.sourceBadge} ${sourceClass}`}>
                  {preview.license}
                </span>
              )}
              <span className={`${styles.sourceBadge} ${sourceClass}`}>
                {sourceLabel}
              </span>
            </div>
          </div>
        </div>
        <div className={styles.previewActions}>
          {isDownloading ? (
            <Button variant="danger" size="sm" onClick={onCancel}>
              Cancel
            </Button>
          ) : (
            <Button onClick={onDownload} disabled={isDisabled}>
              Download
            </Button>
          )}
        </div>
      </div>

      {/* ── Description ───────────────────────────────────────── */}
      {preview.description && (
        <div className={styles.previewDescription}>
          <p
            className={
              needsTruncate && !showFullDesc
                ? styles.previewDescriptionClamped
                : ""
            }
          >
            {preview.description}
          </p>
          {needsTruncate && (
            <button
              className={styles.previewExpandBtn}
              onClick={() => setShowFullDesc(!showFullDesc)}
              type="button"
            >
              {showFullDesc ? "▲ Show less" : "▼ Show more"}
            </button>
          )}
        </div>
      )}

      {/* ── Configuration Expand Trigger ─────────────────────── */}
      {(hasConfigs || hasTextColumns) && (
        <button
          className={styles.previewExpandBtn}
          onClick={() => setExpanded(!expanded)}
          type="button"
        >
          {expanded ? "▲ Hide configuration" : "▼ Configure ingestion"}
        </button>
      )}

      {/* ── Configuration Panel (Slide-up) ───────────────────── */}
      {expanded && (
        <div className={styles.previewPanel}>
          {/* Config selection */}
          {hasConfigs && (
            <div className={styles.panelSection}>
              <label className={styles.panelLabel}>Configuration</label>
              {!selectedConfig && (
                <div className={styles.configHintBanner}>
                  ⚠ Please select a configuration to continue
                </div>
              )}
              <select
                className={styles.panelSelect}
                value={selectedConfig}
                onChange={(e) => onConfigChange(e.target.value)}
              >
                {preview.configs.map((c) => (
                  <option key={c} value={c}>
                    {c}
                  </option>
                ))}
              </select>
            </div>
          )}

          {/* Auto-ingest toggle */}
          <div className={styles.panelSection}>
            <label
              className={styles.autoIngestLabel}
              style={{
                cursor: isDownloading ? "not-allowed" : "pointer",
                opacity: isDownloading ? 0.5 : 1,
              }}
            >
              <input
                type="checkbox"
                checked={autoIngest}
                onChange={(e) => onAutoIngestChange(e.target.checked)}
                disabled={isDownloading}
              />
              Auto-ingest after download
            </label>
            <p className={styles.panelHint}>
              Automatically index this dataset in Qdrant for RAG retrieval
            </p>
          </div>

          {/* Ingest options */}
          {showIngestOptions && hasTextColumns && (
            <div className={styles.panelField}>
              <label className={styles.panelFieldLabel}>
                Text Columns to Embed
              </label>
              <MultiSelect
                id={`text-cols-${preview.full_dataset_id.replace(/\//g, "-")}`}
                options={textColumnOptions}
                selected={autoIngestTextCols}
                onChange={onAutoIngestTextColsChange}
              />
              <p className={styles.panelFieldHint}>
                Select columns containing text for semantic search
              </p>
            </div>
          )}

          {showIngestOptions && (
            <div className={styles.panelField}>
              <label className={styles.panelFieldLabel}>
                Row Limit (optional)
              </label>
              <input
                className={styles.panelInput}
                type="text"
                placeholder="Full dataset"
                value={rowLimitInput}
                onChange={(e) => onRowLimitChange(e.target.value)}
              />
              <p className={styles.panelFieldHint}>
                Limit rows for testing (e.g., 500)
              </p>
            </div>
          )}
        </div>
      )}

      {/* Config required hint */}
      {hasConfigs && !selectedConfig && !expanded && !isDownloading && (
        <div className={styles.configHintBanner}>
          ⚠ Select a configuration in the expand panel to continue
        </div>
      )}
    </div>
  );
}
