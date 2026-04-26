import test from "node:test";
import assert from "node:assert/strict";

import { makeShoe } from "../src/game/engine.js";
import {
  getInsuranceAmount,
  settleImmediateHands,
  settleDealerHands,
} from "../src/game/roundSettlement.js";

const makeCard = (rank, suit) => ({ rank, suit });

const makeHand = ({ cards, bet, sb = { pp: 0, t: 0 }, result = null, message = "", payout = 0, done = false, doubled = false, isSplit = false, isAceSplit = false }) => ({
  cards,
  bet,
  sb,
  result,
  message,
  payout,
  done,
  doubled,
  isSplit,
  isAceSplit,
  sideBetResults: [],
});

function seededRng(seed) {
  let state = seed >>> 0;
  return () => {
    state = (1664525 * state + 1013904223) >>> 0;
    return state / 2 ** 32;
  };
}

test("insurance is half of the total main wager", () => {
  assert.equal(getInsuranceAmount(2_000_000), 1_000_000);
  assert.equal(getInsuranceAmount(1_500_000), 750_000);
});

test("immediate settlement resolves blackjack, side bets, and dealer blackjack loss", () => {
  const hands = [
    makeHand({
      cards: [makeCard("A", "hearts"), makeCard("A", "hearts")],
      bet: 2_000_000,
      sb: { pp: 100_000, t: 100_000 },
    }),
  ];
  const dealerCards = [makeCard("K", "spades"), makeCard("A", "clubs")];

  const settled = settleImmediateHands(hands, dealerCards);

  assert.equal(settled.dealerBJ, true);
  assert.equal(settled.hands[0].result, "lose");
  assert.equal(settled.hands[0].message, "Dealer BJ");
  assert.equal(settled.hands[0].payout, 0);
  assert.equal(settled.sideBetPayout, 2_500_000);
  assert.equal(settled.immediatePayout, 0);
  assert.equal(settled.hands[0].sideBetResults.length, 2);
  assert.equal(settled.hands[0].sideBetResults[0].won, false);
  assert.equal(settled.hands[0].sideBetResults[1].name, "Perfect Pair");
});

test("side bet helpers use listed profit-only payout tables", () => {
  const hands = [
    makeHand({
      cards: [makeCard("7", "hearts"), makeCard("7", "diamonds")],
      bet: 1_000_000,
      sb: { pp: 100_000, t: 100_000 },
    }),
  ];
  const dealerCards = [makeCard("7", "clubs"), makeCard("9", "spades")];

  const settled = settleImmediateHands(hands, dealerCards);

  assert.equal(settled.sideBetPayout, 4_200_000);
  assert.deepEqual(
    settled.hands[0].sideBetResults.map((result) => result.payout),
    [3_000_000, 1_200_000],
  );
});

test("21+3 counts ace as high for Q-K-A straights", () => {
  const hands = [
    makeHand({
      cards: [makeCard("Q", "spades"), makeCard("K", "hearts")],
      bet: 1_000_000,
      sb: { t: 100_000 },
    }),
  ];
  const dealerCards = [makeCard("A", "diamonds"), makeCard("5", "clubs")];

  const settled = settleImmediateHands(hands, dealerCards);

  assert.equal(settled.sideBetPayout, 1_000_000);
  assert.equal(settled.hands[0].sideBetResults[0].name, "Straight");
});

test("immediate settlement pays blackjack at 3:2", () => {
  const hands = [
    makeHand({
      cards: [makeCard("A", "spades"), makeCard("K", "hearts")],
      bet: 1_000_000,
    }),
  ];
  const dealerCards = [makeCard("9", "clubs"), makeCard("7", "diamonds")];

  const settled = settleImmediateHands(hands, dealerCards);

  assert.equal(settled.dealerBJ, false);
  assert.equal(settled.hands[0].result, "blackjack");
  assert.equal(settled.hands[0].payout, 2_500_000);
  assert.equal(settled.immediatePayout, 2_500_000);
});

test("ace-split hand reaching 21 pays 1:1, not 3:2 (no blackjack on splits)", () => {
  // Ace split: player has A + K (2 cards, value 21) but it's a split hand
  // Should pay 1:1 (win), NOT 3:2 (blackjack)
  const hands = [
    makeHand({
      cards: [makeCard("A", "spades"), makeCard("K", "hearts")],
      bet: 1_000_000,
      isAceSplit: true,
      done: true, // ace splits are marked done immediately after card is dealt
    }),
  ];
  const dealerCards = [makeCard("7", "clubs"), makeCard("9", "diamonds")]; // dealer 16 → bust scenario handled by dealer rules elsewhere

  const settled = settleDealerHands(hands, dealerCards);

  assert.equal(settled.hands[0].result, "win");
  assert.equal(settled.hands[0].payout, 2_000_000); // 1:1, not 2_500_000 (3:2)
});

test("regular split hand reaching 21 pays 1:1, not 3:2", () => {
  // e.g. split 10s, one hand draws an A making 21 with 2 cards — still not blackjack
  const hands = [
    makeHand({
      cards: [makeCard("10", "spades"), makeCard("A", "hearts")],
      bet: 1_000_000,
      isSplit: true,
    }),
  ];
  const dealerCards = [makeCard("8", "clubs"), makeCard("9", "diamonds")];

  const settled = settleDealerHands(hands, dealerCards);

  assert.equal(settled.hands[0].result, "win");
  assert.equal(settled.hands[0].payout, 2_000_000); // 1:1, not 2_500_000
});

test("dealer resolution uses deterministic shuffle-ready math helpers", () => {
  const shoeA = makeShoe(1, seededRng(1234));
  const shoeB = makeShoe(1, seededRng(1234));

  assert.deepEqual(shoeA, shoeB);

  const hands = [
    makeHand({
      cards: [makeCard("10", "hearts"), makeCard("9", "clubs")],
      bet: 1_000_000,
    }),
  ];
  const dealerCards = [makeCard("10", "spades"), makeCard("8", "diamonds"), makeCard("4", "clubs")];

  const settled = settleDealerHands(hands, dealerCards);

  assert.equal(settled.hands[0].result, "win");
  assert.equal(settled.hands[0].payout, 2_000_000);
  assert.equal(settled.payout, 2_000_000);
});
