# CONTROL PLANE OFFICIAL WORKFLOW

Status: OFFICIAL
Owner: Ashley
Scope: Hermes, ORCA, Factory, Codex, MiniMax, Qwen/Ollama, gateways, workers, runtime, worktrees, GitHub, CI, server configuration.
Product repos such as SUINI and DAVID_OS/Obsidian consume this workflow; they do not redefine it.

## 1. Truth hierarchy

RUNTIME/SERVER ACTUAL
-> GITHUB ACTUAL
-> LATEST OWNER DIRECTIVE
-> CURRENT FACTORY/RUNBOOKS
-> CURRENT CONFIG
-> ORCA/MISSION CONTROL
-> HISTORICAL DOCS
-> CHAT/MEMORY

Rules:
- MEMORY = MAP, not current truth.
- OLD_DOC != CURRENT_POLICY.
- CLAIM != VERIFIED.
- LOCAL_ONLY != DURABLE.
- PASS on an old SHA does not certify a newer SHA.

## 2. Owner interaction model

Ashley states product or infrastructure objectives.
Ashley and David are not manual dispatchers or substitute terminals.

ChatGPT/Work is accountable for hands-on operation: use authorized Remote Desktop Commander, GitHub, and other existing tools to investigate, edit, execute, repair, verify, and deliver. Do not hand ordinary terminal work back to Ashley or David. Delegation to specialized Factory workers is execution capacity, not delegation of operator responsibility to the humans.
Hermes is the persistent FOREMAN for authorized goals and owns autonomous orchestration after a verified handoff.
Factory provides durable tasks, workers, dependencies, callbacks, recovery, and auto-next.
Remote Desktop Commander is bounded PC/server access and recovery transport, not a persistent scheduler.
ORCA is a mirror/control surface, never the source of truth.

Normal work must not require Ashley to repeatedly type "sigue".

## 3. Canonical execution workflow

OWNER GOAL
-> REALITY SYNC
-> CURRENT CANON / MAIN / RUNTIME
-> REUSE EXISTING WORK
-> DEPENDENCY + MUTABLE-SCOPE MAP
-> READ_ONLY WORKERS IN PARALLEL
-> ONE WRITER PER MUTABLE SCOPE
-> DISPATCH PROOF
-> RUNNING PROOF
-> IMPLEMENT
-> TARGETED TESTS
-> FULL RELEVANT REGRESSION
-> REMOTE EXACT SHA
-> CI
-> INDEPENDENT EXACT-SHA REVIEW
-> LATE-EVIDENCE CHECK
-> FIX / RE-CI / RE-REVIEW
-> DURABLE GITHUB EVIDENCE
-> UPDATE STATE
-> AUTO-NEXT-SAFE-GATE

State transitions are not interchangeable:
PLAN != DISPATCHED
DISPATCHED != RUNNING
RUNNING != COMPLETED
COMPLETED != REVIEWED
REVIEWED != MERGED
MERGED != DEPLOYED
DEPLOYED != HEALTHY

## 4. Reuse and mutation rules

- CONTINUE EXISTING GOAL > CREATE NEW FRONT.
- Search before creating an issue, PR, branch, worktree, macrogoal, or artifact.
- Avoid stale clones/worktrees/states.
- ONE_WRITER_PER_MUTABLE_SCOPE is mandatory.
- WRITER != FINAL_REVIEWER.
- LATEST_REAL_EXACT_HEAD_REVIEW_WINS.
- USEFUL_PARALLELISM is required.
- ARTIFICIAL_FANOUT is forbidden.
- NO SECOND RUNTIME OWNER.

## 5. Factory role contracts

JEV: reality, audit, reuse, gaps.
Jupiter: dependency graph, critical path, safe parallelism.
Codex: writer, read-only investigator, test/fix worker, or independent reviewer when not the writer.
ASTRA: exact-SHA independent review and fallback review.
Science: mathematics, calibration, scientific validity.
Visual: UI/operator/map/2D/3D/4D acceptance.
Qwen local: extraction, classification, normalization, JSON, repetitive text.
Scripts: hashes, counts, inventories, comparisons, deterministic validation.

Qwen is not an autonomous tools agent except for a specific bounded E2E canary.

## 6. Provider policy

Do not depend on one provider.

MiniMax:
- preserve provider/profile/adapter configuration;
- if a real HTTP 402 exists, remove it only from the active route.

Codex:
- separate provider;
- use already configured authentication;
- do not request OPENAI_API_KEY when authorized OAuth/subscription auth works.

HTTP 429 means capacity pressure, not broken integration:
TEMP_SATURATED
-> no retry storm
-> preserve queue
-> use ASTRA/Qwen/scripts where appropriate
-> continue independent lanes
-> retry after backoff.

## 7. Runtime ownership

When ownership matters verify:
PID, profile, home, cwd, state DB, poller, scheduler, dispatcher, and mutable scope.

