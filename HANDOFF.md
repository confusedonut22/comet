# Handoff

Repo: `/Users/gerryturnbow/Downloads/comet`

## Current State

- Git `HEAD` is `d04516b`.
- The repo's current committed layout is the approved baseline.
- Do not use older conversational layout instructions as active rules.
- Do not assume production, screenshots, or prior experiments override the current committed repo state.

## Layout Freeze

The current layout is frozen exactly as it exists in Git at commit `d04516b`.

No pixel movement is allowed anywhere in the game unless the user explicitly unlocks:

- the exact element or region
- the exact geometry change that is allowed

Authoritative lock file:

- [/Users/gerryturnbow/Downloads/comet/LAYOUT_LOCK_RULES.md](/Users/gerryturnbow/Downloads/comet/LAYOUT_LOCK_RULES.md)

Authoritative Codex skill:

- `/Users/gerryturnbow/.codex/skills/comet-layout-freeze-guard/SKILL.md`

## Frozen By Default

- screen 1
- screen 2
- screen 3
- single-hand layout
- multi-hand layout
- dealer layout
- player cards
- count bubble
- wager bubble / wager bar
- sidebets
- options / balance placement
- divider / felt / texture layout
- bottom action area

## Operational Rule

Future work must assume:

1. The current committed layout is the only approved geometry.
2. Historical nudges, trial fixes, screenshot-specific adjustments, and prior ad hoc layout rules are obsolete.
3. Functional fixes must preserve current pixel geometry unless the user explicitly authorizes a visual change.
4. If an implementation would move frozen geometry as a side effect, that implementation is invalid.

## Do Not Do

- Do not reinterpret old chat history as permission to move layout.
- Do not use sidebet presence to shift cards or bubbles.
- Do not use screen/state transitions to shift cards or bubbles.
- Do not "clean up" spacing, centering, or alignment unless the user explicitly unlocks that exact area.
- Do not change desktop behavior unless explicitly requested.

## Recommended Next Step

Do not perform any layout work unless the user explicitly unlocks a specific region.

If the user requests a functional change:

1. Treat layout as frozen by default.
2. Verify whether the change can be implemented without moving frozen geometry.
3. If not, stop and report the conflict plainly.

## Build Note

- `npm run build` should still be used before finishing code changes.
- Existing non-blocking Svelte a11y warnings are not part of the layout freeze and should not be treated as layout permission.
