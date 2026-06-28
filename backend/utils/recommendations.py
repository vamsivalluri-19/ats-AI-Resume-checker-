from backend.utils.skill_extractor import extract_skills

def get_recommendations(resume_text, job_description=""):
    """Generate intelligent suggestions for improving the resume.

    Compares resume skills with job description requirements, and provides general feedback
    regarding length, action verbs, and quantifiable impact.
    """
    recommendations = []

    resume_skills = extract_skills(resume_text)
    resume_skills_lower = {s.lower() for s in resume_skills}

    # Job description comparison
    if job_description:
        job_skills = extract_skills(job_description)
        missing_skills = [s for s in job_skills if s.lower() not in resume_skills_lower]

        for skill in missing_skills:
            recommendations.append(f"Consider adding the '{skill}' skill, as it is requested in the job description.")

        if not missing_skills and resume_skills:
            recommendations.append("Excellent! Your resume covers all the skills listed in the job description.")
    else:
        # Default fallback recommendations if no job description is provided
        if "python" not in resume_skills_lower:
            recommendations.append("Add 'Python' to your resume if you have experience with backend programming.")
        if "sql" not in resume_skills_lower:
            recommendations.append("Mention database management and 'SQL' skills.")
        if "machine learning" not in resume_skills_lower:
            recommendations.append("Highlight 'Machine Learning' or data analytics projects.")

    # General heuristic resume improvements
    text_lower = (resume_text or "").lower()
    words_count = len(text_lower.split())

    if words_count < 100:
        recommendations.append("Expand your resume with more detailed descriptions of your past projects and achievements.")
    elif words_count > 1000:
        recommendations.append("Your resume is quite long. Consider condensing it to 1-2 pages of core highlights.")

    action_verbs = ["achieved", "led", "developed", "managed", "created", "designed", "implemented", "delivered", "optimized"]
    if not any(verb in text_lower for verb in action_verbs):
        recommendations.append("Start your bullet points with strong action verbs (e.g. 'Led', 'Developed', 'Optimized') rather than passive phrases.")

    if not any(char.isdigit() for char in text_lower):
        recommendations.append("Include quantifiable achievements (e.g. 'improved performance by 20%', 'managed $5k budget') to demonstrate real impact.")

    return recommendations


def detect_mistakes(resume_text):
    """Return a list of simple issues found in the resume text.

    This is a lightweight, heuristic-based detector for common problems
    (extra spaces, common typos, missing end punctuation).
    """
    import re

    text = (resume_text or "")
    issues = []

    # Extra spaces
    if '  ' in text:
        issues.append('Extra multiple spaces found')

    # Common simple typos
    common_typos = ['teh', 'recieve', 'adn', 'lenght', 'managment']
    low = text.lower()
    for t in common_typos:
        if t in low:
            issues.append(f"Possible typo: '{t}'")

    # Sentences missing end punctuation (very rough)
    sentences = re.split(r'\n|(?<=[.!?])\s+', text.strip())
    for i, s in enumerate(sentences[:10]):
        s = s.strip()
        if not s:
            continue
        if not s[-1] in '.!?':
            snippet = s if len(s) < 80 else s[:77] + '...'
            issues.append(f"Sentence may be missing punctuation: '{snippet}'")
            break

    # Deduplicate
    seen = set()
    unique = []
    for it in issues:
        if it not in seen:
            seen.add(it)
            unique.append(it)

    return unique