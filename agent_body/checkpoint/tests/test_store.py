"""Tests for the CHECKPOINT STORE.

Stdlib only. Uses the stdlib unittest module via unittest.TestCase so it
runs under `python -m pytest tests/` AND `python -m unittest discover`.

Coverage targets from the task spec:
  - atomic write
  - stale detection (FRESH and STALE)
  - rotation (keep last 10)
  - recovery after a simulated mid-write crash
  - chain-of-thought guard (forbidden field rejection)
"""

from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

# Make the parent `checkpoint/` directory importable as `checkpoint.store`.
HERE = Path(__file__).resolve().parent
PKG_PARENT = HERE.parent
sys.path.insert(0, str(PKG_PARENT))

from checkpoint import store  # noqa: E402  (intentional path bootstrap)


def _make_payload(
    task_id: str = "t_test01",
    *,
    phase: str = "HANDOFF",
    heads: dict | None = None,
    world_hash: str | None = None,
    task_hash: str | None = None,
    knowledge: str = "mission_control://kg/v1/entity/e_test",
    evidence: str = "audit://agent_body/test/row-1",
    writer: str = "jupiter",
    lease: str | None = None,
) -> dict:
    if heads is None:
        heads = {
            "target_repo_branch": "a" * 40,
            "mission_control_kg": "b" * 40,
            "ia_vision_world_state": "c" * 40,
        }
    return {
        "schema": store.SCHEMA_NAME,
        "version": store.SCHEMA_VERSION,
        "task_id": task_id,
        "lifecycle_phase": phase,
        "world_state_hash": world_hash or store.sha256_of_bytes(b"world-v1"),
        "task_state_hash": task_hash or store.sha256_of_bytes(b"task-v1"),
        "knowledge_pointer": knowledge,
        "evidence_pointer": evidence,
        "lease_token": lease,
        "head_observed": heads,
        "writer_profile": writer,
    }


class AtomicWriteTests(unittest.TestCase):
    """Acceptance: atomic write succeeds; file exists; INDEX.json consistent."""

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="ckpt-"))

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_atomic_write_creates_file_and_index(self) -> None:
        p = _make_payload()
        written = store.atomic_write(self.tmp, p)
        self.assertEqual(written["seq"], 0)
        self.assertTrue(written["checkpoint_id"].startswith("ckpt-t_test01-000000-"))
        self.assertTrue(written["checkpoint_id"].endswith("Z"))

        files = list(self.tmp.glob("ckpt-*.json"))
        self.assertEqual(len(files), 1)
        self.assertTrue((self.tmp / "INDEX.json").exists())

        idx = json.loads((self.tmp / "INDEX.json").read_text(encoding="utf-8"))
        self.assertEqual(idx["schema"], store.INDEX_SCHEMA_NAME)
        self.assertEqual(idx["tasks"]["t_test01"]["seq"], 0)
        self.assertEqual(idx["tasks"]["t_test01"]["file"], files[0].name)

    def test_atomic_write_assigns_monotonic_seq(self) -> None:
        for i in range(3):
            written = store.atomic_write(self.tmp, _make_payload())
            self.assertEqual(written["seq"], i)

        ckpts = store.list_checkpoints(self.tmp, "t_test01")
        self.assertEqual(len(ckpts), 3)
        # Newest first.
        self.assertEqual(ckpts[0]["seq"], 2)
        self.assertEqual(ckpts[2]["seq"], 0)

    def test_atomic_write_persists_payload_to_disk(self) -> None:
        written = store.atomic_write(self.tmp, _make_payload(writer="astra"))
        on_disk = json.loads(
            (self.tmp / f"{written['checkpoint_id']}.json").read_text(encoding="utf-8")
        )
        self.assertEqual(on_disk["writer_profile"], "astra")
        self.assertEqual(on_disk["task_id"], "t_test01")
        self.assertEqual(on_disk["seq"], 0)

    def test_atomic_write_returns_written_payload_with_assigned_fields(self) -> None:
        written = store.atomic_write(self.tmp, _make_payload())
        for k in ("seq", "written_at_utc", "checkpoint_id"):
            self.assertIn(k, written)
        self.assertTrue(written["written_at_utc"].endswith("Z"))


