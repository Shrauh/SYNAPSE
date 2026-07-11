# SYNAPSE API Contract

## GET /incidents

Response 200

[
  {
    "id": "inc_001",
    "service": "payment-service",
    "severity": "high",
    "status": "open",
    "timestamp": "2026-07-11T10:00:00Z"
  }
]

## GET /incidents/{id}

Response 200

{
  "id": "inc_001",
  "service": "payment-service",
  "severity": "high",
  "status": "open"
}

## GET /incidents/{id}/causal-graph

Response 200

{
  "nodes": [],
  "edges": []
}

## GET /incidents/{id}/report

Response 200

{
  "report": "AI generated report"
}

## POST /runbooks

Response 201

{
  "message": "Runbook uploaded"
}

## GET /metrics

Response 200

{
  "total_incidents": 10,
  "open_incidents": 2
}
