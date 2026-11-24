# Agentic AI-Based Banking Requirement Analysis

## Project Overview

This project aims to develop an **Agentic AI-based system for automated software requirement gathering, analysis, and SDLC identification in the financial sector**.

The system uses a fine-tuned Large Language Model (LLM) combined with Retrieval-Augmented Generation (RAG) to extract and analyze software requirements from uploaded banking and financial documents.

It helps identify individual requirements, classify their priorities, analyze missing or ambiguous information, and determine the appropriate Software Development Life Cycle (SDLC) approach.

## Key Features

- **Document Upload:** Upload banking and financial documents in PDF and DOCX formats.
- **Requirement Extraction:** Identify and extract individual software requirements from uploaded documents.
- **Requirement Analysis:** Analyze extracted requirements using a fine-tuned LLM.
- **Priority Classification:** Classify requirements based on their importance and context.
- **Missing Information Detection:** Identify incomplete, ambiguous, or unclear requirements.
- **RAG-Based Retrieval:** Retrieve relevant document sections to provide source-grounded analysis.
- **Source References:** Associate extracted requirements with their original document locations.
- **SDLC Identification:** Analyze requirements to identify an appropriate SDLC approach.
- **Dashboard:** View requirement analysis results and summaries.

## Technology Stack

### Frontend
- React.js
- Vite
- JavaScript
- CSS

### Backend
- Python
- FastAPI
- Uvicorn

### AI and Machine Learning
- Qwen3-4B
- QLoRA Fine-Tuning
- Hugging Face Transformers
- PEFT
- BitsAndBytes
- Sentence Transformers

### Retrieval-Augmented Generation
- ChromaDB
- all-MiniLM-L6-v2 Embedding Model

## System Architecture

1. User uploads a banking or financial document through the frontend.
2. The backend extracts the document content.
3. The extracted content is divided into smaller chunks.
4. Embeddings are generated and stored in ChromaDB.
5. Relevant document chunks are retrieved for each requirement.
6. The fine-tuned Qwen3-4B model analyzes the requirements using the retrieved context.
7. Results, including requirement classifications and source references, are returned to the frontend.

## Project Structure

```text
requirement-ai-full-project/
│
├── backend/
│   ├── app.py
│   ├── document_processing.py
│   ├── model_service.py
│   ├── rag_service.py
│   ├── requirements.txt
│   └── tests/
│
├── requirement-ai-frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── context/
│   │   ├── pages/
│   │   └── utils/
│   ├── package.json
│   └── package-lock.json
│
├── test_model.py
└── README.md
```

## Model Requirements

The project uses:
- Base model: `Qwen/Qwen3-4B`
- Fine-tuned adapter: QLoRA adapter trained for software requirement analysis.
- Embedding model: `sentence-transformers/all-MiniLM-L6-v2`

The model weights and adapter files are not included in this repository because of their size. They must be downloaded or configured separately before running the complete AI analysis pipeline.

## Running the Project

### 1. Backend Setup

Create and activate a Python virtual environment, then install the dependencies:

```bash
pip install -r backend/requirements.txt
```

Configure the model paths and other required environment variables using the provided `.env.example` file.

Start the backend:

```bash
python -m uvicorn backend.app:app --host 127.0.0.1 --port 8000
```

### 2. Frontend Setup

Navigate to the frontend directory:

```bash
cd requirement-ai-frontend
```

Install dependencies:

```bash
npm install
```

Start the development server:

```bash
npm run dev
```

The frontend runs at:

`http://localhost:5173`

## Testing

Backend tests are available in:

```text
backend/tests/
```

Run them using:

```bash
pytest backend/tests/
```

## Project Status

The project is under active development. Features, model integration, requirement analysis, and system evaluation are being developed and refined.

---

**Project Domain:** Artificial Intelligence | Natural Language Processing | Software Engineering | Banking and Financial Technology
