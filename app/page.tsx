"use client"

import { MainLayout } from '@/components/layout/main-layout';
import { KPICards } from '@/components/kpi-cards';
import { ExecutionTrend } from '@/components/charts/execution-trend';
import { SuccessRate } from '@/components/charts/success-rate';
import { DurationChart } from '@/components/charts/duration-chart';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Activity, ArrowRight, ExternalLink, Globe, LayoutDashboard } from 'lucide-react';
import Link from 'next/link';
import { cn, formatDuration } from '@/lib/utils';
import { useRunsStore } from '@/store/runs-store';

export default function Home() {
  const runs = useRunsStore(state => state.runs);

  // Sort by date and take last 5
  const recentRuns = [...runs]
    .sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime())
    .slice(0, 5);

  return (
    <MainLayout>
      <div className="space-y-10 max-w-[1600px] mx-auto">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <LayoutDashboard className="h-5 w-5 text-primary" />
              <h1 className="text-3xl font-bold tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-foreground to-foreground/50">Intelligence Core</h1>
            </div>
            <p className="text-muted-foreground text-sm flex items-center gap-2">
              <span className={cn(
                "inline-block w-2 h-2 rounded-full",
                runs.some(r => r.status === 'running') ? "bg-green-500 animate-pulse" : "bg-muted"
              )} />
              Real-time monitoring of autonomous agent clusters and pipeline efficiency.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <Link href="/new-run">
              <button className="px-4 py-2 rounded-lg bg-primary text-primary-foreground text-sm font-bold uppercase tracking-widest hover:bg-primary/90 transition-all shadow-lg shadow-primary/20 active:scale-95">
                New Execution
              </button>
            </Link>
          </div>
        </div>

        {/* KPI Row */}
        <KPICards />

        {/* Charts Grid */}
        <div className="grid gap-6 grid-cols-1 lg:grid-cols-3">
          <ExecutionTrend />
          <SuccessRate />
        </div>

        <div className="grid gap-6 grid-cols-1 lg:grid-cols-3">
          <DurationChart />

          <Card className="lg:col-span-2 border-border/40 bg-card/30 backdrop-blur-md shadow-2xl overflow-hidden">
            <CardHeader className="flex flex-row items-center justify-between border-b border-border/40 bg-muted/20 py-4">
              <div className="space-y-0.5">
                <CardTitle className="text-sm font-bold uppercase tracking-widest flex items-center gap-2">
                  <Activity className="h-4 w-4 text-primary" />
                  Neural Feed
                </CardTitle>
                <div className="text-[10px] text-muted-foreground uppercase opacity-70">Latest agent stream throughput</div>
              </div>
              <Link href="/runs" className="text-[10px] font-bold uppercase text-primary hover:underline flex items-center gap-1">
                View All <ArrowRight className="h-3 w-3" />
              </Link>
            </CardHeader>
            <CardContent className="p-0">
              <div className="divide-y divide-border/40">
                {recentRuns.length === 0 ? (
                  <div className="p-12 text-center">
                    <Activity className="h-8 w-8 text-muted/20 mx-auto mb-4" />
                    <p className="text-xs text-muted-foreground font-bold uppercase tracking-widest">No Active Streams Detected</p>
                  </div>
                ) : recentRuns.map((run) => (
                  <div key={run.id} className="group flex items-center justify-between p-4 hover:bg-primary/5 transition-colors">
                    <div className="flex items-center gap-4">
                      <div className={cn(
                        "p-2.5 rounded-xl border transition-all duration-300",
                        run.status === 'completed' ? "bg-green-500/10 border-green-500/20 text-green-500" :
                          run.status === 'running' ? "bg-primary/10 border-primary/20 text-primary animate-pulse" :
                            "bg-red-500/10 border-red-500/20 text-red-500"
                      )}>
                        <Globe className="h-4 w-4" />
                      </div>
                      <div className="space-y-1">
                        <p className="text-sm font-semibold tracking-tight group-hover:text-primary transition-colors">{run.url.replace(/^https?:\/\//, '')}</p>
                        <div className="flex items-center gap-2 text-[10px] text-muted-foreground uppercase font-bold tracking-tighter">
                          <span className="font-mono">{run.id}</span>
                          <span className="opacity-30">•</span>
                          <span>{new Date(run.createdAt).toLocaleTimeString()}</span>
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center gap-6">
                      <div className="hidden sm:flex flex-col items-end">
                        <span className="text-[10px] uppercase font-bold text-muted-foreground/50">Run Metrics</span>
                        <span className="text-xs font-mono">{run.agents.crawler?.metrics?.elements || 0} Locators</span>
                      </div>
                      <Badge
                        className="rounded-lg px-3 py-1 text-[9px] uppercase font-bold tracking-widest border-none shadow-sm"
                        variant={
                          run.status === 'completed' ? 'success' :
                            run.status === 'running' ? 'running' :
                              'destructive'
                        }
                      >
                        {run.status}
                      </Badge>
                      <Link href={`/runs/${run.id}`}>
                        <div className="p-2 hover:bg-primary/20 rounded-lg transition-all text-muted-foreground hover:text-primary cursor-pointer">
                          <ExternalLink className="h-4 w-4" />
                        </div>
                      </Link>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </MainLayout>
  );
}

