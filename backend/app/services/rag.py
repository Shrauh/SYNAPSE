
import os
import uuid
import hashlib
import numpy as np
from typing import List, Dict, Optional, Any
from datetime import datetime

import chromadb
from chromadb import EmbeddingFunction, Embeddings

# ── Lightweight embedding (no GPU / model download needed) ────────────────────
class SynapseHashEmbedding(EmbeddingFunction):
    def __init__(self): pass
    def name(self): return "synapse-hash-v1"
    def __call__(self, input):
        results = []
        for text in input:
            seed = int(hashlib.md5(
                text.lower().strip().encode()
            ).hexdigest()[:8], 16)
            rng = np.random.default_rng(seed)
            results.append(rng.random(128).tolist())
        return results


# ── Service list ──────────────────────────────────────────────────────────────
SERVICE_IDS = [
    "fe","checkout","cart","catalog",
    "payment","order","ad","redis","email","orderdb"
]

SERVICE_NAMES = {
    "fe":"Frontend","checkout":"Checkout Service",
    "cart":"Cart Service","catalog":"Product Catalog",
    "payment":"Payment Service","order":"Order Service",
    "ad":"Ad Service","redis":"Redis Cache",
    "email":"Email Service","orderdb":"Order DB"
}

TOPOLOGY = {
    "fe":       ["checkout","cart","catalog","ad"],
    "checkout": ["payment","order","cart"],
    "cart":     ["redis"],
    "payment":  ["orderdb"],
    "order":    ["orderdb","email"],
}

# ── Runbook knowledge base ────────────────────────────────────────────────────
RUNBOOKS = [
    {
        "id": "rb_cpu_stress",
        "content": (
            "CPU Stress Runbook: Payment Service CPU > 90% — scale to 3 replicas. "
            "Payment Service causes Checkout and Order to slow down. "
            "Root cause: Payment Service. Victims: Checkout, Order, Frontend."
        ),
        "fault_type": "cpu_stress",
        "root_service": "payment",
    },
    {
        "id": "rb_db_exhaustion",
        "content": (
            "DB Pool Exhaustion: Order DB at 100% connections — Payment and Order fail. "
            "Increase pool size or add read replica. "
            "Root cause: Order DB. Victims: Payment, Order, Checkout, Frontend."
        ),
        "fault_type": "db_exhaustion",
        "root_service": "orderdb",
    },
    {
        "id": "rb_dns_failure",
        "content": (
            "DNS Failure: Cart Service DNS resolution fails — 100% errors, near-zero latency. "
            "Restart CoreDNS. Check ConfigMap entries. "
            "Root cause: Cart Service. Victims: Checkout, Frontend."
        ),
        "fault_type": "dns_failure",
        "root_service": "cart",
    },
    {
        "id": "rb_oom_kill",
        "content": (
            "OOM Kill: Memory at 99%, OS kills service. Rolling restart immediately. "
            "Increase pod memory limit. Profile for memory leaks. "
            "Root cause: affected service itself."
        ),
        "fault_type": "oom_kill",
        "root_service": "order",
    },
    {
        "id": "rb_network_latency",
        "content": (
            "Network Latency: Redis Cache slow — cascades to Cart, Checkout, Frontend. "
            "Check inter-node policies. Enable gRPC keepalives. "
            "Root cause: Redis Cache."
        ),
        "fault_type": "network_latency",
        "root_service": "redis",
    },
    {
        "id": "rb_pod_crash",
        "content": (
            "Pod Crash CrashLoopBackOff: kubectl describe pod for exit code. "
            "Check recent deployments and rollback if needed. "
            "Email crash affects Order notification pipeline."
        ),
        "fault_type": "pod_crash",
        "root_service": "email",
    },
    {
        "id": "rb_topology",
        "content": (
            "Topology: Frontend calls Checkout, Cart, Catalog, Ad. "
            "Checkout calls Payment, Order, Cart. Cart calls Redis. "
            "Payment calls OrderDB. Order calls OrderDB and Email. "
            "DB and cache are high blast-radius — failures propagate upward."
        ),
        "fault_type": "general",
        "root_service": "general",
    },
]


