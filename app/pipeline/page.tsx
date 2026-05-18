"use client"

import { motion } from 'framer-motion';
import { Brain, Bot, Code2, PlayCircle, AlertTriangle, GitBranch, Share2 } from 'lucide-react';
import { MainLayout } from '@/components/layout/main-layout';
import { Card } from '@/components/ui/card';
import { cn } from '@/lib/utils';

const agents = [
    {
        name: 'Crawler',
        icon: Brain,
        description: 'Autonomous exploration unit. Discovers interactive elements, handles complex auth flows, and maps site architecture.',
        color: 'from-blue-500 to-cyan-400',
        shadow: 'shadow-blue-500/20',
        active: true,
    },
    {
        name: 'Test Generator',
        icon: Bot,
        description: 'Neural reasoning engine. Analyzes page state and locators to architect logical test scenarios and edge cases.',
        color: 'from-purple-500 to-pink-400',
        shadow: 'shadow-purple-500/20',
    },
    {
        name: 'Script Gen',
        icon: Code2,
        description: 'Code synthesis layer. Transforms semantic test requirements into robust, executable Playwright/Pytest scripts.',
        color: 'from-emerald-500 to-teal-400',
        shadow: 'shadow-emerald-500/20',
    },
    {
        name: 'CI/CD Executor',
        icon: PlayCircle,
        description: 'Deployment & Runtime. Orchestrates parallel execution across headless clusters and captures rich artifacts.',
        color: 'from-amber-500 to-orange-400',
        shadow: 'shadow-amber-500/20',
    },
    {
        name: 'Triage Engine',
        icon: AlertTriangle,
        description: 'Fault isolation & Analysis. Classifies failures using AI, generates bug reports, and updates the Triage DB.',
        color: 'from-red-500 to-rose-400',
        shadow: 'shadow-red-500/20',
    },
];

