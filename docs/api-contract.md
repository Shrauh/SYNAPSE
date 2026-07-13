# SYNAPSE API Contract

## Base URL

```
http://localhost:8000
```

---

# 1. GET /incidents

Returns a list of all incidents.

### Response 200

```json
[
  {
    "id": "inc_001",
    "service": "payment-service",
    "severity": "High",
    "status": "Open",
    "timestamp": "2026-07-11T10:00:00Z"
  },
  {
    "id": "inc_002",
    "service": "order-service",
    "severity": "Medium",
    "status": "Resolved",
    "timestamp": "2026-07-11T09:15:00Z"
  },
  {
    "id": "inc_003",
    "service": "user-service",
    "severity": "Low",
    "status": "Open",
    "timestamp": "2026-07-11T08:45:00Z"
  }
]
```

---

# 2. GET /incidents/{id}

Returns complete details of a specific incident.

### Example

```
GET /incidents/inc_001
```

### Response 200

```json
{
  "id": "inc_001",
  "service": "payment-service",
  "severity": "High",
  "status": "Open",
  "title": "Payment API Failure",
  "description": "Customers are unable to complete payments due to API timeout.",
  "owner": "Payments Team",
  "created_at": "2026-07-11T10:00:00Z",
  "updated_at": "2026-07-11T10:20:00Z"
}
```

---

# 3. GET /incidents/{id}/causal-graph

Returns a causal dependency graph for an incident.

### Example

```
GET /incidents/inc_001/causal-graph
```

### Response 200

```json
{
  "nodes": [
    {
      "id": "gateway",
      "label": "API Gateway"
    },
    {
      "id": "payment",
      "label": "Payment Service"
    },
    {
      "id": "database",
      "label": "Database"
    }
  ],
  "edges": [
    {
      "source": "gateway",
      "target": "payment"
    },
    {
      "source": "payment",
      "target": "database"
    }
  ]
}
```

---

# 4. GET /incidents/{id}/report

Returns an AI-generated incident report.

### Example

```
GET /incidents/inc_001/report
```

### Response 200

```json
{
  "incident_id": "inc_001",
  "summary": "Payment API experienced increased latency due to database connection saturation.",
  "root_cause": "High database load.",
  "impact": "Payment requests failed for approximately 15 minutes.",
  "recommendation": [
    "Restart payment service.",
    "Scale database resources.",
    "Monitor API latency."
  ]
}
```

---

# 5. POST /runbooks

Uploads a runbook document.

### Request

```
Content-Type: multipart/form-data
```

Field

```
file
```

### Response 201

```json
{
  "message": "Runbook uploaded successfully.",
  "filename": "payment-runbook.pdf",
  "status": "Stored"
}
```

---

# 6. GET /metrics

Returns dashboard metrics.

### Response 200

```json
{
  "total_incidents": 15,
  "open_incidents": 4,
  "resolved_incidents": 11,
  "critical_incidents": 2,
  "average_resolution_time": "18 minutes"
}
```

---

# Status Codes

| Status Code | Meaning |
|-------------|---------|
| 200 | Success |
| 201 | Resource Created |
| 400 | Bad Request |
| 404 | Incident Not Found |
| 500 | Internal Server Error |

---

# Notes

- All responses use JSON except file upload.
- Time is represented in ISO 8601 UTC format.
- IDs are unique strings.
- Authentication is not included in the MVP.
