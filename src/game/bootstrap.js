import { get, writable } from "svelte/store";

import { replayMode, sessionQuery } from "./session.js";
import { authenticateSession, fetchReplayEvent } from "./rgsClient.js";
import { applyStakeBootstrap, hydrateStakeRound } from "./store.js";
import { canHydrateRoundState } from "./stakeRoundState.js";
import { buildBootstrapState } from "./sessionBootstrapModel.js";

export const sessionBootstrap = writable({
  status: "idle",
  authenticated: false,
  localMode: true,
  error: "",
  round: null,
  config: null,
  balance: null,
  resumeBlocked: false,
});

let bootstrapPromise = null;

export async function bootstrapStakeSession() {
  if (bootstrapPromise) return bootstrapPromise;

  bootstrapPromise = (async () => {
    const session = get(sessionQuery);
    const isReplay = get(replayMode);
    const hasReplayParams = Boolean(
      session.rgsUrl &&
      session.game &&
      session.version &&
      session.mode &&
      session.event
    );

    if ((!session.sessionID || !session.rgsUrl) && !(isReplay && hasReplayParams)) {
      sessionBootstrap.set(buildBootstrapState({ localMode: true }));
      return null;
    }

    sessionBootstrap.set({
      status: "loading",
      authenticated: false,
      localMode: false,
      error: "",
      round: null,
      config: null,
      balance: null,
      resumeBlocked: false,
    });

    try {
      if (isReplay && hasReplayParams) {
        const replay = await fetchReplayEvent(session);
        if (replay?.round?.state && canHydrateRoundState(replay.round.state)) {
          hydrateStakeRound({
            ...replay.round,
            active: false,
          });
        } else {
          sessionBootstrap.set({
            status: "error",
            authenticated: false,
            localMode: false,
            error: "Replay payload did not include a compatible round.state.",
            round: replay?.round ?? null,
            config: null,
            balance: null,
            resumeBlocked: false,
          });
          return replay;
        }
        sessionBootstrap.set({
          status: "replay-ready",
          authenticated: false,
          localMode: false,
          error: "",
          round: replay?.round ?? null,
          config: null,
          balance: null,
          resumeBlocked: false,
        });
        return replay;
      }
      const auth = await authenticateSession(session);
      applyStakeBootstrap(auth);
      if (auth?.round?.active && canHydrateRoundState(auth.round?.state)) {
        hydrateStakeRound(auth.round);
      }
      sessionBootstrap.set(buildBootstrapState({ auth }));
      return auth;
    } catch (error) {
      sessionBootstrap.set(buildBootstrapState({
        error: error instanceof Error ? error.message : String(error),
      }));
      return null;
    }
  })();

  return bootstrapPromise;
}

export function resetSessionBootstrapForTest() {
  bootstrapPromise = null;
  sessionBootstrap.set({
    status: "idle",
    authenticated: false,
    localMode: true,
    error: "",
    round: null,
    config: null,
    balance: null,
    resumeBlocked: false,
  });
}
