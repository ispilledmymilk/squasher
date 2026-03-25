# CodeDecay QA — Production deployment

CodeDecay QA is a **server + VS Code extension** stack. Treat the API as an internal service: authenticate it, limit exposure, and run health checks in your orchestrator.

## Architecture

| Component | Role |
|-----------|------|
| **QA API** (FastAPI) | Analysis, pre-commit checks, metrics persistence (SQLite), optional ChromaDB |
| **VS Code extension** | Calls the API with `file_path` + `repo_path` (paths must be readable by the API process) |

**Important:** The API must run on a host that can read your repositories (same machine, shared volume, or agent that receives file contents — future enhancement).

## Security checklist

- [ ] Set `ENV=production`
- [ ] Set `API_SECRET_KEY` to a long random value (`openssl rand -hex 32`)
- [ ] Configure `CORS_ORIGINS` if a **browser** will call the API (comma-separated). VS Code extension requests usually do not require CORS.
- [ ] Set `EXPOSE_ERROR_DETAILS=false` so 500 responses do not leak internals
- [ ] Run the API behind a reverse proxy (TLS, rate limiting, IP allowlist)
- [ ] Do not expose `/docs` publicly without auth (optional: put API behind VPN only)
- [ ] Store `.env` outside the image; use secrets manager in Kubernetes/ECS
- [ ] Run the container as non-root (Dockerfile uses user `codedecay`)

## Configuration reference

| Variable | Description |
|----------|-------------|
| `ENV` | `development` or `production` |
| `API_SECRET_KEY` | If set, all `/api/*` routes require `Authorization: Bearer <token>` |
| `CORS_ORIGINS` | Comma-separated allowed origins |
| `EXPOSE_ERROR_DETAILS` | `true` only for debugging |
| `MAX_PRE_COMMIT_FILES` | Max files per pre-commit request (default 200) |
| `MAX_FILE_BYTES_FOR_SCAN` | Skip larger files (default 2 MiB) |
| `METRICS_DB_PATH` | SQLite path for persisted metrics |

## Health endpoints

- **`GET /health`** — Liveness (process up)
- **`GET /health/ready`** — Readiness (SQLite reachable). Use for Kubernetes `readinessProbe`.

## Docker

From repository root `codedecay/`:

```bash
docker compose build
docker compose up -d
```

Set secrets in `.env` (from `.env.example`).

## VS Code extension (production)

1. Settings → **CodeDecay: Api Url** → your API base URL (e.g. `https://qa-api.internal.company`)
2. Settings → **CodeDecay: Api Secret** → same value as `API_SECRET_KEY` (if enabled)

## CI / pre-commit without VS Code

```bash
curl -sS -X POST "$QA_API/api/analysis/pre-commit" \
  -H "Authorization: Bearer $API_SECRET_KEY" \
  -H "Content-Type: application/json" \
  -d "{\"repo_path\":\"$CI_PROJECT_DIR\",\"file_paths\":[\"$CI_PROJECT_DIR/src/foo.py\"]}"
```

Exit non-zero in CI if `ok` is `false` in the JSON response.

## Tests (CI)

```bash
cd codedecay
pip install -r requirements.txt
pytest
```

Example GitHub Actions job (run from repo root; set `working-directory` to `codedecay` if the project is in a subfolder):

```yaml
- uses: actions/setup-python@v5
  with:
    python-version: "3.12"
- run: pip install -r requirements.txt && pytest tests/ -q
  working-directory: codedecay
```

## Operational notes

- **SQLite**: Single-writer; for multiple API replicas use a shared network filesystem or migrate metrics to PostgreSQL (future work).
- **ChromaDB**: Embedded path under `VECTOR_DB_PATH`; back up the volume for pattern RAG data.
- **Logs**: Structured text to stdout; ship with your log agent (CloudWatch, Datadog, etc.).
