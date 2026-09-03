import * as THREE from 'three';

import { Assets, tintInstance } from '@/core/Assets';
import { PET_BY_ID } from '@/data/pets';
import { MUTATIONS, RARITIES, SIZES } from '@/data/rarity';
import { PetAnimator } from '@/fx/PetAnimator';
import type { Pedestal } from '@/world/SafeZone';

import type { GameState, HatchingEgg, OwnedPet } from './GameState';

/**
 * The garden: the pets standing on your pedestals, and the eggs cracking open
 * on the empty ones.
 *
 * This is the reward surface of the entire game, so it gets more care than its
 * mechanical importance suggests. A pet on a pedestal breathes, looks at you
 * as you walk past, and celebrates when it pays out. Rarity, size and mutation
 * are all readable from across the courtyard -- aura ring, physical scale, and
 * a tint on the model itself -- because the fantasy is *displaying* a
 * collection, not owning a spreadsheet.
 */

interface PedestalEntry {
  pedestal: Pedestal;
  petUid: string | null;
  model: THREE.Object3D | null;
  animator: PetAnimator | null;
  aura: THREE.Mesh | null;
  eggModel: THREE.Object3D | null;
  /** Hue cycle phase for animated mutations. */
  huePhase: number;
  hueMaterials: THREE.MeshStandardMaterial[];
}

export class PetGarden {
  private entries: PedestalEntry[] = [];
  private readonly group = new THREE.Group();
  private lookTarget: THREE.Vector3 | null = null;

  constructor(
    scene: THREE.Object3D,
    private readonly assets: Assets,
    private readonly state: GameState,
  ) {
    this.group.name = 'garden';
    scene.add(this.group);
  }

  setPedestals(pedestals: Pedestal[]): void {
    this.entries = pedestals.map((pedestal) => ({
      pedestal,
      petUid: null,
      model: null,
      animator: null,
      aura: null,
      eggModel: null,
      huePhase: pedestal.index * 0.37,
      hueMaterials: [],
    }));
  }

  /** Called whenever placement changes: hatch, rebirth, pedestal purchase. */
  sync(): void {
    const bySlot = new Map<number, OwnedPet>();
    for (const pet of this.state.pets) {
      if (pet.slot >= 0) bySlot.set(pet.slot, pet);
    }
    const eggsBySlot = new Map<number, HatchingEgg>();
    for (const egg of this.state.hatching) eggsBySlot.set(egg.slot, egg);

    const unlocked = this.state.pedestalSlots;

    for (const entry of this.entries) {
      const index = entry.pedestal.index;
      const available = index < unlocked;
      const pet = available ? bySlot.get(index) : undefined;
      const egg = available ? eggsBySlot.get(index) : undefined;

      if (!available) {
        this.clearPet(entry);
        this.clearEgg(entry);
        continue;
      }

      if (pet && pet.uid !== entry.petUid) {
        this.clearPet(entry);
        this.clearEgg(entry);
        this.spawnPet(entry, pet);
      } else if (!pet && entry.petUid) {
        this.clearPet(entry);
      }

      if (egg && !entry.eggModel) {
        this.clearPet(entry);
        this.spawnEgg(entry, egg);
      } else if (!egg && entry.eggModel) {
        this.clearEgg(entry);
      }
    }
  }

  private spawnPet(entry: PedestalEntry, pet: OwnedPet): void {
    const def = PET_BY_ID[pet.petId];
    if (!def) return;

    const model = this.assets.instantiate(def.model);
    const scale = def.scale * SIZES[pet.size].scale * 1.15;
    model.scale.setScalar(scale);
    model.position.copy(entry.pedestal.petAnchor);
    // Face the middle of the courtyard, so a full garden looks like an
    // audience rather than a car park.
    model.rotation.y = Math.atan2(
      -entry.pedestal.position.x, -entry.pedestal.position.z,
    ) + Math.PI;
    model.name = `pet:${pet.uid}`;
    this.group.add(model);

    const mutation = MUTATIONS[pet.mutation];
    entry.hueMaterials = [];
    if (mutation.tint) {
      tintInstance(model, (material) => {
        if (mutation.id === 'gold' || mutation.id === 'diamond') {
          // Metallic mutations recolour toward the tint but keep the pet's own
          // value structure, so a Gold Fox still reads as a fox.
          material.color.lerp(new THREE.Color(mutation.tint!), 0.72);
          material.metalness = mutation.id === 'gold' ? 0.85 : 0.4;
          material.roughness = mutation.id === 'gold' ? 0.25 : 0.12;
        } else {
          material.color.lerp(new THREE.Color(mutation.tint!), 0.45);
        }
        material.emissive = new THREE.Color(mutation.tint!);
        material.emissiveIntensity = mutation.emissive;
        if (mutation.animated) entry.hueMaterials.push(material);
      });
    }

    const rarity = RARITIES[def.rarity];
    if (rarity.aura > 0.05) {
      const aura = new THREE.Mesh(
        new THREE.RingGeometry(0.7, 0.98, 28),
        new THREE.MeshBasicMaterial({
          color: new THREE.Color(rarity.glow),
          transparent: true,
          opacity: 0.28 + rarity.aura * 0.42,
          side: THREE.DoubleSide,
          depthWrite: false,
        }),
      );
      aura.rotation.x = -Math.PI / 2;
      aura.position.copy(entry.pedestal.petAnchor).add(new THREE.Vector3(0, 0.04, 0));
      aura.renderOrder = 2;
      this.group.add(aura);
      entry.aura = aura;
    }

    entry.model = model;
    entry.petUid = pet.uid;
    entry.animator = new PetAnimator(
      model,
      { ...def.personality },
      Math.abs(hashString(pet.uid)),
    );
    entry.animator.celebrate(1.2);
  }

