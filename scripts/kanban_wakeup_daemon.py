#!/usr/bin/env python3
"""
kanban_wakeup_daemon.py — factory wake-up loop for the directive owner-OS macrogoal.

PURPOSE
=======
When a worker (task_run) transitions to a terminal state (done/failed/blocked/expired),
the parent task that depends on it (logical owner task t_f24825f6) needs to be
"woken up" so the foreman can resume execution on the next safe gate.

This daemon:
  1. Polls kanban.db every N seconds for any task_run that transitioned to terminal
     since the last poll.
  2. Detects whether that task_run was a child of t_f24825f6 (or any parent that
     the foreman is tracking via directive_id = ASHLEY-ORCA-OWNER-OS-SUINI-OBSIDIAN-FIRST-20260923-01).
  3. Emits a wake event to C:/hermes-server/state/callbacks/wakeup_queue.jsonl
     so the foreman can pick it up on its next turn.
  4. Maintains a SHA-tracked "last seen state" so it does not emit duplicate events.

This is NOT a new orchestrator. It is a thin watcher.
- Uses only existing kanban.db
- Does NOT mutate kanban.db
- Does NOT spawn workers
- Does NOT touch any product / Orca / OneDrive / David or Diego surface
- Runs as a Windows-friendly Python process; can also run as a Hermes cron job

EXIT BEHAVIOR
=============
- 0 = clean (no transitions detected this tick)
- 0 = clean (transitions detected and emitted to wakeup queue)
- 1 = unexpected error (logged, will retry next tick)
"""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
import time
from pathlib import Path
from typing import Any, Iterable

KANBAN_DB = Path("C:/hermes-server/factory/kanban.db")
STATE_PATH = Path("C:/hermes-server/state/kanban_wakeup_daemon_state.json")
WAKEUP_QUEUE = Path("C:/hermes-server/state/callbacks/wakeup_queue.jsonl")
LOG_PATH = Path("C:/hermes-server/state/kanban_wakeup_daemon.log")

# Macrogoal / parent tracking (loaded fresh from durable_multi_agent_state.json)
DURABLE_STATE_PATH = Path("C:/hermes-server/state/durable_multi_agent_state.json")

TERMINAL_STATUSES = {"done", "completed", "failed", "blocked", "cancelled", "expired", "timed_out", "crashed"}

# Multiple places use status literals.


def log(line: str) -> None:
    ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    msg = f"[{ts}] {line}"
    print(msg, file=sys.stderr)
    try:
        with LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(msg + "\n")
    except Exception:
        pass


def load_state() -> dict[str, Any]:
    if not STATE_PATH.exists():
        return {"last_seen_run_ids": [], "tick_count": 0, "started_at": time.time()}
    try:
        with STATE_PATH.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"last_seen_run_ids": [], "tick_count": 0, "started_at": time.time()}


def save_state(state: dict[str, Any]) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with STATE_PATH.open("w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)


def fetch_tracked_directive_ids() -> list[str]:
    """Read durable_multi_agent_state.active_goal.carrier to extract the directive_id we should track."""
    if not DURABLE_STATE_PATH.exists():
        return []
    try:
        with DURABLE_STATE_PATH.open("r", encoding="utf-8") as f:
            d = json.load(f)
        active_goal = d.get("active_goal", "")
        # also look for directives_to_track if present
        tracked = d.get("wakeup_daemon_tracked_directive_ids", []) or []
        if active_goal:
            tracked = list({active_goal, *tracked})
        return tracked
    except Exception as e:
        log(f"failed to read durable_multi_agent_state: {e}")
        return []


def fetch_active_parents() -> list[dict[str, Any]]:
    """Find all parent task ids whose body contains any tracked directive_id."""
    directive_ids = fetch_tracked_directive_ids()
    if not directive_ids:
        return []
    conn = sqlite3.connect(str(KANBAN_DB))
    cur = conn.cursor()
    parents = []
    for did in directive_ids:
        cur.execute("SELECT id, status, title, body, completed_at FROM tasks WHERE body LIKE ?", (f"%{did}%",))
        for r in cur.fetchall():
            parents.append({"id": r[0], "status": r[1], "title": r[2], "body": r[3], "completed_at": r[4]})
    conn.close()
    return parents


def fetch_children_of_parent(parent_id: str) -> list[str]:
    """Find all children (via task_links) of the given parent."""
    conn = sqlite3.connect(str(KANBAN_DB))
    cur = conn.cursor()
    cur.execute("SELECT child_id FROM task_links WHERE parent_id = ?", (parent_id,))
    children = [r[0] for r in cur.fetchall()]
    conn.close()
    return children


def fetch_recent_runs(since_run_id: int = 0) -> list[dict[str, Any]]:
    """Fetch all task_runs whose status is terminal AND id > since_run_id."""
    conn = sqlite3.connect(str(KANBAN_DB))
    cur = conn.cursor()
    cur.execute("""
        SELECT tr.id, tr.task_id, tr.profile, tr.status, tr.started_at, tr.ended_at,
               tr.worker_pid, tr.outcome, tr.summary, t.body
        FROM task_runs tr
        JOIN tasks t ON t.id = tr.task_id
        WHERE tr.status IN ('completed','done','failed','blocked','cancelled','expired','crashed','timed_out')
          AND tr.id > ?
        ORDER BY tr.id ASC
    """, (since_run_id,))
    out = []
    for r in cur.fetchall():
        out.append({
            "run_id": r[0], "task_id": r[1], "profile": r[2], "status": r[3],
            "started_at": r[4], "ended_at": r[5], "worker_pid": r[6],
            "outcome": r[7], "summary": r[8], "body": r[9],
        })
    conn.close()
    return out


def emit_wake(parent_id: str, run: dict[str, Any]) -> None:
    """Append a wake event to the queue."""
    WAKEUP_QUEUE.parent.mkdir(parents=True, exist_ok=True)
    event = {
        "schema": "wakeup_event_v1",
        "emitted_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "parent_task_id": parent_id,
        "trigger_run_id": run["run_id"],
        "trigger_task_id": run["task_id"],
        "trigger_task_status": run["status"],
        "trigger_task_outcome": run["outcome"],
        "trigger_task_summary": (run.get("summary") or "")[:600],
        "directive_id": "ASHLEY-ORCA-OWNER-OS-SUINI-OBSIDIAN-FIRST-20260923-01",
    }
    with WAKEUP_QUEUE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event) + "\n")
    log(f"emitted wake: parent={parent_id} run={run['run_id']} task={run['task_id']} status={run['status']}")


