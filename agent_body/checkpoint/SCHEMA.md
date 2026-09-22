# CHECKPOINT STORE — SCHEMA

> **Scope**: this schema defines the JSON shape of one operational
> checkpoint and of the per-store index. It is the *only* contract a
> checkpoint consumer reads against. If you add a field here, downstream
> readers must adopt it; if you forget, downstream reads will fail.

## 0. Design intent

A checkpoint gives a fresh Hermes/MiniMax session the **minimum
operational state** needed to resume a task — and **nothing more**.

It is explicitly **not**:

- a chat transcript
- a model reasoning log
- a tool-call history
- a private note
- chain-of-thought in any form

The store is the *resumability seam*. The store is **not** the brain.

## 1. File layout

```
C:/hermes-server/agent_body/checkpoint/
├── SCHEMA.md            # this file
├── README.md            # usage + what NOT to store
├── store.py             # atomic write + read + list + stale-compare
├── tests/
│   └── test_store.py    # pytest, stdlib only
├── INDEX.json           # { task_id -> { seq, file, written_at_utc } }
└── ckpt-<task_id>-<seq>-<utc>.json   # one snapshot per checkpoint
```

- `ckpt-<task_id>-<seq>-<utc>.json` — exactly one JSON object per file.
- `INDEX.json` — small manifest of latest valid checkpoint per task.

### 1.1 Filename grammar

`ckpt-<task_id>-<seq>-<utc>.json`

