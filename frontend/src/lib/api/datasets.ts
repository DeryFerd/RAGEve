import { apiFetch } from "./client";
import type {
  DatasetInfo,
  DatasetListResponse,
  HuggingFaceRegisterResponse,
  IngestRequest,
  ProcessedFileResponse,
  CollectionDeleteResponse,
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
  UploadProgressHandlers,
  KbTaskResponse,
  KnowledgebaseResponse,
  KbDocumentResponse,
} from "@/lib/types";

// Import knowledgebases API functions
import {
  listKnowledgebases,
  uploadFilesToKnowledgebase,
  deleteKnowledgebase,
  getKnowledgebase,
  listDocuments,
} from "./knowledgebases";

// ── Core knowledge base operations (adapted to legacy Dataset* types) ─────────────

/**
 * List all knowledge bases. Returns DatasetListResponse for compatibility.
 * Note: chunks_count and vector_size are not available from the new API and are set to 0.
 */
export async function listDatasets(): Promise<DatasetListResponse> {
  const res = await listKnowledgebases();
  const datasets: DatasetInfo[] = res.knowledgebases.map(
    (kb): DatasetInfo => ({
      dataset_id: kb.id,
      name: kb.name,
      collection: kb.id,
      chunks_count: 0,
      vector_size: 0,
      status: "unknown",
    }),
  );
  return { datasets, total: res.total };
}

/**
 * Upload files to a knowledge base (non-streaming).
 */
export async function uploadFiles(
  kbId: string,
  files: File[],
  ingestOptions?: IngestRequest,
): Promise<{ dataset_id: string; files: ProcessedFileResponse[] }> {
  const options = {
    parser_id: ingestOptions?.force_profile || undefined,
    chunk_size: ingestOptions?.chunk_size,
    chunk_overlap: ingestOptions?.chunk_overlap,
  };
  await uploadFilesToKnowledgebase(kbId, files, options);
  // Ingestion happens in background; detailed results not immediately available.
  return { dataset_id: kbId, files: [] };
}

/**
 * Upload files with streaming progress via task polling.
 */
export async function uploadFilesStreaming(
  kbId: string,
  files: File[],
  handlers: UploadProgressHandlers,
  ingestOptions?: IngestRequest,
  signal?: AbortSignal,
): Promise<void> {
  const options = {
    parser_id: ingestOptions?.force_profile || undefined,
    chunk_size: ingestOptions?.chunk_size,
    chunk_overlap: ingestOptions?.chunk_overlap,
  };
  const uploadResults = await uploadFilesToKnowledgebase(kbId, files, options);
  const taskIds = uploadResults.map((r) => r.task_id);
  const totalFiles = files.length;
  const fileMap = new Map<string, { filename: string; index: number }>();
  uploadResults.forEach((r, idx) =>
    fileMap.set(r.task_id, { filename: r.filename, index: idx }),
  );

  let completedCount = 0;
  const completedTasks = new Set<string>();

  while (completedCount < taskIds.length) {
    if (signal?.aborted) {
      throw new DOMException("Upload aborted", "AbortError");
    }

    for (const taskId of taskIds) {
      if (completedTasks.has(taskId)) continue;

      try {
        const task = await apiFetch<KbTaskResponse>(
          `/knowledgebases/tasks/${taskId}`,
        );
        const fileInfo = fileMap.get(taskId)!;
        handlers.onStatus({
          event: "status",
          stage: task.progress >= 100 ? "completed" : "processing",
          message: task.progress_msg,
          progress: task.progress,
          dataset_id: kbId,
          file: fileInfo.filename,
          file_index: fileInfo.index + 1,
          file_total: totalFiles,
          chunks_done: task.progress,
          chunks_total: 100,
        });

        if (task.progress >= 100) {
          completedCount++;
          completedTasks.add(taskId);
          handlers.onFileDone?.({
            event: "file_done",
            stage: "completed",
            message: task.progress_msg,
            progress: 100,
            dataset_id: kbId,
            file: fileInfo.filename,
            file_index: fileInfo.index + 1,
            file_total: totalFiles,
            result: {} as ProcessedFileResponse,
          });
        }
      } catch (err) {
        handlers.onError?.({
          event: "error",
          stage: "failed",
          message: err instanceof Error ? err.message : String(err),
          progress: 0,
          dataset_id: kbId,
        });
        return;
      }
    }

    await new Promise((resolve) => setTimeout(resolve, 1000));
  }

  handlers.onDone({
    event: "done",
    stage: "completed",
    message: `Uploaded ${totalFiles} file(s)`,
    progress: 100,
    dataset_id: kbId,
    files: [],
  });
}

/**
 * Get dataset info (adapted).
 */
export async function getDatasetInfo(kbId: string): Promise<DatasetInfo> {
  return {
    dataset_id: kbId,
    name: kbId,
    collection: kbId,
    chunks_count: 0,
    vector_size: 0,
    status: "unknown",
  };
}

/**
 * Delete a knowledge base.
 */
export async function deleteDataset(
  kbId: string,
): Promise<CollectionDeleteResponse> {
  await deleteKnowledgebase(kbId);
  return {
    dataset_id: kbId,
    deleted: true,
    message: `Dataset '${kbId}' deleted.`,
  };
}

