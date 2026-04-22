# ChadJack — Stake Engine Submission Handoff

## Project Overview

**ChadJack** is a full-featured mobile blackjack game built in Svelte 4 / Vite 8. It is RGS-integrated against the Stake Engine wallet API and is ready for submission. The production build is live on Vercel.

- **Production URL:** https://comet-nqfeufej0-confusedonut22s-projects.vercel.app
- **GitHub repo:** https://github.com/confusedonut22/comet
- **Branch:** `main` (all mobile work is merged)
- **Vercel project:** `comet` (org: confusedonut22s-projects, projectId: `prj_GOr914Jj4Ml0h4TxW44WZCSomhbd`)

---

## Game Tile Visual Asset

Mandatory submission assets have been prepared in:

`game-tile-visual-asset/`

Files:

- `ChadJack-BG.jpg` — background tile art derived from the provided in-game felt screenshot
- `ChadJack-FG.png` — transparent ChadJack foreground logo
- `ChadLabs-Logo.png` — transparent provider logo

Source copies retained in the same folder:

- `source-screenshot.png`
- `ChadJack-FG-source.png`
- `ChadLabs-Logo-source.png` (copied from the provided `chadlabs.png`)

Asset sizes:

| File | Size |
|---|---|
| `ChadJack-BG.jpg` | 482,110 bytes |
| `ChadJack-FG.png` | 157,176 bytes |
| `ChadLabs-Logo.png` | 150,558 bytes |

`ChadJack-BG.jpg` + `ChadJack-FG.png` combined size: **639,286 bytes** (~0.61 MB), which is under the **3 MB** submission cap.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Framework | Svelte 4 |
| Build tool | Vite 8 |
| Rendering | PixiJS 8 (canvas layer for animations) |
| Fonts | Bebas Neue, Fredoka One, Oswald, Rock Salt, Caveat, Inter |
| Node | 24.x (Vercel default) |
| Hosting | Vercel (static SPA) |

---

## Repository Structure

```
src/
  game/
    store.js              — Full game state (Svelte stores), all game logic
    engine.js             — Blackjack rules engine (deal, hit, stand, double, split)
    rules.js              — Configurable rule set (decks, S17/H17, DAS, RSA, etc.)
    rgsClient.js          — Stake Engine RGS API client (authenticate, play, end-round, replay, events)
    stakeRound.js         — Stake round normalizer
    stakeRoundState.js    — Round state snapshot/hydration (schema v1)
    betConfig.js          — Bet level/min/max/step normalizer from Stake config payload
    session.js            — URL query param parser (sessionID, rgs_url, lang, device, etc.)
    sessionBootstrapModel.js — Bootstrap state machine (local/error/resumed/resume-blocked/ready)
    roundSettlement.js    — Payout calculation
    audio.js              — Sound effects
    canvas.js             — PixiJS canvas bridge
    bootstrap.js          — App init / session hydration
    content.js            — Static text / copy
  ui/
    GameTableMobile.svelte  — MAIN MOBILE UI (~5100 lines, single-file component)
    GameTable.svelte        — Desktop entry point
    desktop-canonical/      — Desktop layout components
```

---

## Stake Engine RGS Integration

### Launch Parameters (URL query string)

| Param | Env var fallback | Description |
|---|---|---|
| `sessionID` | `VITE_STAKE_SESSION_ID` | Player session token |
| `rgs_url` | `VITE_STAKE_RGS_URL` | RGS base URL |
| `lang` | `VITE_STAKE_LANG` | Language code (default: `en`) |
| `device` | `VITE_STAKE_DEVICE` | `mobile` / `desktop` |
| `game` | `VITE_STAKE_GAME` | Game identifier |
| `version` | `VITE_STAKE_VERSION` | Game version |
| `mode` | `VITE_STAKE_MODE` | `BASE` / `REPLAY` |
| `event` | `VITE_STAKE_EVENT` | Replay event ID |
| `social` | `VITE_STAKE_SOCIAL` | Social casino flag (`1`/`true`) |
| `replay` | `VITE_STAKE_REPLAY` | Enable replay mode (`1`/`true`) |

### RGS API Endpoints (all relative to `{rgs_url}`)

| Endpoint | Method | Purpose |
|---|---|---|
| `/wallet/authenticate` | POST | Session auth — returns balance + config + active round |
| `/wallet/balance` | POST | Fetch current balance |
| `/wallet/play` | POST | Start a round, place bet |
| `/wallet/end-round` | POST | Settle and close round |
| `/bet/event` | POST | Post mid-round game state snapshot |
| `/bet/replay/{game}/{version}/{mode}/{event}` | GET | Fetch a replay round |

### Round State Schema (version 1)

Game state is snapshotted and sent to `/bet/event` after every significant player action. Shape (`buildRoundStateSnapshot` in `stakeRoundState.js`):

```json
{
  "schemaVersion": 1,
  "phase": "PLAY | RESULT | BET",
  "activeHand": 0,
  "allowedActions": ["hit", "stand", "double"],
  "dealerHand": [{ "rank": "K", "suit": "spades" }],
  "shoe": [],
  "hands": [
    {
      "bet": 1000,
      "baseBet": 1000,
      "sideBets": { "pp": 0, "t": 0 },
      "cards": [],
      "result": null,
      "message": "",
      "payout": 0,
      "done": false,
      "doubled": false,
      "isSplit": false,
      "isAceSplit": false,
      "sideBetResults": []
    }
  ],
  "pendingInsurance": null,
  "message": "",
  "lossStreak": 0
}
```

### Bet Config (from authenticate response `config` field)

