"""Load a filing's chunks, embed them once, and find the ones closest to a question."""
import json
from pathlib import Path

import numpy as np

MODEL_NAME = "BAAI/bge-small-en-v1.5"
QUERY_PREFIX = "Represent this sentence for searching relevant passages: "  # BGE wants this on questions only
PROCESSED_DIR = Path("data/processed")

_model = None


def get_model():
    """Load the embedding model on first use (it takes a few seconds)."""
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer

        _model = SentenceTransformer(MODEL_NAME)
    return _model


def load_index(doc_name: str):
    """Return (chunks, vectors) for one filing. Embeddings are saved to disk and reused."""
    chunks_path = PROCESSED_DIR / f"{doc_name}.chunks.json"
    vectors_path = PROCESSED_DIR / f"{doc_name}.embeddings.npy"
    chunks = json.loads(chunks_path.read_text(encoding="utf-8"))

    # reuse saved embeddings only if they are newer than the chunks they were made from
    if vectors_path.exists() and vectors_path.stat().st_mtime > chunks_path.stat().st_mtime:
        vectors = np.load(vectors_path)
    else:
        texts = [c["text"] for c in chunks]
        vectors = get_model().encode(texts, normalize_embeddings=True, show_progress_bar=True)
        np.save(vectors_path, vectors)
    return chunks, vectors


def search(question: str, chunks: list[dict], vectors: np.ndarray, top_k: int = 5) -> list[dict]:
    """Return the top_k chunks for the question, best first, each with a 'score' added."""
    question_vector = get_model().encode(QUERY_PREFIX + question, normalize_embeddings=True)
    scores = vectors @ question_vector  # normalized vectors: dot product = similarity
    best = np.argsort(scores)[::-1][:top_k]
    return [{**chunks[i], "score": float(scores[i])} for i in best]
