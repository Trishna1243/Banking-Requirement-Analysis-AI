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
        self.overall_sdlc_input = None
        self.finalization_error = None
        self.missing_validation_error = None

    def analyze_requirement(self, statement, source_context=None):
        self.contexts.append(source_context)
        return {
            "requirement_statement": statement,
            "requirement_type": "non-functional",
            "category": "Security",
            "priority": "High",
            "priority_reasoning": (
                "Failure could expose sensitive customer data, creating substantial customer and "
                "operational impact."
            ),
            "ambiguity": None,
            "missing_information": ["Which encryption algorithm is required?"],
            "suggested_questions": [],
            "sdlc_stage": "Design",
            "sdlc_reasoning": "Security controls are specified during design.",
        }

    def finalize_analysis(self, analyzed_requirements, source_document_text):
        self.overall_sdlc_input = (analyzed_requirements, source_document_text)
        if self.finalization_error:
            raise self.finalization_error
        result = {
            "sdlc_recommendation": {
                "recommended_model": "Evidence-based test model",
                "reasoning": "The project requirements support this test recommendation.",
                "supporting_factors": {
                    "requirement_characteristics": "The supplied requirements are explicit.",
                    "risk_and_compliance": "The document identifies security concerns.",
                    "project_complexity": "The supplied requirements describe the project scope.",
                    "development_and_validation": "Testing needs are represented in the requirements.",
                },
                "evidence_limitations": ["The document does not describe change frequency."],
            },
            "missing_information_by_requirement": {
                item["requirement_id"]: item["analysis"]["missing_information"]
                for item in analyzed_requirements
            },
            "missing_information_details_by_requirement": {
                item["requirement_id"]: [
                    {
                        "requirement_id": item["requirement_id"],
                        "category": "incomplete",
                        "information": "The encryption algorithm",
                        "why_it_matters": (
                            "The implementation cannot be verified without a defined algorithm."
                        ),
                        "evidence_checked": [item["source_evidence"]],
                        "question": "Which encryption algorithm is required?",
                    }
                ]
                for item in analyzed_requirements
            },
        }
        if self.missing_validation_error:
            result["missing_information_error"] = self.missing_validation_error
            result["missing_information_by_requirement"] = {}
            result["missing_information_details_by_requirement"] = {}
        return result

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
        self.assertEqual(
            item["analysis"]["missing_information"],
            ["Which encryption algorithm is required?"],
        )
        self.assertEqual(
            item["analysis"]["missing_information_details"][0]["requirement_id"],
            item["requirement_id"],
        )
        self.assertEqual(
            item["analysis"]["missing_information_details"][0]["evidence_checked"],
            [item["source_evidence"]],
        )
        self.assertEqual(
            body["sdlc_recommendation"]["recommended_model"],
            "Evidence-based test model",
        )
        self.assertEqual(body["sdlc_status"], "completed")
        self.assertEqual(body["missing_information_status"], "validated")
        analyzed_requirements, source_text = self.model.overall_sdlc_input
        self.assertEqual(len(analyzed_requirements), 1)
        self.assertIn("shall encrypt financial records", source_text)

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
        parts = ["Functional Requirements"]
        for identifier in identifiers:
            if identifier == "NFR-01":
                parts.append("3. Non-Functional Requirements")
            elif identifier == "BR-01":
                parts.append("4. Business Rules")
            parts.append(
                f"{identifier}: The system shall retain the required record."
            )
        parts.extend(
            [
                "5. Constraints The system must comply with financial regulations.",
                "6. Additional Information The bank expects improved customer experience.",
            ]
        )
        text = "\n".join(parts)
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
            self.assertEqual(
                item["analysis"]["requirement_statement"],
                item["requirement_statement"],
            )
            self.assertIn(identifier, item["source_evidence"])
            self.assertTrue(item["source_chunk_id"])
            self.assertTrue(item["retrieved_sources"])
            self.assertEqual(item["analysis"]["priority"], "High")
            self.assertIn("Failure could expose", item["analysis"]["priority_reasoning"])
            self.assertNotIn("5. Constraints", item["requirement_statement"])
            self.assertNotIn("6. Additional Information", item["requirement_statement"])
        self.assertEqual(len(self.model.overall_sdlc_input[0]), 20)
        self.assertIn("Functional Requirements", self.model.overall_sdlc_input[1])
        self.assertIn("5. Constraints", self.model.overall_sdlc_input[1])
        self.assertIn("6. Additional Information", self.model.overall_sdlc_input[1])
        self.assertEqual(
            set(self.model.overall_sdlc_input[0][0]),
            {"requirement_id", "requirement_statement", "source_document", "source_page", "source_evidence",
             "source_location", "source_chunk_id", "retrieved_sources", "analysis"},
        )

    def test_finalization_failure_preserves_completed_requirement_analysis(self):
        self.model.finalization_error = RuntimeError("CUDA out of memory")

        response = self.client.post(
            "/api/analyze-document",
            files={"file": ("financial-policy.pdf", build_pdf(), "application/pdf")},
        )

        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertEqual(body["requirement_count"], 1)
        self.assertEqual(body["requirements"][0]["requirement_id"], "REQ-001")
        self.assertEqual(
            body["requirements"][0]["analysis"]["missing_information"],
            ["Which encryption algorithm is required?"],
        )
        self.assertIsNone(body["sdlc_recommendation"])
        self.assertEqual(body["sdlc_status"], "failed")
        self.assertIn("CUDA out of memory", body["sdlc_error"])
        self.assertEqual(body["missing_information_status"], "unverified")

    def test_missing_validation_error_does_not_fail_sdlc_or_replace_candidates(self):
        self.model.missing_validation_error = (
            "ModelInferenceError: missing-information generation ran out of memory"
        )

        response = self.client.post(
            "/api/analyze-document",
            files={"file": ("financial-policy.pdf", build_pdf(), "application/pdf")},
        )

        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertEqual(body["sdlc_status"], "completed")
        self.assertIsNone(body["sdlc_error"])
        self.assertEqual(body["missing_information_status"], "unverified")
        self.assertIn("ran out of memory", body["missing_information_error"])
        self.assertEqual(
            body["requirements"][0]["analysis"]["missing_information"],
            ["Which encryption algorithm is required?"],
        )
        self.assertNotIn(
            "missing_information_details",
            body["requirements"][0]["analysis"],
        )


if __name__ == "__main__":
    unittest.main()
