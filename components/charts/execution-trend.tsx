"use client"


import {
    Chart as ChartJS,
    CategoryScale,
    LinearScale,
    PointElement,
    LineElement,
    Title,
    Tooltip,
    Legend,
    Filler,
} from "chart.js"
import { Line } from "react-chartjs-2"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { useRunsStore } from "@/store/runs-store"

ChartJS.register(
    CategoryScale,
    LinearScale,
    PointElement,
    LineElement,
    Title,
    Tooltip,
    Legend,
    Filler
)

const options = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
        legend: {
            position: "top" as const,
            labels: {
                color: "#94a3b8",
                usePointStyle: true,
                pointStyle: "circle",
            },
        },
        tooltip: {
            backgroundColor: "#1b212d",
            titleColor: "#ffffff",
            bodyColor: "#94a3b8",
            borderColor: "#22252e",
            borderWidth: 1,
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
                precision: 0
            },
        },
    },
}

export function ExecutionTrend() {
    const runs = useRunsStore(state => state.runs);

    // Group runs by date (Last 7 days)
    const last7Days = Array.from({ length: 7 }, (_, i) => {
        const d = new Date();
        d.setDate(d.getDate() - (6 - i));
        return d.toLocaleDateString('en-US', { weekday: 'short' }); // Mon, Tue...
    });

    const datasetTotal = new Array(7).fill(0);
    const datasetFailures = new Array(7).fill(0);

    runs.forEach(run => {
        const runDate = new Date(run.createdAt);
        const dayName = runDate.toLocaleDateString('en-US', { weekday: 'short' });

        // Find index in last7Days (basic matching, assumes current week context for now)
        const index = last7Days.indexOf(dayName);
        if (index !== -1) {
            datasetTotal[index]++;
            if (run.status === 'failed') {
                datasetFailures[index]++;
            }
        }
    });

    const data = {
        labels: last7Days,
        datasets: [
            {
                label: "Total Tests",
                data: datasetTotal,
                borderColor: "rgb(59, 130, 246)",
                backgroundColor: "rgba(59, 130, 246, 0.1)",
                fill: true,
                tension: 0.4,
            },
            {
                label: "Failures",
                data: datasetFailures,
                borderColor: "rgb(239, 68, 68)",
                backgroundColor: "rgba(239, 68, 68, 0.1)",
                fill: true,
                tension: 0.4,
            },
        ],
    }

    return (
        <Card className="border-none bg-card/50 backdrop-blur-sm shadow-xl col-span-2">
            <CardHeader>
                <CardTitle className="text-base font-medium">Execution Trend (Session)</CardTitle>
            </CardHeader>
            <CardContent>
                <div className="h-[300px]">
                    <Line options={options} data={data} />
                </div>
            </CardContent>
        </Card>
    )
}
