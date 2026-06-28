import PyPDF2
import os

def _read_plain_text(file_path):
    """Utility to read raw text with automatic encoding detection (utf-16, utf-8, latin-1)."""
    try:
        with open(file_path, 'rb') as bf:
            raw = bf.read()
    except Exception:
        return ""

    # If null bytes present, it's likely UTF-16
    if b'\x00' in raw:
        try:
            return raw.decode('utf-16', errors='ignore')
        except Exception:
            pass

    # Try utf-8 then latin-1
    for enc in ('utf-8', 'latin-1'):
        try:
            return raw.decode(enc, errors='ignore')
        except Exception:
            continue
    return ""

def extract_text(file_path):
    ext = os.path.splitext(file_path)[1].lower()

    # If it is a text file, parse it directly as plain text
    if ext in ['.txt', '.md']:
        return _read_plain_text(file_path)

    # For PDF files, extract text using PyPDF2
    text_parts = []
    if ext == '.pdf':
        try:
            with open(file_path, "rb") as file:
                reader = PyPDF2.PdfReader(file)
                for page in reader.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(page_text)
            if text_parts:
                return "\n".join(text_parts)
        except Exception:
            pass

    # General fallback for any other files or failed PDF parses
    return _read_plain_text(file_path)