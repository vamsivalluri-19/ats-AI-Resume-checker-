import re

def extract_experience(text):
    """Extract years of experience from resume text.

    Supports explicit patterns (3.5 years experience), as well as date ranges
    (e.g., 2021 - Present or 2018 - 2022) using hyphens and en-dashes as a fallback.
    Scans all matches and returns the calculated duration span.
    """
    text_lower = (text or "").lower()
    
    # 1. Look for explicit "X years experience" patterns
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

    # 2. Fallback: Parse date ranges (e.g. 2021 - Present or 2018 - 2022)
    # Matches four-digit years separated by hyphens, en-dashes, or "to", ending in a year or "present/current/now"
    range_pattern = r'\b(19\d{2}|20\d{2})\s*(?:-|–|to)\s*(19\d{2}|20\d{2}|present|current|now)\b'
    range_matches = re.findall(range_pattern, text_lower)
    if range_matches:
        try:
            import datetime
            current_year = datetime.datetime.now().year
            earliest_start = current_year
            latest_end = 1980
            has_valid_range = False

            for start_str, end_str in range_matches:
                start = int(start_str)
                if any(x in end_str for x in ["present", "current", "now"]):
                    end = current_year
                else:
                    end = int(end_str)

                if 1980 < start <= end <= current_year:
                    if start < earliest_start:
                        earliest_start = start
                    if end > latest_end:
                        latest_end = end
                    has_valid_range = True

            if has_valid_range and latest_end >= earliest_start:
                span = latest_end - earliest_start
                # Cap span at 25 to avoid high outliers from education/birthyears
                span = min(25, max(0, span))
                if span > 0:
                    return f"{span} Years"
        except Exception:
            pass

    return "Fresher"