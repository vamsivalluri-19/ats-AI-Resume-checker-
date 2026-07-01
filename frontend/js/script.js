// Resolve the API base URL. Replace this with your own Render URL (e.g. https://your-app.onrender.com) after deploying.
const isLocal = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1' || window.location.protocol === 'file:';
const API_BASE = isLocal ? "http://127.0.0.1:5000" : "https://ats-ai-resume-checker.onrender.com";

let liveAnalyzeTimer = null;
let chatHistory = []; // Stores conversation context: { role: 'user'|'model', text: '...' }

function escapeHtml(value) {
    return String(value ?? '')
        .replaceAll('&', '&amp;')
        .replaceAll('<', '&lt;')
        .replaceAll('>', '&gt;')
        .replaceAll('"', '&quot;')
        .replaceAll("'", '&#39;');
}

function formatTitle(value) {
    return String(value || '')
        .replaceAll('_', ' ')
        .replace(/\b\w/g, ch => ch.toUpperCase());
}

function formatBytes(bytes, decimals = 1) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const dm = decimals < 0 ? 0 : decimals;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
}

function getResumeFormData() {
    const fileInput = document.getElementById("resume");
    const jobDescEl = document.getElementById('job_description');

    if (!fileInput || !fileInput.files || fileInput.files.length === 0) {
        return null;
    }

    const formData = new FormData();
    formData.append("resume", fileInput.files[0]);
    formData.append("job_description", jobDescEl ? jobDescEl.value.trim() : '');
    return formData;
}

// Function to handle showing the uploaded file badge
function updateFileInfo(file) {
    const dropzone = document.getElementById("dropzone");
    const fileInfo = document.getElementById("fileInfo");
    const fileName = document.getElementById("fileName");
    const fileSize = document.getElementById("fileSize");

    if (file) {
        fileName.textContent = file.name;
        fileSize.textContent = formatBytes(file.size);
        
        dropzone.classList.add("hidden");
        fileInfo.classList.remove("hidden");
    } else {
        dropzone.classList.remove("hidden");
        fileInfo.classList.add("hidden");
    }
}

