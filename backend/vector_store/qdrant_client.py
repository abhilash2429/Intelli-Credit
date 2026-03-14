"""
Qdrant vector store client for semantic search over document and research chunks.
Collections:
  - document_chunks: RAG over uploaded company documents
  - research_chunks: RAG over web research results

Embedding model: BAAI/bge-m3 (multilingual, handles Indian language text)
Vector dimension: 1024
"""

import logging
import uuid
import re
from typing import Dict, List

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue

from backend.config import settings

logger = logging.getLogger(__name__)

VECTOR_DIM = 1024
_embed_model = None
_embed_model_load_failed = False


def _get_embed_model(allow_download: bool = False):
    """
    Lazy-load the embedding model.
    By default we avoid runtime downloads in request paths and use lexical fallback.
    """
    global _embed_model, _embed_model_load_failed
    if _embed_model is None:
        if not allow_download or _embed_model_load_failed:
            return None
        from sentence_transformers import SentenceTransformer
        try:
            _embed_model = SentenceTransformer("BAAI/bge-m3")
        except Exception as exc:
            _embed_model_load_failed = True
            logger.warning("[Qdrant] Embedding model load failed, using lexical fallback: %s", exc)
            return None
    return _embed_model


client = QdrantClient(url=settings.qdrant_url)


def init_collections() -> None:
    """
    Create Qdrant collections if they don't exist.
    Called on application startup. Idempotent.
    """
    for collection_name in ["document_chunks", "research_chunks"]:
        try:
            if not client.collection_exists(collection_name):
                client.create_collection(
                    collection_name=collection_name,
                    vectors_config=VectorParams(size=VECTOR_DIM, distance=Distance.COSINE),
                )
                logger.info(f"[Qdrant] Created collection: {collection_name}")
            else:
                logger.info(f"[Qdrant] Collection exists: {collection_name}")
        except Exception as e:
            logger.error(f"[Qdrant] Failed to init {collection_name}: {e}")


def upsert_document_chunks(embeddings: List[List[float]], payloads: List[Dict]) -> None:
    """
    Upsert document chunks with embeddings into Qdrant.

    Args:
        embeddings: List of embedding vectors.
        payloads: List of payload dicts (company_id, doc_type, chunk_text, chunk_index).
    """
    points = [
        PointStruct(id=str(uuid.uuid4()), vector=emb, payload=pay)
        for emb, pay in zip(embeddings, payloads)
    ]
    client.upsert(collection_name="document_chunks", points=points)
    logger.info(f"[Qdrant] Upserted {len(points)} document chunks")


def search_chunks(
    query: str,
    company_id: str,
    top_k: int = 5,
    collection: str = "document_chunks",
    use_semantic: bool = False,
) -> List[Dict]:
    """
    Semantic search over chunks for a specific company.

    Args:
        query: Search query text.
        company_id: Company identifier to filter by.
        top_k: Number of results to return.
        collection: Qdrant collection to search.

    Returns:
        List of dicts with chunk_text, doc_type, and relevance score.
    """
    if use_semantic:
        model = _get_embed_model(allow_download=False)
        if model is not None:
            try:
                query_vector = model.encode(query).tolist()
                results = client.search(  # type: ignore[reportAttributeAccessIssue]
                    collection_name=collection,
                    query_vector=query_vector,
                    limit=top_k,
                    query_filter=Filter(
                        must=[FieldCondition(key="company_id", match=MatchValue(value=company_id))]
                    ),
                )
                if results:
                    return [
                        {
                            "chunk_text": r.payload.get("chunk_text", ""),
                            "doc_type": r.payload.get("doc_type", ""),
                            "score": r.score,
                        }
                        for r in results
                    ]
            except Exception as exc:
                logger.warning("[Qdrant] Semantic search failed, falling back to lexical: %s", exc)

    # Fast lexical fallback (no embedding model dependency)
    try:
        points, _ = client.scroll(
            collection_name=collection,
            scroll_filter=Filter(
                must=[FieldCondition(key="company_id", match=MatchValue(value=company_id))]
            ),
            with_payload=True,
            with_vectors=False,
            limit=max(top_k * 20, 50),
        )
    except Exception as exc:
        logger.warning("[Qdrant] Lexical scroll failed: %s", exc)
        return []

    query_tokens = set(re.findall(r"[a-z0-9]+", query.lower()))
    ranked: List[Dict] = []
    for point in points:
        payload = point.payload or {}
        chunk_text = str(payload.get("chunk_text", "") or "")
        if not chunk_text:
            continue
        text_tokens = set(re.findall(r"[a-z0-9]+", chunk_text.lower()))
        overlap = len(query_tokens & text_tokens)
        score = float(overlap) / max(1, len(query_tokens))
        if score <= 0:
            continue
        ranked.append(
            {
                "chunk_text": chunk_text,
                "doc_type": str(payload.get("doc_type", "") or ""),
                "score": score,
            }
        )

    ranked.sort(key=lambda x: x["score"], reverse=True)
    if ranked:
        return ranked[:top_k]

    # As final fallback, return first few chunks even if lexical overlap is low.
    return [
        {
            "chunk_text": str((p.payload or {}).get("chunk_text", "") or ""),
            "doc_type": str((p.payload or {}).get("doc_type", "") or ""),
            "score": 0.0,
        }
        for p in points[:top_k]
        if (p.payload or {}).get("chunk_text")
    ]
