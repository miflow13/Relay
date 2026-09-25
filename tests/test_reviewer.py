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

    def test_unwraps_nested_review(self) -> None:
        payload = ReviewerAgent._normalize_payload(
            {
                "review": {
                    "status": "needs changes",
                    "feedback": "Persist completed notes.",
                }
            }
        )
        self.assertEqual(payload["status"], "changes_requested")
        self.assertEqual(payload["feedback"], "Persist completed notes.")

    def test_uses_verdict_as_status(self) -> None:
        payload = ReviewerAgent._normalize_payload(
            {"verdict": "approve", "comments": "Meets the requirements."}
        )
        self.assertEqual(payload["status"], "approved")
        self.assertEqual(payload["feedback"], "Meets the requirements.")

    def test_boolean_decision_is_normalized(self) -> None:
        payload = ReviewerAgent._normalize_payload(
            {"decision": False, "reason": "Needs keyboard accessibility."}
        )
        self.assertEqual(payload["status"], "changes_requested")

    def test_list_feedback_is_preserved(self) -> None:
        payload = ReviewerAgent._normalize_payload(
            {
                "status": "reject",
                "issues": ["Missing persistence", "Delete button lacks a label"],
            }
        )
        self.assertIn("Missing persistence", payload["feedback"])
        self.assertIn("Delete button lacks a label", payload["feedback"])

    def test_unknown_status_still_fails_validation(self) -> None:
        payload = ReviewerAgent._normalize_payload(
            {"status": "maybe", "feedback": "Unsure."}
        )
        with self.assertRaises(AgentProtocolError):
            ReviewerAgent._validate(payload)


if __name__ == "__main__":
    unittest.main()