```json
{
  "minBet": 100,
  "maxBet": 100000,
  "stepBet": 100,
  "defaultBetLevel": 1000,
  "betLevels": [100, 500, 1000, 5000, 10000],
  "sideBets": {
    "pp": { "minBet": 100, "maxBet": 5000 },
    "t":  { "minBet": 100, "maxBet": 5000 }
  }
}
```

All monetary values are **integers in the smallest currency unit** (e.g. cents). Normalized by `normalizeStakeConfig` in `betConfig.js`.

### Jurisdiction Flags (from authenticate response)

```json
{
  "socialCasino": false,
  "disabledFullscreen": false,
  "disabledTurbo": false,
  "disabledSuperTurbo": false,
  "disabledAutoplay": false,
  "disabledSlamstop": false,
  "disabledSpacebar": false,
  "disabledBuyFeature": false,
  "displayNetPosition": false,
  "displayRTP": true,
  "displaySessionTimer": false,
  "minimumRoundDuration": 0
}
```

### Session Bootstrap States

After authenticate, the app enters one of these states (`sessionBootstrapModel.js`):

| Status | Meaning |
|---|---|
| `local` | No sessionID/rgs_url — running in local/demo mode |
| `error` | Auth failed |
| `ready` | Authenticated, no active round |
| `resumed` | Active round found and state is hydratable — resumes mid-hand |
| `resume-blocked` | Active round found but state cannot be hydrated — player blocked |

### Window Events Emitted (for host iframe integration)

| Event | Detail | Fired when |
|---|---|---|
| `balanceUpdate` | `balance` (integer) | After any wallet call returning balance |
| `roundActive` | `{ active: boolean }` | Round starts or ends |

---

## Mobile UI — GameTableMobile.svelte

This is the primary deliverable. Single Svelte component, ~5100 lines.

### Game Features
- Blackjack with configurable rules (1–8 decks, S17/H17, DAS, RSA, BJ pays 3:2 / 6:5 / 7:5)
- **Side bets: Perfect Pairs + 21+3** (enabled/configured via Stake config)
- **Multi-hand play** (up to 4 simultaneous betting spots)
- **Split hands** (including Ace splits, re-split where allowed)
- Double down, insurance
- Autoplay (Conservative / Optimal basic strategy / High Roller modes, configurable max rounds)
- Replay mode (fetches historical round from RGS, plays back non-interactively)
- Social casino mode (hides real-money UI elements)
- Custom face card art (Jack of Clubs custom image supported)

### Split Layout (finalized — was the main bug this session)

When a player splits a pair, the UI enters `useSplitRows` mode:

```javascript
$: useSplitRows = !isDesktop && handEntries.some(({ hand }) => hand.isSplit);
```

- **Left (original) hand**: frozen in its single-hand position — `felt.single-hand` and `phase-play-single-hand` classes are preserved via `class:single-hand={!multi || useSplitRows}` and `class:phase-play-single-hand={isPlay && ($numSlots === 1 || useSplitRows)}`
- **Right (split) hand**: the second `isSplit=true` hand (`splitRightIdx`) is taken out of flow — `position:absolute; left:calc(50% + 90px); top:50%; transform:translateY(-50%); --mobile-geometry-scale:calc(0.9 * 0.7)` — 30% smaller, vertically centered, no side bets, no bet bar
- **Containing block**: `.hands-row.has-split { position: relative }` — selector is intentionally broad (not `.two.has-split`) so it works with any number of slots
- Works correctly with 2 active betting spots — neither original hand drifts when one splits

### Key Svelte Stores (src/game/store.js)

| Store | Type | Purpose |
|---|---|---|
| `numSlots` | writable(1) | Number of active betting spots (1–4) |
| `hands` | writable([]) | Array of hand objects |
| `phase` | derived | `"BET" \| "PLAY" \| "RESULT"` |
| `sideBetsEnabled` | writable | Side bet UI toggle |
| `autoBetEnabled` | writable | Autoplay on/off |
| `showRules` | writable | Rules panel open state |

---

## Local Development

```bash
# Clone
git clone https://github.com/confusedonut22/comet.git
cd comet
npm install

# Standard dev server (localhost only)
npm run dev

# LAN — accessible from phone on same WiFi
npm run dev:mobile
# Opens on: http://<your-mac-ip>:5173/
```

### Testing on physical mobile device
1. Run `npm run dev:mobile`
2. Note the `Network:` URL in the terminal output
3. Connect your phone to the same WiFi network
4. Open the Network URL in your phone's browser

---

## Deployment

```bash
# Deploy to Vercel production
vercel --prod
```

The app is a fully static SPA — no serverless functions. All config arrives via URL query params at runtime.

---

## Files to Read First in a New Claude Session

To continue work on this project without losing context, read these in order:

1. `HANDOFF.md` — this document
2. `src/game/store.js` — all game state and logic
3. `src/ui/GameTableMobile.svelte` — entire mobile UI
4. `src/game/rgsClient.js` — Stake RGS API integration
5. `src/game/stakeRoundState.js` — round state schema
6. `src/game/session.js` — launch param parsing

---

## Outstanding Items Before / After Submission

- [ ] Remove debug `console.log` statements from `GameTableMobile.svelte` script section
- [ ] Confirm Stake Engine's expected `game` and `version` identifier strings
- [ ] End-to-end test replay mode against a live Stake RGS sandbox
- [ ] `src/ui/desktop-canonical/` has uncommitted local changes — desktop build is separate work
- [ ] Confirm certificate/compliance requirements with Stake (RTP display, session timer, etc.)

---

*Generated 2026-04-20. Production commit: `5742e09`.*
