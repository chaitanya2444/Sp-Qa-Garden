"use client"

import { useEffect, useState } from 'react';
import { MainLayout } from '@/components/layout/main-layout';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Activity, ShieldCheck, ShieldAlert, RefreshCw, Cpu, Database, Network } from 'lucide-react';
import { cn } from '@/lib/utils';
import axios from 'axios';

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';

interface AgentStatus {
    name: string;
    path: string;
    description: string;
    port: number;
    status: 'checking' | 'online' | 'offline';
    responseTime?: number;
    details?: string;
}

export default function HealthPage() {
    const [unifiedStatus, setUnifiedStatus] = useState<'checking' | 'online' | 'offline'>('checking');
    const [responseTime, setResponseTime] = useState<number | null>(null);
    const [agents, setAgents] = useState<AgentStatus[]>([
        {
            name: 'Web Crawler API',
            path: 'crawler/',
            port: 8005,
            description: 'Extracts interactive elements and maps UI configurations.',
            status: 'checking'
        },
        {
            name: 'Test Case Generator',
            path: 'test_gen/',
            port: 8001,
            description: 'Translates locator maps into logical test cases using AI.',
            status: 'checking'
        },
        {
            name: 'Playwright Script Gen',
            path: 'playwright/',
            port: 8002,
            description: 'Transforms requirements into deployable test script bundles.',
            status: 'checking'
        },
        {
            name: 'CI/CD Runtime Executor',
            path: 'cicd/',
            port: 8003,
            description: 'Runs parallel browsers in sandboxed containers.',
            status: 'checking'
        },
        {
            name: 'Failure Triage Engine',
            path: 'triage/',
            port: 8004,
            description: 'Investigates failed executions using BERT/LLM clusters.',
            status: 'checking'
        }
    ]);

    const checkHealth = async () => {
        setUnifiedStatus('checking');
        const startUnified = Date.now();
        
        // 1. Check Unified Gateway
        try {
            const res = await axios.get(BACKEND_URL, { timeout: 8000 });
            setResponseTime(Date.now() - startUnified);
            if (res.data && String(res.data).includes('Unified Backend')) {
                setUnifiedStatus('online');
            } else {
                setUnifiedStatus('online'); // Still connected to proxy
            }
        } catch (err) {
            setUnifiedStatus('offline');
            setResponseTime(null);
        }

        // 2. Check Each Agent Proxy Route
        const updatedAgents = [...agents];
        for (let i = 0; i < updatedAgents.length; i++) {
            const agent = updatedAgents[i];
            agent.status = 'checking';
            const agentStart = Date.now();
            try {
                // Ping agent proxy path (using a HEAD/GET request)
                const url = `${BACKEND_URL}/${agent.path}`;
                await axios.get(url, { 
                    timeout: 8000,
                    headers: { 'X-API-Key': 'qa-garden-secret-key' } 
                });
                agent.status = 'online';
                agent.responseTime = Date.now() - agentStart;
                agent.details = 'Active and answering.';
            } catch (err: any) {
                // If it answers with a client/server error but NOT a 502/504 bad gateway, the service is STILL running
                const status = err.response?.status;
                if (status && status !== 502 && status !== 504 && status !== 503) {
                    agent.status = 'online';
                    agent.responseTime = Date.now() - agentStart;
                    agent.details = `Active (Response Code ${status}).`;
                } else {
                    agent.status = 'offline';
                    agent.responseTime = undefined;
                    agent.details = err.response?.status === 502 ? '502 Bad Gateway (Port Closed)' : 'Unreachable.';
                }
            }
        }
        setAgents(updatedAgents);
    };

    useEffect(() => {
        checkHealth();
    }, []);

    return (
        <MainLayout>
            <div className="max-w-6xl mx-auto space-y-10 pb-16 px-4">
                {/* Header */}
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 border-b border-border/40 pb-8">
                    <div className="space-y-1">
                        <div className="flex items-center gap-2">
                            <Activity className="h-6 w-6 text-primary animate-pulse" />
                            <h1 className="text-4xl font-black tracking-tighter bg-clip-text text-transparent bg-gradient-to-br from-foreground to-foreground/40">System Health</h1>
                        </div>
                        <p className="text-muted-foreground text-sm font-medium">
                            Real-time diagnostics of the AI cluster proxy gateway and agent containers.
                        </p>
                    </div>

                    <button 
                        onClick={checkHealth}
                        className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-primary/10 hover:bg-primary/20 border border-primary/30 text-primary text-xs font-bold uppercase tracking-widest active:scale-95 transition-all shadow-md"
                    >
                        <RefreshCw className="h-4 w-4" />
                        Trigger Diagnostics
                    </button>
                </div>

                {/* Gateway Status Panel */}
                <Card className="border-border/40 bg-card/30 backdrop-blur-xl shadow-2xl relative overflow-hidden">
                    <div className="absolute top-0 right-0 p-8 opacity-5">
                        <Network className="h-32 w-32" />
                    </div>
                    <CardHeader className="pb-4">
                        <CardTitle className="text-sm font-bold uppercase tracking-widest text-primary/60">Unified Cluster Gateway</CardTitle>
                        <CardDescription className="text-xs">Primary entry point for global ingress proxy routing</CardDescription>
                    </CardHeader>
                    <CardContent className="flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
                        <div className="space-y-2">
                            <div className="flex items-center gap-3">
                                <span className="text-xs font-bold font-mono text-muted-foreground uppercase bg-muted/50 py-1 px-2.5 rounded border border-border/40">Endpoint</span>
                                <span className="text-lg font-mono font-bold tracking-tight text-foreground/80 break-all">{BACKEND_URL}</span>
                            </div>
                            {responseTime !== null && (
                                <p className="text-xs text-muted-foreground uppercase font-bold tracking-tighter">
                                    Latency: <span className="text-primary">{responseTime}ms</span>
                                </p>
                            )}
                        </div>

                        <div className="flex items-center gap-3">
                            <Badge 
                                className={cn(
                                    "rounded-xl px-4 py-2 text-xs font-bold uppercase tracking-widest border-none shadow-md",
                                    unifiedStatus === 'online' ? "bg-green-500/10 text-green-500" :
                                    unifiedStatus === 'checking' ? "bg-amber-500/10 text-amber-500 animate-pulse" :
                                    "bg-red-500/10 text-red-500"
                                )}
                            >
                                {unifiedStatus === 'online' ? (
                                    <span className="flex items-center gap-2"><ShieldCheck className="h-4 w-4" /> Connected</span>
                                ) : unifiedStatus === 'checking' ? (
                                    <span className="flex items-center gap-2"><RefreshCw className="h-4 w-4 animate-spin" /> Verifying</span>
                                ) : (
                                    <span className="flex items-center gap-2"><ShieldAlert className="h-4 w-4" /> Offline (404/Connection Failed)</span>
                                )}
                            </Badge>
                        </div>
                    </CardContent>
                </Card>

                {/* Agents Status Grid */}
                <div className="space-y-6">
                    <h2 className="text-lg font-bold uppercase tracking-widest text-muted-foreground">Neural Agent Nodes</h2>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        {agents.map((agent) => (
                            <Card key={agent.name} className="border-border/40 bg-card/20 backdrop-blur-md shadow-lg flex flex-col justify-between hover:bg-card/30 transition-all duration-300">
                                <CardHeader className="pb-2">
                                    <div className="flex items-center justify-between">
                                        <div className="space-y-1">
                                            <CardTitle className="text-base font-bold text-foreground/90">{agent.name}</CardTitle>
                                            <p className="text-[10px] font-mono text-muted-foreground uppercase tracking-widest">Proxied Ingress /{agent.path} (Port {agent.port})</p>
                                        </div>
                                        <Badge 
                                            className={cn(
                                                "rounded-lg px-2.5 py-1 text-[9px] uppercase font-black tracking-widest border-none",
                                                agent.status === 'online' ? "bg-green-500/10 text-green-500" :
                                                agent.status === 'checking' ? "bg-amber-500/10 text-amber-500 animate-pulse" :
                                                "bg-red-500/10 text-red-500"
                                            )}
                                        >
                                            {agent.status}
                                        </Badge>
                                    </div>
                                </CardHeader>
                                <CardContent className="pt-4 flex flex-col justify-between flex-grow gap-4">
                                    <p className="text-xs text-muted-foreground/80 leading-relaxed font-medium">
                                        {agent.description}
                                    </p>
                                    <div className="flex items-center justify-between border-t border-border/20 pt-4 text-[10px] uppercase font-bold text-muted-foreground/50">
                                        <span>Status: {agent.details || 'Awaiting ping...'}</span>
                                        {agent.responseTime && (
                                            <span className="text-primary font-mono font-black">{agent.responseTime}ms</span>
                                        )}
                                    </div>
                                </CardContent>
                            </Card>
                        ))}
                    </div>
                </div>
            </div>
        </MainLayout>
    );
}
