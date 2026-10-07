# PROJECT CONSUMER CONTRACT

This file defines how product projects use the certified Control Plane.

## Projects currently consuming the workflow

- SUINI
- DAVID_OS / Obsidian / panorama-mission-control

## Startup contract

Every product conversation begins with a Reality Sync of its own canon:
- canonical repository;
- owner/authority;
- main/current HEAD;
- active goal/carrier;
- open PRs;
- branches/worktrees;
- CI/reviews;
- runtime state when relevant;
- latest durable directive;
- blockers and evidence.

Historical project prompts are maps, not frozen truth.

## Execution contract

Product projects use the official Control Plane workflow from:
`runbooks/CONTROL_PLANE_OFFICIAL.md`

They do not copy or redefine Control Plane internals.

Ashley gives an objective.
Hermes/Factory perform orchestration.
The project continues through safe gates automatically until:
- DONE with verifiable evidence;
- a real HUMAN_GO boundary;
- a true external blocker;
- no remaining safe work.

## Separation of concerns

SUINI product work remains in SUINI.
DAVID_OS/Obsidian product/estate work remains in panorama-mission-control and its authorized estate scopes.
Control Plane fixes remain in hermes-server / hermes-agent control-plane scopes.

Cross-product writes require explicit authority.

## Regression handling

If a product detects a Control Plane problem:
1. verify the failure;
2. capture minimal reproducible evidence;
3. do not create a competing runtime owner or ad-hoc orchestration layer;
4. return the infrastructure repair to Control Plane;
5. continue unaffected product lanes.

## Official behavior

The desired operator experience is objective-driven, not dispatcher-driven.

Correct:
"Ashley gives the goal; the system recovers state, dispatches, verifies, reviews, persists evidence, and advances."

Incorrect:
"Ashley manually assigns every worker or repeatedly types 'sigue' to make progress."
