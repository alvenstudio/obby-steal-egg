/**
 * Speed, treadmills, trails and rebirth -- the progression spine.
 *
 * The reference game's best idea is that ONE stat gates everything. Speed is
 * both the key to the next biome and the only thing that gets you out of it
 * alive, so "can I unlock this" and "can I survive this" are the same question
 * and the player is never handed content they cannot actually play.
 *
 * Money never buys Speed directly. Money buys the *rate* at which training
 * produces Speed, which keeps the two currencies from collapsing into one and
 * gives the pet economy a job: fund the treadmill so the treadmill funds the
 * next biome so the next biome funds better pets.
 */

import { formatMoney, roundNice } from './balance';

// ---------------------------------------------------------------------------
// speed -> movement
// ---------------------------------------------------------------------------

/**
 * Speed climbs to seven billion, so world movement has to be logarithmic in it
 * or the last biome would need a map a thousand kilometres wide. A log curve
 * also keeps every upgrade feeling like something: the same +1 tier is worth
 * the same *fraction* of your speed at every point on the curve.
 */
export const SPEED_LOG_FACTOR = 0.26;

export function speedMultiplier(speedStat: number): number {
  return 1 + SPEED_LOG_FACTOR * Math.log10(1 + Math.max(0, speedStat));
}

/** Metres per second the player actually runs at, sprinting. */
export function sprintSpeed(speedStat: number, baseSprint: number): number {
  return baseSprint * speedMultiplier(speedStat);
}

// ---------------------------------------------------------------------------
// treadmill: converts time-on-belt into Speed
// ---------------------------------------------------------------------------

export interface TreadmillTier {
  tier: number;
  name: string;
  /** Multiplier on the base training rate. */
  rate: number;
  cost: number;
  color: string;
}

const TREADMILL_RATES = [1, 2.5, 7, 20, 55, 150, 420, 1200, 3400, 9500];
const TREADMILL_NAMES = [
  'Rusty Belt', 'Jogger', 'Sprinter', 'Turbo Belt', 'Piston Runner',
  'Hyperbelt', 'Overdrive', 'Warp Belt', 'Singularity', 'Impossible Machine',
];
const TREADMILL_COLORS = [
  '#8d97a3', '#6fd28a', '#5aa9f0', '#b072f2', '#ffb443',
  '#ff5f7e', '#5ce1ff', '#8affd6', '#a06bff', '#ffd447',
];
/**
 * Costs are set so each tier is affordable roughly when the biome it unlocks
 * has been farmed for a couple of minutes. The balance test in tests/ asserts
 * this relationship holds rather than pinning the literal numbers.
 */
const TREADMILL_COSTS = [
  0, 1_200, 22_000, 400_000, 7_500_000,
  140_000_000, 2_600_000_000, 48_000_000_000, 900_000_000_000, 17_000_000_000_000,
];

export const TREADMILLS: TreadmillTier[] = TREADMILL_RATES.map((rate, index) => ({
  tier: index,
  name: TREADMILL_NAMES[index],
  rate,
  cost: TREADMILL_COSTS[index],
  color: TREADMILL_COLORS[index],
}));

/** Speed gained per second of running on the belt. */
export const BASE_TRAINING_RATE = 25;

export function trainingRate(treadmillTier: number, trailTier: number): number {
  const treadmill = TREADMILLS[Math.min(treadmillTier, TREADMILLS.length - 1)];
  const trail = TRAILS[Math.min(trailTier, TRAILS.length - 1)];
  return BASE_TRAINING_RATE * treadmill.rate * trail.multiplier;
}

// ---------------------------------------------------------------------------
// trails: multiply training, and leave a visible streak behind the player
// ---------------------------------------------------------------------------

export interface TrailTier {
  tier: number;
  name: string;
  multiplier: number;
  cost: number;
  color: string;
  /** Emissive strength of the ribbon left behind while sprinting. */
  glow: number;
}

const TRAIL_SPECS: Array<[string, number, number, string, number]> = [
  ['No Trail', 1, 0, '#ffffff', 0],
  ['Dust', 1.6, 4_000, '#d8c9a4', 0.2],
  ['Leaf', 2.6, 70_000, '#6fd28a', 0.4],
  ['Bubble', 4.2, 1_300_000, '#5aa9f0', 0.6],
  ['Ember', 7, 24_000_000, '#ff6a1f', 1.2],
  ['Frost', 11, 450_000_000, '#a8e8ff', 1.4],
  ['Storm', 18, 8_400_000_000, '#b072f2', 1.8],
  ['Starlight', 30, 160_000_000_000, '#5ce1ff', 2.2],
  ['Eclipse', 50, 3_000_000_000_000, '#2a1140', 2.6],
  ['Ascension', 85, 56_000_000_000_000, '#ffd447', 3.2],
];

export const TRAILS: TrailTier[] = TRAIL_SPECS.map(
  ([name, multiplier, cost, color, glow], tier) => ({
    tier, name, multiplier, cost, color, glow,
  }),
);

// ---------------------------------------------------------------------------
// base upgrades: pedestals, luck, hatch speed, carry
// ---------------------------------------------------------------------------

export interface UpgradeSpec {
  id: UpgradeId;
  name: string;
  description: string;
  maxLevel: number;
  baseCost: number;
  growth: number;
  /** Human-readable effect at a given level. */
  effect: (level: number) => string;
  icon: string;
}

