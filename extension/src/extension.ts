import * as vscode from 'vscode';
import { DecayPanel } from './panels/DecayPanel';
import { AnalyticsPanel } from './panels/AnalyticsPanel';
import { PreCommitReportPanel } from './panels/PreCommitReportPanel';
import { ApiService } from './services/ApiService';
import { GitService } from './services/GitService';
import { DecayDecorator } from './decorators/DecayDecorator';
import { Logger } from './utils/logger';
import { HighRiskFile } from './services/ApiService';

let decayPanel: DecayPanel | undefined;
let analyticsPanel: AnalyticsPanel | undefined;
let apiService: ApiService;
let gitService: GitService;
let decorator: DecayDecorator;

export function activate(context: vscode.ExtensionContext) {
    Logger.log('CodeDecay extension activating...');

    apiService = new ApiService();
    gitService = new GitService();
    decorator = new DecayDecorator();

    const analyzeFileCommand = vscode.commands.registerCommand(
        'codedecay.analyzeFile',
        async () => {
            const editor = vscode.window.activeTextEditor;
            if (!editor) {
                vscode.window.showErrorMessage('No active file to analyze');
                return;
            }
            const filePath = editor.document.uri.fsPath;
            const repoPath = await gitService.getRepoRoot(filePath);
            if (!repoPath) {
                vscode.window.showErrorMessage(
                    'File is not in a git repository'
                );
                return;
            }
            await analyzeFile(filePath, repoPath);
        }
    );

    const analyzeProjectCommand = vscode.commands.registerCommand(
        'codedecay.analyzeProject',
        async () => {
            const workspaceFolders = vscode.workspace.workspaceFolders;
            if (!workspaceFolders?.length) {
                vscode.window.showErrorMessage('No workspace folder open');
                return;
            }
            const repoPath = workspaceFolders[0].uri.fsPath;
            await analyzeProject(repoPath);
        }
    );

    const showPanelCommand = vscode.commands.registerCommand(
        'codedecay.showPanel',
        () => {
            if (DecayPanel.currentPanel) {
                DecayPanel.currentPanel.show();
            } else {
                decayPanel = DecayPanel.render(
                    context.extensionUri,
                    apiService
                );
            }
        }
    );

    const showAnalyticsCommand = vscode.commands.registerCommand(
        'codedecay.showAnalytics',
        () => {
            if (AnalyticsPanel.currentPanel) {
                AnalyticsPanel.currentPanel.show();
            } else {
                analyticsPanel = new AnalyticsPanel(
                    context.extensionUri,
                    apiService
                );
            }
        }
    );

    const checkBeforeCommitCommand = vscode.commands.registerCommand(
        'codedecay.checkBeforeCommit',
        async () => {
            const workspaceFolders = vscode.workspace.workspaceFolders;
            if (!workspaceFolders?.length) {
                vscode.window.showErrorMessage('No workspace folder open');
                return;
            }
            const repoPath = workspaceFolders[0].uri.fsPath;
            const repoRoot = await gitService.getRepoRoot(repoPath);
            if (!repoRoot) {
                vscode.window.showErrorMessage('Not a git repository');
                return;
            }
            await runCheckBeforeCommit(context.extensionUri, repoRoot);
        }
    );

    const analyzeGithubCommand = vscode.commands.registerCommand(
        'codedecay.analyzeGithub',
        async () => {
            const url = await vscode.window.showInputBox({
                title: 'CodeDecay: GitHub URL',
                prompt:
                    'Repository (https://github.com/owner/repo) or raw file (raw.githubusercontent.com/...)',
                placeHolder: 'https://github.com/owner/repo',
            });
            if (!url?.trim()) {
                return;
            }
            const ref = await vscode.window.showInputBox({
                title: 'Branch or tag (optional)',
                prompt: 'Leave empty to use the URL default or repository default branch',
            });
            await vscode.window.withProgress(
                {
                    location: vscode.ProgressLocation.Notification,
                    title: 'CodeDecay: Analyzing GitHub source…',
                    cancellable: false,
                },
                async (progress) => {
                    progress.report({ message: 'Cloning or fetching…' });
                    try {
                        const result = await apiService.analyzeGithub(
                            url.trim(),
                            ref?.trim() || undefined
                        );
                        const doc = await vscode.workspace.openTextDocument({
                            content: JSON.stringify(result, null, 2),
                            language: 'json',
                        });
                        await vscode.window.showTextDocument(doc, {
                            preview: true,
                        });
                        const recs = result.shareability_recommendations;
                        if (recs?.length) {
                            vscode.window.showInformationMessage(
                                `Top suggestion: ${recs[0]}`
                            );
                        } else {
                            vscode.window.showInformationMessage(
                                'GitHub analysis complete — see JSON tab for full report.'
                            );
                        }
                    } catch (e) {
                        Logger.error('GitHub analysis failed', e);
                        vscode.window.showErrorMessage(
                            `GitHub analysis failed: ${e instanceof Error ? e.message : String(e)}`
                        );
                    }
                }
            );
        }
    );

    const showHighRiskCommand = vscode.commands.registerCommand(
        'codedecay.showHighRisk',
        async () => {
            const highRiskFiles = await apiService.getHighRiskFiles(70);
            if (highRiskFiles.length === 0) {
                vscode.window.showInformationMessage(
                    'No high-risk files found'
                );
                return;
            }
            const quickPick = vscode.window.createQuickPick();
            quickPick.items = highRiskFiles.map(
                (file: HighRiskFile) => ({
                    label: `$(warning) ${file.file_path}`,
                    description: `Decay: ${(file.decay_score ?? 0).toFixed(1)} | ${file.risk_level || ''}`,
                    detail: (file.recommendations || []).join('; '),
                    file_path: file.file_path,
                })
            );
            quickPick.placeholder = 'Select a high-risk file to open';
            quickPick.onDidChangeSelection((selection) => {
                const item = selection[0] as { file_path?: string } | undefined;
                if (item?.file_path) {
                    vscode.workspace
                        .openTextDocument(item.file_path)
                        .then((doc) =>
                            vscode.window.showTextDocument(doc)
                        );
                    quickPick.hide();
                }
            });
            quickPick.show();
        }
    );

    context.subscriptions.push(
        analyzeFileCommand,
        analyzeProjectCommand,
        showPanelCommand,
        showAnalyticsCommand,
        checkBeforeCommitCommand,
        analyzeGithubCommand,
        showHighRiskCommand
    );

    vscode.workspace.onDidOpenTextDocument(async (document) => {
        if (document.uri.scheme === 'file') {
            const filePath = document.uri.fsPath;
            const repoPath = await gitService.getRepoRoot(filePath);
            if (repoPath) {
                const status = await apiService.getAnalysisStatus(filePath);
                if (status?.prediction) {
                    decorator.updateDecorations(
                        document,
                        status.prediction
                    );
                }
            }
        }
    });

    const statusBarItem = vscode.window.createStatusBarItem(
        vscode.StatusBarAlignment.Right,
        100
    );
    statusBarItem.text = '$(pulse) CodeDecay';
    statusBarItem.command = 'codedecay.showPanel';
    statusBarItem.tooltip = 'Click to open CodeDecay panel';
    statusBarItem.show();
    context.subscriptions.push(statusBarItem);

    Logger.log('CodeDecay extension activated successfully');
}

