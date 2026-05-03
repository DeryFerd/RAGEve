"use client";

import { create } from "zustand";
import type {
  ProcessedFileResponse,
  DatasetInfo,
  UploadProgressState,
  KbDocumentResponse,
} from "@/lib/types";
import { initialUploadProgressState } from "@/lib/types";
import { listDocuments } from "@/lib/api/knowledgebases";

interface DatasetsState {
  datasets: DatasetInfo[];
  uploadingDatasetId: string | null;
  uploadResults: Record<string, ProcessedFileResponse[]>;
  uploadProgress: UploadProgressState;
  loading: boolean;
  error: string | null;

  // --- NEW: Dataset detail expansion ---
  selectedDetailId: string | null;
  documentsByDataset: Record<string, KbDocumentResponse[]>;
  documentsLoading: Record<string, boolean>;

  // --- NEW: Create wizard state ---
  isCreateWizardOpen: boolean;
  createWizardStep: 1 | 2 | 3;
  createForm: { name: string; description: string };
  createWizardFiles: File[];
  creatingDatasetId: string | null;
  createWizardSaving: boolean;

  // --- NEW: Ingest progress ---
  ingestProgress: Record<
    string,
    { active: boolean; progress: number; message: string; stage: string }
  >;

  setDatasets: (datasets: DatasetInfo[]) => void;
  addDataset: (dataset: DatasetInfo) => void;
  removeDataset: (datasetId: string) => void;
  setUploading: (datasetId: string | null) => void;
  setUploadResults: (
    datasetId: string,
    results: ProcessedFileResponse[],
  ) => void;
  setUploadProgress: (progress: Partial<UploadProgressState>) => void;
  resetUploadProgress: () => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;

  // --- NEW: Detail expansion actions ---
  toggleDetail: (datasetId: string) => void;
  setDetail: (datasetId: string | null) => void;
  setDocuments: (datasetId: string, docs: KbDocumentResponse[]) => void;
  addDocuments: (datasetId: string, docs: KbDocumentResponse[]) => void;
  setDocumentsLoading: (datasetId: string, loading: boolean) => void;

  // --- NEW: Wizard actions ---
  openCreateWizard: () => void;
  closeCreateWizard: () => void;
  setCreateWizardStep: (step: 1 | 2 | 3) => void;
  setCreateForm: (form: Partial<{ name: string; description: string }>) => void;
  setCreateWizardFiles: (files: File[]) => void;
  setCreatingDatasetId: (id: string | null) => void;
  setCreateWizardSaving: (saving: boolean) => void;
  resetCreateWizard: () => void;

  // --- NEW: Ingest actions ---
  setIngestProgress: (
    datasetId: string,
    progress: Partial<{
      active: boolean;
      progress: number;
      message: string;
      stage: string;
    }>,
  ) => void;
  resetIngestProgress: (datasetId: string) => void;
}

export const useDatasetsStore = create<DatasetsState>()((set, get) => ({
  datasets: [],
  uploadingDatasetId: null,
  uploadResults: {},
  uploadProgress: initialUploadProgressState,
  loading: false,
  error: null,

  // --- NEW: Dataset detail expansion ---
  selectedDetailId: null,
  documentsByDataset: {},
  documentsLoading: {},

  // --- NEW: Create wizard state ---
  isCreateWizardOpen: false,
  createWizardStep: 1,
  createForm: { name: "", description: "" },
  createWizardFiles: [],
  creatingDatasetId: null,
  createWizardSaving: false,

  // --- NEW: Ingest progress ---
  ingestProgress: {},

  setDatasets: (datasets) => set({ datasets }),
  addDataset: (dataset) =>
    set((state) => ({
      datasets: state.datasets.some((d) => d.dataset_id === dataset.dataset_id)
        ? state.datasets
        : [...state.datasets, dataset],
    })),
  removeDataset: (datasetId) =>
    set((state) => ({
      datasets: state.datasets.filter((d) => d.dataset_id !== datasetId),
      uploadResults: Object.fromEntries(
        Object.entries(state.uploadResults).filter(([k]) => k !== datasetId),
      ),
    })),
  setUploading: (uploadingDatasetId) => set({ uploadingDatasetId }),
  setUploadResults: (datasetId, results) =>
    set((state) => ({
      uploadResults: { ...state.uploadResults, [datasetId]: results },
    })),
  setUploadProgress: (progress) =>
    set((state) => ({
      uploadProgress: { ...state.uploadProgress, ...progress },
    })),
  resetUploadProgress: () =>
    set({ uploadProgress: initialUploadProgressState }),
  setLoading: (loading) => set({ loading }),
  setError: (error) => set({ error }),

  // --- NEW: Detail expansion actions ---
  toggleDetail: async (datasetId) => {
    const state = get();
    if (state.selectedDetailId === datasetId) {
      set({ selectedDetailId: null });
      return;
    }
    set({ selectedDetailId: datasetId });
    try {
      get().setDocumentsLoading(datasetId, true);
      const res = await listDocuments({ kb_id: datasetId });
      get().setDocuments(datasetId, res);
    } catch (err) {
      console.error("Failed to load documents:", err);
    } finally {
      get().setDocumentsLoading(datasetId, false);
    }
  },
  setDetail: (datasetId) => set({ selectedDetailId: datasetId }),
  setDocuments: (datasetId, docs) =>
    set((state) => ({
      documentsByDataset: { ...state.documentsByDataset, [datasetId]: docs },
    })),
  addDocuments: (datasetId, docs) =>
    set((state) => ({
      documentsByDataset: {
        ...state.documentsByDataset,
        [datasetId]: [...(state.documentsByDataset[datasetId] || []), ...docs],
      },
    })),
  setDocumentsLoading: (datasetId, loading) =>
    set((state) => ({
      documentsLoading: { ...state.documentsLoading, [datasetId]: loading },
    })),

  // --- NEW: Wizard actions ---
  openCreateWizard: () =>
    set({
      isCreateWizardOpen: true,
      createWizardStep: 1,
      createForm: { name: "", description: "" },
      createWizardFiles: [],
      creatingDatasetId: null,
      createWizardSaving: false,
    }),
  closeCreateWizard: () =>
    set({
      isCreateWizardOpen: false,
      createWizardStep: 1,
      createForm: { name: "", description: "" },
      createWizardFiles: [],
      creatingDatasetId: null,
      createWizardSaving: false,
    }),
  setCreateWizardStep: (step) => set({ createWizardStep: step }),
  setCreateForm: (form) =>
    set((state) => ({
      createForm: { ...state.createForm, ...form },
    })),
  setCreateWizardFiles: (files) => set({ createWizardFiles: files }),
  setCreatingDatasetId: (id) => set({ creatingDatasetId: id }),
  setCreateWizardSaving: (saving) => set({ createWizardSaving: saving }),
  resetCreateWizard: () =>
    set({
      createWizardStep: 1,
      createForm: { name: "", description: "" },
      createWizardFiles: [],
      creatingDatasetId: null,
      createWizardSaving: false,
    }),

  // --- NEW: Ingest actions ---
  setIngestProgress: (datasetId, progress) =>
    set((state) => ({
      ingestProgress: {
        ...state.ingestProgress,
        [datasetId]: {
          ...(state.ingestProgress[datasetId] || {}),
          ...progress,
        },
      },
    })),
  resetIngestProgress: (datasetId) =>
    set((state) => ({
      ingestProgress: {
        ...state.ingestProgress,
        [datasetId]: { active: false, progress: 0, message: "", stage: "" },
      },
    })),
}));
