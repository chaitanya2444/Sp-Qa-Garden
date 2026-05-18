import { Artifact } from './agent';

export interface Failure {
    id: string;
    runId: string;
    title: string;
    stage: string;
    category: string;
    severity: 'low' | 'medium' | 'high';
    cause: string;
    suggestion: string;
    artifact?: Artifact;
    // AI Triage results
    aiTitle?: string;
    aiDescription?: string;
    aiLabel?: string;
    aiConfidence?: number;
    errorLine?: number;
    playwrightScript?: string;
    testUrl?: string;
}
