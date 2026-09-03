import type { RarityId } from './rarity';

/**
 * The eleven biomes, in progression order.
 *
 * The reference game gates biomes on one stat -- Speed -- and nothing else.
 * No money price, no rebirth wall, no pet-power check. That is a genuinely
 * good design: the same number that unlocks a zone is the number that lets you
 * survive it, so "can I get in" and "can I get out" are the same question, and
 * the player never unlocks content they cannot actually play.
 *
 * Speed is also why this converts to first person well. In third person the
 * chase is a number comparison you watch from outside; in first person it is a
 * corridor you are running down with something roaring behind you.
 */

export type BiomeId =
  | 'forest'
  | 'lake'
  | 'desert'
  | 'jungle'
  | 'snow'
  | 'volcano'
  | 'abyss'
  | 'prehistoric'
  | 'cosmic'
  | 'blossom'
  | 'titan'
  | 'event';

export interface BiomePalette {
  /** Ground / terrain. */
  ground: string;
  groundAlt: string;
  /** Rock, cliff and structural props. */
  rock: string;
  /** Foliage or the biome's signature accent. */
  accent: string;
  accentAlt: string;
  /** Sky and fog. */
  sky: string;
  fog: string;
  /** Sun colour and intensity for this zone. */
  sun: string;
  sunIntensity: number;
  ambient: string;
  ambientIntensity: number;
  /** Nest platform materials. */
  nest: string;
  nestAlt: string;
}

export interface BiomeDef {
  id: BiomeId;
  name: string;
  /** Position in the unlock chain; `event` is -1 (never in the chain). */
  order: number;
  /** Speed stat required to enter. */
  speedGate: number;
  /** Guardian archetype defending this biome's nest. */
  guardian: string;
  /**
   * The guardian is a giant version of the biome's signature animal, exactly
   * as in the reference game, so it reuses that pet's model rather than
   * needing one of its own -- and seeing the thing that chased you later
   * standing on your own pedestal is a genuinely good payoff.
   */
  guardianPet: string;
  /** How much bigger the guardian is than the pet it is built from. */
  guardianScale: number;
  /** Guardian tier from ai/Guardian's tuning table. */
  guardianTier: 'drowsy' | 'watchful' | 'fierce' | 'relentless' | 'apex';
  /**
   * Guardian top speed as a FRACTION of the player's sprint at this biome's
   * gate -- never an absolute number.
   *
   * Hardcoding absolute speeds is how these games end up unwinnable: the
   * player's movement is logarithmic in Speed, so a linear guardian table
   * silently overtakes them in the late biomes. Expressed as a ratio, "you
   * escape by a hair at the gate and gain comfort by overtraining" holds by
   * construction at every tier, and re-tuning the movement curve cannot break
   * it. Resolve with `guardianSpeedAt()`.
   */
  guardianSpeedRatio: number;
  /** Distance from the safe zone to this biome's nest, world units. */
  distance: number;
  /** Compass bearing of the biome from the safe zone, radians. */
  bearing: number;
  /** How mass the egg is: higher slows the carrier more. */
  eggWeight: number;
  /** Seconds to complete the steal interaction. */
  stealTime: number;
  /** Rarities this biome's eggs can roll, in ascending order. */
  rarities: RarityId[];
  palette: BiomePalette;
  /** One-line flavour shown on the unlock card. */
  tagline: string;
  /** Ambience root frequency, Hz. */
  ambienceHz: number;
  /** Terrain generator style. */
  terrain: 'meadow' | 'water' | 'dunes' | 'canopy' | 'ice' | 'lava' | 'deep' | 'bone' | 'void' | 'garden' | 'ruins';
}

