import unittest

from app.evidence import EvidenceSource
from app.fact_check import FactCheckService
from app.verdict import FactCheckResult, Verdict


class FakeSearcher:
    def __init__(self, evidence):
        self.evidence = evidence
        self.claim = None

    def search(self, claim):
        self.claim = claim
        return self.evidence


class FakeGenerator:
    def __init__(self):
        self.arguments = None

    def check_claim(self, claim, evidence):
        self.arguments = (claim, evidence)
        return FactCheckResult(
            verdict=Verdict.TRUE,
            confidence=90,
            explanation="The source directly supports the claim. Its guidance matches the wording.",
            sources=(evidence[0],),
        )


class FactCheckServiceTests(unittest.TestCase):
    def test_no_trusted_evidence_returns_unverified_without_calling_gpt(self) -> None:
        generator = FakeGenerator()
        service = FactCheckService(FakeSearcher([]), generator)

        result = service.check("An unsupported claim")

        self.assertEqual(result.verdict, Verdict.UNVERIFIED)
        self.assertEqual(result.confidence, 0)
        self.assertEqual(result.sources, ())
        self.assertIsNone(generator.arguments)

    def test_result_uses_only_sources_selected_from_the_search_results(self) -> None:
        source = EvidenceSource("Gov", "https://www.gov.sg/page", "www.gov.sg", "Evidence")
        searcher = FakeSearcher([source])
        generator = FakeGenerator()
        service = FactCheckService(searcher, generator)

        reply = service.answer("A test claim")

        self.assertEqual(searcher.claim, "A test claim")
        self.assertEqual(generator.arguments, ("A test claim", [source]))
        self.assertIn("Verdict: True", reply)
        self.assertIn("https://www.gov.sg/page", reply)
