// Shared constants for HuggingFace page components

/**
 * LocalStorage key for persisting active download dataset ID across page refreshes.
 */
export const ACTIVE_DOWNLOAD_KEY = "hf_active_download_dataset_id";

/**
 * Terminal states for download/ingest status tracking.
 */
export const TERMINAL_STATES = new Set(["completed", "failed", "cancelled"]);
