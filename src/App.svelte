<script>
  import { innerWidth } from "svelte/reactivity/window";
  import GameTable from "./ui/GameTable.svelte";
  import DesktopCanonicalApp from "./ui/desktop-canonical/App.svelte";

  $: isDesktop = (innerWidth.current ?? 0) >= 768;
</script>

{#if isDesktop}
  <DesktopCanonicalApp />
{:else}
  <GameTable />
{/if}
