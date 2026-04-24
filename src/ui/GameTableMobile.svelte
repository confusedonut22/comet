<script>
  import { onMount, onDestroy, afterUpdate } from "svelte";
  import { get } from "svelte/store";
  import {
    phase, balance, dealerHand, hands, activeHand, message, pending,
    numSlots, maxHands, autoPlay, autoSpeed, autoCount, autoMax, autoMode,
    showAuto, showRules, totalCost, canDeal, introOp, rgsStatus, rgsError, runtimeConfig, runtimeJurisdiction,
    sessionStartedAt, netPosition, runtimeCurrency, autoBetEnabled, sideBetsEnabled,
    startIntro, addSlot, removeSlot, addSideBetChip, clearSideBet, setSideBetAmount, addChip, clearBet, setBetLevel, adjustBetByFactor,
    newRound, deal, hit, stand, doubleDown, split, takeInsurance, autoTick, refreshStakeBalance,
  } from "../game/store.js";
  import { PHASE, SPEEDS, MONEY_SCALE, CHIPS, CHIP_IMAGES, LOGO_IMAGE, CARD_BACK_IMAGE, C } from "../game/constants.js";
  import { handValue, isSoft } from "../game/engine.js";
  import { launchWarnings, replayMode, sessionQuery } from "../game/session.js";
  import { sessionBootstrap } from "../game/bootstrap.js";
  import { formatCurrencyAmount, formatSessionDuration, formatSignedMoney } from "../game/sessionDisplay.js";
  import { toggleMute, isMuted, setMuted } from "../game/audio.js";
  import INTRO_VIDEO from "../assets/chad_labs_intro_powergrid_v7.mp4";
  import INTRO_VIDEO_MOBILE from "../assets/chad_labs_intro_powergrid_v7_mobile.mp4";
  import AUTOPLAY_BUTTON from "../assets/autoplaybutton.png";
  import JACK_SPADES_CHADJACK from "../assets/custom-face-cards/jack-spades-chadjack.png";
  import JACK_HEARTS_CHADJACK from "../assets/custom-face-cards/jack-hearts-chadjack.png";
  import JACK_CLUBS_CHADJACK from "../assets/custom-face-cards/jack-clubs-chadjack.png";
  import JACK_DIAMONDS_CHADJACK from "../assets/custom-face-cards/jack-diamonds-chadjack.png";

  /*
    LAYOUT FREEZE RULE — DO NOT MOVE ANY GEOMETRY

    User lock in force for the entire mobile blackjack layout:
    - Nothing on any screen may move unless the user explicitly unlocks that exact element.
    - All player decks are frozen.
    - All dealer decks are frozen.
    - All wager bars are frozen.
    - All count bubbles are frozen.
    - All sidebets are frozen.
    - All player and dealer layout lanes are frozen.
    - Screen 1, screen 2, and screen 3 are all frozen.

    Any future change must treat layout movement as prohibited by default.
  */

  // ─── FORMAT ───
  const AUTO_MODES = [
    {
      key: "conservative",
      label: "Conservative",
      summary: "Protects bankroll by minimizing doubles and leaning toward lower-variance stands.",
    },
    {
      key: "optimal",
      label: "Optimal",
      summary: "Uses mathematically correct basic strategy for the current rule set.",
    },
    {
      key: "high-stakes",
      label: "High Roller",
      summary: "Pushes more aggressive doubles and pressure spots for bigger swings.",
    },
  ];
  const FELT_THEMES = [
    { key: "velvet-black", label: "Black Velvet" },
    { key: "velvet-blue", label: "Blue Velvet" },
    { key: "velvet-green", label: "Green Velvet" },
    { key: "ridge-black", label: "Black Ridge" },
    { key: "ridge-blue", label: "Blue Ridge" },
    { key: "ridge-green", label: "Green Ridge" },
    { key: "felt-black", label: "Felt Black" },
    { key: "felt-blue", label: "Felt Blue" },
    { key: "felt-green", label: "Felt Green" },
  ];
  const FELT_THEME_STORAGE_KEY = "chadjack.feltTheme";
  const TEXTURE_ROWS = [
    {
      textureKey: "felt",
      textureLabel: "Felt",
      options: [{ key: "felt-green" }, { key: "felt-blue" }, { key: "felt-black" }],
    },
    {
      textureKey: "velvet",
      textureLabel: "Velvet",
      options: [{ key: "velvet-green" }, { key: "velvet-blue" }, { key: "velvet-black" }],
    },
    {
      textureKey: "ridge",
      textureLabel: "Ridge",
      options: [{ key: "ridge-green" }, { key: "ridge-blue" }, { key: "ridge-black" }],
    },
  ];

  function normalizeSocialCurrency(currency) {
    const normalized = String(currency || "").trim().toUpperCase();
    if (normalized === "SC" || normalized === "STAKE CASH" || normalized === "STAKE_CASH" || normalized === "SWEEP COINS") return "SC";
    return "GC";
  }

  const fmt = (v, currency = "USD") => formatCurrencyAmount(v, currency, MONEY_SCALE);
  const fmtVal = (cards) => {
    if (!cards?.length) return "";
    const v = handValue(cards);
    const soft = isSoft(cards) && v <= 21;
    if (soft) return `${v - 10}/${v}`;
    return v;
  };

  function detectPortraitLockedMobile() {
    if (typeof window === "undefined" || typeof navigator === "undefined") return false;
    const ua = navigator.userAgent || "";
    const isMobileUa = /Android|iPhone|iPod|Mobile/i.test(ua);
    const hasCoarsePointer = window.matchMedia?.("(pointer: coarse)")?.matches ?? navigator.maxTouchPoints > 0;
    return isMobileUa && hasCoarsePointer;
  }

  // ─── RESPONSIVE ───
  let windowWidth = 500;
  let windowHeight = 900;
  let forceMobilePortrait = false;
  $: {
    windowWidth;
    windowHeight;
    forceMobilePortrait = detectPortraitLockedMobile();
  }
  $: isDesktop = windowWidth >= 768 && !forceMobilePortrait;
  $: isMobileLandscape = forceMobilePortrait && windowWidth > windowHeight;
  $: introVideoSrc = isDesktop ? INTRO_VIDEO : INTRO_VIDEO_MOBILE;
  $: isWideDesktop = windowWidth >= 1280;
  $: {
    maxHands.set(2);
  }

  // ─── COMPUTED ───
  $: isBet    = $phase === PHASE.BET;
  $: isPlay   = $phase === PHASE.PLAY;
  $: isDealer = $phase === PHASE.DEALER;
  $: isResult = $phase === PHASE.RESULT;
  $: isIns    = $phase === PHASE.INS;
  $: locked   = !isBet;
  $: dealerVal = $dealerHand.length ? handValue($dealerHand) : 0;
  $: dealerSoft = $dealerHand.length >= 2 && !(isPlay || isIns) && isSoft($dealerHand) && dealerVal <= 21;
  $: dealerDisplay = (isPlay || isIns)
    ? handValue([$dealerHand[0]])
    : (dealerVal === 21 && $dealerHand.length === 2 ? 21 : (dealerSoft ? `${dealerVal - 10}/${dealerVal}` : dealerVal));
  $: multi = $numSlots > 1;
  $: activeH = $activeHand >= 0 ? $hands[$activeHand] : null;
  $: isReplay = $replayMode;
  $: isSocial = $sessionQuery.social || $runtimeJurisdiction?.socialCasino === true;
  $: autoplayDisabled = $runtimeJurisdiction?.disabledAutoplay === true;
  $: showMobileAutoplay = $autoBetEnabled && !autoplayDisabled && (isBet || isResult);
  $: showRtp = $runtimeJurisdiction?.displayRTP !== false;
  $: availableSpeeds = Object.entries(SPEEDS).filter(([k]) => {
    if (k === '5x' && $runtimeJurisdiction?.disabledTurbo) return false;
    if (k === 'Max' && $runtimeJurisdiction?.disabledSuperTurbo) return false;
    return true;
  });
  $: {
    // If current speed is no longer allowed, reset to fastest permitted
    const allowedKeys = availableSpeeds.map(([k]) => k);
    if (!allowedKeys.includes($autoSpeed) && allowedKeys.length > 0) {
      autoSpeed.set(allowedKeys[allowedKeys.length - 1]);
    }
  }
  let nowMs = Date.now();
  let sessionClock = null;
  let hideBetLogoDuringRedeal = false;
  $: showSessionTimer = $runtimeJurisdiction?.displaySessionTimer === true && Number.isInteger($sessionStartedAt) && !isReplay;
  $: showNetPosition = $runtimeJurisdiction?.displayNetPosition === true && !isReplay;
  $: displayCurrency = isSocial ? normalizeSocialCurrency($runtimeCurrency) : $runtimeCurrency;
  $: sessionElapsed = showSessionTimer ? formatSessionDuration(nowMs - $sessionStartedAt) : "00:00";
  $: sessionNet = formatSignedMoney($netPosition, MONEY_SCALE, displayCurrency);
  $: netPositive = $netPosition > 0;
  $: netNegative = $netPosition < 0;

  // ─── RESPONSIVE INLINE STYLE VALUES ───
  $: cardOverlap      = isDesktop ? (isWideDesktop ? '-41px' : '-46px') : '-18px';
  $: cardOverlapSmall = isDesktop ? (isWideDesktop ? '-55px' : '-57px') : '-13px';
  $: dealerOverlap    = isDesktop ? (isWideDesktop ? '-21px' : '-26px') : '-18px';
  $: isFour = $numSlots === 4;
  $: cardsRowMinH     = isDesktop ? (isFour ? 71 : (multi ? (isWideDesktop ? 117 : 138) : (isWideDesktop ? 149 : 176))) : (isFour ? 80 : (multi ? 113 : 146));
  $: handColMaxW      = isDesktop ? (multi ? (isWideDesktop ? '325px' : '390px') : (isWideDesktop ? '507px' : '598px')) : (multi ? '260px' : '416px');
  $: canDouble = (() => {
    if (!activeH || activeH.cards.length !== 2 || $balance < activeH.bet) return false;
    if (activeH.doubled) return false;
    if (activeH.isSplit || activeH.isAceSplit) return false;
    const total = handValue(activeH.cards);
    const soft = isSoft(activeH.cards);
    if (soft) return false;
    return total === 9 || total === 10 || total === 11;
  })();
  $: canSplit  = activeH
    && !activeH.isSplit
    && !activeH.isAceSplit
    && activeH.cards.length === 2
    && $balance >= activeH.bet
    && $hands.length < 6
    && activeH.cards[0].rank === activeH.cards[1].rank;
  $: isBadBeat = isResult && $message;
  $: dealLabel = $autoPlay ? `Auto ${$autoCount}/${$autoMax}` : isDealer ? "Dealing..." : isIns ? "Insurance..." : isResult ? "Next Hand" : "Deal";
  $: tableControlMode = isDesktop && !isPlay ? 'table' : 'footer';

  // ─── ACTIONS ───
  function onDeal() {
    if (isResult) {
      hideBetLogoDuringRedeal = true;
      newRound();
      Promise.resolve(deal()).finally(() => {
        hideBetLogoDuringRedeal = false;
      });
    } else if (isBet) {
      deal();
    }
  }

  function toggleAuto() {
    if (autoplayDisabled) return;
    if ($autoPlay) {
      autoPlay.set(false);
    } else {
      showAuto.set(false); // close the panel immediately
      autoCount.set(0);
      autoPlay.set(true);
      if (isResult || isBet) autoTick(); // kick off immediately
    }
  }

  function resultColor(result) {
    if (result === "win" || result === "blackjack") return "#66ff88";
    if (result === "push") return C.cd;
    return C.rd;
  }

  function handMsg(h) {
    const v = handValue(h.cards);
    if (v === 21 && h.cards?.length === 2) return 21;
    if (isSoft(h.cards) && v <= 21) return `${v - 10}/${v}`;
    return v;
  }

  function mobileResultLabel(message) {
    if (message === "You Win!") return "PLAYER";
    if (message === "Dealer Wins") return "DEALER";
    if (message === "Push") return "PUSH";
    return message;
  }

  function playerCardMargin(i) {
    if (i === 0) return "0";
    const baseOverlap = Number.parseFloat(multi ? cardOverlapSmall : cardOverlap);
    if (isDesktop || !(isPlay || isResult) || Number.isNaN(baseOverlap)) {
      return i > 0 ? (multi ? cardOverlapSmall : cardOverlap) : "0";
    }
    return "-54px";
  }

  function splitRightCardMargin(i) {
    if (i === 0) return "0";
    const baseOverlap = Number.parseFloat(cardOverlapSmall);
    if (isDesktop || !(isPlay || isResult) || Number.isNaN(baseOverlap)) {
      return `${Math.round(baseOverlap * 0.7)}px`;
    }
    return "-38px";
  }

  function dealerCardMargin(i, cardCount) {
    if (i === 0) return "0";
    if (isDesktop) return dealerOverlap;
    const cardWidth = 92 * 0.9;
    const extraCards = Math.max(0, cardCount - 2);
    const visibleWidth = Math.max(20, Math.min(cardWidth - 12, 32 - extraCards * 2));
    return `-${Math.round((cardWidth - visibleWidth) * 10) / 10}px`;
  }


  function customFaceCardImage(card) {
    if (card?.rank !== "J") return null;
    if (card?.suit === "spades") return JACK_SPADES_CHADJACK;
    if (card?.suit === "hearts") return JACK_HEARTS_CHADJACK;
    if (card?.suit === "clubs") return JACK_CLUBS_CHADJACK;
    if (card?.suit === "diamonds") return JACK_DIAMONDS_CHADJACK;
    return null;
  }

  function groupMobileSplitRows(entries) {
    const rows = [];
    for (let i = 0; i < entries.length; i += 1) {
      const current = entries[i];
      const next = entries[i + 1];
      if (current?.hand.isSplit && next?.hand.isSplit) {
        rows.push([current, next]);
        i += 1;
      } else {
        rows.push([current]);
      }
    }
    return rows;
  }

  $: handEntries = $hands.map((hand, idx) => ({ hand, idx }));
  $: useSplitRows = !isDesktop && handEntries.some(({ hand }) => hand.isSplit);
  $: handRows = [handEntries];
  $: splitRightIdx = (() => {
    let first = true;
    for (const { hand, idx } of handEntries) {
      if (hand.isSplit) {
        if (first) { first = false; continue; }
        return idx;
      }
    }
    return -1;
  })();
  $: if (useSplitRows) console.log('SPLIT DEBUG', { numSlots: $numSlots, splitRightIdx, useSplitRows, hands: handEntries.map(e => ({ idx: e.idx, isSplit: e.hand.isSplit, cards: e.hand.cards.length })) });

  // ─── SIDE BET SELECTION ───
  let sbSelect = {}; // { [handIdx]: "pp" | "t" | null }
  let sbDraft = {};  // { [handIdx+key]: string } — live input value while editing
  let betEntryMode = "amount";
  let betDraft = {};
  $: if (!isBet && !isResult) {
    sbSelect = {};
    sbDraft = {};
    betDraft = {};
  }
  $: if (isPlay) {
    showAuto.set(false); // always close auto panel when play starts
  }

  function toggleSbSelect(idx, key) {
    if (!isBet && !isResult) return;
    const next = sbSelect[idx] === key ? null : key;
    sbSelect = { ...sbSelect, [idx]: next };
    // When opening a sidebet, pre-fill draft with current amount if set
    if (next) {
      const hand = $hands[idx];
      const cur = hand?.sb[next] ?? 0;
      const draftKey = idx + next;
      sbDraft = { ...sbDraft, [draftKey]: cur > 0 ? (cur / MONEY_SCALE).toFixed(2) : '' };
    }
  }

  function onSbDraftInput(idx, key, val) {
    sbDraft = { ...sbDraft, [idx + key]: val };
  }

  function sbFocusInput(node) {
    node.focus();
    node.select();
  }

  function commitSbDraft(idx, key) {
    const draftKey = idx + key;
    const raw = Number.parseFloat(String(sbDraft[draftKey] ?? '').replace(/[^0-9.]/g, ''));
    if (Number.isFinite(raw) && raw > 0) {
      setSideBetAmount(idx, key, Math.round(raw * MONEY_SCALE));
    }
    sbSelect = { ...sbSelect, [idx]: null };
  }

  function onChipClick(idx, value) {
    if (!isBet && !isResult) return;
    const sb = sbSelect[idx];
    if (sb) addSideBetChip(idx, sb, value);
    else if ($runtimeConfig?.betLevels?.length) setBetLevel(idx, value);
    else addChip(idx, value);
  }

  function onClear(idx) {
    const sb = sbSelect[idx];
    const hand = $hands[idx];
    if (sb) {
      clearSideBet(idx, sb);
      return;
    }
    if (hand?.sb?.pp > 0) {
      clearSideBet(idx, 'pp');
      return;
    }
    if (hand?.sb?.t > 0) {
      clearSideBet(idx, 't');
      return;
    }
    clearBet(idx);
  }

  function onBetDraftInput(idx, nextValue) {
    betDraft = { ...betDraft, [idx]: nextValue };
  }

  function commitBetDraft(idx) {
    const raw = Number.parseFloat(String(betDraft[idx] ?? "").replace(/[^0-9.]/g, ""));
    if (!Number.isFinite(raw) || raw <= 0) return;
    const scaled = Math.round(raw * MONEY_SCALE);
    setBetLevel(idx, scaled);
    betDraft = { ...betDraft, [idx]: fmt(scaled, displayCurrency).replace(/[^0-9.]/g, "") };
  }

  let showAbout = false;
  let showFeltPanel = false;
  let showOptionsMenu = false;
  let feltEl;
  let ghostRowEl;
  let fixedAutoplayEl;
  let fixedAutoplayTop = null;
  let soundMuted = false;
  let feltTheme = "felt-green";

  function syncFixedAutoplayPosition() {
    if (typeof window === "undefined" || isDesktop || !showMobileAutoplay || !ghostRowEl || !fixedAutoplayEl) {
      fixedAutoplayTop = null;
      return;
    }
    const ghostEl = ghostRowEl.querySelector(".ghost");
    if (!ghostEl) {
      fixedAutoplayTop = null;
      return;
    }
    const ghostBox = ghostEl.getBoundingClientRect();
    const autoBox = fixedAutoplayEl.getBoundingClientRect();
    fixedAutoplayTop = Math.round(((ghostBox.top + ghostBox.bottom) / 2) - (autoBox.height / 2));
  }

  function onToggleMute(event) {
    event?.stopPropagation?.();
    soundMuted = toggleMute();
  }

  function closePanels() {
    if ($showAuto) showAuto.set(false);
    if ($showRules) showRules.set(false);
    if (showAbout) showAbout = false;
    showFeltPanel = false;
    showOptionsMenu = false;
  }

  function toggleAbout(event) {
    event?.stopPropagation?.();
    showAbout = !showAbout;
    showAuto.set(false);
    showRules.set(false);
    showFeltPanel = false;
    showOptionsMenu = true;
  }

  function applyFeltTheme(themeKey) {
    feltTheme = themeKey;
    if (typeof window !== "undefined") {
      window.localStorage.setItem(FELT_THEME_STORAGE_KEY, themeKey);
    }
  }

  function toggleFeltPanel(event) {
    event?.stopPropagation?.();
    showFeltPanel = !showFeltPanel;
    showAuto.set(false);
    showRules.set(false);
    showAbout = false;
    showOptionsMenu = true;
  }

  // ─── PER-HAND INSURANCE ───
  let insSelect = {};
  $: if (!isIns) insSelect = {};

  function toggleInsHand(idx) {
    insSelect = { ...insSelect, [idx]: !insSelect[idx] };
  }

  function toggleInsAll() {
    const allOn = $hands.every((_, i) => insSelect[i]);
    insSelect = Object.fromEntries($hands.map((_, i) => [i, !allOn]));
  }

  function confirmInsurance() {
    const anySelected = $hands.some((_, i) => insSelect[i]);
    if (!anySelected) { takeInsurance(false); return; }
    const amt = $hands.reduce((sum, h, i) => insSelect[i] ? sum + Math.floor(h.bet / 2) : sum, 0);
    takeInsurance(true, amt > 0 ? amt : null);
  }

  function toggleAutoPanel(event) {
    event?.stopPropagation?.();
    if (isPlay) return; // don't open auto panel mid-hand
    showAuto.update((v) => !v);
    showRules.set(false);
    showFeltPanel = false;
    showAbout = false;
    showOptionsMenu = false;
  }

  function toggleRulesPanel(event) {
    event?.stopPropagation?.();
    showRules.update((v) => !v);
    showAuto.set(false);
    showFeltPanel = false;
    showAbout = false;
    showOptionsMenu = true;
  }

  function toggleOptionsMenu(event) {
    event?.stopPropagation?.();
    showOptionsMenu = !showOptionsMenu;
    showAuto.set(false);
    if (!showOptionsMenu) {
      showRules.set(false);
      showFeltPanel = false;
      showAbout = false;
    }
  }

  function toggleAutoBetSetting(event) {
    event?.stopPropagation?.();
    const next = !get(autoBetEnabled);
    autoBetEnabled.set(next);
    showAuto.set(false);
    if (!next) autoPlay.set(false);
  }

  function toggleSideBetsSetting(event) {
    event?.stopPropagation?.();
    const next = !get(sideBetsEnabled);
    sideBetsEnabled.set(next);
    sbSelect = {};
    if (!next && isBet) {
      hands.update((list) => list.map((hand) => ({ ...hand, sb: { pp: 0, t: 0 } })));
    }
  }

  function stopEvent(event) {
    event?.stopPropagation?.();
  }

  function stopClick(node) {
    const handleClick = (event) => event.stopPropagation();
    node.addEventListener("click", handleClick);
    return {
      destroy() {
        node.removeEventListener("click", handleClick);
      }
    };
  }

  function onAddSlot(event) {
    event?.stopPropagation?.();
    addSlot();
    requestAnimationFrame(() => {
      if (feltEl && (isBet || isResult)) feltEl.scrollTop = 0;
    });
  }

  onMount(() => {
    try {
      if (typeof window !== "undefined" && window.screen?.orientation?.lock) {
        window.screen.orientation.lock("portrait").catch(() => {});
      }
    } catch {}
    setMuted(false);
    soundMuted = false;
    if (typeof window !== "undefined") {
      const savedTheme = window.localStorage.getItem(FELT_THEME_STORAGE_KEY);
      const legacyThemeMap = {
        "royal-velvet": "velvet-blue",
        "emerald-velvet": "velvet-green",
        "black-velvet": "velvet-black",
        "gold-velvet": "felt-black",
        "marble-gold": "felt-black",
        "marble-white": "felt-black",
        "marble-black": "felt-black",
        "satin-green": "felt-green",
        "classic-felt": "felt-green",
        "dark-marble": "felt-black",
        "onyx-gold": "felt-black",
        "walnut-top": "felt-black",
        emerald: "felt-green",
        "casino-green": "felt-green",
        "blue-velvet": "velvet-blue",
        midnight: "felt-black",
        "olive-matte": "felt-black",
        royal: "velvet-blue",
      };
      const normalizedSavedTheme = legacyThemeMap[savedTheme] || savedTheme;
      if (normalizedSavedTheme && FELT_THEMES.some((theme) => theme.key === normalizedSavedTheme)) {
        feltTheme = normalizedSavedTheme;
      }
    }

    startIntro();
    sessionClock = setInterval(() => {
      nowMs = Date.now();
    }, 1000);

    const handleWindowFocus = () => {
      refreshStakeBalance();
    };
    const handleVisibilityChange = () => {
      if (typeof document !== "undefined" && document.visibilityState === "visible") {
        refreshStakeBalance();
      }
    };

    if (typeof window !== "undefined") {
      window.addEventListener("focus", handleWindowFocus);
      window.addEventListener("resize", syncFixedAutoplayPosition);
    }
    if (typeof document !== "undefined") {
      document.addEventListener("visibilitychange", handleVisibilityChange);
    }

    return () => {
      if (typeof window !== "undefined") {
        window.removeEventListener("focus", handleWindowFocus);
        window.removeEventListener("resize", syncFixedAutoplayPosition);
      }
      if (typeof document !== "undefined") {
        document.removeEventListener("visibilitychange", handleVisibilityChange);
      }
    };
  });

  onDestroy(() => {
    if (sessionClock) clearInterval(sessionClock);
  });

  afterUpdate(() => {
    if (typeof window !== "undefined") {
      requestAnimationFrame(syncFixedAutoplayPosition);
    }
  });
</script>

