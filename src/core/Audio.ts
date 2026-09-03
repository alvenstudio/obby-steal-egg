import * as THREE from 'three';

/**
 * Procedural audio.
 *
 * Every sound is synthesised at runtime from oscillators and filtered noise —
 * no audio files ship with the game. That keeps the repository self-contained
 * and, more usefully, makes sounds parametric: one `chirp` covers a hundred
 * pets by varying pitch with rarity.
 *
 * This carries real gameplay weight in first person. In the third-person
 * original you can see a guardian closing from behind; here the only warning
 * is a panned, dopplered footfall, so positional audio is a mechanic rather
 * than decoration.
 */

export type SfxName =
  | 'step'
  | 'jump'
  | 'land'
  | 'landHard'
  | 'grab'
  | 'steal'
  | 'alarm'
  | 'caught'
  | 'hatch'
  | 'coin'
  | 'purchase'
  | 'denied'
  | 'unlock'
  | 'levelUp'
  | 'petHappy'
  | 'guardianRoar'
  | 'guardianStep'
  | 'whoosh'
  | 'checkpoint'
  | 'rebirth';

interface PlayOptions {
  /** World position; omit for a 2D sound. */
  position?: THREE.Vector3;
  volume?: number;
  /** Multiplies the sound's base frequency; 2 = one octave up. */
  pitch?: number;
  /** Max audible distance for positional sounds. */
  radius?: number;
}

export class AudioSystem {
  private ctx: AudioContext | null = null;
  private master: GainNode | null = null;
  private sfxBus: GainNode | null = null;
  private musicBus: GainNode | null = null;
  private noiseBuffer: AudioBuffer | null = null;
  private listenerPosition = new THREE.Vector3();
  private listenerForward = new THREE.Vector3(0, 0, -1);
  private musicNodes: Array<{ stop: () => void }> = [];
  private started = false;

  masterVolume = 0.7;
  sfxVolume = 0.85;
  musicVolume = 0.35;
  muted = false;

