# SYNAPSE — Teammate Setup Guide

## Prerequisites

| Tool | Install Link | Required |
|------|-------------|----------|
| **Python 3.12** | https://python.org/downloads | ✅ Yes |
| **Node.js 18+** | https://nodejs.org | ✅ Yes |
| **Git** | https://git-scm.com | ✅ Yes |
| **Docker Desktop** | https://docker.com/products/docker-desktop | ✅ Yes |
| **Ollama** | https://ollama.com | ✅ Yes |

### Windows Only (one-time)
Open **PowerShell as Admin** and run:
```powershell
dism.exe /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart
dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart
wsl --install
# Restart laptop after this
```

---

## Step 1: Clone the Repo

```bash
git clone https://github.com/Shrauh/SYNAPSE.git
cd SYNAPSE
git checkout shravani
```

---

## Step 2: Backend Setup

```bash
cd backend
pip install -r requirements.txt
```

### Run Backend
```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```
Backend runs at: **http://localhost:8000**
API docs at: **http://localhost:8000/docs**

### Run Tests
```bash
python -m pytest tests/ -v
```
Expected: **29+ tests pass**

---

## Step 3: Frontend Setup

```bash
cd frontend
npm install
npm run dev
```
Frontend runs at: **http://localhost:5173**

---

## Step 4: Ollama (Free Local LLM)

```bash
# Install Ollama from https://ollama.com
# Then pull the model:
ollama pull llama3.2:3b

# Test it works:
ollama run llama3.2:3b "What is root cause analysis?"
```

---

## Step 5: Docker Services (Real-time Monitoring)

### Pull Images
```bash
docker pull python:3.12-slim
docker pull prom/prometheus:latest
```

### Build Microservice Image
```bash
cd infrastructure/services
docker build -t synapse-service .
```

### Start Everything
```bash
# Create network
docker network create synapse-net

# Start 5 microservices
docker run -d --name payment-service --network synapse-net -p 8085:8085 -e SERVICE_NAME=payment-service -e SERVICE_PORT=8085 synapse-service
docker run -d --name auth-service --network synapse-net -p 8081:8081 -e SERVICE_NAME=auth-service -e SERVICE_PORT=8081 synapse-service
docker run -d --name user-service --network synapse-net -p 8082:8082 -e SERVICE_NAME=user-service -e SERVICE_PORT=8082 synapse-service
docker run -d --name order-service --network synapse-net -p 8083:8083 -e SERVICE_NAME=order-service -e SERVICE_PORT=8083 synapse-service
docker run -d --name api-gateway --network synapse-net -p 8080:8080 -e SERVICE_NAME=api-gateway -e SERVICE_PORT=8080 synapse-service

# Start Prometheus (update path to your local path)
docker run -d --name prometheus --network synapse-net -p 9090:9090 -v /path/to/SYNAPSE/infrastructure/prometheus/prometheus.yml:/etc/prometheus/prometheus.yml prom/prometheus:latest
```

### Verify
```bash
docker ps                              # Should show 6 containers
curl http://localhost:8080/health       # {"status":"healthy"}
curl http://localhost:8080/metrics      # Prometheus metrics
```

---

## Step 6: Demo — Inject a Fault

```powershell
# Inject 2-second latency into order-service
Invoke-WebRequest -Method POST -Uri "http://localhost:8083/fault?latency_ms=2000"

# Check Prometheus: http://localhost:9090
# Query: http_request_duration_seconds_sum

# Clear fault
Invoke-WebRequest -Method POST -Uri "http://localhost:8083/fault/clear"
```

---

## All URLs

| Service | URL |
|---------|-----|
| SYNAPSE Backend | http://localhost:8000 |
| SYNAPSE Frontend | http://localhost:5173 |
| API Docs (Swagger) | http://localhost:8000/docs |
| Prometheus | http://localhost:9090 |
| api-gateway | http://localhost:8080 |
| auth-service | http://localhost:8081 |
| user-service | http://localhost:8082 |
| order-service | http://localhost:8083 |
| payment-service | http://localhost:8085 |

---

## Cleanup

```bash
docker stop api-gateway auth-service user-service order-service payment-service prometheus
docker rm api-gateway auth-service user-service order-service payment-service prometheus
docker network rm synapse-net
```