async function analyzeResume() {
    const fileInput = document.getElementById("resume");
    const loadingEl = document.getElementById("loading");
    const resultEl = document.getElementById("result");
    const welcomeEl = document.getElementById("welcomePlaceholder");
    const analyzeBtn = document.querySelector('.analyze-btn');

    // Basic validation
    if (!fileInput.files || fileInput.files.length === 0) {
        alert("Please select or drop a resume file first.");
        return;
    }

    const formData = getResumeFormData();
    if (!formData) {
        return;
    }

    // Show loading, hide others
    loadingEl.classList.remove("hidden");
    resultEl.classList.add("hidden");
    if (welcomeEl) welcomeEl.classList.add("hidden");
    if (analyzeBtn) analyzeBtn.disabled = true;

    // Reset editor/chatbot state
    const editorPanel = document.getElementById("editorChatbotPanel");
    if (editorPanel) editorPanel.classList.add("hidden");
    chatHistory = [];
    const chatMsg = document.getElementById("chatMessages");
    if (chatMsg) {
        chatMsg.innerHTML = `
            <div class="chat-message assistant">
                <p>Hi! I'm your AI Resume Assistant. You can ask me to write a professional summary, add skills, rewrite your experience, or fix the mistakes listed above!</p>
            </div>
        `;
    }

    try {
        const apiUrl = `${API_BASE}/analyze`;

        const response = await fetch(apiUrl, {
            method: "POST",
            body: formData
        });

        if (!response.ok) {
            const text = await response.text();
            throw new Error(`Server error: ${response.status} ${text}`);
        }

        const data = await response.json();

        const recs = (data.recommendations || []);
        const mistakes = (data.mistake_details || data.mistakes || []);
        const skills = (data.skills || []);
        const atsScore = data.ats_score ?? 0;

        // Formulate skills
        const skillsHtml = skills.length
            ? skills.map(s => `<span class="skill">${escapeHtml(s)}</span>`).join('')
            : '<p class="empty-state">No key skills detected</p>';

        // Formulate recommendations
        const suggestionItems = recs.length
            ? recs.map(r => `<li>${escapeHtml(r)}</li>`).join('')
            : '<li class="empty-state success-state"><i class="fa-solid fa-check-circle"></i> No major improvements needed!</li>';

        // Formulate mistakes
        const mistakesHtml = mistakes.length
            ? mistakes.map(m => {
                const item = typeof m === 'string' ? { message: m, severity: 'medium', code: 'general_issue' } : m;
                return `
                    <div class="issue-card severity-${escapeHtml(item.severity || 'medium')}">
                        <div class="issue-head">
                            <span class="issue-code">${escapeHtml(formatTitle(item.code || 'issue'))}</span>
                            <span class="issue-badge">${escapeHtml(formatTitle(item.severity || 'medium'))}</span>
                        </div>
                        <p>${escapeHtml(item.message || 'Resume issue detected')}</p>
                    </div>
                `;
            }).join('')
            : '<p class="success-state"><i class="fa-solid fa-circle-check"></i> No critical issues or mistakes detected. Great job!</p>';

        const issueSummary = mistakes.length
            ? `<p class="issue-summary"><i class="fa-solid fa-triangle-exclamation"></i> ${mistakes.length} critical issue${mistakes.length === 1 ? '' : 's'} identified.</p>`
            : '<p class="issue-summary success-state"><i class="fa-solid fa-square-check"></i> No critical mistakes were flagged.</p>';

        const breakdown = data.score_breakdown || { skills: 0, experience: 0, formatting: 0, impact: 0 };

        // Render result template
        resultEl.innerHTML = `
            <div class="result-card score-header-card card">
                <div class="gauge-container">
                    <svg class="gauge-svg" viewBox="0 0 130 130">
                        <circle class="gauge-bg" cx="65" cy="65" r="60"/>
                        <circle class="gauge-progress" id="atsProgress" cx="65" cy="65" r="60"/>
                    </svg>
                    <div class="gauge-text">
                        <span class="gauge-number">${atsScore}%</span>
                        <span class="gauge-label">ATS Score</span>
                    </div>
                </div>
                <div class="score-details-meta">
                    <h2>Analysis Summary</h2>
                    <div class="meta-grid">
                        <div class="meta-item"><i class="fa-solid fa-briefcase"></i> Experience: <strong>${escapeHtml(data.experience ?? 'Not detected')}</strong></div>
                        <div class="meta-item"><i class="fa-solid fa-cube"></i> Engine: <strong>${escapeHtml(data.mistake_source ?? 'heuristic')}</strong></div>
                        <div class="meta-item"><i class="fa-solid fa-bug"></i> Issues Found: <strong>${mistakes.length}</strong></div>
                        <div class="meta-item"><i class="fa-solid fa-brain"></i> ML Predicted Score: <strong>${data.predicted_score !== undefined && data.predicted_score !== null ? data.predicted_score + '%' : 'N/A'}</strong></div>
                    </div>
                    ${issueSummary}
                </div>
                <div class="breakdown-container">
                    <div class="breakdown-item">
                        <div class="breakdown-header">
                            <span>Skills Fit</span>
                            <span>${breakdown.skills}%</span>
                        </div>
                        <div class="progress-bar-bg">
                            <div class="progress-bar" style="width: ${breakdown.skills}%;"></div>
                        </div>
                    </div>
                    <div class="breakdown-item">
                        <div class="breakdown-header">
                            <span>Experience Relevance</span>
                            <span>${breakdown.experience}%</span>
                        </div>
                        <div class="progress-bar-bg">
                            <div class="progress-bar" style="width: ${breakdown.experience}%;"></div>
                        </div>
                    </div>
                    <div class="breakdown-item">
                        <div class="breakdown-header">
                            <span>Formatting & Style</span>
                            <span>${breakdown.formatting}%</span>
                        </div>
                        <div class="progress-bar-bg">
                            <div class="progress-bar" style="width: ${breakdown.formatting}%;"></div>
                        </div>
                    </div>
                    <div class="breakdown-item">
                        <div class="breakdown-header">
                            <span>Quantifiable Impact</span>
                            <span>${breakdown.impact}%</span>
                        </div>
                        <div class="progress-bar-bg">
                            <div class="progress-bar" style="width: ${breakdown.impact}%;"></div>
                        </div>
                    </div>
                </div>
            </div>

            <div class="result-grid-3">
                <div class="result-card card">
                    <h3><i class="fa-solid fa-tags"></i> Top Detected Skills</h3>
                    <div class="skills">${skillsHtml}</div>
                </div>

                <div class="result-card card">
                    <h3><i class="fa-solid fa-lightbulb"></i> Actionable Suggestions</h3>
                    <ul class="suggestion-list">${suggestionItems}</ul>
                </div>

                <div class="result-card card">
                    <h3><i class="fa-solid fa-triangle-exclamation"></i> Identified Mistakes</h3>
                    <div class="issue-grid">${mistakesHtml}</div>
                </div>
            </div>
        `;

        // Animate circular gauge
        const offset = 377 - (377 * atsScore) / 100;
        setTimeout(() => {
            const progressCircle = document.getElementById('atsProgress');
            if (progressCircle) {
                progressCircle.style.strokeDashoffset = offset;
            }
        }, 100);

        // Populate inline editor with extracted plain text
        const editorTextarea = document.getElementById("resumeTextEditor");
        if (editorTextarea && data.resume_text) {
            editorTextarea.value = data.resume_text;
        }

        // Show editor/chatbot section
        if (editorPanel) {
            editorPanel.classList.remove("hidden");
        }

    } catch (err) {
        console.error(err);
        alert('Failed to analyze resume: ' + err.message);
    } finally {
        loadingEl.classList.add("hidden");
        resultEl.classList.remove("hidden");
        if (analyzeBtn) analyzeBtn.disabled = false;
    }
}

