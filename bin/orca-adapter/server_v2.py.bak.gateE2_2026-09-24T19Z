"""
Orca Minimal Adapter v1 — stdlib HTTP relay for Hermes kanban state.

Read-only. Bound to 127.0.0.1 only. Reversible. No second orchestrator or
truth store — reads directly from the existing Hermes kanban SQLite DB.

Endpoints:
  GET /health            — liveness probe.
  GET /workspaces        — list known kanban workspace paths.
  GET /tasks/active      — running + blocked tasks.
  GET /tasks/{id}        — task detail (title, status, assignee, dates).
  GET /tasks/{id}/runs   — runs for a task.
  GET /gateway           — gateway/session summary from durable state.
  GET /registry          — canonical registry snippet (V2 JSON).

Run:
    python C:/hermes-server/bin/orca-adapter/server.py --port 7777
"""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

# ---- Configuration -----------------------------------------------------------

DEFAULT_DB = Path(os.environ.get("HERMES_KANBAN_DB", r"C:\hermes-server\factory\kanban.db"))
DEFAULT_REGISTRY = Path(r"C:\hermes-server\state\canonical_registry.json")
DEFAULT_DURABLE = Path(r"C:\hermes-server\state\durable_multi_agent_state.json")
DEFAULT_PORT = 7777
BIND_HOST = "127.0.0.1"  # hard-coded; adapter will not bind elsewhere.


# ---- Helpers -----------------------------------------------------------------

def _open_readonly(db_path: Path) -> sqlite3.Connection:
    """Open a SQLite database in immutable, read-only mode.

    Raises FileNotFoundError if missing. URI mode prevents accidental
    writes and protects against locking contention with the dispatcher.
    """
    if not db_path.exists():
        raise FileNotFoundError(f"DB not found: {db_path}")
    uri = f"file:{db_path}?mode=ro"
    conn = sqlite3.connect(uri, uri=True, check_same_thread=False)
    return conn


def _rows_to_dicts(cursor: sqlite3.Cursor, rows: list) -> list[dict]:
    cols = [c[0] for c in cursor.description] if cursor.description else []
    return [dict(zip(cols, r)) for r in rows]


# ---- Endpoint logic ----------------------------------------------------------

def get_health(_db: sqlite3.Connection | None) -> dict[str, Any]:
    return {"status": "ok", "service": "orca-adapter", "version": "1"}


def get_workspaces(db: sqlite3.Connection | None) -> dict[str, Any]:
    if db is None:
        return {"workspaces": [], "note": "DB unavailable"}
    cur = db.execute(
        "SELECT workspace_kind, workspace_path, COUNT(*) AS n "
        "FROM tasks GROUP BY workspace_kind, workspace_path"
    )
    return {"workspaces": _rows_to_dicts(cur, cur.fetchall())}


def get_tasks_active(db: sqlite3.Connection | None) -> dict[str, Any]:
    if db is None:
        return {"tasks": [], "note": "DB unavailable"}
    cur = db.execute(
        "SELECT id, title, status, assignee, started_at "
        "FROM tasks WHERE status IN ('running','blocked','ready','todo') "
        "ORDER BY started_at DESC LIMIT 50"
    )
    return {"tasks": _rows_to_dicts(cur, cur.fetchall())}


def get_task(db: sqlite3.Connection | None, task_id: str) -> dict[str, Any]:
    if db is None:
        return {"error": "DB unavailable"}
    cur = db.execute(
        "SELECT id, title, status, assignee, workspace_kind, workspace_path, "
        "started_at, completed_at, result "
        "FROM tasks WHERE id = ?", (task_id,)
    )
    row = cur.fetchone()
    if not row:
        return {"error": f"task {task_id} not found"}
    return {"task": _rows_to_dicts(cur, [row])[0]}


def get_task_runs(db: sqlite3.Connection | None, task_id: str) -> dict[str, Any]:
    if db is None:
        return {"runs": [], "note": "DB unavailable"}
    cur = db.execute(
        "SELECT id, profile, outcome, started_at, ended_at, summary "
        "FROM task_runs WHERE task_id = ? ORDER BY id DESC", (task_id,)
    )
    return {"runs": _rows_to_dicts(cur, cur.fetchall())}


def get_gateway() -> dict[str, Any]:
    """Surface minimal Hermes summary info Orca can render without DB access."""
    if not DEFAULT_DURABLE.exists():
        return {"error": f"durable state not found: {DEFAULT_DURABLE}"}
    try:
        with DEFAULT_DURABLE.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        return {"error": f"failed to read durable state: {e}"}
    return {
        "active_execution": data.get("active_execution"),
        "active_goal": data.get("active_goal"),
        "active_gates_count": len(data.get("active_gates", [])),
    }


