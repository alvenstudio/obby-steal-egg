import { describe, expect, it } from 'vitest';
import * as THREE from 'three';

import { ColliderWorld, moveBox } from '@/core/Physics';
import { Rng } from '@/core/Rng';
import { BIOMES } from '@/data/biomes';
import { PET_BY_ID } from '@/data/pets';
import { UPGRADES } from '@/data/progression';
import { GameState } from '@/game/GameState';

const SHAPE = { radius: 0.38, height: 1.85, stepHeight: 0.52 };
const STEP = 1 / 120;

/**
 * Run the mover for `frames` fixed steps, the way the game actually does.
 *
 * Contact flags are OR-ed across the whole run rather than taken from the last
 * frame. A wall hit on frame one zeroes that axis, so by the final frame there
 * is no motion left to collide and the flag would read false -- which says
 * nothing about whether the mover was ever blocked.
 */
function simulate(
  world: ColliderWorld,
  position: THREE.Vector3,
  velocity: THREE.Vector3,
  frames: number,
  gravity = 0,
) {
  let result = moveBox(world, position, velocity, SHAPE, STEP);
  let hitWall = result.hitWall;
  let hitCeiling = result.hitCeiling;
  let grounded = result.grounded;
  for (let i = 1; i < frames; i++) {
    if (gravity) result.velocity.y -= gravity * STEP;
    result = moveBox(world, result.position, result.velocity, SHAPE, STEP);
    hitWall = hitWall || result.hitWall;
    hitCeiling = hitCeiling || result.hitCeiling;
    grounded = grounded || result.grounded;
  }
  return { ...result, hitWall, hitCeiling, grounded };
}

function floor(world: ColliderWorld, size = 40, y = 0): void {
  world.add(
    new THREE.Vector3(-size, y - 1, -size),
    new THREE.Vector3(size, y, size),
  );
}

describe('collision', () => {
  it('lands a falling box on the floor instead of through it', () => {
    const world = new ColliderWorld();
    floor(world);
    const result = simulate(
      world, new THREE.Vector3(0, 3, 0), new THREE.Vector3(0, -20, 0), 40,
    );
    expect(result.grounded).toBe(true);
    expect(result.position.y).toBeCloseTo(0, 5);
    expect(result.velocity.y).toBe(0);
  });

  it('slides along a wall instead of stopping dead in the corner', () => {
    const world = new ColliderWorld();
    floor(world);
    // A wall facing -X at x = 2.
    world.add(new THREE.Vector3(2, 0, -10), new THREE.Vector3(3, 4, 10));

    const result = simulate(
      world, new THREE.Vector3(1, 0, 0), new THREE.Vector3(8, 0, 8), 20,
    );
    // Blocked on X...
    expect(result.velocity.x).toBe(0);
    // ...but the Z component survives, which is what makes running into a
    // corner feel like sliding rather than sticking.
    expect(result.velocity.z).toBeGreaterThan(0);
    expect(result.position.z).toBeGreaterThan(0);
  });

  it('steps over a low ledge but is blocked by a high one', () => {
    const low = new ColliderWorld();
    floor(low);
    low.add(new THREE.Vector3(1, 0, -5), new THREE.Vector3(6, 0.4, 5));
    const stepped = simulate(
      low, new THREE.Vector3(0, 0, 0), new THREE.Vector3(6, 0, 0), 30,
    );
    expect(stepped.position.x).toBeGreaterThan(0.1);
    expect(stepped.position.y).toBeGreaterThan(0.3);

    const high = new ColliderWorld();
    floor(high);
    high.add(new THREE.Vector3(1, 0, -5), new THREE.Vector3(6, 2.5, 5));
    const blocked = simulate(
      high, new THREE.Vector3(0, 0, 0), new THREE.Vector3(6, 0, 0), 30,
    );
    expect(blocked.hitWall).toBe(true);
    expect(blocked.position.x).toBeLessThan(1);
  });

  it('reports the surface it is standing on', () => {
    const world = new ColliderWorld();
    world.add(
      new THREE.Vector3(-8, -1, -8), new THREE.Vector3(8, 0, 8), 'ice',
    );
    const result = simulate(
      world, new THREE.Vector3(0, 2, 0), new THREE.Vector3(0, -30, 0), 30,
    );
    expect(result.groundKind).toBe('ice');
  });

  it('does not tunnel through a thin platform at high speed', () => {
    const world = new ColliderWorld();
    // A 0.55-unit platform, exactly what the obby is built from.
    world.add(new THREE.Vector3(-6, -0.55, -6), new THREE.Vector3(6, 0, 6));
    // Terminal velocity in one oversized frame: 2.75 units of travel from 1.5
    // units up, which without substepping steps clean past a 0.55 platform.
    const result = moveBox(
      world, new THREE.Vector3(0, 1.5, 0), new THREE.Vector3(0, -55, 0), SHAPE, 1 / 20,
    );
    expect(result.position.y).toBeGreaterThanOrEqual(0);
    expect(result.grounded).toBe(true);
  });

  it('finds the nearest hit when raycasting through several boxes', () => {
    const world = new ColliderWorld();
    world.add(new THREE.Vector3(4, -1, -1), new THREE.Vector3(5, 3, 1));
    world.add(new THREE.Vector3(9, -1, -1), new THREE.Vector3(10, 3, 1));
    const hit = world.raycast(
      new THREE.Vector3(0, 1, 0), new THREE.Vector3(1, 0, 0), 20,
    );
    expect(hit).not.toBeNull();
    expect(hit!.distance).toBeCloseTo(4, 3);
  });
});

