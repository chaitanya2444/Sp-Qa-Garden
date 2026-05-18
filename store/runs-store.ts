"use client"

import { create } from 'zustand';
import { Run, RunLog } from '@/types/run';
import { AgentType, AgentData } from '@/types/agent';

interface RunsStore {
    runs: Run[];
    logs: RunLog[];
    addRun: (run: Run) => void;
    updateRun: (runId: string, updates: Partial<Run>) => void;
    updateAgent: (runId: string, agent: AgentType, updates: Partial<AgentData>) => void;
    addLog: (log: RunLog) => void;
    getRun: (runId: string) => Run | undefined;
    getRunLogs: (runId: string) => RunLog[];
}

export const useRunsStore = create<RunsStore>((set, get) => ({
    runs: [],
    logs: [],

    addRun: (run) => set((state) => ({
        runs: [run, ...state.runs],
    })),

    updateRun: (runId, updates) => set((state) => ({
        runs: state.runs.map((run) =>
            run.id === runId ? { ...run, ...updates } : run
        ),
    })),

    updateAgent: (runId, agent, updates) => set((state) => ({
        runs: state.runs.map((run) =>
            run.id === runId
                ? {
                    ...run,
                    agents: {
                        ...run.agents,
                        [agent]: { ...run.agents[agent], ...updates },
                    },
                }
                : run
        ),
    })),

    addLog: (log) => set((state) => ({
        logs: [...state.logs, log],
    })),

    getRun: (runId) => get().runs.find((run) => run.id === runId),

    getRunLogs: (runId) => get().logs.filter((log) => log.runId === runId),
}));
