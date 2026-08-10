"""
SYNAPSE End-to-End Demo Script.

Demonstrates the complete pipeline:
1. Injects a fault into a running Docker microservice
2. Triggers SYNAPSE RCA pipeline
3. Shows the detection → analysis → recovery flow

Usage:
    python demo.py
    python demo.py --fault latency --service order-service
"""
import argparse
import asyncio
import httpx
import json
import time
import sys

SYNAPSE_URL = "http://localhost:8000"
SERVICES = {
    "api-gateway": 8080,
    "auth-service": 8081,
    "user-service": 8082,
    "order-service": 8083,
    "payment-service": 8085,
}

FAULTS = {
    "latency": {"latency_ms": 2000, "error_rate": 0.0},
    "errors": {"latency_ms": 0, "error_rate": 0.5},
    "mixed": {"latency_ms": 1000, "error_rate": 0.3},
}


async def check_services():
    """Check all services are running."""
    print("\n🔍 Checking services...")
    async with httpx.AsyncClient(timeout=3.0) as client:
        for name, port in SERVICES.items():
            try:
                resp = await client.get(f"http://localhost:{port}/health")
                status = "✅" if resp.status_code == 200 else "❌"
            except Exception:
                status = "❌"
            print(f"  {status} {name} (:{port})")

        # Check SYNAPSE
        try:
            resp = await client.get(f"{SYNAPSE_URL}/api/v1/health")
            print(f"  ✅ SYNAPSE Backend (:8000)")
        except Exception:
            print(f"  ❌ SYNAPSE Backend (:8000) — run: python -m uvicorn app.main:app --port 8000")
            return False

        # Check Prometheus
        try:
            resp = await client.get("http://localhost:9090/api/v1/status/config")
            print(f"  ✅ Prometheus (:9090)")
        except Exception:
            print(f"  ⚠️  Prometheus (:9090) — optional")

    return True


async def inject_fault(service: str, fault_type: str):
    """Inject a fault into a service."""
    port = SERVICES[service]
    params = FAULTS[fault_type]
    print(f"\n💥 Injecting {fault_type} fault into {service}...")
    print(f"   Parameters: {params}")

    async with httpx.AsyncClient(timeout=5.0) as client:
        resp = await client.post(
            f"http://localhost:{port}/fault", params=params,
        )
        print(f"   Response: {resp.json()}")


async def trigger_analysis():
    """Trigger SYNAPSE RCA analysis."""
    print("\n🧠 Triggering SYNAPSE RCA pipeline...")
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(f"{SYNAPSE_URL}/api/v1/rca/analyze")
        if resp.status_code == 200:
            data = resp.json()
            print(f"   Incident ID: {data.get('incident_id', 'N/A')}")
            return data.get("incident_id")
        else:
            print(f"   Error: {resp.status_code} — {resp.text[:200]}")
            return None


async def wait_for_result(incident_id: str, max_wait: int = 60):
    """Poll for RCA result."""
    print(f"\n⏳ Waiting for analysis (max {max_wait}s)...")
    async with httpx.AsyncClient(timeout=5.0) as client:
        for i in range(max_wait // 3):
            await asyncio.sleep(3)
            try:
                resp = await client.get(f"{SYNAPSE_URL}/api/v1/incidents/{incident_id}/report")
                if resp.status_code == 200:
                    return resp.json()
            except Exception:
                pass
            print(f"   ... analyzing ({(i+1)*3}s)")
    return None


def display_result(report: dict):
    """Display the RCA result."""
    print("\n" + "=" * 60)
    print("📊 ROOT CAUSE ANALYSIS RESULT")
    print("=" * 60)

    rc = report.get("root_cause", {})
    print(f"\n  🎯 Root Cause:  {rc.get('service', 'unknown')}")
    print(f"  📈 Confidence:  {rc.get('confidence', 0):.0%}")
    print(f"  ⚡ Fault Type:  {rc.get('fault_type', 'unknown')}")

    severity = report.get("severity", {})
    if severity:
        print(f"  🔴 Severity:    {severity.get('level', 'N/A')}")
        print(f"  📋 Strategy:    {severity.get('response_strategy', 'N/A')}")

    print(f"\n  💬 Explanation:")
    print(f"     {report.get('explanation', 'N/A')}")

    chain = report.get("propagation_chain", "")
    if chain:
        print(f"\n  🔗 Propagation: {chain}")

    actions = report.get("recommended_actions", [])
    if actions:
        print(f"\n  🔧 Recommended Actions:")
        for i, a in enumerate(actions, 1):
            print(f"     {i}. {a}")

    recovery = report.get("recovery", {})
    if recovery:
        print(f"\n  🛠️  Recovery Action:")
        print(f"     $ {recovery.get('kubectl_command', 'N/A')}")

    print("\n" + "=" * 60)


async def clear_fault(service: str):
    """Clear injected fault."""
    port = SERVICES[service]
    async with httpx.AsyncClient(timeout=5.0) as client:
        await client.post(f"http://localhost:{port}/fault/clear")
    print(f"\n🧹 Fault cleared from {service}")


async def main():
    parser = argparse.ArgumentParser(description="SYNAPSE E2E Demo")
    parser.add_argument("--service", default="order-service", choices=SERVICES.keys())
    parser.add_argument("--fault", default="latency", choices=FAULTS.keys())
    parser.add_argument("--skip-check", action="store_true")
    args = parser.parse_args()

    print("🚀 SYNAPSE — End-to-End Demo")
    print("=" * 40)

    # 1. Check services
    if not args.skip_check:
        ok = await check_services()
        if not ok:
            sys.exit(1)

    # 2. Inject fault
    await inject_fault(args.service, args.fault)

    # 3. Wait for Prometheus to scrape
    print("\n⏱️  Waiting 10s for Prometheus to scrape metrics...")
    await asyncio.sleep(10)

    # 4. Trigger analysis
    incident_id = await trigger_analysis()

    # 5. Get result
    if incident_id:
        report = await wait_for_result(incident_id)
        if report:
            display_result(report)
        else:
            print("\n⚠️  Analysis timed out. Check SYNAPSE logs.")

    # 6. Cleanup
    await clear_fault(args.service)
    print("\n✅ Demo complete! Open http://localhost:5173 to see the dashboard.")


if __name__ == "__main__":
    asyncio.run(main())
