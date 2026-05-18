"use client"

import { useState } from "react"
import {
    Dialog,
    DialogContent,
    DialogHeader,
    DialogTitle,
} from "@/components/ui/dialog"
import { Artifact } from "@/types/agent"
import { JsonViewer } from "./json-viewer"
import { Download, ExternalLink, FileIcon, ZoomIn, ZoomOut, Maximize2 } from "lucide-react"
import { Button } from "./ui/button"
import { cn } from "@/lib/utils"

interface ArtifactViewerProps {
    artifact: Artifact | null
    open: boolean
    onOpenChange: (open: boolean) => void
}

export function ArtifactViewer({ artifact, open, onOpenChange }: ArtifactViewerProps) {
    const [zoom, setZoom] = useState(1)

    if (!artifact) return null

    const handleZoomIn = () => setZoom(prev => Math.min(prev + 0.2, 3))
    const handleZoomOut = () => setZoom(prev => Math.max(prev - 0.2, 0.5))
    const resetZoom = () => setZoom(1)

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="max-w-5xl max-h-[95vh] overflow-hidden flex flex-col p-0 border-border/40 bg-[#0A0A0A] shadow-2xl">
                <DialogHeader className="p-4 border-b border-border/40 bg-muted/20 flex flex-row items-center justify-between space-y-0">
                    <DialogTitle className="flex items-center gap-3 text-sm font-bold uppercase tracking-widest">
                        <div className="p-1.5 rounded-lg bg-primary/10 text-primary">
                            <FileIcon className="h-4 w-4" />
                        </div>
                        <div className="flex flex-col">
                            <span>{artifact.name}</span>
                            <span className="text-[10px] font-mono text-muted-foreground lowercase opacity-70">
                                source: {artifact.url}
                            </span>
                        </div>
                    </DialogTitle>
                    <div className="flex items-center gap-2">
                        <span className="text-[10px] font-bold uppercase text-primary bg-primary/10 px-2 py-0.5 rounded-md border border-primary/20 mr-4">
                            {artifact.type}
                        </span>
                        <div className="flex items-center gap-1 border-r border-border/40 pr-2 mr-2">
                            {artifact.type === 'screenshot' && (
                                <>
                                    <Button variant="ghost" size="icon" className="h-8 w-8 text-muted-foreground hover:text-foreground" onClick={handleZoomOut}>
                                        <ZoomOut className="h-4 w-4" />
                                    </Button>
                                    <Button variant="ghost" size="icon" className="h-8 w-8 text-muted-foreground hover:text-foreground" onClick={handleZoomIn}>
                                        <ZoomIn className="h-4 w-4" />
                                    </Button>
                                    <Button variant="ghost" size="icon" className="h-8 w-8 text-muted-foreground hover:text-foreground" onClick={resetZoom}>
                                        <Maximize2 className="h-4 w-4" />
                                    </Button>
                                </>
                            )}
                        </div>
                        <Button variant="ghost" size="icon" className="h-8 w-8" asChild>
                            <a href={artifact.url} target="_blank" rel="noopener noreferrer">
                                <Download className="h-4 w-4" />
                            </a>
                        </Button>
                    </div>
                </DialogHeader>

                <div className="flex-1 overflow-auto p-0 bg-[radial-gradient(#ffffff10_1px,transparent_1px)] [background-size:20px_20px] bg-[#050505]">
                    {artifact.type === 'video' && (
                        <div className="relative w-full h-[70vh] flex items-center justify-center bg-black">
                            <video
                                src={artifact.url}
                                controls
                                autoPlay
                                muted
                                playsInline
                                className="max-w-full max-h-full shadow-2xl"
                            />
                        </div>
                    )}

                    {artifact.type === 'screenshot' && (
                        <div className="w-full h-[70vh] flex items-center justify-center overflow-auto p-12">
                            <div
                                className="transition-transform duration-200 ease-out shadow-[0_0_100px_rgba(0,0,0,0.5)] rounded-lg overflow-hidden border border-border/20"
                                style={{ transform: `scale(${zoom})` }}
                            >
                                {/* eslint-disable-next-line @next/next/no-img-element */}
                                <img
                                    src={artifact.url}
                                    alt={artifact.name}
                                    className="max-w-none w-auto h-auto"
                                />
                            </div>
                        </div>
                    )}

                    {(artifact.type === 'log' || artifact.type === 'trace') && (
                        <div className="p-6">
                            <div className="bg-[#050505] p-6 rounded-xl border border-border/40 font-mono text-xs leading-relaxed text-muted-foreground whitespace-pre-wrap overflow-auto max-h-[60vh] shadow-inner">
                                <div className="flex items-center gap-2 mb-4 text-primary opacity-50">
                                    <span className="w-2 h-2 rounded-full bg-primary animate-pulse" />
                                    <span>STREAMING BYTE_DATA FROM SOURCE...</span>
                                </div>
                                <span className="text-foreground">Fetching trace context from endpoint:</span> {artifact.url}
                            </div>
                        </div>
                    )}

                    {artifact.type === 'json' && (
                        <div className="p-6">
                            <div className="bg-[#050505] p-6 rounded-xl border border-border/40 shadow-inner">
                                <div className="flex items-center justify-between mb-4">
                                    <div className="text-[10px] font-bold uppercase text-muted-foreground tracking-widest">Metadata Schema</div>
                                    <Button variant="ghost" size="sm" className="h-7 text-[10px] uppercase font-bold text-primary">Copy JSON</Button>
                                </div>
                                <JsonViewer data={{
                                    session: artifact.runId,
                                    type: artifact.type,
                                    timestamp: new Date().toISOString(),
                                    payload: { mock: "data", note: "Real viewer would fetch content from source" }
                                }} />
                            </div>
                        </div>
                    )}
                </div>
            </DialogContent>
        </Dialog>
    )
}
