import unittest

from relaylab.agents.reviewer import ReviewerAgent
from relaylab.jsonutil import AgentProtocolError


class ReviewerProtocolTests(unittest.TestCase):
    def test_normalizes_rejected(self) -> None:
        payload = ReviewerAgent._normalize_payload(
            {"status": "rejected", "feedback": "Fix persistence."}
        )
        self.assertEqual(payload["status"], "changes_requested")

    def test_normalizes_request_changes_with_spaces(self) -> None:
        payload = ReviewerAgent._normalize_payload(
            {"status": "Request Changes", "feedback": "Fix the UI."}
        )
        self.assertEqual(payload["status"], "changes_requested")

    def test_normalizes_pass(self) -> None:
        payload = ReviewerAgent._normalize_payload(
            {"status": "PASS", "feedback": "Looks good."}
        )
        self.assertEqual(payload["status"], "approved")

    def test_accepts_feedback_alias(self) -> None:
        payload = ReviewerAgent._normalize_payload(
            {"status": "approved", "reason": "Requirements are met."}
        )
        self.assertEqual(payload["feedback"], "Requirements are met.")

    def test_unknown_status_still_fails_validation(self) -> None:
        payload = ReviewerAgent._normalize_payload(
            {"status": "maybe", "feedback": "Unsure."}
        )
        with self.assertRaises(AgentProtocolError):
            ReviewerAgent._validate(payload)


if __name__ == "__main__":
    unittest.main()
