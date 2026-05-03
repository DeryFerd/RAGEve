// Conversations API client — replaces the old /chat/sessions endpoints.
// Backend: GET/POST/PUT/DELETE /conversations/

import { apiFetch } from "./client";
import type {
  AppendMessageRequest,
  AppendMessageResponse,
  ConversationCreate,
  ConversationListResponse,
  ConversationResponse,
  ConversationUpdate,
  SourceChunk,
} from "@/lib/types";

const BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// ── Conversation CRUD ─────────────────────────────────────────────────────────

/**
 * Create a new conversation for a dialog.
 */
export async function createConversation(
  payload: ConversationCreate,
): Promise<ConversationResponse> {
  return apiFetch<ConversationResponse>("/conversations/", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

/**
 * List conversations, optionally filtered by dialog_id or user_id.
 */
export async function listConversations(params?: {
  dialog_id?: string;
  user_id?: string;
  limit?: number;
  offset?: number;
}): Promise<ConversationListResponse> {
  const qs = new URLSearchParams();
  if (params?.dialog_id) qs.set("dialog_id", params.dialog_id);
  if (params?.user_id) qs.set("user_id", params.user_id);
  if (params?.limit != null) qs.set("limit", String(params.limit));
  if (params?.offset != null) qs.set("offset", String(params.offset));
  const query = qs.toString();
  return apiFetch<ConversationListResponse>(
    `/conversations/${query ? `?${query}` : ""}`,
  );
}

/**
 * Get a conversation by ID including all messages.
 */
export async function getConversation(
  conversationId: string,
): Promise<ConversationResponse> {
  return apiFetch<ConversationResponse>(`/conversations/${conversationId}`);
}

/**
 * Update conversation metadata (name, reference).
 */
export async function updateConversation(
  conversationId: string,
  payload: ConversationUpdate,
): Promise<ConversationResponse> {
  return apiFetch<ConversationResponse>(`/conversations/${conversationId}`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

/**
 * Delete a conversation. Returns void on 204.
 */
export async function deleteConversation(
  conversationId: string,
): Promise<void> {
  return apiFetch<void>(`/conversations/${conversationId}`, {
    method: "DELETE",
  });
}

// ── Messages ──────────────────────────────────────────────────────────────────

/**
 * Append a single message to a conversation.
 */
export async function appendMessage(
  conversationId: string,
  payload: AppendMessageRequest,
): Promise<AppendMessageResponse> {
  return apiFetch<AppendMessageResponse>(
    `/conversations/${conversationId}/messages`,
    {
      method: "POST",
      body: JSON.stringify(payload),
    },
  );
}

// ── Streaming chat ────────────────────────────────────────────────────────────

export type ConversationStreamHandler = {
  onChunk: (content: string) => void;
  onSources: (
    sources: SourceChunk[],
    rerankerModel?: string | null,
    messageId?: string,
  ) => void;
  onError: (error: string) => void;
};

/**
 * Stream a RAG chat turn for a conversation.
 *
 * All parameters are passed as query strings because the backend endpoint
 * (`POST /conversations/{id}/chat/stream`) uses Query params, not a JSON body.
 */
export async function conversationChatStream(
  conversationId: string,
  params: {
    question: string;
    top_k?: number;
    temperature?: number;
    use_hybrid?: boolean;
    use_reranker?: boolean;
    reranker_model?: string | null;
    score_threshold?: number;
  },
  handlers: ConversationStreamHandler,
  signal: AbortSignal,
): Promise<void> {
  const qs = new URLSearchParams();
  qs.set("question", params.question);
  if (params.top_k != null) qs.set("top_k", String(params.top_k));
  if (params.temperature != null)
    qs.set("temperature", String(params.temperature));
  if (params.use_hybrid != null)
    qs.set("use_hybrid", String(params.use_hybrid));
  if (params.use_reranker != null)
    qs.set("use_reranker", String(params.use_reranker));
  if (params.reranker_model) qs.set("reranker_model", params.reranker_model);
  if (params.score_threshold != null)
    qs.set("score_threshold", String(params.score_threshold));

  const apiKey = process.env.NEXT_PUBLIC_API_KEY || "";
  const res = await fetch(
    `${BASE}/conversations/${conversationId}/chat/stream?${qs}`,
    {
      method: "POST",
      signal,
      headers: apiKey ? { "X-API-Key": apiKey } : undefined,
    },
  );

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(
      (err as { detail?: string }).detail ||
        `Conversation chat stream failed: ${res.status}`,
    );
  }

  if (!res.body) throw new Error("Response body is null");

  const reader = res.body.getReader();
  const decoder = new TextDecoder();

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    const chunk = decoder.decode(value, { stream: true });
    const lines = chunk.split("\n");

    for (const line of lines) {
      if (!line.trim()) continue;
      try {
        const event = JSON.parse(line) as {
          event: string;
          content?: string;
          sources?: SourceChunk[];
          reranker_model?: string | null;
          message_id?: string;
          error?: string;
        };
        if (event.event === "chunk") {
          handlers.onChunk(event.content ?? "");
        } else if (event.event === "end") {
          handlers.onSources(
            event.sources ?? [],
            event.reranker_model ?? null,
            event.message_id,
          );
        } else if (event.event === "error") {
          handlers.onError(event.error ?? "Unknown error");
        }
      } catch {
        // Skip malformed lines
      }
    }
  }
}
