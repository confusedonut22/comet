import json
import pathlib
import shutil
import tempfile
import unittest
import csv

ROOT = pathlib.Path(__file__).resolve().parents[1]
import sys

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine import Card, MONEY_SCALE, Shoe, HandState, resolve_hand_state, evaluate_21_plus_3, evaluate_perfect_pairs
from exact_sidebet_math import perfect_pairs_stats, twenty_one_plus_three_stats
from stake_export import mode_names, simulate_bundle, simulate_mode_bundles, write_bundle


class MathReadinessTests(unittest.TestCase):
    def test_perfect_pairs_uses_profit_only_payout_table(self):
        result = evaluate_perfect_pairs(
            Card(rank="9", suit="hearts"),
            Card(rank="9", suit="diamonds"),
            100_000,
        )
        self.assertTrue(result.won)
        self.assertEqual(result.multiplier, 12)
        self.assertEqual(result.payout, 1_200_000)

    def test_twenty_one_plus_three_uses_profit_only_payout_table(self):
        result = evaluate_21_plus_3(
            Card(rank="7", suit="hearts"),
            Card(rank="7", suit="diamonds"),
            Card(rank="7", suit="clubs"),
            100_000,
        )
        self.assertTrue(result.won)
        self.assertEqual(result.multiplier, 30)
        self.assertEqual(result.payout, 3_000_000)

    def test_twenty_one_plus_three_treats_ace_as_high_for_straights(self):
        result = evaluate_21_plus_3(
            Card(rank="Q", suit="hearts"),
            Card(rank="K", suit="diamonds"),
            Card(rank="A", suit="clubs"),
            100_000,
        )
        self.assertTrue(result.won)
        self.assertEqual(result.name, "Straight")
        self.assertEqual(result.payout, 1_000_000)

    def test_seeded_shoe_is_deterministic(self):
        import random

        shoe_a = Shoe(rng=random.Random(42))
        shoe_b = Shoe(rng=random.Random(42))
        first_a = [repr(shoe_a.draw()) for _ in range(10)]
        first_b = [repr(shoe_b.draw()) for _ in range(10)]
        self.assertEqual(first_a, first_b)

    def test_simulation_bundle_is_reproducible(self):
        records_a = simulate_mode_bundles(rounds=25, seed=123)
        records_b = simulate_mode_bundles(rounds=25, seed=123)
        summary_a = {
            mode_name: [(record["id"], record["payoutMultiplier"]) for record in records]
            for mode_name, records in records_a.items()
        }
        summary_b = {
            mode_name: [(record["id"], record["payoutMultiplier"]) for record in records]
            for mode_name, records in records_b.items()
        }
        self.assertEqual(summary_a, summary_b)

    def test_write_bundle_emits_expected_files(self):
        records = simulate_mode_bundles(rounds=10, seed=77)
        temp_dir = pathlib.Path(tempfile.mkdtemp(prefix="stake-export-"))
        try:
            written = write_bundle(temp_dir, records)
            self.assertTrue(written["index"].exists())
            index_payload = json.loads(written["index"].read_text(encoding="utf-8"))
            self.assertFalse(index_payload["draft"])  # submission-ready: draft=false
            self.assertEqual([mode["name"] for mode in index_payload["modes"]], sorted(mode_names()))
            self.assertEqual(
                {mode["name"]: mode["cost"] for mode in index_payload["modes"]},
                {
                    "double_213_symmetric": 4,
                    "double_base": 2,
                    "double_both_symmetric": 6,
                    "double_pp_symmetric": 4,
                    "single_213": 2,
                    "single_base": 1,
                    "single_both": 3,
                    "single_pp": 2,
                },
            )
            self.assertTrue(any("split support" in note.lower() for note in index_payload["notes"]))
            self.assertTrue(any("frozen 8-mode" in note.lower() for note in index_payload["notes"]))
            self.assertTrue((temp_dir / "single_base.csv").exists())
            self.assertTrue((temp_dir / "single_base.jsonl").exists())
            self.assertTrue((temp_dir / "double_both_symmetric.csv").exists())
            with (temp_dir / "single_base.csv").open(encoding="utf-8") as handle:
                rows = list(csv.reader(handle))
            self.assertEqual(rows[0], ["simulation_number", "round_probability", "payout_multiplier"])
        finally:
            shutil.rmtree(temp_dir)

    def test_double_mode_initial_deal_contains_two_hands(self):
        records = simulate_bundle(rounds=1, seed=99, mode_name="double_base")
        initial_deal = records[0]["events"][0]
        self.assertEqual(initial_deal["type"], "initialDeal")
        self.assertEqual(len(initial_deal["playerHands"]), 2)

    def test_exact_perfect_pairs_rtp(self):
        stats = perfect_pairs_stats()
        self.assertEqual(stats["categories"]["Perfect Pair"], 780)
        self.assertEqual(stats["categories"]["Coloured Pair"], 936)
        self.assertEqual(stats["categories"]["Mixed Pair"], 1872)
        self.assertAlmostEqual(stats["rtp"] * 100, 86.49517684887459, places=10)

    def test_exact_twenty_one_plus_three_rtp(self):
        stats = twenty_one_plus_three_stats()
        self.assertEqual(stats["categories"]["Suited Trips"], 1040)
        self.assertEqual(stats["categories"]["Straight Flush"], 10368)
        self.assertEqual(stats["categories"]["Three of a Kind"], 25272)
        self.assertEqual(stats["categories"]["Straight"], 155520)
        self.assertEqual(stats["categories"]["Flush"], 292896)
        self.assertAlmostEqual(stats["rtp"] * 100, 85.70288750767953, places=10)

    def test_split_hand_twenty_one_is_not_blackjack_in_math_engine(self):
        hand = HandState(
            cards=[Card(rank="A", suit="hearts"), Card(rank="K", suit="clubs")],
            bet=MONEY_SCALE,
            is_split_hand=True,
            counts_as_blackjack=False,
        )
        dealer_cards = [Card(rank="10", suit="spades"), Card(rank="7", suit="diamonds")]
        result, payout = resolve_hand_state(hand, dealer_cards)
        self.assertEqual(result.value, "win")
        self.assertEqual(payout, MONEY_SCALE * 2)


if __name__ == "__main__":
    unittest.main()