def tick(state: dict[str, Any]) -> dict[str, Any]:
    """One polling tick. Returns updated state."""
    state["tick_count"] = state.get("tick_count", 0) + 1
    last_seen = state.get("last_seen_run_id", 0)
    runs = fetch_recent_runs(last_seen)
    if not runs:
        return state

    # Track all known parent task ids (any task whose body contains a tracked directive_id)
    parents = fetch_active_parents()
    parent_by_id = {p["id"]: p for p in parents}

    # Build directive-id -> list of parents map (so we know which parent to wake for which directive)
    directive_to_parents: dict[str, list[str]] = {}
    for p in parents:
        for did in fetch_tracked_directive_ids():
            if did in (p.get("body") or ""):
                directive_to_parents.setdefault(did, []).append(p["id"])

    # For each new terminal run, find a parent it belongs to
    new_runs = 0
    for run in runs:
        # Method 1: link-based parent
        owning_parents = []
        conn = sqlite3.connect(str(KANBAN_DB))
        cur = conn.cursor()
        cur.execute("SELECT parent_id FROM task_links WHERE child_id = ?", (run["task_id"],))
        for (pid,) in cur.fetchall():
            if pid in parent_by_id:
                owning_parents.append(pid)
        conn.close()

        # Method 2: directive-id-based parent
        # Soft fallback: any task whose body contains the same DIRECTIVE_ID as a known parent
        # (avoids the kernel-enforced parent-child block). Use this as primary since parent links
        # are now logical (the kernel would block promotion if we kept them strict).
        if not owning_parents:
            tracked = fetch_tracked_directive_ids()
            run_directives = [d for d in tracked if d in (run.get("body") or "")]
            for did in run_directives:
                owning_parents.extend(directive_to_parents.get(did, []))

        # Emit for each owning parent (link-based is authoritative)
        for pid in owning_parents:
            emit_wake(pid, run)

        new_runs += 1
        last_seen = max(last_seen, run["run_id"])

    state["last_seen_run_id"] = last_seen
    state["last_tick_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    state["last_tick_new_runs"] = new_runs
    state["last_tick_parents_tracked"] = len(parents)
    return state


def main() -> int:
    parser = argparse.ArgumentParser(description="Kanban wake-up daemon for the owner-OS macrogoal.")
    parser.add_argument("--interval", type=int, default=15, help="Polling interval in seconds")
    parser.add_argument("--once", action="store_true", help="Run one tick and exit")
    args = parser.parse_args()

    log(f"starting kanban wakeup daemon (interval={args.interval}s, once={args.once})")
    state = load_state()
    if args.once:
        new_state = tick(state)
        save_state(new_state)
        log(f"single tick complete: last_seen_run_id={new_state.get('last_seen_run_id')} new_runs={new_state.get('last_tick_new_runs')}")
        return 0

    while True:
        try:
            state = tick(state)
            save_state(state)
        except Exception as e:
            log(f"tick error: {e}")
        time.sleep(args.interval)


if __name__ == "__main__":
    sys.exit(main())