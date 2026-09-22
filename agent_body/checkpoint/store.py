"""Checkpoint store for the AGENT-BODY MVP-2 piece.

Stdlib only. Public API:

    validate_task_id(task_id) -> None        # raises ValueError
    validate_payload(payload)  -> None        # raises ValueError
    next_seq(store_root, task_id) -> int
    atomic_write(store_root, payload) -> dict # returns written payload (with assigned seq/utc/id)
    read(store_root, task_id, seq=None) -> dict | None
    list_checkpoints(store_root, task_id) -> [dict, ...]   # newest first
    compare_head(checkpoint, current_heads) -> dict         # STALE/FRESH

Design contract (see SCHEMA.md):

- One JSON file per checkpoint, named ckpt-<task>-<seq>-<utc>.json.
- INDEX.json lists the latest valid checkpoint per task.
- Writes are atomic (tmp + os.replace + fsync).
- A crash mid-write MUST NOT produce a partial checkpoint file or a
  corrupt INDEX.json. The previous valid state must remain readable.
- Retention: keep last 10 per task by descending seq.
- Reversibility: this module never deletes anything outside its root.

Forbidden fields are enforced at write time; nothing reasoning-shaped
or chat-shaped may enter this store.
"""

from __future__ import annotations

import datetime as _dt
import hashlib
import json
import os
import re
import uuid
from pathlib import Path
from typing import Any


# --------------------------------------------------------------------------- #
# Constants
# --------------------------------------------------------------------------- #

SCHEMA_NAME = "AGENT_BODY_CHECKPOINT"
SCHEMA_VERSION = 1
INDEX_SCHEMA_NAME = "AGENT_BODY_CHECKPOINT_INDEX"
INDEX_VERSION = 1
RETENTION_PER_TASK = 10

# Lifecycle phases a checkpoint may record. Tight allowlist: better to fail
# closed than to record an ungrounded phase.
LIFECYCLE_PHASES = frozenset(
    {"ENTER", "OBSERVE", "PLAN", "ACT", "VERIFY", "HANDOFF", "EXIT"}
)

# Fields that MUST NEVER appear in a checkpoint payload. Chain-of-thought
# guard. If you need to add a new category here, also update SCHEMA.md 2.3.
FORBIDDEN_FIELDS = frozenset(
    {
        "reasoning",
        "thoughts",
        "chain_of_thought",
        "cot",
        "messages",
        "chat",
        "conversation",
        "transcript",
        "dialogue",
        "tool_calls",
        "tool_results",
        "function_calls",
        "notes",
        "private_notes",
        "scratch",
        "memo",
        "diary",
        "embedding",
        "vector",
        "summary",
        "paraphrase",
        "system_prompt",
        "developer_prompt",
        "instructions",
    }
)

# Required top-level fields. Order matters for stable diffs but json.dump
# uses dict order so we keep a canonical order in atomic_write.
# Required top-level fields the CALLER must provide. `written_at_utc`,
# `seq`, and `checkpoint_id` are server-assigned by atomic_write and
# therefore not part of the caller contract — that is intentional so the
# caller cannot pass a forged timestamp.
REQUIRED_FIELDS = (
    "schema",
    "version",
    "task_id",
    "lifecycle_phase",
    "world_state_hash",
    "task_state_hash",
    "knowledge_pointer",
    "evidence_pointer",
    "lease_token",
    "head_observed",
    "writer_profile",
)

REQUIRED_HEAD_FIELDS = (
    "target_repo_branch",
    "mission_control_kg",
    "ia_vision_world_state",
)

_TASK_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$")
_SEQ_RE = re.compile(r"^\d{6}$")


# --------------------------------------------------------------------------- #
# Validation
# --------------------------------------------------------------------------- #


def validate_task_id(task_id: Any) -> None:
    """Reject anything that could escape the store root via filenames."""
    if not isinstance(task_id, str):
        raise ValueError(f"task_id must be str, got {type(task_id).__name__}")
    if not _TASK_ID_RE.match(task_id):
        raise ValueError(
            f"task_id {task_id!r} is not safe: must match "
            f"{_TASK_ID_RE.pattern!r} (alnum, dash, underscore, 1-128 chars)"
        )


