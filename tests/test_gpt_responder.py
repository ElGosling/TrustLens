from types import SimpleNamespace
import unittest

from app.gpt_responder import GPTResponder, SYSTEM_INSTRUCTIONS


class FakeResponses:
    def __init__(self) -> None:
        self.arguments = None

    def create(self, **kwargs):
        self.arguments = kwargs
        return SimpleNamespace(output_text=" A helpful reply. ")


class GPTResponderTests(unittest.TestCase):
    def test_answer_sends_text_to_the_responses_api(self) -> None:
        responses = FakeResponses()
        client = SimpleNamespace(responses=responses)
        responder = GPTResponder(model="test-model", client=client)

        reply = responder.answer("Hello TrustLens")

        self.assertEqual(reply, "A helpful reply.")
        self.assertEqual(responses.arguments["model"], "test-model")
        self.assertEqual(responses.arguments["input"], "Hello TrustLens")
        self.assertEqual(responses.arguments["instructions"], SYSTEM_INSTRUCTIONS)
        self.assertFalse(responses.arguments["store"])
