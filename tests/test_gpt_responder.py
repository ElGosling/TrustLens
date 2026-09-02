import json
from types import SimpleNamespace
import unittest

from app.evidence import EvidenceSource
from app.gpt_responder import GPTResponder, SYSTEM_INSTRUCTIONS
from app.verdict import Verdict


class FakeResponses:
    def __init__(self) -> None:
        self.arguments = None

    def create(self, **kwargs):
        self.arguments = kwargs
        return SimpleNamespace(
            output_text=json.dumps(
                {
                    "verdict": "True",
                    "confidence": 82,
                    "explanation": "The official source supports the claim. It describes the same rule.",
                    "source_ids": [1],
                }
            )
        )


class GPTResponderTests(unittest.TestCase):
    def test_check_claim_sends_evidence_and_maps_source_ids(self) -> None:
        responses = FakeResponses()
        client = SimpleNamespace(responses=responses)
        responder = GPTResponder(model="test-model", client=client)
        source = EvidenceSource(
            title="Official guidance",
            url="https://www.gov.sg/guidance",
            domain="www.gov.sg",
            snippet="The rule applies.",
        )

        result = responder.check_claim("The rule applies.", [source])

        self.assertEqual(result.verdict, Verdict.TRUE)
        self.assertEqual(result.confidence, 82)
        self.assertEqual(result.sources, (source,))
        self.assertEqual(responses.arguments["model"], "test-model")
        self.assertEqual(responses.arguments["instructions"], SYSTEM_INSTRUCTIONS)
        self.assertFalse(responses.arguments["store"])
        self.assertEqual(json.loads(responses.arguments["input"])["claim"], "The rule applies.")
        self.assertEqual(responses.arguments["text"]["format"]["type"], "json_schema")
        self.assertNotIn(
            "uniqueItems",
            responses.arguments["text"]["format"]["schema"]["properties"]["source_ids"],
        )
