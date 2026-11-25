import json
import unittest

from backend.model_service import (
    ModelInferenceError,
    ModelService,
    normalize_missing_information,
    normalize_priority_classification,
)


def queue_model_responses(service, prompts, responses):
    remaining = list(responses)

    def generate(prompt, **kwargs):
        prompts.append(prompt)
        if not remaining:
            raise AssertionError("Unexpected additional model generation call.")
        return json.dumps(remaining.pop(0))

    service.generate = generate


def missing_response(
    reviewed_requirement_ids=None,
    candidate_reviews=None,
    additional_findings=None,
):
    return {
        "reviewed_requirement_ids": reviewed_requirement_ids or [],
        "candidate_reviews": candidate_reviews or [],
        "additional_findings": additional_findings or [],
    }


class PriorityClassificationTests(unittest.TestCase):
    def test_accepts_and_normalizes_all_priority_levels_with_reasoning(self):
        reason = "Failure could interrupt the documented customer activity and cause material service impact."

        for expected in ("Critical", "High", "Medium", "Low"):
            with self.subTest(priority=expected):
                priority, reasoning = normalize_priority_classification(
                    expected.lower(),
                    reason,
                )
                self.assertEqual(priority, expected)
                self.assertEqual(reasoning, reason)

    def test_missing_or_invalid_priority_is_not_silently_assigned(self):
        for invalid in (None, "", "Urgent", 3):
            with self.subTest(priority=invalid):
                priority, reasoning = normalize_priority_classification(
                    invalid,
                    "Failure could interrupt the documented customer activity and cause material service impact.",
                )
                self.assertIsNone(priority)
                self.assertIn("missing or invalid", reasoning)

    def test_generic_or_missing_reasoning_invalidates_priority(self):
        for reason in (None, "", "The requirement is explicitly stated in the document."):
            with self.subTest(reason=reason):
                priority, normalized_reason = normalize_priority_classification(
                    "High",
                    reason,
                )
                self.assertIsNone(priority)
                self.assertIn("concrete consequence", normalized_reason)

    def test_requirement_analysis_uses_reasoned_levels_and_preserves_wording(self):
        service = object.__new__(ModelService)
        prompts = []
        statement = "NFR-01: Encrypt sensitive customer information in transit and at rest."
        service.generate = lambda prompt: (
            prompts.append(prompt)
            or json.dumps(
                {
                    "requirement_statement": "rewritten model wording",
                    "priority": "high",
                    "priority_reasoning": (
                        "Failure could expose sensitive customer information because the requirement "
                        "requires encryption during transmission and storage."
                    ),
                }
            )
        )

        result = service.analyze_requirement(statement)

        self.assertEqual(result["priority"], "High")
        self.assertIn("Failure could expose sensitive customer information", result["priority_reasoning"])
        self.assertEqual(result["requirement_statement"], statement)
        self.assertIn("Critical, High, Medium, Low", prompts[0])
        self.assertIn("Do not classify all security", prompts[0])


class MissingInformationNormalizationTests(unittest.TestCase):
    def test_keeps_only_unique_complete_questions_and_rejects_placeholders(self):
        questions = [
            "No",
            "Yes",
            "N/A",
            "Encryption protocols",
            "Are encryption protocols specified?",
            "are encryption protocols specified?",
            "Which recovery time objective is required?",
        ]

        self.assertEqual(
            normalize_missing_information(questions),
            [
                "Are encryption protocols specified?",
                "Which recovery time objective is required?",
            ],
        )

    def test_requirement_analysis_uses_retrieved_context_without_repeating_document_text(self):
        service = object.__new__(ModelService)
        prompt = []
        service.generate = lambda value: (
            prompt.append(value)
            or json.dumps(
                {
                    "missing_information": [
                        "No",
                        "Are encryption protocols specified?",
                        "Are encryption protocols specified?",
                        "Data retention period",
                    ],
                    "suggested_questions": ["N/A"],
                    "priority": "Medium",
                }
            )
        )

        result = service.analyze_requirement(
            "NFR-01: Protect customer data.",
            [{"source_page": 2, "text": "Customer data must be encrypted."}],
        )

        self.assertEqual(
            result["missing_information"],
            [
                "Are encryption protocols specified?",
            ],
        )
        self.assertEqual(result["suggested_questions"], [])
        self.assertIn("Customer data must be encrypted.", prompt[0])
        self.assertNotIn("Uploaded document text", prompt[0])


