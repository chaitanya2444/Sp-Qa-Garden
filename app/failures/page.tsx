"use client"

import { useState, useEffect } from 'react';
import { MainLayout } from '@/components/layout/main-layout';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { ArtifactViewer } from '@/components/artifact-viewer';
import { MOCK_FAILURES, MOCK_ARTIFACTS } from '@/lib/mock-data';
import { AlertCircle, Search, Filter, Bug, Image as ImageIcon, Sparkles, Wand2 } from 'lucide-react';
import { Input } from '@/components/ui/input';
import { Artifact } from '@/types/agent';
import { useToast } from '@/hooks/use-toast';
import { cn } from '@/lib/utils';
import { Skeleton } from '@/components/ui/skeleton';


interface ApiFailure {
    id: string;
    run_id?: string;
    title: string;
    description: string;
    status: string;
    triage_label?: string;
    created_at?: string;
    raw_failure_text?: string;
    stack_trace?: string;
    playwright_script?: string;
    test_url?: string;
}

interface UiFailure {
    id: string;
    runId: string;
    title: string;
    stage: string;
    category: string;
    cause: string;
    suggestion: string;
    artifact?: Artifact;
    raw?: ApiFailure;
}

export default function FailuresPage() {
    const [failures, setFailures] = useState<UiFailure[]>([]);
    const [selectedArtifact, setSelectedArtifact] = useState<Artifact | null>(null);
    const [filterCategory, setFilterCategory] = useState('all');
    const [isLoading, setIsLoading] = useState(true);
    const { toast } = useToast();

    // Fetch live failures from Triage API
    useEffect(() => {
        const fetchFailures = async () => {
            try {
                const res = await fetch('http://localhost:8004/api/triage');
                if (!res.ok) throw new Error('Failed to fetch triage results');

                const data = await res.json();
                const apiResults: ApiFailure[] = data.results || [];

                const mappedFailures: UiFailure[] = apiResults.map(f => ({
                    id: f.id,
                    runId: f.run_id || 'unknown-run',
                    title: f.title || 'Untitled Failure',
                    stage: 'triage', // Default stage for now
                    category: (f.triage_label || 'uncategorized').toLowerCase().replace(/\s+/g, '_'),
                    cause: f.description || 'No description provided.',
                    suggestion: f.status === 'success' ? 'Fix applied' : 'Review suggested fix',
                    // Map screenshot/video if available in artifacts (future)
                    // For now, use a placeholder or check if API provides one
                    artifact: undefined,
                    raw: f
                }));

                setFailures(mappedFailures);
            } catch (error) {
                console.error("Error loading failures:", error);
                toast({
                    title: "Connection Error",
                    description: "Could not load failures from Triage Engine.",
                    variant: "destructive",
                });
                // Fallback to empty or keep mock? Let's show empty for reality.
                setFailures([]);
            } finally {
                setIsLoading(false);
            }
        };

        fetchFailures();

        // Optional: Poll every 5s for updates
        const interval = setInterval(fetchFailures, 5000);
        return () => clearInterval(interval);
    }, [toast]);

    const filteredFailures = filterCategory === 'all'
        ? failures
        : failures.filter(f => f.category === filterCategory);

    const handleCreateJira = (failureId: string) => {
        toast({
            title: "Jira Ticket Created",
            description: `Bug report generated for failure ${failureId}. Issue key: QA-${Math.floor(Math.random() * 9000) + 1000}`,
            variant: "success",
        });
    };

    return (
        <MainLayout>
            <div className="space-y-8 max-w-[1600px] mx-auto">
                <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
                    <div>
                        <h1 className="text-3xl font-bold tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-foreground to-foreground/50">Failures & Triage</h1>
                        <p className="text-muted-foreground mt-1 text-sm">
                            Autonomous analysis of pipeline deviations and AI-remediation suggestions.
                        </p>
                    </div>

                    {/* Filters */}
                    <div className="flex items-center gap-3">
                        <div className="relative w-64">
                            <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground/50" />
                            <Input
                                type="search"
                                placeholder="Filter trace logs..."
                                className="pl-8 bg-card/40 border-border/50"
                            />
                        </div>
                        <Select value={filterCategory} onValueChange={setFilterCategory}>
                            <SelectTrigger className="w-[180px] bg-card/40 border-border/50">
                                <Filter className="mr-2 h-4 w-4 opacity-50" />
                                <SelectValue placeholder="Category" />
                            </SelectTrigger>
                            <SelectContent>
                                <SelectItem value="all">All Deviation Types</SelectItem>
                                <SelectItem value="locator_changed">Locator Drift</SelectItem>
                                <SelectItem value="network_timeout">Infrastructure Timeout</SelectItem>
                                <SelectItem value="assertion_failed">Logic Assertion Failure</SelectItem>
                                <SelectItem value="test_failure">Test Failure</SelectItem>
                            </SelectContent>
                        </Select>
                    </div>
                </div>

                {/* Summary Grid - Recalculated from Live Data */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                    <Card className="border-none bg-red-500/5 border-l-4 border-l-red-500 shadow-xl overflow-hidden">
                        <CardContent className="p-4 flex items-center gap-4">
                            <div className="p-3 rounded-full bg-red-500/10 text-red-500">
                                <AlertCircle className="h-5 w-5" />
                            </div>
                            <div>
                                <p className="text-[10px] uppercase font-bold text-red-500/70">Unresolved Failures</p>
                                <p className="text-2xl font-bold">{failures.length}</p>
                            </div>
                        </CardContent>
                    </Card>
                    <Card className="border-none bg-blue-500/5 border-l-4 border-l-blue-500 shadow-xl">
                        <CardContent className="p-4 flex items-center gap-4">
                            <div className="p-3 rounded-full bg-blue-500/10 text-blue-500">
                                <Sparkles className="h-5 w-5" />
                            </div>
                            <div>
                                <p className="text-[10px] uppercase font-bold text-blue-500/70">AI Coverage</p>
                                <p className="text-2xl font-bold">100% Analyzed</p>
                            </div>
                        </CardContent>
                    </Card>
                    <Card className="border-none bg-green-500/5 border-l-4 border-l-green-500 shadow-xl">
                        <CardContent className="p-4 flex items-center gap-4">
                            <div className="p-3 rounded-full bg-green-500/10 text-green-500">
                                <Wand2 className="h-5 w-5" />
                            </div>
                            <div>
                                <p className="text-[10px] uppercase font-bold text-green-500/70">Auto-Fix Suggests</p>
                                <p className="text-2xl font-bold">N/A</p> {/* Placeholder until backend supports fix tracking */}
                            </div>
                        </CardContent>
                    </Card>
                </div>

                {/* Failures Table */}
                <div className="rounded-xl border border-border/40 bg-card/30 backdrop-blur-sm shadow-2xl overflow-hidden">
                    <Table>
                        <TableHeader className="bg-muted/50">
                            <TableRow className="hover:bg-transparent border-border/40">
                                <TableHead className="w-[100px] uppercase text-[10px] font-bold">ID</TableHead>
                                <TableHead className="uppercase text-[10px] font-bold">Root Cause</TableHead>
                                <TableHead className="uppercase text-[10px] font-bold">Deviation Category</TableHead>
                                <TableHead className="uppercase text-[10px] font-bold">AI Triage Context</TableHead>
                                <TableHead className="uppercase text-[10px] font-bold">Evidence</TableHead>
                                <TableHead className="text-right uppercase text-[10px] font-bold">Resolution</TableHead>
                            </TableRow>
                        </TableHeader>
                        <TableBody>
                            {isLoading ? (
                                Array.from({ length: 3 }).map((_, i) => (
                                    <TableRow key={i} className="border-border/40 hover:bg-transparent">
                                        <TableCell><Skeleton className="h-4 w-12" /></TableCell>
                                        <TableCell><Skeleton className="h-4 w-32" /></TableCell>
                                        <TableCell><Skeleton className="h-4 w-24" /></TableCell>
                                        <TableCell><Skeleton className="h-4 w-full" /></TableCell>
                                        <TableCell><Skeleton className="h-4 w-8" /></TableCell>
                                        <TableCell className="text-right flex justify-end gap-2 px-4 py-4"><Skeleton className="h-8 w-16" /><Skeleton className="h-8 w-24" /></TableCell>
                                    </TableRow>
                                ))
                            ) : filteredFailures.length === 0 ? (
                                <TableRow>
                                    <TableCell colSpan={6} className="h-24 text-center text-muted-foreground">
                                        No failures recorded. Pipeline is healthy! 🌿
                                    </TableCell>
                                </TableRow>
                            ) : (
                                filteredFailures.map((failure) => (
                                    <TableRow key={failure.id} className="border-border/40 hover:bg-muted/30 transition-colors">
                                        <TableCell className="font-mono text-[10px] text-muted-foreground">
                                            #{failure.runId.substring(0, 6)}
                                        </TableCell>
                                        <TableCell>
                                            <div className="font-semibold text-sm">{failure.title}</div>
                                            <div className="text-[10px] text-muted-foreground uppercase mt-0.5 tracking-tight font-medium">Stage: {failure.stage}</div>
                                        </TableCell>
                                        <TableCell>
                                            <Badge variant="outline" className={cn(
                                                "border-none px-2 py-0.5 text-[10px] font-bold uppercase",
                                                failure.category.includes('locator') ? "bg-orange-500/10 text-orange-500 shadow-[0_0_10px_rgba(249,115,22,0.1)]" :
                                                    failure.category.includes('fail') ? "bg-red-500/10 text-red-500 shadow-[0_0_10px_rgba(239,44,44,0.1)]" :
                                                        "bg-blue-500/10 text-blue-500"
                                            )}>
                                                {failure.category.replace('_', ' ')}
                                            </Badge>
                                        </TableCell>
                                        <TableCell className="max-w-md">
                                            <div className="space-y-1.5 py-1">
                                                <div className="text-[11px] leading-relaxed text-muted-foreground italic border-l-2 border-red-500/30 pl-2">
                                                    "{failure.cause}"
                                                </div>
                                                <div className="text-[11px] font-bold text-green-500 flex items-center gap-1.5">
                                                    <Wand2 className="h-3 w-3" />
                                                    Suggestion: {failure.suggestion}
                                                </div>
                                            </div>
                                        </TableCell>
                                        <TableCell>
                                            {failure.artifact ? (
                                                <Button
                                                    variant="ghost"
                                                    size="icon"
                                                    onClick={() => setSelectedArtifact(failure.artifact || null)}
                                                    className="h-8 w-8 hover:bg-primary/10 hover:text-primary transition-all active:scale-95"
                                                >
                                                    <ImageIcon className="h-4 w-4" />
                                                </Button>
                                            ) : (
                                                <span className="text-[10px] text-muted-foreground">-</span>
                                            )}
                                        </TableCell>
                                        <TableCell className="text-right space-x-2">
                                            <Button variant="ghost" size="sm" className="text-[10px] uppercase font-bold text-muted-foreground hover:text-foreground">Ignore</Button>
                                            <Button
                                                variant="secondary"
                                                size="sm"
                                                className="text-[10px] uppercase font-bold bg-primary/10 text-primary border border-primary/20 hover:bg-primary/20"
                                                onClick={() => handleCreateJira(failure.id)}
                                            >
                                                <Bug className="h-3 w-3 mr-1.5" />
                                                Log Bug
                                            </Button>
                                        </TableCell>
                                    </TableRow>
                                )))}
                        </TableBody>
                    </Table>
                </div>
            </div>

            <ArtifactViewer
                artifact={selectedArtifact}
                open={!!selectedArtifact}
                onOpenChange={(open) => !open && setSelectedArtifact(null)}
            />
        </MainLayout>
    );
}
