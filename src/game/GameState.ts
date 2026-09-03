import { BIOMES, BIOME_BY_ID, BiomeDef, BiomeId, highestUnlocked } from '@/data/biomes';
import { PETS, PET_BY_ID, PetDef, petsOfBiome } from '@/data/pets';
import {
  MUTATIONS, MUTATION_ORDER, MutationId, RARITIES, RarityId, RARITY_ORDER,
  SIZES, SIZE_ORDER, SizeId, decoratedName, mutationWeights, rarityWeights,
  rollMultiplier, sizeWeights,
} from '@/data/rarity';
import {
  TRAILS, TREADMILLS, UpgradeId, UPGRADES, carryCapacity, carryPenaltyFactor,
  hatchSeconds, jumpFactor, luckValue, pedestalCount, rebirthCost,
  rebirthIncomeMultiplier, rebirthSpeedKeep, staminaSeconds, trainingRate,
  upgradeCostAt,
} from '@/data/progression';
import { Rng } from '@/core/Rng';

/**
 * The entire persistent game model.
 *
 * Everything the player has done lives here and nowhere else: the renderer,
 * the UI and the world all read from this and never hold their own copy. That
 * is what makes save/load a single JSON round-trip and makes the balance tests
 * able to fast-forward a whole playthrough without a browser.
 */

export interface OwnedPet {
  /** Unique instance id; several copies of the same species can coexist. */
  uid: string;
  petId: string;
  size: SizeId;
  mutation: MutationId;
  /** Pedestal index, or -1 when sitting in storage. */
  slot: number;
  /** Timestamp (ms) the pet was obtained, for sorting the collection. */
  obtainedAt: number;
}

export interface CarriedEgg {
  biome: BiomeId;
  /** Pre-rolled at steal time so the hatch cannot be save-scummed. */
  petId: string;
  size: SizeId;
  mutation: MutationId;
  weight: number;
}

export interface HatchingEgg {
  slot: number;
  petId: string;
  size: SizeId;
  mutation: MutationId;
  /** Seconds remaining. */
  remaining: number;
  total: number;
}

export interface Stats {
  eggsStolen: number;
  timesCaught: number;
  petsHatched: number;
  totalEarned: number;
  distanceRun: number;
  bestPetIncome: number;
  playSeconds: number;
}

export interface SaveData {
  version: number;
  money: number;
  speed: number;
  treadmillTier: number;
  trailTier: number;
  upgrades: Record<UpgradeId, number>;
  rebirths: number;
  pets: OwnedPet[];
  hatching: HatchingEgg[];
  discovered: string[];
  stats: Stats;
  savedAt: number;
  seed: number;
}

export const SAVE_VERSION = 3;

export type GameEvent =
  | { type: 'money'; amount: number; total: number }
  | { type: 'stole'; biome: BiomeId }
  | { type: 'caught'; biome: BiomeId; lost: boolean }
  | { type: 'delivered'; egg: CarriedEgg; slot: number }
  | { type: 'hatched'; pet: OwnedPet; isNew: boolean }
  | { type: 'biomeUnlocked'; biome: BiomeDef }
  | { type: 'upgrade'; id: UpgradeId | 'treadmill' | 'trail'; level: number }
  | { type: 'rebirth'; count: number }
  | { type: 'notice'; text: string; tone?: 'info' | 'good' | 'bad' };

type Listener = (event: GameEvent) => void;

let uidCounter = 0;

export class GameState {
  money = 0;
  speed = 0;
  treadmillTier = 0;
  trailTier = 0;
  rebirths = 0;

  upgrades: Record<UpgradeId, number> = {
    pedestals: 0, luck: 0, hatch: 0, carry: 0, stamina: 0, jump: 0,
  };

  pets: OwnedPet[] = [];
  hatching: HatchingEgg[] = [];
  discovered = new Set<string>();
  carried: CarriedEgg[] = [];

  stats: Stats = {
    eggsStolen: 0, timesCaught: 0, petsHatched: 0, totalEarned: 0,
    distanceRun: 0, bestPetIncome: 0, playSeconds: 0,
  };

  /** Set while the player is standing on the treadmill. */
  training = false;

  private listeners: Listener[] = [];
  private rng = new Rng(Date.now() & 0xffffffff);
  private seed = Date.now() & 0xffffffff;
  /** Fractional money carried between frames so small incomes still pay out. */
  private moneyFraction = 0;

  // -- events ---------------------------------------------------------------

  on(listener: Listener): () => void {
    this.listeners.push(listener);
    return () => {
      const at = this.listeners.indexOf(listener);
      if (at >= 0) this.listeners.splice(at, 1);
    };
  }