def validate_payload(payload: Any) -> None:
    """Validate the payload before writing. Raises ValueError on failure.

    Guards:
      - top-level type must be dict
      - schema name + version must match
      - all required fields present
      - lifecycle_phase must be in allowlist
      - no forbidden (chain-of-thought / chat / reasoning) field
      - head_observed shape (three required SHAs, all non-null strings)
      - hashes are sha256:<hex>  form
      - knowledge_pointer / evidence_pointer are string URIs
    """
    if not isinstance(payload, dict):
        raise ValueError(f"payload must be dict, got {type(payload).__name__}")

    # Schema gate. Reader version gate.
    if payload.get("schema") != SCHEMA_NAME:
        raise ValueError(
            f"payload.schema must be {SCHEMA_NAME!r}, got {payload.get('schema')!r}"
        )
    if payload.get("version") != SCHEMA_VERSION:
        raise ValueError(
            f"payload.version must be {SCHEMA_VERSION}, got {payload.get('version')!r}"
        )

    # Chain-of-thought guard. Reject before doing anything else.
    forbidden_hit = FORBIDDEN_FIELDS.intersection(payload.keys())
    if forbidden_hit:
        raise ValueError(
            "forbidden field(s) in payload: "
            + ", ".join(sorted(forbidden_hit))
            + " (see SCHEMA.md 2.3 — checkpoint store is operational only)"
        )

    # Required fields present.
    missing = [f for f in REQUIRED_FIELDS if f not in payload]
    if missing:
        raise ValueError(f"payload missing required field(s): {missing}")

    # task_id format.
    validate_task_id(payload["task_id"])

    # lifecycle_phase allowlist.
    if payload["lifecycle_phase"] not in LIFECYCLE_PHASES:
        raise ValueError(
            f"lifecycle_phase {payload['lifecycle_phase']!r} not in "
            f"{sorted(LIFECYCLE_PHASES)}"
        )

    # Hashes must look like sha256:<hex64>.
    _validate_sha256_pointer("world_state_hash", payload["world_state_hash"])
    _validate_sha256_pointer("task_state_hash", payload["task_state_hash"])

    # Pointers must be string URIs (we don't parse, but require non-empty).
    if not isinstance(payload["knowledge_pointer"], str) or not payload["knowledge_pointer"]:
        raise ValueError("knowledge_pointer must be a non-empty string URI")
    if not isinstance(payload["evidence_pointer"], str) or not payload["evidence_pointer"]:
        raise ValueError("evidence_pointer must be a non-empty string URI")

    # lease_token: string or None.
    lt = payload["lease_token"]
    if lt is not None and not isinstance(lt, str):
        raise ValueError("lease_token must be str or null")

    # writer_profile non-empty str.
    if not isinstance(payload["writer_profile"], str) or not payload["writer_profile"]:
        raise ValueError("writer_profile must be a non-empty string")

    # head_observed shape.
    head = payload["head_observed"]
    if not isinstance(head, dict):
        raise ValueError("head_observed must be a dict")
    for f in REQUIRED_HEAD_FIELDS:
        if f not in head:
            raise ValueError(f"head_observed missing required field {f!r}")
        v = head[f]
        if not isinstance(v, str) or len(v) < 7:
            raise ValueError(f"head_observed.{f} must be a non-empty string SHA")
    # Extra keys in head_observed are allowed (forward compat) but we warn
    # gently by ignoring them; no error.
    # NOTE: written_at_utc, seq, checkpoint_id are server-assigned by
    # atomic_write AFTER validation succeeds, so they are not validated
    # here — the caller is forbidden from supplying them.