// CHATBOT FUNCTIONS
async function sendChatMessage(customMessage = null) {
    const chatInput = document.getElementById("chatInput");
    const chatMessages = document.getElementById("chatMessages");
    const resumeEditor = document.getElementById("resumeTextEditor");
    const jobDescEl = document.getElementById('job_description');

    const message = customMessage ? customMessage : chatInput.value.trim();
    if (!message) return;

    if (!resumeEditor || !resumeEditor.value.trim()) {
        alert("No resume text available to optimize.");
        return;
    }

    // Append user message bubble
    const userBubble = document.createElement("div");
    userBubble.className = "chat-message user";
    userBubble.innerHTML = `<p>${escapeHtml(message)}</p>`;
    chatMessages.appendChild(userBubble);
    
    // Clear input
    if (!customMessage) chatInput.value = "";
    
    // Auto-scroll chat
    chatMessages.scrollTop = chatMessages.scrollHeight;

    // Show typing bubble
    const typingBubble = document.createElement("div");
    typingBubble.className = "chat-message assistant typing-indicator-bubble";
    typingBubble.innerHTML = `<p><i class="fa-solid fa-circle-notch fa-spin"></i> Writing edits...</p>`;
    chatMessages.appendChild(typingBubble);
    chatMessages.scrollTop = chatMessages.scrollHeight;

    try {
        const chatUrl = `${API_BASE}/chat`;

        const response = await fetch(chatUrl, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                message: message,
                history: chatHistory,
                resume_text: resumeEditor.value.trim(),
                job_description: jobDescEl ? jobDescEl.value.trim() : ""
            })
        });

        // Remove typing indicator
        typingBubble.remove();

        if (!response.ok) {
            const errText = await response.text();
            throw new Error(`Chat failed: ${response.status} ${errText}`);
        }

        const data = await response.json();

        // Append assistant response bubble
        const assistantBubble = document.createElement("div");
        assistantBubble.className = "chat-message assistant";
        assistantBubble.innerHTML = `<p>${escapeHtml(data.response || "No response details returned.")}</p>`;
        chatMessages.appendChild(assistantBubble);

        // If AI returned updated resume text, update our editor content
        if (data.updated_resume_text) {
            resumeEditor.value = data.updated_resume_text;
            
            // Add a brief subtle flash animation to highlight editor change
            resumeEditor.style.boxShadow = "0 0 15px var(--accent-glow)";
            setTimeout(() => {
                resumeEditor.style.boxShadow = "";
            }, 1000);
        }

        // Add to history
        chatHistory.push({ role: 'user', text: message });
        chatHistory.push({ role: 'model', text: JSON.stringify(data) });

    } catch (error) {
        typingBubble.remove();
        console.error(error);
        const errorBubble = document.createElement("div");
        errorBubble.className = "chat-message assistant";
        errorBubble.innerHTML = `<p style="color: var(--severity-high);"><i class="fa-solid fa-circle-exclamation"></i> Error: ${escapeHtml(error.message)}</p>`;
        chatMessages.appendChild(errorBubble);
    } finally {
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
}

// Auto-fix handler
function triggerAutoFix() {
    sendChatMessage("Please automatically rewrite my entire resume to fix all identified mistakes and improve visual structure, vocabulary, and keywords.");
}

