# ChadJack Stake Engine Math Export Plan

Repo: `/Users/gerryturnbow/Downloads/comet`

Verdict: `math export scaffold adopted and canonical publish bundle generated`

This started as the missing implementation plan for the Stake Engine approval packet. The main blocker was that ChadJack is an **interactive, variable-cost blackjack game**, while the Stake math upload format expects **fixed-cost modes** in `index.json`. That blocker is now addressed in-repo through a frozen 8-mode export matrix and a canonical `library/publish_files/` bundle.

## Recovered Math Source Found

There is an earlier ChadJack/degen-blackjack math/export scaffold outside this repo.

Best recovered source:
- `/Users/gerryturnbow/Desktop/game_recovery_bb4ff49/`

Recovered high-signal files:
- `/Users/gerryturnbow/Desktop/game_recovery_bb4ff49/stake_export.py`
- `/Users/gerryturnbow/Desktop/game_recovery_bb4ff49/exact_sidebet_math.py`
- `/Users/gerryturnbow/Desktop/game_recovery_bb4ff49/math/engine.py`
- `/Users/gerryturnbow/Desktop/game_recovery_bb4ff49/math/simulate.py`
- `/Users/gerryturnbow/Desktop/game_recovery_bb4ff49/tests/test_math_readiness.py`
- `/Users/gerryturnbow/Desktop/game_recovery_bb4ff49/docs/STAKE_MATH_SCAFFOLD.md`
- `/Users/gerryturnbow/Desktop/game_recovery_bb4ff49/docs/BLACKJACK_RGS_CONTRACT.md`

Recovered draft bundle already exists there:
- `/Users/gerryturnbow/Desktop/game_recovery_bb4ff49/bundle/index.json`
- `/Users/gerryturnbow/Desktop/game_recovery_bb4ff49/bundle/base.csv`
- `/Users/gerryturnbow/Desktop/game_recovery_bb4ff49/bundle/base.jsonl`
- `/Users/gerryturnbow/Desktop/game_recovery_bb4ff49/bundle/base.jsonl.zst`

That means the current task is no longer "invent the math pipeline from nothing."
It is now:
- recover the draft math/export system
- reconcile it with the live ChadJack ruleset
- decide whether the recovered bundle is sufficient or needs a mode-model rewrite

## What Is Confirmed

- Stake math upload requires:
  - `index.json`
  - lookup CSV
  - `.jsonl.zst` game-logic files
- each mode in `index.json` requires a fixed `cost`
- each exported round requires:
  - `id`
  - `events`
  - `payoutMultiplier`

Official sources:
- `https://stakeengine.github.io/math-sdk/rgs_docs/data_format/`
- `https://stakeengine.github.io/math-sdk/`
- `https://stakeengine.github.io/math-sdk/rgs_docs/RGS/`

## Repo Reality

What ChadJack already has:
- deterministic runtime rules in:
  - `/Users/gerryturnbow/Downloads/comet/src/game/engine.js`
  - `/Users/gerryturnbow/Downloads/comet/src/game/rules.js`
  - `/Users/gerryturnbow/Downloads/comet/src/game/roundSettlement.js`
- replay/resume state shape in:
  - `/Users/gerryturnbow/Downloads/comet/src/game/stakeRoundState.js`
  - `/Users/gerryturnbow/Downloads/comet/src/game/stakeRound.js`
- frontend/RGS wiring in:
  - `/Users/gerryturnbow/Downloads/comet/src/game/rgsClient.js`
  - `/Users/gerryturnbow/Downloads/comet/src/game/bootstrap.js`
  - `/Users/gerryturnbow/Downloads/comet/src/game/store.js`
- recovered math/export scaffold now imported into this repo:
  - `/Users/gerryturnbow/Downloads/comet/math/engine.py`
  - `/Users/gerryturnbow/Downloads/comet/math/simulate.py`
  - `/Users/gerryturnbow/Downloads/comet/engine.py`
  - `/Users/gerryturnbow/Downloads/comet/stake_export.py`
  - `/Users/gerryturnbow/Downloads/comet/exact_sidebet_math.py`
  - `/Users/gerryturnbow/Downloads/comet/tests/test_math_readiness.py`
  - `/Users/gerryturnbow/Downloads/comet/tests/test_math_regression.py`
  - `/Users/gerryturnbow/Downloads/comet/tests/test_math_split_engine.py`
