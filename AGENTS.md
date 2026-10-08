# CONTROL PLANE - Agent entrypoint

Owner: Ashley. Scope: Hermes/Factory/ORCA/gateways/workers/CI/server runtime, not product implementation. Governing versioned policy: [runbooks/CONTROL_PLANE_OFFICIAL.md](runbooks/CONTROL_PLANE_OFFICIAL.md). Product-specific docs do not supersede it. Read the latest owner directive and verify current runtime + GitHub before a material write. Historical SHAs and certification reports are evidence, not current health.

## Operator contract

- Ashley states the North Star. ChatGPT/Work uses authorized Remote Desktop Commander, GitHub, and other connected tools to **do** the work; it must not turn Ashley or David into terminals, dispatchers, or manual fixers.
- Hermes is the persistent foreman; Factory is the durable goal/task/run/worker/heartbeat/callback/reclaim/auto-next system. Agent delegation is allowed for useful scoped capacity, not to transfer accountability to humans. ORCA is a control surface.
- Run `REALITY/DELTA_SYNC -> REUSE -> EXECUTE -> VERIFY -> AUTO_NEXT_SAFE_GATE`. Reconcile actual `origin/main`, worktree/HEAD, and runtime before making changes. Do not repeat a full audit if fresh trustworthy evidence needs only a delta.
- Investigate technical unknowns, classification and safe repair; do not stop on a dirty unrelated worktree, old task ID, flaky test, provider 429, or connector outage. Continue unaffected safe lanes. Protect unique uncommitted work.
- One writer per overlapping mutable scope; independent exact-SHA reviewer for material work. Useful read-only parallelism, no artificial fanout or duplicate runtime owner.
- Record exact tests/CI/review, real runtime/deployment acceptance, durable GitHub receipts. `READY != RUNNING`, `RUNNING != DONE`, `DEPLOYED != HEALTHY`. Do not declare a North Star complete because an intermediate PR/audit/preview gate passed.
- For persistence beyond chat, *prove* a scheduler-owned task, run, live PID, fresh heartbeat, recovery/reclaim and automatic next transition. ChatGPT/RDC are not a daemon; never imply otherwise.
- Temporary Vercel previews may deploy directly from files when supported; do not invent a GitHub integration prerequisite. Verify the browser/rendered site and protection state before claiming acceptance.
- Only HUMAN_GO for secrets/auth/security, destructive irreversible changes, reserved merges/releases, money/licenses/hardware, sensitive global changes, unapproved cross-product writes, reserved visual approval or an unresolved material owner decision.
- Keep David's identity/secrets separate. Do not read or copy private credentials to satisfy this policy.

Do not freeze a provider, PID, branch, SHA, PR, runtime path, or deployment ID in this entrypoint. For the full contract, read `runbooks/CONTROL_PLANE_OFFICIAL.md`, especially section 14.
