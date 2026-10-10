# SYNAPSE Setup Guide

## Prerequisites
- Python 3.12+
- Node.js 20+
- Docker Desktop (with K8s enabled)
- Ollama installed

## Step 1: Backend
```bash
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## Step 2: Frontend
```bash
cd frontend
npm install
npm run dev
# Open http://localhost:5173
```

## Step 3: Ollama (Optional — better explanations)
```bash
ollama pull llama3.2:3b
# Set LLM_PROVIDER=ollama in backend/.env
```

## Step 4: Online Boutique on K8s (Optional)
```bash
kubectl apply -f infrastructure/k8s/online-boutique.yaml
kubectl port-forward svc/prometheus 9090:9090
```

## Step 5: Test the Pipeline
```bash
# Trigger simulation
curl -X POST http://localhost:8000/api/v1/rca/simulate \
  -H 'Content-Type: application/json' \
  -d '{"fault_type": "latency_spike", "root_cause_service": "payment-service"}'

# Check result
curl http://localhost:8000/api/v1/incidents
```

## Common Issues

| Issue | Fix |
|-------|-----|
| `ModuleNotFoundError` | Run `pip install -r requirements.txt` |
| K8s pods not found | Run `kubectl get pods` to check status |
| Ollama not responding | Run `ollama serve` first |
| Port 8000 in use | Kill existing process or change port |
