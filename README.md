# Integrated Requirement AI Project

Folders:
- `requirement-ai-frontend/` — React/Vite user interface.
- `backend/` — Local FastAPI PDF/DOCX extraction, RAG, and model-analysis API.
- `models/` — Local base model and LoRA adapter directories.
- `backend/vector_store/` — Local persistent document chunks and embeddings (created at runtime).

RAG uses CPU-based `sentence-transformers/all-MiniLM-L6-v2` embeddings and a local persistent
Chroma collection. The existing Qwen3-4B base model and LoRA adapter remain the only generative
model and continue to run with the existing 4-bit GPU configuration.

This project runs the fine-tuned model locally on Windows. The default backend URL is
`http://127.0.0.1:8000`, and the Vite development URL is `http://localhost:5173`.

See [backend/README.md](./backend/README.md) and
[requirement-ai-frontend/README.md](./requirement-ai-frontend/README.md) for startup instructions.

## Run locally on Windows

Terminal 1 - FastAPI:

```powershell
cd requirement-ai-full-project
.\.venv\Scripts\python.exe -m uvicorn backend.app:app --host 127.0.0.1 --port 8000
```

Terminal 2 - Vite:

```powershell
cd requirement-ai-full-project\requirement-ai-frontend
npm ci
npm run dev
```

Open `http://localhost:5173`.
