<script>
  import BlackjackDesktopLayout from "./lib/layouts/BlackjackDesktopLayout.svelte";
  import { initializeLayoutContext } from "./game/layout.svelte.js";

  initializeLayoutContext();
</script>

<BlackjackDesktopLayout />
