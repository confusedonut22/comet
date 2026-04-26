"""
Deterministic Stake-style math export for ChadJack.

Emits reproducible round records, per-mode lookup CSVs, and an index.json
for the frozen first-pass Stake submission matrix. Supports split-capable
rounds including pair splitting with basic strategy, locked split aces,
and no double after split (DAS=False). Compression to .jsonl.zst is only
performed when the optional `zstandard` dependency is installed.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
import subprocess
from collections import Counter
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Optional, Sequence

from engine import (
    BJ_MULTIPLIER,
    MONEY_SCALE,
    Card,
    HandResult,
    HandState,
    RoundState,
    Shoe,
    SideBetType,
    complete_round,
    hand_value,
    is_blackjack,
    is_soft,
)

MODE_MATRIX: List[Dict[str, object]] = [
    {
        "name": "single_base",
        "costUnits": 1,
        "hands": [{}],
    },
    {
        "name": "single_pp",
        "costUnits": 2,
        "hands": [{"perfectPairs": True}],
    },
    {
        "name": "single_213",
        "costUnits": 2,
        "hands": [{"twentyOnePlusThree": True}],
    },
    {
        "name": "single_both",
        "costUnits": 3,
        "hands": [{"perfectPairs": True, "twentyOnePlusThree": True}],
    },
    {
        "name": "double_base",
        "costUnits": 2,
        "hands": [{}, {}],
    },
    {
        "name": "double_pp_symmetric",
        "costUnits": 4,
        "hands": [{"perfectPairs": True}, {"perfectPairs": True}],
    },
    {
        "name": "double_213_symmetric",
        "costUnits": 4,
        "hands": [{"twentyOnePlusThree": True}, {"twentyOnePlusThree": True}],
    },
    {
        "name": "double_both_symmetric",
        "costUnits": 6,
        "hands": [
            {"perfectPairs": True, "twentyOnePlusThree": True},
            {"perfectPairs": True, "twentyOnePlusThree": True},
        ],
    },
]
MODE_LOOKUP = {mode["name"]: mode for mode in MODE_MATRIX}


def card_token(card: Card) -> str:
    return f"{card.rank}{card.suit[0]}"


def serialize_side_bets(side_bets: Mapping[SideBetType, int]) -> Dict[str, int]:
    return {
        "perfectPairs": side_bets.get(SideBetType.PERFECT_PAIRS, 0),
        "twentyOnePlusThree": side_bets.get(SideBetType.TWENTY_ONE_PLUS_THREE, 0),
    }


def serialize_hand(hand: HandState, hand_index: int) -> Dict[str, object]:
    return {
        "handIndex": hand_index,
        "cards": [card_token(card) for card in hand.cards],
        "sideBets": serialize_side_bets(hand.side_bets),
        "isSplitHand": hand.is_split_hand,
    }


def side_bet_config(
    *,
    bet_amount: int,
    perfect_pairs: bool = False,
    twenty_one_plus_three: bool = False,
) -> Dict[SideBetType, int]:
    side_bets: Dict[SideBetType, int] = {}
    if perfect_pairs:
        side_bets[SideBetType.PERFECT_PAIRS] = bet_amount
    if twenty_one_plus_three:
        side_bets[SideBetType.TWENTY_ONE_PLUS_THREE] = bet_amount
    return side_bets


def mode_names() -> List[str]:
    return [str(mode["name"]) for mode in MODE_MATRIX]


def mode_cost_units(mode_name: str) -> int:
    mode = MODE_LOOKUP.get(mode_name)
    if mode is None:
        return 1
    return int(mode["costUnits"])


def hand_configs_for_mode(mode_name: str, *, base_bet: int = MONEY_SCALE) -> List[Dict[str, object]]:
    mode = MODE_LOOKUP.get(mode_name)
    if mode is None:
        raise ValueError(f"Unknown mode: {mode_name}")

    hand_configs: List[Dict[str, object]] = []
    for hand in mode["hands"]:
        hand_spec = dict(hand)
        hand_configs.append(
            {
                "bet": base_bet,
                "side_bets": side_bet_config(
                    bet_amount=base_bet,
                    perfect_pairs=bool(hand_spec.get("perfectPairs")),
                    twenty_one_plus_three=bool(hand_spec.get("twentyOnePlusThree")),
                ),
            }
        )
    return hand_configs


def basic_strategy_action(
    player_cards: List[Card],
    dealer_up_card: Card,
    *,
    allow_split: bool = True,
    allow_double: bool = True,
) -> str:
    dv = dealer_up_card.value
    if dealer_up_card.rank in ("J", "Q", "K"):
        dv = 10

    if allow_split and len(player_cards) == 2 and player_cards[0].rank == player_cards[1].rank:
        pair_rank = player_cards[0].rank

        if pair_rank in ("A", "8"):
            return "split"

        if pair_rank in ("4", "5", "10", "J", "Q", "K"):
            pass
        elif pair_rank in ("2", "3", "6", "7") and 2 <= dv <= 7:
            return "split"
        elif pair_rank == "9" and dv in (2, 3, 4, 5, 6, 8, 9):
            return "split"

    pv = hand_value(player_cards)
    soft = is_soft(player_cards)
    can_double = allow_double and len(player_cards) == 2

    if pv >= 17:
        return "stand"
    if pv <= 8:
        return "hit"

    if soft:
        if pv >= 19:
            return "stand"
        if pv == 18:
            return "hit" if dv >= 9 else "stand"
        return "hit"

    if pv >= 13 and dv <= 6:
        return "stand"
    if pv == 12 and 4 <= dv <= 6:
        return "stand"
    if pv == 11 and can_double:
        return "double"
    if pv == 10 and dv <= 9 and can_double:
        return "double"
    if pv == 9 and 3 <= dv <= 6 and can_double:
        return "double"
    return "hit"


def evaluate_initial_resolution(hand: HandState, dealer_cards: List[Card]) -> None:
    player_bj = is_blackjack(hand.cards)
    dealer_bj = is_blackjack(dealer_cards)

    if player_bj and dealer_bj:
        hand.result = HandResult.PUSH
        hand.payout = hand.bet
    elif player_bj:
        hand.result = HandResult.BLACKJACK
        hand.payout = hand.bet + int(hand.bet * BJ_MULTIPLIER)
    elif dealer_bj:
        hand.result = HandResult.LOSE
        hand.payout = 0


def play_round_record(
    *,
    shoe: Shoe,
    hand_configs: List[Dict[str, object]],
    take_insurance: bool = False,
    mode_name: Optional[str] = None,
) -> Dict[str, object]:
    from engine import deal_round, split_hand as engine_split_hand

    state: RoundState = deal_round(shoe, hand_configs)
    events: List[Dict[str, object]] = []

    events.append(
        {
            "type": "initialDeal",
            "mode": mode_name,
            "dealerUp": card_token(state.dealer_cards[0]),
            "dealerHole": card_token(state.dealer_cards[1]),
            "playerHands": [
                serialize_hand(hand, hand_index)
                for hand_index, hand in enumerate(state.player_hands)
            ],
            "insuranceOffered": state.insurance_offered,
        }
    )

    side_bet_results: List[Dict[str, object]] = []
    for hand_index, hand in enumerate(state.player_hands):
        for result in hand.side_bet_results:
            side_bet_results.append(
                {
                    "handIndex": hand_index,
                    "betType": result.bet_type.value,
                    "won": result.won,
                    "name": result.name,
                    "multiplier": result.multiplier,
                    "payout": result.payout,
                }
            )
    if side_bet_results:
        events.append({"type": "sideBetsResolved", "results": side_bet_results})

    if state.insurance_offered and take_insurance:
        state.insurance_taken = True
        events.append({"type": "insuranceTaken", "amount": state.insurance_amount})

    initial_resolutions: List[Dict[str, object]] = []
    for hand_index, hand in enumerate(state.player_hands):
        evaluate_initial_resolution(hand, state.dealer_cards)
        if hand.result is not None:
            initial_resolutions.append(
                {
                    "handIndex": hand_index,
                    "result": hand.result.value,
                    "payout": hand.payout,
                }
            )
    if initial_resolutions:
        events.append({"type": "initialResolution", "hands": initial_resolutions})

    hand_index = 0
    while hand_index < len(state.player_hands):
        hand = state.player_hands[hand_index]
        if hand.result is not None or hand.from_split_aces:
            hand_index += 1
            continue

        split_created = False
        while hand.result is None:
            action = basic_strategy_action(
                hand.cards,
                state.dealer_cards[0],
                allow_split=not hand.is_split_hand,
                allow_double=not hand.is_split_hand,
            )

            if action == "stand":
                events.append(
                    {
                        "type": "playerAction",
                        "action": "stand",
                        "handIndex": hand_index,
                    }
                )
                break

            if action == "double":
                state.total_wagered += hand.bet
                hand.bet *= 2
                hand.doubled = True
                drawn = shoe.draw()
                hand.cards.append(drawn)
                events.append(
                    {
                        "type": "playerAction",
                        "action": "double",
                        "handIndex": hand_index,
                        "card": card_token(drawn),
                        "value": hand_value(hand.cards),
                    }
                )
                if hand_value(hand.cards) > 21:
                    hand.result = HandResult.BUST
                    hand.payout = 0
                break

            if action == "split":
                success, split_hands = engine_split_hand(state, hand_index, shoe)
                if not success:
                    action = "hit"
                else:
                    events.append(
                        {
                            "type": "playerAction",
                            "action": "split",
                            "handIndex": hand_index,
                            "splitAces": hand.cards[0].rank == "A",
                            "hands": [
                                {
                                    "handIndex": hand_index + offset,
                                    "cards": [card_token(card) for card in split_hand.cards],
                                }
                                for offset, split_hand in enumerate(split_hands)
                            ],
                        }
                    )
                    split_created = True
                    break

            drawn = shoe.draw()
            hand.cards.append(drawn)
            events.append(
                {
                    "type": "playerAction",
                    "action": "hit",
                    "handIndex": hand_index,
                    "card": card_token(drawn),
                    "value": hand_value(hand.cards),
                }
            )
            if hand_value(hand.cards) > 21:
                hand.result = HandResult.BUST
                hand.payout = 0
                break

        if split_created:
            continue
        hand_index += 1

    state = complete_round(state, shoe)

    events.append(
        {
            "type": "dealerFinal",
            "cards": [card_token(card) for card in state.dealer_cards],
            "value": hand_value(state.dealer_cards),
        }
    )

    events.append(
        {
            "type": "roundSettlement",
            "hands": [
                {
                    "handIndex": index,
                    "handResult": hand.result.value if hand.result else None,
                    "handPayout": hand.payout,
                    "isSplitHand": hand.is_split_hand,
                }
                for index, hand in enumerate(state.player_hands)
            ],
            "totalWagered": state.total_wagered,
            "totalReturned": state.total_returned,
            "insuranceTaken": state.insurance_taken,
        }
    )

    payout_multiplier_float = (
        state.total_returned / state.total_wagered
        if state.total_wagered > 0
        else 0.0
    )
    # Spec requires uint64 integer — store as multiplier × 100 (e.g. 2.5x → 250)
    payout_multiplier = int(round(payout_multiplier_float * 100))

    return {
        "events": events,
        "payoutMultiplier": payout_multiplier,
        "totalWagered": state.total_wagered,
        "totalReturned": state.total_returned,
    }


def record_id_for(events: List[Dict[str, object]], payout_multiplier: float) -> str:
    payload = json.dumps(
        {"events": events, "payoutMultiplier": payout_multiplier},
        separators=(",", ":"),
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def simulate_bundle(
    *,
    rounds: int,
    seed: int,
    base_bet: int = MONEY_SCALE,
    perfect_pairs_bet: int = 0,
    twenty_one_plus_three_bet: int = 0,
    take_insurance: bool = False,
    mode_name: Optional[str] = None,
) -> List[Dict[str, object]]:
    import random

    rng = random.Random(seed)
    shoe = Shoe(rng=rng)
    records: List[Dict[str, object]] = []

    if mode_name is not None:
        hand_configs = hand_configs_for_mode(mode_name, base_bet=base_bet)
    else:
        hand_configs = [
            {
                "bet": base_bet,
                "side_bets": side_bet_config(
                    bet_amount=base_bet,
                    perfect_pairs=perfect_pairs_bet > 0,
                    twenty_one_plus_three=twenty_one_plus_three_bet > 0,
                ),
            }
        ]

    for _ in range(rounds):
        record = play_round_record(
            shoe=shoe,
            hand_configs=hand_configs,
            take_insurance=take_insurance,
            mode_name=mode_name,
        )
        record["id"] = record_id_for(record["events"], float(record["payoutMultiplier"]))
        records.append(record)

    return records


def simulate_mode_bundles(
    *,
    rounds: int,
    seed: int,
    base_bet: int = MONEY_SCALE,
    take_insurance: bool = False,
    mode_selection: Optional[Sequence[str]] = None,
) -> Dict[str, List[Dict[str, object]]]:
    selected_mode_names = list(mode_selection) if mode_selection else mode_names()
    unknown_modes = [mode for mode in selected_mode_names if mode not in MODE_LOOKUP]
    if unknown_modes:
        raise ValueError(f"Unknown mode(s): {', '.join(unknown_modes)}")

    bundles: Dict[str, List[Dict[str, object]]] = {}
    for index, selected_mode in enumerate(selected_mode_names):
        mode_seed = seed + (index * 100_003)
        bundles[selected_mode] = simulate_bundle(
            rounds=rounds,
            seed=mode_seed,
            base_bet=base_bet,
            take_insurance=take_insurance,
            mode_name=selected_mode,
        )
    return bundles


def collapse_records(records: Iterable[Dict[str, object]]) -> List[Dict[str, object]]:
    records_list = list(records)
    weights = Counter(str(record["id"]) for record in records_list)
    total_rounds = sum(weights.values())

    unique: Dict[str, Dict[str, object]] = {}
    for record in records_list:
        unique.setdefault(str(record["id"]), record)

    collapsed: List[Dict[str, object]] = []
    for simulation_number, record_id in enumerate(sorted(unique.keys()), start=1):
        record = unique[record_id]
        probability = weights[record_id] / total_rounds if total_rounds > 0 else 0.0
        collapsed.append(
            {
                "id": simulation_number,
                "recordId": record_id,
                "events": record["events"],
                "payoutMultiplier": record["payoutMultiplier"],
                "probability": round(probability, 10),
                "totalWagered": record["totalWagered"],
                "totalReturned": record["totalReturned"],
            }
        )
    return collapsed


def compress_bundle_jsonl(base_jsonl: Path, compressed_path: Path) -> str:
    try:
        import zstandard  # type: ignore

        compressor = zstandard.ZstdCompressor(level=10)
        with base_jsonl.open("rb") as src, compressed_path.open("wb") as dst:
            dst.write(compressor.compress(src.read()))
        return "native-zstandard"
    except Exception as native_exc:
        helper_python = Path(__file__).resolve().parent / ".venv-zstd" / "bin" / "python"
        if helper_python.exists():
            script = (
                "from pathlib import Path\n"
                "import sys\n"
                "import zstandard as zstd\n"
                "src = Path(sys.argv[1])\n"
                "dst = Path(sys.argv[2])\n"
                "cctx = zstd.ZstdCompressor(level=10)\n"
                "with src.open('rb') as fin, dst.open('wb') as fout:\n"
                "    cctx.copy_stream(fin, fout)\n"
            )
            try:
                subprocess.run(
                    [str(helper_python), "-c", script, str(base_jsonl), str(compressed_path)],
                    check=True,
                    capture_output=True,
                    text=True,
                )
                return "local-zstandard-helper"
            except Exception:
                pass
        zstd_cli = shutil.which("zstd")
        if zstd_cli:
            try:
                subprocess.run(
                    [zstd_cli, "-q", "-f", "-19", str(base_jsonl), "-o", str(compressed_path)],
                    check=True,
                    capture_output=True,
                    text=True,
                )
                return "zstd-cli"
            except Exception:
                pass
        raise native_exc


def write_bundle(
    out_dir: Path,
    records_or_modes: Mapping[str, List[Dict[str, object]]] | List[Dict[str, object]],
) -> Dict[str, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)

    if isinstance(records_or_modes, list):
        records_by_mode: Dict[str, List[Dict[str, object]]] = {"base": records_or_modes}
    else:
        records_by_mode = dict(records_or_modes)

    mode_entries: List[Dict[str, object]] = []
    compression_lines: List[str] = []

    for mode_name in sorted(records_by_mode.keys()):
        collapsed = collapse_records(records_by_mode[mode_name])

        jsonl_path = out_dir / f"{mode_name}.jsonl"
        with jsonl_path.open("w", encoding="utf-8") as handle:
            for record in collapsed:
                json.dump(
                    {
                        "id": record["id"],
                        "events": record["events"],
                        # Spec: integer uint64 (multiplier × 100, e.g. 2.5x → 250)
                        "payoutMultiplier": int(record["payoutMultiplier"]),
                    },
                    handle,
                    separators=(",", ":"),
                )
                handle.write("\n")

        csv_path = out_dir / f"{mode_name}.csv"
        with csv_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            # Spec: no header row, all uint64 values
            # probability scaled by 10^12 → integer weight; payoutMultiplier must exactly match JSONL
            for record in collapsed:
                prob_uint64 = int(round(float(record["probability"]) * 10**12))
                writer.writerow([record["id"], prob_uint64, int(record["payoutMultiplier"])])

        logic_filename = f"{mode_name}.jsonl.zst"
        try:
            compressed_path = out_dir / logic_filename
            method = compress_bundle_jsonl(jsonl_path, compressed_path)
            compression_lines.append(f"{mode_name}: {logic_filename} via {method}")
        except Exception as exc:
            logic_filename = f"{mode_name}.jsonl"
            compression_lines.append(
                f"{mode_name}: compression fallback used, serving {logic_filename} ({type(exc).__name__}: {exc})"
            )

        mode_entries.append(
            {
                "name": mode_name,
                # Spec: float cost multiplier
                "cost": float(mode_cost_units(mode_name)),
                # Spec: field names must be "weights" and "events"
                "weights": csv_path.name,
                "events": logic_filename,
            }
        )

    index_json = out_dir / "index.json"
    index_json.write_text(
        json.dumps(
            # Spec: strictly enforced form — only "modes" array with name/cost/events/weights
            {"modes": mode_entries},
            indent=2,
        ),
        encoding="utf-8",
    )

    compression_note = out_dir / "compression.txt"
    compression_note.write_text("\n".join(compression_lines) + "\n", encoding="utf-8")

    return {
        "index": index_json,
        "compression_note": compression_note,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Emit a deterministic Stake-style ChadJack math bundle.")
    parser.add_argument("--rounds", type=int, default=5000)
    parser.add_argument("--seed", type=int, default=1337)
    parser.add_argument("--out-dir", default="library/publish_files")
    parser.add_argument("--base-bet", type=int, default=MONEY_SCALE)
    parser.add_argument("--take-insurance", action="store_true")
    parser.add_argument(
        "--mode",
        action="append",
        choices=mode_names(),
        dest="modes",
        help="Optional repeatable filter to export only specific frozen modes.",
    )
    args = parser.parse_args()

    records = simulate_mode_bundles(
        rounds=args.rounds,
        seed=args.seed,
        base_bet=args.base_bet,
        take_insurance=args.take_insurance,
        mode_selection=args.modes,
    )
    written = write_bundle(Path(args.out_dir), records)
    print(json.dumps({key: str(value) for key, value in written.items()}, indent=2))


if __name__ == "__main__":
    main()
