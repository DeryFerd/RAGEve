"use client";

import { useState, useRef } from "react";
import { Modal } from "@/components/ui/Modal";
import { Input, Textarea } from "@/components/ui/Input";
import { Button } from "@/components/ui/Button";
import { useDatasetsStore } from "@/stores/useDatasetsStore";
import { useToastStore } from "@/stores/useToastStore";
import { createKnowledgebase } from "@/lib/api/knowledgebases";
import { uploadFilesStreaming } from "@/lib/api/datasets";
import { DatasetInfo } from "@/lib/types";
import styles from "./DatasetCreateWizard.module.css";

interface DatasetCreateWizardProps {
  open: boolean;
  onClose: () => void;
}

export function DatasetCreateWizard({ open, onClose }: DatasetCreateWizardProps) {
  const {
    isCreateWizardOpen,
    createWizardStep,
    createForm,
    createWizardFiles,
    creatingDatasetId,
    createWizardSaving,
    setCreateWizardStep,
    setCreateForm,
    setCreateWizardFiles,
    setCreatingDatasetId,
    setCreateWizardSaving,
    addDataset,
    closeCreateWizard,
  } = useDatasetsStore();

  const addToast = useToastStore((s) => s.addToast);

  const [ingestProgress, setIngestProgress] = useState<{
    progress: number;
    message: string;
  }>({ progress: 0, message: "" });

  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleClose = () => {
    closeCreateWizard();
    onClose();
    setIngestProgress({ progress: 0, message: "" });
  };

  const handleStep1Next = async () => {
    if (!createForm.name.trim()) {
      addToast("Dataset name is required", "error");
      return;
    }
    try {
      const result = await createKnowledgebase({
        tenant_id: "00000000000000000000000000000000",
        name: createForm.name.trim(),
        description: createForm.description || null,
        created_by: "00000000000000000000000000000001",
      });
      setCreatingDatasetId(result.id);
      setCreateWizardStep(2);
    } catch (err) {
      addToast(
        `Failed to create dataset: ${err instanceof Error ? err.message : "Unknown error"}`,
        "error"
      );
    }
  };

  const handleStep2Next = () => {
    if (createWizardFiles.length === 0) return;
    setCreateWizardStep(3);
  };

  const handleStep2Back = () => {
    setCreateWizardStep(1);
  };

  const handleStep3Back = () => {
    setCreateWizardStep(2);
    setIngestProgress({ progress: 0, message: "" });
  };

  const handleCreateAndIngest = async () => {
    if (!creatingDatasetId) return;
    setCreateWizardSaving(true);
    setIngestProgress({ progress: 0, message: "Starting ingestion..." });

    try {
      await uploadFilesStreaming(
        creatingDatasetId,
        createWizardFiles,
        {
          onStatus: (event) => {
            setIngestProgress({
              progress: event.progress,
              message: event.message,
            });
          },
          onDone: () => {
            setIngestProgress({ progress: 100, message: "Complete" });
          },
          onError: (event) => {
            throw new Error(event.message);
          },
        }
      );

      const newDataset: DatasetInfo = {
        dataset_id: creatingDatasetId,
        name: createForm.name,
        collection: creatingDatasetId,
        chunks_count: 0,
        vector_size: 0,
        status: "completed",
      };
      addDataset(newDataset);
      addToast(`Dataset "${createForm.name}" created and ingested successfully`, "success");
      handleClose();
    } catch (err) {
      addToast(
        `Ingestion failed: ${err instanceof Error ? err.message : "Unknown error"}`,
        "error"
      );
      setCreateWizardSaving(false);
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files) return;
    const newFiles = Array.from(files);
    setCreateWizardFiles([...createWizardFiles, ...newFiles]);
    e.target.value = "";
  };

  const removeFile = (index: number) => {
    setCreateWizardFiles(createWizardFiles.filter((_, i) => i !== index));
  };

  const renderStepIndicator = () => (
    <div className={styles.stepIndicator}>
      {[1, 2, 3].map((step) => (
        <div
          key={step}
          className={`${styles.stepCircle} ${
            createWizardStep === step
              ? styles.stepActive
              : createWizardStep > step
              ? styles.stepCompleted
              : ""
          }`}
        >
          {step}
        </div>
      ))}
      <div className={styles.stepLine}>
        <div
          className={styles.stepLineFill}
          style={{
            width: `${
              createWizardStep === 1 ? 0 : createWizardStep === 2 ? 50 : 100
            }%`,
          }}
        />
      </div>
    </div>
  );

  const renderStep1 = () => (
    <div className={styles.stepContent}>
      <Input
        label="Dataset Name"
        placeholder="Enter dataset name"
        value={createForm.name}
        onChange={(e) => setCreateForm({ name: e.target.value })}
        error={createForm.name.length === 0}
      />
      <Textarea
        label="Description (optional)"
        placeholder="Describe this dataset..."
        value={createForm.description}
        onChange={(e) => setCreateForm({ description: e.target.value })}
        rows={3}
      />
    </div>
  );

  const renderStep2 = () => (
    <div className={styles.stepContent}>
      <input
        ref={fileInputRef}
        type="file"
        multiple
        className={styles.hiddenInput}
        onChange={handleFileSelect}
      />
      <Button
        variant="secondary"
        onClick={() => fileInputRef.current?.click()}
      >
        Choose Files
      </Button>
      {createWizardFiles.length > 0 && (
        <ul className={styles.fileList}>
          {createWizardFiles.map((file, idx) => (
            <li key={`${file.name}-${idx}`} className={styles.fileItem}>
              <span className={styles.fileName}>{file.name}</span>
              <span className={styles.fileSize}>
                {(file.size / 1024).toFixed(1)} KB
              </span>
              <button
                className={styles.removeBtn}
                onClick={() => removeFile(idx)}
                aria-label={`Remove ${file.name}`}
              >
                <svg width="12" height="12" viewBox="0 0 12 12" fill="none" stroke="currentColor" strokeWidth="1.5">
                  <path d="M1 1l10 10M11 1L1 11" />
                </svg>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );

  const renderStep3 = () => (
    <div className={styles.stepContent}>
      <div className={styles.summary}>
        <div className={styles.summaryRow}>
          <span className={styles.summaryLabel}>Name:</span>
          <span className={styles.summaryValue}>{createForm.name}</span>
        </div>
        {createForm.description && (
          <div className={styles.summaryRow}>
            <span className={styles.summaryLabel}>Description:</span>
            <span className={styles.summaryValue}>{createForm.description}</span>
          </div>
        )}
        <div className={styles.summaryRow}>
          <span className={styles.summaryLabel}>Files:</span>
          <span className={styles.summaryValue}>
            {createWizardFiles.length} file(s)
          </span>
        </div>
      </div>

      {ingestProgress.progress > 0 && (
        <div className={styles.ingestProgress}>
          <div className={styles.progressBar}>
            <div
              className={styles.progressFill}
              style={{ width: `${ingestProgress.progress}%` }}
            />
          </div>
          <span className={styles.progressPct}>
            {Math.round(ingestProgress.progress)}%
          </span>
          {ingestProgress.message && (
            <span className={styles.progressMessage}>
              {ingestProgress.message}
            </span>
          )}
        </div>
      )}
    </div>
  );

  const getFooter = () => {
    switch (createWizardStep) {
      case 1:
        return (
          <Button variant="primary" onClick={handleStep1Next}>
            Next
          </Button>
        );
      case 2:
        return (
          <>
            <Button variant="ghost" onClick={handleStep2Back}>
              Back
            </Button>
            <Button
              variant="primary"
              onClick={handleStep2Next}
              disabled={createWizardFiles.length === 0}
            >
              Next
            </Button>
          </>
        );
      case 3:
        return (
          <>
            <Button variant="ghost" onClick={handleStep3Back} disabled={createWizardSaving}>
              Back
            </Button>
            <Button
              variant="primary"
              onClick={handleCreateAndIngest}
              loading={createWizardSaving}
              disabled={createWizardSaving}
            >
              Create & Ingest
            </Button>
          </>
        );
    }
  };

  return (
    <Modal
      open={isCreateWizardOpen && open}
      onClose={handleClose}
      title="Create Dataset"
      footer={getFooter()}
    >
      {renderStepIndicator()}
      {createWizardStep === 1 && renderStep1()}
      {createWizardStep === 2 && renderStep2()}
      {createWizardStep === 3 && renderStep3()}
    </Modal>
  );
}
