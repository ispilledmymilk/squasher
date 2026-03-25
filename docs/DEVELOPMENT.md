# CodeDecay QA — Development

## Setup

From `codedecay/`:

```bash
./scripts/setup.sh
# or manually: python3 -m venv backend/venv && source backend/venv/bin/activate && pip install -r requirements.txt
cd backend && source venv/bin/activate && python -m api.main
```

Extension: open `extension/` in VS Code, **F5** for Extension Development Host.

## Environment

Copy `.env.example` → `.env`. Important keys:

- `OPENAI_API_KEY` — enables **PatternAgent** LLM summary (`OPENAI_MODEL` optional, default `gpt-4o-mini`).
- `API_SECRET_KEY` — locks HTTP routes; set `codedecay.apiSecret` in the extension.
- `GITHUB_TOKEN` — optional private GitHub clone for `/api/analysis/github`.

## Tests

```bash
cd backend
source venv/bin/activate
PYTHONPATH=. pytest ../tests -q
```

## Train decay model (optional)

```bash
python scripts/train_model.py
```

Writes `data/models/decay_model.pkl` (synthetic bootstrap). Replace with real `(X, y)` from `MetricsStore` when you add an export pipeline.

## LangGraph vs sequential

If `langgraph` fails to import or compile, the server logs **sequential mode**; behavior stays the same for API consumers.

## Code map

- **Orchestration:** `backend/orchestrator/langgraph_workflow.py`
- **Progress:** `backend/utils/progress_bus.py` + `backend/api/main.py` lifespan
- **Blueprint helpers:** `complexity_calculator`, `change_frequency`, `pattern_matcher`, `github_fetcher`, `model_trainer`
