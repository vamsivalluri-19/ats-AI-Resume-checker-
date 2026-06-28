# AI Resume Screener & Chatbot Optimizer

A premium, responsive, glassmorphic web application built with a Flask backend and a modern vanilla CSS/JS frontend. It analyzes resumes against job descriptions using a hybrid pipeline (Gemini 3.5 Flash API + local scikit-learn & sentence-transformers fallback) and allows inline AI-guided corrections and A4 PDF downloads.

## Features

1. **Hybrid Analysis Pipeline**: Calls the **Gemini 3.5 Flash API** to perform deep content and ATS analysis when configured, falling back seamlessly to **offline heuristics** and scikit-learn models if the API is unavailable.
2. **Visual Score Breakdown**: Computes and displays sub-scores for **Skills Fit**, **Experience Relevance**, **Formatting & Style**, and **Quantifiable Impact** as animated progress indicators.
3. **Interactive AI Resume Chatbot & Editor**: Includes an inline plain text resume editor alongside an AI chatbot helper. You can edit text manually or tell the AI to rewrite sections, draft summaries, or fix formatting.
4. **Auto-Fix Assistant**: A one-click button to automatically rewrite the entire resume to resolve all detected layout and keyword mistakes.
5. **Formatted A4 PDF Exporter**: Client-side A4 PDF generator that automatically parses the editor's text, rendering centered headers for Names and Contacts, structured bold section headers with divider lines, and indented bullet points.
6. **Polished Dark/Light Themes**: A premium glassmorphic interface with glow effects and transitions that supports persistent dark/light theme choices.

---

## Quick Start

### 1. Configure the Environment
Create a `.env` file in the root folder to store your Gemini API key:
```env
GEMINI_API_KEY=your_gemini_api_key_here
```
*(Note: `.env` is already configured in `.gitignore` to prevent committing it to GitHub.)*

### 2. Python Environment Setup
Create a virtual environment and install the required dependencies:
```powershell
# Create and activate virtual environment
python -m venv .venv
.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r backend/requirements.txt
```

### 3. Model Training (Offline Fallbacks)
To train the offline mistake classifier scikit-learn model, run:
```powershell
.venv\Scripts\python.exe -m backend.train_resume_mistakes
```

### 4. Run the Live Application
Start the Flask backend server:
```powershell
.venv\Scripts\python.exe -m backend.app
```
Once running, open your browser and navigate to:
👉 **[http://127.0.0.1:5000/](http://127.0.0.1:5000/)**

---

## Verification & Tests
Verify backend endpoints and analytical tests locally:
```powershell
# Run main smoke test
.venv\Scripts\python.exe -m backend.run_smoke

# Run boundary case test
.venv\Scripts\python.exe -m backend.check_analyze_empty
```
