"""Local MiniLM semantic retrieval over the same resource text as BM25."""

from taxaid import TOP_K

MODEL_ID = "sentence-transformers/all-MiniLM-L6-v2"
MODEL_REVISION = "1110a243fdf4706b3f48f1d95db1a4f5529b4d41"


class MiniLM:
    """Rank the full catalog by cosine similarity; never embed scenario labels."""

    def __init__(self, resources):
        try:
            from sentence_transformers import SentenceTransformer, __version__
        except ImportError as error:
            raise RuntimeError(
                "MiniLM requires sentence-transformers; install it with "
                "python -m pip install -r requirements.txt"
            ) from error

        self.resources = resources
        self.model = SentenceTransformer(MODEL_ID, revision=MODEL_REVISION, device="cpu")
        self.embeddings = self.model.encode(
            [" ".join(resource[key] for key in ("title", "summary", "search_terms")) for resource in resources],
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        self.metadata = {
            "method": "minilm",
            "model": MODEL_ID,
            "model_revision": MODEL_REVISION,
            "sentence_transformers_version": __version__,
            "max_seq_length": self.model.max_seq_length,
        }

    def rank(self, text):
        if not text.strip():
            raise ValueError("Query must not be blank")
        query = self.model.encode(text, normalize_embeddings=True, show_progress_bar=False)
        scores = self.embeddings @ query
        ranked = [
            {
                "resource_id": resource["id"], "title": resource["title"],
                "url": resource["url"], "score": float(score),
                "explanation": f"Semantic similarity to the resource description. Resource summary: {resource['summary']} This match does not establish applicability.",
            }
            for resource, score in zip(self.resources, scores)
        ]
        ranked.sort(key=lambda result: (-result["score"], result["resource_id"]))
        return [{"rank": rank, **result} for rank, result in enumerate(ranked[:TOP_K], start=1)]
