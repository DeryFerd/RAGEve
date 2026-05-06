// Dialogs API client — replaces the old /agents endpoints.
// Backend: GET/POST/PUT/DELETE /dialogs/

import { create } from "zustand";
import type { DialogResponse } from "@/lib/types";

interface AgentsState {
  agents: DialogResponse[];
  selectedAgentId: string | null;
  loading: boolean;
  error: string | null;

  setAgents: (agents: DialogResponse[]) => void;
  addAgent: (agent: DialogResponse) => void;
  updateAgent: (agent: DialogResponse) => void;
  removeAgent: (agentId: string) => void;
  setSelectedAgentId: (id: string | null) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
}

export const useAgentsStore = create<AgentsState>()((set) => ({
  agents: [],
  selectedAgentId: null,
  loading: false,
  error: null,

  setAgents: (agents) => set({ agents }),
  addAgent: (agent) =>
    set((state) => ({
      agents: [...state.agents, agent],
    })),
  updateAgent: (agent) =>
    set((state) => ({
      agents: state.agents.map((a) =>
        a.id === agent.id ? agent : a,
      ),
    })),
  removeAgent: (agentId) =>
    set((state) => ({
      agents: state.agents.filter((a) => a.id !== agentId),
      selectedAgentId:
        state.selectedAgentId === agentId ? null : state.selectedAgentId,
    })),
  setSelectedAgentId: (selectedAgentId) => set({ selectedAgentId }),
  setLoading: (loading) => set({ loading }),
  setError: (error) => set({ error }),
}));