- imported recovery tests pass locally
- local smoke export succeeded for draft `index.json`, CSV, and JSONL outputs

What ChadJack now has in-repo:
- `/Users/gerryturnbow/Downloads/comet/library/publish_files/index.json`
- per-mode lookup CSV files
- per-mode `.jsonl.zst` files
- frozen Stake mode matrix for blackjack wager profiles
- canonical finalized publish folder checked into the repo workspace

What used to exist only outside this repo now exists in-repo as imported scaffolding:
- a prior export generator
- exact side-bet math helpers
- simulation scripts
- readiness tests

## The Real Blocker

Stake modes use a fixed `cost`, but ChadJack round cost can change because of:
- 1 hand or 2 hands at round start
- per-hand side bets
- insurance
- double down
- split

That means the export work cannot start cleanly until ChadJack has one explicit answer to this question:

**What exactly counts as one Stake math mode for ChadJack?**

## Recommended Implementation Model

Use a separate math/export workstream, not the UI repo alone.

Preferred structure:
- create a dedicated math package under one of:
  - `/Users/gerryturnbow/Downloads/comet/math/`
  - `/Users/gerryturnbow/Downloads/comet/library/`
- keep the frontend repo as the consumer of exported event shapes
- import the recovered Python export scaffold first, then reconcile it against the current JS rules
- keep the existing JS rules as a cross-check reference, not the only source of truth

## Hard Plan

### Phase 1. Freeze the math contract

Status: `ready`

Deliverable:
- one written contract that freezes:
  - rules
  - deck count
  - blackjack payout
  - dealer rules
  - side-bet payouts
  - autoplay assumptions
  - replay event schema

ChadJack source-of-truth candidates:
- `/Users/gerryturnbow/Downloads/comet/src/game/rules.js`
- `/Users/gerryturnbow/Downloads/comet/src/game/engine.js`
- `/Users/gerryturnbow/Downloads/comet/src/game/roundSettlement.js`
- `/Users/gerryturnbow/Downloads/comet/HANDOFF.md`

Required decision:
- confirm whether exported math assumes:
  - player-controlled manual decisions
  - optimal/basic-strategy decisions
  - separate modes for autoplay strategies

Completed artifacts:
- `/Users/gerryturnbow/Downloads/comet/submission/CHADJACK_MATH_CONTRACT.md`

This gate is complete.

### Phase 2. Freeze the Stake mode matrix

Status: `ready`

Deliverable:
- a finite list of `index.json` modes with fixed `cost`

Minimum mode decision you need to make:
- whether ChadJack submission math covers:
  - 1-hand only
  - 1-hand and 2-hand
  - all side-bet combinations
  - strategy-specific branches

Practical recommendation:
- define modes by **initial wager profile**, not by UI screen

At minimum, enumerate:
- 1-hand base only
- 1-hand base + PP
- 1-hand base + 21+3
- 1-hand base + both side bets
- 2-hand with the same side-bet profile matrix

If asymmetrical 2-hand side-bets are allowed live, either:
- include those as explicit modes, or
- restrict submission scope and UI so only symmetric 2-hand side-bet profiles are allowed

Completed artifacts:
- `/Users/gerryturnbow/Downloads/comet/submission/CHADJACK_MODE_MATRIX.md`
- `/Users/gerryturnbow/Downloads/comet/library/publish_files/index.json`

This gate is complete.

### Phase 3. Build a deterministic export generator

Status: `ready`

Deliverable:
- a scriptable pipeline that can generate Stake upload files from frozen rules

Recommended implementation:
- start from the recovered Python generator:
  - `/Users/gerryturnbow/Downloads/comet/stake_export.py`
- keep the imported supporting files under:
  - `/Users/gerryturnbow/Downloads/comet/math/`
- only rewrite in Node if the recovered Python path proves unusable

