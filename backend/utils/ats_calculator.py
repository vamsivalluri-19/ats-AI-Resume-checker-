def calculate_exact_ats_score(resume_skills, job_skills):
    """Return a deterministic ATS score from exact skill overlap."""
    resume_set = {skill.strip().lower() for skill in (resume_skills or []) if skill}
    job_set = {skill.strip().lower() for skill in (job_skills or []) if skill}

    if not job_set:
        return 100

    matched = resume_set & job_set
    score = (len(matched) / len(job_set)) * 100
    return int(round(score))


def compute_ats_score_with_breakdown(resume_text, job_description, resume_skills, job_skills, mistakes_details):
    """Compute a blended ATS score and category breakdown.

    Categories:
    - Skills (0-100): Overlap or catalog coverage.
    - Experience (0-100): Based on extracted years of experience.
    - Formatting (0-100): Deducting points for layout/formatting issues.
    - Impact (0-100): Checking for quantifiable metrics in the text.
    """
    # 1. Skills Score
    resume_set = {s.strip().lower() for s in (resume_skills or []) if s}
    job_set = {s.strip().lower() for s in (job_skills or []) if s}

    if job_set:
        matched = resume_set & job_set
        skills_score = int(round((len(matched) / len(job_set)) * 100))
    else:
        # Default skills coverage of catalog
        from backend.app import SKILLS_FILE, BASE_DIR
        import json
        import os
        try:
            skills_path = os.path.join(BASE_DIR, 'data', 'skills.json')
            with open(skills_path, 'r', encoding='utf-8') as sf:
                skills_data = json.load(sf)
            total = max(1, len(skills_data.get('skills', [])))
            skills_score = int(min(100, round((len(resume_skills) / total) * 100)))
        except Exception:
            skills_score = 50

    # 2. Experience Score
    from backend.utils.experience import extract_experience
    exp_str = extract_experience(resume_text)
    import re
    match = re.search(r'(\d+(?:\.\d+)?)', exp_str)
    years = float(match.group(1)) if match else 0.0

    if years == 0:
        experience_score = 30
    elif years < 2:
        experience_score = 65
    elif years < 5:
        experience_score = 85
    else:
        experience_score = 100

    # 3. Formatting Score
    formatting_score = 100
    formatting_codes = {"no_bullets", "too_short", "missing_contact", "general_issue"}
    for m in (mistakes_details or []):
        if m.get("code") in formatting_codes:
            formatting_score = max(30, formatting_score - 20)

    # 4. Impact Score
    has_numbers = any(char.isdigit() for char in (resume_text or ""))
    impact_score = 100 if has_numbers else 35

    # 5. Semantic Blending
    from backend.utils.bert_matcher import calculate_similarity
    similarity = calculate_similarity(resume_text, job_description) if job_description else 0.0

    if similarity > 0.0:
        if job_set:
            final_score = 0.6 * similarity + 0.4 * skills_score
        else:
            final_score = similarity
    else:
        if job_set:
            final_score = skills_score
        else:
            final_score = (skills_score + experience_score + formatting_score + impact_score) / 4

    final_score = int(round(min(100, max(0, final_score))))

    return {
        "ats_score": final_score,
        "score_breakdown": {
            "skills": skills_score,
            "experience": experience_score,
            "formatting": formatting_score,
            "impact": impact_score
        }
    }


def calculate_ats(similarity, skills):
    """Backward-compatible fallback."""
    bonus = len(skills) * 2
    try:
        score = float(similarity) + float(bonus)
    except Exception:
        score = 0.0

    if score > 100:
        score = 100.0

    return float(round(score, 2))