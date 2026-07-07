"""
artifact_service.py

Minimal, read-only artifact loader for the LLM backend module.

Scope (intentionally narrow):
    Loads exactly the saved offline artifacts required to build a
    TransactionContext:
        - results/predictions/hybrid_predictions.csv
        - results/explanations/gnn/important_nodes.csv
        - results/explanations/gnn/important_edges.csv
        - results/explanations/shap/transaction_explanations.csv
        - results/shared/feature_categories.json

Out of scope:
    - Report history / report metadata artifacts.
    - Any writing back to disk.
    - The full offline pipeline (models, GATv2, XGBoost, SHAP, GNNExplainer).
      Those are pre-computed by the notebooks; this module only reads their
      saved outputs.

Design notes:
    - Artifacts are loaded lazily on first access and cached in memory for
      the lifetime of the process (simple dict-based cache). This keeps the
      module framework-agnostic (no dependency on Streamlit's st.cache_data)
      so it can be reused directly by services/transaction_service.py or
      wrapped by app/components/data_loader.py later.
    - Nothing here calls Azure OpenAI or knows about LLM prompts. This file
      only exposes lookup-by-transaction_id access.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import pandas as pd

from utils.cache import artifact_cache


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Root of the results/ directory. Configurable via env var so this module
# does not hardcode a path that only works in one environment.
RESULTS_ROOT = os.environ.get("GRAPHSHIELD_RESULTS_ROOT", "results")

PREDICTIONS_PATH = os.path.join(RESULTS_ROOT, "predictions", "hybrid_predictions.csv")
IMPORTANT_NODES_PATH = os.path.join(RESULTS_ROOT, "explanations", "gnn", "important_nodes.csv")
IMPORTANT_EDGES_PATH = os.path.join(RESULTS_ROOT, "explanations", "gnn", "important_edges.csv")
SHAP_EXPLANATIONS_PATH = os.path.join(RESULTS_ROOT, "explanations", "shap", "transaction_explanations.csv")
FEATURE_CATEGORIES_PATH = os.path.join(RESULTS_ROOT, "shared", "feature_categories.json")


class ArtifactNotFoundError(FileNotFoundError):
    """Raised when a required artifact file is missing on disk."""


# ---------------------------------------------------------------------------
# Cached loaders (backed by utils.cache.artifact_cache -- process lifetime)
# ---------------------------------------------------------------------------

def _load_csv_cached(path: str, key: str) -> pd.DataFrame:
    def _loader() -> pd.DataFrame:
        if not os.path.exists(path):
            raise ArtifactNotFoundError(f"Required artifact not found: {path}")
        return pd.read_csv(path)

    return artifact_cache.get_or_load(key, _loader)


def _load_json_cached(path: str, key: str) -> Dict[str, Any]:
    def _loader() -> Dict[str, Any]:
        if not os.path.exists(path):
            raise ArtifactNotFoundError(f"Required artifact not found: {path}")
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    return artifact_cache.get_or_load(key, _loader)


def clear_cache() -> None:
    """Clear all cached artifacts. Useful for tests and hot-reloading."""
    artifact_cache.clear()


# ---------------------------------------------------------------------------
# Public lookup API
# ---------------------------------------------------------------------------

def get_prediction_row(transaction_id: str) -> Optional[Dict[str, Any]]:
    """Return the prediction row (prediction, true_label, risk_score) for a
    transaction, or None if the transaction_id does not exist."""
    df = _load_csv_cached(PREDICTIONS_PATH, "predictions")
    match = df[df["txId"].astype(str) == str(transaction_id)]
    if match.empty:
        return None
    return match.iloc[0].to_dict()


def get_gnn_importance_row(transaction_id: str) -> Optional[Dict[str, Any]]:
    """Return the GNN importance / neighbor row for a transaction, or None."""
    df = _load_csv_cached(IMPORTANT_NODES_PATH, "important_nodes")
    match = df[df["txId"].astype(str) == str(transaction_id)]
    if match.empty:
        return None
    return match.iloc[0].to_dict()


def get_important_neighbors(transaction_id: str) -> List[Dict[str, Any]]:
    """Return all neighbor rows associated with a transaction's node
    (rows in important_nodes.csv that are marked as neighbors of it)."""
    df = _load_csv_cached(IMPORTANT_NODES_PATH, "important_nodes")
    if "target_txId" in df.columns:
        match = df[df["target_txId"].astype(str) == str(transaction_id)]
    else:
        # Fallback: no explicit target linkage column available.
        match = df.iloc[0:0]
    return match.to_dict(orient="records")


def get_important_edges(transaction_id: str) -> List[Dict[str, Any]]:
    """Return edge rows connected to the given transaction's node."""
    df = _load_csv_cached(IMPORTANT_EDGES_PATH, "important_edges")
    cols = [c for c in ("source", "target") if c in df.columns]
    if not cols:
        return []
    mask = False
    for c in cols:
        mask = mask | (df[c].astype(str) == str(transaction_id))
    return df[mask].to_dict(orient="records")


def get_shap_row(transaction_id: str) -> Optional[Dict[str, Any]]:
    """Return the raw SHAP explanation row for a transaction, or None."""
    df = _load_csv_cached(SHAP_EXPLANATIONS_PATH, "shap_explanations")
    match = df[df["txId"].astype(str) == str(transaction_id)]
    if match.empty:
        return None
    return match.iloc[0].to_dict()


def get_feature_categories() -> Dict[str, Any]:
    """Return the shared feature-category mapping (ranges/prefix/label)."""
    return _load_json_cached(FEATURE_CATEGORIES_PATH, "feature_categories")


def transaction_exists(transaction_id: str) -> bool:
    return get_prediction_row(transaction_id) is not None


def node_exists(node_index: Any) -> bool:
    """Check whether a given node index appears in the important_nodes
    artifact (i.e. it is a known node in the analyzed graph)."""
    df = _load_csv_cached(IMPORTANT_NODES_PATH, "important_nodes")
    if "node_index" not in df.columns:
        return False
    return (df["node_index"].astype(str) == str(node_index)).any()
