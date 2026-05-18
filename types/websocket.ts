import { AgentType, AgentStatus, Artifact } from './agent';

export type WSMessage =
    | {
        event: 'agent_update';
        run_id: string;
        agent: AgentType;
        status: AgentStatus;
        progress?: number;
        duration?: number;
    }
    | {
        event: 'run_update';
        run_id: string;
        status: AgentStatus;
        total_duration?: number;
    }
    | {
        event: 'log';
        run_id: string;
        agent: AgentType;
        message: string;
        timestamp: string;
        level?: 'info' | 'warning' | 'error';
    }
    | {
        event: 'artifact';
        run_id: string;
        agent: AgentType;
        artifact: Artifact;
    }
    | {
        event: 'error';
        run_id: string;
        message: string;
        agent?: AgentType;
    };
