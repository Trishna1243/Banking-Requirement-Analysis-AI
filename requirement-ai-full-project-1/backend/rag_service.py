import os
import threading
from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer

try:
    from .document_processing import DocumentChunk
except ImportError:
    from document_processing import DocumentChunk

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_VECTOR_STORE_PATH = Path(__file__).resolve().parent / "vector_store"
EMBEDDING_MODEL_NAME = os.getenv(
    "RAG_EMBEDDING_MODEL",
    "sentence-transformers/all-MiniLM-L6-v2",
)


def resolve_vector_store_path() -> Path:
    configured = os.getenv("RAG_VECTOR_STORE_PATH")
    if not configured:
        return DEFAULT_VECTOR_STORE_PATH.resolve()

    path = Path(configured).expanduser()
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return path.resolve()


class RagService:
    """Local CPU embeddings and persistent, document-scoped vector retrieval."""

    def __init__(self):
        self._lock = threading.RLock()
        self.embedding_model = SentenceTransformer(EMBEDDING_MODEL_NAME, device="cpu")
        self.client = chromadb.PersistentClient(path=str(resolve_vector_store_path()))
        self.collection = self.client.get_or_create_collection(
            name="requirement_chunks",
            metadata={"hnsw:space": "cosine"},
        )

    def index_document(self, chunks: list[DocumentChunk]) -> None:
        if not chunks:
            raise ValueError("Cannot index a document with no text chunks.")

        texts = [chunk.text for chunk in chunks]
        embeddings = self.embedding_model.encode(
            texts,
            batch_size=16,
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        with self._lock:
            self.collection.upsert(
                ids=[chunk.chunk_id for chunk in chunks],
                documents=texts,
                embeddings=embeddings.tolist(),
                metadatas=[self._metadata(chunk) for chunk in chunks],
            )

    def retrieve(self, query: str, document_id: str, top_k: int = 3) -> list[dict]:
        if top_k < 1:
            raise ValueError("top_k must be at least one.")
        with self._lock:
            collection_size = self.collection.count()
        if collection_size == 0:
            return []

        query_embedding = self.embedding_model.encode(
            [query],
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        with self._lock:
            result = self.collection.query(
                query_embeddings=query_embedding.tolist(),
                n_results=min(top_k, collection_size),
                where={"document_id": document_id},
                include=["documents", "metadatas", "distances"],
            )

        retrieved = []
        for result_id, text, metadata, distance in zip(
            result["ids"][0],
            result["documents"][0],
            result["metadatas"][0],
            result["distances"][0],
        ):
            retrieved.append(
                {
                    "chunk_id": result_id,
                    "text": text,
                    "source_document": metadata["source_document"],
                    "source_page": metadata["page_number"] if metadata["page_number"] >= 0 else None,
                    "source_location": metadata["source_location"],
                    "distance": float(distance),
                }
            )
        return retrieved

    @staticmethod
    def _metadata(chunk: DocumentChunk) -> dict:
        return {
            "document_id": chunk.document_id,
            "source_document": chunk.source_document,
            "page_number": chunk.page_number if chunk.page_number is not None else -1,
            "source_location": chunk.source_location,
            "chunk_index": chunk.chunk_index,
        }
