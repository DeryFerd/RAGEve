"use client";

import type { DialogResponse } from "@/lib/types";
import { Button } from "@/components/ui/Button";
import styles from "./AgentCard.module.css";

interface AgentCardProps {
  agent: DialogResponse;
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
          <span className={styles.fieldValue}>{agent.kb_ids?.[0] || "-"}</span>
        </div>
        <div className={styles.field}>
          <span className={styles.fieldLabel}>Embed Model</span>
          <span className={styles.fieldValue}>
            {String((agent.llm_setting as Record<string, unknown>)?.embedding_model || "-")}
          </span>
        </div>
        <div className={styles.field}>
          <span className={styles.fieldLabel}>Chat Model</span>
          <span className={styles.fieldValue}>{agent.llm_id}</span>
        </div>
        <div className={styles.field}>
          <span className={styles.fieldLabel}>Temperature</span>
          <span className={styles.fieldValue}>
            {(agent.llm_setting as Record<string, unknown>)?.temperature ?? 0.7}
          </span>
        </div>
        <div className={styles.field}>
          <span className={styles.fieldLabel}>Top-K</span>
          <span className={styles.fieldValue}>{agent.top_k}</span>
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
