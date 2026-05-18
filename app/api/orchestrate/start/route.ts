import { spawn } from 'child_process';
import path from 'path';
import { NextResponse } from 'next/server';

export async function POST() {
    try {
        // Resolve the crawler directory
        const crawlerDir = path.resolve(process.cwd(), 'agents', 'crawler');
        const scriptPath = 'fastapi_endpoint.py';

        // Attempting to boot crawler in the resolved directory

        // Launch the process using the virtual environment's python executable
        const venvPython = path.join(crawlerDir, '.venv', 'Scripts', 'python.exe');

        const child = spawn(venvPython, [scriptPath], {
            cwd: crawlerDir,
            detached: true,
            stdio: 'inherit',
            shell: true
        });

        // Allow the child to run independently of the parent
        child.unref();

        return NextResponse.json({
            status: 'initiating',
            message: 'Crawler boot sequence started.',
            pid: child.pid
        });
    } catch (error: any) {
        console.error('[Orchestrator] Failed to spawn crawler:', error);
        return NextResponse.json({
            status: 'failed',
            error: error.message
        }, { status: 500 });
    }
}
