import * as vscode from 'vscode';
import { PreCommitIssue, PreCommitResult } from '../services/ApiService';
import { Logger } from '../utils/logger';

export class PreCommitReportPanel {
    public static currentPanel: PreCommitReportPanel | undefined;
    private readonly _panel: vscode.WebviewPanel;
    private _disposables: vscode.Disposable[] = [];

    private constructor(
        extensionUri: vscode.Uri,
        result: PreCommitResult
    ) {
        PreCommitReportPanel.currentPanel = this;
        this._panel = vscode.window.createWebviewPanel(
            'codedecayPreCommit',
            'CodeDecay – Check before commit',
            vscode.ViewColumn.One,
            { enableScripts: true }
        );
        this._panel.webview.html = this.getHtml(result);
        this._panel.onDidDispose(() => this.dispose(), null, this._disposables);
        this._panel.webview.onDidReceiveMessage(
            (msg: { command: string; file: string; line: number }) => {
                if (msg.command === 'openFile' && msg.file) {
                    vscode.workspace.openTextDocument(msg.file).then((doc) => {
                        vscode.window.showTextDocument(doc).then((editor) => {
                            if (msg.line > 0) {
                                const line = Math.max(0, msg.line - 1);
                                editor.revealRange(
                                    new vscode.Range(line, 0, line, 0),
                                    vscode.TextEditorRevealType.InCenter
                                );
                            }
                        });
                    });
                }
            },
            null,
            this._disposables
        );
    }

    public static show(extensionUri: vscode.Uri, result: PreCommitResult): void {
        if (PreCommitReportPanel.currentPanel) {
            PreCommitReportPanel.currentPanel._panel.reveal();
            PreCommitReportPanel.currentPanel._panel.webview.html =
                PreCommitReportPanel.currentPanel.getHtml(result);
            return;
        }
        new PreCommitReportPanel(extensionUri, result);
    }

    private getHtml(result: PreCommitResult): string {
        const s = result.by_severity;
        const ok = result.ok;
        const issues = result.issues || [];
        const rows = issues
            .map(
                (i: PreCommitIssue) => `
        <tr class="severity-${i.severity}">
          <td><button class="link" data-file="${escapeHtml(i.file_path)}" data-line="${i.line}">${escapeHtml(shortPath(i.file_path))}</button></td>
          <td>${i.line || '-'}</td>
          <td><span class="badge">${i.severity}</span></td>
          <td>${escapeHtml(i.type)}</td>
          <td>${escapeHtml(i.message)}</td>
        </tr>`
            )
            .join('');

        return `<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <style>
    body { font-family: var(--vscode-font-family); padding: 16px; color: var(--vscode-foreground); }
    .summary { margin-bottom: 16px; padding: 12px; border-radius: 8px; }
    .summary.pass { background: rgba(0,128,0,0.15); border: 1px solid rgba(0,128,0,0.4); }
    .summary.fail { background: rgba(200,0,0,0.15); border: 1px solid rgba(200,0,0,0.4); }
    .counts { display: flex; gap: 12px; margin: 8px 0; flex-wrap: wrap; }
    .count { padding: 4px 8px; border-radius: 4px; }
    .count.critical { background: #d32f2f; color: #fff; }
    .count.high { background: #f57c00; color: #fff; }
    .count.medium { background: #fbc02d; color: #000; }
    .count.low { background: #689f38; color: #fff; }
    table { width: 100%; border-collapse: collapse; font-size: 13px; }
    th, td { text-align: left; padding: 8px; border-bottom: 1px solid var(--vscode-widget-border); }
    .link { background: none; border: none; color: var(--vscode-textLink-foreground); cursor: pointer; text-decoration: underline; }
    .badge { font-size: 11px; padding: 2px 6px; border-radius: 4px; }
    .severity-critical .badge { background: #d32f2f; color: #fff; }
    .severity-high .badge { background: #f57c00; color: #fff; }
    .severity-medium .badge { background: #fbc02d; color: #000; }
    .severity-low .badge { background: #689f38; color: #fff; }
    .empty { color: var(--vscode-descriptionForeground); padding: 24px; text-align: center; }
  </style>
</head>
<body>
  <div class="summary ${ok ? 'pass' : 'fail'}">
    <strong>${ok ? '✓ OK to commit' : '⚠ Fix issues before commit'}</strong>
    <p>${escapeHtml(result.message)}</p>
    <div class="counts">
      <span class="count critical">Critical: ${s.critical}</span>
      <span class="count high">High: ${s.high}</span>
      <span class="count medium">Medium: ${s.medium}</span>
      <span class="count low">Low: ${s.low}</span>
    </div>
    <p>Files checked: ${result.files_checked} | With issues: ${result.files_with_issues}</p>
  </div>
  ${
      rows
          ? `<table><thead><tr><th>File</th><th>Line</th><th>Severity</th><th>Type</th><th>Message</th></tr></thead><tbody>${rows}</tbody></table>`
          : '<div class="empty">No issues to show.</div>'
  }
  <script>
    document.querySelectorAll('.link').forEach(btn => {
      btn.addEventListener('click', () => {
        const vscode = acquireVsCodeApi();
        vscode.postMessage({ command: 'openFile', file: btn.dataset.file, line: parseInt(btn.dataset.line || '0', 10) });
      });
    });
  </script>
</body>
</html>`;
    }

    public dispose(): void {
        PreCommitReportPanel.currentPanel = undefined;
        this._panel.dispose();
        this._disposables.forEach((d) => d.dispose());
    }
}

function escapeHtml(s: string): string {
    return s
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;');
}

function shortPath(p: string, maxLen = 60): string {
    if (p.length <= maxLen) return p;
    return '...' + p.slice(-(maxLen - 3));
}