def _validate_sha256_pointer(name: str, value: Any) -> None:
    if not isinstance(value, str):
        raise ValueError(f"{name} must be a string, got {type(value).__name__}")
    if not value.startswith("sha256:"):
        raise ValueError(f"{name} must start with 'sha256:' (got {value!r})")
    hexpart = value[len("sha256:"):]
    if len(hexpart) != 64 or not all(c in "0123456789abcdef" for c in hexpart):
        raise ValueError(f"{name} must be sha256:<64 hex chars> (got {value!r})")


# --------------------------------------------------------------------------- #
# Filename helpers
# --------------------------------------------------------------------------- #


def _utc_compact(dt: _dt.datetime) -> str:
    """Return YYYYMMDDTHHMMSSZ — used in filenames (no colons, FS-safe)."""
    return dt.strftime("%Y%m%dT%H%M%SZ")


def _now_utc() -> _dt.datetime:
    return _dt.datetime.now(_dt.timezone.utc).replace(microsecond=0)


def _seq_str(seq: int) -> str:
    if seq < 0 or seq >= 10**6:
        raise ValueError(f"seq {seq} out of range [0, 10^6)")
    return f"{seq:06d}"


def _filename(task_id: str, seq: int, dt: _dt.datetime) -> str:
    return f"ckpt-{task_id}-{_seq_str(seq)}-{_utc_compact(dt)}.json"


def _parse_filename(name: str) -> tuple[str, int, str] | None:
    """Parse ckpt-<task>-<seq>-<utc>.json. Returns (task, seq, utc) or None.

    The literal prefix is ``ckpt-``. The task id itself may contain
    dashes (e.g. ``t_771d8615``), so we strip the prefix first and
    then split off the trailing two dash-delimited segments (seq and
    utc). Anything else is part of the task id.
    """
    if not name.endswith(".json"):
        return None
    base = name[:-5]
    if not base.startswith("ckpt-"):
        return None
    rest = base[len("ckpt-"):]
    parts = rest.split("-")
    if len(parts) < 3:
        return None
    seq_part = parts[-2]
    utc_part = parts[-1]
    if not _SEQ_RE.match(seq_part) or not (utc_part.endswith("Z") and "T" in utc_part):
        return None
    task_id = "-".join(parts[:-2])  # task_id may itself contain dashes
    return task_id, int(seq_part), utc_part


# --------------------------------------------------------------------------- #
# Index management
# --------------------------------------------------------------------------- #


def _read_index(store_root: Path) -> dict:
    """Read INDEX.json. Return empty structure if missing or malformed."""
    idx_path = store_root / "INDEX.json"
    if not idx_path.exists():
        return {
            "schema": INDEX_SCHEMA_NAME,
            "version": INDEX_VERSION,
            "updated_at_utc": _now_utc().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "tasks": {},
        }
    try:
        with idx_path.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
    except (json.JSONDecodeError, OSError):
        # Corrupt index — treat as empty rather than crashing the writer.
        # The next successful write replaces it.
        return {
            "schema": INDEX_SCHEMA_NAME,
            "version": INDEX_VERSION,
            "updated_at_utc": _now_utc().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "tasks": {},
        }
    if not isinstance(data, dict):
        return {
            "schema": INDEX_SCHEMA_NAME,
            "version": INDEX_VERSION,
            "updated_at_utc": _now_utc().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "tasks": {},
        }
    data.setdefault("tasks", {})
    return data


def _write_index_atomic(store_root: Path, index: dict) -> None:
    """Atomically replace INDEX.json. Crash before replace leaves prior intact."""
    tmp = store_root / "INDEX.json.tmp"
    final = store_root / "INDEX.json"
    payload = json.dumps(index, indent=2, sort_keys=True, ensure_ascii=False)
    with open(tmp, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(payload)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, final)


# --------------------------------------------------------------------------- #
# Discovery
# --------------------------------------------------------------------------- #


