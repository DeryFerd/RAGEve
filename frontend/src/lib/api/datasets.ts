/**
 * @deprecated The backend renamed /datasets to /knowledgebases.
 * This shim maps the legacy DatasetInfo / DatasetListResponse shapes to the new
 * KnowledgebaseResponse for components that have not yet been migrated.
 *
 * Import from "@/lib/api/knowledgebases" directly for new code.
 *
 * HuggingFace endpoints (/datasets/hf/*) remain on the old /hf_ingest and
 * /hf_download backend routes and are NOT changed here.
 */

import { apiFetch } from "./client";
import type {
  DatasetInfo,
  DatasetListResponse,
  HuggingFaceRegisterResponse,
  IngestRequest,
  IngestResponse,
  ProcessedFileResponse,
  CollectionDeleteResponse,
  DiscoveredDataset,
  HFIngestSubmitResponse,
  HFIngestStatusResponse,
  HuggingFaceDiscoveryResponse,
  HuggingFaceInstructionsResponse,
  HuggingFaceRegisterRequest,
  HuggingFaceDownloadRequest,
  HuggingFaceDownloadResponse,
  HuggingFaceDownloadStatusResponse,
  HuggingFacePreviewResponse,
  HuggingFaceStatusResponse,
  HuggingFaceStatusTextsResponse,
  UploadProgressEvent,
  UploadProgressHandlers,
  KnowledgebaseResponse,
} from "@/lib/types";
import {
  listKnowledgebases,
  deleteKnowledgebase,
  getKnowledgebase,
  uploadFilesToKnowledgebase,
} from "./knowledgebases";

// ── Adapter helpers ────────────────────────────────────────────────────────────

/**
 * Map a KnowledgebaseResponse to the legacy DatasetInfo shape.
 */
function kbToDatasetInfo(kb: KnowledgebaseResponse): DatasetInfo {
  return {
    dataset_id: kb.id,
    collection: kb.id,
    chunks_count: 0,        // Not available on KB response — poll Qdrant separately if needed
    vector_size: 0,
    status: "available",
  };
}

// ── Core dataset operations (legacy surface) ──────────────────────────────────

export async function listDatasets(): Promise<DatasetListResponse> {
  const res = await listKnowledgebases();
  return {
    datasets: res.knowledgebases.map(kbToDatasetInfo),
    total: res.total,
  };
}

/**
 * Upload files via the new /knowledgebases/{kb_id}/upload endpoint.
 *
 * NOTE: The new endpoint uses a background-task model (returns immediately with
 * task IDs). It does NOT support streaming progress events.  Components that
 * relied on the streaming upload should migrate to `uploadFilesToKnowledgebase`
 * from "@/lib/api/knowledgebases".
 */
export async function uploadFiles(
  datasetId: string,
  files: File[],
  _ingestOptions?: IngestRequest
): Promise<{ dataset_id: string; files: ProcessedFileResponse[] }> {
  const uploaded = await uploadFilesToKnowledgebase(datasetId, files);

  // The new endpoint returns task records, not quality reports.
  // Return a minimal shape compatible with the old ProcessedFileResponse.
  const processedFiles: ProcessedFileResponse[] = uploaded.map((u) => ({
    dataset_id: datasetId,
    filename: u.filename,
    extension: u.file_type,
    chars: 0,
    chunks: 0,
    collection: datasetId,
    document_analysis: { types: {}, alpha_ratio: 0, characters: 0 },
    sample_chunk_analysis: [],
    quality_report: {
      quality_score: 0,
      selected_profile: "general",
      profile_reason: "pending",
      signals: {
        alpha_ratio: 0,
        ocr_noise_ratio: 0,
        broken_line_ratio: 0,
        header_footer_ratio: 0,
        table_density: 0,
        avg_sentence_length: 0,
        language_script_changes: 0,
        repeated_word_ratio: 0,
        code_delimiter_ratio: 0,
        issue_tags: [],
      },
    },
    layout_summary: null,
    extraction: {
      extractor: "background",
      message: `Queued as task ${u.task_id}`,
    },
  }));

  return { dataset_id: datasetId, files: processedFiles };
}

/**
 * Streaming upload shim.
 *
 * The new knowledgebases endpoint does NOT support streaming progress events.
 * This shim immediately invokes onDone after a plain upload so existing
 * progress-bar components still reach their terminal state.
 */
