// ChadJack — Web Audio API synthesized sound effects
// All sounds synthesized — no external files required.

let ctx = null;
let _muted = false;

export function isMuted() { return _muted; }
export function setMuted(value) { _muted = Boolean(value); }
export function toggleMute() { _muted = !_muted; return _muted; }

function getCtx() {
  if (!ctx) ctx = new (window.AudioContext || window.webkitAudioContext)();
  if (ctx.state === 'suspended') ctx.resume();
  return ctx;
}

function noise(ac, dur, freq, Q, gainVal, decay = 20) {
  const buf = ac.createBuffer(1, Math.ceil(ac.sampleRate * dur), ac.sampleRate);
  const d = buf.getChannelData(0);
  for (let i = 0; i < d.length; i++)
    d[i] = (Math.random() * 2 - 1) * Math.exp(-(i / d.length) * decay);
  const src = ac.createBufferSource(); src.buffer = buf;
  const filt = ac.createBiquadFilter(); filt.type = 'bandpass'; filt.frequency.value = freq; filt.Q.value = Q;
  const gain = ac.createGain(); gain.gain.value = gainVal;
  src.connect(filt); filt.connect(gain); gain.connect(ac.destination);
  src.start(); return src;
}

function tone(ac, freq, dur, gainVal, type = 'sine', fadeIn = 0.005, fadeOut = 0.08) {
  const osc = ac.createOscillator();
  osc.type = type; osc.frequency.value = freq;
  const gain = ac.createGain();
  const now = ac.currentTime;
  gain.gain.setValueAtTime(0, now);
  gain.gain.linearRampToValueAtTime(gainVal, now + fadeIn);
  gain.gain.setValueAtTime(gainVal, now + dur - fadeOut);
  gain.gain.linearRampToValueAtTime(0, now + dur);
  osc.connect(gain); gain.connect(ac.destination);
  osc.start(now); osc.stop(now + dur);
  return osc;
}

function chord(ac, freqs, dur, gainVal, type = 'sine') {
  freqs.forEach(f => tone(ac, f, dur, gainVal / freqs.length, type));
}

// ── Card snap: crisp filtered noise burst ──
export function playCardSnap() {
  if (_muted) return;
  try {
    const ac = getCtx();
    noise(ac, 0.07, 2400, 1.2, 0.35, 35);
    // subtle body thud underneath
    tone(ac, 180, 0.06, 0.12, 'sine');
  } catch (_) {}
}

// ── Deal swoosh: descending noise sweep ──
export function playDealSwoosh() {
  if (_muted) return;
  try {
    const ac = getCtx();
    const buf = ac.createBuffer(1, Math.ceil(ac.sampleRate * 0.18), ac.sampleRate);
    const d = buf.getChannelData(0);
    for (let i = 0; i < d.length; i++) {
      const t = i / d.length;
      d[i] = (Math.random() * 2 - 1) * Math.exp(-t * 12) * (1 - t) * 0.28;
    }
    const src = ac.createBufferSource(); src.buffer = buf;
    const filt = ac.createBiquadFilter(); filt.type = 'lowpass';
    const now = ac.currentTime;
    filt.frequency.setValueAtTime(4000, now);
    filt.frequency.exponentialRampToValueAtTime(800, now + 0.18);
    const gain = ac.createGain(); gain.gain.value = 0.55;
    src.connect(filt); filt.connect(gain); gain.connect(ac.destination);
    src.start();
  } catch (_) {}
}

// ── Chip place: plastic click ──
export function playChipPlace() {
  if (_muted) return;
  try {
    const ac = getCtx();
    noise(ac, 0.04, 3200, 2.5, 0.28, 50);
    tone(ac, 320, 0.04, 0.08, 'sine');
  } catch (_) {}
}

// ── Stand: soft thud / decision thump ──
export function playStand() {
  if (_muted) return;
  try {
    const ac = getCtx();
    tone(ac, 220, 0.12, 0.18, 'sine');
    noise(ac, 0.05, 400, 0.8, 0.12, 30);
  } catch (_) {}
}

