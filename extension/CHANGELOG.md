# Change Log

All notable changes to the CodeDecay extension will be documented in this file.

## [1.0.0] - 2025-03-17

### Added

- **CodeDecay: Analyze Current File** – Analyze the active file and show decay score and risk level
- **CodeDecay: Analyze Entire Project** – Background analysis for the whole workspace
- **CodeDecay: Show Analysis Panel** – Webview panel with predicted issues and recommendations
- **CodeDecay: Show Analytics Dashboard** – Risk distribution chart and high-risk file list
- **CodeDecay: Show High-Risk Files** – Quick pick to open high-risk files
- Editor decorations for risk level (critical / high / medium) on the first line
- Context menu: right-click in editor or explorer to analyze current file
- Settings: `codedecay.apiUrl`, `codedecay.riskThreshold`, `codedecay.autoAnalyze`
- Status bar item to open the analysis panel

### Requirements

- CodeDecay backend running (default: http://localhost:8000)
- Workspace must be a git repository for full analysis
