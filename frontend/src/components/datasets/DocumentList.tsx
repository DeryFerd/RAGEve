"use client";

import type { KbDocumentResponse } from "@/lib/types";
import { DocumentItem } from "./DocumentItem";
import styles from "./DocumentList.module.css";

interface DocumentListProps {
  documents: KbDocumentResponse[];
  loading: boolean;
  datasetId: string;
}

export function DocumentList({
  documents,
  loading,
  datasetId,
}: DocumentListProps) {
  if (loading) {
    return <div className={styles.message}>Loading documents...</div>;
  }

  if (documents.length === 0) {
    return (
      <div className={styles.message}>
        No documents yet. Use the upload section below to add files.
      </div>
    );
  }

  return (
    <div className={styles.list}>
      {documents.map((doc) => (
        <DocumentItem key={doc.id} document={doc} datasetId={datasetId} />
      ))}
    </div>
  );
}
