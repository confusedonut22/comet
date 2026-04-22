# ChadJack Mode Matrix

Repo: `/Users/gerryturnbow/Downloads/comet`

Purpose: freeze the first-pass Stake Engine math mode list for ChadJack so the export pipeline has a fixed set of costs to target.

Status: `draft, recommended submission scope`

## Core Rule

For the first approval pass, ChadJack should use a **reduced, explicit mode matrix**.

Included:
- 1-hand base game
- 1-hand side-bet combinations
- 2-hand base game
- 2-hand symmetric side-bet combinations

Excluded:
- asymmetric 2-hand side-bet combinations
- strategy-specific autoplay math modes
- alternate rule-set variants

This keeps the Stake mode list finite and keeps `index.json` costs clean.

## Money Assumption

Current chip/display baseline in ChadJack:
- base unit: `$1.00`
- Perfect Pairs side bet unit: `$1.00`
- 21+3 side bet unit: `$1.00`

If you later support more bet levels in the export package, this matrix can be scaled by multiplier. For now, this document freezes the **mode pattern**, not every denomination ladder.

## Included First-Pass Modes

### Single-hand modes

1. `single_base`
- hands: `1`
- main bets: `1 x base bet`
- side bets: none
- fixed starting cost: `$1.00`
- meaning: single hand, no side bets

2. `single_pp`
- hands: `1`
- main bets: `1 x base bet`
- side bets: `Perfect Pairs` on that hand
- fixed starting cost: `$2.00`
- meaning: single hand plus Perfect Pairs

3. `single_213`
- hands: `1`
- main bets: `1 x base bet`
- side bets: `21+3` on that hand
- fixed starting cost: `$2.00`
- meaning: single hand plus 21+3

4. `single_both`
- hands: `1`
- main bets: `1 x base bet`
- side bets: `Perfect Pairs + 21+3`
- fixed starting cost: `$3.00`
- meaning: single hand plus both side bets

### Two-hand symmetric modes

5. `double_base`
- hands: `2`
- main bets: `2 x base bet`
- side bets: none
- fixed starting cost: `$2.00`
- meaning: two hands, no side bets

6. `double_pp_symmetric`
- hands: `2`
- main bets: `2 x base bet`
- side bets: `Perfect Pairs` on both hands
- fixed starting cost: `$4.00`
- meaning: both hands carry PP, same on each hand

7. `double_213_symmetric`
- hands: `2`
- main bets: `2 x base bet`
- side bets: `21+3` on both hands
- fixed starting cost: `$4.00`
- meaning: both hands carry 21+3, same on each hand

8. `double_both_symmetric`
- hands: `2`
- main bets: `2 x base bet`
- side bets: `Perfect Pairs + 21+3` on both hands
- fixed starting cost: `$6.00`
- meaning: both hands carry both side bets

## Explicitly Excluded For First Approval Pass

These should not be part of the first export matrix unless you choose to expand scope later.

### Excluded asymmetric two-hand modes

Examples:
- hand 1 has PP, hand 2 has none
- hand 1 has 21+3, hand 2 has PP
- hand 1 has both, hand 2 has only one side bet

Reason:
- they explode the mode count
- they complicate fixed-cost bookkeeping
- they are not necessary for a first-pass approval scope

### Excluded autoplay strategy modes

Excluded:
- conservative-specific mode
- optimal-specific mode
- high-stakes-specific mode

Reason:
- autoplay strategy should be treated as a decision policy inside a round model, not a separate starting-cost mode, unless Stake specifically requires otherwise

### Excluded alternate ruleset modes

Excluded:
- different deck-count variants
- different blackjack payout variants
- alternate dealer rules

Reason:
- current submitted product should freeze one ruleset only

## What This Means For Export

The first export pass should target exactly these 8 mode names.

Every one of those modes needs:
- one fixed `cost`
- one export path
- one lookup CSV
- one logic file

The exporter should not generate math for excluded asymmetric combinations unless this document is revised.

## Mid-Round Variable Wagers

These are **not** separate starting modes:
- insurance
- double down
- split

They are round-branch behavior inside the mode’s exported event book.

That means:
- starting cost is fixed by the mode
- extra wager behavior still needs to be represented in event logic and payout normalization

## Recommended `index.json` Direction

The exact schema still depends on the final exporter, but the intended mode names are:

```json
[
  "single_base",
  "single_pp",
  "single_213",
  "single_both",
  "double_base",
  "double_pp_symmetric",
  "double_213_symmetric",
  "double_both_symmetric"
]
```

## Scope Lock

If the live approved build still exposes excluded asymmetric 2-hand side-bet combinations, then one of these must happen before approval:

1. expand this matrix to include them, or
2. constrain the UI/logic so the approved build matches this matrix

## Next Step

After this file, the next required artifact is:
- `/Users/gerryturnbow/Downloads/comet/submission/CHADJACK_MATH_CONTRACT.md`

That contract should define how insurance, double, split, and autoplay decisions are represented inside these 8 modes.
