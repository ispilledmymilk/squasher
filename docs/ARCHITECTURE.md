# CodeDecay QA — Architecture

## High level

- **VS Code extension (TypeScript)** calls the **FastAPI** backend over HTTP (`/api/analysis/*`, `/api/metrics/*`).
- **WebSocket (`/ws`)** broadcasts **JSON** messages with `type: "analysis_progress"` while a file analysis runs (when the API uses a worker thread so the event loop can drain the queue).
- **Analysis** is a **LangGraph** `StateGraph` when `langgraph` imports succeed; otherwise the same steps run **sequentially** (same agents, same outputs).

## Agent pipeline (per file)

1. **ComplexityAgent** — Radon (via `ComplexityCalculator` / `CodeAnalyzer`), history from SQLite.
2. **VelocityAgent** — `GitAnalyzer` / `change_frequency` helpers.
3. **DependencyAgent** — import graph heuristics from source.
4. **PatternAgent** — `PatternMatcher` → ChromaDB RAG; optional **OpenAI** narrative review when `OPENAI_API_KEY` is set.
5. **DecayPredictor** — weighted risk score, recommendations, predicted issues.

**Pre-commit** uses **CodeStyleAgent** only (no full decay graph).

## Data

- **SQLite** (`metrics_store`) — per-file metrics and predictions.
- **ChromaDB** (`vector_store`) — decay + bug pattern embeddings (seed via `scripts/seed_data.py`).
- **GitHub cache** — shallow clones under `data/github_cache/` for remote analysis.

## Blueprint modules (explicit files)

| Module | Role |
|--------|------|
| `analyzers/complexity_calculator.py` | Radon CC, MI, LOC, comments |
| `analyzers/change_frequency.py` | Git churn wrappers |
| `ml/pattern_matcher.py` | RAG queries over Chroma |
| `data/github_fetcher.py` | `GitHubDataFetcher` → `prepare_github_workdir` |
| `ml/model_trainer.py` | Train/save `RandomForestRegressor` for decay |
| `utils/progress_bus.py` | Thread-safe progress → asyncio queue → WS |

See also [`PRODUCTION.md`](PRODUCTION.md) for deployment and auth.
