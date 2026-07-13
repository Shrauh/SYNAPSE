# SYNAPSE

AIOps platform for automated Root Cause Analysis of microservice failures using **Graph Neural Networks**, **Causal Inference**, and **LLM-powered reasoning** with **Continual Learning**.

---

## Architecture

```
Microservice Metrics → Ingestion → GNN Anomaly Detection → Causal Inference → LLM Reasoning → RCA Report
                                         ↓                       ↓
                                   Continual Learning       Topology Validation
                                   (EWC + Replay)          (Dependency Graph)
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend API | Python, FastAPI |
| GNN | PyTorch + PyTorch Geometric (GAT Autoencoder) |
| Causal Inference | causal-learn (PC Algorithm) |
| LLM | OpenAI API / Mock (configurable) |
| Continual Learning | EWC + Experience Replay |
| Meta-Learning | MAML (few-shot adaptation) |
| Database | SQLAlchemy + aiosqlite (dev) / PostgreSQL (prod) |
| Containerization | Docker |

## Quick Start

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Visit `http://localhost:8000/docs` for the interactive API docs.

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/health` | GET | Health check |
| `/api/v1/metrics` | GET | System metrics |
| `/api/v1/graph/current` | GET | Service dependency graph |
| `/api/v1/incidents` | GET/POST | List/create incidents |
| `/api/v1/incidents/{id}` | GET | Incident details |
| `/api/v1/incidents/{id}/report` | GET | AI-generated RCA report |
| `/api/v1/incidents/{id}/causal-graph` | GET | Causal DAG |
| `/api/v1/rca/trigger` | POST | Trigger RCA pipeline |
| `/api/v1/rca/simulate` | POST | Simulate fault + run RCA |
| `/api/v1/model/status` | GET | AI model status |
| `/api/v1/live` | WS | Live anomaly streaming |

## Testing

```bash
cd backend
python -m pytest tests/ -v
```

## Team

- **Shravani** — Backend + AI Module (GNN, LLM, Causal Inference)
- **Teammates** — Frontend Dashboard