  emit(event: GameEvent): void {
    for (const listener of this.listeners) listener(event);
  }

  notice(text: string, tone: 'info' | 'good' | 'bad' = 'info'): void {
    this.emit({ type: 'notice', text, tone });
  }

  // -- derived values -------------------------------------------------------

  get luck(): number {
    return luckValue(this.upgrades.luck, this.rebirths);
  }

  get incomeMultiplier(): number {
    return rebirthIncomeMultiplier(this.rebirths);
  }

  get pedestalSlots(): number {
    return pedestalCount(this.upgrades.pedestals);
  }

  get carryLimit(): number {
    return carryCapacity(this.upgrades.carry);
  }

  get carryDrag(): number {
    return carryPenaltyFactor(this.upgrades.carry);
  }

  get staminaMax(): number {
    return staminaSeconds(this.upgrades.stamina);
  }

  get jumpMultiplier(): number {
    return jumpFactor(this.upgrades.jump);
  }

  get trainingRatePerSecond(): number {
    return trainingRate(this.treadmillTier, this.trailTier);
  }

  get unlockedBiome(): BiomeDef {
    return highestUnlocked(this.speed);
  }

  isBiomeUnlocked(biome: BiomeId): boolean {
    const def = BIOME_BY_ID[biome];
    return def ? this.speed >= def.speedGate : false;
  }

  /** Income per second from every placed pet, after the rebirth multiplier. */
  get incomePerSecond(): number {
    let total = 0;
    for (const pet of this.pets) {
      if (pet.slot < 0 || pet.slot >= this.pedestalSlots) continue;
      total += this.petIncome(pet);
    }
    return total * this.incomeMultiplier;
  }

  petIncome(pet: OwnedPet): number {
    const def = PET_BY_ID[pet.petId];
    if (!def) return 0;
    return def.income * rollMultiplier(pet.size, pet.mutation);
  }

  /** Pets sitting in storage because there is no free pedestal. */
  get storedPets(): OwnedPet[] {
    return this.pets.filter((pet) => pet.slot < 0 || pet.slot >= this.pedestalSlots);
  }

  get placedPets(): OwnedPet[] {
    return this.pets.filter((pet) => pet.slot >= 0 && pet.slot < this.pedestalSlots);
  }

  firstFreeSlot(): number {
    const taken = new Set<number>();
    for (const pet of this.pets) if (pet.slot >= 0) taken.add(pet.slot);
    for (const egg of this.hatching) taken.add(egg.slot);
    for (let i = 0; i < this.pedestalSlots; i++) {
      if (!taken.has(i)) return i;
    }
    return -1;
  }

  // -- money ----------------------------------------------------------------

  addMoney(amount: number): void {
    if (amount <= 0) return;
    this.money += amount;
    this.stats.totalEarned += amount;
    this.emit({ type: 'money', amount, total: this.money });
  }

  spend(amount: number): boolean {
    if (this.money < amount) return false;
    this.money -= amount;
    return true;
  }

  // -- the steal / carry / deliver loop --------------------------------------

  /**
   * Roll what is inside a nest's egg at the moment it is taken.
   *
   * Rolling at steal time rather than hatch time matters: it means a run home
   * with a Titanic Rainbow already in your arms is genuinely at stake, and it
   * makes the result impossible to reroll by reloading a save.
   */
  rollEgg(biome: BiomeId): CarriedEgg | null {
    const def = BIOME_BY_ID[biome];
    if (!def) return null;
    const pool = petsOfBiome(biome);
    if (pool.length === 0) return null;

    const available = def.rarities.filter((rarity) =>
      pool.some((pet) => pet.rarity === rarity),
    );
    const rarity = available.length
      ? this.rng.pickWeighted(available, rarityWeights(this.luck, available))
      : (pool[0].rarity as RarityId);

    const candidates = pool.filter((pet) => pet.rarity === rarity);
    const pet = candidates.length ? this.rng.pick(candidates) : this.rng.pick(pool);
    const size = this.rng.pickWeighted(SIZE_ORDER, sizeWeights(this.luck));
    const mutation = this.rng.pickWeighted(MUTATION_ORDER, mutationWeights(this.luck));

    return {
      biome,
      petId: pet.id,
      size,
      mutation,
      weight: def.eggWeight * SIZES[size].scale,
    };
  }

  canCarryMore(): boolean {
    return this.carried.length < this.carryLimit;
  }

  takeEgg(biome: BiomeId): CarriedEgg | null {
    if (!this.canCarryMore()) return null;
    const egg = this.rollEgg(biome);
    if (!egg) return null;
    this.carried.push(egg);
    this.stats.eggsStolen++;
    this.emit({ type: 'stole', biome });
    return egg;
  }

