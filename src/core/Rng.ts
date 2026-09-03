/**
 * Deterministic RNG. Every piece of world generation goes through a seeded
 * stream so a given save always rebuilds the same map, and so a bug in level
 * layout can be reproduced from the seed alone.
 */
export class Rng {
  private state: number;

  constructor(seed: number | string = 1) {
    this.state = typeof seed === 'string' ? Rng.hash(seed) : seed >>> 0;
    if (this.state === 0) this.state = 0x9e3779b9;
  }

  /** FNV-1a — cheap, and good enough to turn a biome name into a seed. */
  static hash(text: string): number {
    let h = 0x811c9dc5;
    for (let i = 0; i < text.length; i++) {
      h ^= text.charCodeAt(i);
      h = Math.imul(h, 0x01000193);
    }
    return h >>> 0;
  }

  /** xorshift32 — fast, no allocation, plenty of quality for level layout. */
  next(): number {
    let x = this.state;
    x ^= x << 13;
    x ^= x >>> 17;
    x ^= x << 5;
    this.state = x >>> 0;
    return this.state / 0x100000000;
  }

  float(min = 0, max = 1): number {
    return min + this.next() * (max - min);
  }

  int(min: number, max: number): number {
    return Math.floor(this.float(min, max + 1));
  }

  bool(chance = 0.5): boolean {
    return this.next() < chance;
  }

  pick<T>(items: readonly T[]): T {
    return items[Math.floor(this.next() * items.length)];
  }

  /** Weighted pick. `weights[i]` need not sum to anything in particular. */
  pickWeighted<T>(items: readonly T[], weights: readonly number[]): T {
    let total = 0;
    for (const w of weights) total += w;
    let roll = this.next() * total;
    for (let i = 0; i < items.length; i++) {
      roll -= weights[i];
      if (roll <= 0) return items[i];
    }
    return items[items.length - 1];
  }

  /** Fisher-Yates, in place. */
  shuffle<T>(items: T[]): T[] {
    for (let i = items.length - 1; i > 0; i--) {
      const j = Math.floor(this.next() * (i + 1));
      [items[i], items[j]] = [items[j], items[i]];
    }
    return items;
  }

  /** A fresh independent stream — lets one subsystem not perturb another. */
  fork(tag: string): Rng {
    return new Rng((this.state ^ Rng.hash(tag)) >>> 0);
  }
}

export const globalRng = new Rng('obby-steal-egg');
