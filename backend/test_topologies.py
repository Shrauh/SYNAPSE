import io
import json
import sys
import time
import urllib.error
import urllib.request

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

BASE_URL = "http://localhost:8000/api/v1"

TEST_CASES = [
    {
        "system": "default",
        "service": "database",
        "fault_type": "latency_spike",
    },
    {
        "system": "online-boutique",
        "service": "redis-cart",
        "fault_type": "latency_spike",
    },
    {
        "system": "fintech",
        "service": "transaction-service",
        "fault_type": "error_burst",
    },
    {
        "system": "healthcare",
        "service": "records-service",
        "fault_type": "resource_exhaustion",
    },
]


def http_get(url):
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8")
        try:
            return e.code, json.loads(body)
        except Exception:
            return e.code, {"error": body}


def http_post(url, payload):
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8")
        try:
            return e.code, json.loads(body)
        except Exception:
            return e.code, {"error": body}


def main():
    print("=== SYNAPSE Topology Switching Test ===")

    # 1. Available systems
    print("\n1. Listing available systems:")
    status, avail = http_get(f"{BASE_URL}/system/available")
    if status != 200:
        print(f"FAILED to list systems: {status} {avail}")
        sys.exit(1)

    systems = [s["id"] for s in avail.get("available", [])]
    print(f"Available systems: {systems}")

    results = {}

    try:
        # 2. Test each system
        for tc in TEST_CASES:
            sys_id = tc["system"]
            svc = tc["service"]
            fault = tc["fault_type"]
            print(f"\n--- Testing System: {sys_id} (service: {svc}, fault: {fault}) ---")

            # Switch system
            status, switch_res = http_post(f"{BASE_URL}/system/switch", {"system": sys_id})
            if status != 200:
                print(f"[FAIL] Switch to {sys_id} failed: {status} {switch_res}")
                results[sys_id] = {"passed": False, "error": f"Switch failed: {switch_res}"}
                continue
            print(f"Switched to {sys_id}: {switch_res.get('message', 'OK')}")
            print(f"Active services ({switch_res.get('service_count')}): {switch_res.get('services')}")

            # Trigger simulation
            sim_payload = {
                "root_cause_service": svc,
                "fault_type": fault,
                "severity": "critical",
                "duration_minutes": 5,
            }
            status, sim_res = http_post(f"{BASE_URL}/rca/simulate", sim_payload)
            if status != 200:
                print(f"[FAIL] Simulation failed: {status} {sim_res}")
                results[sys_id] = {"passed": False, "error": f"Simulation failed: {sim_res}"}
                continue

            incident_id = sim_res.get("incident_id")
            print(f"Simulation triggered: incident_id={incident_id}")

            # Poll for report
            start_poll = time.time()
            report_data = None
            max_wait = 15  # seconds
            while time.time() - start_poll < max_wait:
                status, report_res = http_get(f"{BASE_URL}/incidents/{incident_id}/report")
                if status == 200:
                    report_data = report_res
                    break
                time.sleep(1.0)

            if not report_data:
                # Check incident status directly to see if it failed
                st, inc_detail = http_get(f"{BASE_URL}/incidents/{incident_id}")
                print(f"[FAIL] Polling timed out (15s). Incident status: {inc_detail.get('status') if st == 200 else 'unknown'}")
                results[sys_id] = {"passed": False, "error": "Report polling timed out"}
                continue

            rc_info = report_data.get("root_cause") or {}
            root_cause = rc_info.get("service")
            confidence = rc_info.get("confidence")
            chain = report_data.get("propagation_chain")
            recovery = (
                (report_data.get("recovery") or {}).get("action")
                or (report_data.get("model_info") or {}).get("recovery_action")
                or "N/A"
            )

            print(f"Result:")
            print(f"  Root Cause:      {root_cause}")
            print(f"  Confidence:      {confidence}")
            print(f"  Propagation:     {chain}")
            print(f"  Recovery Action: {recovery}")

            passed = (root_cause is not None)
            results[sys_id] = {
                "passed": passed,
                "root_cause": root_cause,
                "confidence": confidence,
                "chain": chain,
                "recovery": recovery,
            }
            if passed:
                print(f"[PASS] {sys_id} passed!")
            else:
                print(f"[FAIL] {sys_id} failed!")

    finally:
        # 3. Switch back to default
        print("\n--- Resetting to default system ---")
        status, reset_res = http_post(f"{BASE_URL}/system/switch", {"system": "default"})
        print(f"Reset status: {status} - {reset_res.get('message', reset_res)}")

    print("\n=== SUMMARY ===")
    all_passed = True
    for sys_id, res in results.items():
        status_str = "PASS" if res.get("passed") else "FAIL"
        if not res.get("passed"):
            all_passed = False
        print(f"[{status_str}] {sys_id}: {res}")

    if all_passed:
        print("\nALL TOPOLOGIES PASSED!")
    else:
        print("\nSOME TOPOLOGIES FAILED!")
        sys.exit(1)


if __name__ == "__main__":
    main()
