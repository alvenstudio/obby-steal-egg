import { describe, expect, it } from 'vitest';

import { BIOMES, guardianSpeedAt } from '@/data/biomes';
import { PETS, PET_BY_ID, petsOfBiome } from '@/data/pets';
import {
  TRAILS, TREADMILLS, UPGRADES, UPGRADE_ORDER, UpgradeId,
  rebirthIncomeMultiplier, sprintSpeed, speedMultiplier, trainingRate,
  upgradeCostAt,
} from '@/data/progression';
import { RARITIES, RARITY_ORDER, SIZES, rarityWeights } from '@/data/rarity';
import { DEFAULT_TUNING } from '@/player/PlayerController';

/**
 * These assert the *relationships* the design depends on, not literal numbers.
 * Anything that pins a constant would just have to be updated every time the
 * economy is retuned, which would make the suite a chore rather than a guard.
 */

describe('biome progression', () => {
  it('gates rise strictly with biome order', () => {
    for (let i = 1; i < BIOMES.length; i++) {
      expect(BIOMES[i].speedGate).toBeGreaterThan(BIOMES[i - 1].speedGate);
    }
  });

  it('places each biome further out than the last', () => {
    for (let i = 1; i < BIOMES.length; i++) {
      expect(BIOMES[i].distance).toBeGreaterThan(BIOMES[i - 1].distance);
    }
  });

  it('gives every biome a guardian model that exists in the roster', () => {
    for (const biome of BIOMES) {
      expect(PET_BY_ID[biome.guardianPet], `${biome.id} guardian`).toBeDefined();
    }
  });

  /**
   * The single most important invariant in the game. A player who has only
   * just met a biome's gate must be able to outrun its guardian -- otherwise
   * the biome is unlockable but unplayable, which is exactly the failure the
   * ratio-based guardian speeds exist to prevent.
   */
  it('always leaves a just-qualified player faster than the guardian', () => {
    for (const biome of BIOMES) {
      const playerSprint = sprintSpeed(biome.speedGate, DEFAULT_TUNING.sprintSpeed);
      const guardian = guardianSpeedAt(biome, playerSprint);
      expect(guardian, `${biome.id} guardian speed`).toBeLessThan(playerSprint);
      // ...but not so much slower that the chase stops being a threat.
      expect(guardian / playerSprint).toBeGreaterThan(0.5);
    }
  });

  it('makes the escape margin tighter in later biomes', () => {
    const margins = BIOMES.map((biome) => 1 - biome.guardianSpeedRatio);
    // The tutorial biome is deliberately generous; from Lake on it tightens.
    for (let i = 2; i < margins.length; i++) {
      expect(margins[i]).toBeLessThanOrEqual(margins[i - 1] + 1e-9);
    }
  });
});

describe('movement curve', () => {
  it('grows with Speed but never explodes', () => {
    expect(speedMultiplier(0)).toBe(1);
    const atLastGate = speedMultiplier(BIOMES[BIOMES.length - 1].speedGate);
    expect(atLastGate).toBeGreaterThan(2);
    expect(atLastGate).toBeLessThan(6);
  });

  it('is monotonic', () => {
    let previous = 0;
    for (const speed of [0, 900, 1e4, 4e4, 1.7e5, 7e5, 2.5e6, 1.8e7, 7e8, 2.5e9, 7e9]) {
      const value = speedMultiplier(speed);
      expect(value).toBeGreaterThan(previous);
      previous = value;
    }
  });
});

describe('pet roster', () => {
  it('has a unique id for every pet', () => {
    const ids = new Set(PETS.map((pet) => pet.id));
    expect(ids.size).toBe(PETS.length);
  });

  it('gives every biome a full roster', () => {
    for (const biome of BIOMES) {
      expect(petsOfBiome(biome.id).length, biome.id).toBeGreaterThanOrEqual(7);
    }
  });

  it('never lets a biome roll a rarity it has no pet for', () => {
    for (const biome of BIOMES) {
      const pool = petsOfBiome(biome.id);
      const present = new Set(pool.map((pet) => pet.rarity));
      const rollable = biome.rarities.filter((rarity) => present.has(rarity));
      expect(rollable.length, `${biome.id} has no rollable rarity`).toBeGreaterThan(0);
    }
  });

  it('pays more for rarer pets within a biome, on average', () => {
    for (const biome of BIOMES) {
      const pool = petsOfBiome(biome.id);
      const byRank = [...pool].sort(
        (a, b) => RARITIES[a.rarity].rank - RARITIES[b.rarity].rank,
      );
      for (let i = 1; i < byRank.length; i++) {
        if (RARITIES[byRank[i].rarity].rank === RARITIES[byRank[i - 1].rarity].rank) continue;
        expect(byRank[i].income, `${biome.id}: ${byRank[i].name}`)
          .toBeGreaterThan(byRank[i - 1].income);
      }
    }
  });

  it('spans the full income range the progression needs', () => {
    const incomes = PETS.map((pet) => pet.income);
    expect(Math.min(...incomes)).toBeLessThanOrEqual(2);
    expect(Math.max(...incomes)).toBeGreaterThan(1e9);
  });

  it('points every pet at a model path derived from its id', () => {
    for (const pet of PETS) {
      expect(pet.model).toBe(`models/pets/${pet.id}.glb`);
    }
  });
});