def _list_task_files(store_root: Path, task_id: str) -> list[tuple[int, str, str]]:
    """Return [(seq_int, utc_str, filename), ...] for one task. Unsorted."""
    out: list[tuple[int, str, str]] = []
    if not store_root.exists():
        return out
    for entry in store_root.iterdir():
        if not entry.is_file():
            continue
        parsed = _parse_filename(entry.name)
        if parsed is None:
            continue
        tid, seq, utc = parsed
        if tid == task_id:
            out.append((seq, utc, entry.name))
    return out


def next_seq(store_root: str | os.PathLike, task_id: str) -> int:
    """Return the next sequence number for this task (0 if none)."""
    validate_task_id(task_id)
    root = Path(store_root)
    existing = _list_task_files(root, task_id)
    if not existing:
        return 0
    return max(s for s, _, _ in existing) + 1


# --------------------------------------------------------------------------- #
# Atomic write
# --------------------------------------------------------------------------- #


def _fsync_dir(directory: Path) -> None:
    """Best-effort fsync of the directory entry. POSIX-only; harmless no-op on Windows."""
    try:
        dir_fd = os.open(str(directory), os.O_RDONLY)
        try:
            os.fsync(dir_fd)
        finally:
            os.close(dir_fd)
    except OSError:
        # Windows / FAT / network shares may not support fsync on dir.
        pass


def atomic_write(store_root: str | os.PathLike, payload: dict) -> dict:
    """Validate, assign seq/utc/id, write atomically, update index, rotate.

    Returns the final written payload (with seq, written_at_utc,
    checkpoint_id filled in). On error, raises ValueError; nothing is
    left half-written because we use os.replace.
    """
    validate_payload(payload)
    validate_task_id(payload["task_id"])

    root = Path(store_root)
    root.mkdir(parents=True, exist_ok=True)

    task_id = payload["task_id"]
    seq = next_seq(root, task_id)
    now = _now_utc()
    utc_compact = _utc_compact(now)
    iso_utc = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    ckpt_id = f"ckpt-{task_id}-{_seq_str(seq)}-{utc_compact}"

    # Build the final payload — do not mutate the caller's dict.
    final = dict(payload)
    final["seq"] = seq
    final["written_at_utc"] = iso_utc
    final["checkpoint_id"] = ckpt_id

    fname = f"{ckpt_id}.json"
    final_path = root / fname
    tmp_path = root / f"{fname}.tmp"

    body = json.dumps(final, indent=2, sort_keys=True, ensure_ascii=False)

    # 1. Write payload atomically.
    with open(tmp_path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(body)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp_path, final_path)

    # 2. Update index atomically.
    index = _read_index(root)
    index["updated_at_utc"] = iso_utc
    index.setdefault("tasks", {})
    index["tasks"][task_id] = {
        "seq": seq,
        "file": fname,
        "written_at_utc": iso_utc,
    }
    _write_index_atomic(root, index)

    # 3. Retention — keep last 10 by seq desc.
    _rotate(root, task_id, keep=RETENTION_PER_TASK)

    # 4. Best-effort dir fsync (POSIX only).
    _fsync_dir(root)

    return final


def _rotate(store_root: Path, task_id: str, keep: int) -> None:
    existing = _list_task_files(store_root, task_id)
    if len(existing) <= keep:
        return
    existing.sort(key=lambda t: t[0], reverse=True)  # by seq desc
    for _seq, _utc, name in existing[keep:]:
        try:
            (store_root / name).unlink()
        except FileNotFoundError:
            pass
    # After rotation, refresh INDEX for this task if the newest removed
    # was the one INDEX pointed at.
    remaining = sorted(_list_task_files(store_root, task_id), key=lambda t: t[0], reverse=True)
    index = _read_index(store_root)
    if not remaining:
        index.get("tasks", {}).pop(task_id, None)
    else:
        s, u, name = remaining[0]
        # Parse iso from utc_compact.
        iso = f"{u[:4]}-{u[4:6]}-{u[6:8]}T{u[9:11]}:{u[11:13]}:{u[13:15]}Z"
        index.setdefault("tasks", {})[task_id] = {
            "seq": s,
            "file": name,
            "written_at_utc": iso,
        }
    index["updated_at_utc"] = _now_utc().strftime("%Y-%m-%dT%H:%M:%SZ")
    _write_index_atomic(store_root, index)