/**
 * Get full details for a single knowledge base.
 * Wraps getKnowledgebase() from knowledgebases.ts.
 */
export async function getDatasetDetail(
  kbId: string,
): Promise<KnowledgebaseResponse> {
  return getKnowledgebase(kbId);
}

/**
 * List all documents for a specific knowledge base.
 * Wraps listDocuments() from knowledgebases.ts.
 */
export async function listDocumentsForDataset(
  kbId: string,
): Promise<KbDocumentResponse[]> {
  const res = await listDocuments({ kb_id: kbId });
  return res;
}

// ── HuggingFace operations (unchanged) ───────────────────────────────────────────

export async function getHFInstructions(
  datasetId: string,
): Promise<HuggingFaceInstructionsResponse> {
  return apiFetch<HuggingFaceInstructionsResponse>(
    `/datasets/hf/instructions/${datasetId}`,
  );
}

export async function previewHFDataset(
  datasetId: string,
): Promise<HuggingFacePreviewResponse> {
  return apiFetch<HuggingFacePreviewResponse>(
    `/datasets/hf/preview/${encodeURIComponent(datasetId)}`,
  );
}

export async function getHFStatusTexts(
  datasetId: string,
): Promise<HuggingFaceStatusTextsResponse> {
  return apiFetch<HuggingFaceStatusTextsResponse>(
    `/datasets/hf/status-texts/${encodeURIComponent(datasetId)}`,
  );
}

export async function discoverHFDatasets(): Promise<HuggingFaceDiscoveryResponse> {
  return apiFetch<HuggingFaceDiscoveryResponse>("/datasets/hf/discover");
}

/** Fetch ingestion status (is_ingested) for all local datasets in one call. */
export async function getHFStatus(): Promise<HuggingFaceStatusResponse> {
  return apiFetch<HuggingFaceStatusResponse>("/datasets/hf/status");
}

/** Search HuggingFace Hub for datasets matching a query string. */
export interface HFDatasetSearchResult {
  id: string;
  downloads: number | null;
  likes: number | null;
  tags: string[];
  description: string;
}

export async function searchHFDatasets(
  query: string,
): Promise<HFDatasetSearchResult[]> {
  const params = new URLSearchParams({ q: query });
  return apiFetch<HFDatasetSearchResult[]>(`/datasets/hf/search?${params}`);
}

export async function downloadHFDataset(
  payload: HuggingFaceDownloadRequest,
): Promise<HuggingFaceDownloadResponse> {
  return apiFetch<HuggingFaceDownloadResponse>("/datasets/hf/download", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

// ── HF ingest (background) ──────────────────────────────────────────────────────

/** Submit a HuggingFace dataset ingest as a background task. Returns immediately. */
export async function submitHFIngest(
  datasetId: string,
  payload?: HFIngestRequest,
): Promise<HFIngestSubmitResponse> {
  return apiFetch<HFIngestSubmitResponse>(
    `/datasets/hf/${encodeURIComponent(datasetId)}/ingest`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload || {}),
    },
  );
}

/** Poll the status of a background HF ingest task. */
export async function getHFIngestStatus(
  ingestId: string,
): Promise<HFIngestStatusResponse> {
  return apiFetch<HFIngestStatusResponse>(
    `/datasets/hf/ingest/${ingestId}/status`,
  );
}

/** Cancel a running or queued HF ingest. */
export async function cancelHFIngest(
  ingestId: string,
): Promise<{ ingest_id: string; status: string; message: string }> {
  return apiFetch(`/datasets/hf/ingest/${ingestId}/cancel`, {
    method: "POST",
  });
}

/**
 * @deprecated Use `submitHFIngest` + polling `getHFIngestStatus` instead.
 * This fires a synchronous request that blocks the server for the full ingest duration.
 */
export async function ingestHFDataset(
  datasetId: string,
  payload?: HFIngestRequest,
): Promise<HFIngestResponse> {
  return apiFetch<HFIngestResponse>(
    `/datasets/hf/${encodeURIComponent(datasetId)}/ingest`,
    {
      method: "POST",
      body: JSON.stringify(payload || {}),
    },
  );
}

export async function getHFDownloadStatus(
  datasetId: string,
): Promise<HuggingFaceDownloadStatusResponse> {
  return apiFetch<HuggingFaceDownloadStatusResponse>(
    `/datasets/hf/download/${datasetId}/status`,
  );
}

export async function cancelHFDownload(
  datasetId: string,
): Promise<HuggingFaceDownloadResponse> {
  return apiFetch<HuggingFaceDownloadResponse>(
    `/datasets/hf/download/${datasetId}/cancel`,
    {
      method: "POST",
    },
  );
}

export async function registerHFDataset(
  payload: HuggingFaceRegisterRequest,
): Promise<HuggingFaceRegisterResponse> {
  return apiFetch<HuggingFaceRegisterResponse>("/datasets/hf/register", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export interface HFIngestRequest {
  split?: string;
  text_columns?: string[];
  metadata_columns?: string[];
  row_limit?: number;
  batch_size?: number;
  chunk_overlap?: number;
  max_tokens_per_chunk?: number;
  /** Force re-ingestion even if the dataset is already in Qdrant. */
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
