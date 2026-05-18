"use client"

import { Card, CardContent } from "@/components/ui/card"
import { Layers, CheckCircle2, AlertCircle, Bug, TrendingUp, TrendingDown, Activity } from "lucide-react"
import { cn } from "@/lib/utils"
import { useRunsStore } from "@/store/runs-store"

export function KPICards() {
    const runs = useRunsStore(state => state.runs);

    // Dynamic Metrics Calculation
    const totalRuns = runs.length;
    const completedRuns = runs.filter(r => r.status === 'completed').length;
    const failedRuns = runs.filter(r => r.status === 'failed').length;
    const runningRuns = runs.filter(r => r.status === 'running').length;

    // Success Rate Calculation
    const totalFinished = completedRuns + failedRuns;
    const successRate = totalFinished > 0
        ? Math.round((completedRuns / totalFinished) * 100)
        : 0;

    // Determine color based on rate
    const successColor = successRate >= 80 ? "text-green-500" : successRate >= 50 ? "text-yellow-500" : "text-red-500";
    const successBg = successRate >= 80 ? "bg-green-500/10" : successRate >= 50 ? "bg-yellow-500/10" : "bg-red-500/10";

    const metrics = [
        {
            title: "Global Executions",
            value: totalRuns.toLocaleString(),
            label: "Total Pipeline Starts",
            icon: Layers,
            iconColor: "text-blue-500",
            bgColor: "bg-blue-500/10",
        },
        {
            title: "Success Rate",
            value: totalFinished === 0 ? "N/A" : `${successRate}%`,
            label: "Completed vs Failed",
            icon: CheckCircle2,
            iconColor: successColor,
            bgColor: successBg,
        },
        {
            title: "Active Clusters",
            value: runningRuns.toString(),
            label: "Agents Currently Scanning",
            icon: Activity,
            iconColor: "text-primary",
            bgColor: "bg-primary/10",
            animate: runningRuns > 0
        },
        {
            title: "Total Deficiencies",
            value: failedRuns.toString(),
            label: "Aborted or Failed Nodes",
            icon: AlertCircle,
            iconColor: "text-red-500",
            bgColor: "bg-red-500/10",
        },
    ]

    return (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
            {metrics.map((kpi) => {
                const Icon = kpi.icon
                return (
                    <Card key={kpi.title} className="overflow-hidden border-none shadow-lg bg-card/50 backdrop-blur-sm group hover:bg-card/60 transition-all">
                        <CardContent className="p-6">
                            <div className="flex items-center justify-between">
                                <div>
                                    <p className="text-sm font-medium text-muted-foreground uppercase tracking-widest text-[10px]">{kpi.title}</p>
                                    <h3 className="text-2xl font-black mt-1">{kpi.value}</h3>
                                </div>
                                <div className={cn(
                                    "p-3 rounded-xl transition-all group-hover:scale-110",
                                    kpi.bgColor,
                                    kpi.animate && "animate-pulse ring-2 ring-primary/20"
                                )}>
                                    <Icon className={cn("h-5 w-5", kpi.iconColor)} />
                                </div>
                            </div>
                            <div className="mt-4 flex items-center gap-2">
                                <span className="text-[10px] text-muted-foreground uppercase font-bold tracking-tighter">{kpi.label}</span>
                            </div>
                        </CardContent>
                    </Card>
                )
            })}
        </div>
    )
}
