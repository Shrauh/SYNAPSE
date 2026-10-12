# SYNAPSE — Complete Setup Guide

## Quick Start (Demo Mode — No External Dependencies)

### Prerequisites
- Python 3.10+
- Node.js 18+
- Git

### Backend Setup
```bash
cd backend
python -m venv venv
# Windows: .\venv\Scripts\activate
# Linux/Mac: source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Frontend Setup
```bash
cd frontend
npm install
npm run dev
# Open http://localhost:5173
```

## Upgrade: Install PyTorch Geometric (Real GNN instead of statistical fallback)

```bash
pip install torch-geometric
# Or for specific CUDA version:
pip install torch-geometric --find-links https://data.pyg.org/whl/torch-2.0.0+cu118.html
```

**Impact:** Without torch-geometric, SYNAPSE uses a simple z-score fallback for anomaly detection instead of the full GAT-VAE graph neural network.

## Upgrade: Connect Real LLM (Instead of mock templates)

### Option A: OpenAI API
Edit `backend/.env`:
```
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-your-key-here
OPENAI_MODEL=gpt-4o-mini
```

### Option B: Local Ollama (Free, Private)
```bash
# Install Ollama from https://ollama.ai
ollama pull llama3.2:3b
```
Edit `backend/.env`:
```
LLM_PROVIDER=ollama
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2:3b
```

## Upgrade: Connect Real Kubernetes Cluster

### Prerequisites
- kubectl configured (`kubectl cluster-info` works)
- A running K8s cluster (minikube, kind, EKS, GKE, AKS)

### Deploy Online Boutique
```bash
kubectl apply -f infrastructure/k8s/online-boutique.yaml
```

### Switch SYNAPSE to monitor it
In the UI, click the system dropdown and select your namespace, or:
```bash
curl -X POST http://localhost:8000/api/v1/system/switch -H 'Content-Type: application/json' -d '{"system": "custom", "namespace": "default"}'
```

## Upgrade: Connect Prometheus (Real Metrics)

```bash
# Deploy Prometheus
kubectl apply -f infrastructure/k8s/prometheus.yaml
# Or use docker-compose
cd infrastructure && docker-compose up -d prometheus
```

Edit `backend/.env`:
```
PROMETHEUS_URL=http://localhost:9090
```

## Upgrade: Slack/Teams Notifications

Edit `backend/.env`:
```
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/T.../B.../xxx
TEAMS_WEBHOOK_URL=https://outlook.office.com/webhook/...
NOTIFY_ON_COMPLETE=true
```

## Upgrade: Docker Compose (Full Stack)

```bash
# Application only
docker-compose up -d

# Full infrastructure (Prometheus + Alertmanager + Loki + mock services)
cd infrastructure
docker-compose up -d
```

## Environment Variables Reference

| Variable | Default / Current | Description |
|----------|---------|-------------|
| LLM_PROVIDER | mock | `mock`, `openai`, `ollama` |
| OPENAI_API_KEY | (empty) | Required if LLM_PROVIDER=openai |
| OPENAI_MODEL | gpt-4o-mini | OpenAI model name |
| OLLAMA_URL | http://localhost:11434 | Ollama server URL |
| OLLAMA_MODEL | llama3.2:3b | Ollama model name |
| PROMETHEUS_URL | http://localhost:9090 | Prometheus endpoint |
| K8S_NAMESPACE | default | Target K8s namespace |
| RECOVERY_DRY_RUN | true | Set false for real kubectl execution |
| ANOMALY_THRESHOLD | 0.6 | GNN anomaly detection threshold |
| DATABASE_URL | sqlite+aiosqlite:///./synapse.db | Database connection |
| SLACK_WEBHOOK_URL | (empty) | Slack incoming webhook |
| TEAMS_WEBHOOK_URL | (empty) | Teams incoming webhook |
| NOTIFY_ON_COMPLETE | false | Send notifications when auto-remediation completes |
| DASHBOARD_URL | http://localhost:5173 | Base URL for frontend dashboard |
| DEBUG | false | Enable debug mode |
| LOG_LEVEL | WARNING | Logging verbosity (DEBUG, INFO, WARNING, ERROR) |

## Architecture Modes

| Feature | Demo Mode | Production Mode |
|---------|-----------|------------------|
| Data Source | Synthetic simulator | Prometheus + K8s live metrics |
| Anomaly Detection | Statistical fallback | GAT-VAE GNN (needs torch-geometric) |
| LLM Reasoning | Mock templates | OpenAI GPT-4o or local Ollama |
| Recovery | Dry-run logging | Real kubectl commands |
| Notifications | Disabled | Slack + Teams webhooks |
| Database | SQLite | PostgreSQL for production |
| Service Discovery | Hardcoded topologies | Dynamic kubectl + Prometheus targets |
