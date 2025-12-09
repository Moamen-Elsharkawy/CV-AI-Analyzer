import os
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from PyPDF2 import PdfReader
from dotenv import load_dotenv
from openai import OpenAI

# =======================
# LOAD ENV
# =======================
load_dotenv()
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# =======================
# OPENAI CLIENT
# =======================
client = OpenAI(
    api_key=OPENROUTER_API_KEY,
    base_url="https://openrouter.ai/api/v1"
)

MODEL = "openai/gpt-4.1-mini"

# =======================
# FASTAPI
# =======================
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# =======================
# UTILS
# =======================

def extract_text_from_pdf(file) -> str:
    reader = PdfReader(file)
    text = ""
    for page in reader.pages:
        text += page.extract_text() or ""
    return text.strip()


def ask_openrouter(system_prompt: str, question: str) -> str:
    completion = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": question}
        ],
        temperature=0.3
    )

    return completion.choices[0].message.content


BASE_SYSTEM_PROMPT = """
You are a professional CV analysis AI.

Rules:
- Only use data from the CV
- Answer in Markdown
- Be concise and clear

CV content:
"""


# =======================
# FRONTEND (UI)
# =======================
@app.get("/", response_class=HTMLResponse)
def home():
    return """
    <html>
    <head>
        <title>CV AI Analyzer</title>
        <link rel="preconnect" href="https://fonts.googleapis.com">
        <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap" rel="stylesheet">

        <style>
            body {
                font-family: 'Inter', sans-serif;
                margin: 0;
                padding: 0;
                background: #0C0F1A;
                color: #f1f5f9;
            }

            .hero {
                text-align: center;
                padding: 80px 20px 40px;
            }

            .hero h1 {
                font-size: 46px;
                font-weight: 700;
                margin-bottom: 15px;
                background: linear-gradient(90deg, #6366F1, #A855F7, #EC4899);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
            }

            .hero p {
                font-size: 18px;
                color: #cbd5e1;
            }

            .container {
                max-width: 700px;
                margin: 40px auto;
                padding: 40px;
                background: #111827;
                border-radius: 20px;
                box-shadow: 0 0 40px rgba(0,0,0,0.45);
                animation: fadeIn 0.7s ease-out;
                border: 1px solid rgba(255,255,255,0.07);
            }

            @keyframes fadeIn {
                from { opacity: 0; transform: translateY(20px); }
                to { opacity: 1; transform: translateY(0); }
            }

            label {
                font-weight: 600;
                margin-top: 15px;
                display: block;
                color: #e2e8f0;
            }

            input[type="file"], textarea {
                width: 100%;
                padding: 14px;
                border-radius: 12px;
                border: 1px solid rgba(255,255,255,0.15);
                background: rgba(255,255,255,0.05);
                color: white;
                margin-top: 8px;
                font-size: 15px;
                transition: border 0.3s, background 0.3s;
            }

            input[type="file"]:hover,
            textarea:focus {
                border-color: #A855F7;
                background: rgba(255,255,255,0.08);
            }

            textarea {
                resize: none;
                height: 120px;
            }

            button {
                width: 100%;
                margin-top: 25px;
                padding: 16px;
                font-size: 17px;
                border-radius: 12px;
                border: none;
                font-weight: 600;
                cursor: pointer;
                color: white;
                background: linear-gradient(90deg, #6366F1, #A855F7, #EC4899);
                transition: 0.25s;
                box-shadow: 0 4px 20px rgba(168, 85, 247, 0.35);
            }

            button:hover {
                opacity: 0.92;
                transform: translateY(-2px);
                box-shadow: 0 6px 22px rgba(236, 72, 153, 0.4);
            }

            #answer {
                margin-top: 30px;
                padding: 28px;
                background: rgba(255,255,255,0.05);
                border-radius: 15px;
                border: 1px solid rgba(255,255,255,0.12);

                white-space: pre-wrap;       /* Preserve formatting but wrap text */
                overflow-wrap: break-word;   /* Force wrap for long content */
                word-break: break-word;      /* Break long words/lists */
                max-width: 100%;             /* Prevent stretching outside */
                box-sizing: border-box;      /* Keeps padding inside boundaries */

                font-size: 15px;
                line-height: 1.7;
                color: #e2e8f0;
                animation: fadeIn 0.45s ease-out;
            }

           
            #answer pre {
                margin: 0;
                white-space: pre-wrap;
                overflow-wrap: break-word;
                word-break: break-word;
            }

            .loading {
                margin-top: 20px;
                font-size: 16px;
                text-align: center;
                color: #A855F7;
                font-weight: 600;
            }

        </style>
    </head>

    <body>

        <div class="hero">
            <h1>✨ CV AI Analyzer</h1>
            <p>Your CV, analyzed instantly — powered by advanced AI.</p>
        </div>

        <div class="container">
            <form id="form">

                <label>Upload CV (PDF)</label>
                <input type="file" id="file" accept=".pdf" required>

                <label>Your Question</label>
                <textarea id="question" placeholder="e.g., Summarize my work experience professionally"></textarea>

                <button type="submit">Analyze Now</button>
            </form>

            <div id="loader" class="loading" style="display:none;">⏳ Processing...</div>

            <div id="answer"></div>
        </div>

        <script>
            const form = document.getElementById("form");
            const answerDiv = document.getElementById("answer");
            const loader = document.getElementById("loader");

            form.addEventListener("submit", async (e) => {
                e.preventDefault();
                answerDiv.innerHTML = "";
                loader.style.display = "block";

                const file = document.getElementById("file").files[0];
                const question = document.getElementById("question").value;

                const data = new FormData();
                data.append("file", file);
                data.append("question", question);

                const response = await fetch("/analyze", {
                    method: "POST",
                    body: data
                });

                const result = await response.text();
                loader.style.display = "none";
                answerDiv.innerHTML = result;
            });
        </script>

    </body>
    </html>
    """

# =======================
# BACKEND
# =======================

@app.post("/analyze", response_class=HTMLResponse)
async def analyze(file: UploadFile = File(...), question: str = Form(...)):

    if not file.filename.endswith(".pdf"):
        return "<b style='color:red'>Only PDF files allowed</b>"

    cv_text = extract_text_from_pdf(file.file)

    if len(cv_text) < 50:
        return "<b style='color:red'>Couldn't extract text from CV</b>"

    system_prompt = BASE_SYSTEM_PROMPT + "\n" + cv_text
    answer = ask_openrouter(system_prompt, question)

    return f"<pre>{answer}</pre>"
