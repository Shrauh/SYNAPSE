"""
SYNAPSE Ingestion Service — Feature Extraction & Normalization.

Reads simulated (or real) metric streams, computes sliding-window
aggregates, normalizes features (z-score), and stores them to the
database. Provides feature matrices for GNN consumption.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ServiceMetric


# Feature column ordering (must match GNN input)
FEATURE_COLUMNS = ["latency", "error_rate", "cpu", "memory", "request_rate"]


class IngestionService:
    """Handles metric ingestion, normalization, and feature extraction."""

    def __init__(self):
        # Running statistics for z-score normalization
        self._means: Optional[Dict[str, float]] = None
        self._stds: Optional[Dict[str, float]] = None
        self._fitted = False

    def fit_normalizer(self, df: pd.DataFrame) -> None:
        """Fit z-score normalizer on a DataFrame of normal-state metrics.

        Args:
            df: DataFrame with columns matching FEATURE_COLUMNS.
        """
        self._means = {col: df[col].mean() for col in FEATURE_COLUMNS}
        self._stds = {col: max(df[col].std(), 1e-8) for col in FEATURE_COLUMNS}
        self._fitted = True

    def normalize(self, df: pd.DataFrame) -> pd.DataFrame:
        """Z-score normalize feature columns. Fits on first call if needed."""
        if not self._fitted:
            self.fit_normalizer(df)

        result = df.copy()
        for col in FEATURE_COLUMNS:
            if col in result.columns:
                result[col] = (result[col] - self._means[col]) / self._stds[col]
        return result

    def aggregate_window(
        self,
        df: pd.DataFrame,
        window_size: int = 5,
    ) -> pd.DataFrame:
        """Compute sliding-window aggregates per service.

        Takes raw time-series and returns one row per service with
        mean/max/std of each feature over the last `window_size` steps.

        Args:
            df: Raw metrics DataFrame with 'service' and 'timestamp' columns.
            window_size: Number of recent time steps to aggregate.

        Returns:
            DataFrame with one row per service, columns are aggregate features.
        """
        # Get the last N timestamps
        timestamps = sorted(df["timestamp"].unique())
        recent_ts = timestamps[-window_size:] if len(timestamps) >= window_size else timestamps
        recent = df[df["timestamp"].isin(recent_ts)]

        agg_rows = []
        for svc in recent["service"].unique():
            svc_data = recent[recent["service"] == svc]
            row = {"service": svc}
            for col in FEATURE_COLUMNS:
                row[col] = svc_data[col].mean()
                row[f"{col}_max"] = svc_data[col].max()
                row[f"{col}_std"] = svc_data[col].std() if len(svc_data) > 1 else 0.0
            agg_rows.append(row)

        return pd.DataFrame(agg_rows)

    def extract_feature_matrix(
        self,
        df: pd.DataFrame,
        service_order: List[str],
        normalize: bool = True,
    ) -> np.ndarray:
        """Extract a feature matrix for GNN input.

        Args:
            df: Aggregated metrics (one row per service).
            service_order: Ordered list of service names (matches GNN node order).
            normalize: Whether to z-score normalize.

        Returns:
            numpy array of shape (num_services, num_features).
        """
        if normalize:
            df = self.normalize(df)

        matrix = np.zeros((len(service_order), len(FEATURE_COLUMNS)))
        svc_to_idx = {svc: i for i, svc in enumerate(service_order)}

        for _, row in df.iterrows():
            svc = row["service"]
            if svc in svc_to_idx:
                idx = svc_to_idx[svc]
                for j, col in enumerate(FEATURE_COLUMNS):
                    matrix[idx, j] = row[col]

        return matrix

    def compute_metric_deltas(
        self,
        current_df: pd.DataFrame,
        baseline_df: Optional[pd.DataFrame] = None,
    ) -> Dict[str, Dict[str, str]]:
        """Compute percentage change in metrics vs baseline.

        Returns dict like: {"database": {"latency": "+340%", "cpu": "+25%"}}
        """
        if baseline_df is None:
            # Use normalizer means as baseline
            if not self._fitted:
                return {}
            baseline = self._means
        else:
            baseline = {col: baseline_df[col].mean() for col in FEATURE_COLUMNS}

        deltas: Dict[str, Dict[str, str]] = {}
        for _, row in current_df.iterrows():
            svc = row["service"]
            svc_deltas = {}
            for col in FEATURE_COLUMNS:
                base_val = baseline.get(col, 1.0) if baseline_df is None else baseline[col]
                if base_val > 0:
                    pct = ((row[col] - base_val) / base_val) * 100
                    if abs(pct) > 10:  # Only report significant changes
                        sign = "+" if pct > 0 else ""
                        svc_deltas[col] = f"{sign}{pct:.0f}%"
            if svc_deltas:
                deltas[svc] = svc_deltas

        return deltas

    async def store_metrics(
        self, df: pd.DataFrame, db: AsyncSession
    ) -> int:
        """Persist metric rows to database.

        Args:
            df: DataFrame with service, timestamp, and feature columns.
            db: SQLAlchemy async session.

        Returns:
            Number of rows stored.
        """
        count = 0
        for _, row in df.iterrows():
            metric = ServiceMetric(
                service_name=row["service"],
                timestamp=row["timestamp"],
                latency=float(row.get("latency", 0)),
                error_rate=float(row.get("error_rate", 0)),
                cpu=float(row.get("cpu", 0)),
                memory=float(row.get("memory", 0)),
                request_rate=float(row.get("request_rate", 0)),
            )
            db.add(metric)
            count += 1

        await db.commit()
        return count

    def get_service_metrics_snapshot(
        self, df: pd.DataFrame
    ) -> Dict[str, Dict[str, float]]:
        """Get latest metrics per service as a dict (for graph builder)."""
        # Aggregate to latest values per service
        agg = self.aggregate_window(df, window_size=3)
        result = {}
        for _, row in agg.iterrows():
            result[row["service"]] = {
                col: float(row[col]) for col in FEATURE_COLUMNS
            }
        return result


# Module-level singleton
ingestion_service = IngestionService()