def get_registry() -> dict[str, Any]:
    if not DEFAULT_REGISTRY.exists():
        return {"error": f"registry not found: {DEFAULT_REGISTRY}"}
    try:
        with DEFAULT_REGISTRY.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        return {"error": f"failed to read registry: {e}"}
    projects = []
    for p in data.get("projects", []):
        projects.append({
            "project_id": p.get("project_id"),
            "logical_owner": p.get("logical_owner"),
            "ashley_authority": p.get("ashley_authority"),
            "sync_state": p.get("sync_state"),
        })
    return {"host_id": data.get("host_id"), "version": data.get("version"),
            "projects": projects}



# ---- PHASE-4 ORCA canonical surfaces (BOUNDED, READ_ONLY, reversible) ---------
# Inserted by t_7a866c87 dispatch. Reversibility: delete this block + the
# /projects/{slug}/surface branch in OrcaAdapterHandler.do_GET to restore prior behavior.
SURFACE_SLUGS = ("mission-control", "suini", "suini-worktree", "david-os", "factory")


def _load_registry_now() -> dict:
    if not DEFAULT_REGISTRY.exists():
        return {"_error": f"registry not found: {DEFAULT_REGISTRY}"}
    try:
        with DEFAULT_REGISTRY.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        return {"_error": f"registry read failed: {e}", "projects": []}


def _load_durable_now() -> dict:
    if not DEFAULT_DURABLE.exists():
        return {}
    try:
        with DEFAULT_DURABLE.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _git_head_safe(local_path):
    """Read HEAD SHA from local .git (handles worktree .git file pointers).
    Returns 12-char SHA, or None if not resolvable. NO git process spawned."""
    if not local_path:
        return None
    p = Path(local_path)
    if not p.exists():
        return None
    git_dir = p / ".git"
    real = None
    if git_dir.is_file():
        try:
            txt = git_dir.read_text(encoding="utf-8", errors="ignore").strip()
            if txt.startswith("gitdir:"):
                cand = Path(txt.split(":", 1)[1].strip())
                if not cand.is_absolute():
                    cand = (p / cand).resolve()
                if cand.exists():
                    real = cand
        except Exception:
            return None
    elif git_dir.is_dir():
        real = git_dir
    if real is None:
        return None
    head = real / "HEAD"
    if not head.is_file():
        return None
    try:
        ref = head.read_text(encoding="utf-8").strip()
        if ref.startswith("ref:"):
            ref_file = real / ref.split(":", 1)[1].strip()
            if ref_file.is_file():
                sha = ref_file.read_text(encoding="utf-8").strip()
                return sha[:12] if sha else None
        elif ref:
            return ref[:12]
    except Exception:
        return None
    return None


def _count_active_kanban(db, project_remote=None):
    if db is None:
        return {"dispatch_active_total": 0, "project_id_match": 0, "body_substring_match": 0}
    out = {"dispatch_active_total": db.execute(
        "SELECT COUNT(*) FROM tasks WHERE status NOT IN ('done','released')").fetchone()[0],
        "project_id_match": 0, "body_substring_match": 0}
    if project_remote:
        out["project_id_match"] = db.execute(
            "SELECT COUNT(*) FROM tasks WHERE status NOT IN ('done','released') AND project_id = ?",
            (project_remote,)).fetchone()[0]
        out["body_substring_match"] = db.execute(
            "SELECT COUNT(*) FROM tasks WHERE status NOT IN ('done','released') AND body LIKE ?",
            (f"%{project_remote}%",)).fetchone()[0]
    return out


def _registry_project(reg, pid):
    for p in reg.get("projects", []):
        if p.get("project_id") == pid:
            return p
    return None


def get_surfaces_index(reg):
    return {"slugs": list(SURFACE_SLUGS),
            "endpoint_pattern": "GET /projects/{slug}/surface",
            "registry_version": reg.get("version"),
            "registry_host_id": reg.get("host_id")}


