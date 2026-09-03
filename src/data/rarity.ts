/**
 * Rarity, size and mutation ladders.
 *
 * Rarity does not set income here -- every pet carries its own authored
 * income -- it sets *drop odds* and presentation. Size and mutation are the
 * multiplicative rolls layered on top, and they are what make a hatch worth
 * watching: a Titanic Rainbow Common can out-earn a plain Legendary, so no
 * pull is ever purely a loss.
 */

export type RarityId =
  | 'common'
  | 'uncommon'
  | 'rare'
  | 'epic'
  | 'legendary'
  | 'mythic'
  | 'cosmic'
  | 'secret'
  | 'eternal'
  | 'divine'
  | 'event';

export interface Rarity {
  id: RarityId;
  name: string;
  /** Relative draw weight within a biome's egg, before luck. */
  weight: number;
  color: string;
  glow: string;
  /** How strongly luck shifts weight toward this tier. */
  luckBias: number;
  /** Aura/particle intensity, 0..1. */
  aura: number;
  /** Rank used for sorting and for "new best pet" comparisons. */
  rank: number;
}

export const RARITIES: Record<RarityId, Rarity> = {
  common: {
    id: 'common', name: 'Common', weight: 1000, color: '#b9c2cc', glow: '#8d97a3',
    luckBias: -1.0, aura: 0, rank: 0,
  },
  uncommon: {
    id: 'uncommon', name: 'Uncommon', weight: 460, color: '#6fd28a', glow: '#3fae5c',
    luckBias: -0.5, aura: 0.08, rank: 1,
  },
  rare: {
    id: 'rare', name: 'Rare', weight: 180, color: '#5aa9f0', glow: '#2f7fd0',
    luckBias: 0.1, aura: 0.2, rank: 2,
  },
  epic: {
    id: 'epic', name: 'Epic', weight: 62, color: '#b072f2', glow: '#7b3fd0',
    luckBias: 0.5, aura: 0.36, rank: 3,
  },
  legendary: {
    id: 'legendary', name: 'Legendary', weight: 19, color: '#ffb443', glow: '#e07a12',
    luckBias: 0.9, aura: 0.52, rank: 4,
  },
  mythic: {
    id: 'mythic', name: 'Mythic', weight: 5.4, color: '#ff5f7e', glow: '#c81e4a',
    luckBias: 1.2, aura: 0.66, rank: 5,
  },
  cosmic: {
    id: 'cosmic', name: 'Cosmic', weight: 1.5, color: '#5ce1ff', glow: '#1b7fa8',
    luckBias: 1.45, aura: 0.78, rank: 6,
  },
  secret: {
    id: 'secret', name: 'Secret', weight: 0.34, color: '#1a1a24', glow: '#8affd6',
    luckBias: 1.7, aura: 0.88, rank: 7,
  },
  eternal: {
    id: 'eternal', name: 'Eternal', weight: 0.075, color: '#f2e6ff', glow: '#a06bff',
    luckBias: 1.9, aura: 0.95, rank: 8,
  },
  divine: {
    id: 'divine', name: 'Divine', weight: 0.012, color: '#fff6c9', glow: '#ffd447',
    luckBias: 2.1, aura: 1, rank: 9,
  },
  event: {
    // Never rolled from a biome egg; awarded by events and the limited shop.
    id: 'event', name: 'Event', weight: 0, color: '#ff8ae0', glow: '#c33ba0',
    luckBias: 0, aura: 0.8, rank: 6.5,
  },
};

export const RARITY_ORDER: RarityId[] = [
  'common', 'uncommon', 'rare', 'epic', 'legendary',
  'mythic', 'cosmic', 'secret', 'eternal', 'divine',
];

/** Rarities a biome egg can actually roll. */
export const ROLLABLE_RARITIES = RARITY_ORDER;

export type SizeId = 'tiny' | 'normal' | 'large' | 'giant' | 'titanic';

