"""
rag.py — Local RAG Memory with Auto-Learning
ChromaDB persistent vector store + SentenceTransformers embeddings.
Astra automatically learns from every conversation.
"""

import uuid
from datetime import datetime
import chromadb
from sentence_transformers import SentenceTransformer

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────
CHROMA_DIR       = "./astra_memory"
COLLECTION_NAME  = "astra"
EMBEDDING_MODEL  = "all-MiniLM-L6-v2"
TOP_K            = 3


# ─────────────────────────────────────────────
# INITIALISE
# ─────────────────────────────────────────────
_client     = chromadb.PersistentClient(path=CHROMA_DIR)
_collection = _client.get_or_create_collection(COLLECTION_NAME)
_encoder    = SentenceTransformer(EMBEDDING_MODEL)


# ─────────────────────────────────────────────
# CORE FUNCTIONS
# ─────────────────────────────────────────────

def add_to_memory(text: str, doc_id: str = None, metadata: dict = None) -> str:
    """
    Store any text in memory with optional metadata.
    Returns the assigned document ID.
    """
    if not doc_id:
        doc_id = str(uuid.uuid4())

    meta = {"timestamp": datetime.now().isoformat(), "type": "manual"}
    if metadata:
        meta.update(metadata)

    embedding = _encoder.encode([text]).tolist()
    _collection.upsert(
        documents=[text],
        embeddings=embedding,
        metadatas=[meta],
        ids=[doc_id]
    )
    return doc_id


def learn_from_conversation(query: str, response: str):
    """
    Auto-learn from every query/response pair.
    Saves both the question and answer as a combined memory.
    Called automatically after every agent response.
    """
    # Save as Q&A pair — this is what Astra learns
    memory_text = f"Question: {query}\nAnswer: {response}"
    doc_id = add_to_memory(
        text=memory_text,
        metadata={
            "type": "learned",
            "query": query[:200],
            "response": response[:500],
            "timestamp": datetime.now().isoformat()
        }
    )

    # Also save the query alone for better recall matching
    add_to_memory(
        text=query,
        metadata={
            "type": "query",
            "linked_id": doc_id,
            "timestamp": datetime.now().isoformat()
        }
    )
    print(f"[Astra] Learned from conversation: '{query[:50]}...'")


def search_rag(query: str, top_k: int = TOP_K) -> list[str]:
    """
    Semantic search over all stored memories.
    Returns top-k most relevant documents.
    """
    if _collection.count() == 0:
        return []

    embedding = _encoder.encode([query]).tolist()
    results = _collection.query(
        query_embeddings=embedding,
        n_results=min(top_k, _collection.count())
    )
    return results["documents"][0] if results["documents"] else []


def search_rag_with_scores(query: str, top_k: int = TOP_K) -> list[tuple]:
    """
    Search with similarity scores.
    Returns list of (document, score) tuples.
    """
    if _collection.count() == 0:
        return []

    embedding = _encoder.encode([query]).tolist()
    results = _collection.query(
        query_embeddings=embedding,
        n_results=min(top_k, _collection.count()),
        include=["documents", "distances", "metadatas"]
    )

    docs      = results["documents"][0] if results["documents"] else []
    distances = results["distances"][0] if results["distances"] else []
    scores    = [round(1 - d, 3) for d in distances]
    return list(zip(docs, scores))


def get_memory_count() -> int:
    """Return total number of stored memories."""
    return _collection.count()


def list_memories(limit: int = 20) -> list[dict]:
    """List recent memories with metadata."""
    result = _collection.get(include=["documents", "metadatas"])
    docs   = result.get("documents", [])
    metas  = result.get("metadatas", [])
    items  = []
    for doc, meta in zip(docs, metas):
        items.append({"text": doc[:100], "meta": meta})
    return items[-limit:]


def clear_memory():
    """Delete ALL memories. Irreversible."""
    global _collection
    _client.delete_collection(COLLECTION_NAME)
    _collection = _client.get_or_create_collection(COLLECTION_NAME)
    print("[RAG] All memory cleared.")


def clear_learned_memories():
    """Delete only auto-learned memories, keep manual ones."""
    result = _collection.get(include=["metadatas"])
    ids_to_delete = []
    for i, meta in enumerate(result.get("metadatas", [])):
        if meta.get("type") in ["learned", "query"]:
            ids_to_delete.append(result["ids"][i])
    if ids_to_delete:
        _collection.delete(ids=ids_to_delete)
        print(f"[RAG] Deleted {len(ids_to_delete)} learned memories.")
    else:
        print("[RAG] No learned memories to delete.")


# ─────────────────────────────────────────────
# SEED DEFAULTS
# ─────────────────────────────────────────────
def _seed_defaults():
    seeds = [
        "Astra is a local autonomous AI assistant running on llama3 via Ollama.",
        "Astra's owner is Sowmik. She responds only to Sowmik's voice.",
        "Astra can open apps, search the web, create files, do maths, and remember facts.",
        "Astra uses pyttsx3 with Microsoft Zira voice for speech output.",
        "Astra learns from every conversation and remembers it for next time.",
    ]
    for fact in seeds:
        add_to_memory(fact, metadata={"type": "seed"})
    print(f"[RAG] Seeded {len(seeds)} default memories.")


if __name__ == "__main__":
    _seed_defaults()
    print(f"Total memories: {get_memory_count()}")
    results = search_rag_with_scores("what can Astra do")
    print("\nSearch results for 'what can Astra do':")
    for doc, score in results:
        print(f"  [{score:.3f}] {doc[:80]}")