  /** Called when a guardian catches the player. Returns the eggs dropped. */
  dropCarried(): CarriedEgg[] {
    const dropped = this.carried;
    this.carried = [];
    this.stats.timesCaught++;
    return dropped;
  }

  /**
   * Deliver carried eggs into free pedestals. Anything that does not fit is
   * kept in hand rather than destroyed, so a full base is an inconvenience and
   * not a punishment.
   */
  deliverCarried(): number {
    let placed = 0;
    const leftover: CarriedEgg[] = [];
    for (const egg of this.carried) {
      const slot = this.firstFreeSlot();
      if (slot < 0) {
        leftover.push(egg);
        continue;
      }
      const biome = BIOME_BY_ID[egg.biome];
      const total = hatchSeconds(biome ? biome.order : 0, this.upgrades.hatch);
      this.hatching.push({
        slot, petId: egg.petId, size: egg.size, mutation: egg.mutation,
        remaining: total, total,
      });
      this.emit({ type: 'delivered', egg, slot });
      placed++;
    }
    this.carried = leftover;
    if (leftover.length > 0) {
      this.notice('No free pedestal — buy more in the shop.', 'bad');
    }
    return placed;
  }

  // -- hatching -------------------------------------------------------------

  private hatch(egg: HatchingEgg): OwnedPet {
    const pet: OwnedPet = {
      uid: `p${++uidCounter}_${(this.rng.next() * 1e9) | 0}`,
      petId: egg.petId,
      size: egg.size,
      mutation: egg.mutation,
      slot: egg.slot,
      obtainedAt: this.stats.playSeconds,
    };
    this.pets.push(pet);
    this.stats.petsHatched++;
    const income = this.petIncome(pet);
    if (income > this.stats.bestPetIncome) this.stats.bestPetIncome = income;

    const isNew = !this.discovered.has(pet.petId);
    this.discovered.add(pet.petId);
    this.emit({ type: 'hatched', pet, isNew });
    return pet;
  }

  /** Skip the remaining wait on one egg (used by the "hurry" button). */
  rushHatch(slot: number): boolean {
    const egg = this.hatching.find((item) => item.slot === slot);
    if (!egg) return false;
    egg.remaining = 0;
    return true;
  }

  // -- shop -----------------------------------------------------------------

  buyUpgrade(id: UpgradeId): boolean {
    const level = this.upgrades[id];
    const spec = UPGRADES[id];
    if (level >= spec.maxLevel) return false;
    const cost = upgradeCostAt(id, level);
    if (!this.spend(cost)) return false;
    this.upgrades[id] = level + 1;
    this.emit({ type: 'upgrade', id, level: level + 1 });
    return true;
  }

  buyTreadmill(): boolean {
    const next = this.treadmillTier + 1;
    if (next >= TREADMILLS.length) return false;
    if (!this.spend(TREADMILLS[next].cost)) return false;
    this.treadmillTier = next;
    this.emit({ type: 'upgrade', id: 'treadmill', level: next });
    return true;
  }

  buyTrail(): boolean {
    const next = this.trailTier + 1;
    if (next >= TRAILS.length) return false;
    if (!this.spend(TRAILS[next].cost)) return false;
    this.trailTier = next;
    this.emit({ type: 'upgrade', id: 'trail', level: next });
    return true;
  }

  canRebirth(): boolean {
    return this.money >= rebirthCost(this.rebirths + 1);
  }

  rebirth(): boolean {
    if (!this.canRebirth()) return false;
    const next = this.rebirths + 1;
    const keptSpeed = this.speed * rebirthSpeedKeep(next);

    this.rebirths = next;
    this.money = 0;
    this.speed = keptSpeed;
    this.treadmillTier = 0;
    this.trailTier = 0;
    this.pets = [];
    this.hatching = [];
    this.carried = [];
    for (const id of Object.keys(this.upgrades) as UpgradeId[]) {
      // Pedestals are deliberately kept: losing your garden every rebirth
      // would make the prestige feel like a demotion rather than a reset.
      if (id !== 'pedestals') this.upgrades[id] = 0;
    }
    this.emit({ type: 'rebirth', count: next });
    return true;
  }

  // -- simulation -----------------------------------------------------------

  update(dt: number): void {
    this.stats.playSeconds += dt;

    const income = this.incomePerSecond * dt + this.moneyFraction;
    const whole = Math.floor(income);
    this.moneyFraction = income - whole;
    if (whole > 0) this.addMoney(whole);

    if (this.training) {
      const before = this.speed;
      this.speed += this.trainingRatePerSecond * dt;
      this.checkUnlocks(before);
    }

    for (let i = this.hatching.length - 1; i >= 0; i--) {
      const egg = this.hatching[i];
      egg.remaining -= dt;
      if (egg.remaining <= 0) {
        this.hatching.splice(i, 1);
        this.hatch(egg);
      }
    }
  }

