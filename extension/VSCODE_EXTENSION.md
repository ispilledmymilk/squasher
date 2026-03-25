# CodeDecay as a VS Code Extension

This folder is the **VS Code extension** for CodeDecay. It talks to the CodeDecay backend API to analyze files and show decay scores, risk levels, and recommendations.

## Run the extension (development)

1. **Start the backend** (required):
   ```bash
   cd ../backend
   source venv/bin/activate
   python -m api.main
   ```
   Keep this running. The extension uses `http://localhost:8000` by default.

2. **Open this folder in VS Code**:
   ```bash
   code "/Users/saipranavikasturi/Documents/projects/BUG PREVENTION BOT/codedecay/extension"
   ```
   Or: File → Open Folder → select the `extension` folder.

3. **Launch the extension**:
   - Press **F5**, or
   - Run → Start Debugging, or
   - Choose "Launch CodeDecay Extension" from the Run and Debug panel.

4. A new VS Code window opens (Extension Development Host). In that window:
   - Open any folder that is a **git repository**.
   - Open a code file (e.g. `.py`, `.ts`, `.js`).
   - **Command Palette** (Cmd+Shift+P / Ctrl+Shift+P) → **CodeDecay: Analyze Current File**.
   - Or right-click in the editor or in the file explorer → **CodeDecay: Analyze Current File**.

## Commands

| Command | Description |
|--------|-------------|
| **CodeDecay: Analyze Current File** | Run decay analysis on the active file |
| **CodeDecay: Analyze Entire Project** | Run analysis on the whole project (background) |
| **CodeDecay: Show Analysis Panel** | Open the analysis results panel |
| **CodeDecay: Show Analytics Dashboard** | Open the analytics dashboard (risk distribution, high-risk files) |
| **CodeDecay: Show High-Risk Files** | List files above the risk threshold |

## Settings

In VS Code: **Settings** → search for **CodeDecay**.

- **CodeDecay: Api Url** – Backend URL (default: `http://localhost:8000`).
- **CodeDecay: Risk Threshold** – Score (0–100) above which files are considered high risk (default: 60).
- **CodeDecay: Auto Analyze** – Analyze files automatically when opened (default: off).

## Package as .vsix (installable extension)

1. Install the packaging tool once:
   ```bash
   npm install -g @vscode/vsce
   ```

2. From the **extension** folder:
   ```bash
   npm run compile
   npm run package
   ```
   This creates `codedecay-1.0.0.vsix` in the same folder.

3. **Install the .vsix** in VS Code:
   - Command Palette → **Extensions: Install from VSIX...**
   - Select `codedecay-1.0.0.vsix`.

   After that, CodeDecay will appear in your Extensions sidebar. You still need the backend running for analysis to work.

## Publish to the Marketplace

1. Create a publisher at [https://marketplace.visualstudio.com/manage](https://marketplace.visualstudio.com/manage).
2. In `package.json`, set `"publisher": "your-publisher-id"`.
3. Run `vsce publish` (requires a Personal Access Token from Azure DevOps).

For more detail, see [Publishing Extensions](https://code.visualstudio.com/api/working-with-extensions/publishing-extension).
