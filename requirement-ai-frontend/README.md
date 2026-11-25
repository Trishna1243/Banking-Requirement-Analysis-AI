# ReqAI Frontend

React + Vite frontend for the local requirement-analysis project.

## Run

```powershell
cd requirement-ai-frontend
npm ci
npm run dev
```

The frontend uses `VITE_API_BASE_URL`, defaulting to `http://127.0.0.1:8000`.

```text
VITE_API_BASE_URL=http://127.0.0.1:8000
```

Open `http://localhost:5173`. The `/api/analyze-document` flow sends PDF or DOCX files to the local
FastAPI backend, persists the successful response in browser session storage, and displays the
extracted source evidence separately from the model-generated analysis.