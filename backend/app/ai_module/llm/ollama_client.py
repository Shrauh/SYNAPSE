"""
Ollama LLM Integration for SYNAPSE.

Connects to a local Ollama instance for free, private LLM reasoning
instead of requiring OpenAI API keys.
"""
import httpx
import json
import logging
from typing import Optional, Dict, List

logger = logging.getLogger(__name__)

OLLAMA_BASE_URL = "http://localhost:11434"
DEFAULT_MODEL = "llama3.2:3b"


async def generate_rca_explanation(
    root_cause_service: str,
    fault_type: str,
    metric_deltas: Dict[str, Dict[str, str]],
    propagation_chain: str,
    confidence: float,
    severity_level: str = "L1",
) -> Dict[str, str]:
    """
    Generate RCA explanation using local Ollama LLM.

    Args:
        root_cause_service: The identified root cause service.
        fault_type: Type of fault (latency_spike, error_burst, etc.).
        metric_deltas: Dictionary of metric changes per service.
        propagation_chain: String showing fault propagation path.
        confidence: Causal confidence score (0-1).
        severity_level: Severity classification (L1-L4).

    Returns:
        Dictionary with 'explanation' and 'recommended_actions'.
    """
    prompt = _build_prompt(
        root_cause_service, fault_type, metric_deltas,
        propagation_chain, confidence, severity_level,
    )

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{OLLAMA_BASE_URL}/api/generate",
                json={
                    "model": DEFAULT_MODEL,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.3,
                        "num_predict": 512,
                    },
                },
            )
            response.raise_for_status()
            result = response.json()
            return _parse_response(result.get("response", ""))
    except httpx.ConnectError:
        logger.warning("Ollama not running. Using fallback explanation.")
        return _fallback_explanation(
            root_cause_service, fault_type, propagation_chain,
        )
    except Exception as e:
        logger.error(f"Ollama error: {e}")
        return _fallback_explanation(
            root_cause_service, fault_type, propagation_chain,
        )


def _build_prompt(
    service: str, fault: str, deltas: Dict,
    chain: str, confidence: float, severity: str,
) -> str:
    """Build the RCA analysis prompt for the LLM."""
    delta_text = ""
    for svc, metrics in (deltas or {}).items():
        changes = ", ".join(f"{k}: {v}" for k, v in metrics.items())
        delta_text += f"  - {svc}: {changes}\n"

    return f"""You are an AIOps expert analyzing a microservice incident.

ROOT CAUSE: {service}
FAULT TYPE: {fault}
SEVERITY: {severity}
CONFIDENCE: {confidence:.0%}
PROPAGATION: {chain}

METRIC CHANGES:
{delta_text or '  No detailed metrics available.'}

Provide a concise incident analysis in this exact format:

EXPLANATION: [2-3 sentence explanation of what happened and why]

ACTIONS:
1. [First recommended action]
2. [Second recommended action]
3. [Third recommended action]
4. [Fourth recommended action]
"""


def _parse_response(text: str) -> Dict[str, str]:
    """Parse LLM response into structured format."""
    explanation = ""
    actions = []

    lines = text.strip().split("\n")
    in_actions = False

    for line in lines:
        line = line.strip()
        if line.upper().startswith("EXPLANATION:"):
            explanation = line.split(":", 1)[1].strip()
            in_actions = False
        elif line.upper().startswith("ACTIONS:"):
            in_actions = True
        elif in_actions and line and line[0].isdigit():
            action = line.split(".", 1)[1].strip() if "." in line else line
            actions.append(action)
        elif not in_actions and explanation and line:
            explanation += " " + line

    return {
        "explanation": explanation or "Analysis completed.",
        "recommended_actions": actions or ["Investigate service logs"],
    }


def _fallback_explanation(
    service: str, fault: str, chain: str,
) -> Dict[str, str]:
    """Generate explanation without LLM (fallback)."""
    fault_desc = {
        "latency_spike": "significant latency increase",
        "error_burst": "sudden spike in error rates",
        "cpu_overload": "CPU utilization exceeding safe thresholds",
        "memory_leak": "gradual memory consumption increase",
        "connection_pool": "connection pool exhaustion",
    }.get(fault, f"{fault} anomaly")

    return {
        "explanation": (
            f"The {service} service experienced a {fault_desc}. "
            f"Causal analysis identified it as the originating point. "
            f"Propagation path: {chain}."
        ),
        "recommended_actions": [
            f"Investigate {service} logs for the incident timeframe",
            f"Check {service} for resource constraints or misconfigurations",
            f"Review recent deployments to {service}",
            f"Consider scaling {service} if under load",
        ],
    }


async def check_ollama_status() -> Dict:
    """Check if Ollama is running and which models are available."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{OLLAMA_BASE_URL}/api/tags")
            resp.raise_for_status()
            models = resp.json().get("models", [])
            return {
                "status": "connected",
                "models": [m["name"] for m in models],
                "default_model": DEFAULT_MODEL,
            }
    except Exception:
        return {"status": "disconnected", "models": [], "default_model": DEFAULT_MODEL}
