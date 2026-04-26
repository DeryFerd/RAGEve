/**
 * Chat API client.
 *
 * Session-aware functions now delegate to the new /conversations endpoints.
 * Legacy direct-agent streaming (chatStreaming / chatNonStreaming) still targets
 * /chat/{dialog_id}/stream which remains valid in the new schema.
 */

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
  ConversationResponse,
  ConversationCreate,
} from "@/lib/types";
import {
  createConversation,
  listConversations,
  getConversation,
  deleteConversation,
  conversationChatStream,
} from "./conversations";

const BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// ── Adapter helpers ────────────────────────────────────────────────────────────

/**
 * Convert a ConversationResponse to the legacy ChatSession shape so existing
 * store code (useChatStore) continues to work without changes.
 */
function convToSession(conv: ConversationResponse): ChatSession {
  return {
    session_id: conv.id,
    agent_id: conv.dialog_id,
    title: conv.name ?? "New conversation",
    message_count: conv.message?.length ?? 0,
    agent_config_snapshot: {
      system_prompt: "",
      dataset_id: "",
      embedding_model: "",
      chat_model: "",
      temperature: 0.7,
      top_k: 5,
    },
    created_at: conv.create_date ?? "",
    updated_at: conv.update_date ?? "",
  };
}

// ── Sessions (now backed by /conversations) ────────────────────────────────────

/**
 * Create a new conversation/session for a dialog (agent).
 */
export async function createSession(
  payload: CreateSessionRequest
): Promise<ChatSession> {
  const convPayload: ConversationCreate = {
    dialog_id: payload.agent_id,
    name: payload.title ?? "New conversation",
  };
  const conv = await createConversation(convPayload);
  return convToSession(conv);
}

/**
 * List sessions for a dialog/agent.
 */
export async function listSessions(params?: {
  agent_id?: string;
  limit?: number;
  offset?: number;
}): Promise<ChatSessionListResponse> {
  const res = await listConversations({
    dialog_id: params?.agent_id,
    limit: params?.limit,
    offset: params?.offset,
  });
  return {
    sessions: res.conversations.map(convToSession),
    total: res.total,
    limit: res.limit,
    offset: res.offset,
  };
}

/**
 * Get a conversation with its messages.
 * Adapts to the legacy ChatSessionWithMessages shape.
 */
export async function getSessionWithMessages(
  sessionId: string
): Promise<ChatSessionWithMessages> {
  const conv = await getConversation(sessionId);
  const session = convToSession(conv);

  // Map embedded ConversationMessage[] to ChatMessageStored[]
  const messages = (conv.message ?? []).map((m, index) => ({
    message_id: `${conv.id}-msg-${index}`,
    session_id: conv.id,
    role: m.role as "user" | "assistant",
    content: m.content,
    token_count: (m.token_count as number | null | undefined) ?? null,
    sources: (m.sources as import("@/lib/types").SourceChunk[] | null | undefined) ?? null,
    feedback: null,
    created_at: conv.create_date ?? "",
  }));

  return { session, messages };
}

/**
 * Delete a conversation/session.
 */
export async function deleteSession(sessionId: string): Promise<void> {
  return deleteConversation(sessionId);
}

// ── Streaming with conversation history ───────────────────────────────────────

export type SessionStreamHandler = {
  onChunk: (content: string) => void;
  onSources: (
    sources: SourceChunk[],
    rerankerModel?: string | null,
    messageId?: string
  ) => void;
  onError: (error: string) => void;
};

/**
 * Stream a chat turn for a session (conversation).
 * Now targets POST /conversations/{id}/chat/stream with query params.
 */
export async function chatSessionStreaming(
  sessionId: string,
  payload: ChatRequest,
  handlers: SessionStreamHandler,
  signal: AbortSignal
): Promise<void> {
  return conversationChatStream(
    sessionId,
    {
      question: payload.question,
      top_k: payload.top_k,
      temperature: payload.temperature,
      use_hybrid: payload.use_hybrid,
      use_reranker: payload.use_reranker,
      reranker_model: payload.reranker_model,
      score_threshold: payload.score_threshold,
    },
    handlers,
    signal
  );
}

// ── Feedback ──────────────────────────────────────────────────────────────────

export async function submitFeedback(
  messageId: string,
  payload: FeedbackPayload
): Promise<void> {
  const res = await fetch(`${BASE}/chat/messages/${messageId}/feedback`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(`Submit feedback failed: ${res.status}`);
}

// ── Legacy direct-agent streaming ─────────────────────────────────────────────
// These target /chat/{dialog_id}/[stream] which still works in the new schema.

export async function chatNonStreaming(
  agentId: string,
  payload: ChatRequest
): Promise<ChatResponse> {
  const response = await fetch(`${BASE}/chat/${agentId}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ...payload, stream: false }),
  });

  if (!response.ok) {
    const err = await response.json().catch(() => ({
      detail: response.statusText,
    }));
    throw new Error(
      (err as { detail?: string }).detail ||
        `Chat failed: ${response.status}`
    );
  }

  return response.json() as Promise<ChatResponse>;
}

export type StreamHandler = {
  onChunk: (content: string) => void;
  onSources: (sources: SourceChunk[], rerankerModel?: string | null) => void;
  onError: (error: string) => void;
};

export async function chatStreaming(
  agentId: string,
  payload: ChatRequest,
  handlers: StreamHandler,
  signal: AbortSignal
): Promise<void> {
  const response = await fetch(`${BASE}/chat/${agentId}/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ...payload, stream: true }),
    signal,
  });

  if (!response.ok) {
    const err = await response.json().catch(() => ({
      detail: response.statusText,
    }));
    throw new Error(
      (err as { detail?: string }).detail ||
        `Chat failed: ${response.status}`
    );
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
        const event: SSEEvent = JSON.parse(line);
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