// jsPDF EXPORT FUNCTION WITH PROFESSIONAL RESUME FORMATTING
function downloadResumePDF() {
    const editor = document.getElementById("resumeTextEditor");
    if (!editor || !editor.value.trim()) {
        alert("There is no resume text available to generate.");
        return;
    }

    const { jsPDF } = window.jspdf;
    
    // Create A4 sized document
    const doc = new jsPDF({
        orientation: 'p',
        unit: 'pt',
        format: 'a4'
    });

    const text = editor.value;
    const lines = text.split('\n');
    const margin = 45;
    const pageWidth = doc.internal.pageSize.getWidth();
    const pageHeight = doc.internal.pageSize.getHeight();
    const maxLineWidth = pageWidth - (margin * 2);

    let y = margin;
    const lineHeight = 15;
    const sectionSpacing = 12;

    doc.setFont("helvetica", "normal");
    doc.setTextColor(40, 40, 40);

    // Simple helper to check and handle page breaks
    function checkPageBreak(neededHeight) {
        if (y + neededHeight > pageHeight - margin) {
            doc.addPage();
            y = margin;
        }
    }

    let isHeaderParsed = false;

    for (let i = 0; i < lines.length; i++) {
        let line = lines[i].trim();
        // Clean markdown bold/italic/headings symbols from the line
        line = line.replace(/\*\*|__|\*|_/g, "");
        line = line.replace(/^#+\s+/, ""); // strip markdown headers like "### "

        if (!line) {
            y += 6; // spacing for empty line
            continue;
        }

        // 1. Detect Name & Header (First few lines, short, no columns or email symbols)
        if (!isHeaderParsed && i < 3 && line.length < 50 && !line.includes(":") && !line.includes("@")) {
            checkPageBreak(25);
            doc.setFont("helvetica", "bold");
            doc.setFontSize(18);
            doc.setTextColor(11, 18, 32); // Dark slate
            doc.text(line, pageWidth / 2, y, { align: "center" });
            y += 22;
            isHeaderParsed = true;
            continue;
        }

        // 2. Detect Contact Details (email, phone, links at the top)
        if (i < 5 && (line.includes("@") || line.includes("+") || /\d{3}-\d{3}/.test(line) || line.toLowerCase().includes("linkedin") || line.toLowerCase().includes("github"))) {
            checkPageBreak(15);
            doc.setFont("helvetica", "normal");
            doc.setFontSize(9.5);
            doc.setTextColor(100, 100, 100);
            doc.text(line, pageWidth / 2, y, { align: "center" });
            y += 14;
            continue;
        }

        // Reset color for body content
        doc.setTextColor(40, 40, 40);

        // 3. Detect Section Headers (e.g. EXPERIENCE, SKILLS, EDUCATION)
        const headerKeywords = ["experience", "education", "skills", "projects", "summary", "achievements", "work", "technical"];
        const isHeader = (line.toUpperCase() === line && line.length < 30) || 
                         (headerKeywords.some(kw => line.toLowerCase().includes(kw)) && line.length < 25 && !line.includes(":"));

        if (isHeader) {
            y += sectionSpacing;
            checkPageBreak(25);
            doc.setFont("helvetica", "bold");
            doc.setFontSize(11.5);
            doc.setTextColor(11, 18, 32); // Dark slate
            doc.text(line.toUpperCase(), margin, y);

            // Draw a thin dividers line below section header
            y += 4;
            doc.setDrawColor(220, 225, 235);
            doc.setLineWidth(0.75);
            doc.line(margin, y, pageWidth - margin, y);

            y += 14;
            continue;
        }

        // 4. Detect Bullet Points (lines starting with -, *, •)
        const isBullet = line.startsWith("-") || line.startsWith("*") || line.startsWith("•");
        if (isBullet) {
            const bulletText = line.substring(1).trim();
            checkPageBreak(15);
            doc.setFont("helvetica", "normal");
            doc.setFontSize(9.5);
            doc.setTextColor(60, 60, 60);

            // Draw bullet character
            doc.text("•", margin + 10, y);

            // Render wrapped text next to the bullet
            const splitBullet = doc.splitTextToSize(bulletText, maxLineWidth - 20);
            for (let j = 0; j < splitBullet.length; j++) {
                checkPageBreak(14);
                doc.text(splitBullet[j], margin + 22, y);
                y += 13.5;
            }
            continue;
        }

        // 5. Standard Body Paragraphs
        checkPageBreak(15);
        doc.setFont("helvetica", "normal");
        doc.setFontSize(9.5);
        doc.setTextColor(60, 60, 60);

        const splitLine = doc.splitTextToSize(line, maxLineWidth);
        for (let j = 0; j < splitLine.length; j++) {
            checkPageBreak(14);
            doc.text(splitLine[j], margin, y);
            y += 13.5;
        }
    }

    doc.save("formatted_resume.pdf");
}

function scheduleLiveAnalysis() {
    clearTimeout(liveAnalyzeTimer);
    liveAnalyzeTimer = setTimeout(() => {
        if (document.getElementById('resume')?.files?.length) {
            analyzeResume();
        }
    }, 2000);
}

function resetForm() {
    const r = document.getElementById('resume');
    if (r) r.value = '';
    
    updateFileInfo(null);
    
    const res = document.getElementById('result');
    if (res) {
        res.innerHTML = '';
        res.classList.add("hidden");
    }
    
    const welcomeEl = document.getElementById("welcomePlaceholder");
    if (welcomeEl) {
        welcomeEl.classList.remove("hidden");
    }

    // Hide editor and reset chat
    const editorPanel = document.getElementById("editorChatbotPanel");
    if (editorPanel) editorPanel.classList.add("hidden");

    const editorTextarea = document.getElementById("resumeTextEditor");
    if (editorTextarea) editorTextarea.value = '';

    chatHistory = [];
    const chatMsg = document.getElementById("chatMessages");
    if (chatMsg) {
        chatMsg.innerHTML = `
            <div class="chat-message assistant">
                <p>Hi! I'm your AI Resume Assistant. You can ask me to write a professional summary, add skills, rewrite your experience, or fix the mistakes listed above!</p>
            </div>
        `;
    }
}

document.addEventListener('DOMContentLoaded', () => {
    const fileInput = document.getElementById('resume');
    const jobDesc = document.getElementById('job_description');
    const dropzone = document.getElementById('dropzone');
    const chatInput = document.getElementById('chatInput');

    // File Input change listener
    if (fileInput) {
        fileInput.addEventListener('change', () => {
            if (fileInput.files && fileInput.files.length > 0) {
                updateFileInfo(fileInput.files[0]);
                analyzeResume();
            } else {
                resetForm();
            }
        });
    }

    // Job Description change listener
    if (jobDesc) {
        jobDesc.addEventListener('input', scheduleLiveAnalysis);
        jobDesc.addEventListener('change', () => {
            clearTimeout(liveAnalyzeTimer);
            if (document.getElementById('resume')?.files?.length) {
                analyzeResume();
            }
        });
    }

    // Drag and Drop listeners
    if (dropzone && fileInput) {
        ['dragenter', 'dragover'].forEach(eventName => {
            dropzone.addEventListener(eventName, (e) => {
                e.preventDefault();
                e.stopPropagation();
                dropzone.classList.add('dragover');
            }, false);
        });

        ['dragleave', 'drop'].forEach(eventName => {
            dropzone.addEventListener(eventName, (e) => {
                e.preventDefault();
                e.stopPropagation();
                dropzone.classList.remove('dragover');
            }, false);
        });

        dropzone.addEventListener('drop', (e) => {
            const dt = e.dataTransfer;
            const files = dt.files;

            if (files && files.length > 0) {
                fileInput.files = files;
                updateFileInfo(files[0]);
                analyzeResume();
            }
        }, false);
    }

    // Chatbot input enter key listener
    if (chatInput) {
        chatInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                sendChatMessage();
            }
        });
    }

    // Initialize Theme Toggle
    const themeBtn = document.getElementById('themeToggle');
    if (themeBtn) {
        const icon = themeBtn.querySelector('i');
        const currentTheme = localStorage.getItem('theme') || 'dark';

        if (currentTheme === 'light') {
            document.body.classList.add('light');
            if (icon) icon.className = 'fa-solid fa-sun';
        } else {
            document.body.classList.remove('light');
            if (icon) icon.className = 'fa-solid fa-moon';
        }

        themeBtn.addEventListener('click', () => {
            const isLight = document.body.classList.toggle('light');
            localStorage.setItem('theme', isLight ? 'light' : 'dark');
            if (icon) {
                icon.className = isLight ? 'fa-solid fa-sun' : 'fa-solid fa-moon';
            }
        });
    }
});