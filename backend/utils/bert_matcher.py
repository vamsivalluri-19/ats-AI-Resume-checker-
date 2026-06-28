try:
    from sentence_transformers import SentenceTransformer
    from sklearn.metrics.pairwise import cosine_similarity
except Exception:
    SentenceTransformer = None
    def cosine_similarity(a, b):
        return [[0.0]]


# Lazy model load
_model = None

def _load_model():
    global _model
    if _model is None:
        if SentenceTransformer is None:
            return None
        try:
            _model = SentenceTransformer("all-MiniLM-L6-v2")
        except Exception:
            _model = None
    return _model


def calculate_similarity(
    resume_text,
    job_description
):
    if not job_description:
        return 0.0

    model = _load_model()
    if model is None:
        return 0.0

    try:
        embeddings = model.encode([resume_text, job_description])
        similarity = cosine_similarity([embeddings[0]], [embeddings[1]])[0][0]
        val = round(float(similarity) * 100, 2)
        return float(val)
    except Exception:
        return 0.0