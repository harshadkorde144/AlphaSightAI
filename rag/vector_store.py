
from pathlib import Path
from typing import Any

import chromadb
from sentence_transformers import SentenceTransformer

from rag.document_loader import chunk_text, load_documents


# Project directories
PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAG_ROOT = Path(__file__).resolve().parent

# ChromaDB storage
CHROMA_DIR = PROJECT_ROOT / "data" / "knowledge_base"

# Local embedding model
EMBEDDING_MODEL_PATH = (
    RAG_ROOT / "data" / "models" / "all-MiniLM-L6-v2"
)

COLLECTION_NAME = "alphasight_research"


# Initialize ChromaDB
CHROMA_DIR.mkdir(parents=True, exist_ok=True)

_client = chromadb.PersistentClient(
    path=str(CHROMA_DIR)
)

_collection = _client.get_or_create_collection(
    name=COLLECTION_NAME,
    metadata={"hnsw:space": "cosine"},
)


_embedding_model = None


def _get_embedding_model() -> SentenceTransformer:
    """Load the local embedding model only once."""

    global _embedding_model

    if _embedding_model is None:

        if not EMBEDDING_MODEL_PATH.exists():
            raise FileNotFoundError(
                f"Embedding model not found: {EMBEDDING_MODEL_PATH}. "
                "Place all-MiniLM-L6-v2 inside rag/data/models/"
            )

        _embedding_model = SentenceTransformer(
            str(EMBEDDING_MODEL_PATH),
            local_files_only=True,
        )

    return _embedding_model


def index_documents() -> dict[str, Any]:
    """Load documents, create chunks and index them in ChromaDB."""

    documents = load_documents()

    if not documents:
        return {
            "documents_found": 0,
            "chunks_indexed": 0,
            "message": (
                "No readable PDF or TXT documents found in rag/documents."
            ),
        }

    model = _get_embedding_model()

    ids = []
    texts = []
    metadatas = []

    for document in documents:

        chunks = chunk_text(document["text"])

        for chunk_number, chunk in enumerate(chunks):

            if not chunk.strip():
                continue

            chunk_id = (
                f'{document["source"]}::chunk::{chunk_number}'
            )

            ids.append(chunk_id)
            texts.append(chunk)

            metadatas.append({
                "source": document["source"],
                "chunk_number": chunk_number,
            })

    if not texts:
        return {
            "documents_found": len(documents),
            "chunks_indexed": 0,
            "message": "No text chunks were extracted.",
        }

    embeddings = model.encode(
        texts,
        normalize_embeddings=True,
        show_progress_bar=False,
    ).tolist()

    _collection.upsert(
        ids=ids,
        documents=texts,
        metadatas=metadatas,
        embeddings=embeddings,
    )

    return {
        "documents_found": len(documents),
        "chunks_indexed": len(texts),
        "message": "Documents indexed successfully.",
    }


def search_knowledge_base(
    query: str,
    top_k: int = 3,
) -> list[dict[str, Any]]:
    """Search ChromaDB for semantically relevant research chunks."""

    if not isinstance(query, str) or not query.strip():
        raise ValueError("Query must not be empty.")

    if top_k < 1:
        raise ValueError("top_k must be at least 1.")

    total_documents = _collection.count()

    if total_documents == 0:
        return []

    model = _get_embedding_model()

    query_embedding = model.encode(
        query.strip(),
        normalize_embeddings=True,
    ).tolist()

    results = _collection.query(
        query_embeddings=[query_embedding],
        n_results=min(top_k, total_documents),
        include=[
            "documents",
            "metadatas",
            "distances",
        ],
    )

    matches = []

    result_ids = results.get("ids", [[]])[0]
    result_docs = results.get("documents", [[]])[0]
    result_metadatas = results.get("metadatas", [[]])[0]
    result_distances = results.get("distances", [[]])[0]

    for index, document_text in enumerate(result_docs):

        metadata = (
            result_metadatas[index]
            if result_metadatas
            else {}
        ) or {}

        matches.append({
            "id": result_ids[index],
            "text": document_text,
            "source": metadata.get("source", "unknown"),
            "chunk_number": metadata.get("chunk_number", -1),
            "distance": float(result_distances[index]),
        })

    return matches
