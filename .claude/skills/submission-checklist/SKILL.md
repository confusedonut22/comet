---
name: submission-checklist
description: Run this skill when the user asks to "run the submission checklist", "check if we're ready to submit", "verify submission requirements", or "go through the approval checklist". Performs a thorough automated audit of the ChadJack game against the Stake approval criteria.
argument-hint: [section]
allowed-tools: [Read, Glob, Grep, Bash]
---

# ChadJack Submission Checklist

Run a thorough audit of the ChadJack game against the Stake submission approval criteria. Work through every item below — check code where possible, flag what requires manual verification, and produce a final pass/fail report.

## Instructions

Work through EVERY section below in order. For each checklist item:
- **PASS** — verified by code inspection or test output
- **FAIL** — found a concrete defect; describe exactly what's wrong
- **MANUAL** — requires human eyes/testing; describe exactly what to check and where

Do NOT skip any item. At the end, produce a clean summary table showing every item with its status.

---

## SECTION 1 — PreChecks

### 1.1 RGS Authentication on Launch
- Read `src/game/rgsClient.js` and `src/game/session.js`
- Verify the game calls `authenticateSession` or equivalent on startup, passes operator token/credentials, and handles auth failure gracefully
- Check `src/game/bootstrap.js` for the launch sequence

### 1.2 Bet Button Sends Successful Play Request to RGS
- In `rgsClient.js`, find the function that sends a play/bet request
- Confirm it sends the correct payload (betAmount, currency, sessionId) to the RGS endpoint
- Run existing tests: `cd /Users/gerryturnbow/Downloads/comet && npm test 2>&1 | tail -40`
- Check `test/stakeRound.test.js` and `test/rgsClient.test.js` specifically

### 1.3 Game Title is Unique and Contains No Forbidden Terms
- Search for the game title string in `src/game/content.js`, `index.html`, and `package.json`
- Confirm the title does NOT contain: "Megaways", "Xways", "Megapays", "Hyperways", or any trademark terms
- Check: `grep -ri "megaways\|xways\|megapays\|hyperways" /Users/gerryturnbow/Downloads/comet/src/ /Users/gerryturnbow/Downloads/comet/index.html`

### 1.4 Game Assets — No Offensive/Discriminatory/Inappropriate Content
- List all image/video assets: `find /Users/gerryturnbow/Downloads/comet/public /Users/gerryturnbow/Downloads/comet/src/assets -type f \( -name "*.png" -o -name "*.jpg" -o -name "*.webp" -o -name "*.mp4" -o -name "*.svg" \) 2>/dev/null`
- Flag any file names that are suspicious; note this requires visual review of actual images
- Status: MANUAL — list the asset filenames and note they need visual sign-off

---

## SECTION 2 — Game Thumbnail

All 6 thumbnail checks are MANUAL — they require visual inspection of the actual tile/thumbnail images.

- Find thumbnail assets: `find /Users/gerryturnbow/Downloads/comet/public /Users/gerryturnbow/Downloads/comet/src/assets -name "*thumb*" -o -name "*tile*" -o -name "*thumbnail*" 2>/dev/null`
- Also check the Stake submission portal for any uploaded thumbnail

Report the following as MANUAL with where the files are:
- **2.1** Tile is bright and doesn't clash with Stake background (no dark edges)
- **2.2** Background image is bright and appropriate
- **2.3** Foreground image is appropriate and key focus area is filled
- **2.4** Gradient color matches background
- **2.5** Game title fits within inner guidelines (not too close to edges)
- **2.6** No wording or multipliers on background/foreground images

---

## SECTION 3 — Math Requirements

### 3.1 Math Section Has No Validation Warnings
- Run the full test suite: `cd /Users/gerryturnbow/Downloads/comet && npm test 2>&1`
- Check `test/roundSettlement.test.js` — look for any failures in payout calculations
- Check `test/session.test.js` — verify RTP is within expected range
- Read `src/game/engine.js` and `src/game/roundSettlement.js` — look for any TODO/FIXME comments related to math
- Read `src/game/rules.js` — verify BJ_MULTIPLIER is 1.5 (3:2), check all payout constants
- Specifically check: does `settleDealerHands` accidentally pay 3:2 on ace-split hands that reach 21? (known potential bug)

---

## SECTION 4 — Frontend Requirements

### 4.1 Space Bar Bound to Bet Button (Deal)
- Search: `grep -n "keydown\|keyup\|keypress\|space\|Key\.Space\| 32\b" /Users/gerryturnbow/Downloads/comet/src/ui/GameTable.svelte /Users/gerryturnbow/Downloads/comet/src/ui/desktop-canonical/lib/layouts/BlackjackTableLayoutCore.svelte 2>/dev/null`
- Verify spacebar triggers the Deal/Next Hand action