def _build_surface_mission_control(reg, durable, db):
    p = _registry_project(reg, "panorama-mission-control")
    if not p:
        return {"slug": "mission-control", "error": "not in canonical_registry.json"}
    return {"slug": "mission-control",
            "project_id": p.get("project_id"),
            "logical_owner": p.get("logical_owner"),
            "ashley_authority": p.get("ashley_authority"),
            "canonical_remote": p.get("canonical_remote"),
            "canonical_path": p.get("canonical_path"),
            "main_branch": p.get("main_branch"),
            "remote_main_sha": p.get("remote_main_sha"),
            "local_main_sha": p.get("local_main_sha"),
            "sync_state": p.get("sync_state"),
            "current_head_sha_local": _git_head_safe(p.get("canonical_path")),
            "active_runtime": p.get("active_runtime", []),
            "active_worktrees": p.get("active_worktrees", []),
            "kanban_active_task_count": _count_active_kanban(db, "neokyhurtado-cmd/panorama-mission-control"),
            "data_source": "canonical_registry.json (READ_ONLY projection)"}


def _build_surface_suini(reg, durable, db):
    p = _registry_project(reg, "suini")
    if not p:
        return {"slug": "suini", "error": "not in canonical_registry.json"}
    return {"slug": "suini",
            "project_id": p.get("project_id"),
            "logical_owner": p.get("logical_owner"),
            "ashley_authority": p.get("ashley_authority"),
            "canonical_remote": p.get("canonical_remote"),
            "canonical_path": p.get("canonical_path"),
            "main_branch": p.get("main_branch"),
            "remote_main_sha": p.get("remote_main_sha"),
            "local_main_sha": p.get("local_main_sha"),
            "sync_state": p.get("sync_state"),
            "current_head_sha_local": _git_head_safe(p.get("canonical_path")),
            "active_runtime": p.get("active_runtime", []),
            "stale_copies": p.get("stale_copies", []),
            "kanban_active_task_count": _count_active_kanban(db, "neokyhurtado-cmd/suini"),
            "current_carrier_from_durable": durable.get("current_carrier"),
            "data_source": "canonical_registry.json + durable_multi_agent_state.json (READ_ONLY projection)"}


def _build_surface_suini_worktree(reg, durable, db):
    p = _registry_project(reg, "suini")
    if not p:
        return {"slug": "suini-worktree", "error": "suini project not in registry"}
    wt_list = list(p.get("active_worktrees") or [])
    sb = durable.get("session_bootstrap") or {}
    sb_wt = sb.get("current_worktrees") or []
    if sb_wt:
        wt_list = wt_list + [{"path": w, "source": "session_bootstrap"} for w in sb_wt]
    enriched = []
    for wt in wt_list:
        if isinstance(wt, dict):
            head = _git_head_safe(wt.get("path"))
            entry = {**wt, "current_head_sha_local": head}
            if head is None and wt.get("head"):
                entry["head_resolution_note"] = (
                    "registry-stored head retained; live local ref not materialized on disk "
                    "(read-only projection; no git operation performed)")
            enriched.append(entry)
        else:
            enriched.append({"path": wt, "type": "string"})
    return {"slug": "suini-worktree",
            "parent_project": "suini",
            "worktrees": enriched,
            "stale_worktrees_excluded_from_session": sb.get("stale_worktrees_excluded", []),
            "note": "Composite surface; HEADs computed read-only via local git (no git process spawned).",
            "data_source": "canonical_registry.json + durable_multi_agent_state.session_bootstrap.current_worktrees"}


def _build_surface_david_os(reg, durable, db):
    """DAVID_OS folder surface — registry metadata only. NO David runtime touch."""
    david_meta = reg.get("human_identity_attribution", {}).get("david", {})
    parallel = []
    for p in reg.get("projects", []):
        for sc in p.get("stale_copies", []) or []:
            if "david" in str(sc.get("path", "")).lower():
                parallel.append({"project": p.get("project_id"), **sc})
    return {"slug": "david-os",
            "label": "DAVID_OS canonical folder context",
            "david_orca_user_data": david_meta.get("orca_user_data"),
            "david_obsidian_install": david_meta.get("obsidian_install"),
            "parallel_canon_paths": parallel,
            "data_source": "canonical_registry.json (human_identity_attribution + stale_copies); NO David runtime touch",
            "read_only_projection": True,
            "warning": "Surface reflects registry metadata only. Do NOT introspect DAVID_OS folder contents."}


