import re

def extract_experience(text):
    """Extract years of experience from resume text.

    Supports decimals (3.5 years), ranges (3-5 years), and plus notations (5+ years).
    Scans all matches and returns the maximum value found, capped at 50 to avoid outliers.
    """
    text_lower = (text or "").lower()
    pattern = r'(\d+(?:\.\d+)?)\s*(?:\+|-|\s*to\s*\d+)?\s*years?'

    matches = re.findall(pattern, text_lower)
    if matches:
        try:
            vals = []
            for m in matches:
                val = float(m)
                if val <= 50:  # Exclude unrealistic numbers
                    vals.append(val)
            if vals:
                max_val = max(vals)
                if max_val.is_integer():
                    return f"{int(max_val)} Years"
                return f"{max_val} Years"
        except Exception:
            pass

    return "Fresher"