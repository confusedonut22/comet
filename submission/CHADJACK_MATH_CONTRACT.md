# ChadJack Math Contract

Repo: `/Users/gerryturnbow/Downloads/comet`

Purpose: freeze the rules, event semantics, and wager-handling assumptions that the imported Stake export scaffold must use for ChadJack.

Status: `draft, first-pass submission contract`

This contract works together with:
- [CHADJACK_MODE_MATRIX.md](/Users/gerryturnbow/Downloads/comet/submission/CHADJACK_MODE_MATRIX.md)

## Core Rule

The mode matrix defines the **fixed starting cost** of a ChadJack round.

This math contract defines:
- what happens inside a round after it starts
- how extra wager decisions are represented
- which player policy the export generator assumes
- what event book shape the frontend and replay logic should expect

## Ruleset Lock

These values are the frozen first-pass export assumptions.

### Base game

- game type: blackjack
- decks: `6`
- reshuffle threshold: `52 cards remaining`
- blackjack payout: `3:2`
- dealer rule: `H17` (dealer hits soft 17)
- split allowed: `yes, same-rank pair only`
- resplit allowed: `no`
- double after split: `no`
- split aces: `one card only, locked`
- insurance offered: `yes, when dealer up-card is Ace`

Repo references:
- `/Users/gerryturnbow/Downloads/comet/src/game/rules.js`
- `/Users/gerryturnbow/Downloads/comet/math/engine.py`
- `/Users/gerryturnbow/Downloads/comet/exact_sidebet_math.py`

### Side bets

- Perfect Pairs:
  - Perfect Pair: `25:1`
  - Coloured Pair: `12:1`
  - Mixed Pair: `6:1`
- 21+3:
  - Suited Trips: `100:1`
  - Straight Flush: `40:1`
  - Three of a Kind: `30:1`
  - Straight: `10:1`
  - Flush: `5:1`

These are treated as fixed rule components of the exported product.

## Mode-to-Round Relationship

Starting modes are defined only by the initial wager profile in:
- [CHADJACK_MODE_MATRIX.md](/Users/gerryturnbow/Downloads/comet/submission/CHADJACK_MODE_MATRIX.md)

That means:
- `single_base` starts with one hand and no side bets
- `single_pp` starts with one hand and PP only
- `single_213` starts with one hand and 21+3 only
- `single_both` starts with one hand and both side bets
- `double_base` starts with two hands and no side bets
- `double_pp_symmetric` starts with two hands and PP on both hands
- `double_213_symmetric` starts with two hands and 21+3 on both hands
- `double_both_symmetric` starts with two hands and both side bets on both hands

Nothing outside those starting profiles belongs in the first-pass math export.

## Player Policy Assumption

For the first export pass, ChadJack math should assume:
- **basic strategy policy**

That means:
- no separate export modes for autoplay strategies
- no separate export modes for arbitrary human deviations
- no strategy-specific RTP modes in `index.json`

Reason:
- this keeps the mode matrix finite
- the recovered exporter already uses a deterministic strategy policy
- it is the cleanest first-pass approximation for Stake upload math

## Wager Handling Contract

This section freezes how each extra wager type is represented.

### Starting cost

The mode cost is the **initial round cost only**.

It includes:
- main bet(s)
- included side bet(s) defined by the selected mode

It does **not** include:
- insurance
- doubles
- split-created extra hands

Those are handled inside the round event book.

### Insurance

Insurance is:
- a conditional in-round wager
- only offered when the dealer up-card is Ace
- capped at half of the relevant main wager amount

Export treatment:
- insurance is **not** a separate starting mode
- insurance appears as an event decision inside the round record
- insurance payout contributes to total returned amount for `payoutMultiplier`

### Double down

Double down is:
- an in-round wager increase on the active hand

Export treatment:
- double is **not** a separate starting mode
- double appears as an in-round player decision
- additional wager amount increases round total wagered
- payout multiplier is computed against the final total wagered for that round

### Split

Split is:
- an in-round branch that creates an additional hand from a pair

Export treatment:
- split is **not** a separate starting mode
- split appears as an in-round player decision
- split-created extra hand wager increases round total wagered
- split aces are locked to one draw
- no resplit
- no DAS

## Payout Multiplier Contract

For exported round records:
- `payoutMultiplier = totalReturned / totalWagered`

Where:
- `totalWagered` includes:
  - starting cost from the mode
  - insurance taken
  - doubles
  - extra wager from split-created hand(s)
- `totalReturned` includes:
  - base-game settlements
  - pushes
  - side-bet payouts
  - insurance payout when applicable

This matches the recovered scaffold behavior and keeps a single round-level multiplier per exported record.

## Event Book Contract

Every exported round must include:
- `id`
- `events`
- `payoutMultiplier`

The intended event sequence for ChadJack is:

1. `initialDeal`
2. `sideBetsResolved` if applicable
3. `insuranceTaken` or no insurance event if offered and declined
4. one or more `playerAction` events:
   - `hit`
   - `stand`
   - `double`
   - `split`
5. `dealerFinal`
6. `roundSettlement`

### Event semantics

#### `initialDeal`

Must capture:
- dealer up card
- dealer hole card for authoritative export record
- initial player cards
- starting side-bet profile
- whether insurance was offered

#### `sideBetsResolved`

Must capture:
- side-bet type
- win/loss
- name/category
- payout

#### `insuranceTaken`

Must capture:
- insurance amount

If insurance is declined, the round may omit this event or represent decline explicitly later if the exporter needs it. For first pass, omission of `insuranceTaken` means no insurance was taken.

#### `playerAction`

Must capture:
- action type
- affected hand index when relevant
- dealt card when action draws a card
- resulting visible value when relevant

#### `dealerFinal`

Must capture:
- final dealer cards
- final dealer value

#### `roundSettlement`

Must capture:
- settlement for each hand
- total wagered
- total returned
- whether insurance was taken

## Replay Contract

The export event book must remain compatible with frontend replay expectations.

That means exported records must be able to explain:
- one-hand rounds
- two-hand rounds
- split rounds
- insurance rounds
- side-bet outcomes
- final settlement totals

The frontend replay system does **not** need separate mode names for split or insurance. Those are event-driven branches inside the selected starting mode.

## Explicit Non-Goals For First Pass

These are out of scope for the first export contract:
- asymmetric two-hand side-bet starting profiles
- autoplay-specific export modes
- alternate payout tables
- alternate deck-count modes
- alternate dealer-rule modes

## Validation Requirements

A round export implementation is only acceptable if it passes all of these:

1. recovered math tests still pass
2. exported event books can represent split rounds
3. exported event books can represent insurance
4. exported event books can represent two-hand symmetric modes
5. exported payout multipliers match total wagered vs total returned exactly

## Acceptance Gate

The imported export scaffold can be treated as ChadJack’s final Stake math baseline only when:

1. this contract is accepted
2. the mode matrix is accepted
3. the exporter writes the 8 frozen modes
4. the outputs land in a canonical publish folder
5. replay verification passes against exported event books

## Next Step

After this contract, the next implementation step is:
- adapt `stake_export.py` so it targets the 8 modes in [CHADJACK_MODE_MATRIX.md](/Users/gerryturnbow/Downloads/comet/submission/CHADJACK_MODE_MATRIX.md) and writes canonical publish outputs.
