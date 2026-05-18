"use client"

import { useState } from 'react';
import { AgentData, AgentType, AGENT_LABELS, AGENT_DESCRIPTIONS, Artifact } from '@/types/agent';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Button } from '@/components/ui/button';
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from '@/components/ui/accordion';
import { JsonViewer } from '@/components/json-viewer';
import { ArtifactViewer } from '@/components/artifact-viewer';
import { formatDuration, cn } from '@/lib/utils';
import { FileIcon, ImageIcon, VideoIcon, FileText, AlertCircle, CheckCircle2, Clock, Terminal, Activity } from 'lucide-react';

interface AgentCardProps {
    type: AgentType;
    data: AgentData;
    isActive?: boolean;
}

export function AgentCard({ type, data, isActive }: AgentCardProps) {
    const [selectedArtifact, setSelectedArtifact] = useState<Artifact | null>(null);

    const getStatusVariant = (status: string) => {
        switch (status) {
            case 'completed': return 'success';
            case 'failed': return 'destructive';
            case 'running': return 'running';
            default: return 'secondary';
        }
    };

    const getArtifactIcon = (type: string) => {
        switch (type) {
            case 'video': return <VideoIcon className="h-3.5 w-3.5" />;
            case 'screenshot': return <ImageIcon className="h-3.5 w-3.5" />;
            case 'json': return <FileIcon className="h-3.5 w-3.5" />;
            default: return <FileText className="h-3.5 w-3.5" />;
        }
    };

    return (
        <div className={cn(
            "w-[260px] shrink-0 transition-all duration-300",
            isActive ? "scale-[1.02] z-10" : "opacity-90 hover:opacity-100"
        )}>
            <div className={cn(
                "group relative border-none rounded-xl bg-card/40 backdrop-blur-md shadow-2xl overflow-hidden transition-all",
                isActive ? "ring-2 ring-primary bg-card/60" : "hover:bg-card/50"
            )}>
                {/* Status Indicator Bar */}
                <div className={cn(
                    "h-1 w-full",
                    data.status === 'completed' ? "bg-green-500" :
                        data.status === 'failed' ? "bg-red-500" :
                            data.status === 'running' ? "bg-primary animate-pulse" : "bg-border/30"
                )} />

                <div className="p-4">
                    <div className="flex items-center justify-between mb-3">
                        <div className="flex items-center gap-2">
                            <div className={cn(
                                "w-2.5 h-2.5 rounded-full",
                                data.status === 'completed' ? "bg-green-500 shadow-[0_0_8px_rgba(34,197,94,0.6)]" :
                                    data.status === 'failed' ? "bg-red-500 shadow-[0_0_8px_rgba(239,44,44,0.6)]" :
                                        data.status === 'running' ? "bg-primary animate-ping" : "bg-muted-foreground/30"
                            )} />
                            <span className="text-[11px] font-bold uppercase tracking-tighter text-muted-foreground">
                                {AGENT_LABELS[type]}
                            </span>
                        </div>
                        <Badge
                            className="text-[9px] h-4 px-1.5 uppercase font-bold"
                            variant={getStatusVariant(data.status)}
                        >
                            {data.status}
                        </Badge>
                    </div>

                    <h4 className="text-xs font-semibold mb-2 line-clamp-1 group-hover:text-primary transition-colors">
                        {AGENT_DESCRIPTIONS[type]}
                    </h4>

                    <div className="space-y-2 mt-4">
                        <div className="flex justify-between items-center">
                            <span className="text-[10px] text-muted-foreground font-mono">Process Heat</span>
                            <span className="text-[10px] font-bold">{Math.round(data.progress || 0)}%</span>
                        </div>
                        <Progress value={data.progress} className="h-1 bg-muted/20" />
                    </div>

                    {/* Real-time Metrics Section */}
                    {data.metrics && (
                        <div className="mt-4 pt-4 border-t border-border/10 space-y-2">
                            <div className="grid grid-cols-2 gap-2">
                                {(() => {
                                    const getMetricsConfig = () => {
                                        switch (type) {
                                            case 'crawler':
                                                return [
                                                    { label: 'Locators', value: data.metrics?.elements || 0 },
                                                    { label: 'Pages', value: data.metrics?.finished || data.metrics?.page_count || 0 }
                                                ];
                                            case 'test_generator':
                                                return [
                                                    { label: 'Test Cases', value: data.metrics?.test_cases || 0 },
                                                    { label: 'Pages', value: data.metrics?.pages || 0 }
                                                ];
                                            case 'script_generator':
                                                return [
                                                    { label: 'Scripts Generated', value: data.metrics?.scripts_generated || 0 },
                                                    { label: 'Pages', value: data.metrics?.pages_covered || 0 }
                                                ];
                                            case 'executor':
                                                return [
                                                    { label: 'Passed', value: data.metrics?.passed || 0, color: 'text-green-500' },
                                                    { label: 'Failed', value: data.metrics?.failed || 0, color: 'text-red-500' }
                                                ];
                                            case 'triage':
                                                return [
                                                    { label: 'Bugs Analyzed', value: data.metrics?.bugs_analyzed || 0 },
                                                    { label: 'Fixes Proposed', value: data.metrics?.fixes_proposed || 0 }
                                                ];
                                            default:
                                                return [
                                                    { label: 'Items', value: Object.values(data.metrics || {})[0] || 0 },
                                                    { label: 'Status', value: 'Active' }
                                                ];
                                        }
                                    };

                                    return getMetricsConfig().map((metric, idx) => (
                                        <div key={idx} className="p-2 bg-muted/10 rounded-lg">
                                            <p className="text-[8px] uppercase font-bold text-muted-foreground/60">
                                                {metric.label}
                                            </p>
                                            <p className={cn("text-xs font-bold", (metric as any).color || "text-primary")}>
                                                {metric.value}
                                            </p>
                                        </div>
                                    ));
                                })()}
                            </div>
                            {data.metrics.current_url && (
                                <p className="text-[9px] text-muted-foreground/60 truncate font-mono">
                                    {data.metrics.current_url.replace(/^https?:\/\//, '')}
                                </p>
                            )}
                        </div>
                    )}

                    {data.duration && (
                        <div className="mt-3 flex items-center justify-between text-[10px] text-muted-foreground/60 font-mono">
                            <div className="flex items-center gap-1">
                                <Clock className="h-3 w-3" />
                                {formatDuration(data.duration)}
                            </div>
                            {isActive && <Activity className="h-3 w-3 animate-pulse text-primary" />}
                        </div>
                    )}
                </div>

                <Accordion type="single" collapsible className="w-full border-t border-border/20">
                    <AccordionItem value="details" className="border-0">
                        <AccordionTrigger className="px-4 py-2 text-[10px] text-muted-foreground hover:no-underline hover:text-foreground">
                            <div className="flex items-center gap-2">
                                <Terminal className="h-3 w-3" />
                                Inspect Agent State
                            </div>
                        </AccordionTrigger>
                        <AccordionContent className="px-4 pb-4">
                            <div className="space-y-4 pt-1">
                                {/* Artifacts Summary */}
                                {data.artifacts && data.artifacts.length > 0 && (
                                    <div className="space-y-2">
                                        <div className="flex flex-wrap gap-1.5">
                                            {data.artifacts.map((artifact) => (
                                                <Button
                                                    key={artifact.id}
                                                    variant="secondary"
                                                    size="sm"
                                                    className="h-7 px-2 text-[10px] bg-muted/30 hover:bg-primary/20 hover:text-primary border-none"
                                                    onClick={() => setSelectedArtifact(artifact)}
                                                >
                                                    {getArtifactIcon(artifact.type)}
                                                    <span className="ml-1.5 max-w-[80px] truncate">{artifact.name}</span>
                                                </Button>
                                            ))}
                                        </div>
                                    </div>
                                )}

                                {data.error && (
                                    <div className="p-2 text-[10px] bg-red-500/10 text-red-400 rounded-lg border border-red-500/20 font-mono">
                                        {data.error}
                                    </div>
                                )}

                                <div className="space-y-2">
                                    <p className="text-[9px] uppercase font-bold text-muted-foreground/50">Agent I/O</p>
                                    <JsonViewer data={{ ...data.inputs, ...data.outputs, metrics: data.metrics }} className="max-h-24 text-[9px]" />
                                </div>
                            </div>
                        </AccordionContent>
                    </AccordionItem>
                </Accordion>
            </div>

            <ArtifactViewer
                artifact={selectedArtifact}
                open={!!selectedArtifact}
                onOpenChange={(open) => !open && setSelectedArtifact(null)}
            />
        </div>
    );
}
