"""
ChromaDB vector store wrapper for VIKO.

Collections:
  - viko_messages: indexed conversation messages
  - viko_facts:    indexed facts / notes

Embedding strategy:
  1. PRIMARY:  Gemini text-embedding-004 (requires GEMINI_API_KEY, online)
  2. FALLBACK: ChromaDB DefaultEmbeddingFunction (offline ONNX)
"""

from __future__ import annotations

import logging
import sys
import threading
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

def _base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent

_CHROMA_PATH = _base_dir() / "memory"


def _make_ef() -> Any:
    """Build the embedding function: Gemini first, fallback to default."""
    try:
        import google.genai as genai
        from viko.config import get_gemini_key

        key = get_gemini_key()

        class GeminiEF:
            def __call__(self, input: list[str]) -> list[list[float]]:  # noqa: A002
                _client = genai.Client(api_key=key)
                result = []
                for text in input:
                    resp = _client.models.embed_content(
                        model="text-embedding-004",
                        contents=text,
                    )
                    result.append(resp.embeddings[0].values)
                return result

        ef = GeminiEF()
        logger.debug("vector_store: using Gemini text-embedding-004")
        return ef
    except Exception as exc:  # noqa: BLE001
        logger.debug("vector_store: Gemini EF unavailable (%s), using default", exc)
        from chromadb.utils.embedding_functions import DefaultEmbeddingFunction

        return DefaultEmbeddingFunction()


class VectorStore:
    """Thread-safe, lazily-initialised ChromaDB wrapper."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._init_lock = threading.Lock()
        self._client: Any = None
        self._ef: Any = None
        self._msgs: Any = None
        self._facts: Any = None

    # ------------------------------------------------------------------
    # Lazy initialisation
    # ------------------------------------------------------------------

    def _ensure_init(self) -> bool:
        """Return True if ChromaDB is available and initialised."""
        if self._client is not None:
            return True

        with self._init_lock:
            # Double-check after acquiring the lock
            if self._client is not None:
                return True

            try:
                import chromadb

                _CHROMA_PATH.mkdir(parents=True, exist_ok=True)
                self._ef = _make_ef()
                self._client = chromadb.PersistentClient(path=str(_CHROMA_PATH))
                self._msgs = self._client.get_or_create_collection(
                    name="viko_messages",
                    embedding_function=self._ef,
                    metadata={"hnsw:space": "cosine"},
                )
                self._facts = self._client.get_or_create_collection(
                    name="viko_facts",
                    embedding_function=self._ef,
                    metadata={"hnsw:space": "cosine"},
                )
                logger.debug("vector_store: ChromaDB initialised at %s", _CHROMA_PATH)
                return True
            except Exception as exc:  # noqa: BLE001
                logger.warning("vector_store: init failed — %s", exc)
                return False

    def _collection(self, name: str) -> Any | None:
        """Return the requested collection or None."""
        if not self._ensure_init():
            return None
        if name == "messages":
            return self._msgs
        if name == "facts":
            return self._facts
        logger.warning("vector_store: unknown collection %r", name)
        return None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def index_message(
        self,
        content: str,
        role: str,
        session_id: int = 0,
        msg_id: int = 0,
    ) -> None:
        """Add a message to viko_messages. Non-blocking (fire-and-forget OK)."""
        if not content.strip():
            return

        col = self._collection("messages")
        if col is None:
            return

        doc_id = f"msg_{msg_id}_{session_id}"
        try:
            with self._lock:
                col.add(
                    documents=[content],
                    metadatas=[{"role": role, "session_id": session_id}],
                    ids=[doc_id],
                )
        except Exception as exc:  # noqa: BLE001
            logger.warning("vector_store: index_message failed — %s", exc)

    def index_fact(
        self,
        fact_text: str,
        category: str = "notes",
        key: str = "",
    ) -> None:
        """Add (or replace) a fact in viko_facts."""
        if not fact_text.strip():
            return

        col = self._collection("facts")
        if col is None:
            return

        doc_id = f"fact_{category}_{key}"
        try:
            with self._lock:
                col.upsert(
                    documents=[fact_text],
                    metadatas=[{"category": category, "key": key}],
                    ids=[doc_id],
                )
        except Exception as exc:  # noqa: BLE001
            logger.warning("vector_store: index_fact failed — %s", exc)

    def search(
        self,
        query: str,
        n: int = 5,
        collection: str = "messages",
    ) -> list[dict]:
        """
        Semantic search in 'messages' or 'facts'.

        Returns a list of dicts: {content, metadata, distance}.
        """
        if not query.strip():
            return []

        col = self._collection(collection)
        if col is None:
            return []

        try:
            count = col.count()
            if count == 0:
                return []
            n_results = min(n, count)
            results = col.query(query_texts=[query], n_results=n_results)

            documents = results.get("documents", [[]])[0]
            metadatas = results.get("metadatas", [[]])[0]
            distances = results.get("distances", [[]])[0]

            return [
                {"content": doc, "metadata": meta, "distance": dist}
                for doc, meta, dist in zip(documents, metadatas, distances)
            ]
        except Exception as exc:  # noqa: BLE001
            logger.warning("vector_store: search failed — %s", exc)
            return []


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

_instance: VectorStore | None = None
_singleton_lock = threading.Lock()


def get_vector_store() -> VectorStore:
    """Return the module-level VectorStore singleton."""
    global _instance
    if _instance is not None:
        return _instance
    with _singleton_lock:
        if _instance is None:
            _instance = VectorStore()
    return _instance


# ---------------------------------------------------------------------------
# Convenience module-level functions
# ---------------------------------------------------------------------------


def index_message(
    content: str,
    role: str,
    session_id: int = 0,
    msg_id: int = 0,
) -> None:
    """Add a message to viko_messages collection. Non-blocking (fire and forget OK)."""
    get_vector_store().index_message(content, role, session_id, msg_id)


def index_fact(
    fact_text: str,
    category: str = "notes",
    key: str = "",
) -> None:
    """Add a fact to viko_facts collection."""
    get_vector_store().index_fact(fact_text, category, key)


def search(
    query: str,
    n: int = 5,
    collection: str = "messages",
) -> list[dict]:
    """
    Search in 'messages' or 'facts' collection.
    Returns list of {content, metadata, distance} dicts.
    """
    return get_vector_store().search(query, n, collection)
