"use client"

import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import { MainLayout } from '@/components/layout/main-layout';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { api } from '@/lib/api';
import { useToast } from '@/hooks/use-toast';
import { Card } from '@/components/ui/card';
import { AgentCard } from '@/components/agent-card';
import { TerminalLog } from '@/components/terminal-log';
import { useWebSocket } from '@/hooks/use-websocket';
import { useRunsStore } from '@/store/runs-store';
import { AgentType } from '@/types/agent';
import { Run } from '@/types/run';
import { MOCK_RUN } from '@/lib/mock-data';
import { ArrowLeft, Pause, Square, Play, Activity } from 'lucide-react';
import Link from 'next/link';
import { Skeleton } from '@/components/ui/skeleton';
import { useShallow } from 'zustand/shallow';

const AGENT_ORDER: AgentType[] = [
    'crawler',
    'test_generator',
    'script_generator',
    'executor',
    'triage',
];

export default function RunDetailPage() {
    const params = useParams();
    const runId = params.id as string;

    const storeRun = useRunsStore(state => state.getRun(runId));
    const logs = useRunsStore(useShallow(state => state.getRunLogs(runId)));
    const { addRun } = useRunsStore();
    const { toast } = useToast();
    const [run, setRun] = useState<Run | undefined>(storeRun);

    useEffect(() => {
        if (storeRun) {
            setRun(storeRun);
        }
    }, [storeRun]);

    useWebSocket({
        runId,
    });

    if (!run) {
        return (
            <MainLayout>
                <div className="flex items-center justify-center h-[calc(100vh-100px)]">
                    <div className="flex flex-col items-center gap-4">
                        <Activity className="h-8 w-8 text-primary animate-pulse" />
                        <p className="text-muted-foreground font-medium">Resolving run session...</p>
                    </div>
                </div>
            </MainLayout>
        );
    }

    return (
        <MainLayout>
            <div className="flex flex-col h-[calc(100vh-100px)] space-y-6">
                {/* Header */}
                <div className="flex items-center justify-between bg-card/30 p-4 rounded-xl border border-border/50 backdrop-blur-md">
                    <div className="flex items-center gap-4">
                        <Link href="/runs">
                            <Button variant="ghost" size="icon" className="hover:bg-primary/10 hover:text-primary">
                                <ArrowLeft className="h-4 w-4" />
                            </Button>
                        </Link>
                        <div>
                            <div className="flex items-center gap-3">
                                <h1 className="text-xl font-bold tracking-tight">Run #{run.id.substring(0, 8)}</h1>
                                <Badge className="uppercase tracking-widest text-[10px] py-0.5" variant={
                                    run.status === 'completed' ? 'success' :
                                        run.status === 'running' ? 'running' :
                                            run.status === 'failed' ? 'destructive' :
                                                'secondary'
                                }>
                                    {run.status}
                                </Badge>
                            </div>
                            <p className="text-xs text-muted-foreground mt-0.5 font-mono">
                                {run.url}
                            </p>
                        </div>
                    </div>

                    <div className="flex items-center gap-2">
                        {run.status === 'running' ? (
                            <Button
                                variant="outline"
                                size="sm"
                                className="bg-background/50 border-orange-500/30 text-orange-500 hover:bg-orange-500/10"
                                onClick={async () => {
                                    try {
                                        await api.post(`/pause/${runId}`);
                                        toast({ title: "Run Paused", description: "Agent activity suspended." });
                                    } catch (e) {
                                        toast({ title: "Action Failed", description: "Could not pause agent.", variant: "destructive" });
                                    }
                                }}
                            >
                                <Pause className="h-4 w-4 mr-2" /> Pause
                            </Button>
                        ) : (
                            <Button
                                variant="outline"
                                size="sm"
                                className="bg-background/50 border-green-500/30 text-green-500 hover:bg-green-500/10"
                                onClick={async () => {
                                    try {
                                        await api.post(`/resume/${runId}`);
                                        toast({ title: "Run Resumed", description: "Agent activity continued." });
                                    } catch (e) {
                                        toast({ title: "Action Failed", description: "Could not resume agent.", variant: "destructive" });
                                    }
                                }}
                            >
                                <Play className="h-4 w-4 mr-2" /> Resume
                            </Button>
                        )}
                        <Button
                            variant="destructive"
                            size="sm"
                            className="bg-red-500/10 border-red-500/30 text-red-500 hover:bg-red-500/20"
                            disabled={run.status !== 'running' && run.status !== 'pending'}
                            onClick={async () => {
                                try {
                                    await api.post(`/abort/${runId}`);
                                    toast({ title: "Run Aborted", description: "Termination sequence initiated." });
                                } catch (e) {
                                    toast({ title: "Action Failed", description: "Could not abort agent.", variant: "destructive" });
                                }
                            }}
                        >
                            <Square className="h-4 w-4 mr-2" /> Abort
                        </Button>
                    </div>
                </div>

                {/* Agent Pipeline Visualizer */}
                <div className="flex-none overflow-x-auto pb-4 custom-scrollbar">
                    <div className="flex items-start gap-0 min-w-max px-2 py-4">
                        {!run ? (
                            AGENT_ORDER.map((_, i) => (
                                <div key={i} className="flex items-center">
                                    <Skeleton className="w-[260px] h-48 rounded-xl opacity-20 mr-4" />
                                    {i < AGENT_ORDER.length - 1 && <Skeleton className="w-12 h-0.5 opacity-10" />}
                                </div>
                            ))
                        ) : AGENT_ORDER.map((agentType, index) => (
                            <div key={agentType} className="flex items-center">
                                <AgentCard
                                    type={agentType}
                                    data={run.agents[agentType] || { type: agentType, status: 'pending' }}
                                    isActive={run.agents[agentType]?.status === 'running'}
                                />

                                {index < AGENT_ORDER.length - 1 && (
                                    <div className="w-12 h-px bg-border/50 relative flex items-center justify-center">
                                        <div className={
                                            `h-1 w-full transition-all duration-1000 ease-in-out ${run.agents[agentType]?.status === 'completed'
                                                ? 'bg-primary shadow-[0_0_10px_rgba(var(--primary),0.5)]'
                                                : 'bg-border/20'
                                            }`
                                        } />
                                        <div className={`absolute right-0 w-2 h-2 rounded-full transform translate-x-1 ${run.agents[agentType]?.status === 'completed' ? 'bg-primary' : 'bg-border/20'
                                            }`} />
                                    </div>
                                )}
                            </div>
                        ))}
                    </div>
                </div>

                {/* Extended Monitoring Partition */}
                <div className="flex-1 grid grid-cols-1 lg:grid-cols-3 gap-6 min-h-0">
                    <Card className="lg:col-span-2 border-none bg-card/30 backdrop-blur-sm overflow-hidden flex flex-col shadow-2xl">
                        <TerminalLog
                            logs={logs.map(l => ({
                                timestamp: l.timestamp,
                                level: l.level as any,
                                message: l.message,
                                agent: l.agent
                            }))}
                            className="flex-1"
                        />
                    </Card>

                    <div className="space-y-6 overflow-y-auto pr-2 custom-scrollbar">
                        <Card className="p-4 border-none bg-card/30 backdrop-blur-sm shadow-xl">
                            <h3 className="text-sm font-bold uppercase tracking-widest text-muted-foreground mb-4">Run Parameters</h3>
                            <div className="space-y-4">
                                <div>
                                    <p className="text-[10px] uppercase font-bold text-muted-foreground/60">Depth Strategy</p>
                                    <p className="text-sm font-mono mt-1">{run.config.crawl_depth} Levels Traverse</p>
                                </div>
                                <div>
                                    <p className="text-[10px] uppercase font-bold text-muted-foreground/60">Failure Policy</p>
                                    <p className="text-sm font-mono mt-1 capitalize">{run.config.failure_policy.onAgentFailure} (Max {run.config.failure_policy.maxRetries} Retries)</p>
                                </div>
                                <div>
                                    <p className="text-[10px] uppercase font-bold text-muted-foreground/60">Auth Bypass</p>
                                    <p className="text-sm font-mono mt-1">{run.config.auth_enabled ? 'Active' : 'Disabled'}</p>
                                </div>
                            </div>
                        </Card>

                        <Card className="p-4 border-none bg-primary/5 border-l-4 border-l-primary shadow-xl">
                            <h3 className="text-sm font-bold uppercase tracking-widest text-primary mb-4 flex items-center gap-2">
                                <Activity className="h-4 w-4" />
                                Real-time Insight
                            </h3>
                            <div className="space-y-1">
                                <p className="text-xl font-bold">{run.successRate || 0}%</p>
                                <p className="text-xs text-muted-foreground">Current Pipeline Stability</p>
                            </div>
                            <div className="mt-4 pt-4 border-t border-primary/10">
                                <div className="flex justify-between items-center text-xs">
                                    <span className="text-muted-foreground">Duration</span>
                                    <span className="font-mono">{(run.totalDuration || 0) / 1000}s</span>
                                </div>
                            </div>
                        </Card>
                    </div>
                </div>
            </div>
        </MainLayout>
    );
}
