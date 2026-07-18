# SYNAPSE Backend — Local Run Guide

## Prerequisites
- Python 3.11 or 3.12 installed
- Git installed
- VS Code with the **Python** extension installed

---

## Step 1 — Open the Project in VS Code

```
File → Open Folder → D:\Codes\SYNAPSE
```

Then open a **new terminal** inside VS Code:
```
Terminal → New Terminal   (or Ctrl + `)
```

---

## Step 2 — Activate the Virtual Environment

The `venv` is already created inside `backend/`. Every time you open VS Code, run:

```powershell
cd backend
.\venv\Scripts\Activate.ps1
```

You should see `(venv)` appear at the start of your terminal prompt.

> **If you get a script execution error**, run this once:
> ```powershell
> Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
> ```

---

## Step 3 — Create Your `.env` File

```powershell
copy .env.example .env
```

Open `.env` and set:
```
LLM_PROVIDER=mock        # Use mock LLM (free, no API key needed)
ANOMALY_THRESHOLD=0.6
```

If you want real LLM responses (optional):
```
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-your-key-here
```

---

## Step 4 — Run the Backend Server

```powershell
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Open your browser: **http://localhost:8000/docs**

You'll see the full interactive Swagger UI with all endpoints.

---

## Step 5 — Test the Full RCA Pipeline

### Option A: Simulate a fault (easiest)
In the Swagger UI → `POST /api/v1/rca/simulate` → click Try it out:
```json
{
  "fault_type": "latency_spike",
  "root_cause_service": "database",
  "severity": "critical",
  "duration_minutes": 5
}
```

This will:
1. Generate synthetic metrics with a database latency spike
2. Train the GNN on normal data (first run only — takes ~10 seconds)
3. Detect anomalies with the GAT autoencoder
4. Run the PC causal algorithm to find root cause
5. Generate an LLM explanation
6. Return the full RCA report

### Option B: Get the RCA report
Take the `incident_id` from simulate response, then:
```
GET /api/v1/incidents/{incident_id}/report
```

### Option C: View the causal graph
```
GET /api/v1/incidents/{incident_id}/causal-graph
```

---

## Step 6 — Run Tests

```powershell
python -m pytest tests/ -v
```

---

## Complete Flow Diagram

```
You call POST /rca/simulate
         │
         ▼
[data/simulator.py]
  Generates 60 time-steps of metrics
  for 10 services with fault injection
  (database latency spikes → cascades to auth, api-gateway...)
         │
         ▼
[app/services/ingestion.py]
  Aggregates last 10 time-steps per service
  Normalizes with z-score
  Output: feature matrix [10 services × 5 features]
         │
         ▼
[app/services/graph_builder.py]
  Holds the dependency graph (NetworkX DiGraph)
  api-gateway → auth-service → database etc.
  Updates with live metric values
         │
         ▼
[app/ai_module/gnn/]
  model.py    → GAT Autoencoder (2-layer Graph Attention Network)
  train.py    → Trains on normal data (self-supervised, no labels)
  infer.py    → Computes anomaly score per service [0.0 → 1.0]
  Output: {"database": 0.95, "auth-service": 0.78, "api-gateway": 0.62}
         │
         ▼
[app/ai_module/causal/]
  discovery.py → PC Algorithm on anomalous services' time-series
  validate.py  → Removes edges that contradict the dependency graph
  dag_utils.py → Extracts root nodes (no incoming causal edges)
  Output: DAG: database → auth-service → api-gateway
          Root: database (0.95)
         │
         ▼
[app/ai_module/llm/]
  prompt_templates.py → Formats GNN + causal data into SRE prompt
  reasoner.py         → Calls mock/OpenAI, returns structured JSON
  cache.py            → Caches responses for same incident patterns
  Output: {
    "root_cause": "database",
    "confidence": 0.92,
    "explanation": "Database latency spike (+340%) caused...",
    "recommended_actions": ["Check slow query logs", ...]
  }
         │
         ▼
[app/ai_module/continual/]  (runs in background after each task)
  ewc.py          → Elastic Weight Consolidation (prevents forgetting)
  replay_buffer.py → Stores past samples for replay
  manager.py       → Coordinates EWC + replay during model updates

[app/ai_module/meta/maml.py]
  MAML adapter for few-shot adaptation to new fault types
         │
         ▼
[app/ai_module/orchestrator.py]
  Fuses all stages above into one pipeline
  Stores result to SQLite database
         │
         ▼
[app/api/]
  FastAPI endpoints serve the result to the frontend
  GET /incidents/{id}/report     → Full RCA explanation
  GET /incidents/{id}/causal-graph → DAG for visualization
  GET /graph/current              → Live service graph with anomaly scores
  WS  /live                       → Real-time anomaly streaming
```

---

## File Structure Reference

```
backend/
├── app/
│   ├── main.py                    ← FastAPI app entry point
│   ├── config.py                  ← All settings (reads .env)
│   ├── api/                       ← HTTP endpoints
│   │   ├── health.py              ← GET /health
│   │   ├── incidents.py           ← CRUD + RCA reports
│   │   ├── rca.py                 ← POST /rca/simulate, /rca/trigger
│   │   ├── graph.py               ← GET /graph/current
│   │   ├── model.py               ← GET /model/status
│   │   └── ws.py                  ← WebSocket /live
│   ├── ai_module/
│   │   ├── orchestrator.py        ← MAIN PIPELINE (start here to understand flow)
│   │   ├── gnn/                   ← Graph Neural Network
│   │   │   ├── model.py           ← GAT Autoencoder architecture
│   │   │   ├── train.py           ← Training loop
│   │   │   └── infer.py           ← Anomaly scoring
│   │   ├── causal/                ← Causal Inference
│   │   │   ├── discovery.py       ← PC Algorithm
│   │   │   ├── dag_utils.py       ← Root cause extraction
│   │   │   └── validate.py        ← Topology cross-check
│   │   ├── llm/                   ← LLM Reasoning
│   │   │   ├── reasoner.py        ← Calls mock/OpenAI
│   │   │   ├── prompt_templates.py← Prompt engineering
│   │   │   └── cache.py           ← Response caching
│   │   ├── continual/             ← Continual Learning
│   │   │   ├── ewc.py             ← Elastic Weight Consolidation
│   │   │   ├── replay_buffer.py   ← Experience replay
│   │   │   └── manager.py         ← Coordinates EWC + replay
│   │   └── meta/
│   │       └── maml.py            ← MAML few-shot adaptation
│   ├── db/
│   │   ├── database.py            ← SQLAlchemy async engine
│   │   └── models.py              ← Incident, RCAResult, ServiceMetric tables
│   └── services/
│       ├── ingestion.py           ← Feature extraction & normalization
│       └── graph_builder.py       ← NetworkX dependency graph
├── data/
│   └── simulator.py               ← Synthetic data generator
├── tests/
│   ├── test_api.py                ← API endpoint tests
│   ├── test_gnn.py                ← GNN model tests
│   ├── test_causal.py             ← Causal inference tests
│   └── test_pipeline.py           ← End-to-end pipeline tests
├── .env.example                   ← Copy to .env and edit
├── requirements.txt               ← All dependencies
├── pytest.ini                     ← Test configuration
├── Dockerfile                     ← Container build
└── docker-compose.yml             ← Multi-service orchestration
```

---

## VS Code Tips

1. **Select the venv interpreter**: `Ctrl+Shift+P` → "Python: Select Interpreter" → choose `backend/venv/Scripts/python.exe`
2. **Run/Debug the server**: Create `.vscode/launch.json` with uvicorn config
3. **Auto-reload**: `--reload` flag restarts server on every file save
