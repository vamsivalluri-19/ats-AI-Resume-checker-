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
        try:
            print("Model file not found. Auto-training from dataset...")
            dataset_path = os.path.join(BASE_DIR, "data", "resume_mistakes_dataset.csv")
            train_from_dataset(dataset_path)
        except Exception as e:
            print(f"Failed to auto-train model: {e}")
            return None

    try:
        with open(MODEL_PATH, "rb") as handle:
            return pickle.load(handle)
    except Exception:
        return None


def predict_resume_score(resume_text):
    bundle = _load_bundle()
    if not bundle or "regressor" not in bundle:
        return None

    vectorizer = bundle.get("vectorizer")
    vectorizer_classifier = bundle.get("vectorizer_classifier", vectorizer)
    regressor = bundle.get("regressor")
    classifier = bundle.get("classifier")
    mlb = bundle.get("mlb")

    if vectorizer is None or regressor is None or classifier is None or mlb is None:
        return None

    text = _normalize_text(resume_text)
    if not text:
        return 0

    try:
        import numpy as np
        from backend.utils.skill_extractor import extract_skills
        from backend.utils.experience import extract_experience
        import re

        # Extract metadata features
        res_skills = extract_skills(text)
        num_skills = len(res_skills)

        exp_str = extract_experience(text)
        match = re.search(r'(\d+(?:\.\d+)?)', exp_str)
        years_exp = float(match.group(1)) if match else 0.0

        word_count = len(text.split())
        has_metrics = 1.0 if any(c.isdigit() for c in text) else 0.0

        # Predict mistakes using classifier vectorizer
        features_for_classifier = vectorizer_classifier.transform([text])
        if hasattr(classifier, "predict_proba"):
            scores_class = classifier.predict_proba(features_for_classifier)[0]
        else:
            raw_scores = classifier.decision_function(features_for_classifier)
            scores_class = raw_scores[0] if hasattr(raw_scores, "__len__") else raw_scores
            
        # Run heuristic check to gate structural false positives
        heuristic_msgs = _heuristic_issue_messages(text)
        heuristic_codes = set()
        for label, msg in LABEL_MESSAGES.items():
            if msg in heuristic_msgs:
                heuristic_codes.add(label)

        num_mistakes = 0
        for index, label in enumerate(mlb.classes_):
            score = scores_class[index] if index < len(scores_class) else 0.0
            if float(score) >= 0.35:
                # Rule-Gated Override: Eliminate ML false positives on structural issues
                structural_codes = {"too_short", "no_bullets", "weak_impact", "missing_contact", "missing_skills", "missing_experience"}
                if label in structural_codes and label not in heuristic_codes:
                    continue
                num_mistakes += 1

        struct_features = np.array([[
            float(num_skills),
            float(years_exp),
            float(word_count),
            float(has_metrics),
            float(num_mistakes)
        ]])

        # Predict score using regressor vectorizer
        features_for_regressor = vectorizer.transform([text])
        tfidf_dense = features_for_regressor.toarray()
        x_combined = np.hstack([tfidf_dense, struct_features])

        pred = regressor.predict(x_combined)[0]
        return int(round(max(0.0, min(100.0, float(pred)))))
    except Exception:
        return None