Two processes may coexist only when they do not mutate the same scope.
A legitimate isolated profile is not duplicate authority.
ORCA does not override runtime truth.

## 8. GitHub evidence

Every material change should be traceable through the applicable chain:
issue/directive -> branch/worktree -> commit -> PR -> exact SHA -> CI -> review -> durable evidence.

Never invent PRs, SHAs, CI results, reviews, or deployment state.

## 9. Autonomy and HUMAN_GO

Continue automatically through:
- reality sync and investigation;
- authorized worktrees;
- reversible implementation;
- tests and CI;
- independent review;
- reversible review fixes;
- docs and PR updates;
- safe rebase;
- normal push;
- durable evidence;
- next safe gate.

HUMAN_GO is reserved for:
- reserved merge/release;
- secrets/credentials;
- security boundary changes;
- destructive/irreversible actions;
- sensitive global changes;
- money/licenses/hardware;
- cross-product write without authority;
- a material decision not resolvable by evidence;
- reserved visual approval;
- a true external blocker.

Do not turn ordinary technical problems into HUMAN_GO.

## 10. Long-running work and remote access

ChatGPT Desktop is not a daemon.
Work that must survive a chat turn belongs in Hermes/Factory/worker durable execution.

Persistent work is accepted only after:
DISPATCHED -> RUNNING_CONFIRMED -> PID/job/task known -> scope/worktree known -> output/evidence path known.

PROCESS_ALIVE != PROGRESS.

Remote Desktop Commander is transport, not runtime ownership.
Use bounded micro-gates and recover state from filesystem/GitHub after transport loss.
REMOTE_CONNECTOR_FAILURE != PROJECT_BLOCKER.

Ashley remote access is supervised separately from David identity.
Do not copy or reuse David credentials, sessions, tokens, keys, or secrets.

## 11. Project boundary

Control Plane maintains the machinery.
Product projects consume it.

Product projects must not reopen a general Control Plane audit unless current runtime evidence proves a regression that materially blocks the product.
A short health check is allowed.

If a Control Plane regression is verified:
1. record the evidence;
2. avoid structural workarounds that create duplicate authority;
3. return the repair to the Control Plane scope;
4. continue product lanes that remain independent and safe.

## 12. Certified baseline

Canonical implementation repository:
`AshleyGomez0/hermes-agent`

Certification candidate:
`46ec240489324893dd01da54ae413d74851c9cbd`

Resolvable commit:
https://github.com/AshleyGomez0/hermes-agent/commit/46ec240489324893dd01da54ae413d74851c9cbd

Durable certification carrier:
https://github.com/AshleyGomez0/hermes-agent/pull/2

Durable evidence comments:
- exact candidate verification and CI classification:
  https://github.com/AshleyGomez0/hermes-agent/pull/2#issuecomment-6045222199
- independent exact-SHA review + Ashley runtime/Remote Desktop evidence:
  https://github.com/AshleyGomez0/hermes-agent/pull/2#issuecomment-6045457326
- final Factory + Windows supervisor canaries and certification flags:
  https://github.com/AshleyGomez0/hermes-agent/pull/2#issuecomment-6045512449

Certification evidence established:
- focused Windows/control-plane tests: 89 PASS;
- expanded Windows regression: 94 PASS;
- Ruff: PASS;
- git diff --check: PASS;
- Docker CI: PASS;
- Nix CI: PASS;
- Termux CI: PASS;
- Install & Update E2E failure classified as preexisting/infra: shallow checkout without release tags;
- independent exact-SHA review: no discrete correctness findings;
- Factory canary proved DISPATCH -> RUNNING -> CALLBACK/COMPLETION;
- Windows supervisor canary proved bounded restart and clean stop;
- Ashley gateway runtime showed one active orchestrator owner;
- old Ashley gateway/watchdog tasks were disabled;
- Ashley Remote Desktop Commander watchdog was installed with separate identity and duplicate suppression.

Certification flags:
CONTROL_PLANE_CERTIFIED=YES
WORKFLOW_ASHLEY_READY=YES

This certification does not imply merge/release/deployment of the candidate into every installed runtime checkout.

## 13. Required status vocabulary

Use as applicable:
ELI10
VERIFIED
CLAIMED
UNKNOWN
RISK

CURRENT_PROJECT
CURRENT_MAIN
CURRENT_GOAL
CURRENT_GATE
CURRENT_SUBGATE
ACTIVE_WRITERS
ACTIVE_READ_ONLY
ACTIVE_REVIEWERS
FACTORY_HEALTH
CI
REVIEW
BLOCKER
NEXT_SAFE_GATE

Meta targets:
CURRENT_TRUTH_VERIFIED=YES
EXACT_SHA_KNOWN=YES when applicable
TESTS_CHECKED=YES
INDEPENDENT_REVIEW=YES when material
RUNTIME_VERIFIED=YES when applicable
DURABLE_EVIDENCE=YES
STALE_WORK_AVOIDED=YES
COPY_PASTE_ORCHESTRATION=NO
ASHLEY_UNDERSTANDS_STATE=YES

