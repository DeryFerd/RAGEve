"use client";

import { useEffect } from "react";
import { useDatasetsStore } from "@/stores/useDatasetsStore";
import { useToastStore } from "@/stores/useToastStore";
import { listDatasets, deleteDataset } from "@/lib/api/datasets";
import { Button } from "@/components/ui/Button";
import { DatasetCard } from "@/components/datasets/DatasetCard";
import { DatasetCreateWizard } from "@/components/datasets/DatasetCreateWizard";
import styles from "./DatasetsPage.module.css";

export default function DatasetsPage() {
  const {
    datasets,
    setDatasets,
    removeDataset,
    selectedDetailId,
    toggleDetail,
    documentsByDataset,
    documentsLoading,
    isCreateWizardOpen,
    openCreateWizard,
    closeCreateWizard,
  } = useDatasetsStore();

  const { addToast } = useToastStore();

  // Fetch datasets on mount
  useEffect(() => {
    listDatasets()
      .then((res) => setDatasets(res.datasets))
      .catch((e) => addToast(`Failed to load datasets: ${e.message}`, "error"));
  }, [setDatasets, addToast]);

  const handleDelete = async (id: string) => {
    try {
      await deleteDataset(id);
      removeDataset(id);
      addToast("Dataset deleted", "info");
    } catch (err) {
      addToast(
        `Delete failed: ${err instanceof Error ? err.message : String(err)}`,
        "error"
      );
    }
  };

  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <h1 className={styles.title}>Datasets</h1>
        <Button onClick={openCreateWizard}>Create New Dataset</Button>
      </div>

      {datasets.length === 0 ? (
        <div className={styles.emptyState}>
          No datasets yet. Create one to get started.
        </div>
      ) : (
        <div className={styles.grid}>
          {datasets.map((ds) => (
            <DatasetCard
              key={ds.dataset_id}
              dataset={ds}
              expanded={selectedDetailId === ds.dataset_id}
              documents={documentsByDataset[ds.dataset_id] || []}
              documentsLoading={!!documentsLoading[ds.dataset_id]}
              onClick={() => toggleDetail(ds.dataset_id)}
              onDelete={() => handleDelete(ds.dataset_id)}
            />
          ))}
        </div>
      )}

      <DatasetCreateWizard
        open={isCreateWizardOpen}
        onClose={closeCreateWizard}
      />
    </div>
  );
}