def _model_issue_messages(resume_text):
    bundle = _load_bundle()
    if not bundle:
        return []

    vectorizer_classifier = bundle.get("vectorizer_classifier")
    classifier = bundle.get("classifier")
    mlb = bundle.get("mlb")
    label_messages = bundle.get("label_messages", LABEL_MESSAGES)

    if vectorizer_classifier is None or classifier is None or mlb is None:
        return []

    text = _normalize_text(resume_text)
    if not text:
        return []

    try:
        features = vectorizer_classifier.transform([text])
        if hasattr(classifier, "predict_proba"):
            scores = classifier.predict_proba(features)[0]
        else:
            raw_scores = classifier.decision_function(features)
            scores = raw_scores[0] if hasattr(raw_scores, "__len__") else raw_scores

        # Run heuristic check to get codes for gating structural false positives
        heuristic_msgs = _heuristic_issue_messages(resume_text)
        heuristic_codes = set()
        for label, msg in LABEL_MESSAGES.items():
            if msg in heuristic_msgs:
                heuristic_codes.add(label)

        predicted = []
        labels = list(mlb.classes_)
        for index, label in enumerate(labels):
            score = scores[index] if index < len(scores) else 0.0
            if float(score) >= 0.35:
                # Rule-Gated Override: Eliminate ML false positives on structural issues
                structural_codes = {"too_short", "no_bullets", "weak_impact", "missing_contact", "missing_skills", "missing_experience"}
                if label in structural_codes and label not in heuristic_codes:
                    continue
                predicted.append(label_messages.get(label, label))

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
    csv_scores = []

    for row in _read_dataset_rows(dataset_path):
        text = _row_text(row)
        labels = _row_labels(row)
        if text:
            texts.append(text)
            label_sets.append(labels)
            
            # Read pre-computed target score if present under "target_score" key
            score_val = None
            if isinstance(row, dict) and "target_score" in row:
                raw_score = row.get("target_score")
                if raw_score is not None:
                    try:
                        score_val = float(str(raw_score).strip())
                    except ValueError:
                        pass
            csv_scores.append(score_val)

    if not texts:
        return {"trained": False, "reason": "dataset is empty or missing text/labels"}

    mlb = MultiLabelBinarizer()
    y = mlb.fit_transform(label_sets)

    vectorizer_classifier = TfidfVectorizer(ngram_range=(1, 2), max_features=1000)
    x_class = vectorizer_classifier.fit_transform(texts)

    classifier = OneVsRestClassifier(LogisticRegression(max_iter=2000))
    classifier.fit(x_class, y)

    vectorizer_regressor = TfidfVectorizer(ngram_range=(1, 2), max_features=100)
    x_reg = vectorizer_regressor.fit_transform(texts)

    # Train ATS Score Regressor with hybrid feature engineering
    from backend.utils.ats_calculator import compute_ats_score_with_breakdown
    from backend.utils.skill_extractor import extract_skills
    from backend.utils.experience import extract_experience
    from sklearn.linear_model import Ridge
    import numpy as np

    scores = []
    struct_list = []
    for text, labels, csv_score in zip(texts, label_sets, csv_scores):
        res_skills = extract_skills(text)
        
        if csv_score is not None:
            scores.append(csv_score)
        else:
            mistakes_details = [{"code": l} for l in labels]
            score_data = compute_ats_score_with_breakdown(
                resume_text=text,
                job_description="",
                resume_skills=res_skills,
                job_skills=[],
                mistakes_details=mistakes_details
            )
            scores.append(score_data["ats_score"])

        # Extract metadata features
        num_skills = len(res_skills)
        exp_str = extract_experience(text)
        import re
        match = re.search(r'(\d+(?:\.\d+)?)', exp_str)
        years_exp = float(match.group(1)) if match else 0.0
        word_count = len(text.split())
        has_metrics = 1.0 if any(c.isdigit() for c in text) else 0.0
        num_mistakes = len(labels)

        struct_list.append([
            float(num_skills),
            float(years_exp),
            float(word_count),
            float(has_metrics),
            float(num_mistakes)
        ])

    tfidf_dense = x_reg.toarray()
    struct_x = np.array(struct_list)
    x_combined = np.hstack([tfidf_dense, struct_x])

    from sklearn.ensemble import RandomForestRegressor
    regressor = RandomForestRegressor(n_estimators=100, random_state=42)
    regressor.fit(x_combined, scores)

    os.makedirs(os.path.dirname(model_path), exist_ok=True)
    with open(model_path, "wb") as handle:
        pickle.dump(
            {
                "vectorizer": vectorizer_regressor,
                "vectorizer_classifier": vectorizer_classifier,
                "classifier": classifier,
                "mlb": mlb,
                "regressor": regressor,
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