class OverallSdlcRecommendationTests(unittest.TestCase):
    def setUp(self):
        self.service = object.__new__(ModelService)
        self.prompts = []

    def test_finalization_separates_sdlc_and_document_wide_gap_analysis(self):
        sdlc_response = {
            "recommended_model": "Evidence-based model",
            "reasoning": "The documented risks require planned verification.",
            "supporting_factors": {
                "requirement_characteristics": "The requirements are explicit.",
                "risk_and_compliance": "Encryption and compliance are specified.",
                "project_complexity": "Banking integrations are described.",
                "development_and_validation": "Verification is necessary.",
            },
            "evidence_limitations": ["Requirement change frequency is not stated."],
        }
        gap_response = missing_response(
            reviewed_requirement_ids=["NFR-01"],
            candidate_reviews=[
                {
                    "requirement_id": "NFR-01",
                    "candidate_question": "Are encryption protocols specified?",
                    "decision": "confirmed_gap",
                    "category": "incomplete",
                    "information": "The encryption algorithm",
                    "why_it_matters": (
                        "The encryption approach cannot be verified without a defined algorithm."
                    ),
                    "evidence_checked": ["NFR-01: Encrypt customer data."],
                    "question": "Which encryption algorithm is required?",
                }
            ]
        )
        queue_model_responses(
            self.service,
            self.prompts,
            [sdlc_response, gap_response],
        )

        result = self.service.finalize_analysis(
            [
                {
                    "requirement_id": "NFR-01",
                    "requirement_statement": "Encrypt customer data.",
                    "source_page": 2,
                    "source_evidence": "NFR-01: Encrypt customer data.",
                    "analysis": {
                        "requirement_type": "non-functional",
                        "missing_information": [
                            "Are encryption protocols specified?",
                        ],
                    },
                    "retrieved_sources": [
                        {
                            "source_page": 2,
                            "text": "NFR-01: Encrypt customer data.",
                        }
                    ],
                }
            ],
            "[page:2]\nNFR-01: Encrypt customer data.",
        )

        recommendation = result["sdlc_recommendation"]
        self.assertEqual(recommendation["recommended_model"], "Evidence-based model")
        self.assertEqual(
            recommendation["supporting_factors"]["risk_and_compliance"],
            "Encryption and compliance are specified.",
        )
        self.assertIn(
            "Requirement change frequency is not stated.",
            recommendation["evidence_limitations"],
        )
        self.assertEqual(
            result["missing_information_by_requirement"]["NFR-01"],
            ["Which encryption algorithm is required?"],
        )
        self.assertEqual(
            result["missing_information_details_by_requirement"]["NFR-01"][0][
                "category"
            ],
            "incomplete",
        )
        self.assertEqual(
            result["missing_information_details_by_requirement"]["NFR-01"][0][
                "evidence_checked"
            ],
            ["NFR-01: Encrypt customer data."],
        )
        self.assertIn("NFR-01: Encrypt customer data.", self.prompts[0])
        self.assertIn("NFR-01: Encrypt customer data.", self.prompts[1])
        self.assertIn("[page:2]", self.prompts[1])
        self.assertIn("candidate questions", self.prompts[1])
        self.assertIn("entire uploaded document", self.prompts[1])
        self.assertNotIn("missing_information_details_by_requirement", self.prompts[0])

    def test_uncertain_recommendation_requires_evidence_limitations(self):
        response = {
            "recommended_model": None,
            "reasoning": "The document is insufficient to compare SDLC models.",
            "supporting_factors": {
                "requirement_characteristics": None,
                "risk_and_compliance": None,
                "project_complexity": None,
                "development_and_validation": None,
            },
            "evidence_limitations": [],
        }
        self.service.generate = lambda prompt: json.dumps(response)

        with self.assertRaisesRegex(
            ModelInferenceError,
            "must explain its evidence limitations",
        ):
            self.service.finalize_analysis(
                [{"requirement_id": "FR-01", "analysis": {"missing_information": []}}],
                "Banking project requirements.",
            )

    def test_classifies_gap_types_and_deduplicates_questions(self):
        sdlc_response = {
            "recommended_model": "Evidence-based model",
            "reasoning": "The supplied requirements support an iterative approach.",
            "supporting_factors": {
                "requirement_characteristics": "The requirements state service outcomes.",
                "risk_and_compliance": None,
                "project_complexity": "Two requirements are supplied.",
                "development_and_validation": "The response target needs validation.",
            },
            "evidence_limitations": ["The document does not specify operational targets."],
        }
        gap_response = missing_response(
            reviewed_requirement_ids=["FR-01", "NFR-01"],
            additional_findings=[
                {
                    "requirement_id": "FR-01",
                    "category": "missing",
                    "information": "Recovery time objective",
                    "why_it_matters": (
                        "Recovery expectations cannot be verified without a target."
                    ),
                    "evidence_checked": [
                        "FR-01: The system shall process requests quickly."
                    ],
                    "question": "What recovery time objective is required?",
                },
                {
                    "requirement_id": "FR-01",
                    "category": "missing",
                    "information": "Recovery time objective",
                    "why_it_matters": (
                        "Recovery expectations cannot be verified without a target."
                    ),
                    "evidence_checked": [
                        "FR-01: The system shall process requests quickly."
                    ],
                    "question": "What target is needed for recovery time?",
                },
                {
                    "requirement_id": "FR-01",
                    "category": "not_missing",
                },
                {
                    "requirement_id": "FR-01",
                    "category": "ambiguous",
                    "information": "Meaning of quickly",
                    "why_it_matters": (
                        "The timing cannot be tested until quickly has a measurable meaning."
                    ),
                    "evidence_checked": [
                        "FR-01: The system shall process requests quickly."
                    ],
                    "question": "What response-time threshold defines quickly?",
                },
                {
                    "requirement_id": "NFR-01",
                    "category": "incomplete",
                    "information": "Backup retention duration",
                    "why_it_matters": (
                        "Retention duration determines which backups remain available."
                    ),
                    "evidence_checked": [
                        "NFR-01: Automated backups every 24 hours."
                    ],
                    "question": "How long should automated backups be retained?",
                },
            ]
        )
        queue_model_responses(
            self.service,
            self.prompts,
            [sdlc_response, gap_response],
        )

        result = self.service.finalize_analysis(
            [
                {
                    "requirement_id": "FR-01",
                    "requirement_statement": "The system shall process requests quickly.",
                    "analysis": {"missing_information": []},
                },
                {
                    "requirement_id": "NFR-01",
                    "requirement_statement": "Automated backups every 24 hours.",
                    "analysis": {"missing_information": []},
                },
            ],
            (
                "[page:1]\nFR-01: The system shall process requests quickly.\n"
                "[page:2]\nNFR-01: Automated backups every 24 hours."
            ),
        )

        fr_gaps = result["missing_information_details_by_requirement"]["FR-01"]
        self.assertEqual(
            [gap["category"] for gap in fr_gaps],
            ["missing", "ambiguous"],
        )
        self.assertEqual(
            result["missing_information_by_requirement"]["FR-01"],
            [
                "What recovery time objective is required?",
                "What response-time threshold defines quickly?",
            ],
        )
        self.assertEqual(
            result["missing_information_details_by_requirement"]["NFR-01"][0][
                "category"
            ],
            "incomplete",
        )
        self.assertIn(
            "candidate question must receive an explicit review",
            self.prompts[1],
        )
        self.assertNotIn("missing_information_details_by_requirement", self.prompts[0])

    def test_missing_validation_error_does_not_discard_sdlc_recommendation(self):
        sdlc_response = {
            "recommended_model": "Evidence-based model",
            "reasoning": "The document supports a staged approach.",
            "supporting_factors": {
                "requirement_characteristics": "The requirements are stated.",
                "risk_and_compliance": None,
                "project_complexity": "Two requirements are documented.",
                "development_and_validation": "Validation is described.",
            },
            "evidence_limitations": ["Change frequency is not specified."],
        }
        queue_model_responses(
            self.service,
            self.prompts,
            [
                sdlc_response,
                missing_response(
                    reviewed_requirement_ids=["FR-01", "NFR-01"],
                    additional_findings=[
                        {
                            "requirement_id": "UNKNOWN",
                            "category": "missing",
                            "information": "Unknown detail",
                            "why_it_matters": "The requirement cannot be verified without it.",
                            "evidence_checked": ["FR-01: Process payments."],
                            "question": "What detail is required?",
                        }
                    ]
                ),
            ],
        )

        result = self.service.finalize_analysis(
            [
                {"requirement_id": "FR-01", "analysis": {"missing_information": []}},
                {"requirement_id": "NFR-01", "analysis": {"missing_information": []}},
            ],
            "FR-01: Process payments.\nNFR-01: Encrypt customer data.",
        )

        self.assertEqual(
            result["sdlc_recommendation"]["recommended_model"],
            "Evidence-based model",
        )
        self.assertIn("unknown or missing requirement ID", result["missing_information_error"])
        self.assertEqual(result["missing_information_by_requirement"], {})
        self.assertEqual(result["missing_information_details_by_requirement"], {})

    def test_empty_findings_are_explicit_for_every_requirement(self):
        sdlc_response = {
            "recommended_model": "Evidence-based model",
            "reasoning": "The requirements support a documented approach.",
            "supporting_factors": {
                "requirement_characteristics": "The requirements are present.",
                "risk_and_compliance": None,
                "project_complexity": "The scope is limited.",
                "development_and_validation": "Testing is described.",
            },
            "evidence_limitations": ["Change frequency is not specified."],
        }
        queue_model_responses(
            self.service,
            self.prompts,
            [
                sdlc_response,
                missing_response(reviewed_requirement_ids=["FR-01", "NFR-01"]),
            ],
        )

        result = self.service.finalize_analysis(
            [
                {"requirement_id": "FR-01", "analysis": {"missing_information": []}},
                {"requirement_id": "NFR-01", "analysis": {"missing_information": []}},
            ],
            "FR-01: Process payments.\nNFR-01: Encrypt customer data.",
        )

        self.assertEqual(
            result["missing_information_by_requirement"],
            {"FR-01": [], "NFR-01": []},
        )
        self.assertEqual(
            result["missing_information_details_by_requirement"],
            {"FR-01": [], "NFR-01": []},
        )

    def test_backup_frequency_is_not_accepted_as_retention_evidence(self):
        sdlc_response = {
            "recommended_model": "Evidence-based model",
            "reasoning": "The requirements support a documented approach.",
            "supporting_factors": {
                "requirement_characteristics": "The requirements are present.",
                "risk_and_compliance": None,
                "project_complexity": "The scope is limited.",
                "development_and_validation": "Testing is described.",
            },
            "evidence_limitations": ["Change frequency is not specified."],
        }
        queue_model_responses(
            self.service,
            self.prompts,
            [
                sdlc_response,
                missing_response(
                    reviewed_requirement_ids=["NFR-06"],
                    candidate_reviews=[
                        {
                            "requirement_id": "NFR-06",
                            "candidate_question": (
                                "How long should automated database backups be retained?"
                            ),
                            "decision": "answered",
                            "evidence_checked": [
                                "The system shall perform automated database backups at least once every 24 hours."
                            ],
                        }
                    ]
                ),
            ],
        )

        result = self.service.finalize_analysis(
            [
                {
                    "requirement_id": "NFR-06",
                    "requirement_statement": (
                        "The system shall perform automated database backups "
                        "at least once every 24 hours."
                    ),
                    "analysis": {
                        "missing_information": [
                            "How long should automated database backups be retained?"
                        ]
                    },
                }
            ],
            (
                "NFR-06: The system shall perform automated database backups "
                "at least once every 24 hours."
            ),
        )

        self.assertIn(
            "does not establish the requested retention detail",
            result["missing_information_error"],
        )
        self.assertEqual(
            result["sdlc_recommendation"]["recommended_model"],
            "Evidence-based model",
        )

    def test_unreviewed_candidate_does_not_become_a_validated_empty_result(self):
        sdlc_response = {
            "recommended_model": "Evidence-based model",
            "reasoning": "The requirements support a documented approach.",
            "supporting_factors": {
                "requirement_characteristics": "The requirements are present.",
                "risk_and_compliance": None,
                "project_complexity": "The scope is limited.",
                "development_and_validation": "Testing is described.",
            },
            "evidence_limitations": ["Change frequency is not specified."],
        }
        queue_model_responses(
            self.service,
            self.prompts,
            [
                sdlc_response,
                missing_response(reviewed_requirement_ids=["NFR-06"]),
            ],
        )

        result = self.service.finalize_analysis(
            [
                {
                    "requirement_id": "NFR-06",
                    "requirement_statement": (
                        "The system shall perform automated database backups "
                        "at least once every 24 hours."
                    ),
                    "analysis": {
                        "missing_information": [
                            "How long should automated database backups be retained?"
                        ]
                    },
                }
            ],
            (
                "NFR-06: The system shall perform automated database backups "
                "at least once every 24 hours."
            ),
        )

        self.assertIn(
            "did not explicitly review every candidate",
            result["missing_information_error"],
        )
        self.assertEqual(
            result["sdlc_recommendation"]["recommended_model"],
            "Evidence-based model",
        )

    def test_finalization_removes_questions_already_answered_in_document(self):
        sdlc_response = {
            "recommended_model": "Evidence-based model",
            "reasoning": "The supplied requirements support an iterative approach.",
            "supporting_factors": {
                "requirement_characteristics": "The requirements are explicit.",
                "risk_and_compliance": "The document identifies security needs.",
                "project_complexity": "The project scope is described.",
                "development_and_validation": "The requirements need validation.",
            },
            "evidence_limitations": ["Change frequency is not stated."],
        }
        gap_response = missing_response(
            reviewed_requirement_ids=["BR-02", "NFR-06"],
            candidate_reviews=[
                {
                    "requirement_id": "BR-02",
                    "candidate_question": (
                        "Is the registered mobile number required before OTP verification?"
                    ),
                    "decision": "answered",
                    "evidence_checked": [
                        "A customer must have a valid registered mobile number to complete OTP verification."
                    ],
                },
                {
                    "requirement_id": "BR-02",
                    "candidate_question": "What is the source of the registered mobile number?",
                    "decision": "answered",
                    "evidence_checked": [
                        "New customers register by providing their mobile number."
                    ],
                },
                {
                    "requirement_id": "NFR-06",
                    "candidate_question": "What is the backup retention policy?",
                    "decision": "confirmed_gap",
                    "category": "incomplete",
                    "information": "Backup retention duration",
                    "why_it_matters": (
                        "Retention duration determines which backups remain available for recovery."
                    ),
                    "evidence_checked": [
                        "The system shall perform automated database backups at least once every 24 hours."
                    ],
                    "question": "How long should database backups be retained?",
                },
            ]
        )
        queue_model_responses(
            self.service,
            self.prompts,
            [sdlc_response, gap_response],
        )

        result = self.service.finalize_analysis(
            [
                {
                    "requirement_id": "BR-02",
                    "requirement_statement": (
                        "A customer must have a valid registered mobile number "
                        "to complete OTP verification."
                    ),
                    "analysis": {
                        "missing_information": [
                            "Is the registered mobile number required before OTP verification?",
                            "What is the source of the registered mobile number?",
                        ],
                    },
                },
                {
                    "requirement_id": "NFR-06",
                    "requirement_statement": (
                        "The system shall perform automated database backups "
                        "at least once every 24 hours."
                    ),
                    "analysis": {
                        "missing_information": [
                            "What is the backup retention policy?",
                        ],
                    },
                },
            ],
            "\n".join(
                [
                    "New customers register by providing their mobile number.",
                    "A customer must have a valid registered mobile number to complete OTP\nverification.",
                    "The system shall perform automated database backups at least once every 24 hours.",
                ]
            ),
        )

        self.assertEqual(
            result["missing_information_by_requirement"]["BR-02"],
            [],
        )
        self.assertEqual(
            result["missing_information_by_requirement"]["NFR-06"],
            ["How long should database backups be retained?"],
        )
        self.assertEqual(
            result["missing_information_by_requirement"]["BR-02"],
            [],
        )


if __name__ == "__main__":
    unittest.main()