<svelte:window bind:innerWidth={windowWidth} bind:innerHeight={windowHeight} on:keydown={(e) => {
  if (e.code === 'Space' && !$runtimeJurisdiction?.disabledSpacebar && !isReplay && !$autoPlay && (isResult || (isBet && $canDeal))) {
    e.preventDefault();
    onDeal();
  }
}} />

<!-- INTRO SCREEN -->
{#if $phase === PHASE.INTRO}
<div class="intro" style="opacity: {$introOp}">
  <div class="intro-video-frame">
    <video class="intro-video" src={introVideoSrc} autoplay muted playsinline preload="auto"></video>
  </div>
</div>
{:else}

<!-- GAME TABLE -->
{#if isMobileLandscape}
<div class="orientation-lock-screen">
  <div class="orientation-lock-card">
    <div class="orientation-lock-title">Portrait Only</div>
    <div class="orientation-lock-copy">You can't play this game in landscape mode.</div>
  </div>
</div>
{:else}
<div
  class="table-wrap"
  class:phase-play={isPlay || isDealer || isIns || isResult}
  class:phase-result={isResult}
  class:phase-result-single-hand={isResult && ($numSlots === 1 || useSplitRows)}
  class:phase-result-two-hand={isResult && $numSlots === 2 && !useSplitRows}
  class:phase-bet={isBet}
  class:phase-play-single-hand={isPlay && ($numSlots === 1 || useSplitRows)}
  class:felt-theme-velvet-blue={feltTheme === "velvet-blue"}
  class:felt-theme-velvet-green={feltTheme === "velvet-green"}
  class:felt-theme-velvet-black={feltTheme === "velvet-black"}
  class:felt-theme-ridge-blue={feltTheme === "ridge-blue"}
  class:felt-theme-ridge-green={feltTheme === "ridge-green"}
  class:felt-theme-ridge-black={feltTheme === "ridge-black"}
  class:felt-theme-felt-blue={feltTheme === "felt-blue"}
  class:felt-theme-felt-green={feltTheme === "felt-green"}
  class:felt-theme-felt-black={feltTheme === "felt-black"}
>
  <div class="balance-pill-stack">
    <span class="mobile-balance-pill">{fmt($balance, displayCurrency)}</span>
    {#if $totalCost > 0 && (isPlay || isResult)}
      <span class="total-wager-sub">{isSocial ? 'Total Play' : 'Total Wager'}: {fmt($totalCost, displayCurrency)}</span>
    {/if}
  </div>
  <button
    class="btn-tab btn-options-toggle mobile-options-launch"
    class:active={showOptionsMenu || $showRules || showAbout}
    on:click={toggleOptionsMenu}
  >
    Options
  </button>

  {#if $sessionBootstrap.status === "loading"}
    <div class="launch-warning">
      {isSocial ? 'Authenticating social casino session...' : 'Authenticating Stake session...'}
    </div>
  {:else if $sessionBootstrap.status === "error"}
    <div class="launch-warning">
      {isReplay ? 'Replay failed' : 'Authenticate failed'}: {$sessionBootstrap.error}
    </div>
  {:else if $rgsError}
    <div class="launch-warning">
      RGS flow warning: {$rgsError}
    </div>
  {:else if $sessionBootstrap.resumeBlocked}
    <div class="launch-warning">
      Authenticated session returned an active round, but the backend did not provide a compatible resumable round state.
    </div>
  {:else if isReplay}
    <div class="replay-banner">
      <strong>Replay mode</strong>
      <span>
        {#if $sessionQuery.game}Game {$sessionQuery.game}{/if}
        {#if $sessionQuery.version} · Version {$sessionQuery.version}{/if}
        {#if $sessionQuery.event} · Event {$sessionQuery.event}{/if}
      </span>
    </div>
    {:else if $launchWarnings.length > 0}
    <div class="launch-warning">
      Launch params incomplete: {$launchWarnings.join(", ")}
    </div>
  {/if}

  {#if showOptionsMenu}
    <div class="mobile-options-drawer" class:full-panel-open={$showRules || showAbout || showFeltPanel} use:stopClick>
      <div class="mobile-options-column">
        <button class="btn-tab btn-options-item btn-options-toggle-pill" class:active={$autoBetEnabled} on:click={toggleAutoBetSetting}>
          <span class="btn-options-toggle-label">Autobet</span>
          <span class="options-mini-toggle" aria-hidden="true">{#if $autoBetEnabled}✓{/if}</span>
        </button>
        <button class="btn-tab btn-options-item btn-options-toggle-pill" class:active={$sideBetsEnabled} on:click={toggleSideBetsSetting}>
          <span class="btn-options-toggle-label">Sidebets</span>
          <span class="options-mini-toggle" aria-hidden="true">{#if $sideBetsEnabled}✓{/if}</span>
        </button>
        <button class="btn-tab btn-options-item" class:active={showFeltPanel} on:click={toggleFeltPanel}>Texture</button>
        <button class="btn-tab btn-options-item" class:active={$showRules} on:click={toggleRulesPanel}>Rules</button>
        <button class="btn-tab btn-options-item btn-mute" class:muted={soundMuted} on:click={onToggleMute}>{soundMuted ? 'Unmute' : 'Sound'}</button>
        <button class="btn-tab btn-options-item" class:active={showAbout} on:click={toggleAbout}>About</button>
      </div>
      {#if showFeltPanel}
        <div class="panel felt-panel felt-panel-inline" use:stopClick>
          <div class="panel-title">Texture</div>
          <div class="texture-picker">
            {#each TEXTURE_ROWS as row}
              <div class="texture-row">
                <div class="texture-row-label">{row.textureLabel}</div>
                {#each row.options as option}
                  <button
                    class="btn-theme texture-option"
                    class:active={feltTheme === option.key}
                    class:theme-velvet-blue={option.key === "velvet-blue"}
                    class:theme-velvet-green={option.key === "velvet-green"}
                    class:theme-velvet-black={option.key === "velvet-black"}
                    class:theme-ridge-blue={option.key === "ridge-blue"}
                    class:theme-ridge-green={option.key === "ridge-green"}
                    class:theme-ridge-black={option.key === "ridge-black"}
                    class:theme-felt-blue={option.key === "felt-blue"}
                    class:theme-felt-green={option.key === "felt-green"}
                    class:theme-felt-black={option.key === "felt-black"}
                    on:click={() => applyFeltTheme(option.key)}
                    aria-label={option.key}
                  >
                    <span class="texture-option-swatch" aria-hidden="true"></span>
                  </button>
                {/each}
              </div>
            {/each}
          </div>
        </div>
      {/if}
      {#if $showRules}
        <div class="panel rules-panel rules-panel-inline" use:stopClick>
          <div class="panel-title">How To Play</div>
          <div class="rules-section"><strong>The Goal</strong>
            <div class="rules-text">Get a hand closer to 21 than the dealer without going over. If you go over 21, you bust and lose automatically, even if the dealer busts too.</div>
          </div>
          <div class="rules-section"><strong>Card Values</strong>
            <div class="rules-text">Number cards are worth their face value. Jack, Queen, and King are worth 10. Aces are worth either 1 or 11, whichever helps your hand more.</div>
          </div>
          <div class="rules-section"><strong>How a Round Works</strong>
            <div class="rules-text">{isSocial
              ? "You choose your play amount, then both you and the dealer are dealt two cards. One of the dealer's cards is face up, one is face down. Based on your cards and the dealer's visible card, you decide what to do next."
              : "You place your bet, then both you and the dealer are dealt two cards. One of the dealer's cards is face up, one is face down. Based on your cards and the dealer's visible card, you decide what to do next."
            }</div>
          </div>
          <div class="rules-section"><strong>Your Options</strong>
            <div class="rules-text">
              <strong>Hit</strong> - Take another card. You can keep hitting as many times as you want, as long as you don't bust.<br/><br/>
              <strong>Stand</strong> - Keep your current hand and end your turn.<br/><br/>
              <strong>Double Down</strong> - Double your original {isSocial ? 'play amount' : 'bet'} and receive exactly one more card, then you're done. No more hits after doubling. This is a power move when your hand is in a strong spot, like starting with a 10 or 11, because you're getting twice the {isSocial ? 'amount in play' : 'money down'} when the odds favor you.<br/><br/>
              <strong>Split</strong> - If your first two cards are the same rank (e.g. two 8s, or two Kings), you can split them into two separate hands. Each hand gets a new card drawn, your {isSocial ? 'play amount' : 'bet'} is duplicated, and you play them out independently. Split Aces receive only one card each and cannot be hit again.
            </div>
          </div>
          <div class="rules-section"><strong>Blackjack</strong>
            <div class="rules-text">{isSocial
              ? "If your first two cards are an Ace and any 10-value card, that's a Blackjack, the best hand in the game. It pays 3:2."
              : "If your first two cards are an Ace and any 10-value card, that's a Blackjack, the best hand in the game. It pays 3:2, meaning a $10 bet wins $15."
            }</div>
          </div>
          <div class="rules-section"><strong>Insurance</strong>
            <div class="rules-text">{isSocial
              ? "If the dealer's face-up card is an Ace, you'll be offered Insurance before play continues. Insurance is a side play that the dealer has Blackjack. It costs half your main play amount and pays 2:1 if the dealer does have Blackjack. It's generally not recommended for most players."
              : "If the dealer's face-up card is an Ace, you'll be offered Insurance before play continues. Insurance is a side bet that the dealer has Blackjack. It costs half your main bet and pays 2:1 if the dealer does have Blackjack. It's generally not recommended for most players."
            }</div>
          </div>
          <div class="rules-section"><strong>Payouts</strong>
            <div class="rules-text">
              Blackjack pays 3:2<br/>
              Winning hand pays 1:1<br/>
              Insurance pays 2:1
            </div>
          </div>
          <div class="rules-section"><strong>{isSocial ? 'Side Plays' : 'Side Bets'}</strong>
            <div class="rules-text">{isSocial
              ? "Side plays are optional extra plays placed before the deal. They're independent from your main hand — you can win a side play and lose your main hand, or vice versa. Side plays are higher risk, higher reward, and have a lower RTP than the base game."
              : "Side bets are optional extra bets placed before the deal. They're independent from your main hand, you can win a side bet and lose your main hand, or vice versa. Side bets are higher risk, higher reward, and have a lower RTP than the base game."
            }</div>
          </div>
          <div class="rules-section"><strong>Perfect Pairs</strong>
            <div class="rules-text rules-text-sm">{isSocial
              ? 'This play wins if your first two cards are a pair, same rank. There are three tiers. Note: the payout is profit only, your original side play amount is not returned on a win.'
              : 'This bet wins if your first two cards are a pair, same rank. There are three tiers. Note: the payout is profit only, your original side bet stake is not returned on a win.'
            }</div>
            <table class="payout-table">
              <tbody>
                <tr><td>Perfect Pair (25:1)</td><td class="rules-example">Same rank, same suit. Example: two 7s of Hearts.</td></tr>
                <tr><td>Coloured Pair (12:1)</td><td class="rules-example">Same rank, same color, different suit. Example: 7 of Hearts and 7 of Diamonds.</td></tr>
                <tr><td>Mixed Pair (6:1)</td><td class="rules-example">Same rank, different color. Example: 7 of Hearts and 7 of Spades.</td></tr>
              </tbody>
            </table>
          </div>
          <div class="rules-section"><strong>21+3</strong>
            <div class="rules-text rules-text-sm">{isSocial
              ? "This play combines your first two cards with the dealer's face-up card to make a 3-card poker hand. Note: the payout is profit only, your original side play amount is not returned on a win."
              : "This bet combines your first two cards with the dealer's face-up card to make a 3-card poker hand. Note: the payout is profit only, your original side bet stake is not returned on a win."
            }</div>
            <table class="payout-table">
              <tbody>
                <tr><td>Suited Trips (100:1)</td><td class="rules-example">All three cards same rank and same suit. Example: three 8s of Clubs.</td></tr>
                <tr><td>Straight Flush (40:1)</td><td class="rules-example">Three consecutive ranks, all the same suit. Example: 4, 5, 6 of Hearts.</td></tr>
                <tr><td>Three of a Kind (30:1)</td><td class="rules-example">All three cards same rank, any suits. Example: three Kings.</td></tr>
                <tr><td>Straight (10:1)</td><td class="rules-example">Three consecutive ranks, any suits. Ace counts high or low.</td></tr>
                <tr><td>Flush (5:1)</td><td class="rules-example">All three cards same suit, any ranks. Example: any three Diamonds.</td></tr>
              </tbody>
            </table>
          </div>
          <div class="rules-section"><strong>Game Rules</strong>
            <div class="rules-text">
              6-deck shoe, reshuffled when fewer than 52 cards remain.<br/>
              Dealer hits soft 17 and stands on hard 17.<br/>
              Double down available on hard 9, 10, or 11 only.<br/>
              One card only after doubling. No further hits.<br/>
              Split available when first two cards share the same rank.<br/>
              Maximum of 6 hands on the table.<br/>
              Split limits depend on active hands: 3 hands on table -> split 3 more, 4 hands -> split 2 more, 5 hands -> split 1 more, 6 hands -> no more splits.<br/>
              No double after split.<br/>
              Split Aces receive one card only and stand automatically.<br/>
              Maximum starting hands: 6 on desktop, 2 on mobile.
            </div>
          </div>
          <div class="rules-section"><strong>Autoplay Modes</strong>
            <div class="rules-text">
              <strong>Conservative</strong> - Lower-variance play. Avoids marginal doubles, stands earlier in riskier spots. Designed to preserve your bankroll over longer sessions.<br/><br/>
              <strong>Optimal</strong> - Perfect basic strategy for this build. The mathematically strongest mode and the closest thing to ideal play.<br/><br/>
              <strong>High Roller</strong> - Aggressive action. Leans into doubles and pressure spots for higher volatility, bigger swings, and faster exposure.
            </div>
            <table class="payout-table strategy-table">
              <thead>
                <tr><th></th><th>Conservative</th><th>Optimal</th><th>High Roller</th></tr>
              </thead>
              <tbody>
                <tr><td>Hard 9 double</td><td>Never</td><td>vs 3-6 only</td><td>vs any</td></tr>
                <tr><td>Hard 10 double</td><td>vs 2-9</td><td>vs 2-9</td><td>vs any</td></tr>
                <tr><td>Hard 11 double</td><td>vs 2-9</td><td>vs any incl. A</td><td>vs any</td></tr>
                <tr><td>Soft doubles</td><td>Never</td><td>Full chart</td><td>More aggressive</td></tr>
                <tr><td>Surrender</td><td>Never</td><td>Yes</td><td>Never</td></tr>
                <tr><td>Splits</td><td>Aces + 8s only</td><td>Full chart</td><td>Full chart +</td></tr>
              </tbody>
            </table>
          </div>
          {#if showRtp}
            <div class="rules-section"><strong>RTP (Return to Player)</strong>
              <div class="rules-text rtp">{#if isSocial}
                Blackjack - 97.2%*<br/>
                Perfect Pairs - 86.4952%<br/>
                21+3 - 85.7029%<br/><br/>
                *These figures describe the theoretical return profile of the game modes under the listed rules. Actual results vary by play choices and session outcomes. Gold Coins are virtual play tokens with no monetary value. Stake Cash is a virtual promotional token and social-casino play is subject to applicable terms, conditions, and local restrictions. Any malfunction voids the game round and all eventual payouts for the round.
              {:else}
                Blackjack - 97.2%*<br/>
                Perfect Pairs - 86.4952%<br/>
                21+3 - 85.7029%<br/><br/>
                *Base game RTP is a simulation-backed estimate using basic strategy over 1,000,000-round test runs. Combined RTP depends on the amounts played on each selected option. If equal amounts are played on multiple options, the effective RTP is the average of those selected values. A player's skill and/or strategy will have an impact on their chances of winning. Any malfunction voids the game round and all eventual payouts for the round. Winnings are settled according to the amount received from the Remote Game Server.
              {/if}</div>
            </div>
          {/if}
        </div>
      {/if}
      {#if showAbout}
        <div class="panel about-panel about-panel-inline" use:stopClick>
          <div class="panel-title">About</div>
          <div class="about-text">We're degens, same as you. We love Stake Originals Blackjack. We just always wanted more at the table. Sidebets. Multiple hands. Autoplay across three strategies: Conservative, Optimal, and Aggressive. We kept waiting for someone to build it and nobody did, so ChadJack did. It's not a competition, it's just more game. Drop a sidebet, open a second hand, and tell us you can stop at just one.</div>
        </div>
      {/if}
    </div>
  {/if}

  <!-- svelte-ignore a11y_click_events_have_key_events -->
  <!-- svelte-ignore a11y_no_static_element_interactions -->
  <!-- FELT AREA -->
  <div
    class="felt"
    bind:this={feltEl}
    class:single-hand={!multi || useSplitRows}
    class:felt-theme-velvet-blue={feltTheme === "velvet-blue"}
    class:felt-theme-velvet-green={feltTheme === "velvet-green"}
    class:felt-theme-velvet-black={feltTheme === "velvet-black"}
    class:felt-theme-ridge-blue={feltTheme === "ridge-blue"}
    class:felt-theme-ridge-green={feltTheme === "ridge-green"}
    class:felt-theme-ridge-black={feltTheme === "ridge-black"}
    class:felt-theme-felt-blue={feltTheme === "felt-blue"}
    class:felt-theme-felt-green={feltTheme === "felt-green"}
    class:felt-theme-felt-black={feltTheme === "felt-black"}
    on:click={closePanels}
  >

    <!-- INSURANCE MODAL — centered overlay -->
    {#if isIns && !isReplay}
      <div class="ins-modal" use:stopClick>
        <div class="ins-modal-title">Dealer shows an Ace</div>
        <div class="ins-modal-sub">Take insurance against a Blackjack?</div>
        {#if $numSlots === 1}
          <!-- Single hand: two clear buttons -->
          <div class="ins-two-btns">
            <button class="btn-ins-take" on:click={() => { insSelect = {0: true}; confirmInsurance(); }}>
              Take Insurance &nbsp; {fmt(Math.floor($hands[0].bet / 2), displayCurrency)}
            </button>
            <button class="btn-ins-skip" on:click={() => takeInsurance(false)}>
              Skip
            </button>
          </div>
        {:else}
          <!-- Multi-hand: per-hand toggles -->
          <div class="ins-modal-hands">
            {#each $hands as hand, idx}
              <button
                class="btn-ins-hand"
                class:active={insSelect[idx]}
                on:click={() => toggleInsHand(idx)}
              >
                {insSelect[idx] ? `✓ Hand ${idx + 1}  ${fmt(Math.floor(hand.bet / 2), displayCurrency)}` : `Hand ${idx + 1}`}
              </button>
            {/each}
          </div>
          <button
            class="btn-ins-all"
            class:active={$hands.every((_, i) => insSelect[i])}
            on:click={toggleInsAll}
          >
            {$hands.every((_, i) => insSelect[i]) ? 'Deselect All' : 'All Hands'}
          </button>
          <button class="btn-ins-confirm" on:click={confirmInsurance}>
            {$hands.some((_, i) => insSelect[i]) ? `Take Insurance  ${fmt($hands.reduce((s, h, i) => s + (insSelect[i] ? Math.floor(h.bet/2) : 0), 0), displayCurrency)}` : 'Skip Insurance'}
          </button>
        {/if}
      </div>
    {/if}

    {#if !isReplay && isBet}
      <div class="felt-menu" use:stopClick>
        <div class="felt-toggle-copy">{isSocial ? 'Play amount' : 'Wager input'}</div>
        <div class="bet-entry-toggle felt-toggle-stack" use:stopClick>
          <button class="bet-entry-btn" class:active={betEntryMode === 'amount'} on:click={() => betEntryMode = 'amount'}>Amount</button>
          <button class="bet-entry-btn" class:active={betEntryMode === 'chips'} on:click={() => betEntryMode = 'chips'}>Chips</button>
        </div>
      </div>
    {/if}

    <!-- DEALER AREA -->
    <div class="dealer-area" class:dealer-area-hidden={isBet}>
      {#if $dealerHand.length > 0}
        <!-- Logo moves left of dealer cards once dealt -->
        <img src={LOGO_IMAGE} alt="ChadJack" class="dealer-logo" />
        <div class="dealer-cards-col">
          <div class="hand-value">{dealerDisplay}</div>
          <div class="cards-row">
            {#each $dealerHand as card, i}
              <div class="card-wrap" style="margin-left: {dealerCardMargin(i, $dealerHand.length)}; z-index: {i}">
                {#if (isPlay || isIns) && i === 1}
                  <div class="card card-hidden">
                    <img src={CARD_BACK_IMAGE} alt="" class="card-back-logo" />
                  </div>
                {:else if customFaceCardImage(card)}
                  <div class="card card-custom">
                    <img src={customFaceCardImage(card)} alt={`${card.rank} of ${card.suit}`} class="card-custom-art" />
                  </div>
                {:else}
                  <div class="card card-face" class:red={card.suit === 'diamonds' || card.suit === 'hearts'}>
                    <div class="card-corner card-tl">
                      <span class="card-rank">{card.rank}</span>
                      <span class="card-suit-sm">{card.suit === 'diamonds' ? '♦' : card.suit === 'hearts' ? '♥' : card.suit === 'clubs' ? '♣' : '♠'}</span>
                    </div>
                    <div class="card-center">{card.suit === 'diamonds' ? '♦' : card.suit === 'hearts' ? '♥' : card.suit === 'clubs' ? '♣' : '♠'}</div>
                    <div class="card-corner card-br">
                      <span class="card-rank">{card.rank}</span>
                      <span class="card-suit-sm">{card.suit === 'diamonds' ? '♦' : card.suit === 'hearts' ? '♥' : card.suit === 'clubs' ? '♣' : '♠'}</span>
                    </div>
                  </div>
                {/if}
              </div>
            {/each}
          </div>
          <div class="dealer-pays-wrap">
            <div class="dealer-pays-line"></div>
            <div class="dealer-pays-copy">CHADJACK pays 3 to 2</div>
          </div>
        </div>
      {:else}
        <div class="dealer-placeholder"></div>
      {/if}
    </div>

    <!-- CHAD LABS LOGO — right side, parallel with dealer logo -->
    {#if isBet}
      <div class="felt-logo-row" class:felt-logo-row-spacer={hideBetLogoDuringRedeal}>
        <img src={LOGO_IMAGE} alt="ChadJack" class="felt-logo felt-logo-large" />
      </div>
    {:else}
      <img src={LOGO_IMAGE} alt="ChadJack" class="felt-logo felt-logo-right" />
    {/if}

    <!-- FIXED HEIGHT MIDDLE ZONE — always 87px, locks player cards to y=422 -->
    <div class="mid-zone">
      <div class="divider-row">
        <div class="divider-line"></div>
      </div>
      <div class="divider-copy">CHADJACK pays 3 to 2</div>
    </div>
    <!-- PLAYER HANDS -->
    <div class="hands-stack">
      {#each handRows as row, rowIdx}
      <div class="hands-row" class:multi class:two={$numSlots === 2 && !useSplitRows} class:four={$numSlots === 4} class:has-split={useSplitRows}>
      <!-- Invisible left spacer mirrors ghost width — keeps card stack at screen center -->
      {#if rowIdx === 0 && (isBet || isResult) && !isReplay && $numSlots < $maxHands}
        <div class="ghost-spacer"></div>
      {/if}

      {#each row as { hand, idx }, rowHandIndex}
        {@const isActive = $activeHand === idx && isPlay}
        {@const rc = resultColor(hand.result)}
        {@const activeSb = sbSelect[idx]}
        {@const reserveSideBetLane = $sideBetsEnabled && !hand.isSplit}
        {@const isSplitRight = useSplitRows && idx === splitRightIdx}
        <div class="hand-col" class:empty-hand={hand.cards.length === 0} class:split-right={isSplitRight}
          style={isSplitRight ? 'position:absolute;left:calc(50% + 90px);top:50%;flex:none;width:auto;transform:translateY(-50%);--mobile-geometry-scale:calc(0.9 * 0.7);' : ''}>

          <!-- Cards area -->
          <div class="cards-area">
            <div class="cards-col" class:has-sidebets={reserveSideBetLane}>
              <!-- Hand value bubble -->
              {#if hand.cards.length > 0}
                <div class="hv-bubble" class:active={isActive} style="color: {hand.result ? rc : C.ac}">
                  {handMsg(hand)}
                </div>
              {/if}

              <!-- sb-col sits beside cards-row in a shared flex row for vertical centering -->
              <div class="sb-and-cards">
                {#if reserveSideBetLane}
                <div class="sb-col" class:sb-col-hidden={!$sideBetsEnabled}>
                  {#each [{k:"pp", n:"Perfect Pairs"}, {k:"t", n:"21+3"}] as sb}
                    <!-- svelte-ignore a11y-click-events-have-key-events -->
                    <!-- svelte-ignore a11y-no-static-element-interactions -->
                    {#if $sideBetsEnabled && (isBet || isResult) && activeSb === sb.k}
                      <!-- Expanded: show inline wager input -->
                      <div class="sb-box sb-box-editing" on:click|stopPropagation>
                        <span class="sb-box-label" class:sb-box-label-213={sb.k === 't'}>{sb.n}</span>
                        <input
                          use:sbFocusInput
                          class="sb-wager-input"
                          type="number"
                          inputmode="numeric"
                          min="0"
                          step="0.01"
                          placeholder="0.00"
                          value={sbDraft[idx + sb.k] ?? ''}
                          on:input={(e) => onSbDraftInput(idx, sb.k, e.currentTarget.value)}
                          on:keydown={(e) => e.key === 'Enter' && commitSbDraft(idx, sb.k)}
                          on:blur={() => commitSbDraft(idx, sb.k)}
                        />
                      </div>
                    {:else}
                      <div class="sb-box-wrap">
                        <div
                          class="sb-box"
                          class:sb-active={hand.sb[sb.k] > 0}
                          on:click={() => $sideBetsEnabled && !isReplay && (isBet || isResult) && toggleSbSelect(idx, sb.k)}
                        >
                          <span class="sb-box-label" class:sb-box-label-213={sb.k === 't'}>{sb.n}</span>
                          {#if hand.sb[sb.k] > 0}
                            <span class="sb-box-amt">{fmt(hand.sb[sb.k], displayCurrency)}</span>
                          {/if}
                        </div>
                        {#if hand.sb[sb.k] > 0 && (isBet || isResult) && !isReplay}
                          <button type="button" class="sb-x-btn" on:click|stopPropagation={() => clearSideBet(idx, sb.k)} aria-label="Remove sidebet">✕</button>
                        {/if}
                      </div>
                    {/if}
                  {/each}
                </div>
                {/if}
                <div
                  class="cards-row"
                  class:active-cards-row={isActive && multi}
                  style="min-height: {cardsRowMinH}px; position: relative;"
                >
                {#if (isBet || isResult) && !isReplay && $numSlots > 1 && !hand.isSplit}
                  <button class="btn-remove-x" on:click={() => removeSlot(idx)}>×</button>
                {/if}
                {#if hand.cards.length > 0}
                  {#each hand.cards as card, i}
                    <div class="card-wrap player-live-card-wrap" style="margin-left: {isSplitRight ? splitRightCardMargin(i) : playerCardMargin(i)}; z-index: {i}; margin-top: {isSplitRight && i > 0 ? `${i * 6}px` : ''};">
                      {#if customFaceCardImage(card)}
                        <div
                          class="card card-custom"
                          class:small={multi && !isDesktop}
                          class:jack-clubs-custom={card.rank === 'J' && card.suit === 'clubs'}
                        >
                          <img src={customFaceCardImage(card)} alt={`${card.rank} of ${card.suit}`} class="card-custom-art" />
                        </div>
                      {:else}
                        <div class="card card-face" class:small={multi && !isDesktop} class:red={card.suit === 'diamonds' || card.suit === 'hearts'}>
                          <div class="card-corner card-tl">
                            <span class="card-rank">{card.rank}</span>
                            <span class="card-suit-sm">{card.suit === 'diamonds' ? '♦' : card.suit === 'hearts' ? '♥' : card.suit === 'clubs' ? '♣' : '♠'}</span>
                          </div>
                          <div class="card-center">{card.suit === 'diamonds' ? '♦' : card.suit === 'hearts' ? '♥' : card.suit === 'clubs' ? '♣' : '♠'}</div>
                          <div class="card-corner card-br">
                            <span class="card-rank">{card.rank}</span>
                            <span class="card-suit-sm">{card.suit === 'diamonds' ? '♦' : card.suit === 'hearts' ? '♥' : card.suit === 'clubs' ? '♣' : '♠'}</span>
                          </div>
                        </div>
                      {/if}
                    </div>
                  {/each}
                {:else}
                  <div class="card-placeholder" class:small={multi && !isDesktop}></div>
                  <div class="card-placeholder" class:small={multi && !isDesktop} style="margin-left: {multi ? cardOverlapSmall : cardOverlap}; opacity: 0.5"></div>
                {/if}
              </div><!-- end cards-row -->
              </div><!-- end sb-and-cards -->




              <!-- Wager controls: 1/2·Bet·2x first, then dollar amount below -->
              {#if (hand.bet > 0 || isBet || isResult) && !hand.isSplit}
                <div class="bet-bar" class:active-hand-bet={isActive && multi}>
                  {#if (isBet || isResult) && !isReplay && !activeSb}
                    <div class="bet-amount-row bet-amount-row-with-actions">
                      <button class="bet-quick-btn" on:click={() => adjustBetByFactor(idx, 0.5)}>1/2</button>
                      <div class="bet-input-shell">
                        <span class="bet-amount-prefix">{isSocial ? 'Play' : 'Bet'}</span>
                        <input
                          class="bet-amount-input"
                          type="number"
                          inputmode="numeric"
                          min="0"
                          step="0.01"
                          value={betDraft[idx] ?? fmt(hand.bet, displayCurrency).replace(/[^0-9.]/g, '')}
                          on:click|stopPropagation
                          on:input={(event) => onBetDraftInput(idx, event.currentTarget.value)}
                          on:blur={() => commitBetDraft(idx)}
                          on:keydown={(event) => event.key === 'Enter' && commitBetDraft(idx)}
                        />
                      </div>
                      <button class="bet-quick-btn" on:click={() => adjustBetByFactor(idx, 2)}>2x</button>
                    </div>
                  {/if}

                </div>
              {/if}

              <!-- Chip buttons -->
              {#if (isBet || isResult) && !isReplay && (betEntryMode === 'chips' || betEntryMode === 'both') && !hand.isSplit}
                <div class="chip-btns">
                  {#if !activeSb && $runtimeConfig?.betLevels?.length}
                    {#each $runtimeConfig.betLevels as betLevel}
                      <button
                        class="chip-btn chip-btn-level"
                        on:click={() => onChipClick(idx, betLevel)}
                        disabled={betLevel > $balance}
                      >
                        {fmt(betLevel, displayCurrency)}
                      </button>
                    {/each}
                  {:else}
                    {#each CHIPS as chip}
                      <button
                        class="chip-btn"
                        class:sb-target={!!activeSb}
                        on:click={() => onChipClick(idx, chip.value)}
                        disabled={$totalCost + chip.value > $balance}
                      >
                        <img src={CHIP_IMAGES[chip.value]} alt={chip.label} />
                      </button>
                    {/each}
                  {/if}
                </div>
                {#if hand.bet > 0 || (activeSb && hand.sb[activeSb] > 0)}
                  <button class="btn-clear" on:click={() => onClear(idx)}>
                    {activeSb && hand.sb[activeSb] > 0 ? `Clear ${activeSb === 'pp' ? 'PP' : '21+3'}` : hand.sb.pp > 0 || hand.sb.t > 0 ? 'Clear Side Bet' : 'Clear'}
                  </button>
                {/if}
              {/if}


            </div><!-- end cards-col -->
          </div><!-- end cards-area -->
        </div>
      {/each}
      </div>
      {/each}

      <!-- Add hand ghost -->
      {#if (isBet || isResult) && !isReplay && ($numSlots < $maxHands || showMobileAutoplay)}
        <div class="ghost-wrap">
          <div class="ghost-row" bind:this={ghostRowEl}>
            {#if $numSlots < $maxHands}
              <!-- svelte-ignore a11y-click-events-have-key-events -->
              <!-- svelte-ignore a11y-no-static-element-interactions -->
              <button type="button" class="ghost" on:click={onAddSlot} aria-label="Add hand">+</button>
            {:else}
              <div class="ghost ghost-placeholder" aria-hidden="true"></div>
            {/if}
          </div>
        </div>
      {/if}
    </div>

  </div>

  </div>

  <!-- BOTTOM DOCK -->
  <div class="bottom-dock" use:stopClick>

      <!-- Auto panel -->
      {#if $showAuto && !autoplayDisabled}
        <div class="panel autoplay-panel" use:stopClick>
          <div class="panel-label">Mode</div>
          <div class="mode-row">
            {#each AUTO_MODES as mode}
              <button class="btn-mode" class:active={$autoMode === mode.key} on:click={() => autoMode.set(mode.key)}>{mode.label}</button>
            {/each}
          </div>
          <div class="panel-hint mode-hint">
            {AUTO_MODES.find((mode) => mode.key === $autoMode)?.summary}
          </div>
          <div class="panel-label">Speed</div>
          <div class="speed-row">
            {#each availableSpeeds as [k, sp]}
              <button class="btn-speed" class:active={$autoSpeed === k} on:click={() => autoSpeed.set(k)}>{sp.label}</button>
            {/each}
          </div>
          <div class="panel-hint">Insurance is always auto-declined. Current {isSocial ? 'plays and side plays' : 'bets and side bets'} stay in place between rounds.</div>
          <div class="rounds-row">
            <span class="panel-label">Max Rounds</span>
            <div class="rounds-ctrl">
              <button on:click={() => autoMax.update(m => Math.max(1, m - 10))}>-</button>
              <span>{$autoMax}</span>
              <button on:click={() => autoMax.update(m => Math.min(1000, m + 10))}>+</button>
            </div>
          </div>
          <button class="btn-auto-toggle" class:stop={$autoPlay} on:click={toggleAuto}>
            {$autoPlay ? "Stop Auto" : "Start Auto"}
          </button>
        </div>
      {/if}

      <!-- Rules/about/texture moved into header options drawer on mobile -->


      <!-- Reload -->
      {#if $balance <= 0 && isBet}
        <button class="btn-reload" on:click={() => balance.set(1_000_000_000)}>{isSocial ? 'Refill' : 'Reload'} {fmt(1_000_000_000, displayCurrency)}</button>
      {/if}


      <!-- Action area: stop bar during autoplay, hit grid during normal play -->
      <div class="action-area-fixed">
        {#if $autoPlay && !isReplay && !autoplayDisabled}
          <button class="btn-stop-bar" on:click={() => autoPlay.set(false)}>
            <span class="stop-bar-label">STOP AUTOPLAY</span>
            <span class="stop-bar-count">{$autoCount}/{$autoMax}</span>
          </button>
        {:else if isPlay && activeH && !isReplay}
          <div class="action-grid">
            <button class="btn-action" on:click={hit}>Hit</button>
            <button class="btn-action" on:click={stand}>Stand</button>
            <button class="btn-action" class:dim={!canSplit} disabled={!canSplit} on:click={canSplit ? split : undefined}>Split</button>
            <button class="btn-action" class:dim={!canDouble} disabled={!canDouble} on:click={canDouble ? doubleDown : undefined}>x2</button>
          </div>
        {/if}
      </div>
      {#if $message && isResult}
        <div class="action-result-msg">
          <span class="nav-result-text mobile-result-text">{mobileResultLabel($message)}</span>
        </div>
      {/if}

      <!-- Deal button — hidden during autoplay so it doesn't cause layout shift -->
      {#if (isBet || isResult) && !isReplay && !$autoPlay}
        <div class="center-deal-wrap">
          <button
            class="btn-deal"
            class:active={$canDeal || isResult}
            disabled={!$canDeal && !isResult}
            on:click={($canDeal || isResult) ? onDeal : undefined}
          >
            {dealLabel}
          </button>
          {#if showMobileAutoplay}
            <button
              bind:this={fixedAutoplayEl}
              class="btn-autoplay-image dock-autoplay-button"
              type="button"
              aria-label="Autoplay"
              on:click={toggleAutoPanel}
            >
              <img src={AUTOPLAY_BUTTON} alt="" />
            </button>
          {/if}
        </div>
      {/if}
  </div>
{/if}
{/if}

<style>
  :global(*) { box-sizing: border-box; margin: 0; padding: 0; }
  :global(body) {
    background: #071a0e;
    color: #f2e8d0;
    font-family: 'Inter', sans-serif;
    -webkit-tap-highlight-color: transparent;
  }
  :global(button) {
    font-family: 'Inter', sans-serif;
    cursor: pointer;
    transition: all 0.1s;
    -webkit-tap-highlight-color: transparent;
  }
  :global(button:active:not(:disabled)) { transform: scale(0.97); opacity: 0.85; }
  :global(button:disabled) { opacity: 0.2; cursor: default; }

  /* INTRO */
  .intro {
    position: fixed; inset: 0;
    background: radial-gradient(circle at 50% 40%, rgba(20, 20, 54, 0.2) 0%, rgba(7, 8, 25, 0.38) 36%, rgba(2, 3, 12, 1) 100%);
    display: flex;
    align-items: center;
    justify-content: center;
    transition: opacity 0.3s;
    overflow: hidden;
  }
  .intro-video-frame {
    position: relative;
    width: min(1100px, 96vw);
    padding: 18px;
    border-radius: 28px;
    background: rgba(12, 12, 26, 0.54);
    box-shadow:
      0 24px 80px rgba(0, 0, 0, 0.42),
      inset 0 0 0 1px rgba(255, 255, 255, 0.05);
    backdrop-filter: blur(14px);
  }
  .intro-video {
    display: block;
    width: 100%;
    height: auto;
    border-radius: 18px;
    background: #050611;
    box-shadow: 0 10px 32px rgba(0,0,0,0.3);
  }
  /* MOBILE INTRO */
  @media (max-width: 767px) {
    .intro-video-frame {
      width: 100vw;
      height: 100vh;
      height: 100dvh;
      padding: 0;
      border-radius: 0;
      background: transparent;
      box-shadow: none;
      backdrop-filter: none;
    }
    .intro-video {
      border-radius: 0;
      width: 100vw;
      height: 100dvh;
      max-width: 100vw;
      max-height: 100dvh;
      min-height: 0;
      object-fit: contain;
      object-position: center;
    }
  }
  /* TABLE */
  .table-wrap {
    height: 100vh;
    width: 100%;
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }
  .orientation-lock-screen {
    position: fixed;
    inset: 0;
    z-index: 120;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 24px;
    background:
      radial-gradient(circle at 50% 16%, rgba(127, 214, 174, 0.12), transparent 38%),
      radial-gradient(ellipse at 50% 33%, rgba(24, 110, 83, 0.18), rgba(9, 58, 40, 0.82) 70%, rgba(4, 31, 22, 0.96) 100%),
      #071a0e;
  }
  .orientation-lock-card {
    width: min(420px, 100%);
    border-radius: 20px;
    border: 1px solid rgba(232, 212, 139, 0.26);
    background: rgba(8, 22, 14, 0.92);
    box-shadow: 0 18px 48px rgba(0,0,0,0.42);
    padding: 24px 20px;
    text-align: center;
  }
  .orientation-lock-title {
    font-family: 'Oswald', sans-serif;
    font-size: 28px;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: #e0ba52;
  }
  .orientation-lock-copy {
    margin-top: 10px;
    font-size: 16px;
    line-height: 1.5;
    color: rgba(242, 232, 208, 0.82);
  }

  .balance-row {
    display: flex;
    justify-content: space-between;
    gap: 12px;
    padding: 8px 14px 8px;
    min-height: 48px;
    align-items: center;
    border-bottom: 1px solid rgba(212,168,64,0.08);
    flex-shrink: 0;
  }
  .header-actions {
    display: flex;
    align-items: center;
    gap: 8px;
    width: 100%;
    justify-content: space-between;
  }
  .utility-btns {
    display: flex;
    gap: 6px;
    align-items: center;
  }
  .btn-autoplay-cta,
  .btn-options-toggle,
  .btn-options-item {
    font-family: 'Oswald', sans-serif !important;
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }
  .btn-autoplay-cta {
    min-height: 34px !important;
    padding: 6px 14px !important;
    border-radius: 999px !important;
    border: 1px solid rgba(232, 212, 139, 0.55) !important;
    background: linear-gradient(180deg, #e0ba52 0%, #b88d26 100%) !important;
    color: #102114 !important;
    font-size: 13px !important;
    font-weight: 800 !important;
    box-shadow: inset 0 1px 0 rgba(255,255,255,0.22);
  }
  .btn-autoplay-cta.stop {
    background: linear-gradient(180deg, #d45b50 0%, #a62922 100%) !important;
    color: #fff5ef !important;
    border-color: rgba(255, 164, 145, 0.45) !important;
  }
  .btn-options-toggle {
    min-height: 34px !important;
    padding: 6px 14px !important;
    border-radius: 999px !important;
    border: 1px solid rgba(203, 218, 206, 0.36) !important;
    background: rgba(10, 30, 19, 0.86) !important;
    color: rgba(212, 223, 213, 0.86) !important;
    font-size: 13px !important;
    font-weight: 700 !important;
  }
  .balance-subrow {
    display: flex;
    justify-content: flex-end;
    padding: 4px 12px 0;
    flex-shrink: 0;
  }
  .balance-meta-mobile {
    margin-left: 0;
    padding: 0;
    min-height: 0;
  }
  .mobile-options-drawer {
    padding: 6px 12px 0;
    display: flex;
    flex-direction: column;
    gap: 8px;
    flex-shrink: 0;
  }
  .mobile-options-column {
    display: grid;
    grid-template-columns: 1fr;
    gap: 6px;
  }
  .btn-options-item {
    min-height: 30px !important;
    padding: 6px 8px !important;
    border-radius: 999px !important;
    border: 1px solid rgba(232, 212, 139, 0.2) !important;
    background: rgba(255, 255, 255, 0.02) !important;
    color: #ffffff !important;
    font-size: 12px !important;
    font-weight: 700 !important;
    box-shadow: inset 0 1px 0 rgba(255,255,255,0.03);
  }
  .btn-options-toggle-pill {
    display: inline-flex !important;
    align-items: center;
    justify-content: center;
    position: relative;
    gap: 0;
    text-align: center;
  }
  .btn-options-toggle-label {
    display: block;
    width: 100%;
    text-align: center;
  }
  .options-mini-toggle {
    width: 12px;
    height: 12px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    border-radius: 2px;
    background: #050505;
    border: 1px solid rgba(255,255,255,0.18);
    box-shadow: inset 0 1px 0 rgba(255,255,255,0.04);
    flex: 0 0 auto;
    color: #ffffff;
    font-size: 10px;
    font-weight: 700;
    line-height: 1;
    position: absolute;
    right: 8px;
    top: 50%;
    transform: translateY(-50%);
  }
  .btn-options-item.active {
    border-color: rgba(212, 168, 64, 0.7) !important;
    background: linear-gradient(180deg, rgba(212, 168, 64, 0.24) 0%, rgba(112, 79, 19, 0.22) 100%) !important;
    color: #fff4cf !important;
    box-shadow:
      inset 0 1px 0 rgba(255, 235, 173, 0.18),
      0 0 0 1px rgba(212, 168, 64, 0.08);
  }
  .felt-panel-inline,
  .rules-panel-inline,
  .about-panel-inline {
    margin-top: 0;
  }
  .btn-utility {
    font-family: 'Oswald', sans-serif !important;
    font-weight: 600;
    font-size: 13px !important;
    letter-spacing: 0.04em;
    text-transform: uppercase;
    padding: 5px 12px !important;
    border-radius: 6px !important;
    min-height: 32px !important;
    min-width: unset !important;
  }
  .btn-mute.muted { opacity: 0.45; }
  .btn-fact { font-size: 16px !important; padding: 7px 20px !important; min-height: 42px !important; }
  .session-meta {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    min-width: 0;
  }
  .session-pill {
    border-radius: 999px;
    border: 1px solid rgba(232, 212, 139, 0.25);
    background: rgba(15, 34, 23, 0.72);
    color: #d9d7ca;
    font-size: 13px;
    line-height: 1;
    padding: 7px 10px;
    white-space: nowrap;
  }
  .session-pill.positive { color: #85f7ad; }
  .session-pill.negative { color: #ff8e8e; }
  .balance-meta {
    margin-left: auto;
    display: flex;
    align-items: center;
    justify-content: flex-end;
  }
  .balance     { font-size: 26px; font-weight: 700; white-space: nowrap; font-family: 'Oswald', sans-serif; letter-spacing: 0.02em; color: #e8d48b; text-shadow: 0 0 10px rgba(212,168,64,0.14); }
  .rgs-status  { margin-left: 10px; font-size: 14px; color: #e8d48b; white-space: nowrap; }
  .replay-banner,
  .launch-warning {
    width: min(960px, 94vw);
    margin: 0 auto 10px;
    padding: 8px 12px;
    border-radius: 12px;
    border: 1px solid rgba(232, 212, 139, 0.35);
    background: rgba(23, 46, 32, 0.88);
    color: #f2e8d0;
    display: flex;
    justify-content: center;
    align-items: center;
    gap: 8px;
    text-align: center;
    font-size: 16px;
  }
  .launch-warning { color: #e8d48b; }

  /* FELT */
  .felt {
    position: relative;
    flex: 1;
    display: flex;
    flex-direction: column;
    padding: 4px 14px 0;
    padding-bottom: 180px;
    background-color: #0b3a25;
    background:
      radial-gradient(circle at 50% 16%, rgba(127, 214, 174, 0.18), transparent 38%),
      radial-gradient(ellipse at 50% 33%, rgba(24, 110, 83, 0.26), rgba(9, 58, 40, 0.78) 70%, rgba(4, 31, 22, 0.92) 100%),
      url('/green.felt.final.png');
    background-size: cover, cover, cover;
    background-position: center top, center center, center top;
    background-repeat: no-repeat, no-repeat, no-repeat;
    background-blend-mode: screen, multiply, normal;
    transform-origin: top center;
    overflow-y: auto;
    overflow-x: hidden;
    -webkit-overflow-scrolling: touch;
  }
  .felt.felt-theme-velvet-blue,
  .table-wrap.felt-theme-velvet-blue {
    background:
      radial-gradient(circle at 50% 16%, rgba(106, 145, 224, 0.18), transparent 38%),
      radial-gradient(ellipse at 50% 33%, rgba(24, 56, 112, 0.26), rgba(7, 20, 52, 0.78) 70%, rgba(4, 12, 32, 0.92) 100%),
      url('/velvet-blue-base.png');
    background-size: cover, cover, cover;
    background-position: center top, center center, center top;
  }
  .felt.felt-theme-velvet-green,
  .table-wrap.felt-theme-velvet-green {
    background:
      radial-gradient(circle at 50% 16%, rgba(127, 214, 174, 0.18), transparent 38%),
      radial-gradient(ellipse at 50% 33%, rgba(24, 110, 83, 0.26), rgba(9, 58, 40, 0.78) 70%, rgba(4, 31, 22, 0.92) 100%),
      url('/velvet-emerald-base.png');
    background-size: cover, cover, cover;
    background-position: center top, center center, center top;
  }
  .felt.felt-theme-felt-green,
  .table-wrap.felt-theme-felt-green {
    background:
      radial-gradient(circle at 50% 16%, rgba(127, 214, 174, 0.18), transparent 38%),
      radial-gradient(ellipse at 50% 33%, rgba(24, 110, 83, 0.26), rgba(9, 58, 40, 0.78) 70%, rgba(4, 31, 22, 0.92) 100%),
      url('/felt-green-base.png');
    background-size: cover, cover, cover;
    background-position: center top, center center, center top;
  }
  .felt.felt-theme-velvet-black,
  .table-wrap.felt-theme-velvet-black {
    background:
      radial-gradient(circle at 50% 16%, rgba(116, 126, 151, 0.12), transparent 38%),
      radial-gradient(ellipse at 50% 33%, rgba(36, 46, 66, 0.28), rgba(12, 16, 24, 0.82) 70%, rgba(6, 8, 12, 0.94) 100%),
      url('/velvet-black-base.png');
    background-size: cover, cover, cover;
    background-position: center top, center center, center top;
  }
  .felt.felt-theme-felt-black,
  .table-wrap.felt-theme-felt-black {
    background:
      radial-gradient(circle at 50% 16%, rgba(116, 126, 151, 0.12), transparent 38%),
      radial-gradient(ellipse at 50% 33%, rgba(36, 46, 66, 0.28), rgba(12, 16, 24, 0.82) 70%, rgba(6, 8, 12, 0.94) 100%),
      url('/felt-black-base.png');
    background-size: cover, cover, cover;
    background-position: center top, center center, center top;
  }
  .felt.felt-theme-ridge-blue,
  .table-wrap.felt-theme-ridge-blue {
    background:
      radial-gradient(circle at 50% 16%, rgba(106, 145, 224, 0.18), transparent 38%),
      radial-gradient(ellipse at 50% 33%, rgba(24, 56, 112, 0.26), rgba(7, 20, 52, 0.78) 70%, rgba(4, 12, 32, 0.92) 100%),
      url('/ridge-blue-base.png');
    background-size: cover, cover, cover;
    background-position: center top, center center, center top;
  }
  .felt.felt-theme-felt-blue,
  .table-wrap.felt-theme-felt-blue {
    background:
      radial-gradient(circle at 50% 16%, rgba(106, 145, 224, 0.18), transparent 38%),
      radial-gradient(ellipse at 50% 33%, rgba(24, 56, 112, 0.26), rgba(7, 20, 52, 0.78) 70%, rgba(4, 12, 32, 0.92) 100%),
      url('/felt-blue-base.png');
    background-size: cover, cover, cover;
    background-position: center top, center center, center top;
  }
  .felt.felt-theme-ridge-green,
  .table-wrap.felt-theme-ridge-green {
    background:
      radial-gradient(circle at 50% 16%, rgba(127, 214, 174, 0.18), transparent 38%),
      radial-gradient(ellipse at 50% 33%, rgba(24, 110, 83, 0.26), rgba(9, 58, 40, 0.78) 70%, rgba(4, 31, 22, 0.92) 100%),
      url('/ridge-green-base.png');
    background-size: cover, cover, cover;
    background-position: center top, center center, center top;
  }
  .felt.felt-theme-ridge-black,
  .table-wrap.felt-theme-ridge-black {
    background:
      radial-gradient(circle at 50% 16%, rgba(116, 126, 151, 0.12), transparent 38%),
      radial-gradient(ellipse at 50% 33%, rgba(36, 46, 66, 0.28), rgba(12, 16, 24, 0.82) 70%, rgba(6, 8, 12, 0.94) 100%),
      url('/ridge-black-base.png');
    background-size: cover, cover, cover;
    background-position: center top, center center, center top;
  }
  .felt::before {
    content: "";
    position: absolute;
    inset: 0;
    pointer-events: none;
    background:
      radial-gradient(circle at 24% 22%, rgba(255,255,255,0.045), transparent 42%),
      radial-gradient(circle at 76% 74%, rgba(0,0,0,0.16), transparent 48%),
      repeating-linear-gradient(0deg, rgba(255,255,255,0.014) 0px, rgba(255,255,255,0.014) 1px, rgba(0,0,0,0.018) 1px, rgba(0,0,0,0.018) 3px),
      repeating-linear-gradient(90deg, rgba(255,255,255,0.01) 0px, rgba(255,255,255,0.01) 1px, rgba(0,0,0,0.014) 1px, rgba(0,0,0,0.014) 4px);
    opacity: 0;
    z-index: 0;
  }
  .felt > * {
    position: relative;
    z-index: 1;
  }
  .felt-menu {
    display: flex;
    flex-direction: row;
    gap: 10px;
    align-items: center;
    justify-content: center;
    padding: 6px 0 2px;
    flex-shrink: 0;
    z-index: 4;
  }
  .felt-menu-row {
    display: flex;
    gap: 8px;
    align-items: center;
  }
  .felt-menu-btn {
    min-width: 92px;
    min-height: 42px;
    border-radius: 999px;
    font-size: 22px;
    padding: 0 18px;
    background: rgba(7, 26, 14, 0.82);
    backdrop-filter: blur(4px);
  }
  .felt-menu-btn-fact {
    min-width: 82px;
  }
  .felt-toggle-copy {
    margin-left: 4px;
    font-size: 18px;
    color: rgba(242, 232, 208, 0.72);
  }
  .felt-toggle-stack {
    margin-left: 2px;
  }
  @media (min-width: 768px) {
    .felt-menu {
      display: none;
    }
  }

  /* DEALER */
  .dealer-area { min-height: 112px; position: relative; display: flex; flex-direction: row; align-items: center; justify-content: center; gap: 16px; }
  .dealer-area-hidden { min-height: 0 !important; overflow: hidden; }
  .dealer-area-hidden .dealer-placeholder { height: 0; }
  .dealer-placeholder { height: 96px; }

  /* CARDS */
  .cards-row   { display: flex; flex-wrap: nowrap; overflow: visible; -webkit-overflow-scrolling: touch; }
  .card-wrap   { position: relative; flex-shrink: 0; }

  .card {
    border-radius: 8px;
    width: 104px;
    height: 200px;
    position: relative;
    overflow: hidden;
    animation: cardIn 0.22s ease both;
    box-shadow: 0 3px 12px rgba(0,0,0,0.3);
  }
  .card.small  { width: 104px; height: 200px; }
  .card-face         { background: #fff; }
  .card-custom { background: transparent; overflow: hidden; }
  .card-custom-art {
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
    object-fit: fill;
    display: block;
  }
  .card-hidden {
    background: transparent;
    border: none;
    display: flex;
    align-items: center;
    justify-content: center;
    overflow: hidden;
  }
  .card-back-logo {
    width: 100%;
    height: 100%;
    object-fit: cover;
    object-position: center;
    opacity: 1;
    filter: none;
  }

  .card-corner { position: absolute; display: flex; flex-direction: column; line-height: 1; }
  .card-tl     { top: 6px; left: 7px; }
  .card-br     { bottom: 6px; right: 7px; transform: rotate(180deg); }
  .card.small .card-tl { top: 4px; left: 5px; }
  .card.small .card-br { bottom: 4px; right: 5px; }

  .card-rank    { font-family: Georgia, serif; font-size: 20px; font-weight: bold; }
  .card-suit-sm { font-family: Georgia, serif; font-size: 17px; margin-top: -1px; }
  .card.small .card-rank    { font-size: 15px; }
  .card.small .card-suit-sm { font-size: 13px; }
  .card-center  { position: absolute; top: 50%; left: 50%; transform: translate(-50%,-50%); font-family: Georgia, serif; font-size: 42px; }
  .card.small .card-center { font-size: 30px; }
  .card-face.red .card-rank,
  .card-face.red .card-suit-sm,
  .card-face.red .card-center { color: #c62828; }
  .card-face:not(.red) .card-rank,
  .card-face:not(.red) .card-suit-sm,
  .card-face:not(.red) .card-center { color: #1b1b1b; }

  .card-placeholder {
    width: 104px; height: 200px;
    border-radius: 8px;
    border: 2.5px dashed rgba(255,255,255,0.55);
    background: rgba(242,232,208,0.03);
  }
  .card-placeholder.small { width: 113px; height: 183px; }

  /* HAND VALUE */
  .hv-bubble {
    background: linear-gradient(180deg, #e0b84c 0%, #b98b20 100%);
    padding: 2px 14px;
    border-radius: 12px;
    font-size: 18px;
    font-weight: 600;
    margin-bottom: 4px;
    border: 1px solid rgba(255, 235, 173, 0.45);
    text-align: center;
    font-family: 'Oswald', sans-serif;
    letter-spacing: 0.02em;
    color: #1e1605 !important;
    box-shadow: inset 0 1px 0 rgba(255,255,255,0.28), 0 4px 10px rgba(0,0,0,0.18);
  }
  .hv-bubble.active {
    background: linear-gradient(180deg, #efc95f 0%, #c79624 100%);
    border-color: rgba(255, 235, 173, 0.75);
    animation: glow 1.5s ease infinite;
  }

  /* HAND VALUE (dealer) */
  .hand-value {
    background: rgba(0,0,0,0.5);
    padding: 3px 16px;
    border-radius: 14px;
    font-size: 22px;
    font-weight: 600;
    margin-bottom: 5px;
    font-family: 'Oswald', sans-serif;
    letter-spacing: 0.02em;
    color: #e8d48b;
  }

  /* PAYOUT */
  .payout { font-size: 16px; color: #66ff88; margin-top: 3px; font-weight: 600; font-family: 'Oswald', sans-serif; letter-spacing: 0.02em; }

  /* FELT LOGO — bet screen only */
  .felt-logo-row {
    display: flex;
    justify-content: center;
    align-items: center;
    padding: 6px 0 4px;
  }
  .felt-logo-row-spacer {
    visibility: hidden;
  }
  .felt-logo {
    width: 72px;
    height: 72px;
    object-fit: contain;
    opacity: 0.85;
    filter: drop-shadow(0 0 10px rgba(212,168,64,0.35));
  }
  .felt-logo-large {
    width: 160px;
    height: 160px;
    opacity: 0.95;
    filter: drop-shadow(0 0 24px rgba(212,168,64,0.55));
  }

  .felt-logo-right {
    position: absolute;
    right: 14px;
    top: 0;
    width: 124px;
    height: 124px;
    object-fit: contain;
    opacity: 0.9;
    filter: drop-shadow(0 0 16px rgba(212,168,64,0.5));
    pointer-events: none;
  }

  /* DEALER LOGO — fixed to left side */
  .dealer-logo {
    position: absolute;
    left: 0;
    top: 0;
    width: 124px;
    height: 124px;
    object-fit: contain;
    opacity: 0.9;
    filter: drop-shadow(0 0 16px rgba(212,168,64,0.5));
  }
  .dealer-cards-col {
    display: flex;
    flex-direction: column;
    align-items: center;
  }
  .dealer-pays-wrap {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 4px;
    margin-top: 10px;
  }
  .dealer-pays-line {
    width: min(220px, 56vw);
    height: 1px;
    background: linear-gradient(90deg, rgba(212,168,64,0.05), rgba(232,212,139,0.95), rgba(212,168,64,0.05));
  }
  .dealer-pays-copy {
    font-family: 'Oswald', sans-serif;
    font-size: 12px;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: #d4a840;
    text-align: center;
  }

  /* INLINE DEALER RESULT MESSAGE */
  .dealer-result-msg-top {
    display: flex;
    justify-content: center;
    align-items: center;
    padding: 6px 0 2px;
    min-height: 36px;
  }
  .dealer-result-msg {
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 4px 0 0;
  }
  .dealer-result-text {
    font-family: 'Oswald', sans-serif;
    font-size: 28px;
    font-weight: 700;
    letter-spacing: 0.04em;
    animation: fadeIn 0.3s ease;
  }
  .dealer-result-text.win  { color: #66ff88; }
  .dealer-result-text.lose { color: #ef5350; }

  /* FIXED HEIGHT MID ZONE — keeps player cards locked */
  .mid-zone {
    position: relative;
    height: 34px !important;
    min-height: 34px !important;
    max-height: 34px !important;
    flex-shrink: 0 !important;
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    gap: 0;
    overflow: visible;
  }

  /* DIVIDER — play screen */
  .divider-row {
    position: absolute;
    left: 0;
    right: 0;
    top: 50%;
    transform: translateY(-50%);
    display: flex;
    align-items: center;
    height: 1px;
    flex-shrink: 0;
    margin: 0;
  }
  .divider-row.has-result { gap: 10px; }
  .divider-line  {
    flex: 1;
    height: 1px;
    background: linear-gradient(
      90deg,
      rgba(212,168,64,0.14) 0%,
      rgba(212,168,64,0.42) 18%,
      rgba(212,168,64,0.52) 50%,
      rgba(212,168,64,0.42) 82%,
      rgba(212,168,64,0.14) 100%
    );
    box-shadow:
      0 1px 0 rgba(6, 24, 15, 0.45),
      0 -1px 0 rgba(255, 227, 160, 0.08);
    opacity: 0.88;
  }
  .divider-label { font-size: 13px; padding: 0 14px; opacity: 0.92; font-family: 'Inter', sans-serif; font-weight: 700; letter-spacing: 0.1em; text-transform: uppercase; color: #e8d48b; }
  .divider-copy {
    position: relative;
    z-index: 2;
    font-family: 'Oswald', sans-serif;
    font-size: 13px;
    font-weight: 700;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: #d4a840;
    white-space: nowrap;
    text-shadow:
      0 1px 0 rgba(0,0,0,0.42),
      0 0 8px rgba(4, 24, 14, 0.55);
  }
  .table-wrap.phase-bet .mid-zone {
    position: fixed;
    left: 0;
    right: 0;
    top: var(--bet-divider-top, calc(max(4px, env(safe-area-inset-top)) + 170px));
    gap: 0;
    margin-top: 0;
    margin-bottom: 0;
    z-index: 2;
    pointer-events: none;
  }
  .table-wrap.phase-bet .divider-line {
    opacity: 0.64;
    box-shadow:
      0 1px 0 rgba(6, 24, 15, 0.52),
      0 -1px 0 rgba(255, 227, 160, 0.05);
  }
  .table-wrap.phase-bet .divider-copy {
    color: #cfa54a;
    text-shadow:
      0 1px 0 rgba(0,0,0,0.46),
      0 0 6px rgba(4, 24, 14, 0.48);
  }
  .table-wrap.phase-play.phase-play-single-hand .divider-copy {
    transform: translateY(-15px);
  }
  .table-wrap.phase-play:not(.phase-play-single-hand) .divider-copy {
    transform: translateY(-37px);
  }
  .divider-result-msg {
    display: flex;
    align-items: center;
    flex: 0 0 auto;
    white-space: nowrap;
  }

  /* FACT BLOCK — top-right corner, beside dealer card */
  .fact-block {
    position: absolute;
    top: 12px;
    right: 14px;
    left: auto;
    width: 200px;
    padding: 10px 14px;
    background: rgba(8, 20, 12, 0.78);
    border: 1px solid rgba(232, 212, 139, 0.18);
    border-radius: 12px;
    backdrop-filter: blur(6px);
    font-family: 'Fredoka One', cursive;
    font-size: 14px;
    line-height: 1.65;
    color: rgba(242, 232, 208, 0.82);
    z-index: 5;
    pointer-events: none;
  }



  .fact-row {
    display: flex;
    flex-direction: column;
    gap: 4px;
    align-items: center;
    margin-bottom: 0;
  }
  .fact-row.table-layout {
    width: min(1180px, 100%);
    margin: 0 auto 8px;
    padding: 12px 0 18px;
    display: grid;
    grid-template-columns: minmax(260px, 340px) minmax(420px, 820px);
    gap: 28px;
    align-items: center;
  }
  .fact-block {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 4px;
    min-width: 0;
  }
  .fact-caption {
    font-size: 20px;
    line-height: 1.1;
    color: rgba(242, 232, 208, 0.78);
    text-align: center;
  }
  .fact {
    font-size: 16px;
    text-align: center;
    line-height: 1.4;
    padding: 0 8px;
    color: #f2e8d0;
    font-family: 'Rocksalt', cursive;
    max-width: 560px;
    align-self: center;
    margin-bottom: 0;
  }
  .desktop-deal-wrap {
    display: flex;
    justify-content: center;
    align-items: center;
    width: 100%;
  }
  .bet-entry-toggle {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 4px;
    border-radius: 999px;
    background: rgba(8, 20, 12, 0.72);
    border: 1px solid rgba(232, 212, 139, 0.18);
  }
  .bet-entry-btn {
    min-width: 72px;
    min-height: 32px;
    padding: 0 12px;
    border-radius: 999px;
    border: 1px solid transparent;
    background: transparent;
    color: #bfb49a;
    font-size: 16px;
    font-weight: 700;
  }
  .bet-entry-btn.active {
    border-color: rgba(232,212,139,0.35);
    background: rgba(232,212,139,0.12);
    color: #f2e8d0;
  }
  .fact-result {
    font-style: normal;
    color: rgba(242, 232, 208, 0.86);
  }
  .result-next-wrap {
    display: flex;
    justify-content: center;
    align-items: center;
    margin: 4px auto 2px;
    width: 100%;
  }
  .btn-next-centered {
    width: min(520px, 92vw);
    min-height: 68px;
    border-radius: 999px;
    font-size: 28px;
    font-weight: 700;
    opacity: 1;
  }

  /* INSURANCE — centered modal overlay */
  .ins-modal {
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    z-index: 30;
    width: min(460px, 88vw);
    background: rgba(7, 26, 14, 0.97);
    border: 1px solid rgba(212, 168, 64, 0.35);
    border-radius: 18px;
    padding: 28px 28px 22px;
    display: flex;
    flex-direction: column;
    align-items: stretch;
    gap: 12px;
    box-shadow: 0 8px 48px rgba(0,0,0,0.7), 0 0 0 1px rgba(212,168,64,0.1);
    animation: fadeIn 0.2s ease;
  }
  .ins-modal-title {
    font-family: 'Oswald', sans-serif;
    font-size: 22px;
    font-weight: 600;
    letter-spacing: 0.05em;
    text-transform: uppercase;
    text-align: center;
    color: #e8d48b;
  }
  .ins-modal-sub {
    font-family: 'Inter', sans-serif;
    font-size: 14px;
    opacity: 0.65;
    text-align: center;
    margin-top: -6px;
  }
  .ins-modal-hands {
    display: flex;
    gap: 8px;
    justify-content: center;
    flex-wrap: wrap;
  }
  .btn-ins-hand {
    min-width: 110px;
    min-height: 40px;
    padding: 0 16px;
    border-radius: 999px;
    border: 1.5px dashed rgba(232, 212, 139, 0.35);
    background: rgba(8, 20, 12, 0.6);
    color: rgba(242, 232, 208, 0.55);
    font-size: 14px;
    font-weight: 700;
    font-family: 'Inter', sans-serif;
    letter-spacing: 0.02em;
    transition: all 0.15s;
  }
  .btn-ins-hand.active {
    border-style: solid;
    border-color: #d4a840;
    background: rgba(212, 168, 64, 0.18);
    color: #f2e8d0;
    box-shadow: 0 0 10px rgba(212, 168, 64, 0.25);
  }
  .btn-ins-all {
    padding: 10px 0;
    border-radius: 8px;
    border: 1px solid rgba(212, 168, 64, 0.25);
    background: transparent;
    color: #bfb49a;
    font-size: 14px;
    font-weight: 700;
    font-family: 'Inter', sans-serif;
    transition: all 0.15s;
  }
  .btn-ins-all.active {
    border-color: #e8d48b;
    background: rgba(232, 212, 139, 0.08);
    color: #e8d48b;
  }
  .btn-ins-confirm {
    padding: 15px 0;
    border-radius: 10px;
    border: none;
    background: linear-gradient(135deg, #d4a840, #a88a30);
    color: #071a0e;
    font-size: 18px;
    font-weight: 700;
    font-family: 'Oswald', sans-serif;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    margin-top: 2px;
  }

  /* Single-hand insurance two-button layout */
  .ins-two-btns { display: flex; gap: 8px; margin-top: 2px; }
  .btn-ins-take {
    flex: 3;
    padding: 15px 0;
    border-radius: 10px;
    border: none;
    background: linear-gradient(135deg, #d4a840, #a88a30);
    color: #071a0e;
    font-size: 18px;
    font-weight: 700;
    font-family: 'Oswald', sans-serif;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    cursor: pointer;
  }
  .btn-ins-skip {
    flex: 1;
    padding: 15px 0;
    border-radius: 10px;
    border: 1.5px solid rgba(242,232,208,0.25);
    background: transparent;
    color: rgba(242,232,208,0.6);
    font-size: 18px;
    font-weight: 700;
    font-family: 'Oswald', sans-serif;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    cursor: pointer;
  }
  .btn-ins-skip:hover { border-color: rgba(242,232,208,0.5); color: #f2e8d0; }

  /* RESULT */
  .result-msg { min-height: 24px; display: flex; align-items: center; justify-content: center; }
  .msg-text   { font-size: 26px; font-weight: 700; animation: fadeIn 0.3s ease; font-family: 'Oswald', sans-serif; letter-spacing: 0.04em; }
  .msg-text.bad-beat { font-size: 30px; color: #ef5350; }

  /* HANDS ROW */
  .hands-stack { display: flex; flex-direction: column; align-items: center; width: 100%; }
  .hands-row { display: flex; justify-content: center; gap: 16px; padding-top: 0; min-height: 0; flex: 0 0 auto; align-items: center; flex-wrap: nowrap; }
  .hands-row.multi { gap: 20px; }
  .hand-col  { display: flex; flex-direction: column; align-items: flex-start; flex: 0 0 auto; min-width: 0; justify-content: flex-start; }

  /* WAGER LABEL */
  .bet-bar {
    margin-top: 1px;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 2px;
    margin-left: 44px; /* center under cards-row, offsetting sb-col width */
  }
  .bet-bar.active-hand-bet {
    border-radius: 16px;
    box-shadow:
      0 0 0 2px rgba(232, 212, 139, 0.96),
      0 0 18px rgba(212, 168, 64, 0.38);
    background: rgba(232, 212, 139, 0.08);
    padding: 3px 6px;
  }
  .wager-label {
    font-size: 20px; font-weight: 600; color: #f2e8d0;
    text-align: center; white-space: nowrap;
    font-family: 'Oswald', sans-serif; letter-spacing: 0.02em;
  }
  .wager-label-top {
    margin-bottom: 1px;
  }
  .bet-quick-actions {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 2px;
    border-radius: 999px;
    background: rgba(8, 20, 12, 0.7);
    border: 1px solid rgba(232, 212, 139, 0.18);
  }
  .bet-quick-actions-bottom {
    margin-top: 2px;
  }
  .bet-quick-btn {
    min-width: 54px;
    min-height: 28px;
    padding: 0 12px;
    border-radius: 999px;
    border: 1px solid rgba(241, 222, 156, 0.65);
    background: linear-gradient(180deg, #e1bd58 0%, #b68a25 100%);
    color: #142314;
    font-size: 16px;
    font-weight: 800;
    box-shadow: inset 0 1px 0 rgba(255,255,255,0.28);
  }
  .bet-amount-row {
    display: inline-flex;
    align-items: center;
    gap: 8px;
  }
  .cards-row.active-cards-row {
    border-radius: 8px;
    box-shadow:
      0 0 18px rgba(255, 99, 34, 0.46),
      0 0 34px rgba(255, 120, 24, 0.41),
      0 0 54px rgba(255, 58, 18, 0.29);
    padding: 0;
    background: transparent;
  }
  .table-wrap.phase-play .hands-row.two .cards-row.active-cards-row {
    border-radius: 8px;
    box-shadow:
      0 0 20px rgba(255, 99, 34, 0.48),
      0 0 38px rgba(255, 120, 24, 0.42),
      0 0 58px rgba(255, 58, 18, 0.31);
    padding: 0;
  }
  .bet-amount-row-with-actions {
    width: 100%;
    justify-content: center;
  }
  .bet-input-shell {
    position: relative;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-height: 28px;
    padding: 0 8px;
    border-radius: 999px;
    background: rgba(0, 0, 0, 0.88);
    border: 1px solid rgba(232, 212, 139, 0.26);

  }
  .bet-amount-prefix {
    position: absolute;
    left: 8px;
    font-size: 11px;
    color: #f2e8d0;
    pointer-events: none;
  }
  .bet-amount-input {
    width: 64px;
    border: none;
    outline: none;
    background: transparent;
    color: #f2e8d0;
    font-family: 'Oswald', sans-serif;
    font-size: 14px;
    font-weight: 600;
    text-align: center;
    letter-spacing: 0.02em;
  }
  /* CHIP BUTTONS */
  .chip-btns { display: flex; gap: 3px; margin-top: 4px; flex-wrap: nowrap; overflow-x: auto; -webkit-overflow-scrolling: touch; justify-content: flex-start; }
  .chip-btn  {
    width: 42px; height: 42px; border-radius: 50%; padding: 0;
    border: none; background: transparent; overflow: hidden;
    transition: all 0.15s;
  }
  .chip-btn-level {
    width: auto;
    min-width: 76px;
    height: 40px;
    border-radius: 999px;
    padding: 0 12px;
    background: rgba(18, 28, 19, 0.9);
    border: 1px solid rgba(232, 212, 139, 0.35);
    color: #f2e8d0;
    font-size: 18px;
    font-weight: 700;
  }
  .chip-btn img { width: 42px; height: 42px; display: block; }
  .chip-btn:disabled { opacity: 0.2; }
  .chip-btn.sb-target { box-shadow: 0 0 0 2px #e8d48b; border-radius: 50%; }

  .btn-clear  { font-size: 12px; color: #bfb49a; background: none; border: 1px solid #2a5a3a; border-radius: 4px; padding: 1px 8px; margin-top: 2px; }

  /* SIDE BETS */
  .cards-area { position: relative; }
  .sb-and-cards { display: flex; flex-direction: row; align-items: center; gap: 4px; }
  .sb-col     { display: flex; flex-direction: column; gap: 6px; flex-shrink: 0; }
  .sb-col.sb-col-hidden {
    visibility: hidden;
    pointer-events: none;
  }
  .cards-col  { min-width: 104px; display: flex; flex-direction: column; align-items: center; }
  .cards-col.has-sidebets { --sidebet-center-offset: 0px; }

  .sb-box {
    width: 39px; min-width: 39px; max-width: 39px;
    height: 39px; min-height: 39px; max-height: 39px;
    border-radius: 7px;
    border: 2px dashed rgba(255,255,255,0.7);
    background: transparent;
    appearance: none;
    cursor: pointer;
    display: flex; flex-direction: column; align-items: center; justify-content: center;
    gap: 2px; padding: 3px;
    overflow: hidden;
    transition: all 0.15s;
    color: #ffffff;
    user-select: none;
    box-shadow: none;
    font: inherit;
  }
  .sb-box.sb-active {
    border-style: solid;
    border-color: rgba(232,212,139,0.68);
    background: rgba(38, 97, 66, 0.72);
    color: #e8d48b;
  }
  .sb-box.sb-selected {
    border-style: solid;
    border-color: #d4a840;
    background: rgba(212,168,64,0.18);
    box-shadow: 0 0 10px rgba(212,168,64,0.3);
    color: #f2e8d0;
  }
  .sb-box-label { font-size: 8px; font-weight: 700; text-align: center; line-height: 1; font-family: 'Oswald', sans-serif; letter-spacing: 0.04em; text-transform: uppercase; color: inherit; }
  .sb-box-amt   { font-size: 8px; font-weight: 700; color: inherit; line-height: 1; text-align: center; }
  .sb-box-wrap { position: relative; }
  .sb-x-btn {
    position: absolute; top: -5px; left: -5px;
    width: 15px; height: 15px; border-radius: 50%;
    background: #000; color: #fff;
    font-size: 8px; font-weight: 900; line-height: 1;
    border: none; cursor: pointer; padding: 0; z-index: 10;
    display: flex; align-items: center; justify-content: center;
  }
  .sb-box-editing {
    width: 72px; min-height: 52px;
    border-radius: 7px;
    border: 1.5px solid rgba(232,212,139,0.82);
    background: rgba(28, 88, 61, 0.88);
    display: flex; flex-direction: column; align-items: center; justify-content: center;
    gap: 3px; padding: 5px 4px;
    color: #f2e8d0;
  }
  .sb-wager-input {
    width: 60px;
    background: rgba(7, 26, 14, 0.92);
    border: 1px solid rgba(232,212,139,0.4);
    border-radius: 4px;
    color: #f2e8d0;
    font-family: inherit;
    font-size: 13px;
    text-align: center;
    padding: 3px 4px;
    outline: none;
  }
  .sb-wager-input:focus { border-color: #d4a840; box-shadow: 0 0 6px rgba(212,168,64,0.3); }

  /* Invisible spacer mirrors ghost width so card stacks stay at true screen center */
  .ghost-spacer { width: 104px; flex-shrink: 0; visibility: hidden; pointer-events: none; }

  .ghost-wrap { display: flex; flex-direction: column; align-items: center; justify-content: flex-start; padding-top: 28px; }
  .ghost-row {
    display: flex;
    align-items: center;
    justify-content: center;
    flex-wrap: nowrap;
    gap: 10px;
    width: 100%;
  }
  .btn-autoplay-image {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    padding: 0;
    border: 0;
    background: transparent;
    margin: 0;
  }
  .btn-autoplay-image img {
    display: block;
    width: 100%;
    height: auto;
  }
  .fixed-autoplay-button {
    position: fixed;
    right: 18px;
    top: 0;
    width: 70px;
    z-index: 31;
  }
  .dock-autoplay-button {
    position: absolute;
    right: 10px;
    bottom: 0;
    width: 70px;
    z-index: 2;
  }
  .ghost {
    width: 104px; height: 146px; border-radius: 8px;
    border: 2.5px dashed rgba(255,255,255,0.55);
    background: transparent;
    appearance: none;
    cursor: pointer;
    display: flex; align-items: center; justify-content: center;
    font-size: 28px; color: rgba(255,255,255,0.55); opacity: 1;
    transition: all 0.2s;
    font: inherit;
  }
  .ghost:hover { opacity: 1; border-color: rgba(255,255,255,0.72); }

  .btn-remove { display: none; }
  .btn-remove-x {
    position: absolute;
    top: -10px;
    right: -10px;
    z-index: 10;
    width: 22px;
    height: 22px;
    border-radius: 50%;
    border: 1px solid rgba(242,232,208,0.35);
    background: rgba(7,26,14,0.9);
    color: #bfb49a;
    font-size: 16px;
    line-height: 1;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 0;
    opacity: 0.7;
    cursor: pointer;
  }
  .btn-remove-x:hover { opacity: 1; color: #ef5350; border-color: #ef5350; }

  /* BOTTOM DOCK */
  .bottom-dock {
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    flex-shrink: 0;
    padding: 0 4px 8px;
    z-index: 10;
    background: linear-gradient(to bottom, rgba(7,26,14,0) 0%, #071a0e 16px);
    padding-top: 16px;
  }

  /* CENTERED DEAL */
  .center-deal-wrap {
    display: flex;
    justify-content: center;
    padding: 8px 0 0;
    flex-shrink: 0;
    position: relative;
  }
  .center-deal-wrap .btn-deal {
    flex: 0 0 min(402px, calc((100% - 12px) * 0.67));
    width: min(402px, calc((100% - 12px) * 0.67));
    max-width: min(402px, calc((100% - 12px) * 0.67));
    min-height: 52px;
    font-size: 20px;
  }

  .action-area-fixed { display: flex; flex-direction: column; justify-content: flex-end; }
  .action-area-spacer { flex: 1; }
  .action-wager-label {
    text-align: center;
    font-family: 'Oswald', sans-serif;
    font-size: 15px;
    font-weight: 600;
    color: rgba(232,212,139,0.82);
    letter-spacing: 0.06em;
    text-transform: uppercase;
    margin-bottom: 3px;
  }
  .action-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 5px; margin-bottom: 5px; }
  /* Full-width red stop bar replaces action buttons during autoplay */
  .btn-stop-bar {
    width: 100%;
    min-height: 86px;
    padding: 0;
    background: #c62828;
    color: #fff;
    font-family: 'Oswald', sans-serif;
    font-size: 28px;
    font-weight: 700;
    border: none;
    border-radius: 8px;
    cursor: pointer;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    margin-bottom: 5px;
    transition: background 0.15s;
  }
  .btn-stop-bar-fixed {
    position: absolute;
    left: 0;
    right: 0;
    bottom: 0;
    width: 100%;
    border-radius: 0;
    margin-bottom: 0;
    min-height: 72px;
    padding-bottom: max(0px, env(safe-area-inset-bottom));
    z-index: 60;
  }
  .btn-stop-bar:hover { background: #e53935; }
  .btn-stop-bar { display: flex; align-items: center; justify-content: center; gap: 14px; }
  .stop-bar-label { font-size: 28px; font-weight: 700; letter-spacing: 0.08em; }
  .stop-bar-count  { font-size: 22px; font-weight: 600; opacity: 0.85; letter-spacing: 0.04em; }
  /* Fact bar — pinned bottom strip, no border */
  .fact-below-actions {
    width: 100%;
    max-width: 912px;
    margin: 0 auto;
    height: 50px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-family: 'Bebas Neue', 'Oswald', sans-serif;
    font-size: 22px;
    letter-spacing: 0.06em;
    color: rgba(242,232,208,0.65);
    text-align: center;
    padding: 0 16px;
    line-height: 1.2;
    background: none;
    border: none;
    box-shadow: none;
  }
  .btn-action {
    padding: 9px 0; border-radius: 7px; font-size: 16px; font-weight: 700;
    background: #1d4a2c; color: #f2e8d0; border: 1px solid #2a5a3a;
    font-family: 'Inter', sans-serif; letter-spacing: 0.04em; text-transform: uppercase;
  }
  .btn-action.dim { background: #172e20; color: #bfb49a; border-color: #172e20; }

  .deal-row {
    display: flex; gap: 6px; align-items: stretch; margin-bottom: 5px;
    max-width: 360px; margin-left: auto; margin-right: auto;
  }
  .btn-deal {
    flex: 1; padding: 12px 0; border-radius: 8px;
    border: none;
    background: #172e20; color: #bfb49a;
    font-size: 18px; font-weight: 700;
    opacity: 0.35;
    font-family: 'Oswald', sans-serif;
    letter-spacing: 0.06em;
    text-transform: uppercase;
  }
  .btn-deal.active {
    background: linear-gradient(135deg, #d4a840, #a88a30);
    color: #071a0e;
    opacity: 1;
  }
  .btn-auto-tab { padding: 0 16px; font-size: 15px; }

  .ctrl-row  { display: flex; align-items: center; justify-content: space-between; min-height: 28px; }
  .ctrl-row-inline { justify-content: flex-end; margin-top: 4px; }
  .ctrl-left { display: flex; gap: 6px; }
  .ctrl-right { min-width: 50px; text-align: center; }

  .btn-tab {
    font-size: 18px; padding: 4px 13px; border-radius: 4px;
    border: 1px solid #2a5a3a; background: transparent; color: #bfb49a;
  }
  .btn-tab.active { border-color: #e8d48b; background: rgba(232,212,139,0.12); color: #e8d48b; }

  .btn-stop { font-size: 14px; padding: 3px 10px; border-radius: 4px; border: 1px solid #ef5350; background: transparent; color: #ef5350; }

  /* PANELS */
  .panel {
    background: #172e20; border-radius: 6px; padding: 8px 10px; margin-top: 8px;
    animation: fadeIn 0.15s ease;
  }
  .panel-label { font-size: 21px; margin-bottom: 3px; opacity: 0.92; color: #dcb85c; }
  .panel-hint  { font-size: 17px; opacity: 0.5; margin-bottom: 6px; line-height: 1.4; }
  .mode-row,
  .speed-row   { display: flex; gap: 3px; margin-bottom: 6px; flex-wrap: wrap; }
  .btn-mode,
  .btn-speed   { flex: 1; padding: 5px 8px; font-size: 20px; border-radius: 4px; border: 1px solid #2a5a3a; background: transparent; color: #bfb49a; min-width: 88px; }
  .btn-mode.active,
  .btn-speed.active { border-color: #e8d48b; background: rgba(232,212,139,0.12); color: #e8d48b; }
  .mode-hint { min-height: 34px; }

  .rounds-row { display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; }
  .rounds-ctrl { display: flex; align-items: center; gap: 3px; }
  .rounds-ctrl button {
    width: 22px; height: 22px; border-radius: 4px;
    border: 1px solid #2a5a3a; background: #071a0e; color: #bfb49a;
    font-size: 16px; font-weight: 700;
    display: flex; align-items: center; justify-content: center;
  }
  .rounds-ctrl span { font-size: 22px; width: 36px; text-align: center; font-weight: 700; }
  .btn-auto-toggle {
    width: 100%; padding: 8px 0; border-radius: 5px; border: none;
    font-size: 21px; font-weight: 700; background: #4caf50; color: #fff;
  }
  .btn-auto-toggle.stop { background: #ef5350; }
  .autoplay-panel {
    background:
      linear-gradient(180deg, rgba(18, 24, 20, 0.96) 0%, rgba(10, 14, 12, 0.98) 100%);
    border: 1px solid rgba(212, 168, 64, 0.28);
    border-radius: 14px;
    box-shadow:
      0 14px 34px rgba(0, 0, 0, 0.38),
      inset 0 1px 0 rgba(255, 232, 176, 0.08);
    backdrop-filter: blur(10px);
  }
  .autoplay-panel .panel-label {
    color: #ffffff;
    font-family: 'Oswald', sans-serif;
    letter-spacing: 0.06em;
    text-transform: uppercase;
  }
  .autoplay-panel .panel-hint {
    color: rgba(255, 255, 255, 0.82);
    opacity: 1;
  }
  .autoplay-panel .btn-mode,
  .autoplay-panel .btn-speed {
    border-radius: 999px;
    border: 1px solid rgba(232, 212, 139, 0.2);
    background: rgba(255, 255, 255, 0.02);
    color: #ffffff;
    box-shadow: inset 0 1px 0 rgba(255,255,255,0.03);
  }
  .autoplay-panel .btn-mode.active,
  .autoplay-panel .btn-speed.active {
    border-color: rgba(212, 168, 64, 0.7);
    background: linear-gradient(180deg, rgba(212, 168, 64, 0.24) 0%, rgba(112, 79, 19, 0.22) 100%);
    color: #fff4cf;
    box-shadow:
      inset 0 1px 0 rgba(255, 235, 173, 0.18),
      0 0 0 1px rgba(212, 168, 64, 0.08);
  }
  .autoplay-panel .rounds-ctrl button {
    border-radius: 999px;
    border: 1px solid rgba(232, 212, 139, 0.24);
    background: rgba(255,255,255,0.04);
    color: #ffffff;
  }
  .autoplay-panel .rounds-ctrl span {
    color: #ffffff;
  }
  .autoplay-panel .btn-auto-toggle {
    border-radius: 999px;
    background: linear-gradient(180deg, #d6af48 0%, #9d7420 100%);
    color: #120f07;
    box-shadow: inset 0 1px 0 rgba(255, 241, 198, 0.3);
  }
  .autoplay-panel .btn-auto-toggle.stop {
    background: linear-gradient(180deg, #e36f56 0%, #b93d2e 100%);
    color: #fff4ef;
  }

  /* ABOUT */
  .about-panel { max-height: min(34vh, 320px); overflow-y: auto; }
  .about-text {
    font-size: 16px;
    line-height: 1.7;
    color: rgba(255, 255, 255, 0.9);
    font-style: normal;
    font-family: 'Oswald', sans-serif;
    letter-spacing: 0.02em;
  }

  /* RULES */
  .rules-panel { max-height: min(34vh, 320px); overflow-y: auto; }
  .panel-title  {
    font-size: 25px;
    font-weight: 700;
    margin-bottom: 8px;
    color: #ffffff;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    font-family: 'Oswald', sans-serif;
  }
  .rules-section {
    margin-bottom: 10px;
    font-size: 20px;
    color: #ffffff;
    font-family: 'Oswald', sans-serif;
  }
  .rules-section strong {
    color: #ffffff;
    font-weight: 700;
    letter-spacing: 0.03em;
    text-transform: uppercase;
  }
  .rules-text   {
    margin-left: 8px;
    margin-top: 4px;
    font-size: 16px;
    line-height: 1.6;
    color: rgba(255, 255, 255, 0.9);
    font-family: 'Oswald', sans-serif;
    letter-spacing: 0.02em;
  }
  .rules-text-sm { font-size: 14px; opacity: 0.82; color: rgba(255,255,255,0.82); }
  .rules-text.rtp { font-size: 14px; opacity: 0.78; color: rgba(255,255,255,0.78); }
  .payout-table { width: 100%; font-size: 15px; margin-top: 6px; border-collapse: collapse; }
  .payout-table td, .payout-table th { padding: 3px 6px; vertical-align: top; }
  .payout-table td:first-child { font-weight: 600; white-space: nowrap; opacity: 0.9; }
  .payout-table .rules-example { font-size: 13px; opacity: 0.65; padding-left: 10px; }
  .strategy-table th { font-size: 13px; opacity: 0.6; font-weight: 600; text-align: center; padding-bottom: 4px; border-bottom: 1px solid rgba(212,168,64,0.15); }
  .strategy-table td { text-align: center; font-size: 13px; }
  .strategy-table td:first-child { text-align: left; opacity: 0.7; font-weight: 500; }
  .strategy-table tr:nth-child(even) td { background: rgba(255,255,255,0.03); }

  .btn-reload {
    width: 100%; padding: 8px 0; border-radius: 5px;
    border: 1px solid #2a5a3a; background: transparent;
    color: #f2e8d0; font-size: 15px; margin-top: 4px;
  }

  /* DESKTOP — fit full screen, no scroll */
  @media (min-width: 768px) {
    .table-wrap  { height: 100vh; overflow: hidden; }
    .felt        { overflow: hidden; padding: 2px 18px 0; }

    .balance     { font-size: 24px; }
    .balance-row { min-height: 38px; padding: 4px 20px 0; }
    .session-pill { font-size: 14px; }
    .nav-result-msg {
      position: absolute;
      top: 6px;
      left: 50%;
      transform: translateX(-50%);
      width: max-content;
      z-index: 4;
      pointer-events: none;
    }
    .balance-row .nav-result-text,
    .balance-row .nav-result-text.win,
    .balance-row .nav-result-text.lose {
      color: #d8b04f !important;
      text-shadow: 0 1px 0 rgba(0,0,0,0.4), 0 0 18px rgba(216,176,79,0.18);
    }

    .dealer-area        { min-height: 64px; gap: 10px; }
    .dealer-logo,
    .felt-logo-right { display: none; }
    .dealer-placeholder { height: 96px; }
    .hand-value         { font-size: 17px; padding: 2px 11px; }
    .dealer-pays-wrap { display: none; }

    .card        { width: 97px; height: 158px; border-radius: 9px; }
    .card.small  { width: 97px; height: 158px; }

    .card-tl     { top: 10px; left: 12px; }
    .card-br     { bottom: 10px; right: 12px; }
    .card.small .card-tl { top: 10px; left: 12px; }
    .card.small .card-br { bottom: 10px; right: 12px; }

    .card-rank    { font-size: 19px; }
    .card-suit-sm { font-size: 15px; }
    .card-center  { font-size: 37px; }
    .card.small .card-rank    { font-size: 19px; }
    .card.small .card-suit-sm { font-size: 16px; }
    .card.small .card-center  { font-size: 39px; }

    .card-placeholder       { width: 97px; height: 158px; }
    .card-placeholder.small { width: 97px; height: 158px; }

    .hands-row      { min-height: 0; gap: 16px; align-items: flex-start; }
    .hands-row.multi{ gap: 10px; }

    .hv-bubble   { font-size: 15px; padding: 2px 10px; }
    .bet-bar { margin-top: 1px; gap: 2px; }
    .wager-label { font-size: 17px; }
    .bet-quick-actions { gap: 6px; padding: 3px; }
    .bet-quick-btn { min-width: 54px; min-height: 28px; font-size: 15px; }
    .bet-input-shell { padding: 3px 8px; }
    .bet-amount-prefix { font-size: 14px; }
    .bet-amount-input { width: 84px; font-size: 18px; }

    .chip-btn     { width: 56px; height: 56px; }
    .chip-btn img { width: 56px; height: 56px; }
    .chip-btns    { gap: 5px; margin-top: 6px; flex-wrap: nowrap; justify-content: center; overflow-x: visible; }

    .sb-and-cards { gap: 1px; align-items: flex-start; }
    .sb-box       { width: 68px; min-height: 50px; }
    .sb-box-label { font-size: 10px; }
    .sb-box-amt   { font-size: 12px; }
    .sb-col       { gap: 5px; }
    .cards-area   { gap: 7px; }

    .ghost-wrap { padding-top: 0; }
    .ghost-row { gap: 8px; }
    .ghost { width: 97px; height: 158px; font-size: 28px; }
    .ghost-autoplay { width: min(88px, 22vw); }
    .ghost-spacer { width: 97px; }
    .cards-col { min-width: 97px; }

    .divider-label {
      color: #d8b04f;
      opacity: 1;
      text-shadow: 0 1px 0 rgba(0,0,0,0.35);
    }
    .action-wager-label {
      color: #ffffff;
      opacity: 1;
      text-shadow: 0 1px 0 rgba(0,0,0,0.35);
    }

    .fact-row.table-layout {
      width: min(960px, 100%);
      margin: 0 auto 2px;
      padding: 3px 2px 2px;
      grid-template-columns: minmax(260px, 340px) minmax(360px, 1fr);
      gap: 18px;
    }
    .fact-block { align-items: center; }
    .fact-caption,
    .fact { text-align: center; }
    .fact-caption { font-size: 20px; }
    .fact      { font-size: 24px; max-width: 760px; }
    .bet-entry-toggle { gap: 4px; padding: 3px; }
    .bet-entry-btn { min-width: 68px; min-height: 30px; font-size: 15px; }
    .felt-menu {
      padding: 8px 0 4px;
    }
    .btn-next-centered {
      width: min(560px, 70vw);
      min-height: 72px;
      font-size: 30px;
    }

    .msg-text  { font-size: 22px; }
    .msg-text.bad-beat { font-size: 28px; }

    .center-deal-wrap .btn-deal { min-height: 56px; font-size: 22px; }
    .bottom-dock { padding: 0 8px 10px; }
    .cards-row { flex-wrap: nowrap; }
  }

  /* ── MOBILE OPTIMIZATIONS (max 767px) ─────────────────────────────────── */
  @media (max-width: 767px) {
    .table-wrap {
      position: relative;
      height: 100dvh;
      min-height: 100dvh;
      overflow: hidden;
      background: none !important;
      --mobile-geometry-scale: 0.9;
      --mobile-zoom: 0.9;
    }
    .table-wrap[class*="felt-theme-"] {
      background: none !important;
    }
    .table-wrap::before {
      content: "";
      position: fixed;
      inset: 0;
      pointer-events: none;
      z-index: 0;
      background: var(--table-texture-image, url('/felt-green-base.png'));
      background-size: cover;
      background-position: center top;
      background-repeat: no-repeat;
    }
    .table-wrap.felt-theme-velvet-blue { --table-texture-image: url('/velvet-blue-base.png'); }
    .table-wrap.felt-theme-velvet-green { --table-texture-image: url('/velvet-emerald-base.png'); }
    .table-wrap.felt-theme-velvet-black { --table-texture-image: url('/velvet-black-base.png'); }
    .table-wrap.felt-theme-ridge-blue { --table-texture-image: url('/ridge-blue-base.png'); }
    .table-wrap.felt-theme-ridge-green { --table-texture-image: url('/ridge-green-base.png'); }
    .table-wrap.felt-theme-ridge-black { --table-texture-image: url('/ridge-black-base.png'); }
    .table-wrap.felt-theme-felt-blue { --table-texture-image: url('/felt-blue-base.png'); }
    .table-wrap.felt-theme-felt-green { --table-texture-image: url('/felt-green-base.png'); }
    .table-wrap.felt-theme-felt-black { --table-texture-image: url('/felt-black-base.png'); }
    .table-wrap > * {
      position: relative;
      z-index: 1;
    }
    .table-wrap.phase-bet {
      --vertical-guide-offset: -106px;
      /* Mobile bet-screen anchor lock */
      --bet-logo-top: calc(max(4px, env(safe-area-inset-top)) + 8px);
      --bet-divider-top: calc(max(4px, env(safe-area-inset-top)) + 150px);
      --bet-single-hand-top: 126px;
      --bet-two-hand-top: 132px;
      --bet-hands-stack-top: 0px;
    }
    .table-wrap.phase-play-single-hand {
      --vertical-guide-offset: 0px;
    }
    .table-wrap.phase-result-single-hand {
      --vertical-guide-offset: 0px;
    }
    .table-wrap.phase-result-two-hand {
      --vertical-guide-offset: 0px;
    }
    .table-wrap.phase-play-single-hand::after {
      content: none;
      position: absolute;
      top: 0;
      bottom: 0;
      left: calc(50% + var(--vertical-guide-offset, 0px));
      width: 1px;
      transform: translateX(-0.5px);
      background: linear-gradient(
        180deg,
        rgba(212, 168, 64, 0.08) 0%,
        rgba(212, 168, 64, 0.34) 16%,
        rgba(212, 168, 64, 0.42) 50%,
        rgba(212, 168, 64, 0.34) 84%,
        rgba(212, 168, 64, 0.08) 100%
      );
      box-shadow: 0 0 2px rgba(212, 168, 64, 0.24);
      pointer-events: none;
      z-index: 3;
    }
    .table-wrap.phase-bet .bottom-dock,
    .table-wrap.phase-bet .mobile-options-drawer,
    .table-wrap.phase-bet .mobile-options-launch,
    .table-wrap.phase-play .bottom-dock,
    .table-wrap.phase-play .mobile-options-launch {
      position: relative;
      z-index: 4;
    }
    .table-wrap.phase-bet .mobile-options-launch,
    .table-wrap.phase-play .mobile-options-launch,
    .table-wrap.phase-result .mobile-options-launch,
    .table-wrap.phase-bet .mobile-options-drawer,
    .table-wrap.phase-play .mobile-options-drawer,
    .table-wrap.phase-result .mobile-options-drawer {
      background: transparent !important;
      backdrop-filter: none !important;
    }
    .table-wrap.phase-play .mobile-options-drawer,
    .table-wrap.phase-result .mobile-options-drawer {
      position: fixed !important;
      top: calc(max(6px, env(safe-area-inset-top)) + 40px) !important;
      right: 12px !important;
      left: auto !important;
      width: min(120px, calc(100vw - 24px)) !important;
      z-index: 46 !important;
      padding: 4px 0 0 !important;
      pointer-events: none !important;
      overflow: visible !important;
    }

    /* Hands row takes natural height so felt can scroll past it */
    .hands-row {
      flex: 0 0 auto;
      gap: 10px;
      width: 100%;
      flex-wrap: wrap;
      justify-content: center;
      padding-top: 20px;
      padding-bottom: 8px;
    }
    .felt.single-hand .hands-row {
      padding-top: 42px;
    }
    .table-wrap.phase-bet .hands-row {
      padding-top: 20px;
    }
    .table-wrap.phase-bet .felt.single-hand .hands-row {
      padding-top: 68px;
    }
    .table-wrap.phase-bet .hands-row.two {
      padding-top: var(--bet-two-hand-top);
    }
    .table-wrap.phase-bet .hands-stack {
      position: relative;
      top: var(--bet-hands-stack-top);
      left: 0;
      right: 0;
      margin: 0;
    }
    .hands-row.multi { gap: 8px; }
    .hands-row.two {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: flex-start;
      gap: 22px;
      min-height: 0;
      padding-top: 22px;
      padding-bottom: 22px;
      width: 100%;
    }
    .hands-row.two .hand-col {
      width: 100%;
      flex: 0 0 auto;
      display: flex;
      justify-content: center;
      align-items: center;
    }
    .table-wrap.phase-bet .hands-row.two .hand-col:first-of-type {
      transform: translateY(50px);
    }
    .table-wrap.phase-bet .hands-row.two .hand-col:last-of-type {
      transform: translateY(90px);
    }
    .table-wrap.phase-play .hands-row.two .hand-col:first-of-type,
    .table-wrap.phase-result-two-hand .hands-row.two .hand-col:first-of-type {
      transform: translateY(68px);
    }
    .table-wrap.phase-play .hands-row.two .hand-col:last-of-type,
    .table-wrap.phase-result-two-hand .hands-row.two .hand-col:last-of-type {
      transform: translateY(58px);
    }
    .hands-row.two .cards-area {
      width: min(100%, 308px);
      margin: 0 auto;
      transform: scale(0.875);
      transform-origin: top center;
    }
    .hands-row.two .cards-col {
      align-items: center;
    }
    .hands-row.two .sb-and-cards {
      width: min(100%, 308px);
      align-items: flex-start;
      gap: 4px;
      margin: 0 auto;
    }
    .hands-row.two .sb-col {
      flex: 0 0 48px;
      width: 48px;
      gap: 4px;
    }
    .hands-row.two .cards-col.has-sidebets {
      --sidebet-center-offset: 0px;
      transform: none;
    }
    .hands-row.two .cards-col.has-sidebets .hv-bubble,
    .hands-row.two .cards-col.has-sidebets .bet-bar {
      transform: none;
    }
    .hands-row.two .cards-row {
      align-items: flex-start;
      justify-content: center;
      min-height: 0;
      transform: translateX(-10px);
    }
    .hands-row.two .card,
    .hands-row.two .card.small,
    .hands-row.two .card-placeholder,
    .hands-row.two .card-placeholder.small {
      width: 86px;
      height: 146px;
      border-radius: 8px;
    }
    .hands-row.two .card::before,
    .hands-row.two .card.small::before {
      border-radius: 8px;
    }
    .hands-row.two .card-rank {
      font-size: 17px;
    }
    .hands-row.two .card-suit-sm {
      font-size: 14px;
    }
    .hands-row.two .card-center {
      font-size: 34px;
    }
    .hands-row.two .bet-bar {
      width: auto;
      min-width: 0;
      margin-left: 0;
      margin-top: 1px;
      transform: none;
      align-self: center;
    }
    .hands-row.two .hv-bubble {
      font-size: 15px;
      padding: 2px 10px;
      border-radius: 10px;
      margin-bottom: 4px;
      align-self: center;
    }
    /* ── SPLIT LAYOUT ── */
    /* Make the row the offset origin for the absolutely-positioned split-right hand */
    .hands-row.has-split {
      position: relative;
    }
    /* Split-right is taken out of flex flow and pinned to the right.
       All sizing and transform are set via inline style on the element. */
    .hands-row.two.has-split .hand-col.split-right .hv-bubble {
      font-size: calc(15px * 0.7) !important;
      padding: 1px 7px !important;
      border-radius: 7px !important;
    }
    /* ── END SPLIT LAYOUT ── */
    .hand-col { width: 100%; align-items: center; }
    .cards-col { width: auto; min-width: 0; }
    .cards-area { width: auto; }
    .sb-and-cards {
      flex-direction: row;
      align-items: flex-start;
      justify-content: center;
      gap: 4px;
      width: min(100%, 308px);
      margin: 0 auto;
      overflow: visible;
    }
    .sb-col {
      flex: 0 0 48px;
      flex-direction: column;
      justify-content: flex-start;
      width: 48px;
      margin-top: 0;
      gap: 4px;
    }
    .bet-bar {
      margin-left: 0;
      width: auto;
      max-width: none;
      align-self: center;
    }
    .felt.single-hand .bet-bar {
      margin-left: 24px;
    }
    .hands-row.multi:not(.split-row):not(.two) .bet-bar {
      margin-left: 24px;
    }
    .ghost-spacer { display: none; }
    .ghost-wrap {
      width: 100%;
      padding-top: 6px;
    }
    .felt.single-hand .ghost-wrap {
      padding-top: 24px;
    }
    .ghost-row {
      width: 100%;
    }
    .ghost {
      width: min(200px, calc(100% - 96px));
      height: 54px;
      border-radius: 16px;
    }
    .ghost-placeholder {
      visibility: hidden;
      pointer-events: none;
    }
    .ghost-autoplay {
      width: 88px;
      flex: 0 0 auto;
    }
    .fixed-autoplay-button {
      right: 18px;
      top: 0;
      width: 54px;
    }
    .mobile-autoplay-launch {
      display: flex;
      justify-content: center;
      width: 100%;
      padding: 4px 0 0;
    }

    /* Sticky bottom dock — deal/action buttons always visible while scrolling */
    .bottom-dock {
      position: fixed;
      left: 0;
      right: 0;
      bottom: 0;
      margin-top: 0;
      z-index: 30;
      display: flex;
      flex-direction: column;
      background: transparent;
      padding: 8px 10px env(safe-area-inset-bottom);
    }

    /* Felt: native-size layout (no scaled canvas) with shared table texture */
    .felt {
      padding: 30px 10px 0;
      padding-bottom: 176px;
      transform: scale(var(--mobile-zoom));
      transform-origin: top center;
      width: calc(100% / var(--mobile-zoom));
      margin-left: calc((100% - (100% / var(--mobile-zoom))) / 2);
      margin-right: 0;
      background: transparent !important;
      overflow: hidden;
      overscroll-behavior: none;
    }
    .felt::before {
      display: none;
    }
    .table-wrap.phase-play .felt {
      display: flex;
      flex-direction: column;
      justify-content: flex-start;
      gap: 0;
    }
    .felt.single-hand {
      padding-top: 34px;
    }
    .table-wrap.phase-bet .felt.single-hand {
      padding-top: var(--bet-single-hand-top);
    }
    .action-area-fixed {
      margin-bottom: 0;
    }

    /* Floating top controls over felt */
    .balance      { font-size: 16px; }
    .balance-row  {
      position: fixed;
      top: max(4px, env(safe-area-inset-top));
      left: 0;
      right: 0;
      z-index: 45;
      display: block;
      min-height: 0;
      padding: 2px 12px 0;
      background: transparent;
      border-bottom: none;
      pointer-events: none;
      overflow: visible;
    }
  .header-actions {
    pointer-events: auto;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 10px;
    width: 100%;
    overflow: visible;
  }
  .mobile-balance-slot {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-height: 34px;
    padding: 0 12px;
    border-radius: 999px;
    border: 1px solid rgba(232, 212, 139, 0.25);
    background: transparent;
    color: #ffffff;
    font-family: 'Oswald', sans-serif;
    font-size: 10.24px;
    font-weight: 700;
    letter-spacing: 0.02em;
    white-space: nowrap;
    box-shadow: none;
  }
    .utility-btns {
      width: auto;
      min-width: 0;
      justify-content: flex-start;
      flex-wrap: nowrap;
      gap: 4px;
      overflow: hidden;
    }
    .session-meta {
      display: none;
    }
    .balance-row,
    .balance-subrow,
    .header-actions,
    .mobile-balance-slot,
    .session-meta,
    .balance-meta-mobile {
      display: none !important;
    }
    .balance-pill-stack {
      position: fixed;
      top: max(6px, env(safe-area-inset-top));
      left: 12px;
      z-index: 46;
      display: flex;
      flex-direction: column;
      align-items: flex-start;
      gap: 3px;
    }
    .balance-pill-stack .total-wager-sub {
      font-size: 10.24px;
      font-family: 'Oswald', sans-serif;
      font-weight: 700;
      letter-spacing: 0.12em;
      color: #d4a840;
      white-space: nowrap;
      padding-left: 4px;
      text-transform: uppercase;
      text-shadow:
        0 1px 0 rgba(0,0,0,0.42),
        0 0 8px rgba(4, 24, 14, 0.55);
    }
    .mobile-balance-pill {
      position: static;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      min-height: 34px;
      padding: 0 12px;
      border-radius: 999px;
      border: 1px solid rgba(232, 212, 139, 0.25);
      background: rgba(10, 30, 19, 0.34);
      color: #ffffff;
      font-family: 'Oswald', sans-serif;
      font-size: 10.24px;
      font-weight: 700;
      letter-spacing: 0.02em;
      line-height: 1;
      white-space: nowrap;
      box-shadow: none;
      backdrop-filter: blur(2px);
    }
    .mobile-options-launch {
      position: fixed;
      top: max(6px, env(safe-area-inset-top));
      right: 12px;
      z-index: 46;
      display: inline-flex !important;
      align-items: center;
      justify-content: center;
      width: auto !important;
      min-width: 0 !important;
      max-width: none !important;
      flex: 0 0 auto !important;
      min-height: 34px !important;
      padding: 0 12px !important;
      border-radius: 999px !important;
      border: 1px solid rgba(232, 212, 139, 0.25) !important;
      background: rgba(10, 30, 19, 0.34) !important;
      color: #ffffff !important;
      font-family: 'Oswald', sans-serif !important;
      font-size: 10.24px !important;
      font-weight: 700 !important;
      letter-spacing: 0.02em !important;
      line-height: 1;
      box-shadow: none !important;
      backdrop-filter: blur(2px);
    }
    .mobile-options-drawer {
      position: fixed;
      top: calc(max(6px, env(safe-area-inset-top)) + 40px);
      right: 12px;
      left: auto;
      width: min(120px, calc(100vw - 24px));
      z-index: 46;
      padding: 4px 0 0;
      gap: 6px;
      pointer-events: none;
    }
    .mobile-options-drawer.full-panel-open {
      top: 0;
      right: 0;
      left: 0;
      bottom: 0;
      width: 100vw;
      min-height: 100dvh;
      padding: max(56px, calc(env(safe-area-inset-top) + 52px)) 12px calc(env(safe-area-inset-bottom) + 12px);
      background: rgba(4, 16, 10, 0.94);
      backdrop-filter: blur(10px);
      justify-content: flex-start;
      overflow-y: auto;
      pointer-events: auto;
    }
    .table-wrap.phase-bet .mobile-options-drawer {
      position: fixed !important;
      top: calc(max(6px, env(safe-area-inset-top)) + 40px) !important;
      right: 12px !important;
      left: auto !important;
      width: min(120px, calc(100vw - 24px)) !important;
      z-index: 46 !important;
      padding: 4px 0 0 !important;
      pointer-events: none !important;
    }
    .table-wrap.phase-bet .mobile-options-drawer.full-panel-open,
    .table-wrap.phase-play .mobile-options-drawer.full-panel-open,
    .table-wrap.phase-result .mobile-options-drawer.full-panel-open {
      top: 0 !important;
      right: 0 !important;
      left: 0 !important;
      bottom: 0 !important;
      width: 100vw !important;
      min-height: 100dvh !important;
      padding: max(56px, calc(env(safe-area-inset-top) + 52px)) 12px calc(env(safe-area-inset-bottom) + 12px) !important;
      background: rgba(4, 16, 10, 0.94) !important;
      backdrop-filter: blur(10px) !important;
      justify-content: flex-start !important;
      overflow-y: auto !important;
      pointer-events: auto !important;
    }
    .mobile-options-column {
      display: grid;
      grid-template-columns: 1fr;
      gap: 4px;
      pointer-events: auto;
    }
    .mobile-options-drawer.full-panel-open .mobile-options-column {
      position: sticky;
      top: 0;
      z-index: 1;
      background: linear-gradient(180deg, rgba(4, 16, 10, 0.98) 0%, rgba(4, 16, 10, 0.82) 100%);
      padding-bottom: 8px;
    }
    .felt-panel-inline,
    .rules-panel-inline,
    .about-panel-inline {
      pointer-events: auto;
    }
    .mobile-options-drawer.full-panel-open .felt-panel-inline,
    .mobile-options-drawer.full-panel-open .rules-panel-inline,
    .mobile-options-drawer.full-panel-open .about-panel-inline {
      width: 100%;
      max-width: none;
      flex: 1 1 auto;
      height: calc(100dvh - max(116px, calc(env(safe-area-inset-top) + 112px)) - env(safe-area-inset-bottom));
      min-height: calc(100dvh - max(116px, calc(env(safe-area-inset-top) + 112px)) - env(safe-area-inset-bottom));
      margin-top: 0;
      padding: 16px 16px 24px;
      border-radius: 18px;
      overflow-y: auto;
      background:
        linear-gradient(180deg, rgba(18, 24, 20, 0.96) 0%, rgba(10, 14, 12, 0.98) 100%);
      border: 1px solid rgba(212, 168, 64, 0.28);
      box-shadow:
        0 14px 34px rgba(0, 0, 0, 0.38),
        inset 0 1px 0 rgba(255, 232, 176, 0.08);
      backdrop-filter: blur(10px);
    }
    .btn-options-item,
    .btn-autoplay-cta {
      font-size: 10px !important;
      min-height: 24px !important;
      padding: 3px 8px !important;
      border-radius: 999px !important;
    }
    .btn-options-toggle {
      min-height: 34px !important;
      padding: 0 12px !important;
      border-radius: 999px !important;
      border: 1px solid rgba(232, 212, 139, 0.25) !important;
      background: transparent !important;
      color: #ffffff !important;
      font-family: 'Oswald', sans-serif !important;
      font-size: 10.24px !important;
      font-weight: 700 !important;
      letter-spacing: 0.02em !important;
      line-height: 1;
      box-shadow: none !important;
    }
    .mobile-options-launch.btn-options-toggle {
      position: fixed !important;
      top: max(6px, env(safe-area-inset-top)) !important;
      right: 12px !important;
      left: auto !important;
      display: inline-flex !important;
      align-items: center !important;
      justify-content: center !important;
      width: fit-content !important;
      min-width: 0 !important;
      max-width: none !important;
      white-space: nowrap !important;
      background: rgba(10, 30, 19, 0.34) !important;
    }
    .launch-warning,
    .replay-banner {
      position: fixed;
      top: calc(max(6px, env(safe-area-inset-top)) + 44px);
      left: 12px;
      right: 12px;
      width: auto;
      margin: 0;
      z-index: 44;
    }
    .btn-utility {
      font-size: 10px !important;
      min-height: 22px !important;
      padding: 1px 7px !important;
      border-radius: 10px !important;
    }
    .balance {
      font-size: 20px;
      line-height: 1;
    }
    .rgs-status {
      font-size: 11px;
      margin-left: 6px;
    }
    .nav-result-msg {
      display: none;
    }

    /* Compact felt logo + divider */
    .felt-logo-row  { padding: 4px 0 8px; }
    .table-wrap.phase-bet .felt-logo-row {
      position: fixed;
      top: var(--bet-logo-top);
      left: 0;
      right: 0;
      margin-top: 0;
      padding-top: 0;
      padding-bottom: 0;
      z-index: 2;
      pointer-events: none;
    }
    .felt-logo      { width: 52px; height: 52px; }
    .felt-logo-large {
      opacity: 0.94;
      width: min(360px, 96vw);
      height: 177px;
      transform: scale(1.648);
      transform-origin: center center;
    }
    .felt-logo-right,
    .dealer-logo { display: none; }
    .table-wrap.phase-play .felt-logo-right,
    .table-wrap.phase-play .dealer-logo,
    .table-wrap.phase-play .hand-value {
      display: none;
    }
    .hands-row.multi .card-custom-art {
      transform-origin: center center;
      transform: scale(1.08);
    }
    .table-wrap.phase-play .hands-row.multi .card.card-custom.jack-clubs-custom .card-custom-art,
    .table-wrap.phase-result .hands-row.multi .card.card-custom.jack-clubs-custom .card-custom-art {
      transform: scale(1);
    }
    .felt.single-hand .card-custom-art {
      transform-origin: center center;
      transform: scale(1.03);
    }

    /* Compact fact block */
    .fact-block { width: 140px; font-size: 11px; padding: 8px 10px; top: 8px; right: 8px; left: auto; }

    /* Compact dealer */
    .dealer-area        { min-height: 52px; gap: 6px; padding-top: 4px; padding-bottom: 4px; }
    .dealer-placeholder { height: 64px; }
    .dealer-cards-col   { max-width: 100%; }
    .dealer-area .card-wrap { flex-shrink: 0; }
    .dealer-cards-col .card,
    .dealer-cards-col .card.small {
      width: 92px;
      height: 156px;
      border-radius: 8px;
    }
    .dealer-cards-col .card-rank { font-size: 18px; }
    .dealer-cards-col .card-suit-sm { font-size: 15px; }
    .dealer-cards-col .card-center { font-size: 36px; }
    .hands-row.multi ~ .dealer-area .card,
    .hands-row.multi ~ .dealer-area .card.small,
    .hands-row.multi ~ .dealer-area .card-placeholder,
    .hands-row.multi ~ .dealer-area .card-placeholder.small,
    .hands-row.multi .card,
    .hands-row.multi .card.small,
    .hands-row.multi .card-placeholder,
    .hands-row.multi .card-placeholder.small {
      width: 92px;
      height: 156px;
      border-radius: 8px;
    }
    .hands-row.multi ~ .dealer-area .card-rank,
    .hands-row.multi .card-rank { font-size: 18px; }
    .hands-row.multi ~ .dealer-area .card-suit-sm,
    .hands-row.multi .card-suit-sm { font-size: 15px; }
    .hands-row.multi ~ .dealer-area .card-center,
    .hands-row.multi .card-center { font-size: 36px; }
    .hand-value {
      background: linear-gradient(180deg, #e0b84c 0%, #b98b20 100%);
      border: 1px solid rgba(255, 235, 173, 0.45);
      box-shadow: inset 0 1px 0 rgba(255,255,255,0.28), 0 4px 10px rgba(0,0,0,0.18);
      color: #1e1605;
      font-size: 15px;
      font-weight: 600;
      padding: 2px 10px;
      margin-bottom: 2px;
      border-radius: 12px;
    }
    .dealer-pays-wrap   { display: none; }
    .table-wrap.phase-play .dealer-area {
      min-height: 168px;
      flex: 0 0 168px;
      gap: 6px;
      margin-top: -20px;
      margin-bottom: 6px;
      justify-content: center;
      align-items: flex-start;
    }
    .table-wrap.phase-play .hand-value {
      display: flex;
      margin: 0 0 4px 0;
      font-size: 15px;
      padding: 2px 10px;
      position: relative;
      top: auto;
      left: auto;
      transform: none;
      z-index: 1;
      pointer-events: none;
    }
    .table-wrap.phase-play:not(.phase-play-single-hand) .hand-value {
      margin: 0;
      font-size: 13px;
      padding: 2px 8px;
      border-radius: 10px;
    }
    .table-wrap.phase-play .dealer-cards-col {
      transform: none;
      width: 100%;
      align-items: center;
      gap: 6px;
      margin-top: 0;
    }
    .table-wrap.phase-play:not(.phase-play-single-hand) .dealer-cards-col {
      gap: 5px;
    }
    .table-wrap.phase-play .dealer-cards-col .card,
    .table-wrap.phase-play .dealer-cards-col .card.small {
      width: 92px;
      height: 156px;
      border-radius: 8px;
    }
    .table-wrap.phase-play .dealer-cards-col .card-rank { font-size: 18px; }
    .table-wrap.phase-play .dealer-cards-col .card-suit-sm { font-size: 15px; }
    .table-wrap.phase-play .dealer-cards-col .card-center { font-size: 36px; }
    .table-wrap.phase-play .dealer-area .cards-row {
      overflow: visible;
      min-height: 156px;
    }
    .table-wrap.phase-play .dealer-pays-wrap {
      display: grid;
      place-items: center;
      width: 100vw;
      min-height: 30px;
      margin: -16px calc(50% - 50vw) 10px;
      padding: 0;
      gap: 0;
      position: relative;
    }
    .table-wrap.phase-play .dealer-cards-col .dealer-pays-wrap {
      margin-top: 0;
    }
    .table-wrap.phase-play .dealer-pays-line {
      grid-area: 1 / 1;
      width: 100%;
      height: 1px;
      background: linear-gradient(
        90deg,
        rgba(212,168,64,0.14) 0%,
        rgba(212,168,64,0.42) 18%,
        rgba(212,168,64,0.52) 50%,
        rgba(212,168,64,0.42) 82%,
        rgba(212,168,64,0.14) 100%
      );
      box-shadow:
        0 1px 0 rgba(6, 24, 15, 0.45),
        0 -1px 0 rgba(255, 227, 160, 0.08);
      opacity: 0.88;
    }
    .table-wrap.phase-play .dealer-pays-copy {
      grid-area: 1 / 1;
      line-height: 1;
      font-size: 13px;
      letter-spacing: 0.12em;
      color: #d4a840;
      text-shadow:
        0 1px 0 rgba(0,0,0,0.42),
        0 0 8px rgba(4, 24, 14, 0.55);
      position: relative;
      z-index: 2;
    }
    .table-wrap.phase-play:not(.phase-play-single-hand) .dealer-pays-copy {
      transform: translateY(-12px);
    }
    .table-wrap.phase-play .mid-zone {
      display: none;
    }
    .table-wrap.phase-play .hands-row {
      flex: 1 1 auto;
      align-items: flex-start;
      justify-content: center;
      margin-top: 14px;
      margin-bottom: 0;
      gap: 8px;
      min-height: 0;
    }
    .table-wrap.phase-play-single-hand .hands-stack,
    .table-wrap.phase-result-single-hand .hands-stack {
      transform: translateY(14px) scale(1.08);
      transform-origin: top center;
    }
    .table-wrap.phase-bet .felt.single-hand .hands-stack {
      transform: translateY(-6px) scale(1.08);
      transform-origin: top center;
    }
    .table-wrap.phase-play .hands-row.multi {
      gap: 6px;
    }
    .table-wrap.phase-play .hand-col {
      justify-content: flex-start;
    }
    .table-wrap.phase-play .cards-area,
    .table-wrap.phase-play .cards-col {
      min-height: 0;
    }
    .table-wrap.phase-play .sb-col {
      gap: 4px;
    }
    .table-wrap.phase-play .sb-box,
    .table-wrap.phase-play .sb-box-editing {
      width: 38px;
      min-width: 38px;
      max-width: 38px;
      height: 38px !important;
      min-height: 38px !important;
      max-height: 38px;
      justify-content: center;
      align-items: center;
      gap: 0;
      padding: 0;
    }
    /* X button: center above top edge so it never overlaps the label */
    .table-wrap.phase-play .sb-x-btn {
      top: -7px;
      left: 50%;
      transform: translateX(-50%);
      width: 12px;
      height: 12px;
      font-size: 7px;
    }
    /* Active sidebet during play: stay locked at 39×39 */
    .table-wrap.phase-play .sb-box.sb-active {
      width: 39px !important;
      min-width: 39px !important;
      max-width: 39px !important;
      height: 39px !important;
      min-height: 39px !important;
      max-height: 39px !important;
      overflow: hidden !important;
      padding: 3px !important;
      gap: 2px !important;
      justify-content: center !important;
    }
    .table-wrap.phase-play .sb-box-label,
    .table-wrap.phase-play .sb-box-label-213 {
      width: 100%;
      margin: 0;
      display: flex;
      align-items: center;
      justify-content: center;
      text-align: center;
      line-height: 1;
      font-size: 8px;
    }
    .table-wrap.phase-play-single-hand .sb-box-label,
    .table-wrap.phase-play-single-hand .sb-box-label-213 {
      transform: none;
    }
    /* Lock single-hand play-phase sb-box to exactly 39×39 — same as screen 3 */
    .table-wrap.phase-play-single-hand .sb-box,
    .table-wrap.phase-play-single-hand .sb-box-editing,
    .table-wrap.phase-play-single-hand .sb-box.sb-active {
      width: 39px !important;
      min-width: 39px !important;
      max-width: 39px !important;
      height: 39px !important;
      min-height: 39px !important;
      max-height: 39px !important;
      overflow: hidden !important;
      padding: 3px !important;
      gap: 2px !important;
    }
    /* Remove label offset when active (amount takes the space) */
    .table-wrap.phase-play-single-hand .sb-box.sb-active .sb-box-label,
    .table-wrap.phase-play-single-hand .sb-box.sb-active .sb-box-label-213 {
      transform: none !important;
    }
    .table-wrap.phase-play .action-wager-label {
      margin-bottom: 0;
      font-size: 15.9px;
      color: #ffffff;
      text-shadow: 0 1px 0 rgba(0,0,0,0.42);
    }
    .table-wrap.phase-play .action-wager-label.multi-play-wager {
      display: none;
    }
    .table-wrap.phase-play-single-hand .action-wager-label {
      color: #ffffff !important;
      -webkit-text-fill-color: #ffffff;
      text-shadow: 0 1px 0 rgba(0,0,0,0.42);
    }
    .table-wrap.phase-play .bet-bar {
      margin-top: 0;
    }
    .table-wrap.phase-play .bottom-dock {
      padding-top: 6px;
      border-top: 1px solid rgba(212, 168, 64, 0.18);
      box-shadow: inset 0 14px 18px rgba(0, 0, 0, 0.16);
    }
    .table-wrap.phase-result .bottom-dock {
      background: transparent;
      border-top: none;
      box-shadow: none;
      padding-top: 4px;
    }
    .table-wrap.phase-result .action-area-fixed {
      background: transparent;
      display: none;
    }
    .table-wrap.phase-result .action-wager-label {
      margin-bottom: 2px;
    }
    .table-wrap.phase-result .action-result-msg {
      margin: 0 auto 4px;
      min-height: 0;
    }
    .table-wrap.phase-result .center-deal-wrap {
      padding-top: 0;
    }
    .felt.single-hand .dealer-area {
      min-height: 96px;
      gap: 6px;
      padding-top: 8px;
      padding-bottom: 8px;
    }
    .felt.single-hand .dealer-cards-col .card,
    .felt.single-hand .dealer-cards-col .card.small {
      width: 92px;
      height: 156px;
      border-radius: 8px;
    }
    .felt.single-hand .dealer-cards-col .card-hidden {
      position: relative;
      background: transparent;
      border: none;
      box-shadow: 0 3px 12px rgba(0,0,0,0.3);
    }
    .felt.single-hand .dealer-cards-col .card-hidden::before {
      content: none;
    }
    .felt.single-hand .dealer-cards-col .card-back-logo {
      position: absolute;
      inset: 0;
      z-index: 1;
      width: 100%;
      height: 100%;
      opacity: 1;
      object-fit: cover;
      filter: none;
    }
    .felt.single-hand .dealer-cards-col .card-rank { font-size: 18px; }
    .felt.single-hand .dealer-cards-col .card-suit-sm { font-size: 15px; }
    .felt.single-hand .dealer-cards-col .card-center { font-size: 36px; }
    .table-wrap.phase-play-single-hand .hands-row .card,
    .table-wrap.phase-play-single-hand .hands-row .card.small,
    .table-wrap.phase-result-single-hand .hands-row .card,
    .table-wrap.phase-result-single-hand .hands-row .card.small,
    .table-wrap.phase-play-single-hand .hands-row .card-placeholder,
    .table-wrap.phase-play-single-hand .hands-row .card-placeholder.small,
    .table-wrap.phase-result-single-hand .hands-row .card-placeholder,
    .table-wrap.phase-result-single-hand .hands-row .card-placeholder.small {
      width: 126px;
      height: 214px;
      border-radius: 9px;
    }
    .table-wrap.phase-play-single-hand .hands-row .card::before,
    .table-wrap.phase-play-single-hand .hands-row .card.small::before,
    .table-wrap.phase-result-single-hand .hands-row .card::before,
    .table-wrap.phase-result-single-hand .hands-row .card.small::before {
      border-radius: 9px;
    }
    .table-wrap.phase-play-single-hand .hands-row .card-rank,
    .table-wrap.phase-result-single-hand .hands-row .card-rank {
      font-size: 24px;
    }
    .table-wrap.phase-play-single-hand .hands-row .card-suit-sm,
    .table-wrap.phase-result-single-hand .hands-row .card-suit-sm {
      font-size: 19px;
    }
    .table-wrap.phase-play-single-hand .hands-row .card-center,
    .table-wrap.phase-result-single-hand .hands-row .card-center {
      font-size: 48px;
    }
    .table-wrap.phase-play-single-hand .hands-row .card,
    .table-wrap.phase-play-single-hand .hands-row .card.small,
    .table-wrap.phase-play-single-hand .hands-row .card-placeholder,
    .table-wrap.phase-play-single-hand .hands-row .card-placeholder.small {
      width: 158px;
      height: 268px;
      border-radius: 10px;
    }
    .table-wrap.phase-play-single-hand .hands-row .card::before,
    .table-wrap.phase-play-single-hand .hands-row .card.small::before {
      border-radius: 10px;
    }
    .table-wrap.phase-play-single-hand .hands-row .card-rank {
      font-size: 30px;
    }
    .table-wrap.phase-play-single-hand .hands-row .card-suit-sm {
      font-size: 24px;
    }
    .table-wrap.phase-play-single-hand .hands-row .card-center {
      font-size: 60px;
    }
    .felt.single-hand .hand-value {
      margin-bottom: 1px;
    }
    .sb-box,
    .sb-box-editing {
      width: 44px;
      min-height: 36px;
      padding: 2px 1px;
      gap: 1px;
      border-width: 2px;
      border-radius: 9px;
    }
    .sb-box-label {
      font-size: 9px;
      line-height: 1.02;
      letter-spacing: 0.03em;
    }
    .sb-box-amt {
      font-size: 10px;
    }
    .table-wrap.phase-bet .sb-col,
    .table-wrap.phase-play .sb-col,
    .table-wrap.phase-result .sb-col {
      gap: 3px;
    }
    .table-wrap.phase-bet .sb-and-cards,
    .table-wrap.phase-play .sb-and-cards,
    .table-wrap.phase-result .sb-and-cards {
      gap: 1px;
    }
    .table-wrap.phase-bet .felt.single-hand .sb-and-cards,
    .table-wrap.phase-play .felt.single-hand .sb-and-cards,
    .table-wrap.phase-result .felt.single-hand .sb-and-cards {
      gap: 2px;
    }
    .table-wrap.phase-bet .felt.single-hand .sb-col,
    .table-wrap.phase-play .felt.single-hand .sb-col,
    .table-wrap.phase-result .felt.single-hand .sb-col {
      margin-right: -1px;
    }
    .table-wrap.phase-bet .felt.single-hand .sb-col {
      transform: translateX(9px);
    }
    .table-wrap.phase-bet .sb-box,
    .table-wrap.phase-bet .sb-box-editing,
    .table-wrap.phase-play .sb-box,
    .table-wrap.phase-play .sb-box-editing,
    .table-wrap.phase-result .sb-box,
    .table-wrap.phase-result .sb-box-editing {
      width: 39px !important;
      min-width: 39px !important;
      max-width: 39px !important;
      height: 39px !important;
      min-height: 39px !important;
      max-height: 39px !important;
      padding: 3px !important;
      overflow: hidden !important;
      border-radius: 7px !important;
      justify-content: center !important;
      gap: 2px !important;
      color: #ffffff !important;
    }
    .table-wrap.phase-bet .sb-box-label,
    .table-wrap.phase-play .sb-box-label,
    .table-wrap.phase-result .sb-box-label {
      font-size: 8px;
      line-height: 0.95;
      color: #ffffff;
    }
    .table-wrap.phase-bet .sb-box-label-213,
    .table-wrap.phase-play .sb-box-label-213,
    .table-wrap.phase-result .sb-box-label-213 {
      font-size: 9px;
      color: #ffffff;
    }
    .table-wrap.phase-bet .sb-box,
    .table-wrap.phase-bet .sb-box-editing {
      width: 36px;
      min-height: 28px;
      padding: 0;
    }
    .table-wrap.phase-bet .sb-box-amt,
    .table-wrap.phase-play .sb-box-amt,
    .table-wrap.phase-result .sb-box-amt {
      font-size: 9px;
      color: #ffffff;
    }
    .table-wrap.phase-bet .sb-box,
    .table-wrap.phase-bet .sb-box-editing,
    .table-wrap.phase-play .sb-box,
    .table-wrap.phase-play .sb-box-editing,
    .table-wrap.phase-result .sb-box,
    .table-wrap.phase-result .sb-box-editing {
      padding-top: 2px;
      padding-bottom: 0;
    }

    /* Make cards fit phone screens more comfortably */
    .card,
    .card.small {
      width: 86px;
      height: 146px;
      border-radius: 8px;
    }
    .card::before,
    .card.small::before {
      border-radius: 8px;
    }
    .hands-row.multi .card::before,
    .hands-row.multi .card.small::before,
    .hands-row.multi ~ .dealer-area .card::before,
    .hands-row.multi ~ .dealer-area .card.small::before {
      border-radius: 6px;
    }
    .card-placeholder,
    .card-placeholder.small {
      width: 86px;
      height: 146px;
    }
    .card-rank { font-size: 17px; }
    .card-suit-sm { font-size: 14px; }
    .card-center { font-size: 34px; }

    /* Result */
    .msg-text           { font-size: 20px; }
    .msg-text.bad-beat  { font-size: 24px; }

    /* Action buttons — bigger touch target */
    .btn-action { padding: 16px 0; }

    /* Bet quick buttons — bigger touch target */
    .bet-quick-btn { min-height: 36px; min-width: 52px; }
    .bet-amount-row-with-actions {
      gap: 0;
    }
    .bet-amount-row-with-actions .bet-quick-btn:first-child {
      margin-right: -2px;
    }
    .bet-amount-row-with-actions .bet-quick-btn:last-child {
      margin-left: -2px;
    }
    .bet-input-shell {
      min-width: 120px;
      justify-content: center;
    }
    .bet-amount-input {
      width: 84px;
      font-size: 18px;
    }
    .table-wrap.phase-bet .bet-amount-row-with-actions .bet-quick-btn,
    .table-wrap.phase-result .bet-amount-row-with-actions .bet-quick-btn {
      min-height: 24px;
      min-width: 35px;
      padding: 0 8px;
      font-size: 11px;
    }
    .action-grid {
      width: 100%;
      max-width: 420px;
      margin: 0 auto 6px;
      order: 1;
    }
    .table-wrap.phase-play-single-hand .action-grid {
      padding: 6px;
      border-radius: 14px;
      border: 1px solid rgba(232, 212, 139, 0.24);
      box-shadow:
        inset 0 1px 0 rgba(255,255,255,0.04),
        0 0 0 1px rgba(9, 28, 18, 0.22);
      background: rgba(8, 22, 14, 0.22);
    }
    .action-result-msg {
      display: flex;
      justify-content: center;
      align-items: center;
      min-height: 22px;
      margin: 0 auto 2px;
      width: 100%;
      max-width: 420px;
    }
    .center-deal-wrap,
    .actions-wrap {
      width: 100%;
      max-width: 420px;
      margin: 0 auto;
    }
    .center-deal-wrap {
      order: 2;
      position: static;
      max-width: 420px;
      margin: 0 auto;
      z-index: auto;
      padding-bottom: 0;
    }
    .action-area-fixed {
      order: 1;
    }

    /* Remove the mobile wager input strip to recover felt space. */
    .felt-menu {
      display: none;
    }
    .felt-toggle-copy { font-size: 14px; }
    .cards-col.has-sidebets {
      --sidebet-center-offset: 26px;
    }
    .cards-col.has-sidebets .hv-bubble,
    .cards-col.has-sidebets .bet-bar {
      transform: translateX(var(--sidebet-center-offset));
    }
    .table-wrap.phase-bet .felt.single-hand .cards-col.has-sidebets,
    .table-wrap.phase-play .felt.single-hand .cards-col.has-sidebets,
    .table-wrap.phase-result .felt.single-hand .cards-col.has-sidebets {
      --sidebet-center-offset: 0px;
      transform: translateX(-26px);
    }
    .table-wrap.phase-bet .felt.single-hand .cards-col.has-sidebets .hv-bubble,
    .table-wrap.phase-play .felt.single-hand .cards-col.has-sidebets .hv-bubble,
    .table-wrap.phase-result .felt.single-hand .cards-col.has-sidebets .hv-bubble {
      transform: none;
      align-self: center;
    }
    .table-wrap.phase-bet .felt.single-hand .cards-col.has-sidebets .hv-bubble {
      font-size: 12px;
      padding: 1px 8px;
      border-radius: 10px;
    }
    .table-wrap.phase-play-single-hand .hv-bubble {
      font-size: 14.4px;
      padding: 1px 11px;
      border-radius: 10px;
    }
    .table-wrap.phase-result-single-hand .felt.single-hand .cards-col.has-sidebets .hv-bubble {
      font-size: 14.4px;
      padding: 1px 11px;
      border-radius: 10px;
      transform: none;
    }
    .table-wrap.phase-bet .felt.single-hand .cards-col.has-sidebets .bet-bar,
    .table-wrap.phase-result .felt.single-hand .cards-col.has-sidebets .bet-bar {
      transform: translate(18px, -12px) scale(0.8);
      transform-origin: center top;
      align-self: center;
    }
    .table-wrap.phase-play .felt.single-hand .cards-col.has-sidebets .bet-bar {
      transform: translateX(26px) scale(0.8);
      transform-origin: center top;
      align-self: center;
    }
    .table-wrap.phase-bet .felt.single-hand .cards-row,
    .table-wrap.phase-play .felt.single-hand .cards-row,
    .table-wrap.phase-result .felt.single-hand .cards-row {
      transform: none;
      justify-content: center;
      margin: 0 auto;
    }
    .table-wrap.phase-play-single-hand .hands-row,
    .table-wrap.phase-result-single-hand .hands-row {
      margin-top: 8px;
    }
    .table-wrap.phase-bet .felt.single-hand .bet-bar,
    .table-wrap.phase-result .felt.single-hand .bet-bar {
      margin-left: 0;
      align-self: center;
      transform: translate(18px, -12px) scale(0.8);
      transform-origin: center top;
    }
    .table-wrap.phase-result-single-hand .felt.single-hand .cards-col.has-sidebets .bet-bar,
    .table-wrap.phase-result-single-hand .felt.single-hand .bet-bar {
      transform: translateX(26px) scale(0.8);
      transform-origin: center top;
      align-self: center;
      margin-left: 0;
    }
    .table-wrap.phase-result-two-hand .hands-row.two .cards-col.has-sidebets .hv-bubble {
      transform: translateX(4px) !important;
      align-self: center !important;
    }
    .table-wrap.phase-result-two-hand .hands-row.two .cards-col.has-sidebets .bet-bar,
    .table-wrap.phase-result-two-hand .hands-row.two .bet-bar {
      transform: translate(4px, 0px) scale(0.8) !important;
      transform-origin: center top !important;
      margin-left: 0 !important;
      align-self: center !important;
    }
    .table-wrap.phase-result-two-hand .hands-row.two .hand-col:last-of-type .cards-col.has-sidebets .bet-bar,
    .table-wrap.phase-result-two-hand .hands-row.two .hand-col:last-of-type .bet-bar {
      transform: translate(4px, 1px) scale(0.8) !important;
    }
    .table-wrap.phase-result-two-hand .hands-row.two .hand-col:last-of-type .cards-col.has-sidebets .bet-bar,
    .table-wrap.phase-result-two-hand .hands-row.two .hand-col:last-of-type .bet-bar {
      transform: translate(4px, 1px) scale(0.8) !important;
    }
    .table-wrap.phase-result-two-hand .hands-row.two .hand-col:last-of-type .cards-col.has-sidebets .bet-bar,
    .table-wrap.phase-result-two-hand .hands-row.two .hand-col:last-of-type .bet-bar {
      transform: translate(4px, 1px) scale(0.8) !important;
    }
    .table-wrap.phase-play .felt.single-hand .bet-bar {
      margin-left: 0;
      align-self: center;
      transform: translateX(26px) scale(0.8);
      transform-origin: center top;
    }
    .bet-bar {
      margin-left: 0;
      width: auto;
      max-width: none;
      align-self: center;
    }
    .felt.single-hand .cards-col.has-sidebets {
      --sidebet-center-offset: 0px;
    }
    .felt.single-hand .bet-bar {
      margin-left: 0;
      transform: none;
    }
    .felt.single-hand .ghost-row {
      display: grid;
      grid-template-columns: 1fr auto 1fr;
      align-items: center;
      width: 100%;
    }
    .felt.single-hand .ghost {
      grid-column: 2;
      justify-self: center;
      width: min(200px, calc(100vw - 184px));
    }
    .felt.single-hand .ghost-autoplay {
      grid-column: 3;
      justify-self: start;
      margin-left: 10px;
    }
    .table-wrap.phase-bet .hands-row.two .cards-col.has-sidebets,
    .table-wrap.phase-play .hands-row.two .cards-col.has-sidebets,
    .table-wrap.phase-result .hands-row.two .cards-col.has-sidebets {
      transform: translateX(-21px);
    }
    .table-wrap.phase-bet .hands-row.two .cards-row,
    .table-wrap.phase-play .hands-row.two .cards-row,
    .table-wrap.phase-result .hands-row.two .cards-row {
      transform: none;
      margin: 0 auto;
      justify-content: center;
    }
    .table-wrap.phase-bet .hands-row.two .cards-col.has-sidebets .bet-bar,
    .table-wrap.phase-result .hands-row.two .cards-col.has-sidebets .bet-bar {
      transform: translateX(21px) scale(0.8);
      transform-origin: center top;
    }
    .table-wrap.phase-bet .hands-row.two .bet-bar,
    .table-wrap.phase-result .hands-row.two .bet-bar {
      transform: translateX(21px) scale(0.8);
      transform-origin: center top;
      margin-left: 0;
      align-self: center;
    }
    .table-wrap.phase-play .hands-row.two .bet-bar {
      transform: none;
      margin-left: 0;
      align-self: center;
    }
    /* Canonical lock: two-hand must match first-hand lane geometry */
    .table-wrap.phase-bet .hands-row.two .cards-col.has-sidebets,
    .table-wrap.phase-result .hands-row.two .cards-col.has-sidebets {
      --sidebet-center-offset: 0px !important;
      transform: translateX(-26px) !important;
    }
    .table-wrap.phase-play .hands-row.two .cards-col.has-sidebets {
      --sidebet-center-offset: 0px !important;
      transform: none !important;
    }
    .table-wrap.phase-bet .hands-row.two .cards-col.has-sidebets .hv-bubble {
      transform: translateX(26px) !important;
      align-self: center !important;
    }
    .table-wrap.phase-play .hands-row.two .cards-col.has-sidebets .hv-bubble,
    .table-wrap.phase-result .hands-row.two .cards-col.has-sidebets .hv-bubble {
      transform: translateX(4px) !important;
      align-self: center !important;
    }
    .table-wrap.phase-bet .hands-row.two .cards-row,
    .table-wrap.phase-play .hands-row.two .cards-row,
    .table-wrap.phase-result .hands-row.two .cards-row {
      transform: none !important;
      justify-content: center !important;
      margin: 0 auto !important;
    }
    .table-wrap.phase-bet .hands-row.two .cards-col.has-sidebets .bet-bar,
    .table-wrap.phase-bet .hands-row.two .bet-bar {
      transform: translateX(26px) scale(0.8) !important;
      transform-origin: center top !important;
      margin-left: 0 !important;
      align-self: center !important;
    }
    .table-wrap.phase-play .hands-row.two .cards-col.has-sidebets .bet-bar,
    .table-wrap.phase-play .hands-row.two .bet-bar,
    .table-wrap.phase-result .hands-row.two .cards-col.has-sidebets .bet-bar,
    .table-wrap.phase-result .hands-row.two .bet-bar {
      transform: translateX(4px) scale(0.8) !important;
      transform-origin: center top !important;
      margin-left: 0 !important;
      align-self: center !important;
    }
    .table-wrap.phase-play .hands-row.two .hand-col:last-of-type .cards-col.has-sidebets .bet-bar,
    .table-wrap.phase-play .hands-row.two .hand-col:last-of-type .bet-bar {
      transform: translate(4px, -44px) scale(0.8) !important;
    }
    .table-wrap.phase-bet .hands-row.two .hand-col:first-of-type .cards-row {
      transform: translateX(6px) !important;
    }
    .table-wrap.phase-play .hands-row.two .sb-box,
    .table-wrap.phase-play .hands-row.two .sb-box-editing {
      width: 39px !important;
      min-width: 39px !important;
      max-width: 39px !important;
      height: 39px !important;
      min-height: 39px !important;
      max-height: 39px !important;
      padding: 3px !important;
      overflow: hidden !important;
    }
    .table-wrap.phase-play .hands-row.two .sb-box-label,
    .table-wrap.phase-play .hands-row.two .sb-box-label-213,
    .table-wrap.phase-play .hands-row.two .sb-box-amt {
      color: #ffffff !important;
    }
    .table-wrap.phase-play .hands-row.two .sb-box-label,
    .table-wrap.phase-play .hands-row.two .sb-box-label-213 {
      transform: none !important;
    }
    .table-wrap.phase-result-two-hand .hands-row.two .cards-col.has-sidebets .hv-bubble {
      transform: translateX(4px) !important;
      align-self: center !important;
    }
    .table-wrap.phase-result-two-hand .hands-row.two .cards-col.has-sidebets .bet-bar,
    .table-wrap.phase-result-two-hand .hands-row.two .bet-bar {
      transform: translate(4px, 0px) scale(0.8) !important;
      transform-origin: center top !important;
      margin-left: 0 !important;
      align-self: center !important;
    }
    .table-wrap.phase-result-two-hand .hands-row.two .hand-col:last-of-type .cards-col.has-sidebets .bet-bar,
    .table-wrap.phase-result-two-hand .hands-row.two .hand-col:last-of-type .bet-bar {
      transform: translate(4px, 1px) scale(0.8) !important;
    }
    .bet-entry-btn    { font-size: 14px; min-width: 60px; min-height: 28px; }

    .mid-zone {
      height: auto !important;
      min-height: 40px !important;
      max-height: none !important;
      gap: 4px;
    }
    .divider-row {
      display: flex;
      align-items: center;
      width: 100vw;
      gap: 10px;
      margin: 0 calc(50% - 50vw);
      padding: 0;
    }
    .divider-line {
      flex: 1 1 auto;
      min-width: 0;
      height: 1px;
      background: rgba(232, 212, 139, 0.85);
    }
    .divider-label {
      padding: 0 6px;
      font-family: 'Oswald', sans-serif;
      font-size: 14px;
      font-weight: 700;
      letter-spacing: 0.12em;
      text-transform: uppercase;
      color: #e8d48b;
      white-space: nowrap;
      text-shadow: 0 1px 0 rgba(0,0,0,0.35), 0 0 8px rgba(212,168,64,0.14);
    }
    .divider-copy {
      font-size: 14px;
      letter-spacing: 0.12em;
      color: #d4a840;
      text-shadow: 0 1px 0 rgba(0,0,0,0.35), 0 0 8px rgba(212,168,64,0.14);
    }

    /* Panels — smaller text so they don't crowd the screen */
    .panel          { padding: 6px 8px; margin-top: 6px; }
    .panel-title    { font-size: 18px; margin-bottom: 6px; }
    .panel-label    { font-size: 15px; margin-bottom: 2px; }
    .panel-hint     { font-size: 13px; margin-bottom: 4px; }
    .mode-row,
    .speed-row      { gap: 3px; margin-bottom: 4px; }
    .btn-mode,
    .btn-speed      { font-size: 14px; min-width: 68px; padding: 5px 6px; }
    .btn-auto-toggle { font-size: 16px; padding: 8px 0; }
    .rounds-ctrl span   { font-size: 18px; }
    .rounds-ctrl button { width: 28px; height: 28px; }
    .rules-section  { font-size: 13px; margin-bottom: 8px; }
    .rules-text     { font-size: 13px; line-height: 1.5; }
    .rules-text-sm  { font-size: 12px; }
    .rules-text.rtp { font-size: 12px; }
    .payout-table   { font-size: 12px; }
    .rules-example  { font-size: 11px; }
    .strategy-table th, .strategy-table td { font-size: 11px; }
  .rules-panel    { max-height: min(42vh, 300px); }
  .panel-title    { font-size: 18px; }
  .mobile-options-drawer.full-panel-open .rules-panel,
  .mobile-options-drawer.full-panel-open .about-panel {
    max-height: none;
  }
  .felt-panel { max-height: min(42vh, 320px); overflow-y: auto; padding: 0; }
  .texture-picker { display: flex; flex-direction: column; gap: 0; }
  .texture-row {
    display: grid;
    grid-template-columns: 76px repeat(3, minmax(0, 1fr));
    gap: 0;
    align-items: stretch;
  }
  .texture-row + .texture-row { margin-top: -1px; }
  .texture-row-label {
    display: flex;
    align-items: center;
    justify-content: center;
    border: 1px solid rgba(232, 212, 139, 0.26);
    background: rgba(11, 28, 18, 0.98);
    color: #f2e8d0;
    font-family: 'Oswald', sans-serif;
    font-size: 14px;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    min-height: 48px;
    margin-right: -1px;
  }
  .btn-theme {
    border: 1px solid rgba(232, 212, 139, 0.26);
    border-radius: 0;
    color: #f2e8d0;
    font-family: 'Oswald', sans-serif;
    font-size: 11px;
    letter-spacing: 0.05em;
    text-transform: uppercase;
    min-height: 48px;
    padding: 4px;
    text-shadow: 0 1px 1px rgba(0,0,0,0.45);
  }
  .texture-row .btn-theme + .btn-theme { margin-left: -1px; }
  .btn-theme.active {
    border-color: rgba(232, 212, 139, 0.82);
    box-shadow: 0 0 0 1px rgba(232, 212, 139, 0.38) inset;
    color: #f2e8d0;
    position: relative;
    z-index: 1;
  }
  .texture-option {
    display: flex;
    align-items: stretch;
    justify-content: center;
    background: rgba(8, 16, 11, 0.42);
  }
  .texture-option-swatch {
    display: block;
    width: 100%;
    min-height: 28px;
    border-radius: 2px;
    border: 1px solid rgba(255, 255, 255, 0.08);
    box-shadow: inset 0 1px 0 rgba(255,255,255,0.1);
    background-size: cover, cover, 132% auto;
    background-position: center center, center center, center center;
    background-repeat: no-repeat, no-repeat, no-repeat;
  }
  .texture-option.theme-velvet-blue .texture-option-swatch {
    background:
      radial-gradient(circle at 50% 16%, rgba(106, 145, 224, 0.18), transparent 38%),
      radial-gradient(ellipse at 50% 33%, rgba(24, 56, 112, 0.26), rgba(7, 20, 52, 0.78) 70%, rgba(4, 12, 32, 0.92) 100%),
      url('/velvet-blue-base.png');
  }
  .texture-option.theme-velvet-green .texture-option-swatch,
  .texture-option.theme-felt-green .texture-option-swatch {
    background:
      radial-gradient(circle at 50% 16%, rgba(127, 214, 174, 0.18), transparent 38%),
      radial-gradient(ellipse at 50% 33%, rgba(24, 110, 83, 0.26), rgba(9, 58, 40, 0.78) 70%, rgba(4, 31, 22, 0.92) 100%),
      url('/felt-green-base.png');
  }
  .texture-option.theme-velvet-green .texture-option-swatch {
    background:
      radial-gradient(circle at 50% 16%, rgba(127, 214, 174, 0.18), transparent 38%),
      radial-gradient(ellipse at 50% 33%, rgba(24, 110, 83, 0.26), rgba(9, 58, 40, 0.78) 70%, rgba(4, 31, 22, 0.92) 100%),
      url('/velvet-emerald-base.png');
  }
  .texture-option.theme-velvet-black .texture-option-swatch,
  .texture-option.theme-felt-black .texture-option-swatch {
    background:
      radial-gradient(circle at 50% 16%, rgba(116, 126, 151, 0.12), transparent 38%),
      radial-gradient(ellipse at 50% 33%, rgba(36, 46, 66, 0.28), rgba(12, 16, 24, 0.82) 70%, rgba(6, 8, 12, 0.94) 100%),
      url('/felt-black-base.png');
  }
  .texture-option.theme-velvet-black .texture-option-swatch {
    background:
      radial-gradient(circle at 50% 16%, rgba(116, 126, 151, 0.12), transparent 38%),
      radial-gradient(ellipse at 50% 33%, rgba(36, 46, 66, 0.28), rgba(12, 16, 24, 0.82) 70%, rgba(6, 8, 12, 0.94) 100%),
      url('/velvet-black-base.png');
  }
  .texture-option.theme-ridge-blue .texture-option-swatch,
  .texture-option.theme-felt-blue .texture-option-swatch {
    background:
      radial-gradient(circle at 50% 16%, rgba(106, 145, 224, 0.18), transparent 38%),
      radial-gradient(ellipse at 50% 33%, rgba(24, 56, 112, 0.26), rgba(7, 20, 52, 0.78) 70%, rgba(4, 12, 32, 0.92) 100%),
      url('/felt-blue-base.png');
  }
  .texture-option.theme-ridge-blue .texture-option-swatch {
    background:
      radial-gradient(circle at 50% 16%, rgba(106, 145, 224, 0.18), transparent 38%),
      radial-gradient(ellipse at 50% 33%, rgba(24, 56, 112, 0.26), rgba(7, 20, 52, 0.78) 70%, rgba(4, 12, 32, 0.92) 100%),
      url('/ridge-blue-base.png');
  }
  .texture-option.theme-ridge-green .texture-option-swatch {
    background:
      radial-gradient(circle at 50% 16%, rgba(127, 214, 174, 0.18), transparent 38%),
      radial-gradient(ellipse at 50% 33%, rgba(24, 110, 83, 0.26), rgba(9, 58, 40, 0.78) 70%, rgba(4, 31, 22, 0.92) 100%),
      url('/ridge-green-base.png');
  }
  .texture-option.theme-ridge-black .texture-option-swatch {
    background:
      radial-gradient(circle at 50% 16%, rgba(116, 126, 151, 0.12), transparent 38%),
      radial-gradient(ellipse at 50% 33%, rgba(36, 46, 66, 0.28), rgba(12, 16, 24, 0.82) 70%, rgba(6, 8, 12, 0.94) 100%),
      url('/ridge-black-base.png');
  }
  .table-wrap.phase-bet .felt.single-hand .sb-and-cards,
  .table-wrap.phase-play .felt.single-hand .sb-and-cards,
  .table-wrap.phase-result .felt.single-hand .sb-and-cards {
    gap: 0 !important;
  }
  .table-wrap.phase-bet .felt.single-hand .sb-col,
  .table-wrap.phase-play .felt.single-hand .sb-col,
  .table-wrap.phase-result .felt.single-hand .sb-col {
    flex: 0 0 40px !important;
    width: 40px !important;
    margin-right: 0 !important;
  }
  .table-wrap.phase-play-single-hand .felt.single-hand .cards-row {
    transform: none !important;
  }
  .table-wrap.phase-play-single-hand .felt.single-hand .sb-and-cards {
    width: max-content !important;
    max-width: none !important;
    justify-content: flex-start !important;
    align-items: center !important;
    gap: 4px !important;
    margin: 0 auto !important;
    transform: none !important;
  }
  .table-wrap.phase-result-single-hand .felt.single-hand .cards-row {
    transform: none !important;
  }
  .table-wrap.phase-play-single-hand .felt.single-hand .sb-col {
    flex: 0 0 38px !important;
    width: 38px !important;
    margin-right: 0 !important;
    transform: translateY(-32px) !important;
  }
  .table-wrap.phase-result-single-hand .felt.single-hand .sb-col {
    transform: translateY(-33px) !important;
  }
  .table-wrap.phase-result-single-hand .felt.single-hand .ghost {
    transform: translateY(30px) !important;
  }
  .table-wrap.phase-result-single-hand .felt.single-hand .sb-and-cards {
    width: max-content !important;
    max-width: none !important;
    justify-content: flex-start !important;
    align-items: center !important;
    gap: 4px !important;
    margin: 0 auto !important;
    transform: translateY(1px) !important;
  }
  .table-wrap.phase-bet .felt.single-hand .cards-col.has-sidebets,
  .table-wrap.phase-play .felt.single-hand .cards-col.has-sidebets,
  .table-wrap.phase-result .felt.single-hand .cards-col.has-sidebets {
    min-width: 104px !important;
  }
  .table-wrap.phase-play-single-hand .felt.single-hand .cards-col {
    transform: translateY(50px) !important;
  }
  .table-wrap.phase-play-single-hand .felt.single-hand .cards-col.has-sidebets {
    transform: translate(-26px, 50px) !important;
  }
  .table-wrap.phase-result-single-hand .felt.single-hand .cards-col {
    transform: translateY(50px) !important;
  }
  .table-wrap.phase-result-single-hand .felt.single-hand .cards-col.has-sidebets {
    transform: translate(-26px, 50px) !important;
  }
  .table-wrap.phase-bet .felt.single-hand .cards-col.has-sidebets .hv-bubble,
  .table-wrap.phase-play .felt.single-hand .cards-col.has-sidebets .hv-bubble,
  .table-wrap.phase-result .felt.single-hand .cards-col.has-sidebets .hv-bubble {
    transform: none !important;
    align-self: center !important;
  }
  .table-wrap.phase-play-single-hand .felt.single-hand .cards-col.has-sidebets .hv-bubble {
    transform: translateX(26px) !important;
    margin-bottom: 3px !important;
  }
  .table-wrap.phase-result-single-hand .felt.single-hand .cards-col.has-sidebets .hv-bubble {
    transform: translateX(26px) !important;
    margin-bottom: 3px !important;
  }

  /* Final anchor-triad lock: phase-result-two-hand only */
  .table-wrap.phase-result-two-hand .dealer-cards-col .hand-value {
    transform: none !important;
    margin-bottom: 0 !important;
  }
  .table-wrap.phase-result-two-hand .mid-zone .divider-copy {
    transform: translateY(-9px) !important;
  }
  .table-wrap.phase-result-single-hand .felt.single-hand .cards-col.has-sidebets .bet-bar,
  .table-wrap.phase-result-single-hand .felt.single-hand .bet-bar {
    transform: translate(26px, -12px) scale(0.8) !important;
    transform-origin: center top !important;
    margin-left: 0 !important;
    align-self: center !important;
  }
  .table-wrap.phase-result-single-hand .felt.single-hand .sb-box,
  .table-wrap.phase-result-single-hand .felt.single-hand .sb-box-editing {
    width: 39px !important;
    min-width: 39px !important;
    max-width: 39px !important;
    height: 39px !important;
    min-height: 39px !important;
    max-height: 39px !important;
    overflow: hidden !important;
  }
  .table-wrap.phase-result .sb-box,
  .table-wrap.phase-result .sb-box-editing {
    width: 39px !important;
    min-width: 39px !important;
    max-width: 39px !important;
    height: 39px !important;
    min-height: 39px !important;
    max-height: 39px !important;
    justify-content: center !important;
    align-items: center !important;
    gap: 2px !important;
    padding: 3px !important;
    overflow: hidden !important;
  }
  .table-wrap.phase-result .sb-box-label,
  .table-wrap.phase-result .sb-box-label-213 {
    text-align: center !important;
    margin: 0 !important;
    line-height: 1 !important;
    width: 100% !important;
  }
  .table-wrap.phase-result-two-hand .hands-row.two .sb-box-label {
    transform: translateY(-2px) !important;
  }
  .table-wrap.phase-result-two-hand .hands-row.two .sb-box-label-213 {
    transform: translateY(-1.5px) !important;
  }
  .table-wrap.phase-result-single-hand .felt.single-hand .sb-box-editing {
    width: 39px !important;
    min-width: 39px !important;
    max-width: 39px !important;
    height: 39px !important;
    min-height: 39px !important;
    max-height: 39px !important;
    transform: none !important;
    overflow: hidden !important;
    position: relative !important;
    z-index: 2 !important;
  }
  .table-wrap.phase-result-single-hand .felt.single-hand .sb-box-editing .sb-wager-input {
    width: 24px !important;
    min-width: 24px !important;
    max-width: 24px !important;
    padding: 1px 2px !important;
    font-size: 9px !important;
    line-height: 1 !important;
  }
  /* Mobile geometry scale lock (90% of current) */
  .table-wrap .card,
  .table-wrap .card.small,
  .table-wrap .card-placeholder,
  .table-wrap .card-placeholder.small {
    width: calc(86px * var(--mobile-geometry-scale)) !important;
    height: calc(146px * var(--mobile-geometry-scale)) !important;
  }
  .table-wrap .card-rank {
    font-size: calc(17px * var(--mobile-geometry-scale)) !important;
  }
  .table-wrap .card-suit-sm {
    font-size: calc(14px * var(--mobile-geometry-scale)) !important;
  }
  .table-wrap .card-center {
    font-size: calc(34px * var(--mobile-geometry-scale)) !important;
  }
  .table-wrap .dealer-cards-col .card,
  .table-wrap .dealer-cards-col .card.small,
  .table-wrap .hands-row.multi ~ .dealer-area .card,
  .table-wrap .hands-row.multi ~ .dealer-area .card.small,
  .table-wrap .hands-row.multi ~ .dealer-area .card-placeholder,
  .table-wrap .hands-row.multi ~ .dealer-area .card-placeholder.small,
  .table-wrap .hands-row.multi .card,
  .table-wrap .hands-row.multi .card.small,
  .table-wrap .hands-row.multi .card-placeholder,
  .table-wrap .hands-row.multi .card-placeholder.small {
    width: calc(92px * var(--mobile-geometry-scale)) !important;
    height: calc(156px * var(--mobile-geometry-scale)) !important;
  }
  .table-wrap .dealer-cards-col .card-rank,
  .table-wrap .hands-row.multi ~ .dealer-area .card-rank,
  .table-wrap .hands-row.multi .card-rank {
    font-size: calc(18px * var(--mobile-geometry-scale)) !important;
  }
  .table-wrap .dealer-cards-col .card-suit-sm,
  .table-wrap .hands-row.multi ~ .dealer-area .card-suit-sm,
  .table-wrap .hands-row.multi .card-suit-sm {
    font-size: calc(15px * var(--mobile-geometry-scale)) !important;
  }
  .table-wrap .dealer-cards-col .card-center,
  .table-wrap .hands-row.multi ~ .dealer-area .card-center,
  .table-wrap .hands-row.multi .card-center {
    font-size: calc(36px * var(--mobile-geometry-scale)) !important;
  }

  /* Split hands use the same geometry-locked card size as other multi hands — no override needed */
  .table-wrap.phase-play .dealer-area {
    min-height: calc(168px * var(--mobile-geometry-scale));
    flex-basis: calc(168px * var(--mobile-geometry-scale));
  }
  .table-wrap.phase-result .dealer-cards-col {
    transform: none;
  }
  .table-wrap .felt.single-hand .dealer-area {
    min-height: calc(96px * var(--mobile-geometry-scale));
  }
  }
  @media (max-width: 767px) and (max-height: 760px) {
    .felt {
      overflow-y: auto;
      overflow-x: hidden;
      -webkit-overflow-scrolling: touch;
      overscroll-behavior: contain;
    }
  }

  @media (max-width: 767px) and (max-height: 700px) {
    .table-wrap.phase-play .felt {
      padding-top: 24px;
    }

    .table-wrap.phase-play .dealer-area {
      min-height: 152px;
      flex-basis: 152px;
      margin-top: -12px;
      margin-bottom: 2px;
    }

    .table-wrap.phase-play .dealer-cards-col {
      gap: 4px;
    }

    .table-wrap.phase-play .hands-row {
      margin-top: 4px;
      gap: 4px;
    }

    .table-wrap.phase-play .hands-row.two {
      gap: 12px;
      padding-top: 6px;
      padding-bottom: 12px;
    }

    .table-wrap.phase-play .hands-row.two .hand-col:first-of-type {
      transform: translateY(60px);
    }

    .table-wrap.phase-play .hands-row.two .hand-col:last-of-type {
      transform: translateY(50px);
    }

    .table-wrap.phase-play .sb-col {
      gap: 2px;
    }

    .table-wrap.phase-play .sb-box {
      min-height: 46px;
    }

    .table-wrap.phase-play .action-wager-label {
      font-size: 14px;
    }
  }

  .nav-result-msg {
    display: flex;
    align-items: center;
    justify-content: center;
    flex: 1;
  }
  .nav-result-text {
    font-family: 'Oswald', sans-serif;
    font-size: 22px;
    font-weight: 700;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    animation: fadeIn 0.3s ease;
  }
  .nav-result-text.win  { color: #66ff88; }
  .nav-result-text.lose { color: #ef5350; }

  /* ANIMATIONS */
  @keyframes introFade {
    0%   { opacity: 0; transform: scale(0.9); }
    30%  { opacity: 1; transform: scale(1); }
    100% { opacity: 1; }
  }
  @keyframes cardIn {
    from { opacity: 0; transform: translateY(-10px) scale(0.95); }
    to   { opacity: 1; transform: translateY(0) scale(1); }
  }
  @keyframes fadeIn {
    from { opacity: 0; transform: translateY(4px); }
    to   { opacity: 1; transform: translateY(0); }
  }
  @keyframes resultBackReveal {
    from { opacity: 0; transform: translateY(10px) scale(0.96); }
    to   { opacity: 1; transform: translateY(0) scale(1); }
  }
  @keyframes glow {
    0%, 100% { box-shadow: 0 0 4px rgba(212,168,64,0.2); }
    50%       { box-shadow: 0 0 14px rgba(212,168,64,0.4); }
  }

  @media (max-width: 767px) {
    .table-wrap.phase-play-single-hand .hands-row,
    .table-wrap.phase-result-single-hand .hands-row,
    .table-wrap.phase-play-single-hand .hand-col,
    .table-wrap.phase-result-single-hand .hand-col,
    .table-wrap.phase-play-single-hand .cards-col,
    .table-wrap.phase-result-single-hand .cards-col,
    .table-wrap.phase-play-single-hand .sb-and-cards,
    .table-wrap.phase-result-single-hand .sb-and-cards,
    .table-wrap.phase-play-single-hand .cards-row,
    .table-wrap.phase-result-single-hand .cards-row,
    .table-wrap.phase-play-single-hand .player-live-card-wrap,
    .table-wrap.phase-result-single-hand .player-live-card-wrap,
    .table-wrap.phase-play-single-hand .player-result-back-wrap,
    .table-wrap.phase-result-single-hand .player-result-back-wrap,
    .table-wrap.phase-play-single-hand .hv-bubble,
    .table-wrap.phase-result-single-hand .hv-bubble,
    .table-wrap.phase-play-single-hand .bet-bar,
    .table-wrap.phase-result-single-hand .bet-bar,
    .table-wrap.phase-play-single-hand .sb-col,
    .table-wrap.phase-result-single-hand .sb-col,
    .table-wrap.phase-play-single-hand .sb-box,
    .table-wrap.phase-result-single-hand .sb-box,
    .table-wrap.phase-play-single-hand .sb-box-editing,
    .table-wrap.phase-result-single-hand .sb-box-editing {
      transition: none !important;
      animation: none !important;
    }

    .player-live-card-wrap {
      transition: transform 220ms ease, opacity 220ms ease;
      transform-origin: top center;
    }

    .player-result-back-wrap {
      animation: resultBackReveal 220ms ease both;
    }

    .player-result-back-wrap-single {
      display: flex;
      justify-content: center;
    }

    .card-result-back {
      box-shadow:
        0 3px 12px rgba(0,0,0,0.28),
        0 0 0 1px rgba(255,255,255,0.04) inset;
    }

    .table-wrap.phase-play .hands-row.two .cards-row {
      align-items: flex-start;
    }

    .action-wager-label {
      color: #ffffff !important;
      -webkit-text-fill-color: #ffffff;
      font-size: 15.9px;
      text-shadow: 0 1px 0 rgba(0,0,0,0.42);
    }

    .action-wager-label.multi-play-wager {
      transform: translateY(5px);
    }

    .table-wrap.phase-play-single-hand .hv-bubble {
      font-size: 14.4px;
      padding: 1px 11px;
      border-radius: 10px;
    }

    .action-result-msg .mobile-result-text {
      font-size: 17px;
      font-weight: 600;
      letter-spacing: 0.12em;
      color: #e8d48b;
      text-shadow: 0 1px 0 rgba(0,0,0,0.35), 0 0 10px rgba(212,168,64,0.12);
    }

    /* Final mobile two-hand sidebet anchor: pin sidebets to the left edge of the live card lane. */
    .table-wrap.phase-result-two-hand .hands-row.two .sb-and-cards {
      width: max-content !important;
      max-width: none !important;
      justify-content: flex-start !important;
      align-items: center !important;
      gap: 4px !important;
      margin: 0 auto !important;
      transform: none !important;
    }
    .table-wrap.phase-play .hands-row.two .sb-and-cards {
      width: max-content !important;
      max-width: none !important;
      justify-content: flex-start !important;
      align-items: center !important;
      gap: 4px !important;
      margin: 0 auto !important;
      transform: translateY(-14px) !important;
    }

    .table-wrap.phase-play .hands-row.two .sb-col {
      flex: 0 0 48px !important;
      width: 48px !important;
      margin-right: 0 !important;
      transform: translateX(9px) !important;
    }
    .table-wrap.phase-result-two-hand .hands-row.two .sb-col {
      flex: 0 0 48px !important;
      width: 48px !important;
      margin-right: 0 !important;
      transform: translateX(9px) !important;
    }

    .table-wrap.phase-play .hands-row.two .cards-col.has-sidebets,
    .table-wrap.phase-result-two-hand .hands-row.two .cards-col.has-sidebets {
      --sidebet-center-offset: 26px !important;
      transform: translateX(-22px) !important;
    }

    .table-wrap.phase-play .hands-row.two .cards-row,
    .table-wrap.phase-result-two-hand .hands-row.two .cards-row {
      width: max-content !important;
      margin: 0 !important;
      justify-content: flex-start !important;
      align-items: flex-start !important;
      transform: none !important;
    }

    .table-wrap.phase-play .hands-row.two .cards-col.has-sidebets .hv-bubble,
    .table-wrap.phase-result-two-hand .hands-row.two .cards-col.has-sidebets .hv-bubble {
      transform: translateX(26px) !important;
      align-self: center !important;
    }

    .table-wrap.phase-play .hands-row.two .cards-col.has-sidebets .bet-bar,
    .table-wrap.phase-play .hands-row.two .bet-bar,
    .table-wrap.phase-result-two-hand .hands-row.two .cards-col.has-sidebets .bet-bar,
    .table-wrap.phase-result-two-hand .hands-row.two .bet-bar {
      transform: translateX(26px) scale(0.8) !important;
      transform-origin: center top !important;
      margin-left: 0 !important;
      align-self: center !important;
    }

    .table-wrap.phase-play .hands-row.two .hand-col:last-of-type .cards-col.has-sidebets .bet-bar,
    .table-wrap.phase-play .hands-row.two .hand-col:last-of-type .bet-bar {
      transform: translate(26px, -44px) scale(0.8) !important;
    }

    .table-wrap.phase-result-two-hand .hands-row.two .hand-col:last-of-type .cards-col.has-sidebets .bet-bar,
    .table-wrap.phase-result-two-hand .hands-row.two .hand-col:last-of-type .bet-bar {
      transform: translate(26px, 5px) scale(0.8) !important;
    }

    .table-wrap.phase-bet .hands-row.two .sb-col {
      transform: translateX(73px) !important;
    }

    .table-wrap.phase-bet .hands-row.two .hand-col:first-of-type .sb-col {
      transform: translateX(69px) !important;
    }

    .table-wrap.phase-bet .hands-row.two .hand-col:last-of-type .sb-col {
      transform: translateX(61.5px) !important;
    }

    .table-wrap.phase-bet .sb-box,
    .table-wrap.phase-bet .sb-box-editing {
      color: #ffffff !important;
    }

    .table-wrap.phase-bet .sb-box-label,
    .table-wrap.phase-bet .sb-box-label-213,
    .table-wrap.phase-bet .sb-box-amt {
      color: #ffffff !important;
    }

  }
</style>
