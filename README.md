# SYNAPSE — Autonomous Microservice Root Cause Analysis

> AI-powered AIOps platform combining Graph Neural Networks, Causal Inference, and LLM reasoning to automatically detect and explain microservice failures.

[![FSE'26 Compatible](https://img.shields.io/badge/Benchmark-RCAEval%20FSE'26-blue)](https://github.com/phamquiluan/RCAEval)
[![Python](https://img.shields.io/badge/Python-3.12-green)]()
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green)]()
[![React](https://img.shields.io/badge/React-18-blue)]()

## What is SYNAPSE?

SYNAPSE solves the **30–90 minute manual diagnosis problem** in microservice incidents. When one service fails and cascades across a system, SYNAPSE:

1. **Detects** anomalies using a VAE-GNN (Variational Autoencoder + Graph Attention Network)
2. **Identifies** the root cause using DECI causal inference with NOTEARS acyclicity constraint  
3. **Explains** the failure in plain English using a local LLM (Ollama/llama3.2)
4. **Recovers** automatically with real `kubectl` commands

## Architecture

```
Metrics (Prometheus / Push) → VAE-GNN Anomaly Detection
                           → DECI Causal Discovery
                           → LLM Explanation (Ollama)
                           → Recovery Engine (kubectl)
                           → Dashboard (React)
```

## Quick Start

### Option 1: Docker Compose (Recommended)
```bash
git clone https://github.com/Shrauh/SYNAPSE
cd SYNAPSE
docker-compose up -d
# Open http://localhost:5173
```

### Option 2: Local Development
```bash
# Backend
cd backend
python -m venv venv
venv\Scripts\activate  # Windows
pip install -r requirements.txt
uvicorn app.main:app --reload

# Frontend (new terminal)
cd frontend
npm install
npm run dev
```

## Multi-System Support

SYNAPSE monitors **any microservice system** — switch live without restart:

| System | Services | How |
|--------|----------|-----|
| Google Online Boutique | 10 services | K8s auto-discovery |
| FinTech Stack | 4 services | K8s auto-discovery |
| HealthCare Stack | 4 services | K8s auto-discovery |
| Any K8s namespace | Auto-detected | POST /api/v1/system/switch |
| Any other system | Any | Push metrics via HTTP |

```bash
# Switch to FinTech in 1 command
curl -X POST http://localhost:8000/api/v1/system/switch \
  -H 'Content-Type: application/json' \
  -d '{"system": "fintech"}'
```

## Benchmark Results (RCAEval)

SYNAPSE evaluated against [RCAEval](https://github.com/phamquiluan/RCAEval) standard benchmarks:

| Method | Avg@5 |
|--------|-------|
| MicroRCA | 0.576 |
| BARO (best baseline) | 0.601 |
| **SYNAPSE (ours)** | **0.73+** |

Metrics: PR@1, PR@3, PR@5, Avg@5, Avg@10, MRR

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `POST /api/v1/rca/simulate` | Trigger RCA on fault injection |
| `GET  /api/v1/incidents` | List all incidents |
| `GET  /api/v1/incidents/{id}/report` | Get AI-generated report |
| `POST /api/v1/system/switch` | Switch monitored system |
| `GET  /api/v1/eval/benchmark` | RCAEval benchmark results |
| `POST /api/v1/k8s/detect-and-recover` | Live K8s detection + recovery |

Full docs: http://localhost:8000/docs

## Tech Stack

- **Backend**: FastAPI + Python 3.12
- **AI**: PyTorch (VAE-GNN), DECI Causal Inference, ChromaDB (RAG)
- **LLM**: Ollama (llama3.2:3b) — runs locally, no API key needed
- **Database**: SQLite (dev) / PostgreSQL (prod)
- **Frontend**: React 18 + TypeScript + Vite
- **Infrastructure**: Kubernetes, Prometheus, Docker

## Team

K.K. Wagh IEER, Nashik — Department of AI & Data Science  
Guide: Dr. Sneha Khaire
