# Handoff

Repo: `/Users/gerryturnbow/Downloads/comet`

## Current State

- Main mobile work is concentrated in [/Users/gerryturnbow/Downloads/comet/src/ui/GameTableMobile.svelte](/Users/gerryturnbow/Downloads/comet/src/ui/GameTableMobile.svelte).
- Latest build passes with non-blocking Svelte a11y warnings.
- Latest preview: `https://comet-hbypgvaib-confusedonut22s-projects.vercel.app`
- Latest inspector: `https://vercel.com/confusedonut22s-projects/comet/Csv2woYSecDgDHtFAoktJ9YV3Tz7`

## What Is Locked

- Dealer card size must not change unless explicitly requested.
- `CHADJACK pays 7 to 5` must not move or change unless explicitly requested.
- Desktop must remain unchanged unless explicitly unlocked.
- Mobile fixes should stay mobile-only.
- The player-count bubble is a hard alignment anchor when aligning player cards.

## Recent Mobile Changes

- Main-menu `CHADJACK` size was reduced from the previously enlarged state.
- Two-hand player-card seam was adjusted toward the player-count centerline without moving the bubble.
- The dark dead block above `NEXT HAND` was removed so felt texture shows through.
- Autoplay access was adjusted so it is available on non-bet screens and hidden on active bet.
- A custom spacing skill was created:
  - `/Users/gerryturnbow/.codex/skills/mobile-blackjack-spacing-lock/SKILL.md`

## Latest Proof Assets

- `/Users/gerryturnbow/Downloads/comet/output/screens/main-menu-chadjack-reduced.png`
- `/Users/gerryturnbow/Downloads/comet/output/screens/two-hand-seam-alignment.png`
- `/Users/gerryturnbow/Downloads/comet/output/screens/active-bet-no-autoplay-fresh.png`
- `/Users/gerryturnbow/Downloads/comet/output/screens/non-bet-autoplay-access-fresh.png`
- `/Users/gerryturnbow/Downloads/comet/output/screens/result-next-hand-felt-v2.png`

## Known Outstanding Risk

- The most recent seam-alignment audit still indicated the player-card seam may not be perfectly locked to the player-count centerline in every two-hand mobile state. If resumed, verify that exact alignment first from a fresh screenshot before changing anything else.

## Exact Next Step

If work resumes, do this in order:

1. Re-check the latest preview on the two-hand mobile screen against the player-count centerline screenshot.
2. If the seam is still off, adjust only the two-hand player card-row horizontal offset in `GameTableMobile.svelte`.
3. Do not move the player-count bubble.
4. Build.
5. Deploy a fresh preview.
