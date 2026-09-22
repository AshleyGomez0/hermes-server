# Checkpoint Store — README

Operational-only resumability for fresh Hermes/MiniMax sessions.

This directory holds small JSON snapshots ("checkpoints") that let a
fresh session pick up a task where a prior session left off. **It
stores pointers, hashes, and metadata — never reasoning, never chat,
never tool-call transcripts.**

See [`SCHEMA.md`](./SCHEMA.md) for the full data shape.

---

## What it is

A bounded local seam between sessions:

```
session A            checkpoint store             session B
   |                       |                          |
   | atomic_write(payload) |                          |
   |---------------------->|                          |
   |                       |                          |
   | ... A dies / finishes |                          |
   |                       |                          |
   |                       |    read(task_id)         |
   |                       |<-------------------------|
   |                       |                          |
   |                       |--- payload ------------->|
   |                       |                          |
   |                       |   compare_head(curr)     |
   |                       |<-------------------------|
   |                       |                          |
   |                       |--- STALE / FRESH ------->|
   |                       |                          |
```

If `STALE`, session B does **not** resume — it calls the resolver
(MVP-4) to reconcile first. If `FRESH`, it resumes.

---

## What goes IN a checkpoint

Required fields (full list in SCHEMA.md):

- `task_id`
- `lifecycle_phase` (ENTER, OBSERVE, PLAN, ACT, VERIFY, HANDOFF, EXIT)
- `world_state_hash` — `sha256:<hex>` of the external world snapshot
- `task_state_hash` — `sha256:<hex>` of the task-internal state
- `knowledge_pointer` — URI to a knowledge graph node (not the node's content)
- `evidence_pointer` — URI to an audit row (not its body)
- `lease_token` — opaque id if a writer lease is currently held, else `null`
- `head_observed` — three SHAs (target repo, MC KG, IA-VISION world)
- `written_at_utc` — ISO-8601 UTC
- `writer_profile` — e.g. `jupiter`

## What NEVER goes in

The store rejects payloads with these fields at write time
(`store.validate_payload()` raises `ValueError`):

- **Reasoning / chain-of-thought**: `reasoning`, `thoughts`,
  `chain_of_thought`, `cot`
- **Chat / conversation**: `messages`, `chat`, `conversation`,
  `transcript`, `dialogue`
- **Tool plumbing**: `tool_calls`, `tool_results`, `function_calls`
- **Private notes**: `notes`, `private_notes`, `scratch`, `memo`,
  `diary`
- **Embeddings / vectors**: `embedding`, `vector`
- **Summaries / paraphrases**: `summary`, `paraphrase`
- **Prompts**: `system_prompt`, `developer_prompt`, `instructions`

If you need to record *why* a decision was made, write a one-line
`evidence_pointer` to the audit row and let the audit row carry the
rationale. The checkpoint itself stays operational.

---

## Usage

```python
from checkpoint import store

# 1. Build a payload
payload = {
    "schema":              "AGENT_BODY_CHECKPOINT",
    "version":             1,
    "task_id":             "t_771d8615",
    "lifecycle_phase":     "HANDOFF",
    "world_state_hash":    store.sha256_of_bytes(b"<world-snapshot>"),
    "task_state_hash":     store.sha256_of_bytes(b"<task-state>"),
    "knowledge_pointer":   "mission_control://kg/v1/entity/e_abc123",
    "evidence_pointer":    "audit://agent_body/2026-09-21/row-42",
    "lease_token":         None,
    "head_observed": {
        "target_repo_branch":     "deadbeef" * 5,
        "mission_control_kg":     "cafebabe" * 5,
        "ia_vision_world_state":  "12345678" * 5,
    },
    "writer_profile":      "jupiter",
}

written = store.atomic_write("C:/hermes-server/agent_body/checkpoint", payload)
print(written["checkpoint_id"])   # ckpt-t_771d8615-000000-...Z

# 2. In a fresh session, read the latest
ck = store.read("C:/hermes-server/agent_body/checkpoint", "t_771d8615")

# 3. Compare current world heads against the checkpoint
verdict = store.compare_head(ck, current_heads={
    "target_repo_branch":     "deadbeef" * 5,
    "mission_control_kg":     "cafebabe" * 5,
    "ia_vision_world_state":  "12345678" * 5,
})
assert verdict["status"] == "FRESH"
```

---

## Atomicity

Every write is:

1. Write `ckpt-<task>-<seq>-<utc>.json.tmp`, fsync.
2. `os.replace` to final name.
3. Write `INDEX.json.tmp`, fsync.
4. `os.replace` to final name.
5. Rotate down to the last 10 per task.

A crash at any point leaves the previous valid file in place. There is
no recovery procedure. The next write just creates a new file.

## Retention

- Keep last **10** checkpoints per task by descending `seq`.
- Older files are deleted at the end of each successful write.
- The store never deletes checkpoints from other tasks.

## Reversibility

Deleting the store has zero impact on anything else:

```
rm -rf C:/hermes-server/agent_body/checkpoint
```

Hermes, MiniMax, IA-VISION, SUINI, and the GitHub-tracked canon are
unaffected. The store is a pure local seam.

---

## File layout

```
checkpoint/
├── README.md         # this file
├── SCHEMA.md         # full schema
├── store.py          # stdlib-only implementation
├── tests/
│   └── test_store.py # pytest, stdlib only
├── INDEX.json        # latest valid checkpoint per task
└── ckpt-<task>-<seq>-<utc>.json
```

---

## Out of scope

This MVP does NOT include:

- Conversation logs, chat archives, embeddings, vector DBs
- Hermes runtime modifications
- IA-VISION code, SUINI code
- Push to `main` of any product repo

If you need those, they live elsewhere. Don't smuggle them in here.