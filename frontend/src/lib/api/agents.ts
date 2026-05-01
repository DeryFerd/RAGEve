// Dialog-based Agents API adapter.
// This adapter translates between the old Agent* types and the new Dialog* endpoints.
// Backend: GET/POST/PUT/DELETE /dialogs/

import { apiFetch } from "./client";
import type {
  AgentCreate,
  AgentListResponse,
  AgentResponse,
  AgentUpdate,
  DialogCreate,
  DialogResponse,
  DialogUpdate,
  DialogListResponse,
} from "@/lib/types";

// TODO: In a real multi-tenant setup, this should be dynamically determined (e.g., from user profile)
const DEFAULT_TENANT_ID = process.env.NEXT_PUBLIC_DEFAULT_TENANT_ID || "00000000000000000000000000000000";

// ── Adapter helpers ─────────────────────────────────────────────────────────────

function dialogToAgent(dialog: DialogResponse): AgentResponse {
  // Extract embedding model from meta_data_filter if stored
  const meta = dialog.meta_data_filter as Record<string, unknown> || {};
  return {
    agent_id: dialog.id,
    name: dialog.name || "",
    description: dialog.description || null,
    config: {
      system_prompt: (dialog.prompt_config as Record<string, unknown>)?.system || "",
      dataset_id: Array.isArray(dialog.kb_ids) && dialog.kb_ids.length > 0 ? dialog.kb_ids[0] : "",
      embedding_model: (meta.embedding_model as string) || "",
      chat_model: dialog.llm_id,
      temperature: (dialog.llm_setting as Record<string, unknown>)?.temperature ?? 0.7,
      top_k: dialog.top_k,
    },
    created_at: dialog.create_time ? new Date(dialog.create_time * 1000).toISOString() : new Date().toISOString(),
    updated_at: dialog.update_time ? new Date(dialog.update_time * 1000).toISOString() : new Date().toISOString(),
  };
}

function agentCreateToDialogCreate(payload: AgentCreate): DialogCreate {
  const cfg = payload.config;
  return {
    tenant_id: DEFAULT_TENANT_ID,
    name: payload.name,
    description: payload.description || null,
    language: "English",
    llm_id: cfg.chat_model,
    llm_setting: { temperature: cfg.temperature },
    prompt_type: "simple",
    prompt_config: { system: cfg.system_prompt },
    kb_ids: [cfg.dataset_id],
    meta_data_filter: { embedding_model: cfg.embedding_model },
    similarity_threshold: 0.2,
    vector_similarity_weight: 0.3,
    top_n: 6,
    top_k: cfg.top_k,
    do_refer: "1",
    rerank_id: "",
    status: "1",
  };
}

function agentUpdateToDialogUpdate(agentId: string, payload: AgentUpdate): DialogUpdate {
  const update: any = {};
  if (payload.name !== undefined) update.name = payload.name;
  if (payload.description !== undefined) update.description = payload.description;
  if (payload.config) {
    const cfg = payload.config;
    if (cfg.chat_model !== undefined) update.llm_id = cfg.chat_model;
    if (cfg.temperature !== undefined) update.llm_setting = { temperature: cfg.temperature };
    if (cfg.system_prompt !== undefined) update.prompt_config = { system: cfg.system_prompt };
    if (cfg.dataset_id !== undefined) update.kb_ids = [cfg.dataset_id];
    if (cfg.embedding_model !== undefined) update.meta_data_filter = { embedding_model: cfg.embedding_model };
    if (cfg.top_k !== undefined) update.top_k = cfg.top_k;
  }
  return update;
}

// ── API functions ───────────────────────────────────────────────────────────────

/**
 * List all agents (dialogs).
 */
export async function listAgents(): Promise<AgentListResponse> {
  const res = await apiFetch<DialogListResponse>("/dialogs/");
  return {
    agents: res.dialogs.map(dialogToAgent),
    total: res.total,
  };
}

/**
 * Create a new agent (dialog).
 */
export async function createAgent(payload: AgentCreate): Promise<AgentResponse> {
  const dialogCreate = agentCreateToDialogCreate(payload);
  const dialog = await apiFetch<DialogResponse>("/dialogs/", {
    method: "POST",
    body: JSON.stringify(dialogCreate),
  });
  return dialogToAgent(dialog);
}

/**
 * Get a single agent by ID.
 */
export async function getAgent(agentId: string): Promise<AgentResponse> {
  const dialog = await apiFetch<DialogResponse>(`/dialogs/${agentId}`);
  return dialogToAgent(dialog);
}

/**
 * Update an agent (dialog).
 */
export async function updateAgent(
  agentId: string,
  payload: AgentUpdate
): Promise<AgentResponse> {
  const dialogUpdate = agentUpdateToDialogUpdate(agentId, payload);
  const dialog = await apiFetch<DialogResponse>(`/dialogs/${agentId}`, {
    method: "PUT",
    body: JSON.stringify(dialogUpdate),
  });
  return dialogToAgent(dialog);
}

/**
 * Delete an agent (dialog).
 */
export async function deleteAgent(agentId: string): Promise<void> {
  await apiFetch<void>(`/dialogs/${agentId}`, { method: "DELETE" });
}
