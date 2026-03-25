import * as vscode from 'vscode';
import { ApiService } from '../services/ApiService';
import { Logger } from '../utils/logger';

interface AnalysisResult {
    prediction?: {
        decay_score?: number;
        risk_level?: string;
        confidence?: number;
        predicted_issues?: Array<{ type?: string; description?: string; timeframe?: string; probability?: number }>;
        recommendations?: string[];
    };
}

export class DecayPanel {
    public static currentPanel: DecayPanel | undefined;
    private readonly _panel: vscode.WebviewPanel;
    private readonly _extensionUri: vscode.Uri;
    private _disposables: vscode.Disposable[] = [];
    private apiService: ApiService;

    private constructor(extensionUri: vscode.Uri, apiService: ApiService) {
        this._extensionUri = extensionUri;
        this.apiService = apiService;
        DecayPanel.currentPanel = this;

        this._panel = vscode.window.createWebviewPanel(
            'codedecayPanel',
            'CodeDecay Analysis',
            vscode.ViewColumn.Two,
            { enableScripts: true, retainContextWhenHidden: true }
        );

        this._panel.webview.html = this.getWebviewContent();
        this._panel.onDidDispose(() => this.dispose(), null, this._disposables);
        this._panel.webview.onDidReceiveMessage(
            async (message: { command: string }) => {
                if (message.command === 'analyzeFile') {
                    await vscode.commands.executeCommand('codedecay.analyzeFile');
                }
            },
            null,
            this._disposables
        );
    }

    public static render(
        extensionUri: vscode.Uri,
        apiService: ApiService
    ): DecayPanel {
        if (DecayPanel.currentPanel) {
            DecayPanel.currentPanel._panel.reveal(vscode.ViewColumn.Two);
            return DecayPanel.currentPanel;
        }
        return new DecayPanel(extensionUri, apiService);
    }

    public show() {
        this._panel.reveal(vscode.ViewColumn.Two);
    }

    public updateContent(analysisResult: AnalysisResult) {
        this._panel.webview.postMessage({
            command: 'updateAnalysis',
            data: analysisResult,
        });
    }

    private getWebviewContent(): string {
        return `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CodeDecay Analysis</title>
    <style>
        body { font-family: var(--vscode-font-family); color: var(--vscode-foreground); background-color: var(--vscode-editor-background); padding: 20px; }
        .header { display: flex; align-items: center; margin-bottom: 30px; }
        .header h1 { margin: 0; color: var(--vscode-foreground); }
        .score-container { background: var(--vscode-editor-inactiveSelectionBackground); border-radius: 8px; padding: 20px; margin-bottom: 20px; }
        .score-value { font-size: 48px; font-weight: bold; margin: 10px 0; }
        .score-critical { color: #f44336; }
        .score-high { color: #ff9800; }
        .score-medium { color: #ffeb3b; }
        .score-low { color: #4caf50; }
        .section { margin-bottom: 30px; }
        .section h2 { color: var(--vscode-foreground); border-bottom: 1px solid var(--vscode-widget-border); padding-bottom: 10px; }
        .issue-item, .rec-item { background: var(--vscode-input-background); border-left: 3px solid var(--vscode-focusBorder); padding: 12px; margin: 10px 0; border-radius: 4px; }
        .button { background: var(--vscode-button-background); color: var(--vscode-button-foreground); border: none; padding: 10px 20px; border-radius: 4px; cursor: pointer; font-size: 14px; }
        .button:hover { background: var(--vscode-button-hoverBackground); }
        .empty-state { text-align: center; padding: 40px; color: var(--vscode-descriptionForeground); }
    </style>
</head>
<body>
    <div class="header"><h1>CodeDecay Analysis</h1></div>
    <div id="content">
        <div class="empty-state">
            <h2>No Analysis Yet</h2>
            <p>Select a file and click "Analyze File" to begin</p>
            <button class="button" onclick="analyzeFile()">Analyze Current File</button>
        </div>
    </div>
    <script>
        const vscode = acquireVsCodeApi();
        function analyzeFile() { vscode.postMessage({ command: 'analyzeFile' }); }
        window.addEventListener('message', event => {
            const message = event.data;
            if (message.command === 'updateAnalysis') updateContent(message.data);
        });
        function updateContent(data) {
            const prediction = data.prediction;
            if (!prediction) return;
            const riskClass = 'score-' + (prediction.risk_level || 'low');
            let html = '<div class="score-container"><h2>Decay Score</h2><div class="score-value ' + riskClass + '">' + (prediction.decay_score ?? 0).toFixed(1) + '</div><div>Risk Level: <strong>' + (prediction.risk_level || 'low').toUpperCase() + '</strong></div><div>Confidence: ' + ((prediction.confidence ?? 0) * 100).toFixed(0) + '%</div></div>';
            if (prediction.predicted_issues && prediction.predicted_issues.length > 0) {
                html += '<div class="section"><h2>Predicted Issues</h2>';
                prediction.predicted_issues.forEach(issue => {
                    html += '<div class="issue-item"><strong>' + (issue.type || '') + '</strong><br>' + (issue.description || '') + '<br><small>Timeframe: ' + (issue.timeframe || '') + ' | Probability: ' + ((issue.probability ?? 0) * 100).toFixed(0) + '%</small></div>';
                });
                html += '</div>';
            }
            if (prediction.recommendations && prediction.recommendations.length > 0) {
                html += '<div class="section"><h2>Recommendations</h2>';
                prediction.recommendations.forEach(rec => { html += '<div class="rec-item">' + rec + '</div>'; });
                html += '</div>';
            }
            document.getElementById('content').innerHTML = html;
        }
    </script>
</body>
</html>`;
    }

    public dispose() {
        DecayPanel.currentPanel = undefined;
        this._panel.dispose();
        this._disposables.forEach((d) => d.dispose());
    }
}