class StaleDetectionTests(unittest.TestCase):
    """Acceptance: STALE when HEAD moved; FRESH when unchanged."""

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="ckpt-"))

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_fresh_when_heads_match(self) -> None:
        ck = _make_payload()
        verdict = store.compare_head(ck, current_heads=ck["head_observed"])
        self.assertEqual(verdict["status"], "FRESH")
        self.assertEqual(verdict["deltas"], [])

    def test_stale_when_target_repo_branch_changed(self) -> None:
        ck = _make_payload()
        current = dict(ck["head_observed"])
        current["target_repo_branch"] = "0" * 40
        verdict = store.compare_head(ck, current_heads=current)
        self.assertEqual(verdict["status"], "STALE")
        self.assertEqual(len(verdict["deltas"]), 1)
        self.assertEqual(verdict["deltas"][0]["field"], "target_repo_branch")
        self.assertEqual(verdict["deltas"][0]["observed"], "a" * 40)
        self.assertEqual(verdict["deltas"][0]["current"], "0" * 40)

    def test_stale_when_any_head_changed(self) -> None:
        ck = _make_payload()
        for changed_field in (
            "target_repo_branch",
            "mission_control_kg",
            "ia_vision_world_state",
        ):
            current = dict(ck["head_observed"])
            current[changed_field] = "f" * 40
            verdict = store.compare_head(ck, current_heads=current)
            self.assertEqual(
                verdict["status"],
                "STALE",
                msg=f"expected STALE when {changed_field} moved",
            )

    def test_stale_when_current_head_is_missing(self) -> None:
        # If current world doesn't track a head, we can't claim freshness.
        ck = _make_payload()
        current = {
            "target_repo_branch": "a" * 40,
            "mission_control_kg": "b" * 40,
            # ia_vision_world_state intentionally absent
        }
        verdict = store.compare_head(ck, current_heads=current)
        self.assertEqual(verdict["status"], "STALE")
        self.assertEqual(len(verdict["deltas"]), 1)
        self.assertEqual(verdict["deltas"][0]["field"], "ia_vision_world_state")

    def test_read_returns_latest_for_task(self) -> None:
        for i in range(3):
            store.atomic_write(self.tmp, _make_payload(writer=f"w{i}"))
        latest = store.read(self.tmp, "t_test01")
        self.assertIsNotNone(latest)
        self.assertEqual(latest["seq"], 2)
        self.assertEqual(latest["writer_profile"], "w2")

    def test_read_returns_none_when_no_checkpoints(self) -> None:
        self.assertIsNone(store.read(self.tmp, "t_test01"))


class RotationTests(unittest.TestCase):
    """Acceptance: only last 10 checkpoints per task survive rotation."""

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="ckpt-"))

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_rotation_keeps_last_ten(self) -> None:
        # Write 15 checkpoints.
        for _ in range(15):
            store.atomic_write(self.tmp, _make_payload())
        files = list(self.tmp.glob("ckpt-t_test01-*.json"))
        self.assertEqual(len(files), 10)
        seqs = []
        for f in files:
            parsed = store._parse_filename(f.name)
            self.assertIsNotNone(parsed)
            seqs.append(parsed[1])
        # Surviving seqs are 5..14 (newest 10).
        self.assertEqual(sorted(seqs), list(range(5, 15)))

    def test_rotation_does_not_touch_other_tasks(self) -> None:
        # Write 12 for t_test01, 3 for t_test02.
        for _ in range(12):
            store.atomic_write(self.tmp, _make_payload(task_id="t_test01"))
        for _ in range(3):
            store.atomic_write(self.tmp, _make_payload(task_id="t_test02"))
        self.assertEqual(len(list(self.tmp.glob("ckpt-t_test01-*.json"))), 10)
        self.assertEqual(len(list(self.tmp.glob("ckpt-t_test02-*.json"))), 3)

    def test_rotation_updates_index_to_newest_survivor(self) -> None:
        for _ in range(12):
            store.atomic_write(self.tmp, _make_payload())
        idx = json.loads((self.tmp / "INDEX.json").read_text(encoding="utf-8"))
        self.assertEqual(idx["tasks"]["t_test01"]["seq"], 11)
        # The file referenced in INDEX should exist on disk.
        self.assertTrue((self.tmp / idx["tasks"]["t_test01"]["file"]).exists())


class CrashRecoveryTests(unittest.TestCase):
    """Acceptance: a corrupt .tmp file never breaks INDEX or surviving files."""

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="ckpt-"))

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_corrupt_tmp_does_not_break_index(self) -> None:
        # First write succeeds — gives us a valid baseline.
        store.atomic_write(self.tmp, _make_payload(writer="baseline"))

        # Simulate a crash: leave garbage .tmp behind. Pretend it was
        # half-written before the process died.
        garbage_name = "ckpt-t_test01-000099-20260921T230000Z.json.tmp"
        (self.tmp / garbage_name).write_bytes(b"\x00\x01GARBAGE_NOT_JSON")

        # INDEX.json must still be valid and parseable.
        idx_path = self.tmp / "INDEX.json"
        idx = json.loads(idx_path.read_text(encoding="utf-8"))
        self.assertEqual(idx["tasks"]["t_test01"]["seq"], 0)

        # Surviving checkpoint must still be readable.
        ck = store.read(self.tmp, "t_test01")
        self.assertIsNotNone(ck)
        self.assertEqual(ck["writer_profile"], "baseline")

        # Next atomic_write should succeed and overwrite the garbage on
        # its own tmp (different name).
        store.atomic_write(self.tmp, _make_payload(writer="next"))
        ck_after = store.read(self.tmp, "t_test01")
        self.assertEqual(ck_after["writer_profile"], "next")
        self.assertEqual(ck_after["seq"], 1)

    def test_corrupt_index_recovers_on_next_write(self) -> None:
        store.atomic_write(self.tmp, _make_payload())
        # Corrupt INDEX.json.
        (self.tmp / "INDEX.json").write_text("not json at all")
        # The next write must succeed and re-establish a valid INDEX.
        store.atomic_write(self.tmp, _make_payload(writer="recovered"))
        idx = json.loads((self.tmp / "INDEX.json").read_text(encoding="utf-8"))
        self.assertEqual(idx["schema"], store.INDEX_SCHEMA_NAME)
        self.assertEqual(idx["tasks"]["t_test01"]["seq"], 1)

    def test_corrupt_index_does_not_lose_files(self) -> None:
        store.atomic_write(self.tmp, _make_payload())
        store.atomic_write(self.tmp, _make_payload(writer="second"))
        # Corrupt INDEX.json.
        (self.tmp / "INDEX.json").write_text("corrupt")
        # Both files must still be on disk and readable.
        cks = store.list_checkpoints(self.tmp, "t_test01")
        self.assertEqual(len(cks), 2)
        writers = {c["writer_profile"] for c in cks}
        self.assertEqual(writers, {"jupiter", "second"})


