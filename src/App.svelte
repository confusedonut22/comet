<script>
  import GameTable from "./ui/GameTable.svelte";
  import DesktopCanonicalApp from "./ui/desktop-canonical/App.svelte";

  let viewportWidth = 0;
  let forceMobilePortraitShell = false;

  function detectPortraitLockedMobile() {
    if (typeof window === "undefined" || typeof navigator === "undefined") return false;
    const ua = navigator.userAgent || "";
    const isMobileUa = /Android|iPhone|iPod|Mobile/i.test(ua);
    const hasCoarsePointer = window.matchMedia?.("(pointer: coarse)")?.matches ?? navigator.maxTouchPoints > 0;
    return isMobileUa && hasCoarsePointer;
  }

  $: {
    viewportWidth;
    forceMobilePortraitShell = detectPortraitLockedMobile();
  }
  $: isDesktop = viewportWidth >= 768 && !forceMobilePortraitShell;
</script>

<svelte:window bind:innerWidth={viewportWidth} />

{#if isDesktop}
  <DesktopCanonicalApp />
{:else}
  <GameTable />
{/if}