const CHAIN: Array<Omit<BiomeDef, 'order'>> = [
  {
    id: 'forest',
    name: 'Whisperpine Forest',
    speedGate: 0,
    guardian: 'Broodhen',
    guardianPet: 'chicken',
    guardianScale: 4.2,
    guardianTier: 'drowsy',
    guardianSpeedRatio: 0.62,
    distance: 88,
    bearing: 0,
    eggWeight: 1,
    stealTime: 1.1,
    rarities: ['common', 'uncommon', 'rare', 'epic', 'legendary'],
    tagline: 'Soft ground, sleepy hens, and your first very bad idea.',
    ambienceHz: 96,
    terrain: 'meadow',
    palette: {
      ground: '#5f9e4a', groundAlt: '#4d8a3c', rock: '#7d7466',
      accent: '#2f7d3f', accentAlt: '#8fc96a',
      sky: '#8fd0f5', fog: '#b8e0f7', sun: '#fff4d6', sunIntensity: 2.5,
      ambient: '#a8ccdd', ambientIntensity: 0.55,
      nest: '#8a6a42', nestAlt: '#c3a06a',
    },
  },
  {
    id: 'lake',
    name: 'Glasswater Lake',
    speedGate: 900,
    guardian: 'Pale Swan',
    guardianPet: 'swan',
    guardianScale: 4.0,
    guardianTier: 'drowsy',
    guardianSpeedRatio: 0.9,
    distance: 132,
    bearing: 0.62,
    eggWeight: 1.15,
    stealTime: 1.3,
    rarities: ['common', 'uncommon', 'rare', 'epic', 'legendary', 'cosmic'],
    tagline: 'Stepping stones, no cover, and something long under the surface.',
    ambienceHz: 108,
    terrain: 'water',
    palette: {
      ground: '#6bb0a0', groundAlt: '#4f9488', rock: '#8b9aa2',
      accent: '#3fa8d8', accentAlt: '#bff0ea',
      sky: '#a4e2f2', fog: '#cdeff5', sun: '#fff8e8', sunIntensity: 2.6,
      ambient: '#b4dfe8', ambientIntensity: 0.6,
      nest: '#a89170', nestAlt: '#d8c9a4',
    },
  },
  {
    id: 'desert',
    name: 'Ashfang Dunes',
    speedGate: 10_000,
    guardian: 'Dune Scorpion',
    guardianPet: 'scorpion',
    guardianScale: 4.4,
    guardianTier: 'watchful',
    guardianSpeedRatio: 0.92,
    distance: 178,
    bearing: 1.24,
    eggWeight: 1.3,
    stealTime: 1.5,
    rarities: ['common', 'uncommon', 'rare', 'epic', 'legendary', 'mythic', 'cosmic'],
    tagline: 'Open sightlines in every direction. There is nowhere to hide out here.',
    ambienceHz: 82,
    terrain: 'dunes',
    palette: {
      ground: '#dcc07a', groundAlt: '#c9a85e', rock: '#a8875a',
      accent: '#e8a55c', accentAlt: '#f7dfa8',
      sky: '#f3d9a4', fog: '#f0dcb0', sun: '#ffe9b0', sunIntensity: 3.1,
      ambient: '#e0c89a', ambientIntensity: 0.7,
      nest: '#9c7844', nestAlt: '#d4ab63',
    },
  },
  {
    id: 'jungle',
    name: 'Verdant Snarl',
    speedGate: 40_000,
    guardian: 'Emerald Tiger',
    guardianPet: 'tiger',
    guardianScale: 4.2,
    guardianTier: 'watchful',
    guardianSpeedRatio: 0.93,
    distance: 226,
    bearing: 1.86,
    eggWeight: 1.45,
    stealTime: 1.7,
    rarities: ['uncommon', 'rare', 'epic', 'legendary', 'mythic', 'cosmic', 'secret'],
    tagline: 'Vine bridges and blind corners. You will hear it before you see it.',
    ambienceHz: 74,
    terrain: 'canopy',
    palette: {
      ground: '#3d7a33', groundAlt: '#2e6128', rock: '#6b6350',
      accent: '#1f8f4a', accentAlt: '#79d05a',
      sky: '#7fc06a', fog: '#8fbf7c', sun: '#eaf7c4', sunIntensity: 2.2,
      ambient: '#84b57a', ambientIntensity: 0.5,
      nest: '#6e5432', nestAlt: '#a88a52',
    },
  },
  {
    id: 'snow',
    name: 'Hollowfrost Shelf',
    speedGate: 170_000,
    guardian: 'Rimebound Yeti',
    guardianPet: 'yeti',
    guardianScale: 4.6,
    guardianTier: 'fierce',
    guardianSpeedRatio: 0.93,
    distance: 272,
    bearing: 2.48,
    eggWeight: 1.6,
    stealTime: 1.9,
    rarities: ['rare', 'epic', 'legendary', 'mythic', 'cosmic', 'secret', 'eternal'],
    tagline: 'Ice you slide on, wind you cannot hear over, and a very patient neighbour.',
    ambienceHz: 128,
    terrain: 'ice',
    palette: {
      ground: '#e4f0f7', groundAlt: '#c6dcea', rock: '#93aec2',
      accent: '#7fc4e8', accentAlt: '#ffffff',
      sky: '#cfe6f5', fog: '#dcecf6', sun: '#eaf4ff', sunIntensity: 2.4,
      ambient: '#c2d9e8', ambientIntensity: 0.75,
      nest: '#9db6c6', nestAlt: '#e8f2f8',
    },
  },
  {
    id: 'volcano',
    name: 'Emberfall Caldera',
    speedGate: 700_000,
    guardian: 'Cerberus',
    guardianPet: 'cerberus',
    guardianScale: 4.8,
    guardianTier: 'fierce',
    guardianSpeedRatio: 0.94,
    distance: 318,
    bearing: 3.10,
    eggWeight: 1.75,
    stealTime: 2.1,
    rarities: ['epic', 'legendary', 'mythic', 'cosmic', 'secret', 'eternal'],
    tagline: 'Three heads, one nest, and a floor that is only sometimes a floor.',
    ambienceHz: 58,
    terrain: 'lava',
    palette: {
      ground: '#3a2a28', groundAlt: '#2a1e1d', rock: '#54403c',
      accent: '#ff6a1f', accentAlt: '#ffc14d',
      sky: '#78302a', fog: '#8f3c2c', sun: '#ffb066', sunIntensity: 2.0,
      ambient: '#7a3a2c', ambientIntensity: 0.65,
      nest: '#6b3a26', nestAlt: '#c4682e',
    },
  },
  {
    id: 'abyss',
    name: 'Abyss Ocean',
    speedGate: 2_500_000,
    guardian: 'Kraken',
    guardianPet: 'kraken',
    guardianScale: 5.2,
    guardianTier: 'relentless',
    guardianSpeedRatio: 0.94,
    distance: 364,
    bearing: 3.72,
    eggWeight: 1.9,
    stealTime: 2.3,
    rarities: ['epic', 'legendary', 'mythic', 'cosmic', 'secret', 'eternal'],
    tagline: 'No sky, no horizon, and eight reasons to keep moving.',
    ambienceHz: 46,
    terrain: 'deep',
    palette: {
      ground: '#16323f', groundAlt: '#0f2530', rock: '#24485a',
      accent: '#1fa8b8', accentAlt: '#68e8ff',
      sky: '#0b2531', fog: '#0f3242', sun: '#7fd4e8', sunIntensity: 1.3,
      ambient: '#16465c', ambientIntensity: 0.85,
      nest: '#2b5468', nestAlt: '#4f93a8',
    },
  },
  {
    id: 'prehistoric',
    name: 'Fossil Basin',
    speedGate: 18_000_000,
    guardian: 'T-Rex',
    guardianPet: 't-rex',
    guardianScale: 5.4,
    guardianTier: 'relentless',
    guardianSpeedRatio: 0.95,
    distance: 410,
    bearing: 4.34,
    eggWeight: 2.1,
    stealTime: 2.5,
    rarities: ['legendary', 'mythic', 'cosmic', 'secret', 'eternal'],
    tagline: 'The ground shakes on a two-second rhythm. Do not let it get to one.',
    ambienceHz: 52,
    terrain: 'bone',
    palette: {
      ground: '#8a7550', groundAlt: '#6f5d3f', rock: '#a89878',
      accent: '#c4652f', accentAlt: '#e0cfa4',
      sky: '#c9a878', fog: '#bfa484', sun: '#ffd9a0', sunIntensity: 2.3,
      ambient: '#b09878', ambientIntensity: 0.6,
      nest: '#7d6a48', nestAlt: '#c0ab80',
    },
  },
  {
    id: 'cosmic',
    name: 'Starfall Rift',
    speedGate: 700_000_000,
    guardian: 'Hollow Constellate',
    guardianPet: 'cosmic-skeleton-boss',
    guardianScale: 5.6,
    guardianTier: 'apex',
    guardianSpeedRatio: 0.95,
    distance: 456,
    bearing: 4.96,
    eggWeight: 2.3,
    stealTime: 2.7,
    rarities: ['mythic', 'cosmic', 'secret', 'eternal', 'divine'],
    tagline: 'Floating islands, low gravity, and something assembling itself behind you.',
    ambienceHz: 138,
    terrain: 'void',
    palette: {
      ground: '#2b2450', groundAlt: '#1e1a3c', rock: '#443a72',
      accent: '#8a6bff', accentAlt: '#5ce1ff',
      sky: '#100c22', fog: '#1a1438', sun: '#c9b4ff', sunIntensity: 1.6,
      ambient: '#2e2760', ambientIntensity: 0.9,
      nest: '#3d3468', nestAlt: '#7f6bd0',
    },
  },
  {
    id: 'blossom',
    name: 'Cherry Blossom Terrace',
    speedGate: 2_500_000_000,
    guardian: 'Nine-Tail Kitsune',
    guardianPet: 'kitsune',
    guardianScale: 5.0,
    guardianTier: 'apex',
    guardianSpeedRatio: 0.96,
    distance: 500,
    bearing: 5.58,
    eggWeight: 2.5,
    stealTime: 2.9,
    rarities: ['cosmic', 'secret', 'eternal', 'divine'],
    tagline: 'The prettiest place in the world to be spectacularly outrun.',
    ambienceHz: 116,
    terrain: 'garden',
    palette: {
      ground: '#d8809f', groundAlt: '#c06a8a', rock: '#8f7a86',
      accent: '#ff9ec4', accentAlt: '#ffe0ec',
      sky: '#ffd0e2', fog: '#ffdcea', sun: '#fff0f6', sunIntensity: 2.5,
      ambient: '#e8b8cc', ambientIntensity: 0.7,
      nest: '#8f6a56', nestAlt: '#d8a88c',
    },
  },
  {
    id: 'titan',
    name: 'Titan Temple',
    speedGate: 7_000_000_000,
    guardian: 'Nightflame',
    guardianPet: 'nightflame',
    guardianScale: 6.0,
    guardianTier: 'apex',
    guardianSpeedRatio: 0.97,
    distance: 548,
    bearing: 6.02,
    eggWeight: 2.8,
    stealTime: 3.2,
    rarities: ['secret', 'eternal', 'divine'],
    tagline: 'Everything here was built to keep something in. It did not work.',
    ambienceHz: 42,
    terrain: 'ruins',
    palette: {
      ground: '#3c3730', groundAlt: '#2c2822', rock: '#5c5348',
      accent: '#d4a03c', accentAlt: '#ff7a3c',
      sky: '#241d1a', fog: '#332a24', sun: '#ffb85c', sunIntensity: 1.5,
      ambient: '#4a3c30', ambientIntensity: 0.8,
      nest: '#5a4c38', nestAlt: '#b08a4c',
    },
  },
];

