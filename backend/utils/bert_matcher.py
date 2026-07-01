from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

def calculate_similarity(resume_text, job_description):
    """Calculate lightweight TF-IDF cosine similarity between resume and job description.
    
    This replaces SentenceTransformer to run in milliseconds and avoid CPU/RAM overheads.
    """
    if not job_description or not resume_text:
        return 0.0

    try:
        vectorizer = TfidfVectorizer(stop_words='english', ngram_range=(1, 2))
        tfidf = vectorizer.fit_transform([resume_text, job_description])
        similarity = cosine_similarity(tfidf[0:1], tfidf[1:2])[0][0]
        val = round(float(similarity) * 100, 2)
        return float(val)
    except Exception:
        return 0.0