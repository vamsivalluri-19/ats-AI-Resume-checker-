import os
import json
import urllib.request
import urllib.error

def analyze_with_gemini(resume_text, job_description=""):
    """Use the Gemini API to analyze the resume and return a structured review.

    Checks for GEMINI_API_KEY in the system environment first, then in the local .env file.
    If no key is found or the request fails, returns None.
    """
    api_key = os.environ.get("GEMINI_API_KEY")

    if not api_key:
        # Check .env file as fallback
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        env_path = os.path.join(base_dir, "..", ".env")
        if os.path.exists(env_path):
            try:
                with open(env_path, "r", encoding="utf-8") as f:
                    for line in f:
                        if line.strip().startswith("GEMINI_API_KEY="):
                            api_key = line.strip().split("=", 1)[1].strip()
                            break
            except Exception:
                pass

    if not api_key:
        return None

    # Use gemini-3.5-flash which is the active and supported model version
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash:generateContent?key={api_key}"

    prompt = f"""
    You are an expert ATS (Applicant Tracking System) and professional resume reviewer.
    Analyze the following resume text and compare it with the optional job description.
    
    Resume Text:
    {resume_text}
    
    Job Description:
    {job_description or "None provided."}
    
    Please return a JSON response with the following keys. Do not include markdown wrappers (like ```json) in your raw response, return only the valid JSON string.
    {{
        "ats_score": <int between 0 and 100 representing how well the resume matches the job description or general industry standards>,
        "score_breakdown": {{
            "skills": <int 0-100 representing skill match or coverage>,
            "experience": <int 0-100 representing experience relevance>,
            "formatting": <int 0-100 representing formatting and layout quality>,
            "impact": <int 0-100 representing metric and impact presence>
        }},
        "skills": [<list of professional skills found in the resume>],
        "experience": "<extracted total years of experience, e.g. '5 Years' or 'Fresher'>",
        "recommendations": [<list of actionable improvement recommendations, matching job description gaps or general resume advice>],
        "mistakes": [<list of resume mistakes found, e.g. 'Missing clear contact details such as email or phone number.', 'Resume looks too short to present enough experience.', etc.>],
        "mistake_details": [
            {{
                "code": "<one of: missing_contact, too_short, missing_skills, missing_experience, missing_projects, no_bullets, grammar_or_typo, weak_impact, keyword_gap, general_issue>",
                "message": "<description of the mistake>",
                "severity": "<high, medium, or low>"
            }}
        ]
    }}
    """

    data = {
        "contents": [{
            "parts": [{"text": prompt}]
        }],
        "generationConfig": {
            "responseMimeType": "application/json"
        }
    }

    req = urllib.request.Request(
        url,
        data=json.dumps(data).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    try:
        # 45 seconds timeout
        with urllib.request.urlopen(req, timeout=45) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            content_text = res_data["candidates"][0]["content"]["parts"][0]["text"].strip()
            return json.loads(content_text)
    except Exception as e:
        print(f"Gemini API analysis failed: {e}")
        return None


def chat_with_gemini(message, history, resume_text, job_description=""):
    """Interact with the Gemini API to discuss and update the resume.

    Maintains conversational memory and enables inline modifications to the resume text.
    Includes a fallback offline rule-based responder.
    """
    api_key = os.environ.get("GEMINI_API_KEY")

    if not api_key:
        # Check .env file as fallback
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        env_path = os.path.join(base_dir, "..", ".env")
        if os.path.exists(env_path):
            try:
                with open(env_path, "r", encoding="utf-8") as f:
                    for line in f:
                        if line.strip().startswith("GEMINI_API_KEY="):
                            api_key = line.strip().split("=", 1)[1].strip()
                            break
            except Exception:
                pass

    # Fallback offline rule-based chatbot
    if not api_key:
        msg = message.lower()
        if "fix" in msg or "auto" in msg:
            fixed = resume_text or ""
            # Fix common spelling issues
            replacements = {
                "teh": "the",
                "recieve": "receive",
                "adn": "and",
                "lenght": "length",
                "managment": "management"
            }
            fixed_count = 0
            for typo, correct in replacements.items():
                if typo in fixed:
                    fixed = fixed.replace(typo, correct)
                    fixed_count += 1
            if fixed_count > 0:
                return {
                    "response": f"Offline Mode: Automatically corrected {fixed_count} spelling mistakes in the editor! Please add your Gemini API key to the `.env` file for AI-powered rewrites and conversational editing.",
                    "updated_resume_text": fixed
                }
            return {
                "response": "Offline Mode: No obvious spelling typos were detected in your resume. Configure your Gemini API key in `.env` to enable full AI edit features.",
                "updated_resume_text": None
            }
        return {
            "response": "Offline Mode: Chatbot features are limited. Please configure a valid Gemini API key in your `.env` file to chat with the AI assistant.",
            "updated_resume_text": None
        }

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash:generateContent?key={api_key}"

    # Build the conversational contents structure
    contents = []

    # 1. System Prompt as the initial context
    context = f"""
    You are an expert AI Resume Editor.
    You have access to the user's current resume text and the target job description.
    
    Current Resume Text:
    ---
    {resume_text}
    ---
    
    Target Job Description:
    ---
    {job_description or "None provided."}
    ---
    
    Instructions:
    - Help the user edit, refine, and optimize their resume.
    - If the user asks for specific rewrites, updates, or improvements, you MUST provide the complete, updated resume text in the JSON field.
    - Set 'updated_resume_text' to null if the user's request is a general question, explanation, or does not explicitly ask to rewrite, format, or change the resume. Only generate the complete resume text when the user explicitly requests edits, rewrites, or corrections.
    - Your response must be in valid JSON format. Do not wrap it in markdown block tags.
    
    Expected JSON schema:
    {{
        "response": "<your chat message to the user explaining the edits or answering their questions>",
        "updated_resume_text": "<the COMPLETE updated resume text incorporating the edits, OR null if no edits were requested/made>"
    }}
    """

    contents.append({
        "role": "user",
        "parts": [{"text": context}]
    })
    contents.append({
        "role": "model",
        "parts": [{"text": json.dumps({"response": "Understood. I am ready to help you edit your resume.", "updated_resume_text": None})}]
    })

    # 2. Append history
    for h in (history or []):
        role = "user" if h.get("role") == "user" else "model"
        text = h.get("text", "")
        # If model role, make sure it is a JSON format string
        if role == "model":
            # If it doesn't look like JSON, wrap it
            if not text.strip().startswith("{"):
                text = json.dumps({"response": text, "updated_resume_text": None})
        contents.append({
            "role": role,
            "parts": [{"text": text}]
        })

    # 3. Add latest message
    contents.append({
        "role": "user",
        "parts": [{"text": message}]
    })

    data = {
        "contents": contents,
        "generationConfig": {
            "responseMimeType": "application/json"
        }
    }

    req = urllib.request.Request(
        url,
        data=json.dumps(data).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=60) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            content_text = res_data["candidates"][0]["content"]["parts"][0]["text"].strip()
            return json.loads(content_text)
    except Exception as e:
        print(f"Gemini Chat API failed: {e}")
        return {
            "response": f"Sorry, I failed to process your chat request: {e}. Please try again.",
            "updated_resume_text": None
        }
