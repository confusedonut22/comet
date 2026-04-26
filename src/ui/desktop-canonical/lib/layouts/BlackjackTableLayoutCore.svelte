<script>
  import { onMount, onDestroy, afterUpdate } from "svelte";
  import { get } from "svelte/store";
  import { getContextLayout } from "../../game/layout.svelte.js";
  import {
    phase, balance, dealerHand, hands, activeHand, message, pending,
    numSlots, maxHands, autoPlay, autoSpeed, autoCount, autoMax, autoMode,
    showAuto, showRules, totalCost, canDeal, introOp, rgsStatus, rgsError, runtimeConfig, runtimeJurisdiction,
    sessionStartedAt, netPosition, runtimeCurrency, autoBetEnabled, sideBetsEnabled,
    startIntro, addSlot, removeSlot, addSideBetChip, clearSideBet, setSideBetAmount, addChip, clearBet, setBetLevel, adjustBetByFactor,
    newRound, deal, hit, stand, doubleDown, split, takeInsurance, autoTick, refreshStakeBalance,
  } from "../../../../game/store.js";
  import { PHASE, SPEEDS, MONEY_SCALE, CHIPS, CHIP_IMAGES, LOGO_IMAGE, CARD_BACK_IMAGE, C } from "../../../../game/constants.js";
  import { handValue, isSoft } from "../../../../game/engine.js";
  import { launchWarnings, replayMode, sessionQuery } from "../../../../game/session.js";
  import { sessionBootstrap } from "../../../../game/bootstrap.js";
  import { formatCurrencyAmount, formatSessionDuration, formatSignedMoney } from "../../../../game/sessionDisplay.js";
  import { toggleMute, isMuted } from "../../../../game/audio.js";
  import INTRO_VIDEO from "../../../../assets/chad_labs_intro_powergrid_v7.mp4";
  import INTRO_VIDEO_MOBILE from "../../../../assets/chad_labs_intro_powergrid_v7_mobile.mp4";
  import AUTOPLAY_BUTTON from "../../../../assets/autoplaybutton.png";
  import JACK_SPADES_CHADJACK from "../../../../assets/custom-face-cards/jack-spades-chadjack.png";
  import JACK_HEARTS_CHADJACK from "../../../../assets/custom-face-cards/jack-hearts-chadjack.png";
  import JACK_CLUBS_CHADJACK from "../../../../assets/custom-face-cards/jack-clubs-chadjack.png";
  import JACK_DIAMONDS_CHADJACK from "../../../../assets/custom-face-cards/jack-diamonds-chadjack.png";

  export let layoutVariant = "desktop";

  const { stateLayoutDerived } = getContextLayout();

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
      options: [
        { key: "felt-green" },
        { key: "felt-blue" },
        { key: "felt-black" },
      ],
    },
    {
      textureKey: "velvet",
      textureLabel: "Velvet",
      options: [
        { key: "velvet-green" },
        { key: "velvet-blue" },
        { key: "velvet-black" },
      ],
    },
    {
      textureKey: "ridge",
      textureLabel: "Ridge",
      options: [
        { key: "ridge-green" },
        { key: "ridge-blue" },
        { key: "ridge-black" },
      ],
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

  // ─── RESPONSIVE ───
  let bottomDockHeight = 0;
  $: liveLayoutType = stateLayoutDerived.layoutType();
  $: layoutType = layoutVariant === "desktop" ? "desktop" : liveLayoutType;
  $: isStacked = layoutVariant !== "desktop";
  $: canvasSizes = stateLayoutDerived.canvasSizes();
  $: windowWidth = canvasSizes.width;
  $: windowHeight = canvasSizes.height;
  $: isDesktop = layoutVariant === "desktop";
  $: introVideoSrc = isDesktop ? INTRO_VIDEO : INTRO_VIDEO_MOBILE;
  $: isWideDesktop = layoutType === "desktop" && windowWidth >= 1280;
  $: {
    maxHands.set(isDesktop ? 6 : 2);
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
    : (dealerSoft ? `${dealerVal - 10}/${dealerVal}` : dealerVal);
  $: multi = $numSlots > 1;
  $: activeH = $activeHand >= 0 ? $hands[$activeHand] : null;
  $: isReplay = $replayMode;
  $: isSocial = $sessionQuery.social || $runtimeJurisdiction?.socialCasino === true;
  $: autoplayDisabled = $runtimeJurisdiction?.disabledAutoplay === true;
  $: showDesktopAutoplay = $autoBetEnabled && !autoplayDisabled && (isBet || isResult);
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
  $: isThreeDesktop = isDesktop && $numSlots === 3;
  $: useSecondRowCardSize = isDesktop && $numSlots > 3;
  $: desktopUiZoom = isDesktop ? ($numSlots <= 3 ? 0.96 : 0.8) : 1;
  $: desktopInfoOverlayOpen = $showRules || showAbout || showFeltPanel;
  $: useFooterAddSlot = isDesktop && !isReplay && (isBet || isResult) && $numSlots >= 1 && $numSlots <= 3 && $numSlots < $maxHands;
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
  // Split rule: max 6 total hands, no re-splitting.
  // 6 hands → no split | 5 → 1 more | 4 → 2 more | 3 → 3 more (always capped at 6)
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
      autoConfirmOpen = false;
      autoPlay.set(false);
    } else {
      autoConfirmOpen = false;
      showAuto.set(false);
      autoCount.set(0);
      autoPlay.set(true);
      if (isResult || isBet) autoTick();
    }
  }

  function resultColor(result) {
    if (result === "win" || result === "blackjack") return "#2db870";
    if (result === "push") return C.cd;
    return C.rd;
  }

  function navResultTone(text) {
    if (text === "You Win!" || text === "Push") return "win";
    if (text === "Dealer Wins") return "lose";
    return "";
  }

  function handMsg(h) {
    // Always show hand value, never per-hand result label
    const v = handValue(h.cards);
    if (v > 21) return "BUST";
    if (isSoft(h.cards) && v <= 21) return `${v - 10}/${v}`;
    return v;
  }

  function customFaceCardImage(card) {
    if (card?.rank !== "J") return null;
    if (card?.suit === "spades") return JACK_SPADES_CHADJACK;
    if (card?.suit === "hearts") return JACK_HEARTS_CHADJACK;
    if (card?.suit === "clubs") return JACK_CLUBS_CHADJACK;
    if (card?.suit === "diamonds") return JACK_DIAMONDS_CHADJACK;
    return null;
  }

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
    if (!isBet) return;
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
    betDraft = { ...betDraft, [idx]: fmt(scaled, $runtimeCurrency).replace(/[^0-9.]/g, "") };
  }

  let showAbout = false;
  let showFeltPanel = false;
  let showOptionsMenu = false;
  let soundMuted = false;
  let autoConfirmOpen = false;
  let feltTheme = "felt-green";

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
    autoConfirmOpen = false;
  }

  function exitReplayMode() {
    if (typeof window === "undefined") return;
    const nextUrl = new URL(window.location.href);
    nextUrl.searchParams.delete("replay");
    nextUrl.searchParams.delete("event");
    if ((nextUrl.searchParams.get("mode") || "").toLowerCase() === "replay") {
      nextUrl.searchParams.delete("mode");
    }
    window.location.assign(nextUrl.toString());
  }

  function toggleAbout(event) {
    event?.stopPropagation?.();
    showAbout = !showAbout;
    showAuto.set(false);
    showRules.set(false);
    showFeltPanel = false;
    showOptionsMenu = false;
    autoConfirmOpen = false;
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
    showOptionsMenu = false;
    autoConfirmOpen = false;
  }

  function closeInfoOverlay() {
    showRules.set(false);
    showAbout = false;
    showFeltPanel = false;
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
    const selectedHandIndexes = $hands.flatMap((_, i) => insSelect[i] ? [i] : []);
    const anySelected = selectedHandIndexes.length > 0;
    if (!anySelected) { takeInsurance(false); return; }
    const amt = $hands.reduce((sum, h, i) => insSelect[i] ? sum + Math.floor(h.bet / 2) : sum, 0);
    takeInsurance(true, amt > 0 ? amt : null, selectedHandIndexes);
  }

  function toggleAutoPanel(event) {
    event?.stopPropagation?.();
    if (isPlay) return; // don't open auto panel mid-hand
    if ($showAuto) autoConfirmOpen = false;
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
    autoConfirmOpen = false;
    showFeltPanel = false;
    showAbout = false;
    showOptionsMenu = false;
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

  onMount(() => {
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
    }
    if (typeof document !== "undefined") {
      document.addEventListener("visibilitychange", handleVisibilityChange);
    }

    return () => {
      if (typeof window !== "undefined") {
        window.removeEventListener("focus", handleWindowFocus);
      }
      if (typeof document !== "undefined") {
        document.removeEventListener("visibilitychange", handleVisibilityChange);
      }
    };
  });

  onDestroy(() => {
    if (sessionClock) clearInterval(sessionClock);
  });
</script>