describe('rarity tables', () => {
  it('orders weights so rarer is rarer', () => {
    for (let i = 1; i < RARITY_ORDER.length; i++) {
      expect(RARITIES[RARITY_ORDER[i]].weight)
        .toBeLessThan(RARITIES[RARITY_ORDER[i - 1]].weight);
    }
  });

  it('lets luck shift the distribution without zeroing any tier', () => {
    const base = rarityWeights(0);
    const lucky = rarityWeights(3);
    for (const weight of lucky) expect(weight).toBeGreaterThan(0);

    const share = (weights: number[], index: number) =>
      weights[index] / weights.reduce((sum, w) => sum + w, 0);
    const topIndex = RARITY_ORDER.length - 1;
    expect(share(lucky, topIndex)).toBeGreaterThan(share(base, topIndex));
    expect(share(lucky, 0)).toBeLessThan(share(base, 0));
  });

  it('makes bigger sizes rarer and more valuable together', () => {
    const order = ['tiny', 'normal', 'large', 'giant', 'titanic'] as const;
    for (let i = 2; i < order.length; i++) {
      expect(SIZES[order[i]].weight).toBeLessThan(SIZES[order[i - 1]].weight);
      expect(SIZES[order[i]].income).toBeGreaterThan(SIZES[order[i - 1]].income);
    }
  });
});

describe('upgrade curves', () => {
  it('makes every upgrade level cost more than the last', () => {
    for (const id of UPGRADE_ORDER) {
      const spec = UPGRADES[id as UpgradeId];
      for (let level = 1; level < spec.maxLevel; level++) {
        expect(upgradeCostAt(id as UpgradeId, level))
          .toBeGreaterThan(upgradeCostAt(id as UpgradeId, level - 1));
      }
      expect(upgradeCostAt(id as UpgradeId, spec.maxLevel)).toBe(Infinity);
    }
  });

  it('raises treadmill and trail rates and costs together', () => {
    for (let i = 1; i < TREADMILLS.length; i++) {
      expect(TREADMILLS[i].rate).toBeGreaterThan(TREADMILLS[i - 1].rate);
      expect(TREADMILLS[i].cost).toBeGreaterThan(TREADMILLS[i - 1].cost);
    }
    for (let i = 1; i < TRAILS.length; i++) {
      expect(TRAILS[i].multiplier).toBeGreaterThan(TRAILS[i - 1].multiplier);
      expect(TRAILS[i].cost).toBeGreaterThan(TRAILS[i - 1].cost);
    }
  });

  it('grows the training rate fast enough to reach the last gate', () => {
    const maxRate = trainingRate(TREADMILLS.length - 1, TRAILS.length - 1);
    const lastGate = BIOMES[BIOMES.length - 1].speedGate;
    const secondsAtFullRate = lastGate / maxRate;
    // A few minutes of training at full kit, not a few days.
    expect(secondsAtFullRate).toBeLessThan(20 * 60);
    expect(secondsAtFullRate).toBeGreaterThan(30);
  });

  it('keeps the first biome reachable almost immediately', () => {
    const startingRate = trainingRate(0, 0);
    const lakeGate = BIOMES[1].speedGate;
    expect(lakeGate / startingRate).toBeLessThan(90);
  });
});

describe('rebirth', () => {
  it('always increases the income multiplier', () => {
    for (let n = 1; n < 12; n++) {
      expect(rebirthIncomeMultiplier(n)).toBeGreaterThan(rebirthIncomeMultiplier(n - 1));
    }
  });
});
