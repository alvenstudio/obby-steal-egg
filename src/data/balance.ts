/**
 * The economy's shape, in one file.
 *
 * Every curve here is a closed-form function rather than a hand-written table,
 * so the whole game can be re-tuned by moving a handful of constants and the
 * balance tests in tests/ can assert the *relationships* (a biome must always
 * cost roughly N seconds of the previous biome's income) rather than magic
 * numbers that rot the moment anything changes.
 */

/** Income of a Common pet in biome `index`, per second, before multipliers. */
export const BIOME_INCOME_STEP = 8;
export const BASE_INCOME = 1;

export function biomeBaseIncome(index: number): number {
  return BASE_INCOME * Math.pow(BIOME_INCOME_STEP, index);
}

/**
 * How long a player should expect to grind before affording the next biome,
 * assuming a reasonably filled base. Kept explicit because it is the single
 * most important pacing number in the game.
 */
export const SECONDS_TO_NEXT_BIOME = 105;

/** Pets a mid-progress player has placed, and their average multiplier. */
const ASSUMED_SLOTS = 8;
const ASSUMED_AVERAGE_MULTIPLIER = 3.6;

export function biomeUnlockCost(index: number): number {
  if (index <= 0) return 0;
  const previousIncome =
    biomeBaseIncome(index - 1) * ASSUMED_SLOTS * ASSUMED_AVERAGE_MULTIPLIER;
  const raw = previousIncome * SECONDS_TO_NEXT_BIOME;
  return roundNice(raw);
}

/** Round to two significant digits so shop prices read as designed, not derived. */
export function roundNice(value: number): number {
  if (value < 100) return Math.round(value);
  const magnitude = Math.pow(10, Math.floor(Math.log10(value)) - 1);
  return Math.round(value / magnitude) * magnitude;
}

// ---------------------------------------------------------------------------
// upgrade cost curves
// ---------------------------------------------------------------------------

export interface CurveSpec {
  base: number;
  growth: number;
}

/** Cost of taking an upgrade from `level` to `level + 1`. */
export function upgradeCost(spec: CurveSpec, level: number): number {
  return roundNice(spec.base * Math.pow(spec.growth, level));
}

/** Total spent to reach `level` from zero. */
export function upgradeTotalCost(spec: CurveSpec, level: number): number {
  let total = 0;
  for (let i = 0; i < level; i++) total += upgradeCost(spec, i);
  return total;
}

// ---------------------------------------------------------------------------
// hatching
// ---------------------------------------------------------------------------

/** Base seconds to hatch an egg from biome `index`. */
export function hatchSeconds(biomeIndex: number, hatchSpeedLevel: number): number {
  const base = 12 + biomeIndex * 4;
  // Diminishing returns: level 10 is a little over 2x faster, not 10x.
  return base / (1 + hatchSpeedLevel * 0.16);
}

// ---------------------------------------------------------------------------
// stealing
// ---------------------------------------------------------------------------

/** Seconds the player must hold the steal prompt at a biome's nest. */
export function stealDuration(biomeIndex: number): number {
  return 1.4 + biomeIndex * 0.28;
}

/** Money lost when a guardian catches you carrying an egg. */
export const CATCH_MONEY_PENALTY = 0.12;
/** Seconds the player is stunned after a catch. */
export const CATCH_STUN_SECONDS = 2.6;

// ---------------------------------------------------------------------------
// rebirth
// ---------------------------------------------------------------------------

/** Money required for rebirth number `n` (1-indexed). */
export function rebirthCost(n: number): number {
  return roundNice(2.5e6 * Math.pow(14, n - 1));
}

/** Permanent income multiplier after `n` rebirths. */
export function rebirthMultiplier(n: number): number {
  return 1 + n * 0.65 + Math.max(0, n - 5) * 0.35;
}

/** Permanent luck granted by rebirths, added to upgrade luck. */
export function rebirthLuck(n: number): number {
  return n * 0.22;
}

// ---------------------------------------------------------------------------
// offline earnings
// ---------------------------------------------------------------------------

/** Fraction of full income earned while the tab is closed. */
export const OFFLINE_RATE = 0.35;
/** Cap on offline accumulation, seconds (4 hours). */
export const OFFLINE_CAP_SECONDS = 4 * 3600;

export function offlineEarnings(incomePerSecond: number, secondsAway: number): number {
  const capped = Math.min(secondsAway, OFFLINE_CAP_SECONDS);
  return incomePerSecond * capped * OFFLINE_RATE;
}

// ---------------------------------------------------------------------------
// number formatting
// ---------------------------------------------------------------------------

const SUFFIXES = [
  '', 'K', 'M', 'B', 'T', 'Qa', 'Qi', 'Sx', 'Sp', 'Oc', 'No', 'Dc',
  'UDc', 'DDc', 'TDc', 'QaDc', 'QiDc', 'SxDc', 'SpDc', 'OcDc', 'NoDc', 'Vg',
];

/** "1.24M" — the only number format the UI ever shows. */
export function formatMoney(value: number): string {
  if (!Number.isFinite(value)) return '∞';
  const sign = value < 0 ? '-' : '';
  let n = Math.abs(value);
  if (n < 1000) {
    return sign + (n < 10 && n % 1 !== 0 ? n.toFixed(1) : Math.floor(n).toString());
  }
  let tier = 0;
  while (n >= 1000 && tier < SUFFIXES.length - 1) {
    n /= 1000;
    tier++;
  }
  const digits = n < 10 ? 2 : n < 100 ? 1 : 0;
  return sign + n.toFixed(digits) + SUFFIXES[tier];
}

/** "1.2K/s" */
export function formatRate(value: number): string {
  return formatMoney(value) + '/s';
}

export function formatDuration(seconds: number): string {
  if (seconds < 60) return Math.ceil(seconds) + 's';
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return minutes + 'm ' + Math.floor(seconds % 60) + 's';
  const hours = Math.floor(minutes / 60);
  return hours + 'h ' + (minutes % 60) + 'm';
}
