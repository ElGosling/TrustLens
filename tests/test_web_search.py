import unittest
from pathlib import Path

from app.trusted_domains import TrustedDomainPolicy
from app.web_search import TrustedWebSearch


class FakeSearchClient:
    def __init__(self, results):
        self.results = results
        self.arguments = None

    def search(self, query, **kwargs):
        self.arguments = {"query": query, **kwargs}
        return {"results": self.results}


class TrustedWebSearchTests(unittest.TestCase):
    def setUp(self) -> None:
        self.policy = TrustedDomainPolicy(("bbc.com", "who.int"))

    def test_trusted_subdomain_is_accepted_but_lookalikes_are_rejected(self) -> None:
        client = FakeSearchClient(
            [
                {"title": "BBC", "url": "https://news.bbc.com/story", "content": "Trusted evidence."},
                {"title": "Fake", "url": "https://fake-bbc.com/story", "content": "Bad evidence."},
                {"title": "Scam", "url": "https://bbc.com.scam.net/story", "content": "Bad evidence."},
            ]
        )

        evidence = TrustedWebSearch(self.policy, client).search("A claim")

        self.assertEqual([item.domain for item in evidence], ["news.bbc.com"])
        self.assertTrue(self.policy.is_trusted_url("https://news.bbc.com/story"))
        self.assertFalse(self.policy.is_trusted_url("https://fake-bbc.com/story"))
        self.assertFalse(self.policy.is_trusted_url("https://bbc.com.scam.net/story"))

    def test_multiple_trusted_sources_are_preserved_with_metadata(self) -> None:
        client = FakeSearchClient(
            [
                {"title": "BBC report", "url": "https://bbc.com/news", "content": "BBC snippet."},
                {"title": "WHO report", "url": "https://www.who.int/report", "content": "WHO snippet."},
            ]
        )

        evidence = TrustedWebSearch(self.policy, client).search("Health claim")

        self.assertEqual(len(evidence), 2)
        self.assertEqual(evidence[0].title, "BBC report")
        self.assertEqual(evidence[0].url, "https://bbc.com/news")
        self.assertEqual(evidence[0].domain, "bbc.com")
        self.assertEqual(evidence[0].snippet, "BBC snippet.")
        self.assertEqual(client.arguments["include_domains"], ["bbc.com", "who.int"])

    def test_no_useful_evidence_found_returns_an_empty_list(self) -> None:
        client = FakeSearchClient([])

        evidence = TrustedWebSearch(self.policy, client).search("Unknown claim")

        self.assertEqual(evidence, [])


class TrustedDomainConfigTests(unittest.TestCase):
    def test_domain_file_loads_one_domain_per_line(self) -> None:
        config_path = Path(__file__).parents[1] / "config" / "trusted_domains.txt"

        policy = TrustedDomainPolicy.from_file(config_path)

        self.assertIn("gov.sg", policy.domains)
        self.assertIn("reuters.com", policy.domains)
