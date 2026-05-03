import { apiFetch } from "./client";
import type {
  ChatRequest,
  ChatResponse,
  ChatSession,
  ChatSessionWithMessages,
  ChatSessionListResponse,
  CreateSessionRequest,
  FeedbackPayload,
  SSEEvent,
  SourceChunk,
} from "@/lib/types";

const BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

function messageFieldAsString(
  record: Record<string, unknown>,
  field: string,
  fallback: string,
): string {
  const value = record[field];
  return typeof value === "string" ? value : fallback;
}

function messageFieldAsNumberOrNull(
  record: Record<string, unknown>,
  field: string,
): number | null {
  const value = record[field];
  return typeof value === "number" ? value : null;
}

function messageSources(record: Record<string, unknown>): SourceChunk[] | null {
  return Array.isArray(record.sources)
    ? (record.sources as SourceChunk[])
    : null;
}

// ── Conversation CRUD (adapted to legacy session types) ───────────────────────────

/**
 * Create a new conversation for a dialog.
 */
export async function createSession(
  payload: CreateSessionRequest,
): Promise<ChatSession> {
  const convPayload = {
    dialog_id: payload.agent_id,
    name: payload.title,
  } as const;
  const conv = await apiFetch<ConversationResponse>("/conversations/", {
    method: "POST",
    body: JSON.stringify(convPayload),
  });
  return {
    session_id: conv.id,
    agent_id: conv.dialog_id,
    title: conv.name || "",
    message_count: conv.message.length,
    agent_config_snapshot: {
      system_prompt: "",
      dataset_id: "",
      embedding_model: "",
      chat_model: "",
      temperature: 0.7,
      top_k: 5,
    },
    created_at: conv.create_time
      ? new Date(conv.create_time * 1000).toISOString()
      : new Date().toISOString(),
    updated_at: conv.update_time
      ? new Date(conv.update_time * 1000).toISOString()
      : new Date().toISOString(),
  };
}

/**
 * List sessions (conversations), optionally filtered by agent_id.
 */
export async function listSessions(params?: {
  agent_id?: string;
  limit?: number;
  offset?: number;
}): Promise<ChatSessionListResponse> {
  const qs = new URLSearchParams();
  if (params?.agent_id) qs.set("dialog_id", params.agent_id);
  if (params?.limit != null) qs.set("limit", String(params.limit));
  if (params?.offset != null) qs.set("offset", String(params.offset));
  const query = qs.toString();
  const res = await apiFetch<ConversationListResponse>(
    `/conversations/${query ? `?${query}` : ""}`,
  );
  const sessions: ChatSession[] = res.conversations.map((conv) => ({
    session_id: conv.id,
    agent_id: conv.dialog_id,
    title: conv.name || "",
    message_count: conv.message.length,
    agent_config_snapshot: {
      system_prompt: "",
      dataset_id: "",
      embedding_model: "",
      chat_model: "",
      temperature: 0.7,
      top_k: 5,
    },
    created_at: conv.create_time
      ? new Date(conv.create_time * 1000).toISOString()
      : new Date().toISOString(),
    updated_at: conv.update_time
      ? new Date(conv.update_time * 1000).toISOString()
      : new Date().toISOString(),
  }));
  return {
    sessions,
    total: res.total,
    limit: res.limit,
    offset: res.offset,
  };
}

/**
 * Get a session with its messages.
 */
export async function getSessionWithMessages(
  sessionId: string,
): Promise<ChatSessionWithMessages> {
  const conv = await apiFetch<ConversationResponse>(
    `/conversations/${sessionId}`,
  );
  const messages = conv.message.map((msg) => {
    const record = msg as Record<string, unknown>;
    const fallbackId = `msg-${Math.random().toString(36).slice(2, 11)}`;
    const role: "user" | "assistant" =
      record.role === "assistant" ? "assistant" : "user";

    return {
      message_id: messageFieldAsString(record, "message_id", fallbackId),
      session_id: conv.id,
      role,
      content: messageFieldAsString(record, "content", ""),
      token_count: messageFieldAsNumberOrNull(record, "token_count"),
      sources: messageSources(record),
      feedback: null,
      created_at: new Date().toISOString(),
    };
  });
  return {
    session: {
      session_id: conv.id,
      agent_id: conv.dialog_id,
      title: conv.name || "",
      message_count: messages.length,
      agent_config_snapshot: {
        system_prompt: "",
        dataset_id: "",
        embedding_model: "",
        chat_model: "",
        temperature: 0.7,
        top_k: 5,
      },
      created_at: conv.create_time
        ? new Date(conv.create_time * 1000).toISOString()
        : new Date().toISOString(),
      updated_at: conv.update_time
        ? new Date(conv.update_time * 1000).toISOString()
        : new Date().toISOString(),
    },
    messages,
  };
}

