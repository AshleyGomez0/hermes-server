# AGENT-BODY local runtime store

This directory is a LOCAL runtime store under `C:/hermes-server/agent_body/`.
It lives outside any GitHub-tracked repo and is not part of any product
codebase.

Contents:

- `manifest/`   (MVP-1; sibling task)
- `checkpoint/` (MVP-2; this branch)
- `registry/`   (MVP-3)
- `resolver/`   (MVP-4)
- `audit/`      (MVP-5; JSONL hash-chained)
- `lease/`      (MVP-6; SQLite stdlib)

Reversibility: deletion of any sibling directory has no effect on Hermes,
MiniMax, IA-VISION, SUINI, or the GitHub-tracked canon. A full reversal is
removing the `agent_body` directory tree.

## Official Control Plane workflow

The authoritative operating policy for Ashley's Control Plane is versioned at:

- `runbooks/CONTROL_PLANE_OFFICIAL.md`
- `runbooks/PROJECT_CONSUMER_CONTRACT.md`

Runtime artifacts under `agent_body/` do not override those policies.