<svelte:window on:keydown={(e) => {
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
<div
  class="table-wrap"
  class:stacked-layout={isStacked}
  class:phase-bet={isBet}
  class:phase-play={isPlay || isIns || isDealer}
  class:phase-result={isResult}
  class:felt-theme-velvet-blue={feltTheme === "velvet-blue"}
  class:felt-theme-velvet-green={feltTheme === "velvet-green"}
  class:felt-theme-velvet-black={feltTheme === "velvet-black"}
  class:felt-theme-ridge-blue={feltTheme === "ridge-blue"}
  class:felt-theme-ridge-green={feltTheme === "ridge-green"}
  class:felt-theme-ridge-black={feltTheme === "ridge-black"}
  class:felt-theme-felt-blue={feltTheme === "felt-blue"}
  class:felt-theme-felt-green={feltTheme === "felt-green"}
  class:felt-theme-felt-black={feltTheme === "felt-black"}
  style={`--mobile-dock-height: ${bottomDockHeight}px; --desktop-ui-zoom: ${desktopUiZoom};`}
>
  <!-- BALANCE -->
  <div class="balance-row">
    <div class="balance-meta">
      <span class="mobile-balance-pill desktop-balance-pill">{fmt($balance, displayCurrency)}</span>
      {#if $totalCost > 0}
        <span class="total-wager-sub">{isSocial ? 'Total Play' : 'Total Wager'}: {fmt($totalCost, displayCurrency)}</span>
      {/if}
    </div>
    <div class="header-controls" use:stopClick>
      <div class="options-anchor">
        <button
          class="btn-tab btn-options-toggle desktop-options-launch"
          class:active={showOptionsMenu || $showRules || showAbout}
          on:click={toggleOptionsMenu}
        >
          Options
        </button>

        {#if showOptionsMenu}
          <div class="mobile-options-drawer desktop-options-drawer" class:full-panel-open={showFeltPanel} use:stopClick>
            <div class="desktop-options-shell">
              <div class="desktop-options-head">
                <div>
                  <div class="desktop-panel-kicker">Table Controls</div>
                  <div class="desktop-options-title">Options</div>
                </div>
                <div class="desktop-options-status">{soundMuted ? 'Muted' : 'Live Audio'}</div>
              </div>
            <div class="mobile-options-column desktop-options-grid">
              <button class="btn-tab btn-options-item btn-options-toggle-pill" class:active={$autoBetEnabled} on:click={toggleAutoBetSetting}>
                <span class="desktop-option-copy">
                  <span class="desktop-option-title">Autobet</span>
                  <span class="desktop-option-meta">Keep your base wager loaded between hands</span>
                </span>
                <span class="options-mini-toggle" aria-hidden="true">{#if $autoBetEnabled}On{:else}Off{/if}</span>
              </button>
              <button class="btn-tab btn-options-item btn-options-toggle-pill" class:active={$sideBetsEnabled} on:click={toggleSideBetsSetting}>
                <span class="desktop-option-copy">
                  <span class="desktop-option-title">Sidebets</span>
                  <span class="desktop-option-meta">Perfect Pairs and 21+3 at every seat</span>
                </span>
                <span class="options-mini-toggle" aria-hidden="true">{#if $sideBetsEnabled}On{:else}Off{/if}</span>
              </button>
              <button class="btn-tab btn-options-item" class:active={showFeltPanel} on:click={toggleFeltPanel}>
                <span class="desktop-option-copy">
                  <span class="desktop-option-title">Texture</span>
                  <span class="desktop-option-meta">Swap the table finish and felt treatment</span>
                </span>
              </button>
              <button class="btn-tab btn-options-item" class:active={$showRules} on:click={toggleRulesPanel}>
                <span class="desktop-option-copy">
                  <span class="desktop-option-title">Rules</span>
                  <span class="desktop-option-meta">Open the full-screen game guide</span>
                </span>
              </button>
              <button class="btn-tab btn-options-item btn-mute" class:muted={soundMuted} on:click={onToggleMute}>
                <span class="desktop-option-copy">
                  <span class="desktop-option-title">{soundMuted ? 'Unmute' : 'Sound'}</span>
                  <span class="desktop-option-meta">Table audio, chip clicks, and reveal cues</span>
                </span>
              </button>
              <button class="btn-tab btn-options-item" class:active={showAbout} on:click={toggleAbout}>
                <span class="desktop-option-copy">
                  <span class="desktop-option-title">About</span>
                  <span class="desktop-option-meta">The ChadJack philosophy and feature stack</span>
                </span>
              </button>
            </div>

            {#if showFeltPanel}
              <div class="panel felt-panel felt-panel-inline desktop-options-panel" use:stopClick>
                <div class="desktop-panel-kicker">Surface Finish</div>
                <div class="panel-title">Texture Library</div>
                <div class="texture-picker">
                  {#each TEXTURE_ROWS as row}
                    <div class="texture-row texture-row-{row.textureKey}">
                      <div class="texture-row-label">{row.textureLabel}</div>
                      {#each row.options as option}
                        <button
                          class={`btn-theme texture-option theme-${option.key}`}
                          class:active={feltTheme === option.key}
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
            </div>

            {#if showAbout}
              <div class="panel about-panel about-panel-inline desktop-options-panel" use:stopClick>
                <div class="panel-title">About</div>
                <div class="about-text">We're degens, same as you. We love Stake Originals Blackjack. We just always wanted more at the table. Sidebets. Multiple hands. Autoplay across three strategies: Conservative, Optimal, and Aggressive. We kept waiting for someone to build it and nobody did, so ChadJack did. It's not a competition, it's just more game. Drop a sidebet, open a second hand, and tell us you can stop at just one.</div>
              </div>
            {/if}

            {#if $showRules}
              <div class="panel rules-panel rules-panel-inline desktop-options-panel" use:stopClick>
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
                    No re-splitting. Max 6 total hands: 3 open → split 3×, 4 → 2×, 5 → 1×, 6 → no split.<br/>
                    No double after split.<br/>
                    Split Aces receive one card only and stand automatically.<br/>
                    Maximum starting hands: 6 on desktop, 2 on mobile.
                  </div>
                </div>

                <div class="rules-section"><strong>Autoplay Modes</strong>
                  <div class="rules-text">
                    <strong>Conservative</strong> - Lower-variance play. Avoids marginal doubles, stands earlier in riskier spots. Designed to preserve your bankroll over longer sessions.<br/><br/>
                    <strong>Optimal</strong> - Perfect basic strategy for this build. The mathematically strongest mode and the closest thing to ideal play.<br/><br/>
                    <strong>High Roller</strong> - More aggressive doubles and pressure spots. Bigger swings, bigger upside, more pain when variance hits.
                  </div>
                </div>

                <div class="rules-section"><strong>Maximum Win</strong>
                  <div class="rules-text">{isSocial
                    ? "The maximum payout for a single round is capped at 10,000× your main play amount. Side plays are subject to their own individual caps as listed in their payout tables."
                    : "The maximum payout for a single round is capped at 10,000× your main bet. Side bets are subject to their own individual caps as listed in their payout tables."
                  }</div>
                </div>

                {#if showRtp}
                  <div class="rules-text rtp">{isSocial
                    ? "ChadJack is a social casino game intended for entertainment only. No real money, prizes, or rewards are offered or implied. Base game RTP: 97.2%. Side plays carry a lower RTP and are optional. Malfunction voids all wins and plays. A consistent internet connection is required. In the event of a disconnection, reload the game to finish any uncompleted rounds. ChadJack™ is a trademark of Chad Labs."
                    : "Base game RTP: 97.2%. Side bets carry a lower RTP and are optional. RTP is a long-run statistical average; individual session results will vary. Malfunction voids all wins and plays. A consistent internet connection is required. In the event of a disconnection, reload the game to finish any uncompleted rounds. ChadJack™ is a trademark of Chad Labs."
                  }</div>
                {/if}
              </div>
            {/if}
          </div>
        {/if}
      </div>

    </div>
  </div>

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
      <div class="replay-banner-copy">
        <strong>Replay mode</strong>
        <span>
          {#if $sessionQuery.game}Game {$sessionQuery.game}{/if}
          {#if $sessionQuery.version} · Version {$sessionQuery.version}{/if}
          {#if $sessionQuery.event} · Event {$sessionQuery.event}{/if}
        </span>
      </div>
      <button class="btn-replay-exit" on:click={exitReplayMode}>{isResult ? "Play Again" : "Play"}</button>
    </div>
  {:else if $launchWarnings.length > 0}
    <div class="launch-warning">
      Launch params incomplete: {$launchWarnings.join(", ")}
    </div>
  {/if}

  <!-- svelte-ignore a11y_click_events_have_key_events -->
  <!-- svelte-ignore a11y_no_static_element_interactions -->
  <!-- FELT AREA -->
  <div
    class="felt"
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

    {#if desktopInfoOverlayOpen}
      <!-- svelte-ignore a11y-click-events-have-key-events -->
      <!-- svelte-ignore a11y-no-static-element-interactions -->
      <div class="desktop-info-overlay-backdrop" on:click={closeInfoOverlay}>
        <div class="desktop-info-overlay" use:stopClick>
          <div class="desktop-info-topbar">
            <div class="desktop-info-headline">
              <div class="desktop-panel-kicker">{showFeltPanel ? 'Surface Finish' : showAbout ? 'ChadJack' : 'Game Guide'}</div>
              <div class="desktop-info-title">{showFeltPanel ? 'Texture Library' : showAbout ? 'About ChadJack' : 'How To Play'}</div>
            </div>
            <button class="desktop-info-close" on:click={closeInfoOverlay}>Close</button>
          </div>

          {#if showFeltPanel}
            <div class="desktop-info-body">
              <section class="desktop-info-card">
                <div class="desktop-info-section-title">Table Textures</div>
                <div class="texture-picker">
                  {#each TEXTURE_ROWS as row}
                    <div class="texture-row texture-row-{row.textureKey}">
                      <div class="texture-row-label">{row.textureLabel}</div>
                      {#each row.options as option}
                        <button
                          class={`btn-theme texture-option theme-${option.key}`}
                          class:active={feltTheme === option.key}
                          on:click={() => applyFeltTheme(option.key)}
                          aria-label={option.key}
                        >
                          <span class="texture-option-swatch" aria-hidden="true"></span>
                        </button>
                      {/each}
                    </div>
                  {/each}
                </div>
              </section>
            </div>
          {/if}

          {#if showAbout}
            <div class="desktop-info-body desktop-about-layout">
              <section class="desktop-info-card desktop-about-hero">
                <div class="desktop-about-logo">CHADJACK</div>
                <p class="desktop-about-lead">Built for players who wanted Stake Originals Blackjack with more pressure, more side action, and more session control at the table.</p>
              </section>
              <section class="desktop-info-card">
                <div class="desktop-info-section-title">What It Adds</div>
                <p class="about-text">ChadJack layers optional sidebets, multi-hand play, and three autoplay styles onto a fast blackjack table without dragging the game into a bloated casino lobby experience.</p>
              </section>
              <section class="desktop-info-card">
                <div class="desktop-info-section-title">Why It Exists</div>
                <p class="about-text">We wanted a sharper desktop build: more hands, cleaner control over repeat action, and a ruleset that stays readable while the table still feels premium and immediate.</p>
              </section>
              <section class="desktop-info-card">
                <div class="desktop-info-section-title">Table Personality</div>
                <p class="about-text">The build keeps the ChadJack identity aggressive but controlled: gold highlights, dark utility chrome, and session tools that stay visible without flattening the felt atmosphere.</p>
              </section>
            </div>
          {/if}

          {#if $showRules}
            <div class="desktop-info-body desktop-rules-layout">
              <section class="desktop-info-card desktop-rules-summary">
                <div class="desktop-info-section-title">Quick Read</div>
                <div class="desktop-rules-grid">
                  <div class="desktop-rule-stat"><span>Blackjack</span><strong>3 to 2</strong></div>
                  <div class="desktop-rule-stat"><span>Insurance</span><strong>2 to 1</strong></div>
                  <div class="desktop-rule-stat"><span>Decks</span><strong>6 Deck Shoe</strong></div>
                  <div class="desktop-rule-stat"><span>Autoplay</span><strong>3 Modes</strong></div>
                </div>
              </section>

              <section class="desktop-info-card">
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
              </section>

              <section class="desktop-info-card">
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
              </section>
            </div>
          {/if}
        </div>
      </div>
    {/if}

    <div class="table-playfield">
      <div class="playfield-top">
        <!-- DEALER AREA -->
        <div class="dealer-area" class:dealer-area-hidden={isBet}>
          {#if $dealerHand.length > 0}
            <!-- Logo moves left of dealer cards once dealt -->
            <img src={LOGO_IMAGE} alt="ChadJack" class="dealer-logo" />
            <div class="dealer-cards-col">
              <div class="hand-value">{dealerDisplay}</div>
              <div class="cards-row">
                {#each $dealerHand as card, i}
                  <div class="card-wrap" style="margin-left: {i > 0 ? dealerOverlap : '0'}; z-index: {i}">
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
            </div>
          {:else}
            <div class="dealer-placeholder"></div>
          {/if}
        </div>

        <!-- CHAD LABS LOGO — right side, parallel with dealer logo -->
        {#if isBet && !hideBetLogoDuringRedeal}
          <div class="felt-logo-row">
            <img src={LOGO_IMAGE} alt="ChadJack" class="felt-logo felt-logo-large" />
          </div>
        {:else}
          <img src={LOGO_IMAGE} alt="ChadJack" class="felt-logo felt-logo-right" />
        {/if}
      </div>

      <div class="playfield-main">
        <!-- FIXED HEIGHT MIDDLE ZONE — always 87px, locks player cards to y=422 -->
        <div class="mid-zone">
          <div class="divider-row">
            <div class="divider-line"></div>
            <span class="divider-label">Blackjack pays 3 to 2</span>
            <div class="divider-line"></div>
          </div>
        </div>
        <!-- PLAYER HANDS -->
        <div
          class="hands-row"
          class:multi
          class:four={$numSlots === 4}
          class:three-up={isThreeDesktop}
          class:two-row={useSecondRowCardSize}
          class:count-one={$numSlots === 1}
          class:count-two={$numSlots === 2}
          class:count-three={$numSlots === 3}
          class:count-fourplus={$numSlots >= 4}
        >
      <!-- Invisible left spacer mirrors ghost width — keeps card stack at screen center -->
      {#if (isBet || isResult) && !isReplay && $numSlots < $maxHands && !isDesktop}
        <div
          class="ghost-spacer"
          class:mid-ghost-spacer={isDesktop && $numSlots === 3}
          class:compact-ghost-spacer={isDesktop && $numSlots >= 4}
        ></div>
      {/if}

      {#each $hands as hand, idx}
        {@const isActive = $activeHand === idx && isPlay}
        {@const rc = resultColor(hand.result)}
        {@const activeSb = sbSelect[idx]}
        {@const reserveSideBetLane = $sideBetsEnabled && !hand.isSplit}
        <div class="hand-col">

          <!-- Cards area -->
          <div class="cards-area">
            <div
              class="cards-col"
              class:mid-cards-col={useSecondRowCardSize}
              class:compact-cards-col={isDesktop && $numSlots > 6}
              class:has-sb={($sideBetsEnabled && (isBet || isResult)) || hand.sb.pp > 0 || hand.sb.t > 0}
            >
              <!-- Hand value bubble -->
              {#if hand.cards.length > 0}
                <div class="hv-bubble" class:active={isActive} style="color: {hand.result ? rc : C.cr}">
                  {handMsg(hand)}
                </div>
              {:else}
                <div class="hv-bubble hv-bubble-placeholder" aria-hidden="true">00</div>
              {/if}

              <!-- sb-col sits beside cards-row in a shared flex row for vertical centering -->
              <div class="sb-and-cards">
                {#if (($sideBetsEnabled && (isBet || isResult)) || hand.sb.pp > 0 || hand.sb.t > 0)}
                <div class="sb-col">
                  {#each [{k:"pp", n:"Perfect Pairs"}, {k:"t", n:"21+3"}] as sb}
                    <!-- svelte-ignore a11y-click-events-have-key-events -->
                    <!-- svelte-ignore a11y-no-static-element-interactions -->
                    {#if $sideBetsEnabled && (isBet || isResult) && activeSb === sb.k}
                      <!-- Expanded: show inline wager input -->
                      <div class="sb-box sb-box-editing" on:click|stopPropagation>
                        <span class="sb-box-label" class:sb-box-label-pp={sb.k === 'pp'} class:sb-box-label-213={sb.k === 't'}>{sb.n}</span>
                        <input
                          use:sbFocusInput
                          class="sb-wager-input"
                          inputmode="decimal"
                          placeholder="0.00"
                          value={sbDraft[idx + sb.k] ?? ''}
                          on:input={(e) => onSbDraftInput(idx, sb.k, e.currentTarget.value)}
                          on:keydown={(e) => e.key === 'Enter' && commitSbDraft(idx, sb.k)}
                          on:blur={() => commitSbDraft(idx, sb.k)}
                        />
                      </div>
                    {:else}
                      <div class="sb-box-wrap">
                        <button
                          type="button"
                          class="sb-box"
                          class:sb-active={hand.sb[sb.k] > 0}
                          on:click={() => $sideBetsEnabled && !isReplay && (isBet || isResult) && toggleSbSelect(idx, sb.k)}
                        >
                          <span class="sb-box-label" class:sb-box-label-pp={sb.k === 'pp'} class:sb-box-label-213={sb.k === 't'}>{sb.n}</span>
                          {#if hand.sb[sb.k] > 0}
                            <span class="sb-box-amt">{fmt(hand.sb[sb.k], $runtimeCurrency)}</span>
                          {/if}
                        </button>
                        {#if hand.sb[sb.k] > 0 && (isBet || isResult) && !isReplay}
                          <button type="button" class="sb-x-btn" on:click|stopPropagation={() => clearSideBet(idx, sb.k)} aria-label="Remove sidebet">✕</button>
                        {/if}
                      </div>
                    {/if}
                  {/each}
                </div>
                {/if}
                <div class="cards-row" class:active-cards-row={isActive && multi} style="min-height: {cardsRowMinH}px; position: relative;">
                {#if (isBet || isResult) && !isReplay && $numSlots > 1}
                  <button class="btn-remove-x" on:click={() => removeSlot(idx)}>×</button>
                {/if}
                {#if hand.cards.length > 0}
                  {#each hand.cards as card, i}
                    <div class="card-wrap" style="margin-left: {i > 0 ? (multi ? cardOverlapSmall : cardOverlap) : '0'}; z-index: {i}">
                      {#if customFaceCardImage(card)}
                        <div
                          class="card card-custom"
                          class:small={multi && !isDesktop}
                          class:mid-deck-card={useSecondRowCardSize}
                          class:compact-deck-card={isDesktop && $numSlots > 6}
                        >
                          <img src={customFaceCardImage(card)} alt={`${card.rank} of ${card.suit}`} class="card-custom-art" />
                        </div>
                      {:else}
                        <div
                          class="card card-face"
                          class:small={multi && !isDesktop}
                          class:red={card.suit === 'diamonds' || card.suit === 'hearts'}
                          class:mid-deck-card={useSecondRowCardSize}
                          class:compact-deck-card={isDesktop && $numSlots > 6}
                        >
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
                  <div
                    class="card-placeholder"
                    class:small={multi && !isDesktop}
                    class:mid-deck-card={useSecondRowCardSize}
                    class:compact-deck-card={isDesktop && $numSlots > 6}
                  ></div>
                  <div
                    class="card-placeholder"
                    class:small={multi && !isDesktop}
                    class:mid-deck-card={useSecondRowCardSize}
                    class:compact-deck-card={isDesktop && $numSlots > 6}
                    style="margin-left: {multi ? cardOverlapSmall : cardOverlap}; opacity: 0.5"
                  ></div>
                {/if}
              </div><!-- end cards-row -->
              </div><!-- end sb-and-cards -->




              <!-- Wager controls: 1/2·Bet·2x first, then dollar amount below -->
              {#if hand.bet > 0 || isBet || isResult}
                <div class="bet-bar" class:active-hand-bet={isActive && multi}>
                  {#if (isBet || isResult) && !isReplay && !activeSb}
                    <div class="bet-amount-row bet-amount-row-with-actions">
                      <button class="bet-quick-btn" on:click={() => adjustBetByFactor(idx, 0.5)}>1/2</button>
                      <div class="bet-input-shell">
                        <span class="bet-amount-prefix">{isSocial ? 'Play' : 'Bet'}</span>
                        <input
                          class="bet-amount-input"
                          inputmode="decimal"
                          value={betDraft[idx] ?? fmt(hand.bet, $runtimeCurrency).replace(/[^0-9.]/g, '')}
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
              {#if (isBet || isResult) && !isReplay && (betEntryMode === 'chips' || betEntryMode === 'both')}
                <div class="chip-btns">
                  {#if !activeSb && $runtimeConfig?.betLevels?.length}
                    {#each $runtimeConfig.betLevels as betLevel}
                      <button
                        class="chip-btn chip-btn-level"
                        on:click={() => onChipClick(idx, betLevel)}
                        disabled={betLevel > $balance}
                      >
                        {fmt(betLevel, $runtimeCurrency)}
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

      <!-- Add hand ghost -->
      {#if (isBet || isResult) && !isReplay && $numSlots < $maxHands && !useFooterAddSlot}
        <div
          class="ghost-wrap"
          class:with-cards={$hands.some((h) => h.cards.length > 0)}
          class:mid-ghost-wrap={useSecondRowCardSize}
          class:compact-ghost-wrap={isDesktop && $numSlots > 6}
        >
          <button
            type="button"
            class="ghost"
            class:mid-ghost={useSecondRowCardSize}
            class:compact-ghost={isDesktop && $numSlots > 6}
            on:click={addSlot}
            aria-label="Add hand"
          >+</button>
        </div>
      {/if}
        </div>
      </div>
    </div>

    <!-- BOTTOM DOCK -->
    <div class="bottom-dock" bind:clientHeight={bottomDockHeight} use:stopClick>

      <!-- Auto panel -->
      {#if $showAuto && showDesktopAutoplay}
        <div class="panel desktop-auto-panel" use:stopClick>
          <div class="desktop-auto-head">
            <div>
              <div class="desktop-panel-kicker">Autoplay Suite</div>
              <div class="panel-title">Autobet Control</div>
            </div>
            <div class="desktop-auto-mode-badge">{AUTO_MODES.find((mode) => mode.key === $autoMode)?.label}</div>
          </div>
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
          <div class="panel-hint desktop-auto-copy">Insurance is always auto-declined. Current {isSocial ? 'plays and side plays' : 'bets and side bets'} stay in place between rounds.</div>
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


      <!-- Reload -->
      {#if $balance <= 0 && isBet}
        <button class="btn-reload" on:click={() => balance.set(1_000_000_000)}>{isSocial ? 'Refill' : 'Reload'} {fmt(1_000_000_000, displayCurrency)}</button>
      {/if}


      <!-- Deal / autoplay row -->
      {#if isReplay}
        <div class="center-deal-wrap">
          <button class="btn-deal active" on:click={exitReplayMode}>
            {isResult ? "Play Again" : "Play"}
          </button>
        </div>
      {:else if $autoPlay}
        <!-- Autoplay active: stop bar fills deal slot, always visible regardless of phase -->
        <div class="center-deal-wrap">
          <button class="btn-stop-bar" on:click={() => autoPlay.set(false)}>
            <span class="stop-bar-label">STOP AUTOPLAY</span>
            <span class="stop-bar-count">{$autoCount}/{$autoMax}</span>
          </button>
        </div>
      {:else if isResult}
        <div class="center-deal-wrap">
          {#if $message}
            {@const tone = navResultTone($message)}
            <span class="result-pill" class:win={tone === 'win'} class:lose={tone === 'lose'}>
              {tone === 'win' ? 'Player' : tone === 'lose' ? 'Dealer' : 'Push'}
            </span>
          {/if}
          <div class="table-footer-row" class:with-add-slot={useFooterAddSlot}>
            {#if useFooterAddSlot}
              <button class="footer-add-slot" on:click={addSlot} aria-label="Add hand">+</button>
            {:else}
              <div class="table-footer-spacer" aria-hidden="true"></div>
            {/if}
            <button
              class="btn-deal active"
              on:click={onDeal}
            >
              {dealLabel}
            </button>
            {#if showDesktopAutoplay}
              <button class="btn-auto-launch btn-autoplay-image" class:active={$showAuto} on:click={toggleAutoPanel} aria-label="Autoplay">
                <img src={AUTOPLAY_BUTTON} alt="" />
              </button>
            {:else}
              <div class="table-footer-spacer" aria-hidden="true"></div>
            {/if}
          </div>
        </div>
      {:else if isBet}
        <div class="center-deal-wrap">
          <div class="table-footer-row" class:with-add-slot={useFooterAddSlot}>
            {#if useFooterAddSlot}
              <button class="footer-add-slot" on:click={addSlot} aria-label="Add hand">+</button>
            {:else}
              <div class="table-footer-spacer" aria-hidden="true"></div>
            {/if}
            <button
              class="btn-deal"
              class:active={$canDeal || isResult}
              disabled={!$canDeal && !isResult}
              on:click={($canDeal || isResult) ? onDeal : undefined}
            >
              {dealLabel}
            </button>
            {#if showDesktopAutoplay}
              <button class="btn-auto-launch btn-autoplay-image" class:active={$showAuto} on:click={toggleAutoPanel} aria-label="Autoplay">
                <img src={AUTOPLAY_BUTTON} alt="" />
              </button>
            {:else}
              <div class="table-footer-spacer" aria-hidden="true"></div>
            {/if}
          </div>
        </div>
      {/if}
      <!-- Action area -->
      {#if isPlay && activeH && !isReplay && !$autoPlay}
        <div class="action-area-fixed">
          <div class="action-grid">
            <button class="btn-action" on:click={hit}>Hit</button>
            <button class="btn-action" on:click={stand}>Stand</button>
            <button class="btn-action" class:dim={!canSplit} disabled={!canSplit} on:click={canSplit ? split : undefined}>Split</button>
            <button class="btn-action" class:dim={!canDouble} disabled={!canDouble} on:click={canDouble ? doubleDown : undefined}>x2</button>
          </div>
        </div>
      {/if}


    </div>
  </div>
</div>
{/if}

<style>
  :global(*) { box-sizing: border-box; margin: 0; padding: 0; }
  :global(body) {
    background: #071a0e;
    color: #f2e8d0;
    font-family: 'Inter', sans-serif;
    -webkit-tap-highlight-color: transparent;
    zoom: 0.97;
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
    transition: opacity 0.7s;
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
      padding: 0;
      border-radius: 0;
      background: transparent;
      box-shadow: none;
      backdrop-filter: none;
    }
    .intro-video {
      border-radius: 0;
      width: 100vw;
      min-height: 100vh;
      min-height: 100dvh;
      object-fit: cover;
    }
  }
  /* TABLE */
  .table-wrap {
    --desktop-ui-zoom: 0.8;
    --desktop-side-gutter-comp: 0px;
    --desktop-autoplay-button-width: 108px;
    min-height: 100vh;
    min-height: 100dvh;
    height: 100vh;
    height: 100dvh;
    width: 100%;
    display: flex;
    flex-direction: column;
    overflow: hidden;
    position: relative;
  }

  .table-wrap:not(.stacked-layout) {
    --desktop-side-gutter-comp: calc(((100% / var(--desktop-ui-zoom)) - 100%) / 2);
    zoom: var(--desktop-ui-zoom);
    width: calc(100% / var(--desktop-ui-zoom));
    min-height: calc(100vh / var(--desktop-ui-zoom));
    min-height: calc(100dvh / var(--desktop-ui-zoom));
    height: calc(100vh / var(--desktop-ui-zoom));
    height: calc(100dvh / var(--desktop-ui-zoom));
    margin-left: calc((100% - (100% / var(--desktop-ui-zoom))) / 2);
    transform-origin: top center;
  }

  .balance-row {
    display: flex;
    justify-content: space-between;
    gap: 12px;
    padding: 6px 14px 4px;
    min-height: 42px;
    align-items: center;
    border-bottom: none;
    flex-shrink: 0;
    background: transparent;
  }
  .table-wrap:not(.stacked-layout) .balance-row {
    padding-left: calc(14px + var(--desktop-side-gutter-comp));
    padding-right: calc(14px + var(--desktop-side-gutter-comp));
  }
  .header-controls,
  .utility-btns {
    display: flex;
    gap: 6px;
    align-items: center;
  }
  .header-controls {
    position: relative;
    gap: 12px;
  }
  .options-anchor {
    position: relative;
    display: flex;
    align-items: center;
  }
  .btn-options-toggle,
  .btn-options-item {
    font-family: 'Oswald', sans-serif !important;
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }
  .btn-options-toggle {
    min-height: 40px !important;
    padding: 7px 18px !important;
    border-radius: 999px !important;
    border: 1px solid rgba(232, 212, 139, 0.28) !important;
    background:
      linear-gradient(180deg, rgba(15, 34, 24, 0.94) 0%, rgba(8, 20, 14, 0.96) 100%) !important;
    color: #f4ead0 !important;
    font-size: 14px !important;
    font-weight: 700 !important;
    box-shadow:
      inset 0 1px 0 rgba(255,255,255,0.08),
      0 14px 30px rgba(0,0,0,0.28) !important;
  }
  .btn-options-toggle.active {
    border-color: rgba(232, 212, 139, 0.68) !important;
    background:
      linear-gradient(180deg, rgba(70, 50, 18, 0.92) 0%, rgba(28, 20, 8, 0.96) 100%) !important;
    color: #fff4cf !important;
  }
  .mobile-balance-pill {
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
  .desktop-balance-pill {
    font-size: 16px;
    min-height: 38px;
    padding: 0 14px;
  }
  .desktop-options-drawer {
    position: absolute;
    top: calc(100% + 12px);
    right: 0;
    left: auto;
    width: min(420px, calc(100vw - 24px));
    z-index: 40;
    padding: 0;
    display: flex;
    flex-direction: column;
    gap: 10px;
  }
  .desktop-options-drawer.full-panel-open {
    width: min(620px, calc(100vw - 24px));
  }
  .desktop-options-shell {
    border-radius: 26px;
    border: 1px solid rgba(232, 212, 139, 0.18);
    background:
      linear-gradient(180deg, rgba(17, 31, 23, 0.97) 0%, rgba(8, 16, 13, 0.985) 100%);
    box-shadow:
      0 28px 70px rgba(0,0,0,0.42),
      inset 0 1px 0 rgba(255,255,255,0.05),
      inset 0 0 0 1px rgba(255,255,255,0.02);
    backdrop-filter: blur(18px);
    padding: 18px;
  }
  .desktop-options-head {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 16px;
    margin-bottom: 14px;
  }
  .desktop-options-title {
    font-family: 'Bebas Neue', 'Oswald', sans-serif;
    font-size: 34px;
    letter-spacing: 0.06em;
    color: #f6edd6;
    line-height: 0.95;
  }
  .desktop-options-status {
    display: inline-flex;
    align-items: center;
    min-height: 34px;
    padding: 0 14px;
    border-radius: 999px;
    border: 1px solid rgba(232, 212, 139, 0.2);
    background: rgba(232, 212, 139, 0.08);
    color: #e8d48b;
    font-family: 'Oswald', sans-serif;
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    white-space: nowrap;
  }
  .mobile-options-column {
    display: grid;
    grid-template-columns: 1fr;
    gap: 10px;
  }
  .desktop-options-grid {
    gap: 10px;
  }
  .btn-options-item {
    min-height: 72px !important;
    padding: 14px 16px !important;
    border-radius: 18px !important;
    border: 1px solid rgba(232, 212, 139, 0.14) !important;
    background:
      linear-gradient(180deg, rgba(255,255,255,0.035) 0%, rgba(255,255,255,0.015) 100%) !important;
    color: #ffffff !important;
    font-size: 13px !important;
    font-weight: 700 !important;
    box-shadow:
      inset 0 1px 0 rgba(255,255,255,0.045),
      0 12px 26px rgba(0,0,0,0.18);
    justify-content: space-between !important;
    text-align: left !important;
  }
  .btn-options-item.active {
    border-color: rgba(232, 212, 139, 0.45) !important;
    background:
      linear-gradient(180deg, rgba(70, 52, 18, 0.88) 0%, rgba(27, 21, 10, 0.96) 100%) !important;
    color: #fff4cf !important;
    box-shadow:
      inset 0 1px 0 rgba(255, 235, 173, 0.2),
      0 18px 34px rgba(0,0,0,0.24);
  }
  .btn-options-toggle-pill {
    display: flex !important;
    align-items: center;
    justify-content: space-between;
    gap: 14px;
  }
  .desktop-option-copy {
    display: flex;
    flex-direction: column;
    gap: 4px;
    min-width: 0;
  }
  .desktop-option-title {
    font-family: 'Oswald', sans-serif;
    font-size: 18px;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: inherit;
  }
  .desktop-option-meta {
    font-family: 'Inter', sans-serif;
    font-size: 12px;
    line-height: 1.45;
    letter-spacing: 0.01em;
    color: rgba(242, 232, 208, 0.68);
  }
  .options-mini-toggle {
    min-width: 58px;
    height: 34px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    border-radius: 999px;
    background: rgba(4, 10, 8, 0.94);
    border: 1px solid rgba(255,255,255,0.14);
    box-shadow: inset 0 1px 0 rgba(255,255,255,0.04);
    color: #ffffff;
    font-size: 11px;
    font-weight: 700;
    line-height: 1;
    letter-spacing: 0.1em;
    text-transform: uppercase;
  }
  .desktop-options-panel {
    margin-top: 16px;
    max-height: none;
    overflow-y: auto;
  }
  .felt-panel-inline,
  .rules-panel-inline,
  .about-panel-inline {
    width: 100%;
  }
  .sb-col-hidden {
    display: none;
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
    background: rgba(8, 20, 12, 0.86);
    border: 1px solid rgba(212, 168, 64, 0.48);
    color: #e0b74a;
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
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    justify-content: center;
    gap: 2px;
  }
  .total-wager-sub {
    font-size: 15px;
    font-family: 'Oswald', sans-serif;
    font-weight: 600;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: #ffffff;
    white-space: nowrap;
  }
  .balance     { font-size: 26px; font-weight: 700; white-space: nowrap; font-family: 'Oswald', sans-serif; letter-spacing: 0.02em; }
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
  .replay-banner {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 14px;
  }
  .replay-banner-copy {
    display: flex;
    flex-direction: column;
    gap: 2px;
  }
  .btn-replay-exit {
    border: 1px solid rgba(212, 178, 88, 0.45);
    background: rgba(11, 28, 18, 0.78);
    color: #f2e8d0;
    border-radius: 999px;
    padding: 10px 18px;
    font-size: 14px;
    font-weight: 800;
    letter-spacing: 0.04em;
    text-transform: uppercase;
    white-space: nowrap;
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
    background: #0a2a16;
    transform-origin: top center;
    overflow-y: auto;
    overflow-x: hidden;
    -webkit-overflow-scrolling: touch;
  }
  .table-playfield,
  .playfield-top,
  .playfield-main {
    display: contents;
  }
  .felt.felt-theme-satin-green,
  .table-wrap.felt-theme-satin-green {
    background:
      radial-gradient(ellipse at 50% 33%, rgba(26, 86, 49, 0.24), rgba(8, 31, 19, 0.68) 70%, rgba(4, 17, 11, 0.88) 100%),
      linear-gradient(180deg, rgba(21, 67, 40, 0.12), rgba(8, 26, 16, 0.28)),
      url('/green.felt.final.png');
    background-size: cover, cover, cover;
    background-position: center center, center center, center center;
    background-repeat: no-repeat, no-repeat, no-repeat;
    background-blend-mode: multiply, color, normal;
  }
  .felt.felt-theme-classic-felt,
  .table-wrap.felt-theme-classic-felt {
    background:
      radial-gradient(ellipse at 50% 33%, rgba(20, 74, 42, 0.3), rgba(9, 34, 20, 0.76) 70%, rgba(5, 18, 12, 0.9) 100%),
      url('/felt-green-texture.png');
    background-size: cover, 780px 460px;
    background-position: center center, center center;
    background-repeat: no-repeat, repeat;
    background-blend-mode: multiply, normal;
  }
  .felt.felt-theme-dark-marble,
  .table-wrap.felt-theme-dark-marble {
    background:
      radial-gradient(ellipse at 38% 30%, rgba(56, 66, 84, 0.36), transparent 42%),
      radial-gradient(ellipse at 72% 70%, rgba(33, 41, 56, 0.28), transparent 48%),
      linear-gradient(140deg, #1b222f 0%, #141a24 45%, #10151d 100%),
      repeating-linear-gradient(
        25deg,
        rgba(255,255,255,0.04) 0px,
        rgba(255,255,255,0.04) 1px,
        rgba(255,255,255,0) 1px,
        rgba(255,255,255,0) 18px
      );
    background-size: cover, cover, cover, auto;
    background-repeat: no-repeat, no-repeat, no-repeat, repeat;
    background-blend-mode: screen, normal, normal, normal;
  }
  .felt.felt-theme-onyx-gold,
  .table-wrap.felt-theme-onyx-gold {
    background:
      radial-gradient(circle at 50% 18%, rgba(179, 136, 41, 0.16), transparent 42%),
      linear-gradient(180deg, #161311 0%, #0f0d0c 100%),
      repeating-linear-gradient(
        115deg,
        rgba(212,168,64,0.07) 0px,
        rgba(212,168,64,0.07) 1px,
        rgba(0,0,0,0) 1px,
        rgba(0,0,0,0) 14px
      );
    background-size: cover, cover, auto;
    background-repeat: no-repeat, no-repeat, repeat;
  }
  .felt.felt-theme-walnut-top,
  .table-wrap.felt-theme-walnut-top {
    background:
      radial-gradient(ellipse at 50% 26%, rgba(96, 63, 33, 0.22), transparent 44%),
      linear-gradient(180deg, #3a2719 0%, #2a1c12 55%, #21160f 100%),
      repeating-linear-gradient(
        90deg,
        rgba(255,255,255,0.03) 0px,
        rgba(255,255,255,0.03) 2px,
        rgba(0,0,0,0.05) 2px,
        rgba(0,0,0,0.05) 10px
      );
    background-size: cover, cover, auto;
    background-repeat: no-repeat, no-repeat, repeat;
  }
  .felt.felt-theme-velvet-blue,
  .table-wrap.felt-theme-velvet-blue {
    background:
      radial-gradient(circle at 50% 16%, rgba(106, 145, 224, 0.18), transparent 38%),
      radial-gradient(ellipse at 50% 33%, rgba(24, 56, 112, 0.26), rgba(7, 20, 52, 0.78) 70%, rgba(4, 12, 32, 0.92) 100%),
      url('/velvet-blue-base.png');
    background-size: cover, cover, cover;
    background-position: center center, center center, center center;
    background-repeat: no-repeat, no-repeat, no-repeat;
    background-blend-mode: screen, multiply, normal;
  }
  .felt.felt-theme-velvet-green,
  .table-wrap.felt-theme-velvet-green {
    background:
      radial-gradient(circle at 50% 16%, rgba(127, 214, 174, 0.18), transparent 38%),
      radial-gradient(ellipse at 50% 33%, rgba(24, 110, 83, 0.26), rgba(9, 58, 40, 0.78) 70%, rgba(4, 31, 22, 0.92) 100%),
      url('/velvet-emerald-base.png');
    background-size: cover, cover, cover;
    background-position: center center, center center, center center;
    background-repeat: no-repeat, no-repeat, no-repeat;
    background-blend-mode: screen, multiply, normal;
  }
  .felt.felt-theme-velvet-black,
  .table-wrap.felt-theme-velvet-black {
    background:
      radial-gradient(circle at 50% 16%, rgba(116, 126, 151, 0.12), transparent 38%),
      radial-gradient(ellipse at 50% 33%, rgba(36, 46, 66, 0.28), rgba(12, 16, 24, 0.82) 70%, rgba(6, 8, 12, 0.94) 100%),
      url('/velvet-black-base.png');
    background-size: cover, cover, cover;
    background-position: center center, center center, center center;
    background-repeat: no-repeat, no-repeat, no-repeat;
    background-blend-mode: screen, multiply, normal;
  }
  .felt.felt-theme-ridge-blue,
  .table-wrap.felt-theme-ridge-blue {
    background:
      radial-gradient(circle at 50% 16%, rgba(106, 145, 224, 0.18), transparent 38%),
      radial-gradient(ellipse at 50% 33%, rgba(24, 56, 112, 0.26), rgba(7, 20, 52, 0.78) 70%, rgba(4, 12, 32, 0.92) 100%),
      url('/ridge-blue-base.png');
    background-size: cover, cover, cover;
    background-position: center center, center center, center center;
    background-repeat: no-repeat, no-repeat, no-repeat;
    background-blend-mode: screen, multiply, normal;
  }
  .felt.felt-theme-ridge-green,
  .table-wrap.felt-theme-ridge-green {
    background:
      radial-gradient(circle at 50% 16%, rgba(127, 214, 174, 0.18), transparent 38%),
      radial-gradient(ellipse at 50% 33%, rgba(24, 110, 83, 0.26), rgba(9, 58, 40, 0.78) 70%, rgba(4, 31, 22, 0.92) 100%),
      url('/ridge-green-base.png');
    background-size: cover, cover, cover;
    background-position: center center, center center, center center;
    background-repeat: no-repeat, no-repeat, no-repeat;
    background-blend-mode: screen, multiply, normal;
  }
  .felt.felt-theme-ridge-black,
  .table-wrap.felt-theme-ridge-black {
    background:
      radial-gradient(circle at 50% 16%, rgba(116, 126, 151, 0.12), transparent 38%),
      radial-gradient(ellipse at 50% 33%, rgba(36, 46, 66, 0.28), rgba(12, 16, 24, 0.82) 70%, rgba(6, 8, 12, 0.94) 100%),
      url('/ridge-black-base.png');
    background-size: cover, cover, cover;
    background-position: center center, center center, center center;
    background-repeat: no-repeat, no-repeat, no-repeat;
    background-blend-mode: screen, multiply, normal;
  }
  .felt.felt-theme-felt-blue,
  .table-wrap.felt-theme-felt-blue {
    background:
      radial-gradient(circle at 50% 16%, rgba(106, 145, 224, 0.18), transparent 38%),
      radial-gradient(ellipse at 50% 33%, rgba(24, 56, 112, 0.26), rgba(7, 20, 52, 0.78) 70%, rgba(4, 12, 32, 0.92) 100%),
      url('/felt-blue-base.png');
    background-size: cover, cover, cover;
    background-position: center center, center center, center center;
    background-repeat: no-repeat, no-repeat, no-repeat;
    background-blend-mode: screen, multiply, normal;
  }
  .felt.felt-theme-felt-green,
  .table-wrap.felt-theme-felt-green {
    background:
      radial-gradient(circle at 50% 16%, rgba(127, 214, 174, 0.18), transparent 38%),
      radial-gradient(ellipse at 50% 33%, rgba(24, 110, 83, 0.26), rgba(9, 58, 40, 0.78) 70%, rgba(4, 31, 22, 0.92) 100%),
      url('/felt-green-base.png');
    background-size: cover, cover, cover;
    background-position: center center, center center, center center;
    background-repeat: no-repeat, no-repeat, no-repeat;
    background-blend-mode: screen, multiply, normal;
  }
  .felt.felt-theme-felt-black,
  .table-wrap.felt-theme-felt-black {
    background:
      radial-gradient(circle at 50% 16%, rgba(116, 126, 151, 0.12), transparent 38%),
      radial-gradient(ellipse at 50% 33%, rgba(36, 46, 66, 0.28), rgba(12, 16, 24, 0.82) 70%, rgba(6, 8, 12, 0.94) 100%),
      url('/felt-black-base.png');
    background-size: cover, cover, cover;
    background-position: center center, center center, center center;
    background-repeat: no-repeat, no-repeat, no-repeat;
    background-blend-mode: screen, multiply, normal;
  }
  .felt::before {
    content: "";
    position: absolute;
    inset: 0;
    pointer-events: none;
    background:
      radial-gradient(circle at 24% 22%, rgba(255,255,255,0.045), transparent 42%),
      radial-gradient(circle at 76% 74%, rgba(0,0,0,0.16), transparent 48%),
      repeating-linear-gradient(
        0deg,
        rgba(255,255,255,0.014) 0px,
        rgba(255,255,255,0.014) 1px,
        rgba(0,0,0,0.018) 1px,
        rgba(0,0,0,0.018) 3px
      ),
      repeating-linear-gradient(
        90deg,
        rgba(255,255,255,0.01) 0px,
        rgba(255,255,255,0.01) 1px,
        rgba(0,0,0,0.014) 1px,
        rgba(0,0,0,0.014) 4px
      );
    opacity: 0;
    z-index: 0;
  }
  .felt > * {
    position: relative;
    z-index: 1;
  }
  .table-wrap.stacked-layout[class*="felt-theme-"] {
    background: transparent !important;
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
  .cards-row   { display: flex; flex-wrap: nowrap; overflow-x: auto; -webkit-overflow-scrolling: touch; }
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
    top: 0; left: 0; right: 0; bottom: 0;
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
    position: relative;
  }
  .card-back-logo {
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
    object-fit: cover;
    object-position: center;
    opacity: 1;
    filter: none;
  }

  .card-corner { position: absolute; display: flex; flex-direction: column; align-items: center; line-height: 1; }
  .card-face .card-tl     { top: 10px; left: 12px; }
  .card-face .card-br     { bottom: 10px; right: 12px; transform: rotate(180deg); }
  .card-face.small .card-tl { top: 10px; left: 12px; }
  .card-face.small .card-br { bottom: 10px; right: 12px; }

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
    background: rgba(0,0,0,0.45);
    padding: 2px 14px;
    border-radius: 12px;
    font-size: 18px;
    font-weight: 600;
    margin-bottom: 4px;
    border: 1px solid transparent;
    text-align: center;
    font-family: 'Oswald', sans-serif;
    letter-spacing: 0.02em;
  }
  .hv-bubble.active {
    background: rgba(212,168,64,0.15);
    border-color: rgba(212,168,64,0.4);
    animation: glow 1.5s ease infinite;
  }
  .hv-bubble-placeholder {
    visibility: hidden;
    pointer-events: none;
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
  .dealer-result-text.win  { color: #2db870; }
  .dealer-result-text.lose { color: #ef5350; }

  /* FIXED HEIGHT MID ZONE — keeps player cards locked */
  .mid-zone {
    height: 28px !important;
    min-height: 28px !important;
    max-height: 28px !important;
    flex-shrink: 0 !important;
    display: flex;
    flex-direction: column;
    justify-content: center;
    overflow: visible;
  }

  /* DIVIDER — play screen */
  .divider-row {
    display: flex;
    align-items: center;
    height: 28px;
    flex-shrink: 0;
    margin-top: 0;
    margin-bottom: 0;
  }
  .divider-row.has-result {
    gap: 12px;
  }
  .divider-line  { flex: 1; height: 1px; background: rgba(212,168,64,0.35); }
  .divider-label {
    font-size: 13px;
    padding: 0 14px;
    opacity: 1;
    color: rgba(255,255,255,0.78);
    font-family: 'Inter', sans-serif;
    font-weight: 700;
    letter-spacing: 0.1em;
    text-transform: uppercase;
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
  .hands-row { display: flex; justify-content: center; gap: 16px; padding-top: 0; min-height: 0; flex: 0 0 auto; align-items: center; flex-wrap: nowrap; }
  .hands-row.multi { column-gap: 125px; }
  .hand-col  { display: flex; flex-direction: column; align-items: flex-start; flex: 0 0 auto; min-width: 0; justify-content: flex-start; }

  /* WAGER LABEL */
  .bet-bar {
    margin-top: 1px;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 2px;
  }
  /* When sb-col is visible, shift the sb-and-cards block left by (72px + 4px gap) / 2 = 38px
     so the cards-row lands at cards-col center — directly under the hv-bubble and bet-bar */
  .cards-col.has-sb .sb-and-cards { margin-left: -38px; }
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
    border: 1px solid rgba(232, 212, 139, 0.7);
    background: linear-gradient(180deg, #e3bc54 0%, #c5972f 55%, #9d7723 100%);
    color: #17130a;
    box-shadow: inset 0 1px 0 rgba(255,255,255,0.26);
    text-shadow: none;
    font-size: 16px;
    font-weight: 700;
  }
  .bet-amount-row {
    display: inline-flex;
    align-items: center;
    gap: 0;
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
  .bet-amount-row-with-actions {
    width: 100%;
    justify-content: center;
  }
  .bet-input-shell {
    position: relative;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    padding: 3px 8px;
    border-radius: 12px;
    background: rgba(8, 20, 12, 0.72);
    border: 1px solid rgba(232, 212, 139, 0.18);

  }
  .bet-amount-row .bet-quick-btn:first-child {
    margin-right: -1px;
    border-top-right-radius: 12px;
    border-bottom-right-radius: 12px;
  }
  .bet-amount-row .bet-quick-btn:last-child {
    margin-left: -1px;
    border-top-left-radius: 12px;
    border-bottom-left-radius: 12px;
  }
  .bet-amount-prefix {
    position: absolute;
    left: 8px;
    font-size: 14px;
    color: #bfb49a;
    pointer-events: none;
  }
  .bet-amount-input {
    width: 92px;
    border: none;
    outline: none;
    background: transparent;
    color: #f2e8d0;
    font-family: 'Oswald', sans-serif;
    font-size: 20px;
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
  .cards-col  { min-width: 104px; display: flex; flex-direction: column; align-items: center; }

  .sb-box {
    width: 72px; min-height: 52px;
    border-radius: 7px;
    border: 2.5px dashed rgba(255,255,255,0.55);
    background: rgba(242,232,208,0.02);
    appearance: none;
    cursor: pointer;
    display: flex; flex-direction: column; align-items: center; justify-content: center;
    gap: 2px; padding: 5px 4px;
    transition: all 0.15s;
    color: rgba(242,232,208,0.35);
    user-select: none;
    font: inherit;
  }
  .sb-box.sb-active {
    border-style: solid;
    border-color: rgba(232,212,139,0.5);
    background: rgba(232,212,139,0.06);
    color: #e8d48b;
  }
  .sb-box.sb-selected {
    border-color: #d4a840;
    background: rgba(212,168,64,0.18);
    box-shadow: 0 0 10px rgba(212,168,64,0.3);
    color: #f2e8d0;
  }
  .sb-box-label { font-size: 12px; font-weight: 700; text-align: center; line-height: 1.2; font-family: 'Oswald', sans-serif; letter-spacing: 0.04em; text-transform: uppercase; }
  .sb-box-label-pp { color: rgba(255,255,255,0.78); }
  .sb-box-label-213 { color: rgba(255,255,255,0.78); }
  .sb-box-label-213 { font-size: 13px; }
  .sb-box-amt   { font-size: 14px; font-weight: 700; color: #e8d48b; }
  .sb-box-wrap { position: relative; }
  .sb-x-btn {
    position: absolute; top: -5px; left: -5px;
    width: 15px; height: 15px; border-radius: 50%;
    background: #000; color: #fff;
    font-size: 8px; font-weight: 900; line-height: 1;
    cursor: pointer; z-index: 10;
    display: flex; align-items: center; justify-content: center;
    appearance: none; border: 0; padding: 0; font-family: inherit;
  }
  .sb-box-editing {
    width: 72px; min-height: 52px;
    border-radius: 7px;
    border: 1.5px solid #d4a840;
    background: rgba(212,168,64,0.12);
    display: flex; flex-direction: column; align-items: center; justify-content: center;
    gap: 3px; padding: 5px 4px;
    color: #f2e8d0;
  }
  .sb-wager-input {
    width: 60px;
    background: rgba(0,0,0,0.35);
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
  .ghost {
    width: 104px; height: 146px; border-radius: 8px;
    border: 2.5px dashed rgba(255,255,255,0.55);
    background: rgba(242,232,208,0.03);
    appearance: none;
    cursor: pointer;
    display: flex; align-items: center; justify-content: center;
    font-size: 28px; color: #f2e8d0; opacity: 0.2;
    transition: all 0.2s;
    font: inherit;
  }
  .ghost:hover { opacity: 0.4; }

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
    background: transparent;
    padding-top: 16px;
  }

  /* CENTERED DEAL */
  .center-deal-wrap {
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: 8px 0 0;
    flex-shrink: 0;
  }
  /* deal-auto-row: deal button + auto launch button side by side */
  .deal-auto-row {
    display: grid;
    grid-template-columns: var(--desktop-autoplay-button-width) minmax(0, 1fr) var(--desktop-autoplay-button-width);
    column-gap: 8px;
    width: min(832px, calc(100% - 12px));
    align-items: stretch;
  }
  .deal-auto-row .btn-deal {
    grid-column: 2;
    width: 100%;
  }
  .table-footer-row {
    --table-footer-side-width: 132px;
    display: grid;
    grid-template-columns: var(--table-footer-side-width) minmax(0, auto) var(--table-footer-side-width);
    column-gap: 12px;
    width: min(860px, calc(100% - 12px));
    align-items: stretch;
    justify-content: center;
  }
  .center-deal-wrap .table-footer-row .btn-deal {
    grid-column: 2;
    justify-self: center;
    width: min(546px, calc(100vw - 360px));
  }
  .table-footer-spacer {
    width: var(--table-footer-side-width);
    min-height: 65px;
  }
  .footer-add-slot {
    width: var(--table-footer-side-width);
    min-height: 65px;
    border-radius: 16px;
    border: 2.5px dashed rgba(255,255,255,0.68);
    background: rgba(242,232,208,0.03);
    color: rgba(255,255,255,0.78);
    font-family: 'Oswald', sans-serif;
    font-size: 26px;
    font-weight: 700;
    line-height: 1;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    justify-self: end;
    margin-right: 50px;
    cursor: pointer;
    transition: opacity 0.2s, background 0.2s, border-color 0.2s;
    opacity: 0.82;
  }
  .footer-add-slot:hover {
    opacity: 1;
    background: rgba(242,232,208,0.05);
    border-color: rgba(255,255,255,0.84);
  }
  .btn-auto-launch {
    grid-column: 3;
    justify-self: end;
    flex-shrink: 0;
    padding: 0;
    border-radius: 0;
    border: none;
    background: transparent;
    width: var(--desktop-autoplay-button-width);
    display: inline-flex;
    align-items: center;
    justify-content: center;
    white-space: nowrap;
  }
  .btn-autoplay-image img {
    display: block;
    width: 100%;
    height: auto;
  }
  .btn-auto-launch.active {
    filter: drop-shadow(0 0 8px rgba(232, 212, 139, 0.4));
  }
  .result-pill {
    display: block;
    text-align: center;
    margin: 0 auto 8px;
    padding: 5px 22px;
    border-radius: 999px;
    border: 1.5px solid rgba(255,255,255,0.18);
    background: rgba(0,0,0,0.35);
    font-family: 'Oswald', sans-serif;
    font-size: 16px;
    font-weight: 700;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: #bfb49a;
    white-space: nowrap;
    pointer-events: none;
    width: fit-content;
  }
  .result-pill.win  { color: #2db870; border-color: rgba(45,184,112,0.45); background: rgba(45,184,112,0.1); }
  .result-pill.lose { color: #ef5350; border-color: rgba(239,83,80,0.4);  background: rgba(239,83,80,0.08); }
  /* Stop bar lives in center-deal-wrap during autoplay */
  .center-deal-wrap .btn-stop-bar {
    width: min(600px, calc(100% - 12px));
    min-height: 65px;
    font-size: 22px;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 14px;
  }
  .stop-bar-label { font-weight: 700; letter-spacing: 0.05em; }
  .stop-bar-count { font-size: 0.78em; opacity: 0.82; font-variant-numeric: tabular-nums; }
  .center-deal-wrap .btn-deal {
    width: min(360px, calc(100% - 12px));
    min-height: 65px;
    font-size: 25px;
  }

  /* Result phase: pin Next Hand + result pill to the bottom of the viewport.
     No background — let the felt show through. The pill has its own opaque bg. */
  .table-wrap.phase-result .center-deal-wrap {
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    z-index: 50;
    padding: 8px 0 max(16px, env(safe-area-inset-bottom));
    background: transparent;
    align-items: center;
  }
  /* Give the result pill a solid-enough background so it's readable over any wager pill */
  .table-wrap.phase-result .result-pill {
    background: rgba(0,0,0,0.75);
    border-color: rgba(255,255,255,0.22);
  }
  .table-wrap.phase-result .result-pill.win  { background: rgba(30,110,68,0.92); border-color: rgba(45,184,112,0.6); }
  .table-wrap.phase-result .result-pill.lose { background: rgba(110,30,30,0.88); border-color: rgba(239,83,80,0.55); }

  .action-area-fixed { display: flex; flex-direction: column; justify-content: flex-end; margin-top: 4px; }
  .action-area-spacer { flex: 1; }
  .action-wager-label {
    text-align: center;
    font-family: 'Oswald', sans-serif;
    font-size: 15px;
    font-weight: 600;
    color: rgba(242,232,208,0.6);
    letter-spacing: 0.06em;
    text-transform: uppercase;
    margin-bottom: 3px;
  }
  .action-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 4px;
    margin-bottom: 5px;
    padding: 4px;
    border-radius: 10px;
    border: 1px solid rgba(130, 102, 34, 0.9);
    background:
      linear-gradient(180deg, rgba(229, 188, 82, 0.94), rgba(172, 136, 49, 0.94));
    box-shadow:
      inset 0 0 0 1px rgba(255,255,255,0.18),
      inset 0 -12px 18px rgba(0,0,0,0.18),
      0 1px 0 rgba(255,255,255,0.03);
  }
  .action-grid.dim {
    border-color: rgba(44, 52, 69, 0.9);
    background: linear-gradient(180deg, rgba(20, 24, 36, 0.92), rgba(12, 15, 24, 0.95));
    box-shadow:
      inset 0 0 0 1px rgba(255,255,255,0.04),
      inset 0 -12px 18px rgba(0,0,0,0.35);
  }
  /* Stop bar base styles (scoped via center-deal-wrap above) */
  .btn-stop-bar {
    padding: 0;
    background: #c62828;
    color: #fff;
    font-family: 'Oswald', sans-serif;
    font-weight: 700;
    border: none;
    border-radius: 8px;
    cursor: pointer;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    margin-bottom: 5px;
    transition: background 0.15s;
  }
  .btn-stop-bar:hover { background: #e53935; }
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
    background: linear-gradient(180deg, #e8bf58, #b99135);
    color: #111;
    border: 1px solid rgba(130, 102, 34, 0.9);
    box-shadow:
      inset 0 1px 0 rgba(255,255,255,0.2),
      inset 0 -10px 14px rgba(0,0,0,0.15);
    font-family: 'Oswald', sans-serif;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    text-shadow: 0 1px 0 rgba(255,255,255,0.12);
  }
  .btn-action.dim {
    background: linear-gradient(180deg, rgba(34, 39, 52, 0.9), rgba(20, 24, 34, 0.95));
    color: rgba(186, 194, 208, 0.58);
    border-color: rgba(72, 80, 98, 0.72);
    box-shadow: inset 0 1px 0 rgba(255,255,255,0.03);
    text-shadow: none;
  }

  .deal-row {
    display: flex; gap: 6px; align-items: stretch; margin-bottom: 5px;
    max-width: 360px; margin-left: auto; margin-right: auto;
  }
  .btn-deal {
    flex: 1; padding: 12px 0; border-radius: 8px;
    border: none;
    background: linear-gradient(135deg, #d4a840, #a88a30);
    color: #071a0e;
    font-size: 18px; font-weight: 700;
    opacity: 1;
    font-family: 'Oswald', sans-serif;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    text-shadow: 0 1px 0 rgba(255,255,255,0.12);
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
  .btn-tab.btn-utility {
    background: rgba(8, 20, 12, 0.86);
    border-color: rgba(255,255,255,0.52);
    color: rgba(255,255,255,0.78);
  }
  .btn-tab.btn-utility.active {
    background: rgba(8, 20, 12, 0.94);
    border-color: rgba(255,255,255,0.78);
    color: rgba(255,255,255,0.9);
  }

  .auto-confirm-row {
    display: flex;
    gap: 8px;
    margin-top: 10px;
  }
  .auto-confirm-copy {
    margin-top: 8px;
  }
  .btn-auto-cancel {
    flex: 1;
    min-height: 42px;
    border-radius: 999px;
    border: 1px solid rgba(232, 212, 139, 0.28);
    background: rgba(8, 22, 15, 0.86);
    color: #f2e8d0;
    font-family: 'Oswald', sans-serif;
    font-size: 18px;
    letter-spacing: 0.03em;
  }

  .btn-stop { font-size: 14px; padding: 3px 10px; border-radius: 4px; border: 1px solid #ef5350; background: transparent; color: #ef5350; }

  /* PANELS */
  .panel {
    background:
      linear-gradient(180deg, rgba(18, 35, 26, 0.96) 0%, rgba(8, 16, 13, 0.985) 100%);
    border: 1px solid rgba(232, 212, 139, 0.18);
    border-radius: 24px;
    padding: 18px 20px;
    margin-top: 10px;
    box-shadow:
      0 26px 60px rgba(0,0,0,0.34),
      inset 0 1px 0 rgba(255,255,255,0.05);
    animation: fadeIn 0.15s ease;
  }
  .desktop-panel-kicker {
    font-family: 'Oswald', sans-serif;
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 0.16em;
    text-transform: uppercase;
    color: #d6b062;
    opacity: 0.95;
  }
  .panel-label { font-size: 14px; margin-bottom: 8px; opacity: 0.72; letter-spacing: 0.12em; text-transform: uppercase; }
  .panel-hint  { font-size: 15px; opacity: 0.64; margin-bottom: 10px; line-height: 1.55; }
  .mode-row,
  .speed-row   { display: flex; gap: 8px; margin-bottom: 12px; flex-wrap: wrap; }
  .btn-mode,
  .btn-speed   {
    flex: 1;
    padding: 10px 12px;
    font-size: 16px;
    border-radius: 14px;
    border: 1px solid rgba(232, 212, 139, 0.14);
    background: rgba(255,255,255,0.025);
    color: #d7cfbb;
    min-width: 110px;
    font-family: 'Oswald', sans-serif;
    letter-spacing: 0.06em;
    text-transform: uppercase;
  }
  .btn-mode.active,
  .btn-speed.active {
    border-color: #e8d48b;
    background: linear-gradient(180deg, rgba(84, 63, 24, 0.84), rgba(29, 22, 10, 0.94));
    color: #fff0c1;
    box-shadow: inset 0 1px 0 rgba(255,255,255,0.08);
  }
  .mode-hint { min-height: 46px; }

  .desktop-auto-panel {
    position: fixed;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    z-index: 200;
    width: min(820px, calc(100% - 24px));
    margin: 0;
  }
  .desktop-auto-head {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 16px;
    margin-bottom: 14px;
  }
  .desktop-auto-mode-badge {
    display: inline-flex;
    align-items: center;
    min-height: 38px;
    padding: 0 16px;
    border-radius: 999px;
    border: 1px solid rgba(232, 212, 139, 0.18);
    background: rgba(232, 212, 139, 0.08);
    font-family: 'Oswald', sans-serif;
    font-size: 13px;
    font-weight: 700;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: #f2deab;
  }
  .desktop-auto-copy {
    max-width: 72ch;
  }
  .rounds-row { display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px; }
  .rounds-ctrl { display: flex; align-items: center; gap: 6px; }
  .rounds-ctrl button {
    width: 34px; height: 34px; border-radius: 10px;
    border: 1px solid rgba(232, 212, 139, 0.16);
    background: rgba(6, 12, 10, 0.96);
    color: #e7d8b0;
    font-size: 20px; font-weight: 700;
    display: flex; align-items: center; justify-content: center;
  }
  .rounds-ctrl span { font-size: 28px; width: 64px; text-align: center; font-weight: 700; font-family: 'Oswald', sans-serif; color: #fff0c1; }
  .btn-auto-toggle {
    width: 100%;
    padding: 14px 0;
    border-radius: 16px;
    border: 1px solid rgba(255,255,255,0.08);
    font-size: 20px;
    font-weight: 700;
    background: linear-gradient(180deg, #47b85a, #237139);
    color: #fff;
    font-family: 'Oswald', sans-serif;
    letter-spacing: 0.08em;
    text-transform: uppercase;
  }
  .btn-auto-toggle.stop { background: linear-gradient(180deg, #d84a41, #8d201d); }

  /* ABOUT */
  .about-panel { max-height: min(34vh, 320px); overflow-y: auto; }
  .about-text {
    font-size: 16px;
    line-height: 1.75;
    color: #ffffff;
    font-style: normal;
    font-family: 'Inter', sans-serif;
  }

  /* RULES */
  .rules-panel { max-height: min(34vh, 320px); overflow-y: auto; }
  .panel-title  { font-size: 25px; font-weight: 700; margin-bottom: 8px; }
  .felt-panel { max-height: min(34vh, 320px); overflow-y: auto; padding: 0; }
  .texture-picker {
    display: flex;
    flex-direction: column;
    gap: 0;
  }
  .texture-row {
    display: grid;
    grid-template-columns: 96px repeat(3, minmax(0, 1fr));
    gap: 0;
    align-items: stretch;
  }
  .texture-row + .texture-row {
    margin-top: -1px;
  }
  .texture-row-label {
    display: flex;
    align-items: center;
    justify-content: center;
    border: 1px solid rgba(232, 212, 139, 0.26);
    background: rgba(11, 28, 18, 0.98);
    color: #f2e8d0;
    font-family: 'Oswald', sans-serif;
    font-size: 20px;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    min-height: 58px;
    margin-right: -1px;
  }
  .btn-theme {
    border: 1px solid rgba(232, 212, 139, 0.26);
    border-radius: 0;
    color: #f2e8d0;
    font-family: 'Oswald', sans-serif;
    font-size: 13px;
    letter-spacing: 0.05em;
    text-transform: uppercase;
    min-height: 58px;
    padding: 5px;
    text-shadow: 0 1px 1px rgba(0,0,0,0.45);
  }
  .texture-row .btn-theme + .btn-theme {
    margin-left: -1px;
  }
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
    min-height: 32px;
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
  .texture-option.theme-velvet-green .texture-option-swatch {
    background:
      radial-gradient(circle at 50% 16%, rgba(127, 214, 174, 0.18), transparent 38%),
      radial-gradient(ellipse at 50% 33%, rgba(24, 110, 83, 0.26), rgba(9, 58, 40, 0.78) 70%, rgba(4, 31, 22, 0.92) 100%),
      url('/velvet-emerald-base.png');
  }
  .texture-option.theme-velvet-black .texture-option-swatch {
    background:
      radial-gradient(circle at 50% 16%, rgba(116, 126, 151, 0.12), transparent 38%),
      radial-gradient(ellipse at 50% 33%, rgba(36, 46, 66, 0.28), rgba(12, 16, 24, 0.82) 70%, rgba(6, 8, 12, 0.94) 100%),
      url('/velvet-black-base.png');
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
  .texture-option.theme-felt-blue .texture-option-swatch {
    background:
      radial-gradient(circle at 50% 16%, rgba(106, 145, 224, 0.18), transparent 38%),
      radial-gradient(ellipse at 50% 33%, rgba(24, 56, 112, 0.26), rgba(7, 20, 52, 0.78) 70%, rgba(4, 12, 32, 0.92) 100%),
      url('/felt-blue-base.png');
  }
  .texture-option.theme-felt-green .texture-option-swatch {
    background:
      radial-gradient(circle at 50% 16%, rgba(127, 214, 174, 0.18), transparent 38%),
      radial-gradient(ellipse at 50% 33%, rgba(24, 110, 83, 0.26), rgba(9, 58, 40, 0.78) 70%, rgba(4, 31, 22, 0.92) 100%),
      url('/felt-green-base.png');
  }
  .texture-option.theme-felt-black .texture-option-swatch {
    background:
      radial-gradient(circle at 50% 16%, rgba(116, 126, 151, 0.12), transparent 38%),
      radial-gradient(ellipse at 50% 33%, rgba(36, 46, 66, 0.28), rgba(12, 16, 24, 0.82) 70%, rgba(6, 8, 12, 0.94) 100%),
      url('/felt-black-base.png');
  }
  .rules-section { margin-bottom: 10px; font-size: 20px; }
  .rules-text   { margin-left: 8px; margin-top: 4px; font-size: 16px; line-height: 1.6; }
  .rules-text-sm { font-size: 14px; opacity: 0.75; }
  .rules-text.rtp { font-size: 14px; opacity: 0.7; }
  .payout-table { width: 100%; font-size: 15px; margin-top: 6px; border-collapse: collapse; }
  .payout-table td, .payout-table th { padding: 3px 6px; vertical-align: top; }
  .payout-table td:first-child { font-weight: 600; white-space: nowrap; opacity: 0.9; }
  .payout-table .rules-example { font-size: 13px; opacity: 0.65; padding-left: 10px; }
  .strategy-table th { font-size: 13px; opacity: 0.6; font-weight: 600; text-align: center; padding-bottom: 4px; border-bottom: 1px solid rgba(212,168,64,0.15); }
  .strategy-table td { text-align: center; font-size: 13px; }
  .strategy-table td:first-child { text-align: left; opacity: 0.7; font-weight: 500; }
  .strategy-table tr:nth-child(even) td { background: rgba(255,255,255,0.03); }

  .desktop-info-overlay-backdrop {
    position: fixed;
    inset: 0;
    z-index: 80;
    background:
      radial-gradient(circle at 50% 18%, rgba(212,168,64,0.16), transparent 34%),
      linear-gradient(180deg, rgba(2, 8, 6, 0.48) 0%, rgba(3, 8, 6, 0.82) 100%);
    backdrop-filter: blur(12px);
    padding: 26px;
  }
  .desktop-info-overlay {
    width: 100%;
    height: 100%;
    border-radius: 30px;
    border: 1px solid rgba(232, 212, 139, 0.18);
    background:
      linear-gradient(180deg, rgba(14, 29, 22, 0.97) 0%, rgba(8, 16, 13, 0.985) 100%);
    box-shadow:
      0 30px 80px rgba(0,0,0,0.46),
      inset 0 1px 0 rgba(255,255,255,0.05);
    overflow: hidden;
    display: flex;
    flex-direction: column;
  }
  .desktop-info-topbar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 18px;
    padding: 28px 30px 18px;
    border-bottom: 1px solid rgba(232, 212, 139, 0.12);
    background: linear-gradient(180deg, rgba(255,255,255,0.025), rgba(255,255,255,0));
  }
  .desktop-info-title {
    font-family: 'Bebas Neue', 'Oswald', sans-serif;
    font-size: 46px;
    letter-spacing: 0.05em;
    color: #f7eed6;
    line-height: 0.95;
  }
  .desktop-info-close {
    min-height: 42px;
    padding: 0 18px;
    border-radius: 999px;
    border: 1px solid rgba(232, 212, 139, 0.2);
    background: rgba(255,255,255,0.03);
    color: #f3e6c2;
    font-family: 'Oswald', sans-serif;
    font-size: 14px;
    font-weight: 700;
    letter-spacing: 0.1em;
    text-transform: uppercase;
  }
  .desktop-info-body {
    flex: 1;
    overflow: auto;
    padding: 24px 30px 30px;
  }
  .desktop-about-layout,
  .desktop-rules-layout {
    display: grid;
    gap: 18px;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    align-content: start;
  }
  .desktop-about-hero,
  .desktop-rules-summary {
    grid-column: 1 / -1;
  }
  .desktop-info-card {
    border-radius: 24px;
    border: 1px solid rgba(232, 212, 139, 0.12);
    background: rgba(255,255,255,0.025);
    box-shadow: inset 0 1px 0 rgba(255,255,255,0.04);
    padding: 22px 24px;
  }
  .desktop-info-section-title {
    font-family: 'Oswald', sans-serif;
    font-size: 20px;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: #efd58d;
    margin-bottom: 12px;
  }
  .desktop-about-logo {
    font-family: 'Bebas Neue', 'Oswald', sans-serif;
    font-size: clamp(58px, 7vw, 108px);
    line-height: 0.9;
    letter-spacing: 0.06em;
    color: #f7ead0;
    text-shadow: 0 2px 0 rgba(0,0,0,0.35), 0 0 24px rgba(212,168,64,0.12);
    margin-bottom: 14px;
  }
  .desktop-about-lead {
    max-width: 48rem;
    font-size: 20px;
    line-height: 1.6;
    color: rgba(242,232,208,0.82);
  }
  .desktop-rules-grid {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 12px;
  }
  .desktop-rule-stat {
    display: flex;
    flex-direction: column;
    gap: 6px;
    padding: 16px 18px;
    border-radius: 18px;
    background: rgba(4, 10, 8, 0.42);
    border: 1px solid rgba(232, 212, 139, 0.1);
  }
  .desktop-rule-stat span {
    font-family: 'Oswald', sans-serif;
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: rgba(242,232,208,0.6);
  }
  .desktop-rule-stat strong {
    font-family: 'Bebas Neue', 'Oswald', sans-serif;
    font-size: 30px;
    letter-spacing: 0.04em;
    color: #f7e5af;
    font-weight: 400;
  }

  .btn-reload {
    width: 100%; padding: 8px 0; border-radius: 5px;
    border: 1px solid #2a5a3a; background: transparent;
    color: #f2e8d0; font-size: 15px; margin-top: 4px;
  }

  /* DESKTOP — fit full screen, no scroll */
  @media (min-width: 768px) {
    .table-wrap  { height: 100vh; overflow: hidden; }
    .balance-row {
      position: absolute;
      top: 8px;
      left: 12px;
      right: 12px;
      z-index: 18;
      min-height: 0;
      padding: 0;
      border-bottom: none;
      background: transparent;
    }
    .felt        { overflow: hidden; margin-top: -44px; padding: 46px 18px 0; }

    .balance     { font-size: 24px; }
    .balance-row { min-height: 0; padding: 0; }
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
    .felt-logo-large { transform: scale(1.8); transform-origin: center; }
    .dealer-placeholder { height: 96px; }
    .hand-value         { font-size: 17px; padding: 2px 11px; }

    .card        { width: 124px; height: 200px; border-radius: 9px; }
    .card.small  { width: 124px; height: 200px; }
    .card.mid-deck-card { width: 111px; height: 179px; }
    .card.compact-deck-card { width: 97px; height: 158px; }

    .card-face .card-tl     { top: 5px; left: 6px; }
    .card-face .card-br     { bottom: 5px; right: 6px; }
    .card-face.small .card-tl { top: 5px; left: 6px; }
    .card-face.small .card-br { bottom: 5px; right: 6px; }

    .card-rank    { font-size: 19px; }
    .card-suit-sm { font-size: 15px; }
    .card-center  { font-size: 37px; }
    .card.small .card-rank    { font-size: 19px; }
    .card.small .card-suit-sm { font-size: 16px; }
    .card.small .card-center  { font-size: 39px; }

    .card-placeholder       { width: 124px; height: 200px; }
    .card-placeholder.small { width: 124px; height: 200px; }
    .card-placeholder.mid-deck-card { width: 111px; height: 179px; }
    .card-placeholder.compact-deck-card { width: 97px; height: 158px; }
    .card-placeholder,
    .card-placeholder.small {
      border-width: 2.5px;
      border-color: rgba(255,255,255,0.72);
      background: rgba(242,232,208,0.03);
    }

    .hands-row {
      min-height: 0;
      align-items: flex-start;
      justify-content: center;
      row-gap: 42px;
      width: fit-content;
      max-width: 100%;
      margin: 0 auto;
      align-content: flex-start;
      display: grid;
      gap: 0;
    }
    .hands-row.count-one { grid-template-columns: max-content; }
    /* Nudge cards+sidebets left 36px in 1-hand layout */
    .hands-row.count-one .sb-and-cards                     { margin-left: -36px; }
    .hands-row.count-one .cards-col.has-sb .sb-and-cards   { margin-left: -74px; } /* -38 - 36 */
    .hands-row.count-two { grid-template-columns: repeat(2, max-content); column-gap: 125px; margin-top: -10px; }
    .hands-row.count-three { grid-template-columns: repeat(3, max-content); column-gap: 125px; }
    /* Nudge cards+sidebets left 36px in 3-hand layout */
    .hands-row.count-three .sb-and-cards                        { margin-left: -36px; }
    .hands-row.count-three .cards-col.has-sb .sb-and-cards      { margin-left: -74px; } /* -38 - 36 */
    .hands-row.count-fourplus { grid-template-columns: repeat(3, max-content); column-gap: 125px; }
    .hands-row.three-up {
      padding-top: 25px;
    }
    .table-wrap.phase-play .hands-row.count-fourplus .hand-col:nth-child(n + 4) {
      transform: translateY(25px);
    }
    .table-wrap.phase-result .hands-row.count-fourplus .hand-col:nth-child(n + 4) {
      transform: translateY(20px);
    }

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
    .sb-box {
      width: 68px;
      min-height: 50px;
      border-width: 2.5px;
      border-color: rgba(255,255,255,0.72);
      background: rgba(242,232,208,0.03);
      color: rgba(242,232,208,0.45);
    }
    .sb-box-label { font-size: 10px; }
    .sb-box-label-213 { font-size: 11px; }
    .sb-box-amt   { font-size: 12px; }
    .sb-col       { gap: 5px; }
    .cards-area   { gap: 7px; }

    .ghost-wrap { padding-top: 29px; margin-left: 0; }
    .ghost-wrap.mid-ghost-wrap { margin-left: 0; }
    .ghost-wrap.compact-ghost-wrap { margin-left: 0; }
    .ghost-wrap.with-cards { padding-top: 29px; }
    .ghost {
      width: 124px;
      height: 200px;
      border-width: 2.5px;
      border-color: rgba(255,255,255,0.72);
      background: rgba(242,232,208,0.03);
      font-size: 30px;
      font-weight: 700;
      line-height: 1;
      color: rgba(255,255,255,0.84);
      text-shadow: none;
      opacity: 0.38;
    }
    .ghost.mid-ghost {
      width: 111px;
      height: 179px;
    }
    .ghost.compact-ghost {
      width: 97px;
      height: 158px;
    }
    .ghost:hover {
      opacity: 0.6;
      background: rgba(242,232,208,0.05);
    }
    .ghost-spacer { width: 124px; }
    .ghost-spacer.mid-ghost-spacer { width: 111px; }
    .ghost-spacer.compact-ghost-spacer { width: 97px; }
    .cards-col { min-width: 124px; }
    .cards-col.mid-cards-col { min-width: 111px; }
    .cards-col.compact-cards-col { min-width: 97px; }

    .divider-label,
    .action-wager-label {
      color: #d8b04f;
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

    /* Header — unified 20px (matched then –33%) */
    .balance { font-size: 52px; }
    .total-wager-sub { font-size: 20px; color: #ffffff; }
    .btn-options-toggle { font-size: 20px !important; min-height: 56px !important; padding: 10px 28px !important; color: #ffffff !important; }
    .btn-options-item { font-size: 26px !important; }
    .session-pill { font-size: 20px; }

    /* Action grid: collapsed 50% wide, centered */
    .action-grid {
      width: 50%;
      margin-left: auto;
      margin-right: auto;
    }
    .btn-action {
      font-size: 24px;
      text-align: center;
      border: 2px solid #000;
    }
  }

  /* ── MOBILE OPTIMIZATIONS (max 767px) ─────────────────────────────────── */
  @media (max-width: 767px) {
    /* Hands row takes natural height so felt can scroll past it */
    .hands-row { flex: 0 0 auto; gap: 10px; }
    .hands-row.multi { gap: 8px; }

    /* Mobile dock is its own bottom layout region, not an overlay on the felt */
    .bottom-dock {
      position: relative;
      bottom: auto;
      left: auto;
      right: auto;
      margin-top: 0;
      flex-shrink: 0;
      z-index: 10;
      background: linear-gradient(to bottom, rgba(7,26,14,0.18) 0%, #071a0e 16px);
      padding: 8px 8px calc(env(safe-area-inset-bottom, 0px) + 8px);
    }

    /* Felt owns only the scrollable playfield */
    .felt {
      padding: 2px 10px 0;
      padding-bottom: 8px;
      min-height: 0;
      flex: 1 1 auto;
    }

    /* Compact top bar */
    .balance      { font-size: 21px; }
    .balance-row  {
      min-height: 42px;
      padding: calc(env(safe-area-inset-top, 0px) + 6px) 10px 6px;
      gap: 8px;
      align-items: flex-start;
    }
    .utility-btns {
      gap: 4px;
      flex-wrap: wrap;
      flex: 1 1 auto;
      min-width: 0;
    }
    .btn-utility {
      font-size: 12px !important;
      padding: 4px 10px !important;
      min-height: 30px !important;
    }
    .balance-meta {
      flex: 0 0 auto;
      min-width: fit-content;
      padding-top: 2px;
    }
    .table-wrap.stacked-layout .balance-row {
      position: relative;
      min-height: 34px;
      padding: calc(env(safe-area-inset-top, 0px) + 4px) 10px 4px;
      align-items: flex-start;
    }
    .table-wrap.stacked-layout .utility-btns {
      position: absolute;
      top: calc(env(safe-area-inset-top, 0px) + 4px);
      left: 10px;
      right: 154px;
      display: flex;
      flex-wrap: nowrap;
      overflow-x: auto;
      overflow-y: hidden;
      -webkit-overflow-scrolling: touch;
      gap: 3px;
      padding-bottom: 1px;
      z-index: 2;
    }
    .table-wrap.stacked-layout .btn-utility {
      flex: 0 0 auto;
      font-size: 10px !important;
      padding: 3px 8px !important;
      min-height: 26px !important;
      letter-spacing: 0.03em;
    }
    .table-wrap.stacked-layout .session-meta,
    .table-wrap.stacked-layout .nav-result-msg {
      display: none;
    }
    .table-wrap.stacked-layout .balance-meta {
      margin-left: auto;
      padding-top: 0;
      padding-left: 96px;
      display: flex;
      align-items: center;
      gap: 6px;
      position: relative;
      z-index: 3;
    }
    .table-wrap.stacked-layout .balance {
      font-size: 19px;
    }
    .table-wrap.stacked-layout .rgs-status {
      margin-left: 0;
      font-size: 10px;
    }

    /* Compact felt logo + divider */
    .felt-logo-row  { padding: 0 0 4px; }
    .felt-logo      { width: 52px; height: 52px; }
    .felt-logo-large {
      width: min(48vw, 180px);
      height: auto;
      max-height: 140px;
      object-fit: contain;
    }

    /* Compact fact block */
    .fact-block { width: 140px; font-size: 11px; padding: 8px 10px; top: 8px; right: 8px; left: auto; }

    /* Compact dealer */
    .dealer-area        { min-height: 44px; }
    .dealer-placeholder { height: 18px; }
    .hand-value         { font-size: 18px; padding: 2px 12px; margin-bottom: 3px; }
    .table-wrap.stacked-layout.phase-play .felt-logo-right,
    .table-wrap.stacked-layout.phase-play .dealer-logo,
    .table-wrap.stacked-layout.phase-play .hand-value {
      display: none;
    }
    .table-wrap.stacked-layout.phase-play .felt {
      display: flex;
      flex-direction: column;
      justify-content: flex-start;
      gap: 0;
    }
    .table-wrap.stacked-layout.phase-play .table-playfield {
      display: flex;
      flex: 1 1 auto;
      flex-direction: column;
      min-height: 0;
    }
    .table-wrap.stacked-layout.phase-play .playfield-top {
      display: flex;
      flex: 0 0 auto;
      flex-direction: column;
    }
    .table-wrap.stacked-layout.phase-play .playfield-main {
      display: flex;
      flex: 1 1 auto;
      flex-direction: column;
      min-height: 0;
    }
    .table-wrap.stacked-layout.phase-play .dealer-area {
      min-height: 132px;
      flex: 0 0 132px;
      gap: 4px;
      margin-bottom: 12px;
      justify-content: flex-start;
    }
    .table-wrap.stacked-layout.phase-play .dealer-cards-col {
      transform: none;
      width: 100%;
      align-items: center;
    }
    .table-wrap.stacked-layout.phase-play .dealer-area .cards-row {
      overflow: visible;
      min-height: 0;
    }
    .table-wrap.stacked-layout.phase-play .mid-zone {
      display: none;
    }
    .table-wrap.stacked-layout.phase-play .hands-row {
      flex: 1 1 auto;
      align-items: flex-start;
      justify-content: center;
      margin-top: 10px;
      margin-bottom: 0;
      gap: 8px;
      min-height: 0;
    }
    .table-wrap.stacked-layout.phase-play .hands-row.multi {
      gap: 6px;
    }
    .table-wrap.stacked-layout.phase-play .hand-col {
      justify-content: flex-start;
    }
    .table-wrap.stacked-layout.phase-play .cards-area,
    .table-wrap.stacked-layout.phase-play .cards-col {
      min-height: 0;
    }
    .table-wrap.stacked-layout.phase-play .sb-col {
      gap: 4px;
    }
    .table-wrap.stacked-layout.phase-play .sb-box {
      width: 54px;
      min-height: 56px;
    }
    .table-wrap.stacked-layout.phase-play .sb-box-label {
      font-size: 8px;
    }
    .table-wrap.stacked-layout.phase-play .sb-box-label-213 {
      font-size: 9px;
    }
    .table-wrap.stacked-layout.phase-play .action-wager-label {
      margin-bottom: 1px;
      font-size: 12px;
    }
    .table-wrap.stacked-layout.phase-play .bet-bar {
      margin-top: 0;
    }
    .table-wrap.stacked-layout.phase-play .bottom-dock {
      padding-top: 20px;
      border-top: 1px solid rgba(212, 168, 64, 0.18);
      box-shadow: inset 0 14px 18px rgba(0, 0, 0, 0.16);
    }
    .table-wrap.stacked-layout.phase-play .center-deal-wrap {
      display: none;
    }
    .table-wrap.stacked-layout.phase-play .action-grid {
      margin-bottom: 0;
      padding: 4px;
    }
    .table-wrap.stacked-layout.phase-play .btn-action {
      padding: 15px 0;
      font-size: 16px;
    }

    /* Result */
    .msg-text           { font-size: 20px; }
    .msg-text.bad-beat  { font-size: 24px; }

    /* Action buttons — bigger touch target */
    .btn-action { padding: 16px 0; }

    /* Bet quick buttons — bigger touch target */
    .bet-quick-btn { min-height: 36px; min-width: 52px; }

    /* Felt menu compact */
    .felt-menu        { padding: 0; gap: 6px; }
    .felt-toggle-copy { font-size: 14px; }
    .bet-entry-btn    { font-size: 14px; min-width: 60px; min-height: 28px; }

    /* Hide divider on mobile — saves ~28px vertical */
    .divider-row { display: none; }
    .mid-zone {
      height: 0 !important;
      min-height: 0 !important;
      max-height: 0 !important;
    }
    .center-deal-wrap {
      padding: 0;
    }
    .center-deal-wrap .btn-deal {
      min-height: 54px;
      font-size: 20px;
      width: min(100%, calc(100% - 12px));
    }
    .action-area-fixed {
      margin-top: 2px;
    }
    .action-grid {
      margin-bottom: 0;
      padding: 3px;
      gap: 3px;
    }
    .action-wager-label {
      margin-bottom: 2px;
      font-size: 13px;
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
  }

  @media (max-width: 1024px) {
    .table-wrap.stacked-layout .table-playfield {
      display: flex;
      flex: 1 1 auto;
      flex-direction: column;
      min-height: 0;
    }
    .table-wrap.stacked-layout .playfield-top {
      display: flex;
      flex: 0 0 auto;
      flex-direction: column;
    }
    .table-wrap.stacked-layout .playfield-main {
      display: flex;
      flex: 1 1 auto;
      flex-direction: column;
      min-height: 0;
    }
    .table-wrap.stacked-layout.phase-play .dealer-area {
      width: 100%;
      justify-content: flex-start;
    }
    .table-wrap.stacked-layout.phase-play .hands-row {
      width: 100%;
      align-items: flex-start;
    }
  }

  .nav-result-msg {
    display: flex;
    align-items: center;
    justify-content: center;
  }
  .nav-result-text {
    font-family: 'Oswald', sans-serif;
    font-size: 22px;
    font-weight: 700;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    animation: fadeIn 0.3s ease;
  }
  .nav-result-text.win  { color: #2db870; }
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
  @keyframes glow {
    0%, 100% { box-shadow: 0 0 4px rgba(212,168,64,0.2); }
    50%       { box-shadow: 0 0 14px rgba(212,168,64,0.4); }
  }
</style>