  private checkUnlocks(previousSpeed: number): void {
    for (const biome of BIOMES) {
      if (previousSpeed < biome.speedGate && this.speed >= biome.speedGate) {
        this.emit({ type: 'biomeUnlocked', biome });
      }
    }
  }

  /** Grant income accrued while the tab was closed. */
  applyOffline(seconds: number): number {
    const capped = Math.min(seconds, 4 * 3600);
    const earned = Math.floor(this.incomePerSecond * capped * 0.35);
    if (earned > 0) this.addMoney(earned);
    return earned;
  }

  // -- display helpers ------------------------------------------------------

  displayName(pet: OwnedPet): string {
    const def = PET_BY_ID[pet.petId];
    return decoratedName(def ? def.name : pet.petId, pet.size, pet.mutation);
  }

  definition(pet: OwnedPet): PetDef | undefined {
    return PET_BY_ID[pet.petId];
  }

  get collectionProgress(): { found: number; total: number } {
    return { found: this.discovered.size, total: PETS.length };
  }

  rarityCounts(): Record<RarityId, number> {
    const counts = Object.fromEntries(
      RARITY_ORDER.map((id) => [id, 0]),
    ) as Record<RarityId, number>;
    for (const id of this.discovered) {
      const def = PET_BY_ID[id];
      if (def && counts[def.rarity as RarityId] !== undefined) {
        counts[def.rarity as RarityId]++;
      }
    }
    return counts;
  }

  // -- persistence ----------------------------------------------------------

  toSave(): SaveData {
    return {
      version: SAVE_VERSION,
      money: this.money,
      speed: this.speed,
      treadmillTier: this.treadmillTier,
      trailTier: this.trailTier,
      upgrades: { ...this.upgrades },
      rebirths: this.rebirths,
      pets: this.pets.map((pet) => ({ ...pet })),
      hatching: this.hatching.map((egg) => ({ ...egg })),
      discovered: [...this.discovered],
      stats: { ...this.stats },
      savedAt: Date.now(),
      seed: this.seed,
    };
  }

  load(data: SaveData): void {
    if (!data || typeof data !== 'object') return;
    this.money = Number(data.money) || 0;
    this.speed = Number(data.speed) || 0;
    this.treadmillTier = clampIndex(data.treadmillTier, TREADMILLS.length);
    this.trailTier = clampIndex(data.trailTier, TRAILS.length);
    this.rebirths = Number(data.rebirths) || 0;
    for (const id of Object.keys(this.upgrades) as UpgradeId[]) {
      const level = Number(data.upgrades?.[id]) || 0;
      this.upgrades[id] = Math.max(0, Math.min(level, UPGRADES[id].maxLevel));
    }
    // Drop any pet whose species no longer exists, so a roster change cannot
    // corrupt an old save.
    this.pets = (data.pets ?? []).filter((pet) => PET_BY_ID[pet.petId]);
    this.hatching = (data.hatching ?? []).filter((egg) => PET_BY_ID[egg.petId]);
    this.discovered = new Set((data.discovered ?? []).filter((id) => PET_BY_ID[id]));
    this.stats = { ...this.stats, ...(data.stats ?? {}) };
    this.seed = Number(data.seed) || this.seed;
    this.rng = new Rng(this.seed ^ 0x5bf03635);
    uidCounter = Math.max(uidCounter, this.pets.length + 1);
  }

  reset(): void {
    this.load({
      version: SAVE_VERSION, money: 0, speed: 0, treadmillTier: 0, trailTier: 0,
      upgrades: { pedestals: 0, luck: 0, hatch: 0, carry: 0, stamina: 0, jump: 0 },
      rebirths: 0, pets: [], hatching: [], discovered: [],
      stats: {
        eggsStolen: 0, timesCaught: 0, petsHatched: 0, totalEarned: 0,
        distanceRun: 0, bestPetIncome: 0, playSeconds: 0,
      },
      savedAt: Date.now(), seed: Date.now() & 0xffffffff,
    });
    this.carried = [];
  }

  /** Test seam: makes rolls reproducible. */
  setSeed(seed: number): void {
    this.seed = seed;
    this.rng = new Rng(seed);
  }
}

function clampIndex(value: unknown, length: number): number {
  const n = Number(value) || 0;
  return Math.max(0, Math.min(Math.floor(n), length - 1));
}

export { RARITIES, MUTATIONS, SIZES };