export async function uploadFilesStreaming(
  datasetId: string,
  files: File[],
  handlers: UploadProgressHandlers,
  _ingestOptions?: IngestRequest,
  signal?: AbortSignal
): Promise<void> {
  const base = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  // Try legacy streaming endpoint first (may still be mounted during migration).
  // If it returns 404 or 405, fall back to the new endpoint.
  try {
    const response = await fetch(`${base}/datasets/${datasetId}/upload/stream`, {
      method: "POST",
      body: (() => {
        const form = new FormData();
        for (const file of files) form.append("files", file);
        return form;
      })(),
      signal,
    });

    if (response.ok && response.body) {
      // Legacy streaming path — parse NDJSON progress events.
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() ?? "";

        for (const line of lines) {
          if (!line.trim()) continue;
          let event: UploadProgressEvent;
          try {
            event = JSON.parse(line) as UploadProgressEvent;
          } catch {
            continue;
          }
          if (event.event === "status") handlers.onStatus(event);
          else if (event.event === "file_done") handlers.onFileDone?.(event);
          else if (event.event === "done") handlers.onDone(event);
          else if (event.event === "error") handlers.onError(event);
        }
      }

      if (buffer.trim()) {
        try {
          const event = JSON.parse(buffer) as UploadProgressEvent;
          if (event.event === "status") handlers.onStatus(event);
          else if (event.event === "file_done") handlers.onFileDone?.(event);
          else if (event.event === "done") handlers.onDone(event);
          else if (event.event === "error") handlers.onError(event);
        } catch {
          // ignore
        }
      }
      return;
    }
  } catch {
    // Legacy endpoint not available — fall through to new endpoint.
  }

  // New knowledgebases endpoint (no streaming).
  handlers.onStatus({
    event: "status",
    stage: "uploading",
    message: "Uploading files...",
    progress: 10,
    dataset_id: datasetId,
  });

  try {
    const uploaded = await uploadFilesToKnowledgebase(datasetId, files);
    const processedFiles: ProcessedFileResponse[] = uploaded.map((u) => ({
      dataset_id: datasetId,
      filename: u.filename,
      extension: u.file_type,
      chars: 0,
      chunks: 0,
      collection: datasetId,
      document_analysis: { types: {}, alpha_ratio: 0, characters: 0 },
      sample_chunk_analysis: [],
      quality_report: {
        quality_score: 0,
        selected_profile: "general",
        profile_reason: "pending",
        signals: {
          alpha_ratio: 0,
          ocr_noise_ratio: 0,
          broken_line_ratio: 0,
          header_footer_ratio: 0,
          table_density: 0,
          avg_sentence_length: 0,
          language_script_changes: 0,
          repeated_word_ratio: 0,
          code_delimiter_ratio: 0,
          issue_tags: [],
        },
      },
      layout_summary: null,
      extraction: {
        extractor: "background",
        message: `Queued as task ${u.task_id}`,
      },
    }));

    handlers.onDone({
      event: "done",
      stage: "completed",
      message: `${uploaded.length} file(s) queued for ingestion`,
      progress: 100,
      dataset_id: datasetId,
      files: processedFiles,
    });
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err);
    handlers.onError({
      event: "error",
      stage: "failed",
      message: msg,
      progress: 0,
      dataset_id: datasetId,
    });
  }
}

export async function ingestDataset(
  datasetId: string,
  options?: IngestRequest
): Promise<IngestResponse> {
  // Legacy /datasets/{id}/ingest — still forwarded directly if the route exists.
  return apiFetch<IngestResponse>(`/datasets/${datasetId}/ingest`, {
    method: "POST",
    body: JSON.stringify(options || {}),
  });
}

export async function getDatasetInfo(datasetId: string): Promise<DatasetInfo> {
  const kb = await getKnowledgebase(datasetId);
  return kbToDatasetInfo(kb);
}

export async function deleteDataset(datasetId: string): Promise<CollectionDeleteResponse> {
  await deleteKnowledgebase(datasetId);
  return {
    dataset_id: datasetId,
    deleted: true,
    message: `Knowledge base '${datasetId}' deleted`,
  };
}

// ── HuggingFace endpoints ─────────────────────────────────────────────────────
// These remain on the original /datasets/hf/* routes (backend has not changed them).

