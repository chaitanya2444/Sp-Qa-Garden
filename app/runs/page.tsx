"use client"

import * as React from "react"
import {
    ColumnDef,
    ColumnFiltersState,
    SortingState,
    VisibilityState,
    flexRender,
    getCoreRowModel,
    getFilteredRowModel,
    getPaginationRowModel,
    getSortedRowModel,
    useReactTable,
} from "@tanstack/react-table"
import { ArrowUpDown, ChevronDown, MoreHorizontal, History, Search, Play, Activity, Clock } from "lucide-react"

import { Button } from "@/components/ui/button"
import {
    DropdownMenu,
    DropdownMenuCheckboxItem,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuLabel,
    DropdownMenuSeparator,
    DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { Input } from "@/components/ui/input"
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from "@/components/ui/table"
import { MainLayout } from "@/components/layout/main-layout"
import { Badge } from "@/components/ui/badge"
import Link from "next/link"
import { formatDate, cn } from "@/lib/utils"
import { Skeleton } from "@/components/ui/skeleton"

export type RunSummary = {
    id: string
    url: string
    status: "pending" | "running" | "completed" | "failed"
    agentsProgress: number
    duration: string
    createdAt: string
}

export const columns: ColumnDef<RunSummary>[] = [
    {
        accessorKey: "id",
        header: ({ column }) => {
            return (
                <Button
                    variant="ghost"
                    size="sm"
                    className="text-[10px] font-bold uppercase tracking-widest hover:bg-transparent p-0"
                    onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}
                >
                    Run Ident
                    <ArrowUpDown className="ml-2 h-3 w-3" />
                </Button>
            )
        },
        cell: ({ row }) => (
            <Link href={`/runs/${row.getValue("id")}`} className="font-mono text-[11px] text-primary hover:text-primary/80 transition-colors uppercase">
                #{row.getValue<string>("id").substring(0, 8)}
            </Link>
        ),
    },
    {
        accessorKey: "url",
        header: "Environment",
        cell: ({ row }) => (
            <div className="flex flex-col">
                <span className="text-sm font-medium tracking-tight truncate max-w-[300px]">{row.getValue<string>("url").replace(/^https?:\/\//, '')}</span>
                <span className="text-[10px] text-muted-foreground font-mono">{row.getValue("url")}</span>
            </div>
        ),
    },
    {
        accessorKey: "status",
        header: "Status",
        cell: ({ row }) => {
            const status = row.getValue("status") as string
            return (
                <Badge
                    className="text-[9px] uppercase font-bold tracking-widest px-2 py-0.5"
                    variant={
                        status === 'completed' ? 'success' :
                            status === 'running' ? 'running' :
                                status === 'failed' ? 'destructive' : 'secondary'
                    }
                >
                    {status}
                </Badge>
            )
        },
    },
    {
        accessorKey: "agentsProgress",
        header: "Execution Progress",
        cell: ({ row }) => {
            const progress = parseFloat(row.getValue("agentsProgress"))
            const status = row.getValue("status") as string
            return (
                <div className="flex items-center gap-3 w-[200px]">
                    <div className="flex-1 h-1.5 bg-muted/30 rounded-full overflow-hidden">
                        <div
                            className={cn(
                                "h-full transition-all duration-500 rounded-full",
                                status === 'completed' ? "bg-green-500" :
                                    status === 'failed' ? "bg-red-500" : "bg-primary shadow-[0_0_8px_rgba(var(--primary),0.5)]"
                            )}
                            style={{ width: `${progress}%` }}
                        />
                    </div>
                    <span className="text-[10px] font-bold font-mono text-muted-foreground w-8">{Math.round(progress)}%</span>
                </div>
            )
        },
    },
    {
        accessorKey: "createdAt",
        header: "Timestamp",
        cell: ({ row }) => (
            <div className="flex items-center gap-2 text-[11px] text-muted-foreground">
                <Clock className="h-3 w-3 opacity-50" />
                {formatDate(row.getValue("createdAt"))}
            </div>
        ),
    },
    {
        accessorKey: "duration",
        header: "Total Time",
        cell: ({ row }) => <div className="font-mono text-[11px]">{row.getValue("duration")}</div>,
    },
    {
        id: "actions",
        enableHiding: false,
        cell: ({ row }) => {
            const run = row.original

            return (
                <div className="text-right">
                    <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                            <Button variant="ghost" className="h-7 w-7 p-0 hover:bg-primary/10 hover:text-primary">
                                <span className="sr-only">Open menu</span>
                                <MoreHorizontal className="h-4 w-4" />
                            </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end" className="bg-card/90 backdrop-blur-md border-border/40">
                            <DropdownMenuLabel className="text-[10px] uppercase font-bold text-muted-foreground tracking-widest">Run Operations</DropdownMenuLabel>
                            <DropdownMenuItem
                                className="text-xs cursor-pointer"
                                onClick={() => navigator.clipboard.writeText(run.id)}
                            >
                                Copy Session ID
                            </DropdownMenuItem>
                            <DropdownMenuSeparator className="bg-border/40" />
                            <DropdownMenuItem className="text-xs cursor-pointer">
                                <Link href={`/runs/${run.id}`} className="w-full">
                                    Analyze Pipeline
                                </Link>
                            </DropdownMenuItem>
                            <DropdownMenuItem className="text-xs cursor-pointer text-destructive focus:text-destructive">Delete Trace</DropdownMenuItem>
                        </DropdownMenuContent>
                    </DropdownMenu>
                </div>
            )
        },
    },
]

// Mock data
const data: RunSummary[] = [
    {
        id: "run-38d9f2",
        url: "https://example.com",
        status: "completed",
        agentsProgress: 100,
        duration: "4m 12s",
        createdAt: new Date().toISOString(),
    },
    {
        id: "run-92a8b1",
        url: "https://staging.app.com",
        status: "running",
        agentsProgress: 65,
        duration: "2m 30s",
        createdAt: new Date(Date.now() - 3600000).toISOString(),
    },
    {
        id: "run-7c3e5d",
        url: "https://demo.platform.io",
        status: "failed",
        agentsProgress: 45,
        duration: "1m 15s",
        createdAt: new Date(Date.now() - 86400000).toISOString(),
    },
]

export default function RunsPage() {
    const [sorting, setSorting] = React.useState<SortingState>([])
    const [columnFilters, setColumnFilters] = React.useState<ColumnFiltersState>([])
    const [columnVisibility, setColumnVisibility] = React.useState<VisibilityState>({})
    const [rowSelection, setRowSelection] = React.useState({})
    const [isLoading, setIsLoading] = React.useState(true)

    React.useEffect(() => {
        const timer = setTimeout(() => setIsLoading(false), 800)
        return () => clearTimeout(timer)
    }, [])

    const table = useReactTable({
        data,
        columns,
        onSortingChange: setSorting,
        onColumnFiltersChange: setColumnFilters,
        getCoreRowModel: getCoreRowModel(),
        getPaginationRowModel: getPaginationRowModel(),
        getSortedRowModel: getSortedRowModel(),
        getFilteredRowModel: getFilteredRowModel(),
        onColumnVisibilityChange: setColumnVisibility,
        onRowSelectionChange: setRowSelection,
        state: {
            sorting,
            columnFilters,
            columnVisibility,
            rowSelection,
        },
    })

    return (
        <MainLayout>
            <div className="w-full space-y-8 max-w-[1600px] mx-auto">
                <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
                    <div>
                        <div className="flex items-center gap-2 mb-1">
                            <History className="h-5 w-5 text-primary" />
                            <h1 className="text-3xl font-bold tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-foreground to-foreground/50">Execution Logs</h1>
                        </div>
                        <p className="text-muted-foreground text-sm">
                            Historical audit trail of all autonomous agent operations.
                        </p>
                    </div>

                    <div className="flex items-center gap-3">
                        <div className="relative w-64 group">
                            <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground/40 group-focus-within:text-primary transition-colors" />
                            <Input
                                placeholder="Search URL signatures..."
                                value={(table.getColumn("url")?.getFilterValue() as string) ?? ""}
                                onChange={(event) =>
                                    table.getColumn("url")?.setFilterValue(event.target.value)
                                }
                                className="pl-8 bg-card/40 border-border/40 focus:ring-1 focus:ring-primary/20"
                            />
                        </div>
                        <Link href="/new-run">
                            <Button className="bg-primary/90 hover:bg-primary shadow-lg shadow-primary/20 group">
                                <Play className="mr-2 h-4 w-4 group-hover:scale-110 transition-transform" />
                                Launch New Agent
                            </Button>
                        </Link>
                    </div>
                </div>

                <div className="rounded-xl border border-border/40 bg-card/30 backdrop-blur-sm shadow-2xl overflow-hidden">
                    <Table>
                        <TableHeader className="bg-muted/50">
                            {table.getHeaderGroups().map((headerGroup) => (
                                <TableRow key={headerGroup.id} className="hover:bg-transparent border-border/40">
                                    {headerGroup.headers.map((header) => {
                                        return (
                                            <TableHead key={header.id} className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground/70 py-4">
                                                {header.isPlaceholder
                                                    ? null
                                                    : flexRender(
                                                        header.column.columnDef.header,
                                                        header.getContext()
                                                    )}
                                            </TableHead>
                                        )
                                    })}
                                </TableRow>
                            ))}
                        </TableHeader>
                        <TableBody>
                            {isLoading ? (
                                Array.from({ length: 5 }).map((_, i) => (
                                    <TableRow key={i} className="border-border/40 hover:bg-transparent">
                                        {columns.map((_, j) => (
                                            <TableCell key={j} className="py-4">
                                                <Skeleton className="h-4 w-full opacity-50" />
                                            </TableCell>
                                        ))}
                                    </TableRow>
                                ))
                            ) : table.getRowModel().rows?.length ? (
                                table.getRowModel().rows.map((row) => (
                                    <TableRow
                                        key={row.id}
                                        data-state={row.getIsSelected() && "selected"}
                                        className="border-border/40 hover:bg-muted/30 transition-colors group"
                                    >
                                        {row.getVisibleCells().map((cell) => (
                                            <TableCell key={cell.id} className="py-2.5">
                                                {flexRender(
                                                    cell.column.columnDef.cell,
                                                    cell.getContext()
                                                )}
                                            </TableCell>
                                        ))}
                                    </TableRow>
                                ))
                            ) : (
                                <TableRow>
                                    <TableCell
                                        colSpan={columns.length}
                                        className="h-32 text-center text-muted-foreground"
                                    >
                                        <div className="flex flex-col items-center gap-2">
                                            <Activity className="h-8 w-8 opacity-20" />
                                            <p className="text-sm font-medium">No execution records found.</p>
                                        </div>
                                    </TableCell>
                                </TableRow>
                            )}
                        </TableBody>
                    </Table>
                </div>

                <div className="flex items-center justify-between py-2">
                    <div className="text-xs text-muted-foreground">
                        Showing {table.getFilteredRowModel().rows.length} records across the cluster
                    </div>
                    <div className="flex items-center space-x-2">
                        <Button
                            variant="outline"
                            size="sm"
                            className="bg-card/40 border-border/40 h-8 text-[11px] font-bold uppercase"
                            onClick={() => table.previousPage()}
                            disabled={!table.getCanPreviousPage()}
                        >
                            Previous
                        </Button>
                        <Button
                            variant="outline"
                            size="sm"
                            className="bg-card/40 border-border/40 h-8 text-[11px] font-bold uppercase"
                            onClick={() => table.nextPage()}
                            disabled={!table.getCanNextPage()}
                        >
                            Next
                        </Button>
                    </div>
                </div>
            </div>
        </MainLayout>
    )
}
