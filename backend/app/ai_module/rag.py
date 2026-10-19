"""
SYNAPSE AI Module — RAG Engine & Causal Prior Generation.

Exposes ChromaDB-backed Retrieval-Augmented Generation (RAG) and causal prior
matrix generation for the SYNAPSE RCA pipeline. Re-exported from app.services.rag
for architectural consistency across the ai_module namespace.
"""

from app.services.rag import (
    DEFAULT_BASE_TOPOLOGY_WEIGHT,
    DEFAULT_RUNBOOK_BOOST_WEIGHT,
    DEFAULT_TRANSITIVE_WEIGHT,
    MAX_PRIOR_WEIGHT,
    MIN_PRIOR_WEIGHT,
    EMBEDDING_DIM,
    SIMILARITY_ROUND_DECIMALS,
    DEFAULT_RETRIEVAL_LIMIT,
    DEFAULT_PROMPT_RETRIEVAL_LIMIT,
    DEFAULT_PERSIST_DIR,
    SERVICE_IDS,
    SERVICE_NAMES,
    TOPOLOGY,
    RUNBOOKS,
    SynapseHashEmbedding,
    SynapseRAG,
)

__all__ = [
    "DEFAULT_BASE_TOPOLOGY_WEIGHT",
    "DEFAULT_RUNBOOK_BOOST_WEIGHT",
    "DEFAULT_TRANSITIVE_WEIGHT",
    "MAX_PRIOR_WEIGHT",
    "MIN_PRIOR_WEIGHT",
    "EMBEDDING_DIM",
    "SIMILARITY_ROUND_DECIMALS",
    "DEFAULT_RETRIEVAL_LIMIT",
    "DEFAULT_PROMPT_RETRIEVAL_LIMIT",
    "DEFAULT_PERSIST_DIR",
    "SERVICE_IDS",
    "SERVICE_NAMES",
    "TOPOLOGY",
    "RUNBOOKS",
    "SynapseHashEmbedding",
    "SynapseRAG",
]
