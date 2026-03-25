import axios, { AxiosInstance } from 'axios';
import * as vscode from 'vscode';
import { Logger } from '../utils/logger';

export interface AnalysisResult {
    file_path: string;
    status: string;
    decay_score?: number;
    risk_level?: string;
    prediction?: Record<string, unknown>;
}

export interface HighRiskFile {
    file_path: string;
    decay_score: number;
    risk_level: string;
    recommendations: string[];
}

export interface PreCommitIssue {
    file_path: string;
    type: string;
    severity: string;
    line: number;
    message: string;
    category?: string;
}

export interface PreCommitResult {
    ok: boolean;
    files_checked: number;
    files_with_issues: number;
    total_issues: number;
    by_severity: { critical: number; high: number; medium: number; low: number };
    issues: PreCommitIssue[];
    message: string;
}

/** Response from POST /api/analysis/github */
export interface GithubAnalysisResult {
    status: string;
    source: Record<string, unknown>;
    summary: Record<string, unknown>;
    repo_hygiene?: Record<string, boolean>;
    future_risk_overview?: Record<string, unknown>;
    style_summary?: Record<string, unknown>;
    shareability_recommendations?: string[];
    file_results?: unknown[];
}

export class ApiService {
    private client: AxiosInstance;
    private baseUrl: string;

    constructor() {
        const config = vscode.workspace.getConfiguration('codedecay');
        this.baseUrl = config.get('apiUrl', 'http://localhost:8000');
        const apiSecret = config.get<string>('apiSecret', '')?.trim() || '';
        const headers: Record<string, string> = { 'Content-Type': 'application/json' };
        if (apiSecret) {
            headers['Authorization'] = `Bearer ${apiSecret}`;
        }
        this.client = axios.create({
            baseURL: this.baseUrl,
            timeout: 300000,
            headers,
        });
        Logger.log(`ApiService initialized with baseUrl: ${this.baseUrl}`);
    }

    async analyzeFile(
        filePath: string,
        repoPath: string
    ): Promise<AnalysisResult> {
        try {
            Logger.log(`Analyzing file: ${filePath}`);
            const response = await this.client.post('/api/analysis/file', {
                file_path: filePath,
                repo_path: repoPath,
            });
            return response.data;
        } catch (error: unknown) {
            Logger.error('Error analyzing file', error);
            const err = error as { response?: { data?: { detail?: string } }; message?: string };
            throw new Error(err.response?.data?.detail || err.message || 'Unknown error');
        }
    }

    async analyzeProject(repoPath: string): Promise<void> {
        try {
            Logger.log(`Analyzing project: ${repoPath}`);
            await this.client.post('/api/analysis/project', {
                repo_path: repoPath,
                file_extensions: ['.py', '.js', '.ts', '.jsx', '.tsx'],
            });
        } catch (error: unknown) {
            Logger.error('Error analyzing project', error);
            const err = error as { response?: { data?: { detail?: string } }; message?: string };
            throw new Error(err.response?.data?.detail || err.message || 'Unknown error');
        }
    }

    async getAnalysisStatus(filePath: string): Promise<{ prediction?: Record<string, unknown> } | null> {
        try {
            const response = await this.client.get(
                `/api/analysis/status/${encodeURIComponent(filePath)}`
            );
            return response.data;
        } catch {
            return null;
        }
    }

    async getHighRiskFiles(threshold: number = 70): Promise<HighRiskFile[]> {
        try {
            const response = await this.client.get('/api/metrics/high-risk', {
                params: { threshold },
            });
            return (response.data?.files as HighRiskFile[]) || [];
        } catch {
            return [];
        }
    }

    async getMetricsSummary(): Promise<Record<string, unknown> | null> {
        try {
            const response = await this.client.get('/api/metrics/summary');
            return response.data;
        } catch {
            return null;
        }
    }

    async getFileMetrics(
        filePath: string,
        limit: number = 10
    ): Promise<unknown[]> {
        try {
            const response = await this.client.get(
                `/api/metrics/file/${encodeURIComponent(filePath)}`,
                { params: { limit } }
            );
            return response.data || [];
        } catch {
            return [];
        }
    }

    async analyzeGithub(
        url: string,
        ref?: string
    ): Promise<GithubAnalysisResult> {
        try {
            Logger.log(`GitHub analysis: ${url}`);
            const response = await this.client.post('/api/analysis/github', {
                url,
                ref: ref || undefined,
            });
            return response.data as GithubAnalysisResult;
        } catch (error: unknown) {
            Logger.error('Error analyzing GitHub URL', error);
            const err = error as { response?: { data?: { detail?: string } }; message?: string };
            throw new Error(err.response?.data?.detail || err.message || 'Unknown error');
        }
    }

    async preCommitCheck(
        repoPath: string,
        filePaths: string[]
    ): Promise<PreCommitResult> {
        try {
            Logger.log(`Pre-commit check for ${filePaths.length} files`);
            const response = await this.client.post('/api/analysis/pre-commit', {
                repo_path: repoPath,
                file_paths: filePaths,
            });
            return response.data as PreCommitResult;
        } catch (error: unknown) {
            Logger.error('Error running pre-commit check', error);
            const err = error as { response?: { data?: { detail?: string } }; message?: string };
            throw new Error(err.response?.data?.detail || err.message || 'Unknown error');
        }
    }
}
