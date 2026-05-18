"use client"


import {
    Chart as ChartJS,
    CategoryScale,
    LinearScale,
    BarElement,
    Title,
    Tooltip,
    Legend,
} from "chart.js"
import { Bar } from "react-chartjs-2"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { useRunsStore } from "@/store/runs-store"
import { formatDuration } from "@/lib/utils"

ChartJS.register(
    CategoryScale,
    LinearScale,
    BarElement,
    Title,
    Tooltip,
    Legend
)

const options = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
        legend: {
            display: false,
        },
        tooltip: {
            backgroundColor: "#1b212d",
            titleColor: "#ffffff",
            bodyColor: "#94a3b8",
            borderColor: "#22252e",
            borderWidth: 1,
            callbacks: {
                label: (context: any) => `Duration: ${formatDuration(context.raw)}`
            }
        },
    },
    scales: {
        x: {
            grid: {
                display: false,
            },
            ticks: {
                color: "#94a3b8",
            },
        },
        y: {
            grid: {
                color: "rgba(148, 163, 184, 0.1)",
            },
            ticks: {
                color: "#94a3b8",
                callback: (value: any) => {
                    return value >= 1000 ? `${(value / 1000).toFixed(1)}s` : `${value}ms`;
                },
            },
        },
    },
}

export function DurationChart() {
    const runs = useRunsStore(state => state.runs);

    // Get last 7 completed runs
    const completedRuns = runs
        .filter(r => r.status === 'completed' && r.agents.crawler?.duration)
        .sort((a, b) => new Date(a.createdAt).getTime() - new Date(b.createdAt).getTime())
        .slice(-7);

    const labels = completedRuns.map(r => `#${r.id.substring(0, 4)}`);
    const dataPoints = completedRuns.map(r => r.agents.crawler?.duration || 0);

    const data = {
        labels: labels.length > 0 ? labels : ["No Data"],
        datasets: [
            {
                label: "Duration",
                data: dataPoints.length > 0 ? dataPoints : [0],
                backgroundColor: (context: any) => {
                    const val = context.dataset.data[context.dataIndex];
                    return val > 60000 ? "rgba(239, 68, 68, 0.8)" : "rgba(59, 130, 246, 0.8)";
                },
                borderRadius: 4,
            },
        ],
    }

    return (
        <Card className="border-none bg-card/50 backdrop-blur-sm shadow-xl">
            <CardHeader>
                <CardTitle className="text-base font-medium">Avg. Execution Duration</CardTitle>
            </CardHeader>
            <CardContent>
                <div className="h-[250px]">
                    <Bar options={options} data={data} />
                </div>
            </CardContent>
        </Card>
    )
}
