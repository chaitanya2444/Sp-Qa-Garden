"use client"

import { useState } from 'react';
import { MainLayout } from '@/components/layout/main-layout';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Slider } from '@/components/ui/slider';
import { Switch } from '@/components/ui/switch';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { PlayCircle, Settings2, Loader2, Zap, ShieldCheck, Globe } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { api } from '@/lib/api';
import { useToast } from '@/hooks/use-toast';
import { cn } from '@/lib/utils';
import axios from 'axios';
import { useRunsStore } from '@/store/runs-store';
import { Run } from '@/types/run';
import { AgentData } from '@/types/agent';

export default function NewRunPage() {
    const router = useRouter();
    const { toast } = useToast();
    const addRun = useRunsStore(state => state.addRun);
    const [url, setUrl] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [crawlDepth, setCrawlDepth] = useState([3]);
    const [maxPages, setMaxPages] = useState(50);
    const [formInteractions, setFormInteractions] = useState(true);
    const [authEnabled, setAuthEnabled] = useState(false);
    const [failurePolicy, setFailurePolicy] = useState<'stop' | 'continue' | 'retry'>('stop');
    const [maxRetries, setMaxRetries] = useState(3);
    const [extremeMode, setExtremeMode] = useState(false);

    const handleWakeUp = async () => {
        setIsLoading(true);
        try {
            await axios.post('/api/orchestrate/start');
            toast({
                title: "Boot Sequence Initiated",
                description: "Crawler cluster is waking up. Please wait 5 seconds and initiate sequence again.",
                variant: "success",
            });
        } catch (err) {
            toast({
                title: "Wake Up Failed",
                description: "Could not auto-start crawler. Please start Python manually.",
                variant: "destructive",
            });
        } finally {
            setIsLoading(false);
        }
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setIsLoading(true);

        const finalDepth = extremeMode ? 999 : crawlDepth[0];
        const finalPages = extremeMode ? 1000 : maxPages;

        try {
            const response = await api.post('/crawl', {
                url,
                max_depth: finalDepth,
                max_pages: finalPages,
                failure_policy: failurePolicy,
                max_retries: maxRetries,
                auth_enabled: authEnabled, // Keeping these as they might be handled by crawler even if not in explicit schema (or schema was partial)
                form_interactions: formInteractions,
            });


            const { run_id } = response.data;

            // Initialize the run in global store
            const newRun: Run = {
                id: run_id,
                url: url,
                status: 'running',
                createdAt: new Date().toISOString(),
                startedAt: new Date().toISOString(),
                config: {
                    crawl_depth: finalDepth,
                    max_pages: finalPages,
                    auth_enabled: authEnabled,
                    failure_policy: {
                        onAgentFailure: failurePolicy,
                        maxRetries: maxRetries
                    }
                },
                agents: {
                    crawler: {
                        type: 'crawler',
                        status: 'running',
                        progress: 0,
                        inputs: { url, depth: finalDepth, max_pages: finalPages }
                    },
                    test_generator: { type: 'test_generator', status: 'pending', progress: 0 },
                    script_generator: { type: 'script_generator', status: 'pending', progress: 0 },
                    executor: { type: 'executor', status: 'pending', progress: 0 },
                    triage: { type: 'triage', status: 'pending', progress: 0 },
                    jira: { type: 'jira', status: 'pending', progress: 0 },
                }
            };
            addRun(newRun);

            toast({
                title: "Agent Deployment Initiated",
                description: `Neural crawl launched for ${url}. Handing over to pipeline...`,
                variant: "success",
            });

            router.push(`/runs/${run_id}`);
        } catch (error: any) {
            console.error('Failed to start run:', error);
            const isConnectionError = !error.response;

            toast({
                title: "Launch Sequence Failed",
                description: (
                    <div className="flex flex-col gap-3">
                        <p>{isConnectionError ? "Autonomous cluster unreachable (Backend is Offline)." : (error.response?.data?.message || "Internal Agent Error")}</p>
                        {isConnectionError && (
                            <Button
                                variant="outline"
                                size="sm"
                                className="w-full bg-primary/20 hover:bg-primary/30 border-primary/50 text-foreground text-[10px] font-bold uppercase"
                                onClick={handleWakeUp}
                            >
                                <Zap className="h-3 w-3 mr-2 fill-primary" />
                                Wake Up Agent Automatically
                            </Button>
                        )}
                    </div>
                ),
                variant: "destructive",
            });
        } finally {
            setIsLoading(false);
        }
    };

    const isValidUrl = url.length === 0 || /^https?:\/\//.test(url);

    return (
        <MainLayout>
            <div className="max-w-5xl mx-auto space-y-10 pb-16 px-4">
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 border-b border-border/40 pb-8">
                    <div className="space-y-1">
                        <div className="flex items-center gap-2">
                            <Zap className="h-6 w-6 text-primary fill-primary/20" />
                            <h1 className="text-4xl font-black tracking-tighter bg-clip-text text-transparent bg-gradient-to-br from-foreground to-foreground/40">Deploy Pipeline</h1>
                        </div>
                        <p className="text-muted-foreground text-sm font-medium">
                            Configure semantic crawling and autonomous test generation parameters.
                        </p>
                    </div>
                </div>

                <form onSubmit={handleSubmit} className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                    <div className="lg:col-span-2 space-y-8">
                        {/* URL Input */}
                        <Card className="border-border/40 bg-card/30 backdrop-blur-xl shadow-2xl relative overflow-hidden group">
                            <div className="absolute top-0 right-0 p-4 opacity-5 group-hover:opacity-10 transition-opacity">
                                <Globe className="h-24 w-24" />
                            </div>
                            <CardHeader>
                                <CardTitle className="text-sm font-bold uppercase tracking-widest text-primary/60">Target Environment</CardTitle>
                                <CardDescription className="text-xs">Specify the entry point for the autonomous agent swarm</CardDescription>
                            </CardHeader>
                            <CardContent>
                                <div className="space-y-4">
                                    <div className="relative">
                                        <Input
                                            id="url"
                                            type="url"
                                            placeholder="https://staging.app.com/login"
                                            value={url}
                                            onChange={(e) => setUrl(e.target.value)}
                                            className="text-xl h-16 bg-background/40 border-border/40 focus:border-primary/50 focus:ring-1 focus:ring-primary/20 pl-4 pr-12 font-semibold"
                                            required
                                        />
                                        <div className="absolute right-4 top-1/2 -translate-y-1/2">
                                            {isValidUrl && url && (
                                                <ShieldCheck className="h-6 w-6 text-green-500/50" />
                                            )}
                                        </div>
                                    </div>
                                    {!isValidUrl && (
                                        <div className="flex items-center gap-2 text-[10px] font-bold text-red-500 uppercase tracking-tighter bg-red-500/10 p-2 rounded border border-red-500/20">
                                            <span>Invalid Protocol: Ensure URL starts with http:// or https://</span>
                                        </div>
                                    )}
                                </div>
                            </CardContent>
                        </Card>

                        <Card className="border-border/40 bg-card/30 backdrop-blur-xl shadow-2xl">
                            <CardHeader className="flex flex-row items-center justify-between pb-2">
                                <div className="space-y-1">
                                    <CardTitle className="text-sm font-bold uppercase tracking-widest text-primary/60">Neural Scanning Depth</CardTitle>
                                    <CardDescription className="text-xs">Define the semantic reach of the crawler</CardDescription>
                                </div>
                                <div className="flex items-center gap-2 bg-primary/10 px-3 py-1.5 rounded-full border border-primary/20 transition-all">
                                    <Zap className={cn("h-3.5 w-3.5 text-primary", extremeMode && "animate-pulse")} />
                                    <span className="text-[10px] font-bold text-primary uppercase">Extreme Mode</span>
                                    <Switch
                                        checked={extremeMode}
                                        onCheckedChange={setExtremeMode}
                                        className="data-[state=checked]:bg-primary"
                                    />
                                </div>
                            </CardHeader>
                            <CardContent className="space-y-10 pt-4">
                                {/* Crawl Depth */}
                                <div className={cn("space-y-6 transition-all duration-500", extremeMode && "opacity-40 grayscale pointer-events-none")}>
                                    <div className="space-y-4">
                                        <div className="flex items-center justify-between">
                                            <Label className="text-xs font-bold uppercase tracking-widest opacity-70">Traversal Depth</Label>
                                            <Badge variant="secondary" className="px-4 py-1.5 font-mono text-xs bg-muted/50 border border-border/40">{extremeMode ? 999 : crawlDepth[0]}</Badge>
                                        </div>
                                        <Slider
                                            value={crawlDepth}
                                            onValueChange={setCrawlDepth}
                                            min={1}
                                            max={15}
                                            step={1}
                                            className="[&_.relative]:h-1.5"
                                        />
                                        <p className="text-[10px] text-muted-foreground uppercase tracking-tight">How many link layers the agent should penetrate</p>
                                    </div>

                                    {/* Max Pages */}
                                    <div className="space-y-4">
                                        <div className="flex items-center justify-between">
                                            <Label className="text-xs font-bold uppercase tracking-widest opacity-70">Page Threshold</Label>
                                            <Badge variant="secondary" className="px-4 py-1.5 font-mono text-xs bg-muted/50 border border-border/40">{extremeMode ? 1000 : maxPages}</Badge>
                                        </div>
                                        <Slider
                                            value={[maxPages]}
                                            onValueChange={(v) => setMaxPages(v[0])}
                                            min={10}
                                            max={1000}
                                            step={10}
                                            className="[&_.relative]:h-1.5"
                                        />
                                        <p className="text-[10px] text-muted-foreground uppercase tracking-tight">Total unique URL nodes to index before termination</p>
                                    </div>
                                </div>

                                {extremeMode && (
                                    <div className="py-6 px-4 rounded-xl bg-orange-500/10 border border-orange-500/20 flex flex-col items-center gap-3 text-center animate-in zoom-in-95">
                                        <Zap className="h-8 w-8 text-orange-500" />
                                        <div className="space-y-1">
                                            <p className="text-xs font-black uppercase text-orange-500 tracking-widest">Extreme Coverage Active</p>
                                            <p className="text-[10px] text-orange-500/70 font-medium">Agent will attempt to map up to 1,000 pages with 999 depth levels.</p>
                                        </div>
                                    </div>
                                )}

                                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                                    <div className="flex items-center justify-between p-5 rounded-xl bg-muted/20 border border-border/40 hover:bg-muted/30 transition-all group">
                                        <div className="space-y-1">
                                            <Label className="text-xs font-bold uppercase tracking-widest group-hover:text-foreground transition-colors">Semantic Forms</Label>
                                            <p className="text-[10px] text-muted-foreground">Autonomous input generation</p>
                                        </div>
                                        <Switch
                                            checked={formInteractions}
                                            onCheckedChange={setFormInteractions}
                                        />
                                    </div>

                                    <div className="flex items-center justify-between p-5 rounded-xl bg-muted/20 border border-border/40 hover:bg-muted/30 transition-all group">
                                        <div className="space-y-1">
                                            <Label className="text-xs font-bold uppercase tracking-widest group-hover:text-foreground transition-colors">Auth Bypass</Label>
                                            <p className="text-[10px] text-muted-foreground">Shadow session injection</p>
                                        </div>
                                        <Switch
                                            checked={authEnabled}
                                            onCheckedChange={setAuthEnabled}
                                        />
                                    </div>
                                </div>
                            </CardContent>
                        </Card>
                    </div>

                    <div className="space-y-6">
                        <Card className="border-border/40 bg-primary/5 shadow-2xl overflow-hidden relative">
                            <div className="absolute inset-0 bg-gradient-to-b from-primary/10 to-transparent pointer-events-none" />
                            <CardHeader>
                                <CardTitle className="text-sm font-bold uppercase tracking-widest text-primary flex items-center gap-2">
                                    <Settings2 className="h-4 w-4" />
                                    Orchestration
                                </CardTitle>
                                <CardDescription className="text-[10px] uppercase font-bold text-muted-foreground/60">Execution Fail-Safes</CardDescription>
                            </CardHeader>
                            <CardContent className="space-y-8 relative z-10">
                                {/* Failure Policy */}
                                <div className="space-y-4">
                                    <Label className="text-[10px] uppercase tracking-widest text-muted-foreground font-black">Agent Drop Policy</Label>
                                    <Select value={failurePolicy} onValueChange={(v: any) => setFailurePolicy(v)}>
                                        <SelectTrigger className="bg-background/50 border-border/40 text-sm h-11 font-medium ring-offset-primary">
                                            <SelectValue />
                                        </SelectTrigger>
                                        <SelectContent className="bg-card/95 border-border/40">
                                            <SelectItem value="stop" className="text-xs font-bold uppercase tracking-tight">Halt Entire Pipeline</SelectItem>
                                            <SelectItem value="continue" className="text-xs font-bold uppercase tracking-tight">Ignore & Proceed</SelectItem>
                                            <SelectItem value="retry" className="text-xs font-bold uppercase tracking-tight">Recursive Auto-Retry</SelectItem>
                                        </SelectContent>
                                    </Select>
                                </div>

                                {failurePolicy === 'retry' && (
                                    <div className="space-y-5 animate-in fade-in slide-in-from-top-4">
                                        <div className="flex items-center justify-between">
                                            <Label className="text-[10px] uppercase font-black text-primary tracking-widest">Max Iterations</Label>
                                            <Badge variant="outline" className="border-primary/50 text-primary font-mono text-[10px]">{maxRetries}</Badge>
                                        </div>
                                        <Slider
                                            value={[maxRetries]}
                                            onValueChange={(v) => setMaxRetries(v[0])}
                                            min={1}
                                            max={5}
                                            step={1}
                                            className="[&_.relative]:h-1"
                                        />
                                    </div>
                                )}
                            </CardContent>
                        </Card>

                        <div className="pt-4 flex flex-col gap-6">
                            <Button
                                type="submit"
                                size="lg"
                                className="w-full h-20 text-md font-black uppercase tracking-[0.2em] shadow-[0_20px_50px_rgba(var(--primary),0.3)] transition-all hover:scale-[1.03] active:scale-[0.98] group relative overflow-hidden"
                                disabled={!isValidUrl || !url || isLoading}
                            >
                                <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/10 to-transparent -translate-x-full group-hover:animate-shimmer" />
                                {isLoading ? (
                                    <Loader2 className="mr-3 h-6 w-6 animate-spin" />
                                ) : (
                                    <PlayCircle className="mr-3 h-6 w-6 group-hover:rotate-12 transition-transform" />
                                )}
                                {isLoading ? 'Deploying swarm...' : 'Initiate Sequence'}
                            </Button>

                            <div className="bg-muted/10 border border-border/40 p-4 rounded-xl flex items-start gap-3">
                                <ShieldCheck className="h-4 w-4 text-green-500/50 shrink-0 mt-0.5" />
                                <p className="text-[9px] text-muted-foreground font-medium uppercase leading-relaxed tracking-tight">
                                    By deploying, you acknowledge that the autonomous swarm will execute real-time interactions including form submissions, navigation traversals, and semantic analysis on the specified environment.
                                </p>
                            </div>
                        </div>
                    </div>
                </form>
            </div>
        </MainLayout>
    );
}
