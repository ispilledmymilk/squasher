# How to Run CodeDecay

## 1. One-time setup

From the **codedecay** folder:

```bash
cd "/Users/saipranavikasturi/Documents/projects/BUG PREVENTION BOT/codedecay"

# Create venv and install Python deps
python3 -m venv backend/venv
source backend/venv/bin/activate   # Windows: backend\venv\Scripts\activate
pip install -r requirements.txt

# Optional: seed pattern DB for better predictions
python scripts/seed_data.py
```

## 2. Start the backend (the “bot”)

From **codedecay**:

```bash
cd backend
source venv/bin/activate
python -m api.main
```

You should see:
- `CodeDecay API starting. Server: localhost:8000`
- API: http://localhost:8000
- Docs: http://localhost:8000/docs

## 3. Run an analysis

**Option A – API (curl)**

With the backend running:

```bash
# Health check
curl http://localhost:8000/health

# Analyze a file (use real paths)
curl -X POST http://localhost:8000/api/analysis/file \
  -H "Content-Type: application/json" \
  -d '{"file_path": "/path/to/your/file.py", "repo_path": "/path/to/your/repo"}'
```

**Option B – VS Code extension**

1. Open `codedecay/extension` in VS Code.
2. Press **F5** (Extension Development Host).
3. In the new window, open a repo.
4. Command Palette (**Cmd+Shift+P** / **Ctrl+Shift+P**) → **CodeDecay: Analyze Current File**.

## 4. Stop the backend

In the terminal where the backend is running, press **Ctrl+C**.