async function analyzeFile(filePath: string, repoPath: string) {
    await vscode.window.withProgress(
        {
            location: vscode.ProgressLocation.Notification,
            title: 'Analyzing file...',
            cancellable: false,
        },
        async (progress) => {
            progress.report({ message: 'Running decay analysis' });
            try {
                const result = await apiService.analyzeFile(
                    filePath,
                    repoPath
                );
                if (result.status === 'completed' && result.prediction) {
                    const pred = result.prediction as { decay_score?: number; risk_level?: string } | undefined;
                    const message = `Decay Score: ${(pred?.decay_score ?? 0).toFixed(1)} | Risk: ${pred?.risk_level || 'unknown'}`;
                    vscode.window.showInformationMessage(message);
                    const document = await vscode.workspace.openTextDocument(
                        filePath
                    );
                    decorator.updateDecorations(
                        document,
                        result.prediction
                    );
                    if (DecayPanel.currentPanel) {
                        DecayPanel.currentPanel.updateContent(result);
                    }
                } else {
                    vscode.window.showErrorMessage('Analysis failed');
                }
            } catch (error) {
                Logger.error('Error analyzing file', error);
                vscode.window.showErrorMessage(
                    `Analysis error: ${error instanceof Error ? error.message : String(error)}`
                );
            }
        }
    );
}

async function analyzeProject(repoPath: string) {
    const proceed = await vscode.window.showInformationMessage(
        'Analyze entire project? This may take several minutes.',
        'Yes',
        'No'
    );
    if (proceed !== 'Yes') return;

    vscode.window.withProgress(
        {
            location: vscode.ProgressLocation.Notification,
            title: 'Analyzing project...',
            cancellable: false,
        },
        async (progress) => {
            try {
                progress.report({ message: 'Starting analysis' });
                await apiService.analyzeProject(repoPath);
                vscode.window.showInformationMessage(
                    'Project analysis started in background. Check Analytics dashboard for results.'
                );
            } catch (error) {
                Logger.error('Error analyzing project', error);
                vscode.window.showErrorMessage(
                    `Project analysis error: ${error instanceof Error ? error.message : String(error)}`
                );
            }
        }
    );
}

async function runCheckBeforeCommit(
    extensionUri: vscode.Uri,
    repoRoot: string
): Promise<void> {
    await vscode.window.withProgress(
        {
            location: vscode.ProgressLocation.Notification,
            title: 'CodeDecay: Checking before commit...',
            cancellable: false,
        },
        async (progress) => {
            progress.report({ message: 'Getting staged files...' });
            let filePaths = await gitService.getStagedFiles(repoRoot);
            if (filePaths.length === 0) {
                progress.report({ message: 'No staged files, checking modified...' });
                filePaths = await gitService.getModifiedFiles(repoRoot);
            }
            if (filePaths.length === 0) {
                vscode.window.showInformationMessage(
                    'CodeDecay: No staged or modified files to check.'
                );
                return;
            }
            progress.report({ message: `Checking ${filePaths.length} files...` });
            try {
                const result = await apiService.preCommitCheck(repoRoot, filePaths);
                PreCommitReportPanel.show(extensionUri, result);
                if (!result.ok) {
                    vscode.window.showWarningMessage(
                        `CodeDecay: ${result.total_issues} issue(s) in ${result.files_with_issues} file(s). Fix before commit.`
                    );
                } else if (result.total_issues > 0) {
                    vscode.window.showInformationMessage(
                        `CodeDecay: ${result.total_issues} low/medium issue(s). Review report.`
                    );
                }
            } catch (e) {
                Logger.error('Pre-commit check failed', e);
                vscode.window.showErrorMessage(
                    `CodeDecay check failed: ${e instanceof Error ? e.message : String(e)}`
                );
            }
        }
    );
}

export function deactivate() {
    Logger.log('CodeDecay extension deactivating...');
}
