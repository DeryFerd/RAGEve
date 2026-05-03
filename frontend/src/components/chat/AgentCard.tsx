"use client";

import type { AgentResponse } from "@/lib/types";
import { Button } from "@/components/ui/Button";
import styles from "./AgentCard.module.css";

interface AgentCardProps {
  agent: AgentResponse;
  onClick: () => void;
}

export function AgentCard({ agent, onClick }: AgentCardProps) {
  return (
    <div className={styles.card} onClick={onClick} role="button" tabIndex={0}>
      <div className={styles.cardTop}>
        <div>
          <div className={styles.cardTitle}>{agent.name}</div>
          {agent.description && (
            <div className={styles.cardDesc}>{agent.description}</div>
          )}
        </div>
      </div>

      <div className={styles.cardBody}>
        <div className={styles.field}>
          <span className={styles.fieldLabel}>Dataset</span>
          <span className={styles.fieldValue}>{agent.config.dataset_id}</span>
        </div>
        <div className={styles.field}>
          <span className={styles.fieldLabel}>Embed Model</span>
          <span className={styles.fieldValue}>
            {agent.config.embedding_model}
          </span>
        </div>
        <div className={styles.field}>
          <span className={styles.fieldLabel}>Chat Model</span>
          <span className={styles.fieldValue}>{agent.config.chat_model}</span>
        </div>
        <div className={styles.field}>
          <span className={styles.fieldLabel}>Temperature</span>
          <span className={styles.fieldValue}>{agent.config.temperature}</span>
        </div>
        <div className={styles.field}>
          <span className={styles.fieldLabel}>Top-K</span>
          <span className={styles.fieldValue}>{agent.config.top_k}</span>
        </div>
      </div>

      <div className={styles.cardAction}>
        <Button variant="primary" size="sm" fullWidth>
          Start Chat
        </Button>
      </div>
    </div>
  );
}