- `<task_id>` — Hermes task id, alphanumeric + dash, e.g. `t_771d8615`.
  Validated by store.py; rejected if it contains `/`, `\`, `..`, or NUL.
- `<seq>` — zero-padded decimal, monotonically increasing per task,
  starting at `000000`. Width: 6 digits (allows up to 999 999 checkpoints
  per task before rollover; spec retention is 10, so width is generous).
- `<utc>` — UTC timestamp of the write, format `YYYYMMDDTHHMMSSZ`.
  For example: `20260921T233000Z`.

Examples of legal names:

```
ckpt-t_771d8615-000000-20260921T233000Z.json
ckpt-t_771d8615-000001-20260921T234512Z.json
```

Illegal names (rejected by `store.write`):

```
ckpt-../etc/passwd-000000-20260921T233000Z.json     # path traversal
ckpt-t_771d8615-000000-20260921T23:30:00Z.json      # colons illegal on Windows
ckpt-t_771d8615-000000.json                        # missing utc
```

### 1.2 INDEX.json shape

```json
{
  "schema": "AGENT_BODY_CHECKPOINT_INDEX",
  "version": 1,
  "updated_at_utc": "2026-09-21T23:34:55Z",
  "tasks": {
    "t_771d8615": {
      "seq": 1,
      "file": "ckpt-t_771d8615-000001-20260921T234512Z.json",
      "written_at_utc": "2026-09-21T23:45:12Z"
    }
  }
}
```

`INDEX.json` is itself a checkpoint file in the sense that it is written
atomically via `tmp` + `os.replace`. A crash mid-write leaves the previous
valid `INDEX.json` in place.

## 2. Checkpoint payload schema

A checkpoint file is a single JSON object with the following fields.
All fields are required unless explicitly marked optional.

```json
{
  "schema": "AGENT_BODY_CHECKPOINT",
  "version": 1,
  "checkpoint_id": "ckpt-t_771d8615-000001-20260921T234512Z",
  "task_id": "t_771d8615",
  "seq": 1,
  "lifecycle_phase": "HANDOFF",
  "world_state_hash": "sha256:9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08",
  "task_state_hash": "sha256:5feceb66ffc86f38d952786c6d696c79c2dbc239dd4e91b46729d73a27fb57e9",
  "knowledge_pointer": "mission_control://kg/v1/entity/e_abc123",
  "evidence_pointer": "audit://agent_body/2026-09-21/ckpt-t_771d8615-000001",
  "lease_token": null,
  "head_observed": {
    "target_repo_branch": "deadbeefdeadbeefdeadbeefdeadbeefdeadbeef",
    "mission_control_kg": "cafebabecafebabecafebabecafebabecafebabe",
    "ia_vision_world_state": "1234567812345678112345678123456781234567"
  },
  "written_at_utc": "2026-09-21T23:45:12Z",
  "writer_profile": "jupiter"
}
```

### 2.1 Field definitions

| Field                   | Type                | Required | Meaning |
|-------------------------|---------------------|----------|---------|
| `schema`                | string              | yes      | Always the literal `"AGENT_BODY_CHECKPOINT"`. Reader version gate. |
| `version`               | integer             | yes      | Always `1` until this doc bumps it. |
| `checkpoint_id`         | string              | yes      | Echoes the filename minus `.json`. |
| `task_id`               | string              | yes      | Hermes task id this checkpoint belongs to. |
| `seq`                   | integer             | yes      | Zero-padded sequence index. Monotonic per task. |
| `lifecycle_phase`       | string              | yes      | One of `ENTER`, `OBSERVE`, `PLAN`, `ACT`, `VERIFY`, `HANDOFF`, `EXIT`. |
| `world_state_hash`      | string              | yes      | `sha256:<hex>` digest of the *external* world snapshot the writer reasoned over. NOT the content. |
| `task_state_hash`       | string              | yes      | `sha256:<hex>` digest of the task-internal mutable state (e.g. leased files, in-flight sub-delegations). NOT the state. |
| `knowledge_pointer`     | string              | yes      | URI-shaped pointer to the knowledge graph node this task uses. The node, not its content. |
| `evidence_pointer`      | string              | yes      | URI-shaped pointer to the audit row(s) backing the last verify. The row, not its body. |
| `lease_token`           | string or null      | yes      | Opaque lease id if the writer currently holds a writer lease. `null` if not held. |
| `head_observed`         | object              | yes      | Git HEAD SHAs observed at write time. See 2.2. |
| `written_at_utc`        | string              | yes      | ISO-8601 UTC timestamp with `Z` suffix. |
| `writer_profile`        | string              | yes      | Hermes profile that wrote this checkpoint (e.g. `jupiter`). |

### 2.2 `head_observed` shape

```json
"head_observed": {
  "target_repo_branch":       "<40-hex SHA>",
  "mission_control_kg":       "<40-hex SHA>",
  "ia_vision_world_state":    "<40-hex SHA>"
}
```

All three fields are required. They give the next-session reader enough
information to call `compare_head` and decide whether the world has
moved on. A `null` SHA is **not** allowed — if you don't know the head,
you don't have a checkpoint.

### 2.3 Reserved / forbidden fields

The following MUST NOT appear anywhere in a checkpoint payload or
example:

- `reasoning`, `thoughts`, `chain_of_thought`, `cot`
- `messages`, `chat`, `conversation`, `transcript`, `dialogue`
- `tool_calls`, `tool_results`, `function_calls`
- `notes`, `private_notes`, `scratch`, `memo`, `diary`
- `embedding`, `vector`, `summary`, `paraphrase`
- `system_prompt`, `developer_prompt`, `instructions`

`store.py:validate_payload()` enforces this list at write time. Adding a
forbidden field raises `ValueError("forbidden field: <name>")` and the
checkpoint is not written.

## 3. STALE / FRESH verdict

`store.compare_head(checkpoint, current_heads) -> Verdict`

```
Verdict = {
  "status":     "FRESH" | "STALE",
  "reason":     str | None,
  "deltas":     [ { "field": str, "observed": str, "current": str }, ... ]
}
```

- `FRESH` — every SHA in `head_observed` equals the current SHA.
- `STALE` — at least one SHA changed. Reader MUST NOT resume blindly;
  it must call the resolver (MVP-4) and re-validate before continuing.

`compare_head` is the gate between "session resumes" and "session
reconciles first". It is intentionally dumb — it does not try to merge,
it does not try to be clever. If a head moved, it is STALE.

## 4. Atomicity guarantee

Every write is performed as:

1. Compute target filename `ckpt-<task>-<seq>-<utc>.json`.
2. Serialize payload to bytes.
3. Write bytes to `ckpt-<task>-<seq>-<utc>.json.tmp` with `O_CREAT|O_WRONLY|O_TRUNC`.
4. `fsync` the tmp file.
5. `os.replace(tmp, final)` — atomic on POSIX, atomic on Windows when the
   destination is on the same volume (which is guaranteed for this store).
6. Update `INDEX.json.tmp`, fsync, `os.replace` to `INDEX.json`.
7. Apply retention: keep only the latest 10 (seq desc) per task, delete the rest.

If the process dies between steps 3 and 5, the final file does not exist
and `INDEX.json` is unchanged. If the process dies between step 6 mid-
write, the previous `INDEX.json` is unchanged. There is no recovery
required — the next write just creates a new file with a new sequence.

## 5. Retention

- Per task: keep the last **10** checkpoints (`seq` descending). Older
  files are deleted at the end of each successful write.
- The store never deletes checkpoints from other tasks.
- `INDEX.json` is updated to reflect only the surviving newest entry.
- Deletion is `os.remove` per file; never a recursive rmtree.

## 6. Reversibility

Deleting the entire checkpoint store has no effect outside it:

```
rm -rf C:/hermes-server/agent_body/checkpoint
```

Hermes, MiniMax, IA-VISION, SUINI, and the GitHub-tracked canon are
unaffected. The store is a pure local seam.

## 7. Versioning

This document is version 1. Adding a *required* field is a breaking
change — bump `version` in section 2 and require readers to gate on it.
Adding an *optional* field is non-breaking if the reader ignores unknown
keys.