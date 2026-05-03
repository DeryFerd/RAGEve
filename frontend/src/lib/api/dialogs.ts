// Dialogs API client — replaces the old /agents endpoints.
// Backend: GET/POST/PUT/DELETE /dialogs/

import { apiFetch } from "./client";
import type {
  DialogCreate,
  DialogListResponse,
  DialogResponse,
  DialogUpdate,
} from "@/lib/types";

/**
 * List all dialogs, optionally filtered by tenant.
 */
export async function listDialogs(params?: {
  tenant_id?: string;
  limit?: number;
  offset?: number;
}): Promise<DialogListResponse> {
  const qs = new URLSearchParams();
  if (params?.tenant_id) qs.set("tenant_id", params.tenant_id);
  if (params?.limit != null) qs.set("limit", String(params.limit));
  if (params?.offset != null) qs.set("offset", String(params.offset));
  const query = qs.toString();
  return apiFetch<DialogListResponse>(`/dialogs/${query ? `?${query}` : ""}`);
}

/**
 * Create a new dialog.
 */
export async function createDialog(
  payload: DialogCreate,
): Promise<DialogResponse> {
  return apiFetch<DialogResponse>("/dialogs/", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

/**
 * Get a single dialog by ID.
 */
export async function getDialog(dialogId: string): Promise<DialogResponse> {
  return apiFetch<DialogResponse>(`/dialogs/${dialogId}`);
}

/**
 * Update a dialog (partial update).
 */
export async function updateDialog(
  dialogId: string,
  payload: DialogUpdate,
): Promise<DialogResponse> {
  return apiFetch<DialogResponse>(`/dialogs/${dialogId}`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

/**
 * Delete a dialog. Returns void on 204.
 */
export async function deleteDialog(dialogId: string): Promise<void> {
  return apiFetch<void>(`/dialogs/${dialogId}`, { method: "DELETE" });
}
