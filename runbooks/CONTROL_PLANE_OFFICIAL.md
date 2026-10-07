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
Ashley is not the manual dispatcher.

Hermes is the FOREMAN and owns orchestration of the authorized workflow.
ChatGPT is the owner interface, auditor, and interactive control surface.
Remote Desktop Commander is bounded PC/server access and recovery transport.
Factory provides persistent execution.
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

Certification candidate:
`46ec240489324893dd01da54ae413d74851c9cbd`

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
