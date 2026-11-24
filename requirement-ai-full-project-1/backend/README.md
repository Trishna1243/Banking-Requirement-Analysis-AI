# Financial Requirement Analysis — Backend

This FastAPI backend loads the local fine-tuned Qwen3-4B model during application startup.
It does not retrain or merge the model.

## Local Windows model setup

The project is expected to contain:

```text
requirement-ai-full-project/
  models/
    Qwen3-4B/
    qwen3-4b-finetuned/
  backend/
```

The default model paths are resolved relative to the project root. Relative or absolute overrides
can be provided through environment variables:

```text
QWEN_BASE_MODEL_PATH=models/Qwen3-4B
QLORA_ADAPTER_PATH=models/qwen3-4b-finetuned
QWEN_MAX_NEW_TOKENS=384
RAG_VECTOR_STORE_PATH=backend/vector_store
RAG_EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
```

RAG embeddings run on CPU to avoid using additional VRAM. The embedding model is a small
sentence-embedding model, not another generative LLM; it is downloaded to the Hugging Face model
cache if it is not already cached. Uploaded text and vectors are persisted locally under
`backend/vector_store` unless overridden with `RAG_VECTOR_STORE_PATH`.

Install the RAG/document dependencies into the existing environment with the working PyTorch CUDA
build:

```powershell
cd requirement-ai-full-project\backend
..\.venv\Scripts\python.exe -m pip install python-docx chromadb sentence-transformers
```

Do not downgrade or reinstall the working PyTorch CUDA installation. Do not run a broad dependency
upgrade as part of this setup.

## Start the backend

From the project root:

```powershell
cd requirement-ai-full-project
uvicorn backend.app:app --host 127.0.0.1 --port 8000
```

The model is loaded once during FastAPI startup using the 4-bit NF4 configuration. The process
keeps the model and adapter in memory and reuses it for subsequent API requests.

Document analysis runs model inference for each extracted requirement and returns the existing
complete response after all requirements have been processed. Large PDFs can therefore take time
to finish. The blocking PDF/model work runs in a worker thread so other API requests, including
`/health`, remain responsive during analysis. Restart Uvicorn after backend code changes.

The backend will also accept these environment variables from a shell or Uvicorn environment file:

```powershell
.venv\Scripts\python.exe -m uvicorn backend.app:app --host 127.0.0.1 --port 8000 --env-file backend\.env
```

## Existing API routes

- `GET /`
- `GET /health`
- `POST /api/analyze`
- `POST /api/extract-document` — extract requirements from PDF or DOCX.
- `POST /api/analyze-document` — extract, index, retrieve relevant chunks, and analyze PDF or DOCX.

The analysis response keeps its original top-level fields and requirement fields. Each requirement
also includes `source_location`, `source_chunk_id`, and `retrieved_sources`. PDF sources include
page numbers. DOCX source locations use paragraph/table-row identifiers; DOCX page numbers are
`null` because the format does not reliably encode rendered pagination.

Requirement statements are extracted from numbered statements or sentences containing explicit
requirement language. The model analyzes these verbatim extracted statements and retrieved chunks;
it is not asked to invent requirements. `source_evidence` remains extractor-provided, while the
separate `analysis` object contains model-generated classification and analysis.

## Verify the backend

Open `http://127.0.0.1:8000/health` or run:

```powershell
curl http://127.0.0.1:8000/health
```

A ready response includes:

```json
{
  "success": true,
  "status": "ready",
  "model_loaded": true,
  "model_ready": true,
  "cuda_available": true
}
```

If startup model loading fails, `/health` reports `status: "unavailable"` and an explanatory
`model_error` value. Check the Uvicorn startup logs for the full exception.

## Frontend startup

The existing frontend can remain unchanged:

```powershell
cd requirement-ai-full-project\requirement-ai-frontend
npm ci
npm run dev
```

## API routes
- `GET /` — API status
- `GET /health` — health status
- `POST /api/analyze` — analyze one requirement JSON body
- `POST /api/extract-document` — extract numbered statements from PDF
- `POST /api/analyze-document` — extract and analyze all numbered statements in PDF

## Limitations / notes
- PDF extraction uses `pypdf`; scanned image PDFs need OCR, which is not included.
- Unnumbered requirements are identified using explicit requirement-language heuristics; documents
  with unusual wording may require adapting those rules.
- The model's classifications are suggestions, not authoritative compliance decisions. Verify every output against the source document.
- CORS allows the local Vite origins by default; additional origins can be configured through `CORS_ALLOWED_ORIGINS`.
- Do not commit credentials or private documents into a public repository.
