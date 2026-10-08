"""Contract checks for the versioned Control Plane operator entrypoint (stdlib only)."""

from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[2]
POLICY = ROOT / "runbooks" / "CONTROL_PLANE_OFFICIAL.md"
ENTRY = ROOT / "AGENTS.md"
HERMES_ENTRY = ROOT / "HERMES.md"


class OwnerOperatorContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.policy = POLICY.read_text(encoding="utf-8")
        cls.entry = ENTRY.read_text(encoding="utf-8")
        cls.hermes_entry = HERMES_ENTRY.read_text(encoding="utf-8")

    def test_versioned_entrypoint_points_to_canonical_policy(self):
        self.assertIn("runbooks/CONTROL_PLANE_OFFICIAL.md", self.entry)
        self.assertIn("runbooks/CONTROL_PLANE_OFFICIAL.md", self.hermes_entry)
        self.assertIn("## 14. OWNER DIRECTIVE 2026-10-08", self.policy)

    def test_direct_execution_not_manual_human_dispatch(self):
        for term in ("hands-on operation", "Remote Desktop Commander", "not manual dispatchers"):
            self.assertIn(term, self.policy)
        self.assertIn("do** the work", self.entry)

    def test_delta_sync_unknown_resolution_and_scope(self):
        for term in ("DELTA SYNC", "UNKNOWN -> INVESTIGATE", "one writer", "AUTO_NEXT_SAFE_GATE"):
            self.assertIn(term.lower(), self.policy.lower())

    def test_runtime_handoff_requires_observable_evidence(self):
        for term in ("RUNNING_CONFIRMED", "fresh heartbeat", "scheduler", "ChatGPT/Work"):
            self.assertIn(term, self.policy)
        self.assertIn("ChatGPT/RDC are not a daemon", self.entry)

    def test_direct_preview_not_forced_through_github(self):
        self.assertIn("Vercel", self.policy)
        self.assertIn("GitHub integration is not a prerequisite", self.policy)

    def test_no_frozen_runtime_sha_in_entrypoint(self):
        self.assertIsNone(re.search(r"\b[0-9a-f]{40}\b", self.entry))
        self.assertIn("Only HUMAN_GO", self.entry)


if __name__ == "__main__":
    unittest.main()
