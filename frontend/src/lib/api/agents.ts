/**
 * @deprecated The backend renamed /agents to /dialogs.
 * This shim maps legacy AgentResponse shapes to the new DialogResponse for
 * components that have not yet been migrated.
 *
 * Import from "@/lib/api/dialogs" directly for new code.
 */

import { apiFetch } from "./client";
import type {
  AgentCreate,
  AgentListResponse,
  AgentResponse,
  AgentUpdate,
  DialogResponse,
} from "@/lib/types";
import { listDialogs, createDialog, updateDialog, deleteDialog, getDialog } from "./dialogs";

// ── Adapter helpers ────────────────────────────────────────────────────────────

/**
 * Convert a new DialogResponse to the legacy AgentResponse shape so existing
 * components continue to work without changes.
 */
function dialogToAgent(d: DialogResponse): AgentResponse {
  const systemPrompt = d.prompt_config?.system ?? "";
  const temperature = (d.llm_setting?.temperature as number | undefined) ?? 0.7;
  const firstKb = d.kb_ids?.[0] ?? "";

  return {
    agent_id: d.id,
    name: d.name ?? "",
    description: d.description ?? "",
    config: {
      system_prompt: systemPrompt,
      dataset_id: firstKb,
      embedding_model: "",       // Tenant-level in new schema — not on dialog
      chat_model: d.llm_id,
      temperature,
      top_k: d.top_k,
    },
    created_at: d.create_date ?? "",
    updated_at: d.update_date ?? "",
  };
}

// ── Legacy exports ─────────────────────────────────────────────────────────────

export async function listAgents(): Promise<AgentListResponse> {
  const res = await listDialogs();
  return {
    agents: res.dialogs.map(dialogToAgent),
    total: res.total,
  };
}

export async function createAgent(payload: AgentCreate): Promise<AgentResponse> {
  // Map AgentCreate → DialogCreate.
  // tenant_id and created_by are required by the backend; use a placeholder
  // until the frontend obtains the real tenant from the auth context.
  const PLACEHOLDER_TENANT = "00000000000000000000000000000001";

  const dialog = await createDialog({
    tenant_id: PLACEHOLDER_TENANT,
    name: payload.name,
    description: payload.description,
    llm_id: payload.config.chat_model,
    llm_setting: {
      temperature: payload.config.temperature,
    },
    prompt_config: {
      system: payload.config.system_prompt,
    },
    kb_ids: payload.config.dataset_id ? [payload.config.dataset_id] : [],
    top_k: payload.config.top_k,
  });
  return dialogToAgent(dialog);
}

export async function getAgent(agentId: string): Promise<AgentResponse> {
  const dialog = await getDialog(agentId);
  return dialogToAgent(dialog);
}

export async function updateAgent(
  agentId: string,
  payload: AgentUpdate
): Promise<AgentResponse> {
  const updates: Parameters<typeof updateDialog>[1] = {};
  if (payload.name !== undefined) updates.name = payload.name;
  if (payload.description !== undefined) updates.description = payload.description;
  if (payload.config) {
    updates.llm_id = payload.config.chat_model;
    updates.llm_setting = { temperature: payload.config.temperature };
    updates.prompt_config = { system: payload.config.system_prompt };
    updates.kb_ids = payload.config.dataset_id ? [payload.config.dataset_id] : [];
    updates.top_k = payload.config.top_k;
  }
  const dialog = await updateDialog(agentId, updates);
  return dialogToAgent(dialog);
}

export async function deleteAgent(agentId: string): Promise<void> {
  return deleteDialog(agentId);
}
