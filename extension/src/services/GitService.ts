import * as child_process from 'child_process';
import * as fs from 'fs';
import * as path from 'path';
import { Logger } from '../utils/logger';

export class GitService {
    async getRepoRoot(filePath: string): Promise<string | null> {
        try {
            let currentDir = path.dirname(filePath);
            while (currentDir !== path.dirname(currentDir)) {
                const gitPath = path.join(currentDir, '.git');
                if (fs.existsSync(gitPath)) {
                    Logger.log(`Found git repo at: ${currentDir}`);
                    return currentDir;
                }
                currentDir = path.dirname(currentDir);
            }
            Logger.log(`No git repo found for: ${filePath}`);
            return null;
        } catch (error) {
            Logger.error('Error finding git repo', error);
            return null;
        }
    }

    async isGitRepo(dirPath: string): Promise<boolean> {
        const gitPath = path.join(dirPath, '.git');
        return fs.existsSync(gitPath);
    }

    /** Get full paths of files currently staged for commit. */
    async getStagedFiles(repoRoot: string): Promise<string[]> {
        return new Promise((resolve) => {
            child_process.exec(
                'git diff --name-only --cached',
                { cwd: repoRoot, maxBuffer: 1024 * 1024 },
                (err, stdout) => {
                    if (err) {
                        Logger.error('Error getting staged files', err);
                        resolve([]);
                        return;
                    }
                    const names = stdout.trim().split(/\r?\n/).filter(Boolean);
                    const fullPaths = names.map((f) =>
                        path.isAbsolute(f) ? f : path.join(repoRoot, f)
                    );
                    resolve(fullPaths);
                }
            );
        });
    }

    /** Get full paths of modified (unstaged) files. */
    async getModifiedFiles(repoRoot: string): Promise<string[]> {
        return new Promise((resolve) => {
            child_process.exec(
                'git diff --name-only',
                { cwd: repoRoot, maxBuffer: 1024 * 1024 },
                (err, stdout) => {
                    if (err) {
                        Logger.error('Error getting modified files', err);
                        resolve([]);
                        return;
                    }
                    const names = stdout.trim().split(/\r?\n/).filter(Boolean);
                    const fullPaths = names.map((f) =>
                        path.isAbsolute(f) ? f : path.join(repoRoot, f)
                    );
                    resolve(fullPaths);
                }
            );
        });
    }
}