export default function PipelinePage() {
    return (
        <MainLayout>
            <div className="min-h-[calc(100vh-100px)] space-y-12 max-w-[1600px] mx-auto pb-12 px-4 md:px-8">
                {/* Header */}
                <div className="text-center space-y-4 pt-8">
                    <motion.div
                        initial={{ opacity: 0, scale: 0.8 }}
                        animate={{ opacity: 1, scale: 1 }}
                        className="flex justify-center"
                    >
                        <div className="p-3 rounded-2xl bg-primary/10 border border-primary/20 backdrop-blur-xl ring-1 ring-primary/20">
                            <GitBranch className="h-8 w-8 text-primary" />
                        </div>
                    </motion.div>
                    <motion.h1
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        className="text-4xl md:text-7xl font-black tracking-tighter bg-clip-text text-transparent bg-gradient-to-b from-foreground to-foreground/40"
                    >
                        Agentic Pipeline
                    </motion.h1>
                    <motion.p
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: 0.1 }}
                        className="text-muted-foreground text-xs md:text-sm max-w-2xl mx-auto font-bold uppercase tracking-[0.3em] opacity-60"
                    >
                        Neural Protocol for Autonomous Quality Assurance
                    </motion.p>
                </div>

                {/* Pipeline Grid */}
                <div className="relative mt-24">
                    {/* SVG Connecting Lines - Visible on LG screens */}
                    <div className="absolute inset-0 pointer-events-none hidden lg:block z-0">
                        <svg className="w-full h-full" preserveAspectRatio="none" viewBox="0 0 100 100">
                            <motion.line
                                initial={{ pathLength: 0, opacity: 0 }}
                                animate={{ pathLength: 1, opacity: 1 }}
                                transition={{ duration: 1.5, delay: 0.5 }}
                                x1="10" y1="40" x2="90" y2="40"
                                stroke="currentColor"
                                strokeWidth="0.2"
                                className="text-primary/20"
                                strokeDasharray="1 2"
                            />
                        </svg>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-8 lg:gap-6 relative z-10">
                        {agents.map((agent, index) => (
                            <div key={agent.name} className="relative group">
                                <motion.div
                                    initial={{ opacity: 0, y: 30 }}
                                    animate={{ opacity: 1, y: 0 }}
                                    transition={{ delay: index * 0.1, duration: 0.5, ease: "easeOut" }}
                                >
                                    <Card className={cn(
                                        "relative h-full border-border/40 bg-card/40 backdrop-blur-2xl overflow-hidden transition-all duration-500",
                                        "group-hover:translate-y-[-10px] group-hover:shadow-2xl group-hover:border-primary/50 group-hover:bg-card/60",
                                        agent.shadow,
                                        agent.active && "ring-1 ring-primary/30"
                                    )}>
                                        {/* Top Accent Gradient with Glow */}
                                        <div className={cn("h-1.5 w-full bg-gradient-to-r relative overflow-hidden", agent.color)}>
                                            {agent.active && (
                                                <motion.div
                                                    animate={{ x: ['-100%', '200%'] }}
                                                    transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
                                                    className="absolute inset-0 bg-gradient-to-r from-transparent via-white/40 to-transparent w-full"
                                                />
                                            )}
                                        </div>

                                        <div className="p-8 space-y-6">
                                            <div className="space-y-4">
                                                <div className={cn(
                                                    "w-16 h-16 rounded-2xl flex items-center justify-center border transition-all duration-500 relative",
                                                    "bg-gradient-to-br from-white/10 to-transparent border-white/10",
                                                    "group-hover:scale-110 group-hover:border-white/40 group-hover:shadow-[0_0_20px_rgba(255,255,255,0.1)]",
                                                    agent.active && "border-primary/40 shadow-[0_0_20px_rgba(var(--primary),0.2)]"
                                                )}>
                                                    <agent.icon className={cn(
                                                        "h-8 w-8 transition-colors duration-500",
                                                        agent.active ? "text-primary" : "text-foreground group-hover:text-primary"
                                                    )} />
                                                    {agent.active && (
                                                        <span className="absolute -top-1 -right-1 flex h-4 w-4">
                                                            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-primary opacity-75"></span>
                                                            <span className="relative inline-flex rounded-full h-4 w-4 bg-primary/20 border border-primary/50 text-[8px] items-center justify-center font-bold text-primary">!</span>
                                                        </span>
                                                    )}
                                                </div>
                                                <h2 className="text-2xl font-black tracking-tight text-white/90 group-hover:text-white transition-colors">{agent.name}</h2>
                                            </div>

                                            <p className="text-sm text-muted-foreground/90 leading-relaxed font-semibold group-hover:text-foreground/90 transition-colors">
                                                {agent.description}
                                            </p>

                                            <div className="pt-6 flex items-center justify-between text-[10px] font-black uppercase tracking-[0.2em] opacity-30 group-hover:opacity-100 group-hover:text-primary transition-all duration-500">
                                                <span className="flex items-center gap-2">
                                                    <span className={cn("w-1.5 h-1.5 rounded-full", agent.active ? "bg-primary animate-pulse" : "bg-muted-foreground/50")} />
                                                    Node 0{index + 1}
                                                </span>
                                                <Share2 className="h-3.5 w-3.5" />
                                            </div>
                                        </div>

                                        {/* Background Radial Glow */}
                                        <div className={cn(
                                            "absolute -right-12 -bottom-12 w-32 h-32 rounded-full blur-[50px] opacity-0 group-hover:opacity-30 transition-opacity duration-700 bg-gradient-to-br",
                                            agent.color
                                        )} />
                                    </Card>
                                </motion.div>
                            </div>
                        ))}
                    </div>
                </div>

                {/* Status Footer */}
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.8 }}
                    className="pt-16 flex flex-col items-center space-y-8"
                >
                    <div className="h-px w-32 bg-gradient-to-r from-transparent via-primary/30 to-transparent" />

                    <div className="bg-card/30 backdrop-blur-xl border border-white/5 py-4 px-10 rounded-full flex flex-col md:flex-row items-center gap-6 shadow-2xl">
                        <div className="flex items-center gap-3">
                            <div className="relative flex h-3 w-3">
                                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-500 opacity-75"></span>
                                <span className="relative inline-flex rounded-full h-3 w-3 bg-emerald-500"></span>
                            </div>
                            <p className="text-sm font-bold uppercase tracking-widest">
                                Pipeline Status: <span className="text-emerald-400">Stable & Synchronized</span>
                            </p>
                        </div>
                        <div className="hidden md:block w-px h-4 bg-white/10" />
                        <p className="text-[11px] text-muted-foreground/60 font-mono tracking-tighter">
                            LAST_PULSE: {new Date().toLocaleTimeString()} // RECEPTOR_READY=TRUE // PROTOCOL_V4.2.1
                        </p>
                    </div>

                    <p className="text-[10px] text-muted-foreground/30 font-black uppercase tracking-[0.4em] pt-4">
                        QA GARDEN INTELLIGENCE CORE // SECURED_TERMINAL
                    </p>
                </motion.div>
            </div>
        </MainLayout>
    );
}