// ── Double down: two quick snaps ──
export function playDoubleDown() {
  if (_muted) return;
  try {
    const ac = getCtx();
    noise(ac, 0.06, 2600, 1.4, 0.32, 40);
    setTimeout(() => { try { noise(getCtx(), 0.06, 2600, 1.4, 0.36, 40); } catch (_) {} }, 90);
  } catch (_) {}
}

// ── Split: two separate snaps with slight pitch difference ──
export function playSplit() {
  if (_muted) return;
  try {
    const ac = getCtx();
    noise(ac, 0.07, 2200, 1.2, 0.3, 35);
    setTimeout(() => { try { noise(getCtx(), 0.07, 2600, 1.2, 0.3, 35); } catch (_) {} }, 110);
  } catch (_) {}
}

// ── Bust: descending thud ──
export function playBust() {
  if (_muted) return;
  try {
    const ac = getCtx();
    const now = ac.currentTime;
    const osc = ac.createOscillator(); osc.type = 'sawtooth';
    osc.frequency.setValueAtTime(300, now);
    osc.frequency.exponentialRampToValueAtTime(60, now + 0.35);
    const gain = ac.createGain(); gain.gain.setValueAtTime(0.22, now);
    gain.gain.linearRampToValueAtTime(0, now + 0.38);
    osc.connect(gain); gain.connect(ac.destination);
    osc.start(now); osc.stop(now + 0.4);
    noise(ac, 0.15, 250, 0.6, 0.14, 10);
  } catch (_) {}
}

// ── Win: bright ascending chime ──
export function playWin() {
  if (_muted) return;
  try {
    const ac = getCtx();
    // Ascending two-note chime
    tone(ac, 523, 0.18, 0.18, 'sine');          // C5
    setTimeout(() => { try { tone(getCtx(), 784, 0.22, 0.2, 'sine'); } catch (_) {} }, 100); // G5
    // sparkle overtone
    setTimeout(() => { try { tone(getCtx(), 1047, 0.14, 0.1, 'sine'); } catch (_) {} }, 180); // C6
  } catch (_) {}
}

// ── Blackjack: triumphant three-note fanfare ──
export function playBlackjack() {
  if (_muted) return;
  try {
    const ac = getCtx();
    tone(ac, 523, 0.18, 0.22, 'triangle');       // C5
    setTimeout(() => { try { tone(getCtx(), 659, 0.18, 0.22, 'triangle'); } catch (_) {} }, 110); // E5
    setTimeout(() => { try { tone(getCtx(), 784, 0.28, 0.24, 'triangle'); } catch (_) {} }, 220); // G5
    // shimmer layer
    setTimeout(() => { try { chord(getCtx(), [1047, 1319], 0.25, 0.18, 'sine'); } catch (_) {} }, 320);
    // coin-drop noise
    setTimeout(() => { try { noise(getCtx(), 0.18, 3500, 2.0, 0.22, 18); } catch (_) {} }, 320);
  } catch (_) {}
}

// ── Lose: low descending two-note ──
export function playLose() {
  if (_muted) return;
  try {
    const ac = getCtx();
    tone(ac, 330, 0.18, 0.16, 'sine');           // E4
    setTimeout(() => { try { tone(getCtx(), 247, 0.25, 0.16, 'sine'); } catch (_) {} }, 130); // B3
  } catch (_) {}
}

// ── Push: neutral single mid tone ──
export function playPush() {
  if (_muted) return;
  try {
    const ac = getCtx();
    tone(ac, 440, 0.14, 0.12, 'sine');           // A4
  } catch (_) {}
}

// ── Insurance taken: two ascending tones ──
export function playInsurance() {
  if (_muted) return;
  try {
    const ac = getCtx();
    tone(ac, 392, 0.12, 0.14, 'sine');           // G4
    setTimeout(() => { try { tone(getCtx(), 494, 0.14, 0.14, 'sine'); } catch (_) {} }, 90); // B4
  } catch (_) {}
}
