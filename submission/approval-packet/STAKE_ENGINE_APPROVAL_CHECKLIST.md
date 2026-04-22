# ChadJack Stake Engine Approval Checklist

Repo: `/Users/gerryturnbow/Downloads/comet`

Verdict: `mostly ready`

The frontend integration, approval art packet, and math upload bundle are now in place. The remaining submission work is operational: generate a fresh `dist/` build at handoff time and place the final packet in a public share folder for the Stake approval request.

## Exact Submission Packet

### 1. Frontend upload files

Status: `ready, but needs fresh build at submission time`

What Stake needs:
- a static frontend build to upload

What ChadJack has:
- Vite static build setup in `vite.config.js`
- `base: "./"` is already set
- main app/frontend exists and builds successfully

What to submit:
- fresh contents of `dist/` generated immediately before submission

Repo evidence:
- `/Users/gerryturnbow/Downloads/comet/vite.config.js`
- `/Users/gerryturnbow/Downloads/comet/src/main.js`
- `/Users/gerryturnbow/Downloads/comet/src/App.svelte`

### 2. RGS communication

Status: `ready`

What Stake expects:
- launch params from the host
- authenticate first
- play, event, and end-round support

What ChadJack has:
- query parsing for `sessionID`, `rgs_url`, `lang`, `device`, `game`, `version`, `mode`, `event`, `social`, `replay`
- RGS helpers for:
  - `/wallet/authenticate`
  - `/wallet/balance`
  - `/wallet/play`
  - `/bet/event`
  - `/wallet/end-round`
  - `/bet/replay/{game}/{version}/{mode}/{event}`

Repo evidence:
- `/Users/gerryturnbow/Downloads/comet/src/game/session.js`
- `/Users/gerryturnbow/Downloads/comet/src/game/rgsClient.js`

### 3. Replay and resume

Status: `ready`

What Stake expects:
- replay mode
- resuming active rounds returned from authenticate
- replayable in-progress round state

What ChadJack has:
- replay query-param support
- replay fetch path
- active-round hydration after authenticate
- round state snapshot schema for multi-step blackjack state

Repo evidence:
- `/Users/gerryturnbow/Downloads/comet/src/game/bootstrap.js`
- `/Users/gerryturnbow/Downloads/comet/src/game/stakeRoundState.js`
- `/Users/gerryturnbow/Downloads/comet/src/game/stakeRound.js`
- `/Users/gerryturnbow/Downloads/comet/src/game/store.js`

### 4. Math upload files

Status: `ready`

What Stake likely needs:
- `index.json`
- lookup CSV
- compressed game-logic file in `.jsonl.zst`

What I found in this repo:
- recovered math/export scaffold imported into this repo:
  - `/Users/gerryturnbow/Downloads/comet/math/engine.py`
  - `/Users/gerryturnbow/Downloads/comet/math/simulate.py`
  - `/Users/gerryturnbow/Downloads/comet/engine.py`
  - `/Users/gerryturnbow/Downloads/comet/stake_export.py`
  - `/Users/gerryturnbow/Downloads/comet/exact_sidebet_math.py`
  - `/Users/gerryturnbow/Downloads/comet/tests/test_math_readiness.py`
  - `/Users/gerryturnbow/Downloads/comet/tests/test_math_regression.py`
  - `/Users/gerryturnbow/Downloads/comet/tests/test_math_split_engine.py`
