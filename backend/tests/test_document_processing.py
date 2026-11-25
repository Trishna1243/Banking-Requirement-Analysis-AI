import unittest
from io import BytesIO

from docx import Document

from backend.document_processing import (
    DocumentSegment,
    chunk_document,
    extract_document_segments,
    extract_requirement_candidates,
)


class DocumentProcessingTests(unittest.TestCase):
    def test_pdf_extraction_preserves_page_numbers(self):
        from pypdf import PdfWriter
        from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

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
        stream.set_data(
            b"BT /F1 12 Tf 72 720 Td "
            b"(1. The system shall retain transaction records.) Tj ET"
        )
        page[NameObject("/Contents")] = writer._add_object(stream)
        pdf = BytesIO()
        writer.write(pdf)
        pdf.seek(0)

        segments, page_count = extract_document_segments(pdf, "requirements.pdf")

        self.assertEqual(page_count, 1)
        self.assertEqual(segments[0].page_number, 1)
        self.assertEqual(segments[0].source_location, "page:1")
        self.assertIn("shall retain", segments[0].text)

    def test_docx_extracts_paragraphs_and_table_rows_without_fabricated_pages(self):
        document = Document()
        document.add_paragraph("The system must encrypt customer records.")
        table = document.add_table(rows=1, cols=2)
        table.cell(0, 0).text = "Audit log"
        table.cell(0, 1).text = "The system shall retain events for 90 days."
        buffer = BytesIO()
        document.save(buffer)
        buffer.seek(0)

        segments, page_count = extract_document_segments(buffer, "requirements.docx")

        self.assertIsNone(page_count)
        self.assertEqual(segments[0].page_number, None)
        self.assertEqual(segments[0].source_location, "paragraph:1")
        self.assertEqual(segments[1].source_location, "table:1:row:1")
        self.assertIn("90 days", segments[1].text)

    def test_chunking_and_candidate_extraction_preserve_source(self):
        text = (
            "The payment system shall record each transaction and "
            "retain the transaction record for regulatory review."
        )
        segments = [
            DocumentSegment(
                text=text,
                page_number=4,
                source_location="page:4",
            )
        ]

        candidates = extract_requirement_candidates(segments)
        chunks = chunk_document(
            segments,
            document_id="doc-test",
            filename="policy.pdf",
            max_chars=45,
            overlap_chars=10,
        )

        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]["source_page"], 4)
        self.assertEqual(candidates[0]["source_evidence"], text)
        self.assertGreater(len(chunks), 1)
        self.assertTrue(all(chunk.document_id == "doc-test" for chunk in chunks))
        self.assertTrue(all(chunk.source_location == "page:4" for chunk in chunks))
        self.assertEqual(chunks[0].chunk_id, "doc-test:0")
        self.assertTrue(
            any("retain the transaction record" in chunk.text for chunk in chunks)
        )

    def test_explicit_fr_nfr_and_br_identifiers_are_split_and_preserved(self):
        identifiers = (
            [f"FR-{index:02d}" for index in range(1, 11)]
            + [f"NFR-{index:02d}" for index in range(1, 7)]
            + [f"BR-{index:02d}" for index in range(1, 5)]
        )
        text = "\n".join(
            f"{identifier}: Requirement text for {identifier}."
            for identifier in identifiers
        )
        segment = DocumentSegment(text, page_number=3, source_location="page:3")

        candidates = extract_requirement_candidates([segment])

        self.assertEqual([item["requirement_id"] for item in candidates], identifiers)
        self.assertEqual(len(candidates), 20)
        for item, identifier in zip(candidates, identifiers):
            self.assertEqual(item["source_page"], 3)
            self.assertIn(identifier, item["source_evidence"])
            self.assertEqual(item["requirement_statement"], f"Requirement text for {identifier}.")

    def test_flattened_requirements_stop_at_numbered_section_headings(self):
        identifiers = (
            [f"FR-{index:02d}" for index in range(1, 11)]
            + [f"NFR-{index:02d}" for index in range(1, 7)]
            + [f"BR-{index:02d}" for index in range(1, 5)]
        )
        statements = {
            "FR-10": (
                "Customer Profile Management The system shall allow customers to "
                "update their email address and residential address."
            ),
            "NFR-06": (
                "Data Backup The system shall perform automated database backups "
                "at least once every 24 hours."
            ),
            "BR-04": "Each customer shall have a unique customer identification number.",
        }
        parts = ["Functional Requirements"]
        for identifier in identifiers:
            if identifier == "NFR-01":
                parts.append("3. Non-Functional Requirements")
            elif identifier == "BR-01":
                parts.append("4. Business Rules")
            parts.append(
                f"{identifier}: {statements.get(identifier, f'The system shall process {identifier}.')}"
            )
        parts.extend(
            [
                "5. Constraints The system must comply with banking regulations.",
                "6. Additional Information The bank expects improved customer experience.",
            ]
        )
        segment = DocumentSegment(
            " ".join(parts),
            page_number=2,
            source_location="page:2",
        )

        candidates = extract_requirement_candidates([segment])

        self.assertEqual([item["requirement_id"] for item in candidates], identifiers)
        self.assertEqual(len(candidates), 20)
        for item, identifier in zip(candidates, identifiers):
            self.assertEqual(item["source_page"], 2)
            self.assertEqual(item["source_location"], "page:2")
            self.assertTrue(item["source_evidence"].startswith(f"{identifier}:"))
        for identifier, expected_statement in statements.items():
            item = next(candidate for candidate in candidates if candidate["requirement_id"] == identifier)
            self.assertEqual(item["requirement_statement"], expected_statement)
        self.assertTrue(
            all(
                "Constraints" not in item["requirement_statement"]
                and "Additional Information" not in item["requirement_statement"]
                for item in candidates
            )
        )
        self.assertIn("5. Constraints", segment.text)
        self.assertIn("6. Additional Information", segment.text)

    def test_page_boundary_preserves_requirement_page_and_excludes_next_section(self):
        segments = [
            DocumentSegment(
                "NFR-06: Data Backup The system shall perform automated backups every 24 hours.",
                page_number=2,
                source_location="page:2",
            ),
            DocumentSegment(
                "4. Business Rules BR-04: Each customer shall have a unique customer "
                "identification number. 5. Constraints The system must comply with "
                "banking regulations.",
                page_number=3,
                source_location="page:3",
            ),
        ]

        candidates = extract_requirement_candidates(segments)

        by_id = {item["requirement_id"]: item for item in candidates}
        self.assertEqual(by_id["NFR-06"]["source_page"], 2)
        self.assertEqual(
            by_id["NFR-06"]["requirement_statement"],
            "Data Backup The system shall perform automated backups every 24 hours.",
        )
        self.assertEqual(by_id["BR-04"]["source_page"], 3)
        self.assertEqual(by_id["BR-04"]["source_location"], "page:3")
        self.assertEqual(
            by_id["BR-04"]["requirement_statement"],
            "Each customer shall have a unique customer identification number.",
        )


if __name__ == "__main__":
    unittest.main()
