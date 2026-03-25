# CodeDecay QA — HTTP API

Base URL: `http://localhost:8000` (configurable). Interactive docs: `/docs`.

## Auth

If `API_SECRET_KEY` is set, send header:

`Authorization: Bearer <API_SECRET_KEY>`

## Analysis

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/analysis/file` | Body: `{ "file_path", "repo_path" }`. Runs full agent graph. Uses a **background thread** so WebSocket progress events can flush during the run. |
| POST | `/api/analysis/project` | Background scan of repo (bounded file count/size). |
| POST | `/api/analysis/pre-commit` | Style / bug-prone checks on listed paths. |
| POST | `/api/analysis/github` | Clone or fetch GitHub URL; analyze up to `MAX_GITHUB_ANALYSIS_FILES` files (no local DB persist). |
| GET | `/api/analysis/status/{file_path}` | Latest stored prediction for a path. |

## Metrics

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/metrics/high-risk` | Query: `threshold` (default 70). |
| GET | `/api/metrics/summary` | Aggregate stats. |
| GET | `/api/metrics/file/{file_path}` | History for one file. |

## WebSocket

`WS /ws`

- Server broadcasts JSON strings, e.g.  
  `{ "type": "analysis_progress", "payload": { "step": "complexity", "file_path": "...", "repo_path": "...", "detail": {...} } }`
- Client can send `{ "type": "ping" }` → `{ "type": "pong" }`.
- Non-JSON text gets `{ "type": "echo", "data": "..." }`.

## Health

- `GET /health` — liveness  
- `GET /health/ready` — SQLite connectivity  