export const BIOMES: BiomeDef[] = CHAIN.map((biome, order) => ({ ...biome, order }));

export const BIOME_BY_ID: Record<string, BiomeDef> = Object.fromEntries(
  BIOMES.map((biome) => [biome.id, biome]),
);

/** Maps the roster's human biome labels onto ids. */
export const BIOME_LABEL_TO_ID: Record<string, BiomeId> = {
  Forest: 'forest',
  Lake: 'lake',
  Desert: 'desert',
  Jungle: 'jungle',
  Snow: 'snow',
  Volcano: 'volcano',
  'Abyss Ocean': 'abyss',
  Prehistoric: 'prehistoric',
  Cosmic: 'cosmic',
  'Cherry Blossom': 'blossom',
  'Titan Temple': 'titan',
  Event: 'event',
};

/** Highest-order biome the player may enter at this Speed. */
export function highestUnlocked(speed: number): BiomeDef {
  let best = BIOMES[0];
  for (const biome of BIOMES) {
    if (speed >= biome.speedGate) best = biome;
  }
  return best;
}

export function isUnlocked(biome: BiomeDef, speed: number): boolean {
  return speed >= biome.speedGate;
}

/** The next locked biome, or null once everything is open. */
export function nextLocked(speed: number): BiomeDef | null {
  for (const biome of BIOMES) {
    if (speed < biome.speedGate) return biome;
  }
  return null;
}


/**
 * The guardian's actual top speed for this biome, in world units per second.
 *
 * `sprintAtGate` is the player's sprint speed at exactly this biome's Speed
 * gate, which the caller computes from the progression curve. Keeping the
 * resolution here means the invariant -- guardian is always slightly slower
 * than a just-qualified player -- lives next to the ratios it constrains.
 */
export function guardianSpeedAt(biome: BiomeDef, sprintAtGate: number): number {
  return sprintAtGate * biome.guardianSpeedRatio;
}
