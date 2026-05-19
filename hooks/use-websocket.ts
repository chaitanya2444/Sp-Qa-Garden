"use client"

import { useEffect, useRef, useState } from 'react';
import { useRunsStore } from '@/store/runs-store';
import axios from 'axios';
import { getWsUrl, getAgentUrl, API_KEY } from '@/lib/api';
import { toast } from '@/hooks/use-toast';
import { AgentType } from '@/types/run';

interface UseWebSocketOptions {
    runId?: string;
    onMessage?: (event: string, data: any) => void;
}

export function useWebSocket({ runId, onMessage }: UseWebSocketOptions = {}) {
    const wsRef = useRef<WebSocket | null>(null);
    const [isConnected, setIsConnected] = useState(false);

    // Get the run from the store to determine the initial port
    const run = useRunsStore(state => state.runs.find(r => r.id === runId));

    // Determine target agent path based on agent statuses
    let initialAgentPath = 'crawler'; // Default to crawler
    if (run) {
        if (run.agents.executor.status === 'running' || run.agents.executor.status === 'completed') {
            initialAgentPath = 'cicd'; // CI/CD Agent
        } else if (run.agents.script_generator.status === 'running' || run.agents.script_generator.status === 'completed') {
            initialAgentPath = 'playwright';
        } else if (run.agents.test_generator.status === 'running' || run.agents.test_generator.status === 'completed') {
            initialAgentPath = 'test_gen';
        }
    }

    const [currentAgentPath, setCurrentAgentPath] = useState<string>(initialAgentPath);

    // Select actions individually to avoid subscribing to the entire store
    const updateAgent = useRunsStore(state => state.updateAgent);
    const updateRun = useRunsStore(state => state.updateRun);
    const addLog = useRunsStore(state => state.addLog);

    useEffect(() => {
        if (!runId || runId === 'undefined') return;

        const wsUrl = getWsUrl(runId, currentAgentPath);
        console.log(`Attempting WebSocket connection to ${wsUrl}...`);

        let ws: WebSocket;
        try {
            ws = new WebSocket(wsUrl);
            wsRef.current = ws;
        } catch (e) {
            console.error("Failed to create WebSocket instance:", e);
            return;
        }

        ws.onopen = () => {
            console.log(`WebSocket Connected to ${wsUrl}`);
            setIsConnected(true);
        };

        ws.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                const type = data.type || data.event;
                const payload = data.payload || data;

                switch (type) {
                    case 'progress':
                        if (payload.config) {
                            updateRun(runId, {
                                url: payload.config.url,
                                config: {
                                    crawl_depth: payload.config.max_depth,
                                    max_pages: payload.config.max_pages,
                                    form_interactions: !!payload.config.form_interactions,
                                    failure_policy: {
                                        onAgentFailure: payload.config.failure_policy,
                                        maxRetries: payload.config.max_retries
                                    },
                                    auth_enabled: !!payload.config.auth_creds
                                }
                            });
                        }

                        updateAgent(runId, (payload.agent || 'crawler') as AgentType, {
                            status: 'running',
                            progress: payload.percent || payload.page_count || payload.finished || 0,
                            duration: payload.duration,
                            inputs: payload.config ? {
                                url: payload.config.url,
                                max_depth: payload.config.max_depth,
                                max_pages: payload.config.max_pages
                            } : undefined,
                            metrics: payload.metrics || {
                                elements: payload.elements,
                                finished: payload.finished,
                                discovered: payload.discovered,
                                current_url: payload.url
                            },
                        });
                        break;

                    case 'page_complete':
                    case 'pages_discovered':
                        addLog({
                            id: `log-${Date.now()}`,
                            runId,
                            agent: (payload.agent || 'crawler') as AgentType,
                            message: payload.url ? `Indexed: ${payload.url}` : `Discovered ${payload.count} pages via ${payload.source}`,
                            level: 'info',
                            timestamp: new Date().toISOString(),
                        });
                        break;

                    case 'log':
                        addLog({
                            id: `log-${Date.now()}`,
                            runId,
                            agent: (payload.agent || 'crawler') as AgentType,
                            message: payload.message,
                            level: payload.level || 'info',
                            timestamp: payload.timestamp || new Date().toISOString(),
                        });
                        break;

                    case 'artifact':
                        const currentRunData = useRunsStore.getState().getRun(runId);
                        if (currentRunData) {
                            const agentType = (payload.agent || 'crawler') as AgentType;
                            const agentData = currentRunData.agents[agentType];
                            updateAgent(runId, agentType, {
                                artifacts: [...(agentData?.artifacts || []), payload.artifact || payload],
                            });
                        }
                        break;

                    case 'error':
                        updateAgent(runId, (payload.agent as AgentType) || 'crawler', {
                            status: 'failed',
                            progress: 0,
                            error: payload.message || payload.error,
                        });
                        toast({
                            title: `Agent Error: ${payload.agent || 'crawler'}`,
                            description: payload.message || payload.error,
                            variant: 'destructive',
                        });
                        break;

                    case 'coverage_update':
                        updateAgent(runId, 'crawler', {
                            metrics: {
                                discovered: payload.discovered,
                                elements: payload.extracted,
                                coverage: payload.coverage_percent,
                            }
                        });
                        break;

                    case 'generation_started':
                        updateAgent(runId, 'test_generator', {
                            status: 'running',
                            startTime: payload.startedAt,
                            inputs: payload.inputs,
                        });
                        addLog({
                            id: `log-${Date.now()}`,
                            runId,
                            agent: 'test_generator',
                            message: 'Test generation started...',
                            level: 'info',
                            timestamp: payload.startedAt,
                        });
                        break;

                    case 'test_cases_updated':
                        updateAgent(runId, 'test_generator', {
                            progress: 100,
                            metrics: payload.metrics || {
                                test_cases: payload.testCaseCount,
                            },
                            outputs: payload.outputs
                        });
                        break;

                    case 'completed':
                        const completedAgent = (payload.agent || 'crawler') as AgentType;
                        const finalMetrics = payload.metrics ? payload.metrics : (payload.total_locators ? {
                            elements: payload.total_locators,
                            discovered: payload.discovered_count,
                            finished: payload.page_count,
                        } : undefined);

                        updateAgent(runId, completedAgent, {
                            status: 'completed',
                            progress: 100,
                            endTime: new Date().toISOString(),
                            metrics: finalMetrics,
                            outputs: payload.result || payload.data || payload
                        });

                        if (completedAgent === 'crawler') {
                            const r = useRunsStore.getState().getRun(runId);
                            const jsonArtifact = payload.path || r?.agents.crawler?.artifacts?.find(a => a.type === 'json' && a.name.includes('Consolidated'))?.path;

                            if (jsonArtifact) {
                                console.log("Triggering handover with artifact:", jsonArtifact);
                                updateAgent(runId, 'test_generator', { status: 'running', progress: 10 });
                                // Pass the DIRECTORY, not the file, so it finds page_*.json
                                const path = payload.path || jsonArtifact;
                                // If path ends in .json, get parent dir
                                const locatorsDir = path.endsWith('.json') ? path.substring(0, path.lastIndexOf('\\')) : path;

                                axios.post(`${getAgentUrl('test_gen')}/api/v1/generate-tests`, {
                                    run_id: runId,
                                    locators_path: locatorsDir,
                                    target_url: r?.url
                                }, {
                                    headers: { 'X-API-Key': API_KEY }
                                }).then(() => {
                                    // Delay agent path switch so the current connection can close gracefully
                                    setTimeout(() => setCurrentAgentPath('test_gen'), 200);
                                }).catch(err => {
                                    console.error("Handover to Test Generator failed", err);
                                    toast({
                                        title: "Handover Failed",
                                        description: "Could not trigger Test Generator. Please check if the service is running on port 8001.",
                                        variant: "destructive"
                                    });
                                });
                            }
                        } else if (completedAgent === 'test_generator') {
                            // Backend already triggered Playwright Gen internally.
                            // Just update UI state and switch WebSocket to listen to it.
                            updateAgent(runId, 'script_generator', { status: 'running', progress: 10 });
                            setTimeout(() => setCurrentAgentPath('playwright'), 200);
                        } else if (completedAgent === 'script_generator') {
                            // Backend already triggered CI/CD internally.
                            // Just update UI state and switch WebSocket to listen to it.
                            updateAgent(runId, 'executor', { status: 'running', progress: 10 });
                            setTimeout(() => setCurrentAgentPath('cicd'), 200);
                        } else if (completedAgent === 'executor') {
                            // Check for failures in metrics
                            const failedTests = payload.metrics?.failed || 0;

                            if (failedTests > 0) {
                                console.log(`Triggering Triage for ${failedTests} failures`);
                                updateAgent(runId, 'triage', { status: 'running', progress: 10 });
                                // Triage is triggered automatically by the CICD agent via webhook, 
                                // but we need to switch the websocket port to listen to it.
                                setTimeout(() => setCurrentAgentPath('triage'), 500);
                            } else {
                                // All passed, pipeline finished
                                updateAgent(runId, 'triage', { status: 'skipped' });
                                // Manually trigger pipeline finish since no more agents
                                updateRun(runId, {
                                    status: 'completed',
                                    completedAt: new Date().toISOString(),
                                });
                            }
                        } else if (completedAgent === 'triage') {
                            // Triage finished
                            updateRun(runId, {
                                status: 'completed',
                                completedAt: new Date().toISOString(),
                            });
                        }

                        break;

                    case 'pipeline_finished':
                        updateRun(runId, {
                            status: 'completed',
                            completedAt: new Date().toISOString(),
                        });
                        break;

                }

                if (onMessage) {
                    onMessage(type, payload);
                }
            } catch (err) {
                console.error('Failed to parse WebSocket message:', err);
            }
        };

        ws.onclose = () => {
            console.log(`WebSocket Disconnected from ${wsUrl}`);
            setIsConnected(false);
        };

        ws.onerror = (error) => {
            console.error('WebSocket Error connection failed. Agent Path:', currentAgentPath);
            // If connection failed on crawler, maybe try a small delay retry?
            // For now, we just log it as the user reported.
        };

        return () => {
            ws.close();
        };
    }, [runId, currentAgentPath, updateAgent, updateRun, addLog, onMessage]);

    return {
        ws: wsRef.current,
        isConnected,
    };
}