  private spawnEgg(entry: PedestalEntry, egg: HatchingEgg): void {
    const def = PET_BY_ID[egg.petId];
    const biome = def ? def.biome : 'forest';
    const model = this.assets.instantiate(`models/props/egg-${biome}.glb`);
    model.scale.setScalar(1.1 * SIZES[egg.size].scale);
    model.position.copy(entry.pedestal.petAnchor);
    model.name = `egg:${entry.pedestal.index}`;
    this.group.add(model);
    entry.eggModel = model;
  }

  private clearPet(entry: PedestalEntry): void {
    if (entry.model) {
      this.group.remove(entry.model);
      entry.model = null;
    }
    if (entry.aura) {
      this.group.remove(entry.aura);
      entry.aura.geometry.dispose();
      (entry.aura.material as THREE.Material).dispose();
      entry.aura = null;
    }
    entry.animator = null;
    entry.petUid = null;
    entry.hueMaterials = [];
  }

  private clearEgg(entry: PedestalEntry): void {
    if (!entry.eggModel) return;
    this.group.remove(entry.eggModel);
    entry.eggModel = null;
  }

  /** Point every pet's head at the player when they are close enough to notice. */
  setLookTarget(position: THREE.Vector3 | null): void {
    this.lookTarget = position;
  }

  /** Spike one pedestal's pet — used on payout ticks and on hatch. */
  celebrate(slot: number, strength = 1): void {
    const entry = this.entries.find((item) => item.pedestal.index === slot);
    entry?.animator?.celebrate(strength);
  }

  update(dt: number, time: number): void {
    const eggsBySlot = new Map<number, HatchingEgg>();
    for (const egg of this.state.hatching) eggsBySlot.set(egg.slot, egg);

    for (const entry of this.entries) {
      if (entry.animator) {
        const distance = this.lookTarget
          ? entry.pedestal.petAnchor.distanceTo(this.lookTarget)
          : Infinity;
        entry.animator.lookAt(distance < 9 ? this.lookTarget : null);
        entry.animator.update(dt);
      }

      if (entry.aura) {
        const material = entry.aura.material as THREE.MeshBasicMaterial;
        material.opacity = 0.22 + Math.sin(time * 1.6 + entry.huePhase * 6) * 0.08 + 0.16;
        entry.aura.rotation.z += dt * 0.4;
      }

      // Rainbow and Void mutations cycle hue rather than sitting on one tint,
      // which is what makes them read as special from across the garden.
      if (entry.hueMaterials.length > 0) {
        const hue = (time * 0.16 + entry.huePhase) % 1;
        for (const material of entry.hueMaterials) {
          material.emissive.setHSL(hue, 0.85, 0.55);
        }
      }

      if (entry.eggModel) {
        const egg = eggsBySlot.get(entry.pedestal.index);
        if (egg) {
          // Wobble harder as the hatch approaches: the pedestal itself is the
          // progress bar, so the player never needs to open a menu to check.
          const progress = 1 - egg.remaining / Math.max(0.001, egg.total);
          const wobble = 0.04 + progress * 0.22;
          entry.eggModel.rotation.z = Math.sin(time * (5 + progress * 16)) * wobble;
          entry.eggModel.rotation.x = Math.cos(time * (4 + progress * 13)) * wobble * 0.6;
          entry.eggModel.position.y =
            entry.pedestal.petAnchor.y + Math.abs(Math.sin(time * (3 + progress * 9))) * progress * 0.12;
        }
      }
    }
  }

  dispose(): void {
    for (const entry of this.entries) {
      this.clearPet(entry);
      this.clearEgg(entry);
    }
    this.group.removeFromParent();
  }
}

function hashString(value: string): number {
  let hash = 0;
  for (let i = 0; i < value.length; i++) {
    hash = (Math.imul(hash, 31) + value.charCodeAt(i)) | 0;
  }
  return hash;
}
