"use client"

import React, { useEffect, useRef } from "react"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Terminal } from "lucide-react"
import { cn } from "@/lib/utils"

interface LogMessage {
    timestamp: string
    level: "info" | "warning" | "error" | "success"
    message: string
    agent?: string
}

interface TerminalLogProps {
    logs: LogMessage[]
    className?: string
}

export function TerminalLog({ logs, className }: TerminalLogProps) {
    const scrollRef = useRef<HTMLDivElement>(null)

    useEffect(() => {
        if (scrollRef.current) {
            scrollRef.current.scrollTop = scrollRef.current.scrollHeight
        }
    }, [logs])

    return (
        <div className={cn("flex flex-col rounded-lg overflow-hidden border bg-[#050505] font-mono text-xs", className)}>
            <div className="flex items-center gap-2 px-4 py-2 bg-[#1a1a1a] border-b border-[#333]">
                <Terminal className="h-4 w-4 text-green-500" />
                <span className="text-gray-400 font-semibold uppercase tracking-wider">System Live Feed</span>
                <div className="flex gap-1.5 ml-auto">
                    <div className="w-2.5 h-2.5 rounded-full bg-red-500/20 border border-red-500/50" />
                    <div className="w-2.5 h-2.5 rounded-full bg-yellow-500/20 border border-yellow-500/50" />
                    <div className="w-2.5 h-2.5 rounded-full bg-green-500/20 border border-green-500/50" />
                </div>
            </div>
            <div
                ref={scrollRef}
                className="flex-1 overflow-y-auto p-4 space-y-1.5 scrollbar-thin scrollbar-thumb-gray-800 scrollbar-track-transparent"
                style={{ scrollBehavior: 'smooth' }}
            >
                {logs.length === 0 ? (
                    <div className="text-gray-600 italic">Waiting for connection...</div>
                ) : (
                    logs.map((log, i) => (
                        <div key={i} className="flex gap-3 animate-in fade-in slide-in-from-left-2 duration-300">
                            <span className="text-gray-600 shrink-0">[{log.timestamp}]</span>
                            <span className={cn(
                                "font-bold shrink-0 uppercase w-16",
                                log.level === "info" && "text-blue-500",
                                log.level === "warning" && "text-yellow-500",
                                log.level === "error" && "text-red-500",
                                log.level === "success" && "text-green-500"
                            )}>
                                {log.level}
                            </span>
                            {log.agent && (
                                <span className="text-purple-400 shrink-0">[{log.agent}]</span>
                            )}
                            <span className="text-gray-300 whitespace-pre-wrap break-all">{log.message}</span>
                        </div>
                    ))
                )}
            </div>
        </div>
    )
}
