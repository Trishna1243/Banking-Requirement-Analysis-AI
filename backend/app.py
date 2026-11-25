import re
import logging
import os
import uuid
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, UploadFile, File, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.concurrency import run_in_threadpool
import torch

try:
    from .document_processing import (
        chunk_document,
        extract_document_segments,
        extract_requirement_candidates,
    )
except ImportError:
    from document_processing import (
        chunk_document,
        extract_document_segments,
        extract_requirement_candidates,
    )

logger = logging.getLogger("uvicorn.error")


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.model_service = None
    app.state.model_ready = False
    app.state.model_error = None
    app.state.rag_service = None
    app.state.rag_ready = False
    app.state.rag_error = None

    try:
        try:
            from .model_service import ModelLoadingError, ModelService
        except ImportError:
            from model_service import ModelLoadingError, ModelService

        app.state.model_service = ModelService()
        app.state.model_ready = True
        logger.info("Fine-tuned Qwen3-4B model loaded successfully.")
    except Exception as exc:
        app.state.model_ready = False
        app.state.model_error = str(exc)
        logger.exception("Fine-tuned model could not be loaded during startup.")

    try:
        try:
            from .rag_service import RagService
        except ImportError:
            from rag_service import RagService

        app.state.rag_service = RagService()
        app.state.rag_ready = True
        logger.info("Local RAG embedding and vector store initialized.")
    except Exception as exc:
        app.state.rag_error = str(exc)
        logger.exception("RAG service could not be initialized during startup.")

    yield

    app.state.model_service = None
    app.state.model_ready = False
    app.state.rag_service = None
    app.state.rag_ready = False