class ChainOfThoughtGuardTests(unittest.TestCase):
    """Acceptance: no chain-of-thought / chat / reasoning field allowed."""

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="ckpt-"))

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_forbidden_fields_are_rejected(self) -> None:
        for field in (
            "reasoning",
            "thoughts",
            "chain_of_thought",
            "cot",
            "messages",
            "chat",
            "conversation",
            "transcript",
            "tool_calls",
            "tool_results",
            "notes",
            "private_notes",
            "embedding",
            "vector",
            "summary",
            "system_prompt",
            "instructions",
        ):
            bad = _make_payload()
            bad[field] = "should never be stored"
            with self.assertRaises(ValueError, msg=f"field {field!r} should be rejected"):
                store.atomic_write(self.tmp, bad)

    def test_no_checkpoint_file_written_when_validation_fails(self) -> None:
        bad = _make_payload()
        bad["reasoning"] = "I'm thinking..."
        with self.assertRaises(ValueError):
            store.atomic_write(self.tmp, bad)
        files = list(self.tmp.glob("ckpt-*.json"))
        self.assertEqual(files, [])

    def test_required_fields_enforced(self) -> None:
        bad = _make_payload()
        del bad["head_observed"]
        with self.assertRaises(ValueError):
            store.atomic_write(self.tmp, bad)

    def test_lifecycle_phase_allowlist(self) -> None:
        bad = _make_payload(phase="WONDERING_OUT_LOUD")
        with self.assertRaises(ValueError):
            store.atomic_write(self.tmp, bad)

    def test_task_id_path_traversal_rejected(self) -> None:
        for bad_id in ("../etc", "..", "a/b", "a\\b", "a..b", "", "x" * 200):
            bad = _make_payload(task_id=bad_id)
            with self.assertRaises(ValueError, msg=f"task_id {bad_id!r} should be rejected"):
                store.validate_payload(bad)
            with self.assertRaises(ValueError):
                store.validate_task_id(bad_id)


class HashFormatTests(unittest.TestCase):
    """Acceptance: hash fields must be sha256:<64 hex>."""

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="ckpt-"))

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_hash_format_enforced(self) -> None:
        bad = _make_payload(world_hash="not-a-hash")
        with self.assertRaises(ValueError):
            store.atomic_write(self.tmp, bad)
        # Confirm no file was written when validation failed.
        files = list(self.tmp.glob("ckpt-*.json"))
        self.assertEqual(files, [])

    def test_task_hash_format_enforced(self) -> None:
        bad = _make_payload(task_hash="sha256:tooshort")
        with self.assertRaises(ValueError):
            store.atomic_write(self.tmp, bad)
        files = list(self.tmp.glob("ckpt-*.json"))
        self.assertEqual(files, [])

    def test_valid_sha256_accepted(self) -> None:
        good = _make_payload()
        written = store.atomic_write(self.tmp, good)
        self.assertTrue(written["world_state_hash"].startswith("sha256:"))
        self.assertEqual(len(written["world_state_hash"]), len("sha256:") + 64)


class EndToEndTest(unittest.TestCase):
    """Single happy-path: write -> read -> compare_head FRESH -> STALE."""

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="ckpt-"))

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_write_read_compare_cycle(self) -> None:
        heads = {
            "target_repo_branch": "1" * 40,
            "mission_control_kg": "2" * 40,
            "ia_vision_world_state": "3" * 40,
        }
        payload = _make_payload(phase="HANDOFF", heads=heads, writer="jupiter")
        written = store.atomic_write(self.tmp, payload)

        ck = store.read(self.tmp, "t_test01")
        self.assertIsNotNone(ck)
        self.assertEqual(ck["checkpoint_id"], written["checkpoint_id"])

        # Fresh — same heads.
        v = store.compare_head(ck, current_heads=heads)
        self.assertEqual(v["status"], "FRESH")

        # World moves on — target repo HEAD bumps.
        moved = dict(heads)
        moved["target_repo_branch"] = "9" * 40
        v = store.compare_head(ck, current_heads=moved)
        self.assertEqual(v["status"], "STALE")
        self.assertEqual(len(v["deltas"]), 1)
        self.assertEqual(v["deltas"][0]["field"], "target_repo_branch")


if __name__ == "__main__":
    unittest.main()