export async function getHFInstructions(
  datasetId: string
): Promise<HuggingFaceInstructionsResponse> {
  return apiFetch<HuggingFaceInstructionsResponse>(
    `/datasets/hf/instructions/${datasetId}`
  );
}

export async function previewHFDataset(
  datasetId: string
): Promise<HuggingFacePreviewResponse> {
  return apiFetch<HuggingFacePreviewResponse>(
    `/datasets/hf/preview/${encodeURIComponent(datasetId)}`
  );
}

export async function getHFStatusTexts(
  datasetId: string
): Promise<HuggingFaceStatusTextsResponse> {
  return apiFetch<HuggingFaceStatusTextsResponse>(
    `/datasets/hf/status-texts/${encodeURIComponent(datasetId)}`
  );
}

export async function discoverHFDatasets(): Promise<HuggingFaceDiscoveryResponse> {
  return apiFetch<HuggingFaceDiscoveryResponse>("/datasets/hf/discover");
}

export async function getHFStatus(): Promise<HuggingFaceStatusResponse> {
  return apiFetch<HuggingFaceStatusResponse>("/datasets/hf/status");
}

export interface HFDatasetSearchResult {
  id: string;
  downloads: number | null;
  likes: number | null;
  tags: string[];
  description: string;
}

export async function searchHFDatasets(
  query: string
): Promise<HFDatasetSearchResult[]> {
  const params = new URLSearchParams({ q: query });
  return apiFetch<HFDatasetSearchResult[]>(`/datasets/hf/search?${params}`);
}

export async function downloadHFDataset(
  payload: HuggingFaceDownloadRequest
): Promise<HuggingFaceDownloadResponse> {
  return apiFetch<HuggingFaceDownloadResponse>("/datasets/hf/download", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

// ── HF ingest (background) ────────────────────────────────────────────────────

export interface HFIngestRequest {
  split?: string;
  text_columns?: string[];
  metadata_columns?: string[];
  row_limit?: number;
  batch_size?: number;
  chunk_overlap?: number;
  max_tokens_per_chunk?: number;
  force?: boolean;
}

export interface HFIngestResponse {
  dataset_id: string;
  collection: string;
  rows_processed: number;
  chunks_embedded: number;
  avg_quality_score: number;
  profiles_used: Record<string, number>;
  text_columns_used: string[];
  message: string;
}

export async function submitHFIngest(
  datasetId: string,
  payload?: HFIngestRequest
): Promise<HFIngestSubmitResponse> {
  return apiFetch<HFIngestSubmitResponse>(
    `/datasets/hf/${encodeURIComponent(datasetId)}/ingest/submit`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload || {}),
    }
  );
}

export async function getHFIngestStatus(
  ingestId: string
): Promise<HFIngestStatusResponse> {
  return apiFetch<HFIngestStatusResponse>(
    `/datasets/hf/ingest/${ingestId}/status`
  );
}

export async function cancelHFIngest(
  ingestId: string
): Promise<{ ingest_id: string; status: string; message: string }> {
  return apiFetch(`/datasets/hf/ingest/${ingestId}/cancel`, {
    method: "POST",
  });
}

/**
 * @deprecated Use `submitHFIngest` + polling `getHFIngestStatus` instead.
 */
export async function ingestHFDataset(
  datasetId: string,
  payload?: HFIngestRequest
): Promise<HFIngestResponse> {
  return apiFetch<HFIngestResponse>(
    `/datasets/hf/${encodeURIComponent(datasetId)}/ingest`,
    {
      method: "POST",
      body: JSON.stringify(payload || {}),
    }
  );
}

export async function getHFDownloadStatus(
  datasetId: string
): Promise<HuggingFaceDownloadStatusResponse> {
  return apiFetch<HuggingFaceDownloadStatusResponse>(
    `/datasets/hf/download/${datasetId}/status`
  );
}

export async function cancelHFDownload(
  datasetId: string
): Promise<HuggingFaceDownloadResponse> {
  return apiFetch<HuggingFaceDownloadResponse>(
    `/datasets/hf/download/${datasetId}/cancel`,
    { method: "POST" }
  );
}

export async function registerHFDataset(
  payload: HuggingFaceRegisterRequest
): Promise<HuggingFaceRegisterResponse> {
  return apiFetch<HuggingFaceRegisterResponse>("/datasets/hf/register", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}