app = FastAPI(
    title="Financial Requirement Analysis API",
    description="Extracts numbered requirements from an uploaded policy PDF and analyzes them with the fine-tuned model.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        origin.strip()
        for origin in os.getenv(
            "CORS_ALLOWED_ORIGINS",
            "http://localhost:5173,http://127.0.0.1:5173",
        ).split(",")
        if origin.strip()
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_model_service(request: Request):
    service = getattr(request.app.state, "model_service", None)
    if not getattr(request.app.state, "model_ready", False) or service is None:
        raise HTTPException(
            status_code=503,
            detail="Model is not ready. Check backend startup logs and /health.",
        )
    return service


def get_rag_service(request: Request):
    service = getattr(request.app.state, "rag_service", None)
    if not getattr(request.app.state, "rag_ready", False) or service is None:
        raise HTTPException(
            status_code=503,
            detail="Document retrieval is unavailable. Check backend startup logs and /health.",
        )
    return service


@app.get("/")
def root():
    return {"success": True, "message": "Financial Requirement Analysis API is running."}

@app.get("/health")
def health(request: Request):
    service = getattr(request.app.state, "model_service", None)
    ready = bool(getattr(request.app.state, "model_ready", False) and service)

    model_health = {}
    if service is not None:
        try:
            model_health = service.health()
        except Exception:
            logger.exception("Could not retrieve model health.")

    return {
        "success": True,
        "status": "ready" if ready else "unavailable",
        "model_loaded": ready,
        "model_ready": ready,
        "cuda_available": torch.cuda.is_available(),
        "gpu_name": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
        "model_error": None if ready else getattr(request.app.state, "model_error", None),
        "rag_ready": bool(getattr(request.app.state, "rag_ready", False)),
        "rag_error": getattr(request.app.state, "rag_error", None),
        **model_health,
    }

@app.post("/api/analyze")
async def analyze(payload: dict[str, Any], request: Request):
    requirement = payload.get("requirement_statement") or payload.get("requirement")
    if not requirement or not isinstance(requirement, str):
        raise HTTPException(status_code=400, detail="Provide requirement_statement.")
    service = get_model_service(request)
    try:
        analysis = await run_in_threadpool(service.analyze_requirement, requirement)
    except Exception as exc:
        logger.exception("Model inference failed for /api/analyze.")
        raise HTTPException(status_code=500, detail="Model inference failed.") from exc
    return {"success": True, "analysis": analysis}

def extract_numbered_requirements(pages: list[str]) -> list[dict[str, Any]]:
    # Keep page markers while joining text so a requirement continuing over a page
    # boundary remains intact and can still be attributed to its starting page.
    joined = "\n".join(f"\n[PAGE_{i+1}]\n{text or ''}" for i, text in enumerate(pages))
    pattern = re.compile(r"(?m)^\s*(\d{1,3})\.\s+")
    matches = list(pattern.finditer(joined))
    output = []
    stop_heading = re.compile(r"(?im)^\s*Grievance Redressal Mechanism\s*$")
    unwanted_headings = {
        "How do the Bank collects customer data?",
        "Purpose of collecting data:",
        "Retention of customer data:",
        "Security:",
        "Due diligence:",
        "Data Destruction:",
    }
    for idx, match in enumerate(matches):
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(joined)
        chunk = joined[match.end():end]
        # Special stop for the known heading that follows item 23 in the sample policy.
        if match.group(1) == "23":
            heading = stop_heading.search(chunk)
            if heading:
                chunk = chunk[:heading.start()]
        start_page_markers = list(re.finditer(r"\[PAGE_(\d+)\]", joined[:match.start()]))
        page_num = int(start_page_markers[-1].group(1)) if start_page_markers else 1
        chunk = re.sub(r"\[PAGE_\d+\]", " ", chunk)
        lines = [re.sub(r"\s+", " ", line).strip() for line in chunk.splitlines()]
        lines = [line for line in lines if line and line not in unwanted_headings]
        statement = re.sub(r"\s+", " ", " ".join(lines)).strip()
        statement = re.sub(r"^\s*[-:;]+\s*", "", statement)
        if not statement:
            continue
        output.append({
            "requirement_id": f"REQ-{int(match.group(1)):03d}",
            "requirement_statement": statement,
            "source_page": page_num,
            "source_evidence": statement,
        })
    return output

@app.post("/api/extract-document")
async def extract_document(file: UploadFile = File(...)):
    if not file.filename or not file.filename.lower().endswith((".pdf", ".docx")):
        raise HTTPException(status_code=400, detail="Please upload a PDF or DOCX file.")
    try:
        segments, page_count = await run_in_threadpool(
            extract_document_segments,
            file.file,
            file.filename,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Could not read document: {exc}")
    requirements = get_document_candidates(file.filename, segments)
    return {
        "success": True,
        "filename": file.filename,
        "page_count": page_count,
        "requirement_count": len(requirements),
        "requirements": requirements,
    }

@app.post("/api/analyze-document")
async def analyze_document(request: Request, file: UploadFile = File(...)):
    if not file.filename or not file.filename.lower().endswith((".pdf", ".docx")):
        raise HTTPException(status_code=400, detail="Please upload a PDF or DOCX file.")
    try:
        segments, page_count = await run_in_threadpool(
            extract_document_segments,
            file.file,
            file.filename,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Could not read document: {exc}")
    source_document_text = "\n\n".join(
        f"[{segment.source_location}]\n{segment.text}"
        for segment in segments
        if segment.text.strip()
    )
    candidates = get_document_candidates(file.filename, segments)
    if not candidates:
        raise HTTPException(
            status_code=422,
            detail="No numbered or explicit requirement statements were detected in this document."
        )

    rag_service = get_rag_service(request)
    service = get_model_service(request)
    document_id = str(uuid.uuid4())
    chunks = chunk_document(segments, document_id, file.filename)
    try:
        await run_in_threadpool(rag_service.index_document, chunks)
    except Exception as exc:
        logger.exception("Could not index uploaded document for retrieval.")
        raise HTTPException(status_code=500, detail="Document indexing failed.") from exc

    results = []
    for requirement_index, item in enumerate(candidates, start=1):
        logger.info(
            "Analyzing requirement %s/%s (%s).",
            requirement_index,
            len(candidates),
            item["requirement_id"],
        )
        source_chunk = find_source_chunk(chunks, item)
        try:
            retrieved = await run_in_threadpool(
                rag_service.retrieve,
                item["requirement_statement"],
                document_id,
                3,
            )
        except Exception as exc:
            logger.exception("Could not retrieve source context for a requirement.")
            raise HTTPException(status_code=500, detail="Document retrieval failed.") from exc

        retrieved_sources = []
        if source_chunk:
            retrieved_sources.append({
                "chunk_id": source_chunk.chunk_id,
                "source_document": source_chunk.source_document,
                "source_page": source_chunk.page_number,
                "source_location": source_chunk.source_location,
                "text": source_chunk.text,
            })
        known_chunk_ids = {source["chunk_id"] for source in retrieved_sources}
        for source in retrieved:
            if source["chunk_id"] not in known_chunk_ids:
                retrieved_sources.append(source)
                known_chunk_ids.add(source["chunk_id"])

        try:
            analysis = await run_in_threadpool(
                service.analyze_requirement,
                item["requirement_statement"],
                retrieved_sources,
            )
        except Exception as exc:
            logger.exception("Model inference failed for /api/analyze-document.")
            raise HTTPException(status_code=500, detail="Model inference failed.") from exc
        results.append({
            "requirement_id": item["requirement_id"],
            "requirement_statement": item["requirement_statement"],
            "source_document": file.filename,
            "source_page": item["source_page"],
            "source_evidence": item["source_evidence"],
            "source_location": item["source_location"],
            "source_chunk_id": source_chunk.chunk_id if source_chunk else None,
            "retrieved_sources": retrieved_sources,
            "analysis": analysis,
        })

    sdlc_recommendation = None
    sdlc_status = "failed"
    sdlc_error = None
    missing_information_status = "unverified"
    missing_information_error = None
    try:
        logger.info(
            "Finalizing overall SDLC recommendation and document-wide missing information."
        )
        final_analysis = await run_in_threadpool(
            service.finalize_analysis,
            results,
            source_document_text,
        )
        sdlc_recommendation = final_analysis["sdlc_recommendation"]
        if not isinstance(sdlc_recommendation, dict):
            raise ValueError("Final analysis returned an invalid SDLC recommendation.")
        sdlc_status = "completed"
        missing_information_error = final_analysis.get(
            "missing_information_error"
        )
        if missing_information_error:
            missing_information_status = "unverified"
            logger.error(
                "Document-wide missing-information validation was not completed: %s",
                missing_information_error,
            )
        else:
            validated_missing = final_analysis[
                "missing_information_by_requirement"
            ]
            validated_gap_details = final_analysis[
                "missing_information_details_by_requirement"
            ]
            if (
                not isinstance(validated_missing, dict)
                or not isinstance(validated_gap_details, dict)
                or any(
                    item["requirement_id"] not in validated_missing
                    or item["requirement_id"] not in validated_gap_details
                    for item in results
                )
            ):
                raise ValueError(
                    "Final analysis did not validate missing-information findings for every requirement."
                )
            for item in results:
                requirement_id = item["requirement_id"]
                missing_questions = validated_missing[requirement_id]
                gap_details = validated_gap_details[requirement_id]
                if not isinstance(missing_questions, list) or not isinstance(gap_details, list):
                    raise ValueError(
                        f"Final analysis returned invalid missing-information findings for {requirement_id}."
                    )
                item["analysis"]["missing_information"] = missing_questions
                item["analysis"]["missing_information_details"] = gap_details
            missing_information_status = "validated"
    except Exception as exc:
        logger.exception("Final project analysis failed for /api/analyze-document.")
        sdlc_error = f"{type(exc).__name__}: {exc}"
        missing_information_error = sdlc_error

    return {
        "success": True,
        "filename": file.filename,
        "page_count": page_count,
        "document_id": document_id,
        "requirement_count": len(results),
        "requirements": results,
        "sdlc_recommendation": sdlc_recommendation,
        "sdlc_status": sdlc_status,
        "sdlc_error": sdlc_error,
        "missing_information_status": missing_information_status,
        "missing_information_error": missing_information_error,
    }


def get_document_candidates(filename: str, segments) -> list[dict]:
    candidates = extract_requirement_candidates(segments)
    if filename.lower().endswith(".pdf"):
        if any(
            re.fullmatch(r"(?:NFR|FR|BR)-\d{1,3}", item["requirement_id"], re.IGNORECASE)
            for item in candidates
        ):
            return candidates

        numbered = extract_numbered_requirements([segment.text for segment in segments])
        if numbered:
            for item in numbered:
                item["source_location"] = f"page:{item['source_page']}"
            return numbered

    return candidates


def find_source_chunk(chunks, candidate: dict):
    matching = [
        chunk
        for chunk in chunks
        if chunk.source_location == candidate.get("source_location")
    ]
    evidence = re.sub(r"\s+", " ", candidate.get("source_evidence", "")).strip().casefold()
    for chunk in matching:
        text = re.sub(r"\s+", " ", chunk.text).strip().casefold()
        if evidence and evidence in text:
            return chunk
    return matching[0] if matching else None
