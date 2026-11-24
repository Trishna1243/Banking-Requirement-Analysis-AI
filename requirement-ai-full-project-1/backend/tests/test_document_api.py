import unittest
from contextlib import asynccontextmanager
from io import BytesIO

from docx import Document
from fastapi.testclient import TestClient
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

from backend.app import app


class FakeModelService:
    def __init__(self):
        self.contexts = []

    def analyze_requirement(self, statement, source_context=None):
        self.contexts.append(source_context)
        return {
            "requirement_statement": statement,
            "requirement_type": "non-functional",
            "category": "Security",
            "priority": "High",
            "ambiguity": None,
            "missing_information": [],
            "suggested_questions": [],
            "sdlc_stage": "Design",
            "sdlc_reasoning": "Security controls are specified during design.",
        }

    def health(self):
        return {"ready": True, "cuda_available": True, "device": "cuda:0"}


class FakeRagService:
    def __init__(self):
        self.indexed_chunks = []

    def index_document(self, chunks):
        self.indexed_chunks = chunks

    def retrieve(self, query, document_id, top_k):
        chunk = next(chunk for chunk in self.indexed_chunks if chunk.document_id == document_id)
        return [{
            "chunk_id": chunk.chunk_id,
            "text": chunk.text,
            "source_document": chunk.source_document,
            "source_page": chunk.page_number,
            "source_location": chunk.source_location,
            "distance": 0.1,
        }]


def build_pdf(text="1. The system shall encrypt financial records."):
    writer = PdfWriter()
    page = writer.add_blank_page(width=612, height=792)
    font = DictionaryObject({
        NameObject("/Type"): NameObject("/Font"),
        NameObject("/Subtype"): NameObject("/Type1"),
        NameObject("/BaseFont"): NameObject("/Helvetica"),
    })
    page[NameObject("/Resources")] = DictionaryObject({
        NameObject("/Font"): DictionaryObject({
            NameObject("/F1"): writer._add_object(font),
        }),
    })
    stream = DecodedStreamObject()
    commands = ["BT /F1 12 Tf 72 720 Td"]
    for line in text.splitlines():
        escaped = line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        commands.append(f"({escaped}) Tj T*")
    commands.append("ET")
    stream.set_data(" ".join(commands).encode("latin-1"))
    page[NameObject("/Contents")] = writer._add_object(stream)
    result = BytesIO()
    writer.write(result)
    result.seek(0)
    return result


def build_docx():
    document = Document()
    document.add_paragraph("The payment service must retain transaction audit records.")
    result = BytesIO()
    document.save(result)
    result.seek(0)
    return result


class DocumentApiTests(unittest.TestCase):
    def setUp(self):
        self.model = FakeModelService()
        self.rag = FakeRagService()

        @asynccontextmanager
        async def test_lifespan(application):
            application.state.model_service = self.model
            application.state.model_ready = True
            application.state.model_error = None
            application.state.rag_service = self.rag
            application.state.rag_ready = True
            application.state.rag_error = None
            yield

        self.original_lifespan = app.router.lifespan_context
        app.router.lifespan_context = test_lifespan
        self.client = TestClient(app)
        self.client.__enter__()

    def tearDown(self):
        self.client.__exit__(None, None, None)
        app.router.lifespan_context = self.original_lifespan

    def test_pdf_analysis_indexes_retrieves_and_returns_page_citations(self):
        response = self.client.post(
            "/api/analyze-document",
            files={"file": ("financial-policy.pdf", build_pdf(), "application/pdf")},
        )

        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertEqual(body["requirement_count"], 1)
        item = body["requirements"][0]
        self.assertEqual(item["source_page"], 1)
        self.assertIn("shall encrypt financial records", item["source_evidence"])
        self.assertIsNotNone(item["source_chunk_id"])
        self.assertEqual(item["retrieved_sources"][0]["source_page"], 1)
        self.assertEqual(self.model.contexts[0][0]["source_page"], 1)

    def test_docx_analysis_returns_paragraph_location(self):
        response = self.client.post(
            "/api/analyze-document",
            files={
                "file": (
                    "financial-policy.docx",
                    build_docx(),
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                )
            },
        )

        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertIsNone(body["page_count"])
        item = body["requirements"][0]
        self.assertEqual(item["source_location"], "paragraph:1")
        self.assertEqual(item["retrieved_sources"][0]["source_location"], "paragraph:1")

    def test_labeled_requirements_return_as_individual_cited_records(self):
        identifiers = (
            [f"FR-{index:02d}" for index in range(1, 11)]
            + [f"NFR-{index:02d}" for index in range(1, 7)]
            + [f"BR-{index:02d}" for index in range(1, 5)]
        )
        text = "Functional requirements\n" + "\n".join(
            f"{identifier}: The system shall retain the required record."
            for identifier in identifiers
        )
        response = self.client.post(
            "/api/analyze-document",
            files={"file": ("Digital_Banking_Requirement.pdf", build_pdf(text), "application/pdf")},
        )

        self.assertEqual(response.status_code, 200, response.text)
        requirements = response.json()["requirements"]
        self.assertEqual(
            [item["requirement_id"] for item in requirements],
            identifiers,
        )
        self.assertEqual(len(requirements), 20)
        for item, identifier in zip(requirements, identifiers):
            self.assertEqual(item["source_page"], 1)
            self.assertIn(identifier, item["source_evidence"])
            self.assertTrue(item["source_chunk_id"])
            self.assertTrue(item["retrieved_sources"])


if __name__ == "__main__":
    unittest.main()
