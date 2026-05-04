"use client";

import { useState } from "react";
import { Badge } from "@/components/ui/Badge";
import type { HuggingFacePreviewResponse } from "@/lib/types";
import styles from "./HuggingFacePage.module.css";

// ── Helpers ─────────────────────────────────────────────────────────────────

const fmtCount = (n: number | null | undefined): string | null => {
  if (n == null) return null;
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}k`;
  return n.toLocaleString();
};

// ── Props ───────────────────────────────────────────────────────────────────

interface DatasetPreviewProps {
  preview: HuggingFacePreviewResponse;
  previewLoading: boolean;
  previewError: string | null;
}

// ── Component ────────────────────────────────────────────────────────────────

export function DatasetPreview({
  preview,
  previewLoading,
  previewError,
}: DatasetPreviewProps) {
  type TabKey = "description" | "tags" | "readme" | "columns";
  const [detailsOpen, setDetailsOpen] = useState(false);
  const [activeTab, setActiveTab] = useState<TabKey>("description");

  if (previewLoading) {
    return (
      <div className={styles.skeletonPreviewCard}>
        <div className={styles.skeletonPreviewHero}>
          <div className={styles.skeletonIcon} />
          <div className={styles.skeletonPreviewInfo}>
            <div className={styles.skeletonTitle} />
            <div className={styles.skeletonBadges}>
              <div className={styles.skeletonBadge} />
              <div className={styles.skeletonBadge} />
              <div className={styles.skeletonBadge} />
            </div>
          </div>
        </div>
        <div className={styles.skeletonStats}>
          <div className={styles.skeletonStat} />
          <div className={styles.skeletonStat} />
          <div className={styles.skeletonStat} />
        </div>
        <div className={styles.skeletonDesc} />
      </div>
    );
  }

  if (previewError) {
    return (
      <div className={styles.previewCard} style={{ padding: "12px 16px" }}>
        <p style={{ fontSize: 12, color: "var(--error)" }}>{previewError}</p>
      </div>
    );
  }

  if (!preview) return null;

  // Which tabs have content?
  const hasDescription = !!preview.description;
  const hasTags = !!(preview.tags && preview.tags.length > 0);
  const hasReadme = !!preview.readme_html;
  const hasColumns = Object.keys(preview.columns).length > 0;

  const tabs: { key: TabKey; label: string; count?: number }[] = [];
  if (hasDescription) tabs.push({ key: "description", label: "Description" });
  if (hasTags)
    tabs.push({ key: "tags", label: "Tags", count: preview.tags?.length });
  if (hasReadme) tabs.push({ key: "readme", label: "README" });
  if (hasColumns)
    tabs.push({
      key: "columns",
      label: "Columns",
      count: Object.keys(preview.columns).length,
    });

  // Set active tab to first available if current is hidden
  const activeTabValid = tabs.some((t) => t.key === activeTab);
  const effectiveTab: TabKey = activeTabValid
    ? activeTab
    : (tabs[0]?.key ?? "description");

  const sourceClass =
    preview.source === "hf-hub"
      ? styles.sourceBadgeBlue
      : preview.source === "datasets-server"
        ? styles.sourceBadgeOrange
        : styles.sourceBadgeGray;

  const sourceLabel =
    preview.source === "hf-hub"
      ? "◆ HF Hub"
      : preview.source === "datasets-server"
        ? "◈ datasets-server"
        : "◎ Hub API";

  const needsTruncate = preview.description && preview.description.length > 180;

  return (
    <div className={styles.previewCard}>
      {/* ── Compact Hero ─────────────────────────────────────────────── */}
      <div className={styles.previewHero}>
        <div className={styles.previewIcon}>⬡</div>
        <div className={styles.previewHeroMeta}>
          <div className={styles.previewDatasetName}>
            {preview.full_dataset_id}
          </div>
          <div className={styles.previewBadgeRow}>
            {preview.estimated_size_human && (
              <Badge variant="accent">{preview.estimated_size_human}</Badge>
            )}
            <Badge variant="default">
              {preview.splits.length} split
              {preview.splits.length !== 1 ? "s" : ""}
            </Badge>
            {preview.license && (
              <Badge variant="default">{preview.license}</Badge>
            )}
            <span className={`${styles.previewSourceBadge} ${sourceClass}`}>
              {sourceLabel}
            </span>
          </div>
        </div>
      </div>

      {/* ── Stats row ───────────────────────────────────────────────── */}
      <div className={styles.previewStats}>
        {preview.language && preview.language.length > 0 && (
          <div className={styles.previewStat}>
            <span className={styles.statLabel}>Lang</span>
            <span className={styles.statValue}>
              {preview.language.slice(0, 3).join(", ")}
            </span>
          </div>
        )}
        {preview.downloads && (
          <div className={styles.previewStat}>
            <span className={styles.statLabel}>↓</span>
            <span className={styles.statValue}>
              {fmtCount(preview.downloads)}
            </span>
          </div>
        )}
        {preview.likes && (
          <div className={styles.previewStat}>
            <span className={styles.statLabel}>♥</span>
            <span className={styles.statValue}>{fmtCount(preview.likes)}</span>
          </div>
        )}
        {preview.tags && preview.tags.length > 0 && (
          <div className={styles.previewStat}>
            <span className={styles.statLabel}>Tags</span>
            <span className={styles.statValue}>
              {preview.tags.slice(0, 3).join(", ")}
            </span>
          </div>
        )}
      </div>

      {/* ── Description (compact) ─────────────────────────────────────── */}
      {preview.description && (
        <div className={styles.previewSection}>
          <p
            className={`${styles.description} ${
              !detailsOpen && needsTruncate ? styles.descriptionClamped : ""
            }`}
          >
            {preview.description}
          </p>
          {needsTruncate && (
            <button
              className={styles.descToggle}
              onClick={() => setDetailsOpen((v) => !v)}
              type="button"
            >
              {detailsOpen ? "▲ Show less" : "▼ Show more"}
            </button>
          )}
        </div>
      )}

      {/* ── Details toggle ────────────────────────────────────────────── */}
      {(hasTags || hasReadme || hasColumns) && (
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "flex-end",
            padding: "4px 16px 8px",
          }}
        >
          <button
            className={styles.previewDetailsBtn}
            onClick={() => setDetailsOpen((v) => !v)}
            type="button"
            aria-expanded={detailsOpen}
          >
            {detailsOpen ? "▲ Hide details" : "▼ Show details"}
          </button>
        </div>
      )}

      {/* ── Expanded tabbed section ──────────────────────────────────── */}
      {detailsOpen && (
        <>
          {/* Tab strip */}
          {tabs.length > 0 && (
            <div className={styles.previewTabStrip} role="tablist">
              {tabs.map((tab) => (
                <button
                  key={tab.key}
                  className={`${styles.previewTab} ${
                    effectiveTab === tab.key ? styles.previewTabActive : ""
                  }`}
                  onClick={() => setActiveTab(tab.key)}
                  type="button"
                  role="tab"
                  aria-selected={effectiveTab === tab.key}
                >
                  {tab.label}
                  {tab.count != null && (
                    <span className={styles.previewTabBadge}>{tab.count}</span>
                  )}
                </button>
              ))}
            </div>
          )}

          {/* Tab content */}
          <div
            className={styles.previewSection}
            style={{ borderBottom: "none" }}
          >
            {/* Description tab */}
            {effectiveTab === "description" && preview.description && (
              <p className={styles.description}>{preview.description}</p>
            )}

            {/* Tags tab */}
            {effectiveTab === "tags" && preview.tags && (
              <div className={styles.tags}>
                {preview.tags.map((tag) => (
                  <span key={tag} className={styles.tag}>
                    {tag}
                  </span>
                ))}
              </div>
            )}

            {/* README tab */}
            {effectiveTab === "readme" && preview.readme_html && (
              <div
                className={styles.readmeContent}
                dangerouslySetInnerHTML={{ __html: preview.readme_html }}
              />
            )}

            {/* Columns tab */}
            {effectiveTab === "columns" && (
              <div>
                <div className={styles.columnsRow}>
                  {Object.entries(preview.columns)
                    .slice(0, 12)
                    .map(([name, type]) => (
                      <span
                        key={name}
                        className={`${styles.col} ${type === "string" ? styles.colText : ""}`}
                      >
                        {name}
                        <span className={styles.colType}>{type}</span>
                      </span>
                    ))}
                  {Object.keys(preview.columns).length > 12 && (
                    <span className={styles.colMore}>
                      +{Object.keys(preview.columns).length - 12} more
                    </span>
                  )}
                </div>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}
