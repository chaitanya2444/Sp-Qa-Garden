import { AgentData, AgentType } from './agent';
export type { AgentData, AgentType };

export type RunStatus =
    | 'pending'
    | 'running'
    | 'completed'
    | 'failed'
    | 'cancelled';

export type FailurePolicy = 'stop' | 'continue' | 'retry';

export interface RunConfig {
    crawl_depth: number;
    max_pages: number;
    form_interactions: boolean;
    auth_enabled: boolean;
    failure_policy: {
        onAgentFailure: FailurePolicy;
        maxRetries: number;
    };
}

export interface Run {
    id: string;
    url: string;
    config: RunConfig;
    status: RunStatus;
    agents: Record<AgentType, AgentData>;
    createdAt: string;
    startedAt?: string;
    completedAt?: string;
    totalDuration?: number;
    successRate?: number;
    bugsCreated?: number;
}

export interface RunLog {
    id: string;
    runId: string;
    agent: AgentType;
    message: string;
    level: 'info' | 'warning' | 'error';
    timestamp: string;
}