export type UpgradeId = 'pedestals' | 'luck' | 'hatch' | 'carry' | 'stamina' | 'jump';

export const UPGRADES: Record<UpgradeId, UpgradeSpec> = {
  pedestals: {
    id: 'pedestals',
    name: 'Pedestals',
    description: 'More pens in your garden means more pets paying out at once.',
    maxLevel: 16,
    baseCost: 900,
    growth: 2.35,
    effect: (level) => `${pedestalCount(level)} slots`,
    icon: 'grid',
  },
  luck: {
    id: 'luck',
    name: 'Luck',
    description: 'Shifts every hatch toward better rarities, sizes and mutations.',
    maxLevel: 20,
    baseCost: 2_400,
    growth: 2.6,
    effect: (level) => `+${(level * 0.14).toFixed(2)} luck`,
    icon: 'clover',
  },
  hatch: {
    id: 'hatch',
    name: 'Hatch Speed',
    description: 'Eggs crack sooner, so a pedestal spends less time paying nothing.',
    maxLevel: 14,
    baseCost: 1_500,
    growth: 2.5,
    effect: (level) => `${(hatchSpeedFactor(level) * 100).toFixed(0)}% faster`,
    icon: 'timer',
  },
  carry: {
    id: 'carry',
    name: 'Carry Strength',
    description: 'Stolen eggs weigh you down less, and eventually you can hold two.',
    maxLevel: 10,
    baseCost: 6_000,
    growth: 2.8,
    effect: (level) =>
      `${Math.round(carryPenaltyFactor(level) * 100)}% drag` +
      (carryCapacity(level) > 1 ? `, carry ${carryCapacity(level)}` : ''),
    icon: 'weight',
  },
  stamina: {
    id: 'stamina',
    name: 'Stamina',
    description: 'Sprint for longer before you have to slow down.',
    maxLevel: 12,
    baseCost: 3_200,
    growth: 2.45,
    effect: (level) => `${staminaSeconds(level).toFixed(1)}s sprint`,
    icon: 'lungs',
  },
  jump: {
    id: 'jump',
    name: 'Jump',
    description: 'Reach higher ledges. Several nests sit on top of something.',
    maxLevel: 10,
    baseCost: 5_000,
    growth: 2.7,
    effect: (level) => `+${(jumpFactor(level) * 100 - 100).toFixed(0)}% height`,
    icon: 'arrow-up',
  },
};

export const UPGRADE_ORDER: UpgradeId[] = [
  'pedestals', 'luck', 'hatch', 'carry', 'stamina', 'jump',
];

export function upgradeCostAt(id: UpgradeId, level: number): number {
  const spec = UPGRADES[id];
  if (level >= spec.maxLevel) return Infinity;
  return roundNice(spec.baseCost * Math.pow(spec.growth, level));
}

// --- derived effects --------------------------------------------------------

export function pedestalCount(level: number): number {
  return 4 + level * 2;
}

export function luckValue(level: number, rebirths: number): number {
  return level * 0.14 + rebirths * 0.22;
}

export function hatchSpeedFactor(level: number): number {
  // Diminishing: level 14 is a bit over 3x faster, not 14x.
  return 1 - 1 / (1 + level * 0.16);
}

export function hatchSeconds(biomeOrder: number, hatchLevel: number): number {
  const base = 10 + biomeOrder * 3.5;
  return base / (1 + hatchLevel * 0.16);
}

export function carryPenaltyFactor(level: number): number {
  return Math.max(0.05, 0.3 - level * 0.026);
}

export function carryCapacity(level: number): number {
  return level >= 6 ? 2 : 1;
}

export function staminaSeconds(level: number): number {
  return 4.5 + level * 0.75;
}

export function jumpFactor(level: number): number {
  return 1 + level * 0.045;
}

// ---------------------------------------------------------------------------
// rebirth
// ---------------------------------------------------------------------------

/** Money required for rebirth number `n` (1-indexed). */
export function rebirthCost(n: number): number {
  return roundNice(5e8 * Math.pow(18, n - 1));
}

/** Permanent income multiplier after `n` rebirths. */
export function rebirthIncomeMultiplier(n: number): number {
  return 1 + n * 0.75 + Math.max(0, n - 5) * 0.4;
}

/** Permanent Speed retained through a rebirth, as a fraction. */
export function rebirthSpeedKeep(n: number): number {
  return Math.min(0.5, 0.08 * n);
}

export interface RebirthPreview {
  cost: number;
  incomeBefore: number;
  incomeAfter: number;
  keptSpeed: number;
  luckGain: number;
}

export function previewRebirth(
  rebirths: number,
  currentSpeed: number,
  currentMultiplier: number,
): RebirthPreview {
  const next = rebirths + 1;
  return {
    cost: rebirthCost(next),
    incomeBefore: currentMultiplier,
    incomeAfter: rebirthIncomeMultiplier(next),
    keptSpeed: currentSpeed * rebirthSpeedKeep(next),
    luckGain: 0.22,
  };
}

// ---------------------------------------------------------------------------
// display helpers
// ---------------------------------------------------------------------------

export function describeTreadmill(tier: number, trailTier: number): string {
  const rate = trainingRate(tier, trailTier);
  return `${formatMoney(rate)} Speed/s`;
}

/** Seconds of training needed to go from `from` Speed to `to`. */
export function trainingTime(from: number, to: number, rate: number): number {
  if (to <= from) return 0;
  return (to - from) / Math.max(1e-9, rate);
}
