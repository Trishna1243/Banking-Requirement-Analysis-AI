# Banking Requirement Analysis (Using Fine-Tuned LLM and RAG)

## 1. Project Overview

This project focuses on automated software requirement gathering, analysis, and SDLC identification in the financial sector.

The system uses a fine-tuned Large Language Model (LLM) combined with Retrieval-Augmented Generation (RAG) to extract and analyze software requirements from uploaded banking and financial documents.

It helps identify functional requirements, non-functional requirements, and business rules, classify their priorities, identify ambiguities and potential missing information, and recommend a suitable Software Development Life Cycle (SDLC) model.

## 2. Key Features

- **Document Upload:** Upload banking and financial documents in PDF and DOCX formats.
- **Requirement Extraction:** Extract individual software requirements from uploaded documents.
- **Requirement Classification:** Identify functional requirements, non-functional requirements, and business rules.
- **Priority Classification:** Assign priority levels based on requirement importance and potential impact.
- **Ambiguity Detection:** Identify unclear or insufficiently specified requirement details.
- **Missing Information Analysis:** Generate potential clarification questions for incomplete requirements.
- **RAG-Based Retrieval:** Retrieve relevant document sections to support requirement analysis.
- **Source References:** Associate extracted requirements with their original document pages and locations.
- **SDLC Identification:** Analyze the overall requirement set and generate an SDLC recommendation with supporting reasoning.
- **Dashboard:** Display requirement analysis results and summaries.

## 3. Technology Stack

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
- PyTorch

### Retrieval-Augmented Generation
- ChromaDB
- Sentence Transformers
- `sentence-transformers/all-MiniLM-L6-v2`

## 4. System Architecture

The system follows a frontend-backend architecture with separate document-processing, retrieval, and model services.

1. The user uploads a banking or financial document through the React frontend.
2. The FastAPI backend receives the uploaded document.
3. The document-processing module extracts text and identifies individual requirements.
4. The extracted document content is divided into smaller chunks with source metadata.
5. Sentence Transformers generates embeddings for the document chunks.
6. ChromaDB stores the embeddings and associated document information.
7. The RAG service retrieves relevant document sections for individual requirements.
8. The model service passes the requirement and retrieved context to the fine-tuned Qwen3-4B model.
9. The model generates requirement analysis, priority classifications, clarification candidates, and SDLC-related reasoning.
10. The backend returns the analysis results to the frontend for presentation.

## 5. Project Structure

```text
requirement-ai-full-project/
│
├── backend/
│   ├── app.py
│   ├── document_processing.py
│   ├── model_service.py
│   ├── rag_service.py
│   ├── requirements.txt
│   ├── .env.example
│   └── tests/
│
├── requirement-ai-frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── context/
│   │   ├── pages/
│   │   └── utils/
│   ├── package.json
│   ├── package-lock.json
│   └── .env.example
│
├── test_model.py
└── README.md
```

## 6. Model Requirements

The project uses the following models:

- **Base Model:** `Qwen/Qwen3-4B`
- **Fine-Tuned Adapter:** QLoRA adapter trained for software requirement analysis.
- **Embedding Model:** `sentence-transformers/all-MiniLM-L6-v2`

The base model weights and fine-tuned adapter are not included in this repository because of their large storage requirements.

They must be obtained separately and placed in the model paths configured for the backend.

## 7. Prerequisites

Before running the project, install:

- Python 3.11
- Node.js and npm
- A compatible PyTorch environment
- CUDA-compatible GPU for GPU-based model inference (recommended)
- Base model and fine-tuned adapter files

## 8. Installation and Setup

### Step 1: Clone the Repository

```bash
git clone https://github.com/Trishna1243/Banking-Requirement-Analysis-AI.git
```

Navigate to the project directory:

```bash
cd Banking-Requirement-Analysis-AI
```

### Step 2: Backend Setup

Create a Python virtual environment:

```bash
python -m venv .venv
```

Activate it on Windows:

```powershell
.\.venv\Scripts\Activate.ps1
```

Install backend dependencies:

```bash
pip install -r backend/requirements.txt
```

Configure the environment variables using `backend/.env.example`.

Ensure that the base model and fine-tuned adapter paths are correctly configured.

### Step 3: Frontend Setup

Navigate to the frontend directory:

```bash
cd requirement-ai-frontend
```

Install the frontend dependencies:

```bash
npm install
```

## 9. Running the Project

The backend and frontend must run in separate terminals.

### Terminal 1: Start the Backend

From the project root:

```bash
python -m uvicorn backend.app:app --host 127.0.0.1 --port 8000
```

Backend health endpoint:

```text
http://127.0.0.1:8000/health
```

### Terminal 2: Start the Frontend

Navigate to the frontend directory:

```bash
cd requirement-ai-frontend
```

Start the development server:

```bash
npm run dev
```

Open the application in your browser:

```text
http://127.0.0.1:5173
```

## 10. Testing

Backend tests are available in:

```text
backend/tests/
```

Run the tests from the project root:

```bash
pytest backend/tests/
```

## 11. Project Status

The core document-processing, requirement-extraction, requirement-analysis, RAG retrieval, and model-integration workflow has been implemented.

Missing-information validation and the quality of generated analysis are still being evaluated and refined. Model-generated clarification candidates should be reviewed against the original document before being treated as confirmed omissions.

The project is under active development.

---

**Project Domain:** Artificial Intelligence | Natural Language Processing | Software Engineering | Banking and Financial Technology
