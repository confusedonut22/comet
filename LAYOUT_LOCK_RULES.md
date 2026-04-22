## ChadJack Layout Lock Rules

Effective date: 2026-04-22
Repo: `/Users/gerryturnbow/Downloads/comet`

### Active Lock

Desktop is frozen exactly as it exists now.

Do not make any desktop layout, styling, geometry, spacing, positioning, scale, card-lane, sidebet-lane, footer, header, options, balance, dealer-area, player-area, or action-bar changes unless the user explicitly unlocks desktop in a future request.

### Frozen Desktop Areas

- screen 1 desktop
- screen 2 desktop
- screen 3 desktop
- single-hand desktop layout
- multi-hand desktop layout
- dealer geometry
- player card geometry
- count bubble geometry
- wager bar / wager label geometry
- sidebet geometry
- autoplay / deal / next-hand footer layout
- options / balance placement
- felt / divider / background layout
- lower action area layout

### Allowed Without Unlock

- mobile-only work
- non-layout desktop bugfixes that do not alter visuals or geometry
- content, copy, or config changes that do not change desktop presentation

### Required Future Behavior

If a future request touches desktop in any way:

1. Restate that desktop is frozen.
2. Identify the exact desktop element the user is unlocking.
3. Do not move any other desktop element without an explicit unlock.