export interface SizeVariant {
  id: SizeId;
  name: string;
  weight: number;
  income: number;
  scale: number;
  color: string;
}

export const SIZES: Record<SizeId, SizeVariant> = {
  tiny: { id: 'tiny', name: 'Tiny', weight: 220, income: 0.6, scale: 0.68, color: '#9aa6b2' },
  normal: { id: 'normal', name: '', weight: 500, income: 1, scale: 1, color: '#cfd6de' },
  large: { id: 'large', name: 'Large', weight: 200, income: 1.8, scale: 1.28, color: '#7fd6a4' },
  giant: { id: 'giant', name: 'Giant', weight: 65, income: 3.4, scale: 1.62, color: '#5aa9f0' },
  titanic: { id: 'titanic', name: 'Titanic', weight: 15, income: 7, scale: 2.05, color: '#ffb443' },
};

export const SIZE_ORDER: SizeId[] = ['tiny', 'normal', 'large', 'giant', 'titanic'];

export type MutationId = 'none' | 'gold' | 'diamond' | 'rainbow' | 'void';

export interface Mutation {
  id: MutationId;
  name: string;
  weight: number;
  income: number;
  tint: string | null;
  emissive: number;
  /** true = cycle hue over time rather than using a fixed tint. */
  animated: boolean;
}

export const MUTATIONS: Record<MutationId, Mutation> = {
  none: { id: 'none', name: '', weight: 780, income: 1, tint: null, emissive: 0, animated: false },
  gold: {
    id: 'gold', name: 'Gold', weight: 140, income: 2.2,
    tint: '#ffc94a', emissive: 0.22, animated: false,
  },
  diamond: {
    id: 'diamond', name: 'Diamond', weight: 55, income: 4.5,
    tint: '#a8e8ff', emissive: 0.35, animated: false,
  },
  rainbow: {
    id: 'rainbow', name: 'Rainbow', weight: 20, income: 9,
    tint: '#ff5f7e', emissive: 0.45, animated: true,
  },
  void: {
    id: 'void', name: 'Void', weight: 5, income: 22,
    tint: '#2a1140', emissive: 0.7, animated: true,
  },
};

export const MUTATION_ORDER: MutationId[] = ['none', 'gold', 'diamond', 'rainbow', 'void'];

/**
 * Luck reweights the tables without ever zeroing a tier. Each point of luck
 * roughly doubles the odds of positively-biased tiers and halves the Commons.
 */
export function rarityWeights(luck: number, allowed: RarityId[] = ROLLABLE_RARITIES): number[] {
  return allowed.map((id) => {
    const rarity = RARITIES[id];
    return rarity.weight * Math.pow(2, rarity.luckBias * luck);
  });
}

export function mutationWeights(luck: number): number[] {
  return MUTATION_ORDER.map((id, index) => {
    const bias = index === 0 ? -0.55 : 0.28 * index;
    return MUTATIONS[id].weight * Math.pow(2, bias * luck);
  });
}

export function sizeWeights(luck: number): number[] {
  return SIZE_ORDER.map((id, index) => {
    const bias = index <= 1 ? -0.22 * (2 - index) : 0.24 * (index - 1);
    return SIZES[id].weight * Math.pow(2, bias * luck * 0.6);
  });
}

/** Income multiplier contributed by the size and mutation rolls. */
export function rollMultiplier(size: SizeId, mutation: MutationId): number {
  return SIZES[size].income * MUTATIONS[mutation].income;
}

/** "Titanic Rainbow Fox" — only the parts worth saying out loud. */
export function decoratedName(base: string, size: SizeId, mutation: MutationId): string {
  const parts: string[] = [];
  if (SIZES[size].name) parts.push(SIZES[size].name);
  if (MUTATIONS[mutation].name) parts.push(MUTATIONS[mutation].name);
  parts.push(base);
  return parts.join(' ');
}
