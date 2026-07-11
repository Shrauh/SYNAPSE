# SYNAPSE API Contract

This document defines the API endpoints for the SYNAPSE AIOps platform.

---

## 1. GET /incidents

Returns a list of all incidents.

### Response (200)

```json
[
  {
    "id": "inc_001",
    "service": "payment-service",
    "severity": "high",
    "status": "open",
    "timestamp": "2026-07-11T10:00:00Z"
  }
]
```

---

## 2. GET /incidents/{id}

Returns details of a specific incident.

### Response (200)

```json
{
  "id": "inc_001",
  "service": "payment-service",
  "severity": "high",
  "status": "open",
  "description": "Payment requests are failing.",
  "timestamp": "2026-07-11T10:00:00Z"
}
```

---

## 3. GET /incidents/{id}/causal-graph

Returns the causal graph for an incident.

### Response (200)

```json
{
  "nodes": [
    {
      "id": "payment-service",
      "label": "Payment Service"
    },
    {
      "id": "database",
      "label": "Database"
    }
  ],
  "edges": [
    {
      "source": "database",
      "target": "payment-service"
    }
  ]
}
```

---

## 4. GET /incidents/{id}/report

Returns an AI-generated incident report.

### Response (200)

```json
{
  "incident_id": "inc_001",
  "summary": "Database latency caused payment failures.",
  "root_cause": "High database response time.",
  "recommendation": "Restart database service and monitor latency."
}
```

---

## 5. POST /runbooks

Uploads a runbook.

### Request

```json
{
  "title": "Restart Database",
  "content": "Step 1: Stop database. Step 2: Restart database."
}
```

### Response (201)

```json
{
  "message": "Runbook uploaded successfully."
}
```

---

## 6. GET /metrics

Returns system metrics.

### Response (200)

```json
{
  "cpu_usage": 45,
  "memory_usage": 68,
  "active_incidents": 2
}
```

---

# Status Codes

| Code | Meaning |
|------|---------|
|200|Success|
|201|Created|
|400|Bad Request|
|404|Not Found|
|500|Internal Server Error|

