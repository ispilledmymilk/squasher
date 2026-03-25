import * as vscode from 'vscode';

export class Config {
    static getApiUrl(): string {
        const config = vscode.workspace.getConfiguration('codedecay');
        return config.get('apiUrl', 'http://localhost:8000');
    }

    static setApiUrl(url: string) {
        const config = vscode.workspace.getConfiguration('codedecay');
        config.update('apiUrl', url, vscode.ConfigurationTarget.Global);
    }
}