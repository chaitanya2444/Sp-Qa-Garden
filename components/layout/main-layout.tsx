"use client"

import { Sidebar } from './sidebar';
import { Topbar } from './topbar';

interface MainLayoutProps {
    children: React.ReactNode;
}

export function MainLayout({ children }: MainLayoutProps) {
    return (
        <div className="flex h-screen">
            <Sidebar />
            <div className="flex-1 flex flex-col overflow-hidden">
                <Topbar />
                <main className="flex-1 overflow-y-auto p-6 bg-background">
                    {children}
                </main>
            </div>
        </div>
    );
}
