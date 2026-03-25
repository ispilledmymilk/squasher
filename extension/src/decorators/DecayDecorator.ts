import * as vscode from 'vscode';
import { Logger } from '../utils/logger';

export class DecayDecorator {
    private criticalDecoration: vscode.TextEditorDecorationType;
    private highDecoration: vscode.TextEditorDecorationType;
    private mediumDecoration: vscode.TextEditorDecorationType;

    constructor() {
        this.criticalDecoration = vscode.window.createTextEditorDecorationType({
            backgroundColor: 'rgba(255, 0, 0, 0.2)',
            border: '2px solid rgba(255, 0, 0, 0.5)',
            isWholeLine: true,
            overviewRulerColor: 'red',
            overviewRulerLane: vscode.OverviewRulerLane.Right,
        });
        this.highDecoration = vscode.window.createTextEditorDecorationType({
            backgroundColor: 'rgba(255, 165, 0, 0.1)',
            border: '1px solid rgba(255, 165, 0, 0.4)',
            isWholeLine: true,
            overviewRulerColor: 'orange',
            overviewRulerLane: vscode.OverviewRulerLane.Right,
        });
        this.mediumDecoration = vscode.window.createTextEditorDecorationType({
            backgroundColor: 'rgba(255, 255, 0, 0.05)',
            isWholeLine: true,
            overviewRulerColor: 'yellow',
            overviewRulerLane: vscode.OverviewRulerLane.Right,
        });
    }

    updateDecorations(
        document: vscode.TextDocument,
        prediction: { risk_level?: string; decay_score?: number; predicted_issues?: Array<{ description?: string; timeframe?: string }>; recommendations?: string[]; confidence?: number }
    ) {
        const editor = vscode.window.activeTextEditor;
        if (!editor || editor.document.uri.toString() !== document.uri.toString()) {
            return;
        }
        const riskLevel = prediction.risk_level || 'low';
        const decayScore = prediction.decay_score ?? 0;
        Logger.log(
            `Updating decorations for ${document.fileName}: ${riskLevel} (${decayScore})`
        );
        editor.setDecorations(this.criticalDecoration, []);
        editor.setDecorations(this.highDecoration, []);
        editor.setDecorations(this.mediumDecoration, []);

        const range = new vscode.Range(0, 0, 0, Number.MAX_VALUE);
        const decoration: vscode.DecorationOptions = {
            range,
            hoverMessage: this.createHoverMessage(prediction),
        };

        if (riskLevel === 'critical') {
            editor.setDecorations(this.criticalDecoration, [decoration]);
        } else if (riskLevel === 'high') {
            editor.setDecorations(this.highDecoration, [decoration]);
        } else if (riskLevel === 'medium') {
            editor.setDecorations(this.mediumDecoration, [decoration]);
        }
    }

    private createHoverMessage(prediction: {
        decay_score?: number;
        risk_level?: string;
        confidence?: number;
        predicted_issues?: Array<{ description?: string; timeframe?: string }>;
        recommendations?: string[];
    }): vscode.MarkdownString {
        const md = new vscode.MarkdownString();
        md.supportHtml = true;
        md.isTrusted = true;
        md.appendMarkdown('## CodeDecay Analysis\n\n');
        md.appendMarkdown(
            `**Decay Score:** ${(prediction.decay_score ?? 0).toFixed(1)}/100\n\n`
        );
        md.appendMarkdown(
            `**Risk Level:** ${(prediction.risk_level || 'low').toUpperCase()}\n\n`
        );
        md.appendMarkdown(
            `**Confidence:** ${((prediction.confidence ?? 0) * 100).toFixed(0)}%\n\n`
        );
        if (
            prediction.predicted_issues &&
            prediction.predicted_issues.length > 0
        ) {
            md.appendMarkdown('### Predicted Issues\n\n');
            for (const issue of prediction.predicted_issues) {
                md.appendMarkdown(
                    `- ${issue.description ?? ''} (${issue.timeframe ?? ''})\n`
                );
            }
            md.appendMarkdown('\n');
        }
        if (
            prediction.recommendations &&
            prediction.recommendations.length > 0
        ) {
            md.appendMarkdown('### Recommendations\n\n');
            for (const rec of prediction.recommendations) {
                md.appendMarkdown(`- ${rec}\n`);
            }
        }
        return md;
    }

    dispose() {
        this.criticalDecoration.dispose();
        this.highDecoration.dispose();
        this.mediumDecoration.dispose();
    }
}
