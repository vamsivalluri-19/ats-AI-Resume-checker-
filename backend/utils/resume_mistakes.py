import csv
import json
import os
import pickle
import re

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.multiclass import OneVsRestClassifier
from sklearn.preprocessing import MultiLabelBinarizer


BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
MODEL_DIR = os.path.join(BASE_DIR, "models")
MODEL_PATH = os.path.join(MODEL_DIR, "resume_mistake_model.pkl")


LABEL_MESSAGES = {
    "missing_contact": "Missing clear contact details such as email or phone number.",
    "too_short": "Resume looks too short to present enough experience.",
    "missing_skills": "No clear skills section or skill keywords were found.",
    "missing_experience": "No work experience section was detected.",
    "missing_projects": "No project examples were detected.",
    "no_bullets": "Resume does not use bullet points to organize achievements.",
    "grammar_or_typo": "Possible grammar or spelling issue detected.",
    "weak_impact": "No measurable results or impact numbers were detected.",
    "keyword_gap": "Resume content does not closely match the job description keywords.",
}


def _normalize_text(value):
    return (value or "").replace("\r\n", "\n").replace("\r", "\n").strip()


def _load_bundle():
    if not os.path.exists(MODEL_PATH):
        return None

    try:
        with open(MODEL_PATH, "rb") as handle:
            return pickle.load(handle)
    except Exception:
        return None


def _model_issue_messages(resume_text):
    bundle = _load_bundle()
    if not bundle:
        return []

    vectorizer = bundle.get("vectorizer")
    classifier = bundle.get("classifier")
    mlb = bundle.get("mlb")
    label_messages = bundle.get("label_messages", LABEL_MESSAGES)

    if vectorizer is None or classifier is None or mlb is None:
        return []

    text = _normalize_text(resume_text)
    if not text:
        return []

    try:
        features = vectorizer.transform([text])
        if hasattr(classifier, "predict_proba"):
            scores = classifier.predict_proba(features)[0]
        else:
            raw_scores = classifier.decision_function(features)
            scores = raw_scores[0] if hasattr(raw_scores, "__len__") else raw_scores

        predicted = []
        labels = list(mlb.classes_)
        for index, label in enumerate(labels):
            score = scores[index] if index < len(scores) else 0.0
            if float(score) >= 0.35:
                predicted.append(label_messages.get(label, label))

        if not predicted and len(scores) > 0:
            best_index = max(range(len(scores)), key=lambda idx: scores[idx])
            if float(scores[best_index]) >= 0.55:
                best_label = labels[best_index]
                predicted.append(label_messages.get(best_label, best_label))

        return predicted
    except Exception:
        return []


def _heuristic_issue_messages(resume_text, job_description=""):
    text = _normalize_text(resume_text)
    job_text = _normalize_text(job_description)
    low = text.lower()
    issues = []

    email_pattern = r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"
    phone_pattern = r"(?:\+?\d{1,3}[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?)?\d{3}[-.\s]?\d{4}"

    if not re.search(email_pattern, text) or not re.search(phone_pattern, text):
        issues.append(LABEL_MESSAGES["missing_contact"])

    if len(re.findall(r"\w+", text)) < 80:
        issues.append(LABEL_MESSAGES["too_short"])

    if not re.search(r"\b(skills|technical skills|core skills)\b", low):
        issues.append(LABEL_MESSAGES["missing_skills"])

    if not re.search(r"\b(experience|work experience|professional experience)\b", low):
        issues.append(LABEL_MESSAGES["missing_experience"])

    if not re.search(r"\b(projects|portfolio)\b", low):
        issues.append(LABEL_MESSAGES["missing_projects"])

    if not re.search(r"^\s*[-*•]", text, flags=re.MULTILINE):
        issues.append(LABEL_MESSAGES["no_bullets"])

    if not re.search(r"\b\d+%?\b", text):
        issues.append(LABEL_MESSAGES["weak_impact"])

    if re.search(r"\b(teh|recieve|adn|lenght|managment)\b", low):
        issues.append("Possible typo detected in common resume wording.")

    if job_text:
        resume_tokens = set(re.findall(r"[a-zA-Z][a-zA-Z0-9+.#-]{1,}", low))
        job_tokens = set(re.findall(r"[a-zA-Z][a-zA-Z0-9+.#-]{1,}", job_text.lower()))
        common = resume_tokens & job_tokens
        if len(common) < 3:
            issues.append(LABEL_MESSAGES["keyword_gap"])

    seen = set()
    deduped = []
    for issue in issues:
        if issue not in seen:
            seen.add(issue)
            deduped.append(issue)

    return deduped


