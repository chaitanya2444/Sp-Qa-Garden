"use client"

import * as React from "react"
import { Check, Copy } from "lucide-react"

import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"

interface JsonViewerProps {
    data: any
    className?: string
}

export function JsonViewer({ data, className }: JsonViewerProps) {
    const [copied, setCopied] = React.useState(false)

    const onCopy = () => {
        navigator.clipboard.writeText(JSON.stringify(data, null, 2))
        setCopied(true)
        setTimeout(() => setCopied(false), 2000)
    }

    return (
        <div className={cn("relative rounded-md border bg-muted/50 font-mono text-xs", className)}>
            <div className="absolute right-2 top-2 z-10">
                <Button
                    variant="ghost"
                    size="icon"
                    className="h-6 w-6"
                    onClick={onCopy}
                >
                    {copied ? (
                        <Check className="h-3 w-3 text-green-500" />
                    ) : (
                        <Copy className="h-3 w-3" />
                    )}
                    <span className="sr-only">Copy JSON</span>
                </Button>
            </div>
            <div className="max-h-[300px] overflow-auto p-4">
                <pre>{JSON.stringify(data, null, 2)}</pre>
            </div>
        </div>
    )
}