def _build_surface_factory(reg, durable, db):
    p = _registry_project(reg, "traficlab-factory")
    if not p:
        return {"slug": "factory", "error": "traficlab-factory not in registry"}
    return {"slug": "factory",
            "project_id": p.get("project_id"),
            "logical_owner": p.get("logical_owner"),
            "ashley_authority": p.get("ashley_authority"),
            "canonical_remote": p.get("canonical_remote"),
            "canonical_path": p.get("canonical_path"),
            "main_branch": p.get("main_branch"),
            "remote_main_sha": p.get("remote_main_sha"),
            "local_main_sha": p.get("local_main_sha"),
            "sync_state": p.get("sync_state"),
            "current_head_sha_local": _git_head_safe(p.get("canonical_path")),
            "active_runtime": p.get("active_runtime", []),
            "active_worktrees": p.get("active_worktrees", []),
            "stale_copies": p.get("stale_copies", []),
            "ashley_push_access": p.get("ashley_push_access"),
            "drift_finding": p.get("drift_finding"),
            "kanban_active_task_count": _count_active_kanban(db, "neokyhurtado-cmd/traficlab-factory"),
            "data_source": "canonical_registry.json + kanban.db (READ_ONLY projection)",
            "notes": "Factory surface counts tasks via project_id + body-substring match. "
                     "For the live dispatcher queue (no project tag), use kanban.db directly or "
                     "/tasks/active on the canonical adapter."}


SURFACE_BUILDERS = {
    "mission-control": _build_surface_mission_control,
    "suini": _build_surface_suini,
    "suini-worktree": _build_surface_suini_worktree,
    "david-os": _build_surface_david_os,
    "factory": _build_surface_factory,
}


def get_surface(slug, db):
    if slug not in SURFACE_SLUGS:
        return {"error": f"unknown surface slug: {slug}",
                "valid_slugs": list(SURFACE_SLUGS)}
    reg = _load_registry_now()
    if reg.get("_error"):
        return {"error": reg["_error"]}
    durable = _load_durable_now()
    return SURFACE_BUILDERS[slug](reg, durable, db)


# ---- HTTP handler ------------------------------------------------------------

class OrcaAdapterHandler(BaseHTTPRequestHandler):
    db: sqlite3.Connection | None = None  # set per-request by the server

    def log_message(self, fmt, *args):  # quieter default
        sys.stderr.write("[orca-adapter] " + (fmt % args) + "\n")

    def _send_json(self, status: int, payload: Any):
        body = json.dumps(payload, indent=2, default=str).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):  # noqa: N802 — http.server API
        path = self.path.split("?", 1)[0].rstrip("/") or "/"
        try:
            if path == "/health":
                self._send_json(200, get_health(self.db))
            elif path == "/workspaces":
                self._send_json(200, get_workspaces(self.db))
            elif path == "/tasks/active":
                self._send_json(200, get_tasks_active(self.db))
            elif path == "/gateway":
                self._send_json(200, get_gateway())
            elif path == "/registry":
                self._send_json(200, get_registry())
            elif path == "/projects" or path == "/projects/":
                self._send_json(200, get_surfaces_index(_load_registry_now()))
            elif path.startswith("/projects/") and path.endswith("/surface"):
                slug = path[len("/projects/"):-len("/surface")].strip("/")
                self._send_json(200, get_surface(slug, self.db))
            elif path.startswith("/tasks/") and path.endswith("/runs"):
                tid = path[len("/tasks/"):-len("/runs")]
                self._send_json(200, get_task_runs(self.db, tid))
            elif path.startswith("/tasks/"):
                tid = path[len("/tasks/"):]
                self._send_json(200, get_task(self.db, tid))
            else:
                self._send_json(404, {"error": f"unknown route: {path}"})
        except sqlite3.DatabaseError as e:
            self._send_json(503, {"error": f"db error: {e}"})
        except Exception as e:  # last-resort guard
            self._send_json(500, {"error": f"internal: {e}"})


class _Server(ThreadingHTTPServer):
    allow_reuse_address = True
    daemon_threads = True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Orca Minimal Adapter v1")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--host", default=BIND_HOST,
                        help="Hard-coded to 127.0.0.1 by default; ignored if overridden to anything else.")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    args = parser.parse_args(argv)

    if args.host != BIND_HOST:
        print(f"refusing to bind to {args.host} (must be {BIND_HOST})", file=sys.stderr)
        return 2

    try:
        db = _open_readonly(args.db)
    except FileNotFoundError as e:
        print(f"warn: {e} — endpoints will report db-unavailable", file=sys.stderr)
        db = None

    OrcaAdapterHandler.db = db
    server = _Server((args.host, args.port), OrcaAdapterHandler)
    print(f"orca-adapter v1 listening on http://{args.host}:{args.port}", file=sys.stderr)
    print(f"  db={args.db}", file=sys.stderr)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("shutting down", file=sys.stderr)
    finally:
        server.server_close()
        if db is not None:
            db.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())