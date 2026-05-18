import { AgentType, AgentData, Artifact } from '@/types/agent';
import { Run, RunConfig } from '@/types/run';

export const MOCK_RUN_ID = 'run-12345';

export const MOCK_ARTIFACTS: Record<string, Artifact> = {
    screenshot: {
        id: 'art-1',
        type: 'screenshot',
        name: 'login-page.png',
        url: 'https://placehold.co/1920x1080/png?text=Login+Page+Screenshot',
        timestamp: new Date().toISOString(),
    },
    video: {
        id: 'art-2',
        type: 'video',
        name: 'test-execution.mp4',
        url: 'https://media.w3.org/2010/05/sintel/trailer_hd.mp4', // Detailed mock video
        timestamp: new Date().toISOString(),
    },
    trace: {
        id: 'art-3',
        type: 'trace',
        name: 'trace.zip',
        url: '#',
        timestamp: new Date().toISOString(),
    },
};

export const MOCK_AGENTS_DATA: Record<AgentType, AgentData> = {
    crawler: {
        type: 'crawler',
        status: 'completed',
        progress: 100,
        duration: 45000,
        inputs: { url: 'https://example.com', depth: 3 },
        outputs: { pages: 12, elements: 450 },
        artifacts: [
            { ...MOCK_ARTIFACTS.screenshot, name: 'home.png' },
        ],
    },
    test_generator: {
        type: 'test_generator',
        status: 'completed',
        progress: 100,
        duration: 12000,
        inputs: { elements_count: 450 },
        outputs: { test_cases: 25 },
    },
    script_generator: {
        type: 'script_generator',
        status: 'running',
        progress: 65,
        duration: 5000,
        inputs: { test_cases: 25 },
        metrics: { coverageEstimate: 85 },
    },
    executor: {
        type: 'executor',
        status: 'pending',
        progress: 0,
    },
    triage: {
        type: 'triage',
        status: 'pending',
        progress: 0,
    },
    jira: {
        type: 'jira',
        status: 'pending',
        progress: 0,
    },
};

export const MOCK_RUN: Run = {
    id: MOCK_RUN_ID,
    url: 'https://example.com',
    status: 'running',
    config: {
        crawl_depth: 3,
        form_interactions: true,
        auth_enabled: false,
        failure_policy: { onAgentFailure: 'stop', maxRetries: 3 }
    },
    agents: MOCK_AGENTS_DATA,
    createdAt: new Date().toISOString(),
    startedAt: new Date().toISOString(),
};

export const MOCK_FAILURES = [
    {
        id: 'fail-1',
        runId: MOCK_RUN_ID,
        title: 'Login button not clickable',
        stage: 'executor',
        category: 'locator_changed',
        severity: 'high',
        cause: 'CSS selector .login-btn matching 0 elements',
        suggestion: 'Update selector to #login-submit',
        artifact: MOCK_ARTIFACTS.screenshot,
    },
    {
        id: 'fail-2',
        runId: MOCK_RUN_ID,
        title: 'Timeout waiting for dashboard',
        stage: 'executor',
        category: 'network_timeout',
        severity: 'medium',
        cause: 'Network request took > 30s',
        suggestion: 'Increase timeout or checking staging env latency',
        artifact: MOCK_ARTIFACTS.trace,
    },
];

export const MOCK_JIRA_BUGS = [
    {
        id: 'BUG-1234',
        summary: 'Login flow broken on staging',
        status: 'To Do',
        assignee: 'QA Bot',
        priority: 'High',
        linkedRunId: MOCK_RUN_ID,
        url: 'https://jira.example.com/browse/BUG-1234',
    },
    {
        id: 'BUG-1235',
        summary: 'Checkout page overlapping elements',
        status: 'In Progress',
        assignee: 'Jane Doe',
        priority: 'Medium',
        linkedRunId: 'run-92a8b1',
        url: 'https://jira.example.com/browse/BUG-1235',
    },
];