describe('the steal-to-hatch loop', () => {
  function ready(): GameState {
    const state = new GameState();
    state.setSeed(12345);
    return state;
  }

  it('rolls an egg that belongs to the biome it came from', () => {
    const state = ready();
    for (const biome of BIOMES) {
      for (let i = 0; i < 25; i++) {
        const egg = state.rollEgg(biome.id);
        expect(egg, biome.id).not.toBeNull();
        const def = PET_BY_ID[egg!.petId];
        expect(def, `${egg!.petId} missing`).toBeDefined();
        expect(def.biome).toBe(biome.id);
        expect(biome.rarities).toContain(def.rarity);
      }
    }
  });

  it('carries, delivers, hatches and then pays out', () => {
    const state = ready();
    expect(state.incomePerSecond).toBe(0);

    const egg = state.takeEgg('forest');
    expect(egg).not.toBeNull();
    expect(state.carried).toHaveLength(1);

    expect(state.deliverCarried()).toBe(1);
    expect(state.carried).toHaveLength(0);
    expect(state.hatching).toHaveLength(1);

    // Run the clock until it hatches.
    for (let i = 0; i < 60 * 60 && state.hatching.length > 0; i++) {
      state.update(1 / 60);
    }
    expect(state.hatching).toHaveLength(0);
    expect(state.pets).toHaveLength(1);
    expect(state.pets[0].slot).toBe(0);
    expect(state.incomePerSecond).toBeGreaterThan(0);
    expect(state.discovered.size).toBe(1);

    const before = state.money;
    state.update(1);
    expect(state.money).toBeGreaterThan(before);
  });

  it('refuses to carry more than the carry limit', () => {
    const state = ready();
    expect(state.carryLimit).toBe(1);
    expect(state.takeEgg('forest')).not.toBeNull();
    expect(state.takeEgg('forest')).toBeNull();

    state.upgrades.carry = UPGRADES.carry.maxLevel;
    expect(state.carryLimit).toBe(2);
    expect(state.takeEgg('forest')).not.toBeNull();
    expect(state.takeEgg('forest')).toBeNull();
  });

  it('drops everything when caught and counts it', () => {
    const state = ready();
    state.takeEgg('forest');
    const dropped = state.dropCarried();
    expect(dropped).toHaveLength(1);
    expect(state.carried).toHaveLength(0);
    expect(state.stats.timesCaught).toBe(1);
  });

  it('keeps eggs in hand rather than destroying them when the garden is full', () => {
    const state = ready();
    state.upgrades.carry = UPGRADES.carry.maxLevel;
    // Fill every pedestal.
    for (let i = 0; i < state.pedestalSlots; i++) {
      state.hatching.push({
        slot: i, petId: 'chicken', size: 'normal', mutation: 'none',
        remaining: 999, total: 999,
      });
    }
    state.takeEgg('forest');
    expect(state.deliverCarried()).toBe(0);
    expect(state.carried).toHaveLength(1);
  });

  it('never places two things on the same pedestal', () => {
    const state = ready();
    state.upgrades.pedestals = 4;
    for (let round = 0; round < 12; round++) {
      state.takeEgg('forest');
      state.deliverCarried();
      for (let i = 0; i < 60 * 40 && state.hatching.length > 0; i++) {
        state.update(1 / 60);
      }
    }
    const used = [...state.pets, ...state.hatching]
      .map((item) => item.slot)
      .filter((slot) => slot >= 0);
    expect(new Set(used).size).toBe(used.length);
  });
});

