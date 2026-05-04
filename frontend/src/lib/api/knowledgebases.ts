// Knowledgebases API client — replaces the old /datasets endpoints.
// Backend: GET/POST/PUT/DELETE /knowledgebases/

import { apiFetch } from "./client";
import type {
  KnowledgebaseCreate,
  KnowledgebaseListResponse,
  KnowledgebaseResponse,
  KnowledgebaseUpdate,
  KbDocumentResponse,
  KbFileUploadResponse,
  KbTaskResponse,
} from "@/lib/types";

const BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// ── Knowledgebase CRUD ────────────────────────────────────────────────────────

/**
 * List knowledge bases, optionally filtered by tenant.
 */
export async function listKnowledgebases(params?: {
  tenant_id?: string;
  limit?: number;
  offset?: number;
}): Promise<KnowledgebaseListResponse> {
  const qs = new URLSearchParams();
  if (params?.tenant_id) qs.set("tenant_id", params.tenant_id);
  if (params?.limit != null) qs.set("limit", String(params.limit));
  if (params?.offset != null) qs.set("offset", String(params.offset));
  const query = qs.toString();
  return apiFetch<KnowledgebaseListResponse>(
    `/knowledgebases/${query ? `?${query}` : ""}`,
  );
}

/**
 * Create a new knowledge base.
 */
export async function createKnowledgebase(
  payload: KnowledgebaseCreate,
): Promise<KnowledgebaseResponse> {
  return apiFetch<KnowledgebaseResponse>("/knowledgebases/", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

/**
 * Get a single knowledge base by ID.
 */
export async function getKnowledgebase(
  kbId: string,
): Promise<KnowledgebaseResponse> {
  return apiFetch<KnowledgebaseResponse>(`/knowledgebases/${kbId}`);
}

/**
 * Update a knowledge base (partial update).
 */
export async function updateKnowledgebase(
  kbId: string,
  payload: KnowledgebaseUpdate,
): Promise<KnowledgebaseResponse> {
  return apiFetch<KnowledgebaseResponse>(`/knowledgebases/${kbId}`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

/**
 * Delete a knowledge base and all its documents, files, tasks, and Qdrant collection.
 * Returns void on 204.
 */
export async function deleteKnowledgebase(kbId: string): Promise<void> {
  return apiFetch<void>(`/knowledgebases/${kbId}`, { method: "DELETE" });
}

// ── File uploads ──────────────────────────────────────────────────────────────

/**
 * Upload files to a knowledge base.
 * The backend creates File + Document + Task records and queues background ingestion.
 * Returns one FileUploadResponse per uploaded file.
 */
export async function uploadFilesToKnowledgebase(
  kbId: string,
  files: File[],
  options?: {
    parser_id?: string;
    chunk_size?: number;
    chunk_overlap?: number;
  },
): Promise<KbFileUploadResponse[]> {
  const form = new FormData();
  for (const file of files) {
    form.append("files", file);
  }

  const qs = new URLSearchParams();
  if (options?.parser_id) qs.set("parser_id", options.parser_id);
  if (options?.chunk_size != null)
    qs.set("chunk_size", String(options.chunk_size));
  if (options?.chunk_overlap != null)
    qs.set("chunk_overlap", String(options.chunk_overlap));
  const query = qs.toString();

  const url = `${BASE}/knowledgebases/${kbId}/upload${query ? `?${query}` : ""}`;
  const response = await fetch(url, {
    method: "POST",
    body: form,
    credentials: "include", // Include auth cookie
  });

  if (!response.ok) {
    if (response.status === 401) {
      const returnUrl = typeof window !== "undefined" ? window.location.pathname + window.location.search : "/";
      if (typeof window !== "undefined") {
        window.location.href = `/login?returnUrl=${encodeURIComponent(returnUrl)}`;
      }
    }
    const err = await response
      .json()
      .catch(() => ({ detail: response.statusText }));
    throw new Error(
      (err as { detail?: string }).detail ||
        `Upload failed: ${response.status}`,
    );
  }

  return response.json() as Promise<KbFileUploadResponse[]>;
}

// ── Documents ──────────────────────────────────────────────────────────────────

/**
 * List documents in a knowledge base.
 */
export async function listDocuments(params?: {
  kb_id?: string;
  limit?: number;
  offset?: number;
}): Promise<KbDocumentResponse[]> {
  const qs = new URLSearchParams();
  if (params?.kb_id) qs.set("kb_id", params.kb_id);
  if (params?.limit != null) qs.set("limit", String(params.limit));
  if (params?.offset != null) qs.set("offset", String(params.offset));
  const query = qs.toString();
  return apiFetch<KbDocumentResponse[]>(
    `/knowledgebases/documents${query ? `?${query}` : ""}`,
  );
}

/**
 * Get a document by ID.
 */
export async function getDocument(docId: string): Promise<KbDocumentResponse> {
  return apiFetch<KbDocumentResponse>(`/knowledgebases/documents/${docId}`);
}

/**
 * List all tasks for a document.
 */
export async function listDocumentTasks(
  docId: string,
): Promise<KbTaskResponse[]> {
  return apiFetch<KbTaskResponse[]>(`/knowledgebases/documents/${docId}/tasks`);
}

// ── Tasks ─────────────────────────────────────────────────────────────────────

/**
 * Get a task by ID.
 */
export async function getTask(taskId: string): Promise<KbTaskResponse> {
  return apiFetch<KbTaskResponse>(`/knowledgebases/tasks/${taskId}`);
}
