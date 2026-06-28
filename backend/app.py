from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os
import sys

# Ensure project root is on sys.path so running `python backend/app.py`
# resolves the `backend` package imports correctly.
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from backend.utils.parser import extract_text
from backend.utils.skill_extractor import extract_skills
from backend.utils.ats_calculator import calculate_exact_ats_score, compute_ats_score_with_breakdown
from backend.utils.recommendations import get_recommendations
from backend.utils.experience import extract_experience
from backend.utils.resume_mistakes import analyze_resume_mistakes, train_from_dataset
import json

# Serve frontend static files from the sibling `frontend` folder so the
# application can be used from a single origin and avoid fetch/CORS issues
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.abspath(os.path.join(BASE_DIR, '..', 'frontend'))
SKILLS_FILE = os.path.join(BASE_DIR, 'data', 'skills.json')

app = Flask(__name__, static_folder=FRONTEND_DIR, static_url_path='')
CORS(app)

UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")

os.makedirs(UPLOAD_FOLDER, exist_ok=True)


@app.route("/", methods=["GET"])
def index():
    # If frontend exists, serve index.html so the whole app runs from Flask.
    index_path = os.path.join(FRONTEND_DIR, 'index.html')
    if os.path.exists(index_path):
        return app.send_static_file('index.html')
    return jsonify({"status": "AI Resume Screener API", "endpoints": ["/analyze"]})


# Allow serving any other frontend assets directly (JS/CSS/images)
@app.route('/<path:filename>')
def serve_frontend_file(filename):
    file_path = os.path.join(FRONTEND_DIR, filename)
    if os.path.exists(file_path):
        return send_from_directory(FRONTEND_DIR, filename)
    return jsonify({'error': 'Not found'}), 404


@app.errorhandler(Exception)
def handle_unexpected_error(exc):
    app.logger.exception("Unexpected backend error")
    return jsonify({"error": f"Unexpected backend error: {exc}"}), 500

@app.route("/analyze", methods=["POST"])
def analyze_resume():
    try:
        if "resume" not in request.files:
            return jsonify({
                "error": "No resume uploaded"
            }), 400

        file = request.files["resume"]

        job_description = request.form.get("job_description", "")

        safe_name = os.path.basename(file.filename or "resume_upload")
        file_path = os.path.join(UPLOAD_FOLDER, safe_name)

        file.save(file_path)

        # Extract Resume Text
        resume_text = extract_text(file_path)

        # 1. Try Gemini API analysis first
        from backend.utils.gemini_analyzer import analyze_with_gemini
        gemini_result = analyze_with_gemini(resume_text, job_description)

        if gemini_result:
            return jsonify({
                "ats_score": gemini_result.get("ats_score", 0),
                "score_breakdown": gemini_result.get("score_breakdown", {
                    "skills": 0, "experience": 0, "formatting": 0, "impact": 0
                }),
                "skills": gemini_result.get("skills", []),
                "experience": gemini_result.get("experience", "Not detected"),
                "recommendations": gemini_result.get("recommendations", []),
                "mistakes": gemini_result.get("mistakes", []),
                "mistake_details": gemini_result.get("mistake_details", []),
                "mistake_source": "Gemini 3.5 Flash API",
                "margin_count": len(gemini_result.get("mistakes", [])),
                "resume_text": resume_text
            })

        # 2. Local Fallback Heuristics Analysis
        skills = extract_skills(resume_text)
        job_skills = extract_skills(job_description) if job_description else []

        experience = extract_experience(resume_text)
        recommendations = get_recommendations(resume_text, job_description)
        mistake_report = analyze_resume_mistakes(resume_text, job_description)
        mistakes_details = mistake_report.get("mistake_details", [])

        # Blended ATS score and breakdown
        score_data = compute_ats_score_with_breakdown(
            resume_text, job_description, skills, job_skills, mistakes_details
        )

        return jsonify({
            "ats_score": score_data["ats_score"],
            "score_breakdown": score_data["score_breakdown"],
            "skills": skills,
            "experience": experience,
            "recommendations": recommendations,
            "mistakes": mistake_report.get("mistakes", []),
            "mistake_details": mistakes_details,
            "mistake_source": mistake_report.get("source", "heuristic"),
            "mistake_count": mistake_report.get("count", 0),
            "resume_text": resume_text
        })

    except Exception as exc:
        app.logger.exception("Resume analysis failed")
        return jsonify({"error": f"Resume analysis failed: {exc}"}), 500


@app.route("/train-mistake-model", methods=["POST"])
def train_resume_mistake_model():
    try:
        dataset_name = request.form.get("dataset_name", "").strip()
        if dataset_name:
            dataset_name = os.path.basename(dataset_name)
            dataset_path = os.path.join(BASE_DIR, "data", dataset_name)
        else:
            dataset_path = os.path.join(BASE_DIR, "data", "resume_mistakes_dataset.csv")

        result = train_from_dataset(dataset_path)
        return jsonify({"status": "trained", **result})
    except Exception as exc:
        return jsonify({
            "error": str(exc),
            "expected_schema": {
                "text": "resume text column (text/resume_text/content)",
                "issues": "comma-separated or pipe-separated issue labels",
            },
        }), 400

@app.route("/chat", methods=["POST"])
def chat_resume():
    try:
        data = request.json or {}
        message = data.get("message", "").strip()
        history = data.get("history", [])
        resume_text = data.get("resume_text", "").strip()
        job_description = data.get("job_description", "").strip()

        if not message:
            return jsonify({"error": "Message is required"}), 400

        from backend.utils.gemini_analyzer import chat_with_gemini
        result = chat_with_gemini(message, history, resume_text, job_description)
        return jsonify(result)
    except Exception as exc:
        app.logger.exception("Chat failed")
        return jsonify({"error": f"Chat failed: {exc}"}), 500


if __name__ == "__main__":
    # Bind to 127.0.0.1 explicitly and enable debug for diagnostic output
    print("Starting AI Resume Screener backend on http://127.0.0.1:5000")
    app.run(host="127.0.0.1", port=5000, debug=True)