class SynapseRAG:
    """
    ChromaDB RAG engine for SYNAPSE.
    Collections: 'incidents' and 'runbooks'
    """

    def __init__(self, persist_dir: str = "./data/chromadb"):
        os.makedirs(persist_dir, exist_ok=True)
        self._ef     = SynapseHashEmbedding()
        self._client = chromadb.PersistentClient(path=persist_dir)

        self._incidents = self._client.get_or_create_collection(
            name="incidents",
            embedding_function=self._ef,
            metadata={"hnsw:space": "cosine"},
        )
        self._runbooks = self._client.get_or_create_collection(
            name="runbooks",
            embedding_function=self._ef,
            metadata={"hnsw:space": "cosine"},
        )
        self._seed_runbooks()

    # ── Add a resolved incident ───────────────────────────────────────────────
    def add_incident(
        self,
        incident_id:     str,
        description:     str,
        fault_type:      str,
        root_service:    str,
        cascade_path:    List[str],
        metrics_summary: Dict[str, Any],
    ) -> str:
        doc = (
            f"Incident: {description}. Fault: {fault_type}. "
            f"Root: {SERVICE_NAMES.get(root_service, root_service)}. "
            f"Cascade: {' -> '.join(cascade_path)}. "
            f"CPU: {metrics_summary.get('cpu_pct','N/A')}%, "
            f"Errors: {metrics_summary.get('error_rate','N/A')}%, "
            f"Latency: {metrics_summary.get('latency_ms','N/A')}ms."
        )
        uid = str(uuid.uuid4())
        self._incidents.add(
            ids=[uid],
            documents=[doc],
            metadatas=[{
                "incident_id":  incident_id,
                "fault_type":   fault_type,
                "root_service": root_service,
                "cascade":      " -> ".join(cascade_path),
                "timestamp":    datetime.utcnow().isoformat(),
            }],
        )
        return uid

    # ── Retrieve similar past incidents ───────────────────────────────────────
    def retrieve_similar_incidents(
        self,
        query:             str,
        n_results:         int = 3,
        fault_type_filter: Optional[str] = None,
    ) -> List[Dict]:
        count = self._incidents.count()
        if count == 0:
            return []
        n = min(n_results, count)
        kwargs = {"query_texts": [query], "n_results": n}
        if fault_type_filter:
            kwargs["where"] = {"fault_type": fault_type_filter}
        try:
            results = self._incidents.query(**kwargs)
        except Exception:
            results = self._incidents.query(
                query_texts=[query], n_results=n
            )
        out = []
        for i, doc in enumerate(results["documents"][0]):
            out.append({
                "document":   doc,
                "metadata":   results["metadatas"][0][i],
                "similarity": round(1 - results["distances"][0][i], 3),
            })
        return out

    # ── Retrieve runbooks ─────────────────────────────────────────────────────
    def retrieve_runbooks(
        self, query: str, n_results: int = 3
    ) -> List[Dict]:
        count = self._runbooks.count()
        if count == 0:
            return []
        n = min(n_results, count)
        results = self._runbooks.query(
            query_texts=[query], n_results=n
        )
        out = []
        for i, doc in enumerate(results["documents"][0]):
            m = results["metadatas"][0][i]
            out.append({
                "document":     doc,
                "fault_type":   m.get("fault_type", ""),
                "root_service": m.get("root_service", ""),
                "similarity":   round(1 - results["distances"][0][i], 3),
            })
        return out

    # ── Build GPT-4 RAG prompt ────────────────────────────────────────────────
    def build_rag_prompt(
        self,
        anomaly_description: str,
        fault_type: Optional[str] = None,
    ) -> str:
        incidents = self.retrieve_similar_incidents(
            anomaly_description, n_results=2,
            fault_type_filter=fault_type
        )
        runbooks = self.retrieve_runbooks(
            anomaly_description, n_results=2
        )
        parts = [
            "You are SYNAPSE, an AI root cause analysis system.",
            "Use the retrieved context below to assist your analysis.\n",
        ]
        if runbooks:
            parts.append("=== RUNBOOK KNOWLEDGE ===")
            for rb in runbooks:
                parts.append(f"[{rb['fault_type']}] {rb['document']}")
            parts.append("")
        if incidents:
            parts.append("=== SIMILAR PAST INCIDENTS ===")
            for inc in incidents:
                m = inc["metadata"]
                parts.append(
                    f"Incident {m.get('incident_id','N/A')}: "
                    f"fault={m.get('fault_type')}, "
                    f"root={m.get('root_service')}, "
                    f"cascade={m.get('cascade')} "
                    f"(similarity={inc['similarity']})"
                )
            parts.append("")
        parts.append(
            f"=== CURRENT ANOMALY ===\n{anomaly_description}\n"
        )
        parts.append(
            "Identify the root cause service and generate "
            "a causal prior matrix W0."
        )
        return "\n".join(parts)

    # ── Generate W0 prior matrix (novel SYNAPSE contribution) ─────────────────
    def generate_w0_prior(
        self, anomaly_description: str
    ) -> np.ndarray:
        """
        W0[i][j] = probability that service i causally influences service j.
        Injected into DECI loss: L += lambda * ||W*(1 - W0)||_F
        """
        n   = len(SERVICE_IDS)
        idx = {s: i for i, s in enumerate(SERVICE_IDS)}
        w0  = np.zeros((n, n))

        # Base topology edges
        for src, targets in TOPOLOGY.items():
            if src not in idx:
                continue
            for tgt in targets:
                if tgt in idx:
                    w0[idx[src]][idx[tgt]] = 0.85

        # Boost from retrieved runbooks
        rbs = self.retrieve_runbooks(anomaly_description, n_results=2)
        for rb in rbs:
            root = rb.get("root_service", "")
            if root in idx:
                for caller, callees in TOPOLOGY.items():
                    if root in callees and caller in idx:
                        w0[idx[root]][idx[caller]] = min(
                            1.0,
                            w0[idx[root]][idx[caller]] + 0.25
                        )

        # 2-hop transitive edges (weaker weight)
        for i in range(n):
            for j in range(n):
                if w0[i][j] > 0:
                    for k in range(n):
                        if w0[j][k] > 0 and i != k:
                            w0[i][k] = max(w0[i][k], 0.35)

        np.fill_diagonal(w0, 0.0)
        return w0

    # ── Stats ─────────────────────────────────────────────────────────────────
    def get_stats(self) -> Dict:
        return {
            "incidents_stored": self._incidents.count(),
            "runbooks_stored":  self._runbooks.count(),
            "persist_dir":      self._persist_dir
                                if hasattr(self, "_persist_dir")
                                else "data/chromadb",
        }

    def clear_incidents(self):
        self._client.delete_collection("incidents")
        self._incidents = self._client.get_or_create_collection(
            name="incidents",
            embedding_function=self._ef,
            metadata={"hnsw:space": "cosine"},
        )

    # ── Internal ──────────────────────────────────────────────────────────────
    def _seed_runbooks(self):
        if self._runbooks.count() >= len(RUNBOOKS):
            return
        for rb in RUNBOOKS:
            existing = self._runbooks.get(ids=[rb["id"]])
            if existing["ids"]:
                continue
            self._runbooks.add(
                ids=[rb["id"]],
                documents=[rb["content"]],
                metadatas=[{
                    "fault_type":   rb["fault_type"],
                    "root_service": rb["root_service"],
                }],
            )
        print(f"[RAG] Seeded {len(RUNBOOKS)} runbooks into ChromaDB")


