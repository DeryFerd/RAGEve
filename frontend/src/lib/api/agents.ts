// Dialog-based Agents API adapter.
// This adapter translates between the old Agent* types and the new Dialog* endpoints.
// Backend: GET/POST/PUT/DELETE /dialogs/

import { apiFetch } from "./client";
import { getMe } from "./auth";
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

// TODO: Consider caching the user profile to avoid repeated fetches
let cachedUserId: string | null = null;

async function getUserId(): Promise<string | null> {
  if (cachedUserId) return cachedUserId;
  try {
    const user = await getMe();
    cachedUserId = user.user_id;
    return user.user_id;
  } catch {
    return null;
  }
}

// ── Adapter helpers ─────────────────────────────────────────────────────────────

function asString(value: unknown, fallback = ""): string {
  return typeof value === "string" ? value : fallback;
}

function asNumber(value: unknown, fallback: number): number {
  return typeof value === "number" ? value : fallback;
}

function dialogToAgent(dialog: DialogResponse): AgentResponse {
  // Extract embedding model from meta_data_filter if stored
  const meta = dialog.meta_data_filter || {};
  const promptConfig = dialog.prompt_config || {};
  const llmSetting = dialog.llm_setting || {};
  return {
    agent_id: dialog.id,
    name: dialog.name || "",
    description: dialog.description || "",
    config: {
      system_prompt: asString(promptConfig.system),
      dataset_id:
        Array.isArray(dialog.kb_ids) && dialog.kb_ids.length > 0
          ? dialog.kb_ids[0]
          : "",
      embedding_model: asString(meta.embedding_model),
      chat_model: dialog.llm_id,
      temperature: asNumber(llmSetting.temperature, 0.7),
      top_k: dialog.top_k ?? 5,
    },
    created_at: dialog.create_time
      ? new Date(dialog.create_time * 1000).toISOString()
      : new Date().toISOString(),
    updated_at: dialog.update_time
      ? new Date(dialog.update_time * 1000).toISOString()
      : new Date().toISOString(),
  };
}

function agentCreateToDialogCreate(payload: AgentCreate): DialogCreate {
  // Note: tenant_id will be set by the caller using the actual user ID
  // The DialogCreate type requires tenant_id, but we'll use a placeholder
  // that gets replaced before the API call
  return {
    tenant_id: "", // Will be filled by createAgent
    name: payload.name,
    description: payload.description || null,
    language: "English",
    llm_id: payload.config.chat_model,
    llm_setting: { temperature: payload.config.temperature },
    prompt_type: "simple",
    prompt_config: { system: payload.config.system_prompt },
    kb_ids: [payload.config.dataset_id],
    meta_data_filter: { embedding_model: payload.config.embedding_model },
    similarity_threshold: 0.2,
    vector_similarity_weight: 0.3,
    top_n: 6,
    top_k: payload.config.top_k,
    do_refer: "1",
    rerank_id: "",
    status: "1",
  };
}

function agentUpdateToDialogUpdate(
  agentId: string,
  payload: AgentUpdate,
): DialogUpdate {
  const update: DialogUpdate = {};
  if (payload.name !== undefined) update.name = payload.name;
  if (payload.description !== undefined)
    update.description = payload.description;
  if (payload.config) {
    const cfg = payload.config;
    if (cfg.chat_model !== undefined) update.llm_id = cfg.chat_model;
    if (cfg.temperature !== undefined)
      update.llm_setting = { temperature: cfg.temperature };
    if (cfg.system_prompt !== undefined)
      update.prompt_config = { system: cfg.system_prompt };
    if (cfg.dataset_id !== undefined) update.kb_ids = [cfg.dataset_id];
    if (cfg.embedding_model !== undefined)
      update.meta_data_filter = { embedding_model: cfg.embedding_model };
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
export async function createAgent(
  payload: AgentCreate,
): Promise<AgentResponse> {
  const tenantId = await getUserId();
  if (!tenantId) {
    throw new Error("Not authenticated. Please log in again.");
  }
  const dialogCreate = agentCreateToDialogCreate(payload);
  // Inject the actual tenant ID from the logged-in user
  dialogCreate.tenant_id = tenantId;
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
  payload: AgentUpdate,
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
