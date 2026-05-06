"use client";

export const dynamic = "force-dynamic";

import { useCallback, useEffect, useRef } from "react";
import { useChatStore } from "@/stores/useChatStore";
import { useAgentsStore } from "@/stores/useAgentsStore";
import { useModelStore } from "@/stores/useModelStore";
import { listDialogs } from "@/lib/api/dialogs";
import { getRerankers } from "@/lib/api/rerank";
import { useChatStream } from "@/components/chat/useChatStream";
import { ChatMessage } from "@/components/chat/ChatMessage";
import { ChatInput } from "@/components/chat/ChatInput";
import { AgentCard } from "@/components/chat/AgentCard";
import { SessionPanel } from "@/components/chat/SessionPanel";
import { useToastStore } from "@/stores/useToastStore";
import { getSessionWithMessages, createSession } from "@/lib/api/chat";
import { Button } from "@/components/ui/Button";
import type { DialogResponse } from "@/lib/types";
import styles from "./ChatPage.module.css";

let msgCounter = 0;

export default function ChatPage() {
  const {
    messages,
    streamingText,
    selectedAgentId,
    currentSession,
    setSelectedAgentId,
    appendMessage,
    loadSessionMessages,
    setRerankerModels,
    addSession,
    isStreaming,
  } = useChatStore();
  const { agents, setAgents } = useAgentsStore();
  const { addToast } = useToastStore();
  const { send, stop } = useChatStream();
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const prevMsgLen = useRef(0);

  // Load agents (dialogs) on mount
  useEffect(() => {
    listDialogs()
      .then((res) => setAgents(res.dialogs as DialogResponse[]))
      .catch((err) =>
        addToast(`Failed to load agents: ${err.message}`, "error"),
      );
  }, [setAgents, addToast]);

  // Refresh Ollama and reranker model lists on mount.
  useEffect(() => {
    getRerankers()
      .then((res) => setRerankerModels(res.rerankers))
      .catch(() => {
        // Non-fatal — reranking just won't be available
      });
  }, [setRerankerModels]);

  // Pull the Ollama model list fresh on mount.
  useEffect(() => {
    const base = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    fetch(`${base}/ollama/models`)
      .then((r) => r.json())
      .then((data) => {
        useModelStore.setState({
          availableModels: data.models ?? [],
          modelsLoaded: data.has_models ?? false,
        });
      })
      .catch(() => {
        // Non-fatal
      });
  }, []);

  // Auto-scroll to bottom
  useEffect(() => {
    const totalLen = messages.length + (streamingText ? 1 : 0);
    if (totalLen !== prevMsgLen.current) {
      messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
      prevMsgLen.current = totalLen;
    }
  }, [messages, streamingText]);

  // Load messages when a session is selected
  const handleSessionSelected = useCallback(
    (sessionId: string) => {
      getSessionWithMessages(sessionId)
        .then((res) => {
          loadSessionMessages(res.messages);
        })
        .catch((err) =>
          addToast(`Failed to load messages: ${err.message}`, "error"),
        );
    },
    [loadSessionMessages, addToast],
  );

  const handleSend = useCallback(
    async (
      question: string,
      opts: {
        temperature: number;
        topK: number;
        useReranker: boolean;
        rerankerModel: string | null;
        useHybrid: boolean;
      },
    ) => {
      // If no session, create one on-the-fly before sending
      if (!currentSession) {
        try {
          const session = await createSession({ agent_id: selectedAgentId! });
          addSession(session);
          addToast("New conversation started", "success");
        } catch (err) {
          addToast(
            `Failed to create session: ${err instanceof Error ? err.message : String(err)}`,
            "error",
          );
          return;
        }
      }

      // Add user message immediately to the local store
      const userMsgId = `msg-${++msgCounter}`;
      appendMessage({
        id: userMsgId,
        role: "user",
        content: question,
        timestamp: Date.now(),
      });
      send(question, {
        temperature: opts.temperature,
        topK: opts.topK,
        useReranker: opts.useReranker,
        rerankerModel: opts.useReranker ? opts.rerankerModel : null,
        useHybrid: opts.useHybrid,
      });
    },
    [
      currentSession,
      selectedAgentId,
      appendMessage,
      send,
      addSession,
      addToast,
    ],
  );

  // When the selected agent changes, reset messages and auto-create a session
  const handleAgentChange = useCallback(
    async (agentId: string) => {
      setSelectedAgentId(agentId);
      try {
        const session = await createSession({ agent_id: agentId });
        addSession(session);
        addToast("New conversation started", "success");
      } catch (err) {
        addToast(
          `Failed to create session: ${err instanceof Error ? err.message : String(err)}`,
          "error",
        );
      }
    },
    [setSelectedAgentId, addSession, addToast],
  );

  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <div className={styles.headerLeft}>
          {selectedAgentId ? (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setSelectedAgentId(null)}
              className={styles.backButton}
            >
              <svg
                width="16"
                height="16"
                viewBox="0 0 16 16"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
              >
                <path d="M10 4l-4 4 4 4" />
              </svg>
              Back
            </Button>
          ) : null}
          <h1 className={styles.title}>Chat</h1>
        </div>
      </div>

      {!selectedAgentId ? (
        agents.length === 0 ? (
          <div className={styles.emptyState}>
            <svg
              className={styles.emptyIcon}
              viewBox="0 0 48 48"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.5"
            >
              <path d="M6 8h36v28H30l-6 6V36H6V8z" />
              <path d="M14 18h20M14 24h12" />
            </svg>
            <div className={styles.emptyTitle}>No agents yet</div>
            <div className={styles.emptyDesc}>
              Create an agent in the <strong>Agents</strong> page to start
              chatting.
            </div>
          </div>
        ) : (
          <div className={styles.agentGrid}>
            {agents.map((dialog) => (
              <AgentCard
                key={dialog.id}
                agent={dialog}
                onClick={() => handleAgentChange(dialog.id)}
              />
            ))}
          </div>
        )
      ) : (
        <div className={styles.layout}>
          <SessionPanel
            agentId={selectedAgentId}
            onSessionSelected={handleSessionSelected}
          />

          <div className={styles.chatArea}>
            {!currentSession ? (
              <div className={styles.emptyState}>
                <svg
                  className={styles.emptyIcon}
                  viewBox="0 0 48 48"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="1.5"
                >
                  <path d="M6 8h36v28H30l-6 6V36H6V8z" />
                  <path d="M14 18h20M14 24h12" />
                </svg>
                <div className={styles.emptyTitle}>Start a conversation</div>
                <div className={styles.emptyDesc}>
                  Click &ldquo;+ New&rdquo; in the sidebar to start a new
                  conversation with this agent.
                </div>
              </div>
            ) : messages.length === 0 && !streamingText ? (
              <div className={styles.emptyState}>
                <svg
                  className={styles.emptyIcon}
                  viewBox="0 0 48 48"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="1.5"
                >
                  <path d="M6 8h36v28H30l-6 6V36H6V8z" />
                  <path d="M14 18h20M14 24h12" />
                </svg>
                <div className={styles.emptyTitle}>Ask a question</div>
                <div className={styles.emptyDesc}>
                  The model will retrieve relevant context from your datasets
                  and answer.
                </div>
              </div>
            ) : (
              <div className={styles.messages}>
                {messages.map((msg) => (
                  <ChatMessage
                    key={msg.id}
                    message={msg}
                    sources={msg.sources || []}
                  />
                ))}
                {streamingText && (
                  <ChatMessage
                    message={{
                      id: "streaming",
                      role: "assistant",
                      content: streamingText,
                      timestamp: Date.now(),
                    }}
                    isStreaming
                  />
                )}
                <div ref={messagesEndRef} />
              </div>
            )}

            <ChatInput
              onSend={handleSend}
              onStop={stop}
              disabled={isStreaming}
            />
          </div>
        </div>
      )}
    </div>
  );
}
