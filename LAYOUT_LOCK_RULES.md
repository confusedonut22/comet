# Layout Lock Rules

Repository: `/Users/gerryturnbow/Downloads/comet`
Baseline commit: `d04516b`
Final build freeze declared: `2026-04-19`

This file replaces all prior conversational layout rules.

## Canonical Rule

The current approved layout is locked exactly as-is.

No pixel movement is allowed anywhere in the game unless the user explicitly unlocks a specific element or region.

## Locked By Default

- All screen 1 layout
- All screen 2 layout
- All screen 3 layout
- Single-hand layout
- Multi-hand layout
- Dealer layout
- Player card layout
- Count bubble layout
- Wager bubble / wager bar layout
- Sidebet layout
- Options / balance layout
- Divider / felt / texture layout
- Bottom action layout

## Operational Rule

For future tasks, assume:

1. The current committed layout is the only approved geometry.
2. Historical instructions, experimental nudges, and prior ad hoc rules are void.
3. No layout-related request may be interpreted as permission to move any element except the exact element the user explicitly unlocks.
4. If a requested implementation would move any locked geometry as a side effect, that implementation is invalid.
5. Functional fixes must preserve current pixel geometry unless the user explicitly authorizes a visual change.
6. Non-geometry styling updates are allowed only when they do not alter position, size, spacing, alignment, or containment.

## Unlock Protocol

Layout may change only if the user explicitly states both:

- what element is unlocked
- what movement or geometry change is allowed

Anything not explicitly unlocked remains frozen.