### 4.2 Confirmation for Bet Modes with >2x Cost
- Read `src/game/betConfig.js` — check if there are any bonus modes or bet multipliers
- Search for confirmation dialogs: `grep -rn "confirm\|modal\|dialog\|2x\|multiplier" /Users/gerryturnbow/Downloads/comet/src/ 2>/dev/null | grep -v ".css\|svelte-" | head -30`
- ChadJack is standard blackjack — verify there are no bet modes exceeding 2x (sidebets don't count as "modes")

### 4.3 Win Verification — 10 Wins per Game Mode
- This is a MANUAL test. Describe what to do:
  - Launch the game at the LAN URL (192.168.1.188:5174)
  - Play 10 hands in each mode: Standard, 2-hand, 3-hand
  - For each win, compare: displayed win amount vs expected (bet × multiplier)
  - Blackjack should pay 3:2, wins pay 1:1, push returns bet

### 4.4 Win Verification — 6 Wins per Game Mode
- MANUAL — same as above, run 6 wins per mode specifically checking:
  - Insurance payout (1:1 on insurance bet)
  - Split hand payouts
  - Double-down payouts

### 4.5 Win Verification — 3 Wins per Game Mode  
- MANUAL — run 3 wins per mode checking 21+3 and Perfect Pairs sidebets match Game Rules

---

## SECTION 5 — Replay Support

### 5.1 Supports Replay URLs and Plays Desired Event
- Read `src/game/session.js` — check for `replayMode`, `replayRound`, or replay URL param handling
- Read `src/game/bootstrap.js` — look for URL param parsing for replay
- Search: `grep -rn "replay\|replayMode\|replayRound\|replayEvent" /Users/gerryturnbow/Downloads/comet/src/ 2>/dev/null | head -20`

### 5.2 Supports Optional Parameters (currency, language, amount)
- In the URL param / session bootstrap code, verify `currency`, `language`, and `amount` params are read and applied
- Search: `grep -rn "currency\|language\|locale" /Users/gerryturnbow/Downloads/comet/src/game/ 2>/dev/null | head -20`

### 5.3 Allows Replaying "event" at End of Replay
- Check if, at replay end, the game returns to a playable state or loops back
- Look for replay completion handlers in `session.js` or `stakeRound.js`

### 5.4 UI Displays Bet Cost Including Multiplier and Real Cost
- This applies if there are bonus rounds with multiplied costs
- For standard ChadJack, verify the bet amount display in the UI is clear and accurate
- Read wager/bet display code in `src/ui/desktop-canonical/lib/layouts/BlackjackTableLayoutCore.svelte` and `src/ui/GameTableMobile.svelte`

---

## SECTION 6 — Final Approval Checklist

### 6.1 Bet-Level Templates Applied (US must use `us_` prefix)
- Read `src/game/betConfig.js` or `src/game/rules.js` — check for bet templates
- Search: `grep -rn "us_\|template\|betTemplate\|betLevel" /Users/gerryturnbow/Downloads/comet/src/ 2>/dev/null | head -20`

### 6.2 Front and Math Requests Set as Approved & Active
- MANUAL — must be verified in the Stake RGS admin portal

### 6.3 Game Appeared in Approved Channels
- MANUAL — check `#stake-engine-game-approved` and `#stake-engine-us-game-approved` Discord/Slack channels

### 6.4 Approval Request Closed Once Rocket-Ship Emoji Live
- MANUAL — monitor the approval request thread

### 6.5 Tested on Older Android and iOS Versions
- MANUAL — test on:
  - Android 9+ (Chrome)
  - iOS 14+ (Safari)
  - Pay attention to: touch events, viewport sizing, font rendering

### 6.6 Game Released
- MANUAL — final go-live confirmation

---

## Output Format

After completing all checks, output a report in this exact format:

```
═══════════════════════════════════════════════════════
  CHADJACK SUBMISSION CHECKLIST REPORT
═══════════════════════════════════════════════════════

SECTION 1 — PreChecks
  ✅ 1.1  RGS Authentication on Launch
  ✅ 1.2  Bet Button Sends Play Request
  ✅ 1.3  Game Title Unique / No Forbidden Terms
  🔍 1.4  Asset Content Review  [MANUAL]

SECTION 2 — Game Thumbnail
  🔍 2.1–2.6  All thumbnail items  [MANUAL — see asset list below]

SECTION 3 — Math
  ✅ 3.1  Math Validation (all tests pass)
  ❌ 3.x  [description of any failure]

SECTION 4 — Frontend
  ✅ 4.1  Spacebar bound to Deal
  ✅ 4.2  No >2x bet modes requiring confirmation
  🔍 4.3  10-win manual test  [MANUAL]
  🔍 4.4  6-win manual test   [MANUAL]
  🔍 4.5  3-win manual test   [MANUAL]

SECTION 5 — Replay
  ✅ 5.1  Replay URL support
  ✅ 5.2  Optional params (currency/language/amount)
  ✅ 5.3  End-of-replay event handling
  ✅ 5.4  Bet cost display clear

SECTION 6 — Final
  🔍 6.1  Bet templates  [verify in portal]
  🔍 6.2  Approved & Active in portal  [MANUAL]
  🔍 6.3  Approved channels  [MANUAL]
  🔍 6.4  Rocket-ship emoji  [MANUAL]
  🔍 6.5  Old Android/iOS tested  [MANUAL]
  🔍 6.6  Game Released  [MANUAL]

───────────────────────────────────────────────────────
AUTOMATED: X passed, X failed, X flagged
MANUAL:    X items require human verification
BLOCKERS:  [list any ❌ items here]
═══════════════════════════════════════════════════════
```

Use ✅ for PASS, ❌ for FAIL (with explanation), 🔍 for MANUAL.
List every BLOCKER (❌) with a one-line description of what's broken and where to fix it.
