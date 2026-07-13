"""
SYNAPSE AI Orchestrator — Full RCA Pipeline Fusion.

This is the core integration layer that connects:
    Data Simulator → Ingestion → GNN → Causal Inference → LLM Reasoner

Pipeline:
    1. Get/build dependency graph
    2. Extract features from metrics window
    3. GNN anomaly detection → per-node scores
    4. Filter anomalous nodes (threshold)
    5. Causal discovery on anomalous subset
    6. Validate causal edges against topology
    7. Extract root cause candidates
    8. LLM generates human-readable explanation
    9. Store results to DB
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

try:
    import torch
    HAS_TORCH = True
except ImportError:
    torch = None  # type: ignore
    HAS_TORCH = False

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai_module.causal.dag_utils import (
    break_cycles,
    get_propagation_chain,
    get_root_nodes,
    to_causal_graph_json,
)
from app.ai_module.causal.discovery import CausalDiscoveryEngine
from app.ai_module.causal.validate import reorient_by_topology, validate_causal_edges
from app.ai_module.continual.manager import continual_manager
from app.ai_module.gnn.infer import GNNInference
from app.ai_module.gnn.model import HAS_PYG, FallbackAnomalyDetector, create_detector
from app.ai_module.gnn.train import GNNTrainer
from app.ai_module.gnn.utils import compute_topk_accuracy
from app.ai_module.llm.reasoner import llm_reasoner
from app.ai_module.meta.maml import maml_adapter
from app.config import settings
from app.db.models import Incident, RCAResult
from app.services.graph_builder import graph_builder
from app.services.ingestion import FEATURE_COLUMNS, ingestion_service


class RCAPipeline:
    """Orchestrates the full Root Cause Analysis pipeline."""

    def __init__(self):
        self._gnn_trainer: Optional[GNNTrainer] = None
        self._gnn_inference: Optional[GNNInference] = None
        self._causal_engine = CausalDiscoveryEngine(alpha=0.05)
        self._initialized = False
        self._model_trained = False

    async def initialize(self) -> None:
        """Initialize all pipeline components."""
        # Initialize graph builder
        graph_builder.initialize_default()

        # Initialize GNN
        self._gnn_trainer = GNNTrainer(
            in_features=len(FEATURE_COLUMNS),
            hidden_dim=32,
            latent_dim=16,
            heads=4,
        )

        # Try loading saved model
        loaded = self._gnn_trainer.load_model(settings.gnn_model_path)
        if loaded:
            self._model_trained = True

        self._gnn_inference = GNNInference(
            model=self._gnn_trainer.get_model(),
            device=self._gnn_trainer.device,
        )

        # Initialize continual learning
        if HAS_PYG:
            continual_manager.initialize(self._gnn_trainer.get_model())
            maml_adapter.initialize(self._gnn_trainer.get_model())

        self._initialized = True
        print("[Orchestrator] Pipeline initialized.")

    async def train_on_normal_data(
        self,
        num_scenarios: int = 20,
        epochs: int = 50,
    ) -> Dict[str, Any]:
        """Train the GNN on normal (non-faulty) data.

        Generates synthetic normal data and trains the autoencoder
        to learn baseline behavior reconstruction.
        """
        from data.simulator import MicroserviceSimulator

        print("[Orchestrator] Training GNN on normal data...")
        sim = MicroserviceSimulator(seed=42)

        # Generate normal scenarios
        training_data = []
        for i in range(num_scenarios):
            result = sim.simulate_normal(num_steps=60)
            agg = ingestion_service.aggregate_window(result.metrics_df)

            if i == 0:
                ingestion_service.fit_normalizer(result.metrics_df)

            feature_matrix = ingestion_service.extract_feature_matrix(
                agg, graph_builder.service_names, normalize=True
            )

            if HAS_PYG:
                from app.ai_module.gnn.graph_builder import networkx_to_pyg
                pyg_data = networkx_to_pyg(graph_builder, feature_matrix)
                training_data.append(pyg_data)
            else:
                training_data.append(
                    type('Data', (), {
                        'x': torch.tensor(feature_matrix, dtype=torch.float32),
                        'edge_index': torch.tensor(
                            graph_builder.get_edge_index_tensor()[0], dtype=torch.long
                        ),
                    })()
                )

        # Train
        stats = self._gnn_trainer.train(
            training_data, epochs=epochs, verbose=True
        )

        # Save model
        self._gnn_trainer.save_model(settings.gnn_model_path)
        self._model_trained = True

        # Register with continual learning
        continual_manager.register_completed_task(
            "normal_baseline", training_data, stats.get("final_loss", 0)
        )

        # Update inference engine
        self._gnn_inference = GNNInference(
            model=self._gnn_trainer.get_model(),
            device=self._gnn_trainer.device,
        )

        print(f"[Orchestrator] Training complete: {stats}")
        return stats

    async def run_rca_pipeline(
        self,
        incident: Incident,
        db: AsyncSession,
        simulation_result=None,
    ) -> Dict[str, Any]:
        """Run the full RCA pipeline for an incident.

        Args:
            incident: The incident to analyze.
            db: Database session for storing results.
            simulation_result: Optional pre-generated simulation data.

        Returns:
            Dict with pipeline results including root cause, explanation, etc.
        """
        start_time = time.time()
        timeline = []

        if not self._initialized:
            await self.initialize()

        # Auto-train if not trained yet
        if not self._model_trained:
            await self.train_on_normal_data(num_scenarios=15, epochs=30)

        # ── Stage 1: Generate/Get Data ──
        t0 = time.time()
        if simulation_result is None:
            from data.simulator import MicroserviceSimulator
            sim = MicroserviceSimulator()
            simulation_result = sim.simulate_incident(
                root_cause="database",
                fault_type="latency_spike",
                severity=5.0,
            )

        metrics_df = simulation_result.metrics_df
        timeline.append({
            "time": datetime.now(timezone.utc).isoformat(),
            "event": "Data ingestion complete",
            "score": round(time.time() - t0, 3),
        })

        # ── Stage 2: Feature Extraction ──
        t0 = time.time()
        agg_df = ingestion_service.aggregate_window(metrics_df, window_size=10)
        service_order = graph_builder.service_names
        feature_matrix = ingestion_service.extract_feature_matrix(
            agg_df, service_order, normalize=True
        )

        # Update graph with current metrics
        metrics_snapshot = ingestion_service.get_service_metrics_snapshot(metrics_df)
        graph_builder.update_all_metrics(metrics_snapshot)

        timeline.append({
            "time": datetime.now(timezone.utc).isoformat(),
            "event": "Feature extraction complete",
            "score": round(time.time() - t0, 3),
        })

        # ── Stage 3: GNN Anomaly Detection ──
        t0 = time.time()
        edge_index, _ = graph_builder.get_edge_index_tensor()
        anomaly_scores = self._gnn_inference.compute_scores(
            feature_matrix=feature_matrix,
            edge_index=edge_index,
            service_names=service_order,
        )

        # Update graph with anomaly scores
        graph_builder.update_anomaly_scores(anomaly_scores)

        timeline.append({
            "time": datetime.now(timezone.utc).isoformat(),
            "event": f"GNN anomaly detection — {sum(1 for s in anomaly_scores.values() if s > settings.anomaly_threshold)} anomalous services",
            "score": round(time.time() - t0, 3),
        })

        # ── Stage 4: Filter Anomalous Subset ──
        anomalous = self._gnn_inference.get_top_anomalous(
            anomaly_scores, threshold=settings.anomaly_threshold
        )
        anomalous_names = [name for name, _ in anomalous]
        anomalous_scores = {name: score for name, score in anomalous}

        if not anomalous_names:
            # No anomalies — lower threshold or take top 3
            anomalous = sorted(anomaly_scores.items(), key=lambda x: x[1], reverse=True)[:3]
            anomalous_names = [name for name, _ in anomalous]
            anomalous_scores = dict(anomalous)

        # ── Stage 5: Causal Discovery ──
        t0 = time.time()
        # Build time-series matrix for anomalous subset
        ts_matrix = self._build_causal_input(metrics_df, anomalous_names)

        causal_result = self._causal_engine.discover(
            time_series_matrix=ts_matrix,
            service_names=anomalous_names,
        )

        # Validate against dependency graph
        causal_result = validate_causal_edges(
            causal_result, graph_builder, strict=False
        )
        causal_result = reorient_by_topology(causal_result, graph_builder)

        # Break cycles if any
        dag = break_cycles(causal_result["dag"], anomalous_scores)
        causal_result["dag"] = dag

        # Extract root cause candidates
        root_candidates = get_root_nodes(dag, anomalous_scores)

        timeline.append({
            "time": datetime.now(timezone.utc).isoformat(),
            "event": f"Causal inference — root candidates: {[r[0] for r in root_candidates[:3]]}",
            "score": round(time.time() - t0, 3),
        })

        # ── Stage 6: LLM Explanation ──
        t0 = time.time()
        metric_deltas = ingestion_service.compute_metric_deltas(agg_df)

        explanation_result = await llm_reasoner.explain(
            root_candidates=root_candidates,
            anomaly_scores=anomalous_scores,
            causal_edges=causal_result.get("edges", []),
            metric_deltas=metric_deltas,
            dependency_edges=graph_builder.get_adjacency_list(),
        )

        timeline.append({
            "time": datetime.now(timezone.utc).isoformat(),
            "event": f"LLM reasoning — root cause: {explanation_result.get('root_cause', 'unknown')}",
            "score": round(time.time() - t0, 3),
        })

        # ── Stage 7: Store Results ──
        total_time_ms = (time.time() - start_time) * 1000

        root_cause_svc = explanation_result.get("root_cause", root_candidates[0][0] if root_candidates else "unknown")
        confidence = float(explanation_result.get("confidence", root_candidates[0][1] if root_candidates else 0.0))

        # Build causal graph JSON for storage
        causal_graph_json = to_causal_graph_json(
            dag=dag,
            edges_with_strength=causal_result.get("edges", []),
            anomaly_scores=anomalous_scores,
            root_candidates=root_candidates,
        )

        # Build propagation chain
        chain = get_propagation_chain(dag, root_cause_svc)
        propagation_str = " → ".join(chain)

        # Create RCA result
        rca_result = RCAResult(
            incident_id=incident.id,
            root_cause_service=root_cause_svc,
            confidence=confidence,
            fault_type=explanation_result.get("fault_type"),
            explanation=explanation_result.get("explanation", ""),
            propagation_chain=propagation_str,
            metric_deltas=metric_deltas,
            recommended_actions=explanation_result.get("recommended_actions", []),
            causal_graph=causal_graph_json,
            model_info={
                "gnn_type": "GAT Autoencoder" if HAS_PYG else "Statistical Fallback",
                "maml_adapted": False,
                "adaptation_steps": 0,
                "causal_method": "PC Algorithm" if causal_result.get("adjacency") else "Temporal Correlation",
                "execution_time_ms": round(total_time_ms, 1),
            },
        )

        db.add(rca_result)

        # Update incident
        incident.status = "detected"
        incident.root_cause_service = root_cause_svc
        incident.confidence = confidence
        incident.fault_type = explanation_result.get("fault_type")
        incident.affected_services = explanation_result.get("affected_services", [])
        incident.anomaly_scores = anomaly_scores
        incident.timeline = timeline

        await db.commit()
        await db.refresh(incident)

        return {
            "incident_id": incident.id,
            "root_cause": root_cause_svc,
            "confidence": confidence,
            "explanation": explanation_result.get("explanation", ""),
            "propagation_chain": propagation_str,
            "affected_services": explanation_result.get("affected_services", []),
            "anomaly_scores": anomaly_scores,
            "causal_graph": causal_graph_json,
            "metric_deltas": metric_deltas,
            "recommended_actions": explanation_result.get("recommended_actions", []),
            "execution_time_ms": round(total_time_ms, 1),
            "timeline": timeline,
        }

    def _build_causal_input(
        self,
        metrics_df,
        anomalous_names: List[str],
    ) -> np.ndarray:
        """Build time-series matrix for causal discovery.

        Each column = one anomalous service's combined metric signal.
        """
        import pandas as pd

        timestamps = sorted(metrics_df["timestamp"].unique())
        matrix = np.zeros((len(timestamps), len(anomalous_names)))

        for j, svc in enumerate(anomalous_names):
            svc_data = metrics_df[metrics_df["service"] == svc].sort_values("timestamp")
            for col in FEATURE_COLUMNS:
                if col in svc_data.columns:
                    # Combine metrics into a single signal per service
                    values = svc_data[col].values[:len(timestamps)]
                    if len(values) == len(timestamps):
                        matrix[:, j] += values / len(FEATURE_COLUMNS)

        # Add small noise to prevent singular matrices
        matrix += np.random.normal(0, 1e-6, matrix.shape)

        return matrix

    def get_model_status(self) -> Dict[str, Any]:
        """Get comprehensive model status for API."""
        return {
            "initialized": self._initialized,
            "model_trained": self._model_trained,
            "gnn_type": "GAT Autoencoder" if HAS_PYG else "Statistical Fallback",
            "training_losses": self._gnn_trainer.training_losses[-10:] if self._gnn_trainer else [],
            "continual_learning": continual_manager.get_status(),
            "maml": maml_adapter.get_status(),
        }


# Module-level singleton
pipeline = RCAPipeline()
