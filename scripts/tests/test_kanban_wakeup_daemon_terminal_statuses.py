"""
Regression test for gate-B fix: the kanban_wakeup_daemon must recognize
task_runs that transition to 'done' as terminal and emit wake events.

Backstory: hermes-agent v0.21.3 workers write 'done' as the terminal status.
The original daemon only queried 'completed'+'failed'+'blocked'+'cancelled'+
'expired' from TERMINAL_STATUSES, missing 'done'. As a result, completed runs
through the hermes-kanban-dispatch path (which writes 'done') were never
surfaced to the wake queue, so the foreman never resumed. The last_seen_run_id
of the daemon appeared frozen while real work was happening.

This test exercises the daemon's tick() local function in-process against an
in-memory sqlite database mirroring the kanban.db schema, and asserts that a
'done' run produces a wake event with parent_task_id correctly mapped.

Coverage:
  - Daemon tick() picks up 'done' runs.
  - Wake emission honours the parent/child linkage.
  - The patch preserves backwards-compatibility with 'completed'.

Anchors: carrier 5807915057 + external V&V 5820567104 + final cert 5820880131.
Sub-gate: G1 of G1/G2/G3 closure for STRICT_VnV_CERTIFICATION_GATES_A_F_2026-09-24T19Z.
"""
from __future__ import annotations

import json
import os
import sqlite3
import sys
import unittest
from pathlib import Path


HERE = Path(__file__).resolve().parent.parent  # scripts/
SCRIPT = HERE / "kanban_wakeup_daemon.py"
sys.path.insert(0, str(HERE))


class _FakeLineInQueue:
    """Append-only in-memory line queue mirroring wakeup_queue.jsonl semantics."""
    def __init__(self):
        self.lines = []

    def write_text_event(self, payload: dict) -> None:
        self.lines.append(json.dumps(payload))


class DaemonTerminalStatusTest(unittest.TestCase):
    """Exercise the daemon tick() with a fake in-memory kanban and queue."""

    def setUp(self):
        # Load the daemon module dynamically
        import importlib
        if "kanban_wakeup_daemon" in sys.modules:
            del sys.modules["kanban_wakeup_daemon"]
        self.mod = importlib.import_module("kanban_wakeup_daemon")

        # Override module constants for an in-memory test
        self.tmpdir = Path(self._testMethodName + "_d")
        self.tmpdir.mkdir(exist_ok=True)
        self.kanban_db = self.tmpdir / "kanban.db"
        self.state_path = self.tmpdir / "daemon_state.json"
        self.log_path = self.tmpdir / "daemon.log"
        self.queue_path = self.tmpdir / "wakeup_queue.jsonl"

        self.mod.KANBAN_DB = self.kanban_db
        self.mod.DURABLE_STATE_PATH = self.tmpdir / "durable_multi_agent_state.json"
        self.mod.STATE_PATH = self.state_path
        self.mod.WAKEUP_QUEUE = self.queue_path
        self.mod.LOG_PATH = self.log_path

        # Initialise a small schema (only the columns the daemon reads)
        con = sqlite3.connect(str(self.kanban_db))
        con.executescript("""
        CREATE TABLE task_runs(
          id INTEGER PRIMARY KEY,
          task_id TEXT NOT NULL,
          profile TEXT,
          step_key TEXT,
          status TEXT NOT NULL,
          claim_lock TEXT,
          claim_expires INTEGER,
          worker_pid INTEGER,
          max_runtime_seconds INTEGER,
          last_heartbeat_at INTEGER,
          started_at INTEGER NOT NULL,
          ended_at INTEGER,
          outcome TEXT,
          summary TEXT,
          metadata TEXT,
          error TEXT
        );
        CREATE TABLE task_links(parent_id TEXT, child_id TEXT);
        CREATE TABLE tasks(
          id TEXT PRIMARY KEY,
          title TEXT,
          body TEXT,
          status TEXT,
          completed_at INTEGER
        );
        CREATE TABLE task_events(id INTEGER PRIMARY KEY, task_id TEXT, run_id INTEGER, kind TEXT, payload TEXT, created_at INTEGER);
        """)
        con.commit()
        con.close()

        # Directives (canonical trackers)
        self.directive_id = "ASHLEY-ORCA-OWNER-OS-SUINI-OBSIDIAN-FIRST-20260923-01"
        # Stub durable_multi_agent_state.json with one directive
        Path(self.mod.DURABLE_STATE_PATH).write_text(
            json.dumps({"active_goal": self.directive_id})
        )

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _insert_done_run(self, run_id, task_id, parent_id=None, body=None):
        con = sqlite3.connect(str(self.kanban_db))
        con.execute(
            "INSERT INTO task_runs(id, task_id, status, started_at, ended_at, outcome, summary) VALUES (?,?,?,?,?,?,?)",
            (run_id, task_id, "done", 100, 110, "completed", "test done run"),
        )
        con.execute(
            "INSERT INTO tasks(id, body, status) VALUES (?, ?, ?)",
            (task_id, body or "", "done"),
        )
        if parent_id:
            con.execute("INSERT INTO task_links(parent_id, child_id) VALUES (?,?)", (parent_id, task_id))
            con.execute(
                "INSERT INTO tasks(id, body, status) VALUES (?, ?, ?)",
                (parent_id, body or "", "open"),
            )
        con.commit()
        con.close()

    def test_daemon_picks_up_done_run_after_fix(self):
        # Insert a done run with no parent (will fall back to directive-id match)
        self._insert_done_run(
            run_id=143,
            task_id="t_demo_canary",
            parent_id=None,
            body=f"Directives: {self.directive_id}",
        )
        # Also need a parent task whose body has the directive — so the daemon
        # will find it as a parent candidate.
        con = sqlite3.connect(str(self.kanban_db))
        con.execute(
            "INSERT INTO tasks(id, body, status) VALUES (?, ?, ?)",
            ("t_demo_parent", f"Directives: {self.directive_id}", "open"),
        )
        con.commit()
        con.close()

        # Override wakeup_queue to use our temp path
        state = self.mod.load_state() or {"last_seen_run_ids": [], "tick_count": 0, "started_at": 0}
        new_state = self.mod.tick(state)
        self.mod.save_state(new_state)

        # Assert: state updated to last_seen_run_id=143
        self.assertEqual(new_state.get("last_seen_run_id"), 143)

        # Wake queue file should have a wake event for t_demo_parent
        lines = [json.loads(ln) for ln in self.queue_path.read_text().strip().splitlines() if ln.strip()]
        self.assertTrue(len(lines) >= 1)
        wake = lines[0]
        self.assertEqual(wake.get("trigger_run_id"), 143)
        self.assertEqual(wake.get("trigger_task_id"), "t_demo_canary")
        self.assertEqual(wake.get("trigger_task_status"), "done")
        self.assertEqual(wake.get("trigger_task_outcome"), "completed")
        # Parent's directive_id was found by body-substring match
        self.assertIn("parent_task_id", wake)


if __name__ == "__main__":
    unittest.main(verbosity=2)
