"""
transaction_service.py

Builds a single TransactionContext for a selected transaction, sourcing all
data from services/artifact_service.py. This module never reads CSV/JSON
files directly and never calls Azure OpenAI -- it only assembles evidence.

TransactionContext is the single source of truth passed on to llm_service.py.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional

from . import artifact_service


class TransactionNotFoundError(Exception):
    """Raised when the requested transaction_id has no saved artifacts."""


@dataclass(frozen=True)
class SelectedNode:
    """Lightweight reference to the node the investigator clicked in the
    3D graph. Keeps every LLM request tied to the same transaction."""

    node_index: Any
    txId: str
    graph_position: Optional[Dict[str, float]] = None  # e.g. {"x":.., "y":.., "z":..}


@dataclass(frozen=True)
class TransactionContext:
    """
    Single source of truth for a transaction under investigation.

    Only the fields listed in the specification are included. This object is
    shared across initial analysis, predefined question answers, and (later)
    report generation.
    """

    transaction_id: str
    prediction: Any
    true_label: Any
    risk_score: Any
    gnn_importance: Any
    positive_shap_features: str
    negative_shap_features: str
    important_neighbors: List[Dict[str, Any]] = field(default_factory=list)
    important_edges: List[Dict[str, Any]] = field(default_factory=list)
    feature_categories: Dict[str, Any] = field(default_factory=dict)
    selected_node: Optional[SelectedNode] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def build_context(transaction_id: str, selected_node: SelectedNode) -> TransactionContext:
    """
    Build a TransactionContext for the given transaction_id and selected_node.

    Raises:
        TransactionNotFoundError: if the transaction has no saved prediction
            artifact. Callers (security/validation.py) should catch and
            convert this into a rejected-request response before any Azure
            call is attempted.
    """
    prediction_row = artifact_service.get_prediction_row(transaction_id)
    if prediction_row is None:
        raise TransactionNotFoundError(
            f"No prediction artifact found for transaction_id={transaction_id!r}"
        )

    gnn_row = artifact_service.get_gnn_importance_row(transaction_id) or {}
    shap_row = artifact_service.get_shap_row(transaction_id) or {}

    return TransactionContext(
        transaction_id=str(transaction_id),
        prediction=prediction_row.get("prediction"),
        true_label=prediction_row.get("true_label") if "true_label" in prediction_row else prediction_row.get("label"),
        risk_score=prediction_row.get("risk_score"),
        gnn_importance=gnn_row.get("gnn_importance"),
        positive_shap_features=shap_row.get("positive_shap", "") or "",
        negative_shap_features=shap_row.get("negative_shap", "") or "",
        important_neighbors=artifact_service.get_important_neighbors(transaction_id),
        important_edges=artifact_service.get_important_edges(transaction_id),
        feature_categories=artifact_service.get_feature_categories(),
        selected_node=selected_node,
    )