/**
 * Delete a session.
 */
export async function deleteSession(sessionId: string): Promise<void> {
  await apiFetch<void>(`/conversations/${sessionId}`, { method: "DELETE" });
}

// ── Streaming with session history ─────────────────────────────────────────────

export type SessionStreamHandler = {
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
 * Uses POST /conversations/{id}/chat/stream with query parameters.
 * Backend returns NDJSON events.
 */
export async function chatSessionStreaming(
  conversationId: string,
  payload: ChatRequest,
  handlers: SessionStreamHandler,
  signal: AbortSignal,
): Promise<void> {
  const qs = new URLSearchParams();
  qs.set("question", payload.question);
  if (payload.top_k != null) qs.set("top_k", String(payload.top_k));
  if (payload.temperature != null)
    qs.set("temperature", String(payload.temperature));
  if (payload.use_hybrid != null)
    qs.set("use_hybrid", String(payload.use_hybrid));
  if (payload.use_reranker != null)
    qs.set("use_reranker", String(payload.use_reranker));
  if (payload.reranker_model) qs.set("reranker_model", payload.reranker_model);
  if (payload.score_threshold != null)
    qs.set("score_threshold", String(payload.score_threshold));

  const apiKey = process.env.NEXT_PUBLIC_API_KEY || "";
  const headers: HeadersInit = {
    ...(apiKey ? { "X-API-Key": apiKey } : {}),
  };

  const res = await fetch(
    `${BASE}/conversations/${conversationId}/chat/stream?${qs}`,
    { method: "POST", signal, headers },
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

// ── Feedback ────────────────────────────────────────────────────────────────────

export async function submitFeedback(
  messageId: string,
  payload: FeedbackPayload,
): Promise<void> {
  try {
    await fetch(`${BASE}/chat/messages/${messageId}/feedback`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
  } catch (err) {
    console.warn("Feedback not supported:", err);
  }
}

// ── Non-streaming chat (stateless) ─────────────────────────────────────────────

export async function chatNonStreaming(
  dialogId: string,
  payload: ChatRequest,
): Promise<ChatResponse> {
  const response = await fetch(`${BASE}/chat/${dialogId}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ...payload, stream: false }),
  });

  if (!response.ok) {
    const err = await response
      .json()
      .catch(() => ({ detail: response.statusText }));
    throw new Error(err.detail || `Chat failed: ${response.status}`);
  }

  return response.json();
}

export type StreamHandler = {
  onChunk: (content: string) => void;
  onSources: (sources: SourceChunk[], rerankerModel?: string | null) => void;
  onError: (error: string) => void;
};

/**
 * Streaming chat (stateless) using /chat/{dialog_id}/stream.
 * Backend returns Server-Sent Events (SSE) format.
 */
export async function chatStreaming(
  dialogId: string,
  payload: ChatRequest,
  handlers: StreamHandler,
  signal: AbortSignal,
): Promise<void> {
  const apiKey = process.env.NEXT_PUBLIC_API_KEY || "";
  const response = await fetch(`${BASE}/chat/${dialogId}/stream`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(apiKey ? { "X-API-Key": apiKey } : {}),
    },
    body: JSON.stringify({ ...payload, stream: true }),
    signal,
  });

  if (!response.ok) {
    const err = await response
      .json()
      .catch(() => ({ detail: response.statusText }));
    throw new Error(err.detail || `Chat failed: ${response.status}`);
  }

  if (!response.body) throw new Error("Response body is null");

  const reader = response.body.getReader();
  const decoder = new TextDecoder();

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    const chunk = decoder.decode(value, { stream: true });
    const lines = chunk.split("\n");

    for (const line of lines) {
      if (!line.trim()) continue;
      try {
        const lineStr = line.trim();
        if (!lineStr.startsWith("data:")) continue;
        const jsonStr = lineStr.slice(5).trim();
        const event = JSON.parse(jsonStr) as SSEEvent;
        if (event.event === "chunk") {
          handlers.onChunk(event.content);
        } else if (event.event === "end") {
          handlers.onSources(event.sources || [], event.reranker_model ?? null);
        } else if (event.event === "error") {
          handlers.onError(event.error);
        }
      } catch {
        // Skip malformed lines
      }
    }
  }
}

// ── Types for new API responses (imported for internal use) ─────────────────────

import type {
  ConversationResponse,
  ConversationListResponse,
} from "@/lib/types";
