"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { searchHFDatasets } from "@/lib/api/datasets";
import styles from "./HuggingFacePage.module.css";

// ── Types ───────────────────────────────────────────────────────────────────

interface HFDatasetSearchResult {
  id: string;
  downloads: number | null;
  likes: number | null;
  tags: string[];
  description: string;
}

// ── Helpers ─────────────────────────────────────────────────────────────────

const fmtCount = (n: number | null | undefined): string | null => {
  if (n == null) return null;
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}k`;
  return n.toLocaleString();
};

const SUGGESTION_CHIPS = [
  { id: "squad", label: "squad", desc: "QA dataset" },
  { id: "imdb", label: "imdb", desc: "Movie reviews" },
  { id: "wikitext", label: "wikitext", desc: "Wikipedia text" },
  { id: "openai/webgpt_comparisons", label: "webgpt", desc: "GPT answers" },
];

// ── Props ───────────────────────────────────────────────────────────────────

interface HubSearchProps {
  datasetId: string;
  onDatasetIdChange: (id: string) => void;
  onChipClick: (id: string) => void;
}

// ── Component ───────────────────────────────────────────────────────────────

export function HubSearch({ datasetId, onDatasetIdChange, onChipClick }: HubSearchProps) {
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<HFDatasetSearchResult[]>([]);
  const [searchLoading, setSearchLoading] = useState(false);
  const [searchError, setSearchError] = useState<string | null>(null);
  const [dropdownOpen, setDropdownOpen] = useState(false);

  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Debounced Hub search
  const fetchHubSearch = useCallback(async (q: string) => {
    if (q.trim().length < 2) {
      setSearchResults([]);
      setDropdownOpen(false);
      return;
    }
    setSearchLoading(true);
    setSearchError(null);
    try {
      const results = await searchHFDatasets(q.trim());
      setSearchResults(results);
      setDropdownOpen(results.length > 0);
    } catch (err) {
      console.error("Hub search error:", err);
      setSearchError("Search failed. Try again.");
      setSearchResults([]);
    } finally {
      setSearchLoading(false);
    }
  }, []);

  const handleSearchInput = (value: string) => {
    setSearchQuery(value);
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => void fetchHubSearch(value), 400);
  };

  const handleSelectResult = (result: HFDatasetSearchResult) => {
    onDatasetIdChange(result.id);
    setSearchQuery(result.id);
    setDropdownOpen(false);
  };

  // Close dropdown on outside click
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      const target = e.target as HTMLElement;
      if (!target.closest("[data-search-dropdown]")) {
        setDropdownOpen(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  // Sync external datasetId to search query (keeps input in sync with chips/clear)
  useEffect(() => {
    setSearchQuery(datasetId);
  }, [datasetId]);

  return (
    <div className={styles.pageHeader}>
      {/* Search input */}
      <div className={styles.searchSection} style={{ position: "relative" }}>
        <div className={styles.searchRow}>
          <svg
            className={styles.searchIcon}
            width="14"
            height="14"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
          >
            <circle cx="11" cy="11" r="8" />
            <path d="M21 21l-4.35-4.35" />
          </svg>
          <input
            className={styles.mainInput}
            type="text"
            value={searchQuery}
            onChange={(e) => handleSearchInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                if (searchResults.length > 0) {
                  handleSelectResult(searchResults[0]);
                } else {
                  onDatasetIdChange(searchQuery.trim());
                }
                setDropdownOpen(false);
              }
            }}
            placeholder="Search HuggingFace Hub or enter dataset ID (e.g. squad, imdb)"
            autoComplete="off"
            spellCheck={false}
            data-search-dropdown="true"
            style={{ paddingLeft: 32 }}
          />

          {/* Lookup / loading indicator */}
          {searchLoading ? (
            <div className={styles.lookupRow}>
              <span className={styles.lookupSpinner} />
              Searching…
            </div>
          ) : searchQuery.length >= 2 && searchResults.length === 0 && !searchError ? (
            <div className={styles.lookupRow} style={{ color: "var(--text-muted)" }}>No results</div>
          ) : null}

          {/* Clear button */}
          {searchQuery && (
            <button
              className={styles.searchClear}
              onClick={() => {
                setSearchQuery("");
                setSearchResults([]);
                setDropdownOpen(false);
                onDatasetIdChange("");
              }}
              type="button"
              title="Clear"
            >
              ✕
            </button>
          )}
        </div>

        {/* Hub search dropdown */}
        {dropdownOpen && (
          <div className={styles.searchDropdown} data-search-dropdown="true">
            {searchLoading && searchResults.length === 0 ? (
              <div className={styles.searchDropdownLoading}>
                {[1, 2, 3].map((i) => (
                  <div key={i} className={styles.skeletonSearchResult}>
                    <div className={styles.skeletonSearchIcon} />
                    <div className={styles.skeletonSearchInfo}>
                      <div className={styles.skeletonSearchName} />
                      <div className={styles.skeletonSearchMeta} />
                      <div className={styles.skeletonSearchDesc} />
                    </div>
                  </div>
                ))}
              </div>
            ) : searchResults.length === 0 && searchQuery.length >= 2 ? (
              <div className={styles.searchNoResults}>
                No datasets found for &ldquo;{searchQuery}&rdquo;
              </div>
            ) : (
              searchResults.map((result) => (
                <div
                  key={result.id}
                  className={styles.searchResultItem}
                  onClick={() => handleSelectResult(result)}
                >
                  <div className={styles.searchResultIcon}>⬡</div>
                  <div className={styles.searchResultInfo}>
                    <div className={styles.searchResultName}>{result.id}</div>
                    <div className={styles.searchResultMeta}>
                      {result.downloads != null && <span>↓ {fmtCount(result.downloads)}</span>}
                      {result.likes != null && <span>♥ {fmtCount(result.likes)}</span>}
                    </div>
                    {result.description && (
                      <div className={styles.searchResultDesc}>{result.description}</div>
                    )}
                  </div>
                </div>
              ))
            )}
          </div>
        )}
      </div>
      
      {/* Suggestion chips — always visible */}
      <div className={styles.chipsRow}>
        <span className={styles.chipsLabel}>Popular:</span>
        {SUGGESTION_CHIPS.map((chip) => (
          <button
            key={chip.id}
            className={`${styles.chip} ${datasetId === chip.id ? styles.chipActive : ""}`}
            onClick={() => onChipClick(chip.id)}
            title={chip.desc}
            type="button"
          >
            {chip.label}
          </button>
        ))}
      </div>
    </div>
  );
}