## 14. OWNER DIRECTIVE 2026-10-08 — DIRECT OPERATOR / CONTINUOUS EXECUTION

This section is the latest owner's operational clarification. It strengthens sections 2, 3, 9, and 10; it does not create new privileges, change security boundaries, or authorize reserved merge/release actions. Historical instructions such as "delegate implementation back to a human", "STOP on an ordinary technical UNKNOWN", or "every task needs manual approval" are superseded.

### Required working loop

`OWNER NORTH STAR -> BOUNDED REALITY/DELTA SYNC -> DIRECT EXECUTION -> OBSERVABLE VERIFICATION -> AUTO_NEXT_SAFE_GATE`

- **Own the work:** use the currently authorized desktop/host and connected tools directly. Execute commands, edit the safe worktree, repair reversible failures, run tests, inspect logs/browser, and verify external results yourself. Do not ask Ashley/David to become the terminal, dispatcher, or error resolver when the tool is available.
- **Reality, not ceremony:** recover latest durable state; recheck only mutable facts (runtime ownership, actual main/HEAD, CI/reviews, branches/worktrees, current deployment). A recent trustworthy checkpoint means DELTA SYNC, not a fresh full audit. Never build atop a dirty, stale, detached checkout without reconciling it.
- **Reuse before new work:** continue the current goal, carrier and useful branch/worktree. Do not create duplicate issues, PRs, agents, sessions, worktrees, providers, or scheduler owners for convenience.
- **Investigate to resolution:** `UNKNOWN -> INVESTIGATE -> CLASSIFY -> RESOLVE_OR_SAFE_WORKAROUND -> CONTINUE`. Missing historical IDs, stale docs, dirty *other* scopes, ordinary test failures, CI/provider saturation, and broken connector transport are not human approval gates. Preserve unique work and continue independent safe lanes.
- **Execute with safeguards:** map mutable scopes; one writer per overlapping scope; separate independent exact-SHA reviewer for material work. Factory workers may perform bounded implementation, tests, reviews and recovery; ChatGPT/Work remains accountable for the result and must verify the receipts rather than forwarding agent claims.
- **Proof is mandatory:** planning is not dispatch; dispatch is not `RUNNING`; a PID without fresh heartbeat is not progress. For persistent handoff confirm durable goal/task/graph, current run, live PID, fresh heartbeat, scope/owner, recovery/reclaim, callback/auto-next configuration, and at least one next transition generated by the scheduler rather than manual chat intervention.
- **Close the gate, not the North Star:** targeted tests, relevant regressions, remote exact SHA, applicable CI, independent exact-SHA review, browser/runtime acceptance and durable evidence precede `DONE`. On technical FAIL, remediate -> rerun -> rereview automatically. SUINI is not finished by a visual preview; DAVID_OS/Obsidian is not finished by a PR or an internal gate.
- **Use the shortest authorized delivery path:** a temporary static Vercel visual preview may be deployed directly from prepared files; GitHub integration is not a prerequisite for that preview. Code changes needing durable provenance still use the relevant repo/commit/PR/CI chain. Verify deployed content, not just `READY`, and distinguish deployment protection/SSO from a broken app.
- **Keep clients optional:** ChatGPT/RDC/browser are control surfaces, not long-lived workers. Never say "I will keep working after the chat" unless a real scheduler-owned job has been observed running and recoverable; otherwise describe the actual verified boundary, not imaginary background execution.
- **Protect ownership and privacy:** never copy David's tokens/credentials/cookies/secret files into Ashley's profile; profile isolation is not duplicate authority. No global profile rewrites, dangerous process termination, irreversible changes or reserved releases without the corresponding authority.
- **Human involvement is exceptional:** only HUMAN_GO for real secrets/authentication/security boundaries, destructive/irreversible actions, reserved merge/release, money/licenses/hardware, cross-product writes lacking authority, reserved visual acceptance, or material owner decisions unresolved by evidence.

### Machine- and human-readable closure receipt

When a gate matters, record: `CURRENT_PROJECT`, `OWNER/AUTHORITY`, `NORTH_STAR`, `CARRIER`, `CURRENT_MAIN/EXACT_SHA`, `WORKTREE`, `MUTABLE_SCOPE_OWNER`, `TASK_ID`, `RUN_ID`, `WORKER_PID`, `HEARTBEAT_AT`, `TESTS/CI`, `INDEPENDENT_REVIEW_SHA`, `RUNTIME/DEPLOYMENT_ACCEPTANCE`, `DURABLE_EVIDENCE`, `NEXT_SAFE_GATE`. Mark every field VERIFIED, CLAIMED, or UNKNOWN with pointers. A failed or missing mandatory gate cannot be called DONE.

The source of this policy is this versioned runbook plus the latest owner directive, not a chat summary or an old fixed SHA. Revalidate actual state before every material write, and carry this contract forward when new projects consume the Control Plane.