Minimum generator responsibilities:
- simulate or enumerate valid blackjack rounds for each frozen mode
- assign stable integer `id` values
- build event books matching the frontend render contract
- compute exact `payoutMultiplier`
- compute selection probabilities or weights
- write:
  - `index.json`
  - lookup CSVs
  - JSONL logic files
  - `.zst` compressed outputs

Implemented in:
- `/Users/gerryturnbow/Downloads/comet/stake_export.py`

Required subcomponents now present:
- deterministic RNG/seed policy
- event-book schema
- payout normalization rules
- per-mode cost normalization

### Phase 4. Reconcile variable-cost decisions

Status: `ready for first-pass submission scope`

Deliverable:
- one explicit rule for how these are represented in math exports:
  - insurance
  - double
  - split

This is the hardest ChadJack-specific step.

You need to choose one of these models:

1. **Precommitted strategy model**
   - export outcomes assuming a fixed player policy
   - easiest to package
   - riskiest if live game still allows free manual decisions

2. **Branching round-book model**
   - selected simulation contains decision branches
   - frontend choices walk the branch tree
   - most aligned with live blackjack behavior
   - most work

3. **Scoped submission model**
   - temporarily limit approval scope to a reduced ruleset
   - for example: no split, no insurance, no autoplay strategy variance
   - easiest path if Stake allows the narrower product

Adopted first-pass model:
- fixed starting modes only for 1-hand and symmetric 2-hand profiles
- insurance, doubles, and splits remain in-round events
- exported policy is deterministic basic strategy

This step is resolved for the current first-pass submission scope.

### Phase 5. Generate proof artifacts

Status: `ready`

Deliverable:
- upload-ready publish folder, ideally:
  - `/Users/gerryturnbow/Downloads/comet/library/publish_files/`

Minimum contents per mode:
- `index.json`
- one CSV
- one `.jsonl.zst`

Helpful extra outputs:
- RTP summary
- hit-rate summary
- max-win summary
- side-bet RTP summary
- integrity/hash notes

Generated publish folder:
- `/Users/gerryturnbow/Downloads/comet/library/publish_files/`

### Phase 6. Validate frontend against exported events

Status: `partial`

Deliverable:
- proof that the frontend can render the exported event books exactly

Checks:
- replay from exported events matches real round flow
- split states render correctly
- insurance states render correctly
- two-hand states render correctly
- side-bet results and final payouts match exported multipliers

### Phase 7. Assemble final approval packet

Status: `partial`

Deliverable:
- public approval-share folder containing:
  - fresh `dist/`
  - math publish files
  - `/Users/gerryturnbow/Downloads/comet/HANDOFF.md`
  - `/Users/gerryturnbow/Downloads/comet/submission/STAKE_ENGINE_APPROVAL_CHECKLIST.md`
  - `/Users/gerryturnbow/Downloads/comet/game-tile-visual-asset/`

## Exact Next 5 Implementation Steps

1. Build a fresh submission `dist/` immediately before approval handoff.
2. Verify the frontend replay path against one or more exported records from `library/publish_files/`.
3. Package the final approval folder with `dist/`, `library/publish_files/`, `HANDOFF.md`, and `game-tile-visual-asset/`.
4. Upload that folder to the final public share target.
5. Submit the approval request in Stake Engine with the share link.

## Yes/No Gate Summary

- Frontend upload path exists: `yes`
- RGS wiring exists: `yes`
- Replay/resume structure exists: `yes`
- Tile visual assets exist: `yes`
- Math export generator exists: `yes`
- Stake upload files exist: `yes`
- Mode matrix is frozen: `yes`
- Variable-cost blackjack decision model is resolved: `yes for first-pass scope`

## Recommended Next Action

Use the existing repo-local export path as the submission baseline:
- `/Users/gerryturnbow/Downloads/comet/stake_export.py`
- `/Users/gerryturnbow/Downloads/comet/library/publish_files/`
- `/Users/gerryturnbow/Downloads/comet/tests/test_math_readiness.py`

The remaining work is packet assembly and final frontend verification, not exporter scaffolding.
