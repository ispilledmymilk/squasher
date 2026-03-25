import * as vscode from 'vscode';

export class Logger {
    private static outputChannel: vscode.OutputChannel;

    static initialize() {
        if (!this.outputChannel) {
            this.outputChannel = vscode.window.createOutputChannel('CodeDecay');
        }
    }

    static log(message: string, ...args: unknown[]) {
        if (!this.outputChannel) this.initialize();
        const timestamp = new Date().toISOString();
        this.outputChannel.appendLine(
            `[${timestamp}] ${message} ${args.length > 0 ? JSON.stringify(args) : ''}`
        );
    }

    static error(message: string, error?: unknown) {
        if (!this.outputChannel) this.initialize();
        const timestamp = new Date().toISOString();
        this.outputChannel.appendLine(`[${timestamp}] ERROR: ${message}`);
        if (error) {
            this.outputChannel.appendLine(JSON.stringify(error, null, 2));
        }
    }

    static show() {
        if (!this.outputChannel) this.initialize();
        this.outputChannel.show();
    }
}