def analyze_resume_mistakes(resume_text, job_description=""):
    model_messages = _model_issue_messages(resume_text)
    heuristic_messages = _heuristic_issue_messages(resume_text, job_description)

    mistakes = []
    seen = set()
    for message in model_messages + heuristic_messages:
        if message not in seen:
            seen.add(message)
            mistakes.append(message)

    if mistakes:
        structured = []
        for message in mistakes:
            severity = "medium"
            if message in {
                LABEL_MESSAGES["missing_contact"],
                LABEL_MESSAGES["too_short"],
                LABEL_MESSAGES["missing_experience"],
                LABEL_MESSAGES["keyword_gap"],
            }:
                severity = "high"
            elif message in {
                LABEL_MESSAGES["missing_projects"],
                LABEL_MESSAGES["missing_skills"],
                LABEL_MESSAGES["no_bullets"],
                LABEL_MESSAGES["weak_impact"],
            }:
                severity = "medium"
            else:
                severity = "low"

            code = None
            for label, label_message in LABEL_MESSAGES.items():
                if label_message == message:
                    code = label
                    break

            structured.append({
                "code": code or "general_issue",
                "message": message,
                "severity": severity,
            })
    else:
        structured = []

    return {
        "mistakes": mistakes,
        "mistake_details": structured,
        "count": len(mistakes),
        "source": "trained_model+heuristic" if model_messages else "heuristic",
    }


def _read_dataset_rows(dataset_path):
    if dataset_path.lower().endswith(".csv"):
        with open(dataset_path, "r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                yield row
        return

    with open(dataset_path, "r", encoding="utf-8") as handle:
        payload = json.load(handle)

    if isinstance(payload, dict):
        payload = payload.get("samples", payload.get("data", []))

    for row in payload:
        yield row


def _row_text(row):
    for key in ("text", "resume_text", "resume", "content"):
        value = row.get(key)
        if value:
            return _normalize_text(value)
    return ""


def _row_labels(row):
    raw_labels = None
    for key in ("labels", "issues", "mistakes", "targets"):
        if row.get(key):
            raw_labels = row.get(key)
            break

    if raw_labels is None:
        return []

    if isinstance(raw_labels, list):
        labels = raw_labels
    else:
        labels = re.split(r"[,|;]", str(raw_labels))

    cleaned = []
    for label in labels:
        value = str(label).strip().lower().replace(" ", "_")
        if value:
            cleaned.append(value)
    return cleaned


def train_from_dataset(dataset_path, model_path=MODEL_PATH):
    texts = []
    label_sets = []

    for row in _read_dataset_rows(dataset_path):
        text = _row_text(row)
        labels = _row_labels(row)
        if text and labels:
            texts.append(text)
            label_sets.append(labels)

    if not texts:
        return {"trained": False, "reason": "dataset is empty or missing text/labels"}

    mlb = MultiLabelBinarizer()
    y = mlb.fit_transform(label_sets)

    vectorizer = TfidfVectorizer(ngram_range=(1, 2), max_features=5000)
    x = vectorizer.fit_transform(texts)

    classifier = OneVsRestClassifier(LogisticRegression(max_iter=2000))
    classifier.fit(x, y)

    os.makedirs(os.path.dirname(model_path), exist_ok=True)
    with open(model_path, "wb") as handle:
        pickle.dump(
            {
                "vectorizer": vectorizer,
                "classifier": classifier,
                "mlb": mlb,
                "label_messages": LABEL_MESSAGES,
            },
            handle,
        )

    return {
        "trained": True,
        "samples": len(texts),
        "labels": list(mlb.classes_),
        "model_path": model_path,
    }