describe('economy behaviour', () => {
  it('gives bigger and mutated pets proportionally more income', () => {
    const state = new GameState();
    const base = {
      uid: 'a', petId: 'fox', size: 'normal' as const,
      mutation: 'none' as const, slot: 0, obtainedAt: 0,
    };
    const plain = state.petIncome(base);
    const titanic = state.petIncome({ ...base, size: 'titanic' });
    const rainbow = state.petIncome({ ...base, mutation: 'rainbow' });
    const both = state.petIncome({ ...base, size: 'titanic', mutation: 'rainbow' });

    expect(titanic).toBeGreaterThan(plain);
    expect(rainbow).toBeGreaterThan(plain);
    expect(both).toBeCloseTo((titanic / plain) * (rainbow / plain) * plain, 6);
  });

  it('only pays for pets on an unlocked pedestal', () => {
    const state = new GameState();
    state.pets.push({
      uid: 'a', petId: 'fox', size: 'normal', mutation: 'none',
      slot: 0, obtainedAt: 0,
    });
    state.pets.push({
      uid: 'b', petId: 'fox', size: 'normal', mutation: 'none',
      slot: 99, obtainedAt: 0,
    });
    expect(state.placedPets).toHaveLength(1);
    expect(state.storedPets).toHaveLength(1);
    expect(state.incomePerSecond).toBeCloseTo(
      PET_BY_ID.fox.income * state.incomeMultiplier, 6,
    );
  });

  it('resets the run on rebirth but keeps the index and the pedestals', () => {
    const state = new GameState();
    state.upgrades.pedestals = 5;
    state.upgrades.luck = 4;
    state.discovered.add('fox');
    state.pets.push({
      uid: 'a', petId: 'fox', size: 'normal', mutation: 'none', slot: 0, obtainedAt: 0,
    });
    state.speed = 1e9;
    state.addMoney(1e12);

    expect(state.rebirth()).toBe(true);
    expect(state.rebirths).toBe(1);
    expect(state.money).toBe(0);
    expect(state.pets).toHaveLength(0);
    expect(state.upgrades.luck).toBe(0);
    expect(state.upgrades.pedestals).toBe(5);
    expect(state.discovered.has('fox')).toBe(true);
    expect(state.speed).toBeGreaterThan(0);
    expect(state.incomeMultiplier).toBeGreaterThan(1);
  });

  it('caps offline earnings', () => {
    const state = new GameState();
    state.pets.push({
      uid: 'a', petId: 'fox', size: 'normal', mutation: 'none', slot: 0, obtainedAt: 0,
    });
    const oneHour = state.applyOffline(3600);
    state.money = 0;
    const oneWeek = state.applyOffline(7 * 24 * 3600);
    expect(oneWeek).toBeGreaterThan(oneHour);
    expect(oneWeek).toBeLessThan(oneHour * 5);
  });
});

describe('persistence', () => {
  it('round-trips a save without losing anything that matters', () => {
    const original = new GameState();
    original.setSeed(99);
    original.addMoney(123456);
    original.speed = 54321;
    original.upgrades.luck = 3;
    original.treadmillTier = 2;
    original.trailTier = 1;
    original.takeEgg('lake');
    original.deliverCarried();
    original.discovered.add('turtle');

    const restored = new GameState();
    restored.load(original.toSave());

    expect(restored.money).toBe(original.money);
    expect(restored.speed).toBe(original.speed);
    expect(restored.upgrades.luck).toBe(3);
    expect(restored.treadmillTier).toBe(2);
    expect(restored.trailTier).toBe(1);
    expect(restored.hatching).toHaveLength(original.hatching.length);
    expect(restored.discovered.has('turtle')).toBe(true);
  });

  it('drops pets whose species no longer exists rather than throwing', () => {
    const state = new GameState();
    const save = state.toSave();
    save.pets.push({
      uid: 'ghost', petId: 'not-a-real-pet', size: 'normal',
      mutation: 'none', slot: 0, obtainedAt: 0,
    });
    save.discovered.push('also-not-real');
    expect(() => state.load(save)).not.toThrow();
    expect(state.pets).toHaveLength(0);
    expect(state.discovered.size).toBe(0);
  });

  it('clamps out-of-range tiers from a tampered save', () => {
    const state = new GameState();
    const save = state.toSave();
    save.treadmillTier = 9999;
    save.trailTier = -5;
    save.upgrades.luck = 9999;
    state.load(save);
    expect(state.treadmillTier).toBeLessThan(20);
    expect(state.trailTier).toBe(0);
    expect(state.upgrades.luck).toBe(UPGRADES.luck.maxLevel);
  });
});

describe('rng', () => {
  it('is deterministic for a given seed', () => {
    const a = new Rng('same');
    const b = new Rng('same');
    for (let i = 0; i < 50; i++) expect(a.next()).toBe(b.next());
  });

  it('respects weights', () => {
    const rng = new Rng(7);
    let heavy = 0;
    for (let i = 0; i < 4000; i++) {
      if (rng.pickWeighted(['a', 'b'], [9, 1]) === 'a') heavy++;
    }
    expect(heavy / 4000).toBeGreaterThan(0.85);
    expect(heavy / 4000).toBeLessThan(0.95);
  });
});
