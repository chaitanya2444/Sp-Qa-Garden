export type AgentType =
    | 'crawler'
    | 'test_generator'
    | 'script_generator'
    | 'executor'
    | 'triage';

export type AgentStatus =
    | 'pending'
    | 'running'
    | 'completed'
    | 'failed'
    | 'skipped';

export interface Artifact {
    id: string;
    type: 'video' | 'screenshot' | 'trace' | 'log' | 'json';
    name: string;
    url: string;
    path?: string;
    runId?: string;
    size?: number;
    timestamp: string;
}

export interface AgentData {
    type: AgentType;
    status: AgentStatus;
    progress?: number; // 0-100
    duration?: number; // milliseconds
    startTime?: string;
    endTime?: string;
    inputs?: Record<string, any>;
    outputs?: Record<string, any>;
    artifacts?: Artifact[];
    error?: string;
    metrics?: Record<string, any>;
}

export const AGENT_LABELS: Record<AgentType, string> = {
    crawler: 'Web Crawler',
    test_generator: 'Test Case Generator',
    script_generator: 'Script Generator',
    executor: 'Test Executor',
    triage: 'Failure Triage',
};

export const AGENT_DESCRIPTIONS: Record<AgentType, string> = {
    crawler: 'Crawls URL and extracts UI elements/locators using Playwright',
    test_generator: 'Generates test cases from crawler data using LLM',
    script_generator: 'Creates executable Playwright scripts',
    executor: 'Runs tests in Docker, captures videos/screenshots/traces',
    triage: 'Analyzes failures using LLM/BERT and suggests fixes',
};
