"use client"

import { useState, useEffect } from 'react';
import { MainLayout } from '@/components/layout/main-layout';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { MOCK_JIRA_BUGS } from '@/lib/mock-data';
import { Bug, ExternalLink, Link as LinkIcon, ShieldAlert } from 'lucide-react';
import Link from 'next/link';
import { cn } from '@/lib/utils';
import { Skeleton } from '@/components/ui/skeleton';

export default function JiraPage() {
    const [isLoading, setIsLoading] = useState(true);

    useEffect(() => {
        const timer = setTimeout(() => setIsLoading(false), 800);
        return () => clearTimeout(timer);
    }, []);

    return (
        <MainLayout>
            <div className="space-y-8 max-w-[1200px] mx-auto">
                <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
                    <div>
                        <h1 className="text-3xl font-bold tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-foreground to-foreground/50">Jira Sync</h1>
                        <p className="text-muted-foreground mt-1 text-sm">
                            Synchronized lifecycle of AI-detected regressions and engineering tasking.
                        </p>
                    </div>

                    <div className="flex items-center gap-2">
                        <div className="px-3 py-1 rounded-full bg-green-500/10 border border-green-500/20 flex items-center gap-2">
                            <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
                            <span className="text-[10px] font-bold uppercase text-green-500">Sync Status: Active</span>
                        </div>
                    </div>
                </div>

                <div className="rounded-xl border border-border/40 bg-card/30 backdrop-blur-sm shadow-2xl overflow-hidden">
                    <Table>
                        <TableHeader className="bg-muted/50">
                            <TableRow className="hover:bg-transparent border-border/40">
                                <TableHead className="w-[120px] uppercase text-[10px] font-bold">Ticket Key</TableHead>
                                <TableHead className="uppercase text-[10px] font-bold">Summary</TableHead>
                                <TableHead className="uppercase text-[10px] font-bold">Priority</TableHead>
                                <TableHead className="uppercase text-[10px] font-bold">Workflow</TableHead>
                                <TableHead className="uppercase text-[10px] font-bold">Assignee</TableHead>
                                <TableHead className="uppercase text-[10px] font-bold">Source Run</TableHead>
                                <TableHead className="text-right uppercase text-[10px] font-bold">External</TableHead>
                            </TableRow>
                        </TableHeader>
                        <TableBody>
                            {isLoading ? (
                                Array.from({ length: 4 }).map((_, i) => (
                                    <TableRow key={i} className="border-border/40 hover:bg-transparent">
                                        <TableCell><Skeleton className="h-4 w-16" /></TableCell>
                                        <TableCell><Skeleton className="h-4 w-full" /></TableCell>
                                        <TableCell><Skeleton className="h-4 w-20" /></TableCell>
                                        <TableCell><Skeleton className="h-4 w-16" /></TableCell>
                                        <TableCell><Skeleton className="h-5 w-5 rounded-full" /></TableCell>
                                        <TableCell><Skeleton className="h-4 w-12" /></TableCell>
                                        <TableCell><Skeleton className="h-8 w-8 rounded-md float-right" /></TableCell>
                                    </TableRow>
                                ))
                            ) : MOCK_JIRA_BUGS.map((bug) => (
                                <TableRow key={bug.id} className="border-border/40 hover:bg-muted/30 transition-colors">
                                    <TableCell className="font-bold text-primary text-xs">
                                        <div className="flex items-center gap-2">
                                            <Bug className="h-3.5 w-3.5" />
                                            {bug.id}
                                        </div>
                                    </TableCell>
                                    <TableCell>
                                        <div className="font-medium text-sm leading-tight text-foreground/90">{bug.summary}</div>
                                    </TableCell>
                                    <TableCell>
                                        <div className="flex items-center gap-2">
                                            <div className={cn(
                                                "w-2 h-2 rounded-full",
                                                bug.priority === 'High' ? "bg-red-500 shadow-[0_0_8px_rgba(239,44,44,0.4)]" :
                                                    bug.priority === 'Medium' ? "bg-orange-500" : "bg-blue-500"
                                            )} />
                                            <span className="text-[10px] font-bold uppercase tracking-tight">{bug.priority}</span>
                                        </div>
                                    </TableCell>
                                    <TableCell>
                                        <Badge variant="outline" className="border-primary/20 bg-primary/5 text-primary text-[10px] uppercase px-2 py-0">
                                            {bug.status}
                                        </Badge>
                                    </TableCell>
                                    <TableCell>
                                        <div className="flex items-center gap-2">
                                            <div className="w-5 h-5 rounded-full bg-muted flex items-center justify-center text-[10px] font-bold">
                                                {bug.assignee.charAt(0)}
                                            </div>
                                            <span className="text-xs text-muted-foreground">{bug.assignee}</span>
                                        </div>
                                    </TableCell>
                                    <TableCell>
                                        <Link href={`/runs/${bug.linkedRunId}`} className="text-muted-foreground hover:text-primary transition-colors text-[10px] font-mono border-b border-muted-foreground/30 hover:border-primary/50">
                                            {bug.linkedRunId.substring(0, 8)}
                                        </Link>
                                    </TableCell>
                                    <TableCell className="text-right">
                                        <Button variant="ghost" size="icon" className="h-8 w-8 hover:bg-primary/10 hover:text-primary active:scale-95" asChild>
                                            <a href={bug.url} target="_blank" rel="noopener noreferrer">
                                                <ExternalLink className="h-3.5 w-3.5" />
                                                <span className="sr-only">Open in Jira</span>
                                            </a>
                                        </Button>
                                    </TableCell>
                                </TableRow>
                            ))}
                        </TableBody>
                    </Table>
                </div>
            </div>
        </MainLayout>
    );
}
