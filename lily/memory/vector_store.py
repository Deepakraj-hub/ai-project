"""Vector store interface.

This module is intentionally provider-neutral. A concrete embeddings-backed
store can replace the in-memory implementation without changing the agent core.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class VectorDocument:
    id: str
    text: str
    metadata: dict


class InMemoryVectorStore:
    """Minimal placeholder vector store using substring matching."""

    def __init__(self):
        self._docs: list[VectorDocument] = []

    def add(self, document: VectorDocument) -> None:
        self._docs.append(document)

    def search(self, query: str, limit: int = 5) -> list[VectorDocument]:
        q = query.lower()
        ranked = [doc for doc in self._docs if q in doc.text.lower()]
        return ranked[:limit]