- recovered math tests pass locally
- canonical publish bundle now exists under:
  - `/Users/gerryturnbow/Downloads/comet/library/publish_files/index.json`
  - `/Users/gerryturnbow/Downloads/comet/library/publish_files/single_base.csv`
  - `/Users/gerryturnbow/Downloads/comet/library/publish_files/single_base.jsonl.zst`
  - `/Users/gerryturnbow/Downloads/comet/library/publish_files/single_pp.csv`
  - `/Users/gerryturnbow/Downloads/comet/library/publish_files/single_pp.jsonl.zst`
  - `/Users/gerryturnbow/Downloads/comet/library/publish_files/single_213.csv`
  - `/Users/gerryturnbow/Downloads/comet/library/publish_files/single_213.jsonl.zst`
  - `/Users/gerryturnbow/Downloads/comet/library/publish_files/single_both.csv`
  - `/Users/gerryturnbow/Downloads/comet/library/publish_files/single_both.jsonl.zst`
  - `/Users/gerryturnbow/Downloads/comet/library/publish_files/double_base.csv`
  - `/Users/gerryturnbow/Downloads/comet/library/publish_files/double_base.jsonl.zst`
  - `/Users/gerryturnbow/Downloads/comet/library/publish_files/double_pp_symmetric.csv`
  - `/Users/gerryturnbow/Downloads/comet/library/publish_files/double_pp_symmetric.jsonl.zst`
  - `/Users/gerryturnbow/Downloads/comet/library/publish_files/double_213_symmetric.csv`
  - `/Users/gerryturnbow/Downloads/comet/library/publish_files/double_213_symmetric.jsonl.zst`
  - `/Users/gerryturnbow/Downloads/comet/library/publish_files/double_both_symmetric.csv`
  - `/Users/gerryturnbow/Downloads/comet/library/publish_files/double_both_symmetric.jsonl.zst`
- `stake_export.py` now writes the frozen 8-mode ChadJack submission matrix into the canonical publish path

What this means:
- the repo now has a real, frozen ChadJack-specific publish bundle under `library/publish_files/`
- the fixed-cost mode matrix is adopted in the exporter and in `index.json`
- the remaining math work is verification/handoff, not missing infrastructure

### 5. Game Tile Visual Asset

Status: `ready`

Prepared assets:
- `/Users/gerryturnbow/Downloads/comet/game-tile-visual-asset/ChadJack-BG.jpg`
- `/Users/gerryturnbow/Downloads/comet/game-tile-visual-asset/ChadJack-FG.png`
- `/Users/gerryturnbow/Downloads/comet/game-tile-visual-asset/ChadLabs-Logo.png`

Current size check:
- `ChadJack-BG.jpg` = `482,110` bytes
- `ChadJack-FG.png` = `157,176` bytes
- combined BG + FG = `639,286` bytes

That is under the stated `3 MB` cap.

### 6. Reviewer handoff materials

Status: `ready`

Prepared docs:
- `/Users/gerryturnbow/Downloads/comet/HANDOFF.md`
- `/Users/gerryturnbow/Downloads/comet/submission/STAKE_ENGINE_APPROVAL_CHECKLIST.md`

### 7. Approval request packaging

Status: `mostly ready`

You still need one final approval packet outside the repo:
- a public Google Drive folder or whatever final share target you use for the approval request

Recommended folder contents:
- fresh `dist/` build
- math publish files
- `HANDOFF.md`
- `game-tile-visual-asset/`

## What Is Already Prepared

- frontend source and build configuration
- Stake launch param parsing
- authenticate/play/event/end-round wiring
- replay mode and active-round hydration
- recovered math/export scaffold
- recovered math tests
- game tile visual asset folder
- reviewer handoff doc

## What Is Still Missing

- final generated `dist/` at the moment of submission
- public approval-share folder containing the final packet

## Exact Next Steps

1. Build a fresh production frontend:
   - run `npm run build`
   - package the generated `dist/`
2. Assemble final submission packet:
   - `dist/`
   - math publish files
   - `HANDOFF.md`
   - `game-tile-visual-asset/`
3. Put that packet in a public Drive/share folder.
4. Use Stake Engine dashboard `Request Approval` and include the public link in the submission comment.

## Open Questions

- blackjack-specific math publication details are still less explicit in the public docs than slot examples
- side-bet math packaging may need confirmation if it is not already included in your math export pipeline
- if autoplay choices affect replay/state branching, confirm those paths are fully represented in exported round logic, not just runtime state

## Official Sources Used

- `https://stakeengine.github.io/math-sdk/`
- `https://stakeengine.github.io/math-sdk/rgs_docs/RGS/`
- `https://stakeengine.github.io/math-sdk/rgs_docs/data_format/`
- `https://stakeengine.github.io/math-sdk/simple_example/simple_example/`
- `https://github.com/StakeEngine/web-sdk`
- `https://github.com/StakeEngine/ts-client`
- `https://github.com/StakeEngine/math-sdk`