  /**
   * Browsers refuse to start audio without a gesture, so this is called from
   * the first click rather than at construction.
   */
  unlock(): void {
    if (this.started) return;
    const Ctor = window.AudioContext ?? (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
    if (!Ctor) return;
    this.ctx = new Ctor();
    this.master = this.ctx.createGain();
    this.master.gain.value = this.muted ? 0 : this.masterVolume;
    this.master.connect(this.ctx.destination);

    this.sfxBus = this.ctx.createGain();
    this.sfxBus.gain.value = this.sfxVolume;
    this.sfxBus.connect(this.master);

    this.musicBus = this.ctx.createGain();
    this.musicBus.gain.value = this.musicVolume;
    this.musicBus.connect(this.master);

    this.noiseBuffer = this.makeNoise(2.0);
    this.started = true;
    void this.ctx.resume();
  }

  setMuted(value: boolean): void {
    this.muted = value;
    if (this.master) this.master.gain.value = value ? 0 : this.masterVolume;
  }

  setMasterVolume(value: number): void {
    this.masterVolume = value;
    if (this.master && !this.muted) this.master.gain.value = value;
  }

  setSfxVolume(value: number): void {
    this.sfxVolume = value;
    if (this.sfxBus) this.sfxBus.gain.value = value;
  }

  setMusicVolume(value: number): void {
    this.musicVolume = value;
    if (this.musicBus) this.musicBus.gain.value = value;
  }

  /** Update the listener each frame so panning tracks the camera. */
  setListener(position: THREE.Vector3, forward: THREE.Vector3): void {
    this.listenerPosition.copy(position);
    this.listenerForward.copy(forward);
  }

  play(name: SfxName, options: PlayOptions = {}): void {
    if (!this.ctx || !this.sfxBus) return;
    const gainValue = this.spatialGain(options);
    if (gainValue <= 0.001) return;

    const pan = this.spatialPan(options);
    const destination = this.makeChannel(gainValue, pan);
    const now = this.ctx.currentTime;
    const pitch = options.pitch ?? 1;

    switch (name) {
      case 'step':
        this.noiseBurst(destination, now, 0.055, 900 * pitch, 0.5, 'bandpass');
        break;
      case 'guardianStep':
        this.noiseBurst(destination, now, 0.13, 240 * pitch, 0.9, 'lowpass');
        this.tone(destination, now, 'sine', 62 * pitch, 44 * pitch, 0.16, 0.55);
        break;
      case 'jump':
        this.tone(destination, now, 'sine', 260 * pitch, 520 * pitch, 0.13, 0.4);
        break;
      case 'land':
        this.noiseBurst(destination, now, 0.09, 520 * pitch, 0.7, 'lowpass');
        break;
      case 'landHard':
        this.noiseBurst(destination, now, 0.2, 320 * pitch, 1.0, 'lowpass');
        this.tone(destination, now, 'sine', 130, 55, 0.22, 0.6);
        break;
      case 'grab':
        this.tone(destination, now, 'triangle', 420 * pitch, 700 * pitch, 0.09, 0.35);
        break;
      case 'steal':
        // Rising arpeggio: the moment the egg leaves the nest should feel like
        // a commitment, not a pickup.
        this.arpeggio(destination, now, [440, 587, 740, 880].map((f) => f * pitch), 0.07, 0.32);
        break;
      case 'alarm':
        this.siren(destination, now, 660 * pitch, 880 * pitch, 0.85, 0.4);
        break;
      case 'caught':
        this.tone(destination, now, 'sawtooth', 320 * pitch, 70 * pitch, 0.45, 0.4);
        this.noiseBurst(destination, now, 0.3, 700, 0.9, 'lowpass');
        break;
      case 'hatch':
        this.noiseBurst(destination, now, 0.14, 2400, 0.4, 'highpass');
        this.arpeggio(destination, now + 0.05,
          [523, 659, 784, 1046, 1318].map((f) => f * pitch), 0.075, 0.3);
        break;
      case 'coin':
        this.arpeggio(destination, now, [988 * pitch, 1318 * pitch], 0.045, 0.22);
        break;
      case 'purchase':
        this.arpeggio(destination, now, [523, 784, 1046].map((f) => f * pitch), 0.06, 0.3);
        break;
      case 'denied':
        this.tone(destination, now, 'square', 200, 140, 0.16, 0.22);
        break;
      case 'unlock':
        this.arpeggio(destination, now,
          [392, 523, 659, 784, 1046].map((f) => f * pitch), 0.09, 0.32);
        break;
      case 'levelUp':
        this.arpeggio(destination, now,
          [523, 659, 784, 1046, 1318, 1568].map((f) => f * pitch), 0.07, 0.3);
        break;
      case 'petHappy':
        this.chirp(destination, now, 700 * pitch, 1250 * pitch, 0.11);
        break;
      case 'guardianRoar':
        this.roar(destination, now, 110 * pitch);
        break;
      case 'whoosh':
        this.noiseBurst(destination, now, 0.22, 1400 * pitch, 0.55, 'bandpass');
        break;
      case 'checkpoint':
        this.arpeggio(destination, now, [659, 880].map((f) => f * pitch), 0.1, 0.28);
        break;
      case 'rebirth':
        this.arpeggio(destination, now,
          [261, 329, 392, 523, 659, 784, 1046].map((f) => f * pitch), 0.11, 0.34);
        this.noiseBurst(destination, now, 0.6, 3000, 0.3, 'highpass');
        break;
    }
  }

  /**
   * A slow ambient pad per biome. Not a melody — a drone plus a sparse bell,
   * which stays out of the way over a long grinding session.
   */
  startAmbience(rootHz: number, brightness = 1): void {
    this.stopAmbience();
    if (!this.ctx || !this.musicBus) return;
    const ctx = this.ctx;
    const now = ctx.currentTime;

    for (const [index, ratio] of [1, 1.5, 2, 3].entries()) {
      const osc = ctx.createOscillator();
      osc.type = index % 2 === 0 ? 'sine' : 'triangle';
      osc.frequency.value = rootHz * ratio;
      const gain = ctx.createGain();
      gain.gain.value = 0;
      gain.gain.linearRampToValueAtTime(0.09 / (index + 1), now + 2.5);

      const lfo = ctx.createOscillator();
      lfo.frequency.value = 0.05 + index * 0.017;
      const lfoGain = ctx.createGain();
      lfoGain.gain.value = rootHz * 0.006 * ratio;
      lfo.connect(lfoGain).connect(osc.frequency);

      const filter = ctx.createBiquadFilter();
      filter.type = 'lowpass';
      filter.frequency.value = 400 * brightness + index * 220;

      osc.connect(gain).connect(filter).connect(this.musicBus);
      osc.start();
      lfo.start();
      this.musicNodes.push({
        stop: () => {
          gain.gain.cancelScheduledValues(ctx.currentTime);
          gain.gain.linearRampToValueAtTime(0, ctx.currentTime + 1.2);
          osc.stop(ctx.currentTime + 1.3);
          lfo.stop(ctx.currentTime + 1.3);
        },
      });
    }
  }

  stopAmbience(): void {
    for (const node of this.musicNodes) node.stop();
    this.musicNodes = [];
  }

  // ---- synthesis primitives ------------------------------------------------

  private makeChannel(volume: number, pan: number): AudioNode {
    const ctx = this.ctx!;
    const gain = ctx.createGain();
    gain.gain.value = volume;
    const panner = ctx.createStereoPanner();
    panner.pan.value = pan;
    gain.connect(panner).connect(this.sfxBus!);
    return gain;
  }

  private spatialGain(options: PlayOptions): number {
    const base = options.volume ?? 1;
    if (!options.position) return base;
    const radius = options.radius ?? 42;
    const distance = this.listenerPosition.distanceTo(options.position);
    if (distance >= radius) return 0;
    // Inverse-square feels too abrupt for gameplay cues; this keeps a guardian
    // audible long enough to react to.
    const falloff = 1 - distance / radius;
    return base * falloff * falloff;
  }

  private spatialPan(options: PlayOptions): number {
    if (!options.position) return 0;
    const toSound = options.position.clone().sub(this.listenerPosition);
    toSound.y = 0;
    if (toSound.lengthSq() < 1e-6) return 0;
    toSound.normalize();
    const right = new THREE.Vector3(-this.listenerForward.z, 0, this.listenerForward.x).normalize();
    return THREE.MathUtils.clamp(toSound.dot(right), -1, 1) * 0.85;
  }

  private makeNoise(seconds: number): AudioBuffer {
    const ctx = this.ctx!;
    const length = Math.floor(ctx.sampleRate * seconds);
    const buffer = ctx.createBuffer(1, length, ctx.sampleRate);
    const data = buffer.getChannelData(0);
    for (let i = 0; i < length; i++) data[i] = Math.random() * 2 - 1;
    return buffer;
  }

  private tone(
    destination: AudioNode,
    at: number,
    type: OscillatorType,
    from: number,
    to: number,
    duration: number,
    peak: number,
  ): void {
    const ctx = this.ctx!;
    const osc = ctx.createOscillator();
    osc.type = type;
    osc.frequency.setValueAtTime(from, at);
    osc.frequency.exponentialRampToValueAtTime(Math.max(1, to), at + duration);
    const gain = ctx.createGain();
    gain.gain.setValueAtTime(0, at);
    gain.gain.linearRampToValueAtTime(peak, at + duration * 0.12);
    gain.gain.exponentialRampToValueAtTime(0.0001, at + duration);
    osc.connect(gain).connect(destination);
    osc.start(at);
    osc.stop(at + duration + 0.02);
  }

  private chirp(destination: AudioNode, at: number, from: number, to: number, duration: number): void {
    this.tone(destination, at, 'sine', from, to, duration, 0.28);
    this.tone(destination, at + duration * 0.5, 'sine', to, from * 1.2, duration * 0.7, 0.16);
  }

  private arpeggio(
    destination: AudioNode,
    at: number,
    notes: number[],
    spacing: number,
    peak: number,
  ): void {
    notes.forEach((frequency, index) => {
      this.tone(destination, at + index * spacing, 'triangle',
        frequency, frequency * 1.01, spacing * 2.4, peak / (1 + index * 0.12));
    });
  }

  private noiseBurst(
    destination: AudioNode,
    at: number,
    duration: number,
    cutoff: number,
    peak: number,
    filterType: BiquadFilterType,
  ): void {
    const ctx = this.ctx!;
    if (!this.noiseBuffer) return;
    const source = ctx.createBufferSource();
    source.buffer = this.noiseBuffer;
    source.loop = true;
    const filter = ctx.createBiquadFilter();
    filter.type = filterType;
    filter.frequency.value = cutoff;
    filter.Q.value = filterType === 'bandpass' ? 2.4 : 0.9;
    const gain = ctx.createGain();
    gain.gain.setValueAtTime(0, at);
    gain.gain.linearRampToValueAtTime(peak * 0.35, at + 0.008);
    gain.gain.exponentialRampToValueAtTime(0.0001, at + duration);
    source.connect(filter).connect(gain).connect(destination);
    source.start(at);
    source.stop(at + duration + 0.02);
  }

  private siren(
    destination: AudioNode,
    at: number,
    low: number,
    high: number,
    duration: number,
    peak: number,
  ): void {
    const ctx = this.ctx!;
    const osc = ctx.createOscillator();
    osc.type = 'square';
    const gain = ctx.createGain();
    gain.gain.setValueAtTime(0, at);
    gain.gain.linearRampToValueAtTime(peak * 0.3, at + 0.04);
    gain.gain.setValueAtTime(peak * 0.3, at + duration - 0.1);
    gain.gain.exponentialRampToValueAtTime(0.0001, at + duration);
    const steps = 4;
    for (let i = 0; i <= steps; i++) {
      const t = at + (duration * i) / steps;
      osc.frequency.setValueAtTime(i % 2 === 0 ? low : high, t);
    }
    osc.connect(gain).connect(destination);
    osc.start(at);
    osc.stop(at + duration + 0.02);
  }

  private roar(destination: AudioNode, at: number, root: number): void {
    const ctx = this.ctx!;
    const duration = 0.85;
    for (const [index, ratio] of [1, 1.5, 2.02].entries()) {
      const osc = ctx.createOscillator();
      osc.type = index === 0 ? 'sawtooth' : 'square';
      osc.frequency.setValueAtTime(root * ratio * 1.25, at);
      osc.frequency.exponentialRampToValueAtTime(root * ratio * 0.7, at + duration);
      const gain = ctx.createGain();
      gain.gain.setValueAtTime(0, at);
      gain.gain.linearRampToValueAtTime(0.22 / (index + 1), at + 0.1);
      gain.gain.exponentialRampToValueAtTime(0.0001, at + duration);
      const filter = ctx.createBiquadFilter();
      filter.type = 'lowpass';
      filter.frequency.setValueAtTime(1400, at);
      filter.frequency.exponentialRampToValueAtTime(340, at + duration);
      osc.connect(gain).connect(filter).connect(destination);
      osc.start(at);
      osc.stop(at + duration + 0.05);
    }
    this.noiseBurst(destination, at, duration * 0.8, 500, 0.5, 'lowpass');
  }
}
