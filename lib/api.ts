import axios from 'axios';

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';
export const API_KEY = process.env.NEXT_PUBLIC_API_KEY || 'qa-garden-secret-key';

export const api = axios.create({
    baseURL: `${BACKEND_URL}/crawler`,
    headers: {
        'Content-Type': 'application/json',
        'X-API-Key': API_KEY,
    },
});

export const getWsUrl = (runId: string, agentPath: string = 'crawler') => {
    const url = new URL(BACKEND_URL);
    const protocol = url.protocol === 'https:' ? 'wss:' : 'ws:';
    const hostname = url.hostname;
    const portString = url.port ? `:${url.port}` : '';
    // Format: ws://localhost:8000/crawler/ws/run_id
    return `${protocol}//${hostname}${portString}/${agentPath}/ws/${runId}`;
};

export const getAgentUrl = (agentPath: string) => {
    // Format: http://localhost:8000/crawler
    return `${BACKEND_URL}/${agentPath}`;
};

