import unittest
from pathlib import Path

from app.trusted_domains import TrustedDomainPolicy, TrustedSource
from app.web_search import TrustedWebSearch


class FakeSearchClient:
    def __init__(self, results):
        self.results = results
        self.arguments = None

    def search(self, query, **kwargs):
        self.arguments = {"query": query, **kwargs}
        return {"results": self.results}


def source(domain: str, include_subdomains: bool = True) -> TrustedSource:
    """Make a small reviewed source fixture for tests that do not read TOML."""
    return TrustedSource(
        id=domain.replace(".", "-"),
        name=domain,
        domain=domain,
        include_subdomains=include_subdomains,
        category="test",
        tier=2,
        notes="Test source.",
    )


class TrustedWebSearchTests(unittest.TestCase):
    def setUp(self) -> None:
        self.policy = TrustedDomainPolicy((source("bbc.com"), source("who.int")))

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
        evidence = TrustedWebSearch(self.policy, FakeSearchClient([])).search("Unknown claim")

        self.assertEqual(evidence, [])

    def test_tracking_url_variants_are_returned_only_once(self) -> None:
        client = FakeSearchClient(
            [
                {"title": "BBC", "url": "https://bbc.com/news/article", "content": "Evidence."},
                {
                    "title": "BBC duplicate",
                    "url": "https://bbc.com/news/article?at_medium=RSS&at_campaign=rss",
                    "content": "Duplicate evidence.",
                },
            ]
        )

        evidence = TrustedWebSearch(self.policy, client).search("A claim")

        self.assertEqual(len(evidence), 1)
        self.assertEqual(evidence[0].url, "https://bbc.com/news/article")

    def test_topical_neighbours_are_rejected_when_a_claim_has_specific_terms(self) -> None:
        client = FakeSearchClient(
            [
                {
                    "title": "Singapore to host Dota 2 tournament",
                    "url": "https://bbc.com/dota",
                    "content": "Singapore will host The International.",
                },
                {
                    "title": "Pokemon World Championships heading to Singapore",
                    "url": "https://bbc.com/pokemon",
                    "content": "Singapore will host the Pokemon World Championships in 2027.",
                },
            ]
        )

        evidence = TrustedWebSearch(self.policy, client).search(
            "Singapore to host the next Pokemon championship"
        )

        self.assertEqual([item.url for item in evidence], ["https://bbc.com/pokemon"])


class TrustedSourceConfigTests(unittest.TestCase):
    def test_source_registry_documents_the_government_umbrella(self) -> None:
        config_path = Path(__file__).parents[1] / "config" / "trusted_sources.toml"

        policy = TrustedDomainPolicy.from_toml(config_path)
        government = next(item for item in policy.sources if item.id == "singapore-government")

        self.assertIn("gov.sg", policy.domains)
        self.assertTrue(policy.is_trusted_url("https://www.moh.gov.sg/health-advisories"))
        self.assertIn("moh.gov.sg", government.notes)
        self.assertIn("channelnewsasia.com", policy.domains)

    def test_event_sources_are_available_for_ticketing_claims(self) -> None:
        config_path = Path(__file__).parents[1] / "config" / "trusted_sources.toml"

        policy = TrustedDomainPolicy.from_toml(config_path)

        self.assertTrue(policy.is_trusted_url("https://tour.yeezy.com/"))
        self.assertTrue(policy.is_trusted_url("https://upperhouse.yejakarta.com/"))
        self.assertTrue(policy.is_trusted_url("https://www.pokemon.com/us/play-pokemon/"))
        self.assertTrue(
            policy.is_trusted_url("https://asia-press.portal-pokemon.com/press-release/")
        )

    def test_source_can_disallow_unreviewed_subdomains(self) -> None:
        policy = TrustedDomainPolicy((source("factcheck.afp.com", include_subdomains=False),))

        self.assertTrue(policy.is_trusted_url("https://factcheck.afp.com/article"))
        self.assertFalse(policy.is_trusted_url("https://regional.factcheck.afp.com/article"))
