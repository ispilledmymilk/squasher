# CodeDecay - Predictive Technical Debt Analyzer

Predict which parts of your codebase will cause bugs or become hard to maintain **before** they do. CodeDecay analyzes code complexity, change history, dependencies, and known bug patterns to give every file a **decay score** and **risk level** (low → critical).

![CodeDecay](https://img.shields.io/badge/CodeDecay-Predict%20Technical%20Debt-blue)

## Features

- **Analyze current file** – Get a decay score and risk level for the active editor
- **Analyze entire project** – Run analysis on the whole repo (background)
- **Check before commit** – Run style and bug-prone checks on **staged** (or modified) files before you commit or push. Surfaces issues from code style and patterns common in AI-generated code (e.g. bare `except`, placeholders, hardcoded secrets, generic names).
- **Analysis panel** – View predicted issues, timeframe, and recommendations
- **Analytics dashboard** – Risk distribution and high-risk file list
- **Editor decorations** – See risk level at a glance (critical/high/medium)
- **High-risk quick pick** – Jump to the most at-risk files

## Requirements

- **CodeDecay backend** must be running. The extension talks to a local API (default: `http://localhost:8000`).
- Your project should be in a **git repository** (for change-history analysis).

To run the backend, see [CodeDecay backend setup](https://github.com/your-username/codedecay#quick-start) or use the standalone backend from the same repo.

## Installation

1. Install the extension from the [VS Code Marketplace](https://marketplace.visualstudio.com/items?itemName=YOUR-PUBLISHER.codedecay) (or install from VSIX).
2. Start the CodeDecay backend (see above).
3. Open a git repo in VS Code and run **CodeDecay: Analyze Current File** from the Command Palette.

## Usage

| Command | Description |
|--------|-------------|
| **CodeDecay: Analyze Current File** | Analyze the active file and show decay score & recommendations |
| **CodeDecay: Analyze Entire Project** | Analyze all supported files in the workspace (runs in background) |
| **CodeDecay: Check before commit** | Check staged (or modified) files for style and bug-prone issues before commit/push |
| **CodeDecay: Show Analysis Panel** | Open the detailed analysis panel |
| **CodeDecay: Show Analytics Dashboard** | View risk distribution and high-risk files |
| **CodeDecay: Show High-Risk Files** | Quick pick to open files above the risk threshold |

Right-click in the editor or in the file explorer → **CodeDecay: Analyze Current File** for quick access.

## Configuration

| Setting | Default | Description |
|--------|---------|-------------|
| `codedecay.apiUrl` | `http://localhost:8000` | URL of the CodeDecay backend API |
| `codedecay.riskThreshold` | `60` | Decay score (0–100) above which files are considered high risk |
| `codedecay.autoAnalyze` | `false` | Automatically analyze files when opened |

## How It Works

The backend runs four analyses per file:

1. **Complexity** – Cyclomatic complexity and maintainability (e.g. Radon for Python)
2. **Velocity** – Git churn, number of authors, time between changes
3. **Dependencies** – Import count and depth
4. **Patterns** – Similarity to known decay/bug patterns (vector search)

Results are combined into a **decay score** (0–100) and **risk level**, with predicted issues and recommended refactor timing.

## License

MIT License – see [LICENSE](LICENSE) file.
