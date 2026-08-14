"""
SYNAPSE Monitoring Configuration.

Defines which services to monitor and their expected topology
for the real-time observability pipeline.
"""

# Service topology - defines the dependency graph
SERVICE_TOPOLOGY = {
    "api-gateway": {
        "type": "gateway",
        "port": 8080,
        "downstream": ["auth-service", "user-service", "order-service"],
    },
    "auth-service": {
        "type": "core",
        "port": 8081,
        "downstream": [],
    },
    "user-service": {
        "type": "core",
        "port": 8082,
        "downstream": [],
    },
    "order-service": {
        "type": "business",
        "port": 8083,
        "downstream": ["payment-service"],
    },
    "payment-service": {
        "type": "business",
        "port": 8085,
        "downstream": [],
    },
}

# Monitoring thresholds
ANOMALY_THRESHOLD = 0.5
CRITICAL_THRESHOLD = 0.8
SCRAPE_INTERVAL = 30  # seconds
WINDOW_SIZE = 300  # 5 minutes

# Severity escalation rules
SEVERITY_CONFIG = {
    "L1_MAX_SERVICES": 1,
    "L2_MAX_SERVICES": 3,
    "L3_MIN_SERVICES": 4,
    "L4_RECURRENCE_THRESHOLD": 3,
    "L4_RECURRENCE_WINDOW_DAYS": 30,
    "MIN_CONFIDENCE_FOR_AUTOFIX": 0.7,
}