# ── Smoke test ────────────────────────────────────────────────────────────────
def smoke_test():
    import shutil
    print("\n[SYNAPSE RAG] Running smoke test...\n")
    shutil.rmtree("./data/chromadb_test", ignore_errors=True)

    rag = SynapseRAG(persist_dir="./data/chromadb_test")

    # 1. Runbooks seeded
    stats = rag.get_stats()
    print(f"  Runbooks stored: {stats['runbooks_stored']}")
    assert stats["runbooks_stored"] == len(RUNBOOKS)
    print("  PASS: runbooks seeded\n")

    # 2. Store an incident
    uid = rag.add_incident(
        incident_id="INC-TEST-001",
        description="Payment service CPU spiked to 97%, checkout failing",
        fault_type="cpu_stress",
        root_service="payment",
        cascade_path=["Payment Service","Checkout Service","Frontend"],
        metrics_summary={"cpu_pct":97,"error_rate":42,"latency_ms":1800},
    )
    assert rag.get_stats()["incidents_stored"] == 1
    print(f"  Stored incident uid: {uid}")
    print("  PASS: incident stored\n")

    # 3. Retrieve similar incident
    results = rag.retrieve_similar_incidents(
        "payment service slow checkout errors", n_results=1
    )
    assert len(results) == 1
    print(f"  Retrieved (similarity={results[0]['similarity']}): "
          f"{results[0]['document'][:60]}...")
    print("  PASS: retrieval works\n")

    # 4. Retrieve runbook
    rbs = rag.retrieve_runbooks("payment CPU overload", n_results=1)
    assert len(rbs) >= 1
    print(f"  Runbook: fault={rbs[0]['fault_type']}, "
          f"similarity={rbs[0]['similarity']}")
    print("  PASS: runbook retrieval works\n")

    # 5. W0 prior matrix
    w0 = rag.generate_w0_prior("payment CPU stress")
    assert w0.shape == (len(SERVICE_IDS), len(SERVICE_IDS))
    assert w0.diagonal().sum() == 0.0
    print(f"  W0 shape: {w0.shape}, "
          f"non-zero: {int((w0>0).sum())}, "
          f"max: {w0.max():.2f}")
    print("  PASS: W0 prior generated\n")

    # 6. RAG prompt
    prompt = rag.build_rag_prompt(
        "payment CPU stress", fault_type="cpu_stress"
    )
    assert "RUNBOOK" in prompt and "ANOMALY" in prompt
    print(f"  RAG prompt length: {len(prompt)} chars")
    print("  PASS: RAG prompt built\n")

    rag.clear_incidents()
    shutil.rmtree("./data/chromadb_test", ignore_errors=True)

    print("=" * 45)
    print("  ALL 6 SMOKE TESTS PASSED")
    print("  ChromaDB + RAG is working correctly.")
    print("=" * 45 + "\n")


if __name__ == "__main__":
    smoke_test()