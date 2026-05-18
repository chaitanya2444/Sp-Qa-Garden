
import { Chart as ChartJS, ArcElement, Tooltip, Legend } from "chart.js"
import { Doughnut } from "react-chartjs-2"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { useRunsStore } from "@/store/runs-store"

ChartJS.register(ArcElement, Tooltip, Legend)

const options = {
    responsive: true,
    maintainAspectRatio: false,
    cutout: "75%",
    plugins: {
        legend: {
            position: "bottom" as const,
            labels: {
                color: "#94a3b8",
                usePointStyle: true,
                pointStyle: "circle",
                padding: 20,
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
}

export function SuccessRate() {
    const runs = useRunsStore(state => state.runs);

    const completed = runs.filter(r => r.status === 'completed').length;
    const failed = runs.filter(r => r.status === 'failed').length;
    const skipped = runs.filter(r => r.status === 'skipped').length;
    const total = completed + failed + skipped;

    const rate = total > 0 ? Math.round((completed / total) * 100) : 0;

    const data = {
        labels: ["Passed", "Failed", "Skipped"],
        datasets: [
            {
                data: total === 0 ? [0, 0, 0] : [completed, failed, skipped],
                backgroundColor: [
                    "rgba(34, 197, 94, 0.8)",
                    "rgba(239, 68, 68, 0.8)",
                    "rgba(234, 179, 8, 0.8)",
                ],
                borderColor: [
                    "rgb(34, 197, 94)",
                    "rgb(239, 68, 68)",
                    "rgb(234, 179, 8)",
                ],
                borderWidth: 1,
            },
        ],
    }

    // Handle empty state visual
    const emptyData = {
        labels: ["No Data"],
        datasets: [{
            data: [1],
            backgroundColor: ["rgba(148, 163, 184, 0.1)"],
            borderColor: ["rgba(148, 163, 184, 0.2)"],
            borderWidth: 1,
        }]
    };

    return (
        <Card className="border-none bg-card/50 backdrop-blur-sm shadow-xl">
            <CardHeader>
                <CardTitle className="text-base font-medium">Global Success Rate</CardTitle>
            </CardHeader>
            <CardContent className="flex flex-col items-center justify-center">
                <div className="h-[250px] w-full relative">
                    <Doughnut options={options} data={total > 0 ? data : emptyData} />
                    <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none pb-8">
                        <span className="text-3xl font-bold">{total > 0 ? `${rate}%` : "N/A"}</span>
                        <span className="text-xs text-muted-foreground">Overall</span>
                    </div>
                </div>
            </CardContent>
        </Card>
    )
}
