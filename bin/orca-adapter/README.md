# Orca Minimal Adapter v1

A stdlib-only HTTP relay that exposes Hermes kanban state to Orca's read-only
browser surface over localhost. Zero writes to Hermes state. Reversible
(disable by stopping the process and removing this directory).

## Why

Orca's UI is browser-only; Hermes state lives in a SQLite DB at
`C:/hermes-server/factory/kanban.db`. The adapter bridges them.

## Endpoints

- `GET /health`               — liveness probe.
- `GET /workspaces`           — list kanban workspaces.
- `GET /tasks/active`         — list currently running/in-progress tasks.
- `GET /tasks/{id}/runs`      — list runs for a task.
- `GET /tasks/{id}`           — task detail.
- `GET /gateway`              — gateway/session metadata (read-only).
- `GET /registry`             — canonical registry snippet (read-only).

All endpoints are read-only and respond with JSON. No auth is enforced
beyond binding to `127.0.0.1` (the server refuses to start if bound
elsewhere).

## How to run

    python C:/hermes-server/bin/orca-adapter/server.py --port 7777

Then in Orca, open a tab pointed at
`http://127.0.0.1:7777/tasks/active` to see live Hermes work.

## Scope

- ~150 lines of Python (stdlib only: `http.server`, `sqlite3`, `json`).
- Reversible: stop the process and delete `C:/hermes-server/bin/orca-adapter/`.
- Does NOT introduce a second orchestrator or a separate truth store —
  it reads from the existing `kanban.db` SQLite file.
- Does NOT touch any canonical repo.

## Safety

- Bound to `127.0.0.1` only.
- Read-only SQL queries against `kanban.db` opened in read-only URI mode.
- Returns 503 if the DB is not reachable.