# --------------------------------------------------------------------------- #
# Read / list
# --------------------------------------------------------------------------- #


def _read_one(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def read(store_root: str | os.PathLike, task_id: str, seq: int | None = None) -> dict | None:
    """Read a checkpoint. If seq is None, return the latest for this task.

    Returns None if no checkpoint exists for this task.
    Raises ValueError on schema mismatch (so callers can decide what to do).
    """
    validate_task_id(task_id)
    root = Path(store_root)
    existing = _list_task_files(root, task_id)
    if not existing:
        return None
    if seq is None:
        existing.sort(key=lambda t: t[0], reverse=True)
        chosen = existing[0]
    else:
        match = [t for t in existing if t[0] == seq]
        if not match:
            return None
        chosen = match[0]
    _seq, _utc, name = chosen
    return _read_one(root / name)


def list_checkpoints(
    store_root: str | os.PathLike, task_id: str
) -> list[dict]:
    """Return all checkpoints for a task, newest first.

    Each entry is the full payload (lightweight; checkpoints are small by design).
    """
    validate_task_id(task_id)
    root = Path(store_root)
    existing = _list_task_files(root, task_id)
    existing.sort(key=lambda t: t[0], reverse=True)
    out = []
    for _seq, _utc, name in existing:
        out.append(_read_one(root / name))
    return out


# --------------------------------------------------------------------------- #
# Stale / fresh
# --------------------------------------------------------------------------- #


def compare_head(checkpoint: dict, current_heads: dict) -> dict:
    """Compare a checkpoint's head_observed against current heads.

    Returns::

        {"status": "FRESH", "reason": None,            "deltas": []}
        {"status": "STALE", "reason": "<n> head(s) moved", "deltas": [{...}]}

    A reader MUST NOT resume on STALE; reconciliation (MVP-4) is required first.
    """
    if not isinstance(checkpoint, dict):
        raise ValueError("checkpoint must be dict")
    head = checkpoint.get("head_observed")
    if not isinstance(head, dict):
        raise ValueError("checkpoint.head_observed missing or not a dict")
    if not isinstance(current_heads, dict):
        raise ValueError("current_heads must be dict")

    deltas: list[dict] = []
    for f in REQUIRED_HEAD_FIELDS:
        observed = head.get(f)
        current = current_heads.get(f)
        if current is None:
            # Current world doesn't track this head — we can't claim
            # freshness. Be conservative.
            deltas.append({"field": f, "observed": observed, "current": None})
            continue
        if observed != current:
            deltas.append({"field": f, "observed": observed, "current": current})

    if not deltas:
        return {"status": "FRESH", "reason": None, "deltas": []}
    return {
        "status": "STALE",
        "reason": f"{len(deltas)} head(s) moved",
        "deltas": deltas,
    }


# --------------------------------------------------------------------------- #
# Optional: hashing helpers (for callers building the payload)
# --------------------------------------------------------------------------- #


def sha256_of_bytes(data: bytes) -> str:
    """Return 'sha256:<hex>' for arbitrary bytes. Convenience for callers
    that need to fill world_state_hash / task_state_hash."""
    return "sha256:" + hashlib.sha256(data).hexdigest()


def checkpoint_uuid() -> str:
    """Generate a fresh opaque id. Exposed so callers can mint
    lease_tokens deterministically per-session if they want."""
    return uuid.uuid4().hex


__all__ = [
    "SCHEMA_NAME",
    "SCHEMA_VERSION",
    "INDEX_SCHEMA_NAME",
    "INDEX_VERSION",
    "RETENTION_PER_TASK",
    "LIFECYCLE_PHASES",
    "FORBIDDEN_FIELDS",
    "validate_task_id",
    "validate_payload",
    "next_seq",
    "atomic_write",
    "read",
    "list_checkpoints",
    "compare_head",
    "sha256_of_bytes",
    "checkpoint_uuid",
]