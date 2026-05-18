"use client"

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { cn } from '@/lib/utils';
import {
    LayoutDashboard,
    PlayCircle,
    History,
    GitBranch,
    AlertTriangle,
    Bug,
    Settings,
    Activity,
} from 'lucide-react';

const navItems = [
    { href: '/', label: 'Overview', icon: LayoutDashboard },
    { href: '/new-run', label: 'New Run', icon: PlayCircle },
    { href: '/runs', label: 'Runs History', icon: History },
    { href: '/pipeline', label: 'Agent Pipeline', icon: GitBranch },
    { href: '/failures', label: 'Failures & Triage', icon: AlertTriangle },
    { href: '/jira', label: 'Jira Bugs', icon: Bug },
    { href: '/settings', label: 'Settings', icon: Settings },
    { href: '/health', label: 'System Health', icon: Activity },
];

export function Sidebar() {
    const pathname = usePathname();

    return (
        <aside className="w-64 border-r bg-card flex flex-col">
            <div className="p-6 border-b">
                <h1 className="text-xl font-bold">QA Garden</h1>
                <p className="text-xs text-muted-foreground mt-1">Autonomous QA Platform</p>
            </div>

            <nav className="flex-1 p-4 space-y-1">
                {navItems.map((item) => {
                    const Icon = item.icon;
                    const isActive = pathname === item.href;

                    return (
                        <Link
                            key={item.href}
                            href={item.href}
                            className={cn(
                                "flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium transition-colors",
                                isActive
                                    ? "bg-primary text-primary-foreground"
                                    : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
                            )}
                        >
                            <Icon className="h-4 w-4" />
                            {item.label}
                        </Link>
                    );
                })}
            </nav>

            <div className="p-4 border-t text-xs text-muted-foreground">
                <p>v1.0.0</p>
            </div>
        </aside>
    );
}
