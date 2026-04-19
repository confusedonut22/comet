# Handoff

Repo: `/Users/gerryturnbow/Downloads/comet`

## Current State

- Git `HEAD` is `e7eeb82`.
- Current uncommitted work is in [/Users/gerryturnbow/Downloads/comet/src/ui/GameTableMobile.svelte](/Users/gerryturnbow/Downloads/comet/src/ui/GameTableMobile.svelte).
- This local state is intentionally **not** equal to production. It includes recent mobile-only layout experiments and partial clean-layout work.
- Latest local dev server used during this session was `http://192.168.1.158:5174`.
- Latest successful local build passed with the usual non-blocking Svelte a11y warnings.

## Working Tree

- Modified:
  - [/Users/gerryturnbow/Downloads/comet/src/ui/GameTableMobile.svelte](/Users/gerryturnbow/Downloads/comet/src/ui/GameTableMobile.svelte)
- Untracked local artifact folders exist and were not cleaned:
  - `/Users/gerryturnbow/Downloads/comet/.playwright-cli/`
  - `/Users/gerryturnbow/Downloads/comet/.playwright/`
  - `/Users/gerryturnbow/Downloads/comet/output/`
  - `/Users/gerryturnbow/Downloads/comet/test-results/`
  - `/Users/gerryturnbow/Downloads/comet/tmp/`
  - `/Users/gerryturnbow/Downloads/comet/tmp-card-fit/`
  - `/Users/gerryturnbow/Downloads/comet/assets/`
  - `/Users/gerryturnbow/Downloads/comet/crofton/`
  - `/Users/gerryturnbow/Downloads/comet/src/ui/comet.svelte`
  - `/Users/gerryturnbow/Downloads/comet/src/ui/crofton.svelte`

## Current Mobile Baseline

- Desktop must remain unchanged.
- Mobile remains the only target for these layout changes.
- The dealer header-strip experiment was **reverted**.
- The current visual baseline is:
  - compact top utility bar retained
  - dealer cards and dealer count restored to the older in-felt layout
  - perimeter highlight removed
  - screen 3 two-hand player result uses one centered ChadJack back per hand
  - stronger player/dealer card collapse helpers remain in place

## Screen Map

- Screen 1:
  - the bet/setup screen before cards are dealt
  - shows empty player placeholders, sidebet boxes, wager row, add-hand `+`, and `DEAL`
- Screen 2:
  - the live play screen after cards are dealt and before the round resolves
  - shows live dealer cards, live player cards, hand-value bubbles, action buttons like `HIT` / `STAND` / `SPLIT` / `x2`
- Screen 3:
  - the result / next-hand screen after the round resolves
  - shows resolved dealer/player state, result copy, preserved wager row, and `NEXT HAND`

## Important Active Behavior In `GameTableMobile.svelte`

- Player cards:
  - use adaptive mobile overlap via `mobilePlayerCardMetrics(cardCount)`
  - use downward stagger in screen 2 two-hand via `playerLiveCardStyle(i, cardCount)`
- Dealer cards:
  - use adaptive overlap via `dealerCardMargin(i, cardCount)`
- Screen 3 two-hand result:
  - uses one centered facedown ChadJack back card per hand
- Active perimeter:
  - removed for now

## What Was Tried And Reverted

- A mobile dealer-header strip was added between Balance and Options to reclaim felt space.
- That experiment moved dealer count/cards into the old utility-bar band.
- User then asked to revert to the previous build except for the utility-bar fix.
- Result:
  - dealer-header strip removed
  - dealer stack restored to prior felt position
  - compact utility bar retained

## Custom Skills Created / Relevant

- Existing curved-seat skill:
  - [/Users/gerryturnbow/.codex/skills/mobile-curved-seat-system-lock/SKILL.md](/Users/gerryturnbow/.codex/skills/mobile-curved-seat-system-lock/SKILL.md)
- New clean-layout skill:
  - [/Users/gerryturnbow/.codex/skills/mobile-layout-cleanliness-guard/SKILL.md](/Users/gerryturnbow/.codex/skills/mobile-layout-cleanliness-guard/SKILL.md)
- Relevant guard skills used/read during this session:
  - [/Users/gerryturnbow/.codex/skills/mobile-header-clearance-lock/SKILL.md](/Users/gerryturnbow/.codex/skills/mobile-header-clearance-lock/SKILL.md)
  - [/Users/gerryturnbow/.codex/skills/mobile-dealer-anchor-lock/SKILL.md](/Users/gerryturnbow/.codex/skills/mobile-dealer-anchor-lock/SKILL.md)

## Agent Audit Summary

- `Volta` and `Nash` both concluded the same thing:
  - the mobile layout is still row-based
  - too many fixed transforms and state-specific overrides are driving geometry
  - future scaling should move toward seat-bounded layout, not more `.hands-row.two` patching
- Their strongest recommendation:
  - treat each hand as one bounded company:
  - bubble
  - card lane
  - sidebet lane
  - wager row
  - then scale that company cleanly across states

## Latest Proof Screenshots

- Revert baseline after dealer-header rollback:
  - [/Users/gerryturnbow/Downloads/comet/output/revert-header-screen1-check.png](/Users/gerryturnbow/Downloads/comet/output/revert-header-screen1-check.png)
  - [/Users/gerryturnbow/Downloads/comet/output/revert-header-screen2-check.png](/Users/gerryturnbow/Downloads/comet/output/revert-header-screen2-check.png)
- Earlier cleanup proof:
  - [/Users/gerryturnbow/Downloads/comet/output/qa-screen1-twohand-clean-layout.png](/Users/gerryturnbow/Downloads/comet/output/qa-screen1-twohand-clean-layout.png)
  - [/Users/gerryturnbow/Downloads/comet/output/qa-screen2-twohand-clean-layout.png](/Users/gerryturnbow/Downloads/comet/output/qa-screen2-twohand-clean-layout.png)
  - [/Users/gerryturnbow/Downloads/comet/output/qa-screen3-twohand-clean-layout.png](/Users/gerryturnbow/Downloads/comet/output/qa-screen3-twohand-clean-layout.png)

## Known Problems Still Open

- Multi-hand bottom player lane is still space-constrained around the wager/action region.
- Dealer/header clearance on mobile is still not truly solved; the header-strip concept worked mechanically but was not kept.
- The current system still uses too many hard-coded mobile row assumptions for long-term scaling.
- A clean 4-hand mobile layout is still unresolved.

## Recommended Next Step

Do this next, in order:

1. Start from the current reverted baseline in [/Users/gerryturnbow/Downloads/comet/src/ui/GameTableMobile.svelte](/Users/gerryturnbow/Downloads/comet/src/ui/GameTableMobile.svelte), not from production assumptions.
2. Solve mobile dealer clearance without reintroducing the full header-strip version unless explicitly requested again.
3. Keep all work mobile-only.
4. Use [/Users/gerryturnbow/.codex/skills/mobile-layout-cleanliness-guard/SKILL.md](/Users/gerryturnbow/.codex/skills/mobile-layout-cleanliness-guard/SKILL.md) on the next pass.
5. Verify with fresh screenshots in:
  - screen 1 two-hand
  - screen 2 two-hand
  - screen 3 two-hand
6. Do not commit or deploy until the user explicitly asks.

## Build Note

- `npm run build` passed during this session.
- The familiar Svelte a11y warnings remain and were not addressed here.
