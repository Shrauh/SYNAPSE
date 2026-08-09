# SYNAPSE Demo Infrastructure

This directory contains the demo microservices and observability stack required to run the SYNAPSE AIOps system on real-time data instead of simulated scenarios.

## Getting Started

To spin up the entire cluster of microservices and the observability tools (Prometheus, Jaeger, Loki), run:

```bash
cd d:\Codes\SYNAPSE\infrastructure
docker-compose up -d
```

## Observability Dashboards

Once running, you can access the telemetry systems:
- **Prometheus** (Metrics): [http://localhost:9090](http://localhost:9090)
- **Jaeger** (Traces): [http://localhost:16686](http://localhost:16686)

## Fault Injection API

Each mock service provides a `/fault` endpoint to dynamically inject failures and test the SYNAPSE system's detection capabilities. You can inject latency, errors, and system faults.

### Inject Latency
Add a 2000ms delay to the order service:
```bash
curl -X POST "http://localhost:8083/fault?latency_ms=2000"
```

### Inject Errors
Cause the authentication service to return `500 Internal Server Error` for 50% of requests:
```bash
curl -X POST "http://localhost:8081/fault?error_rate=0.5"
```

### Inject Memory Leaks
Simulate a memory leak (100MB) in the payment service:
```bash
curl -X POST "http://localhost:8085/fault?memory_leak_mb=100"
```

### Clear Faults
To return a service to normal operation:
```bash
curl -X POST "http://localhost:8083/fault/clear"
```

## Connecting SYNAPSE

Configure the main SYNAPSE system to use the Prometheus endpoint at `http://localhost:9090` and the Jaeger collector in its configuration settings. The demo services will stream real-time operational data into these tools, allowing SYNAPSE's AI orchestrator to detect anomalies dynamically based on the faults you inject.
