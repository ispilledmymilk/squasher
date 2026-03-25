import * as vscode from 'vscode';
import { ApiService, HighRiskFile } from '../services/ApiService';
import { Logger } from '../utils/logger';

export class AnalyticsPanel {
    public static currentPanel: AnalyticsPanel | undefined;
    private readonly _panel: vscode.WebviewPanel;
    private readonly _extensionUri: vscode.Uri;
    private _disposables: vscode.Disposable[] = [];
    private apiService: ApiService;

    constructor(extensionUri: vscode.Uri, apiService: ApiService) {
        this._extensionUri = extensionUri;
        this.apiService = apiService;
        AnalyticsPanel.currentPanel = this;

        this._panel = vscode.window.createWebviewPanel(
            'codedecayAnalytics',
            'CodeDecay Analytics',
            vscode.ViewColumn.Two,
            { enableScripts: true, retainContextWhenHidden: true }
        );

        this._panel.webview.html = this.getWebviewContent();
        this._panel.onDidDispose(() => this.dispose(), null, this._disposables);
        this.loadData();
    }

    public show() {
        this._panel.reveal(vscode.ViewColumn.Two);
        this.loadData();
    }

    private async loadData() {
        try {
            const summary = await this.apiService.getMetricsSummary();
            const highRisk = await this.apiService.getHighRiskFiles(60);
            this._panel.webview.postMessage({
                command: 'updateData',
                data: { summary: summary || {}, highRisk: highRisk || [] },
            });
        } catch (error) {
            Logger.error('Error loading analytics data', error);
        }
    }

    private getWebviewContent(): string {
        return `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CodeDecay Analytics</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
    <style>
        body { font-family: var(--vscode-font-family); color: var(--vscode-foreground); background-color: var(--vscode-editor-background); padding: 20px; }
        .dashboard { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin-bottom: 30px; }
        .card { background: var(--vscode-editor-inactiveSelectionBackground); border-radius: 8px; padding: 20px; border: 1px solid var(--vscode-widget-border); }
        .card h3 { margin: 0 0 10px 0; font-size: 14px; color: var(--vscode-descriptionForeground); text-transform: uppercase; }
        .card-value { font-size: 32px; font-weight: bold; margin: 10px 0; }
        .chart-container { background: var(--vscode-editor-inactiveSelectionBackground); border-radius: 8px; padding: 20px; margin-bottom: 20px; border: 1px solid var(--vscode-widget-border); }
        .file-list { list-style: none; padding: 0; }
        .file-item { background: var(--vscode-input-background); padding: 15px; margin: 10px 0; border-radius: 4px; border-left: 4px solid; }
        .file-item.critical { border-color: #f44336; }
        .file-item.high { border-color: #ff9800; }
        .file-item.medium { border-color: #ffeb3b; }
        .file-name { font-weight: bold; margin-bottom: 5px; }
        .file-score { font-size: 18px; margin: 5px 0; }
    </style>
</head>
<body>
    <h1>CodeDecay Analytics Dashboard</h1>
    <div class="dashboard" id="dashboard">
        <div class="card"><h3>Total Files Analyzed</h3><div class="card-value" id="totalFiles">-</div></div>
        <div class="card"><h3>Critical Risk</h3><div class="card-value" style="color: #f44336;" id="criticalCount">-</div></div>
        <div class="card"><h3>High Risk</h3><div class="card-value" style="color: #ff9800;" id="highCount">-</div></div>
        <div class="card"><h3>Average Decay Score</h3><div class="card-value" id="avgScore">-</div></div>
    </div>
    <div class="chart-container"><h2>Risk Distribution</h2><canvas id="riskChart" width="400" height="200"></canvas></div>
    <div class="chart-container"><h2>High-Risk Files</h2><ul class="file-list" id="fileList"><li>Loading...</li></ul></div>
    <script>
        const vscode = acquireVsCodeApi();
        let riskChart = null;
        window.addEventListener('message', event => {
            if (event.data.command === 'updateData') updateDashboard(event.data.data);
        });
        function updateDashboard(data) {
            const summary = data.summary || {};
            const highRisk = data.highRisk || [];
            document.getElementById('totalFiles').textContent = summary.total_files_analyzed || 0;
            document.getElementById('criticalCount').textContent = (summary.risk_distribution && summary.risk_distribution.critical) || 0;
            document.getElementById('highCount').textContent = (summary.risk_distribution && summary.risk_distribution.high) || 0;
            document.getElementById('avgScore').textContent = summary.average_decay_score != null ? summary.average_decay_score.toFixed(1) : '-';
            updateRiskChart(summary.risk_distribution);
            const fileList = document.getElementById('fileList');
            if (!highRisk.length) { fileList.innerHTML = '<li>No high-risk files found</li>'; return; }
            fileList.innerHTML = highRisk.map(file => '<li class="file-item ' + (file.risk_level || '') + '"><div class="file-name">' + (file.file_path || '') + '</div><div class="file-score">Decay Score: ' + (file.decay_score ?? 0).toFixed(1) + '</div><div>Risk: <strong>' + (file.risk_level || '').toUpperCase() + '</strong></div><div style="margin-top: 10px; font-size: 12px;">' + (file.recommendations || []).slice(0, 2).join('<br>') + '</div></li>').join('');
        }
        function updateRiskChart(distribution) {
            const ctx = document.getElementById('riskChart').getContext('2d');
            if (riskChart) riskChart.destroy();
            riskChart = new Chart(ctx, {
                type: 'doughnut',
                data: {
                    labels: ['Critical', 'High', 'Medium'],
                    datasets: [{
                        data: [distribution && distribution.critical || 0, distribution && distribution.high || 0, distribution && distribution.medium || 0],
                        backgroundColor: ['rgba(244, 67, 54, 0.8)', 'rgba(255, 152, 0, 0.8)', 'rgba(255, 235, 59, 0.8)'],
                        borderWidth: 0
                    }]
                },
                options: { responsive: true, maintainAspectRatio: true, plugins: { legend: { position: 'bottom' } } }
            });
        }
    </script>
</body>
</html>`;
    }

    public dispose() {
        AnalyticsPanel.currentPanel = undefined;
        this._panel.dispose();
        this._disposables.forEach((d) => d.dispose());
    }
}
