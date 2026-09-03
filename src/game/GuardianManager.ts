import * as THREE from 'three';

import { Guardian, GuardianContext, GuardianState, NoiseEvent } from '@/ai/Guardian';
import { Assets } from '@/core/Assets';
import { ColliderWorld } from '@/core/Physics';
import { BiomeDef, BiomeId, guardianSpeedAt } from '@/data/biomes';
import { sprintSpeed } from '@/data/progression';
import { PET_BY_ID } from '@/data/pets';
import { PetAnimator } from '@/fx/PetAnimator';
import type { NestState } from '@/world/World';

/**
 * Every biome's guardian: its AI, its model, and the sleep/wake behaviour that
 * makes the theft a decision rather than a stealth puzzle.
 *
 * The reference game's guardian sleeps by its nest and wakes the instant you
 * lift the egg -- there is no detection meter, no sight cone, no sneaking. That
 * is a much better fit for first person than a stealth system would be: the
 * player is never punished for information they could not see, and the whole
 * encounter collapses into one clean question, "can I outrun this".
 *
 * The AI in ai/Guardian is still a full FSM because the extra states earn
 * their keep after the wake: search, leash and return are what let a guardian
 * lose you around a rock instead of magnetically tracking you home.
 */

export interface GuardianVisual {
  guardian: Guardian;
  model: THREE.Object3D;
  animator: PetAnimator;
  biome: BiomeDef;
  /** Set while asleep; the model slumps and the AI ignores the player. */
  asleep: boolean;
  /** Seconds since waking, used for the roar and the wake animation. */
  awakeFor: number;
}

export interface GuardianEvents {
  onWake?: (visual: GuardianVisual) => void;
  onCatch?: (visual: GuardianVisual) => void;
  onStateChange?: (visual: GuardianVisual, from: GuardianState, to: GuardianState) => void;
  onFootstep?: (visual: GuardianVisual) => void;
}

export class GuardianManager {
  readonly guardians = new Map<BiomeId, GuardianVisual>();
  events: GuardianEvents = {};

  private noises: NoiseEvent[] = [];

  constructor(
    private readonly scene: THREE.Object3D,
    private readonly colliders: ColliderWorld,
    private readonly assets: Assets,
  ) {}

  spawn(nests: Map<BiomeId, NestState>): void {
    for (const [id, nest] of nests) {
      const biome = nest.biome;
      const guardian = new Guardian(nest.info.guardianHome, biome.guardianTier, this.colliders);
      guardian.setPatrolRing(7.5, 5, biome.bearing);

      // Guardians are giant versions of their biome's signature pet, so the
      // thing chasing you is something you can eventually own.
      const petDef = PET_BY_ID[biome.guardianPet];
      const model = this.assets.instantiate(
        petDef ? petDef.model : `models/pets/${biome.guardianPet}.glb`,
      );
      model.scale.setScalar(biome.guardianScale);
      model.position.copy(nest.info.guardianHome);
      model.name = `guardian:${id}`;
      this.scene.add(model);

      const animator = new PetAnimator(model, {
        gait: 'walk',
        energy: 0.7,
        bounce: 0.02,
        curiosity: 0.05,
        waggle: 0.18,
      }, biome.order * 37);

      const visual: GuardianVisual = {
        guardian, model, animator, biome, asleep: true, awakeFor: 0,
      };

      guardian.events = {
        onCatch: () => this.events.onCatch?.(visual),
        onStateChange: (from, to) => this.events.onStateChange?.(visual, from, to),
        onFootstep: () => this.events.onFootstep?.(visual),
      };

      this.guardians.set(id, visual);
    }
  }

  get(biome: BiomeId): GuardianVisual | undefined {
    return this.guardians.get(biome);
  }

  /** Raise a noise the guardians can hear this frame. */
  addNoise(position: THREE.Vector3, loudness: number): void {
    this.noises.push({ position: position.clone(), loudness });
  }

  /** Wake a guardian: the egg has been taken. */
  wake(biome: BiomeId): void {
    const visual = this.guardians.get(biome);
    if (!visual || !visual.asleep) return;
    visual.asleep = false;
    visual.awakeFor = 0;
    visual.guardian.awareness = 1;
    visual.animator.personality.energy = 1.6;
    this.events.onWake?.(visual);
  }

  /** Send every guardian home and back to sleep -- used by nightfall. */
  sleepAll(): void {
    for (const visual of this.guardians.values()) {
      visual.asleep = true;
      visual.awakeFor = 0;
      visual.animator.personality.energy = 0.7;
      visual.guardian.reset();
    }
  }

  sleep(biome: BiomeId): void {
    const visual = this.guardians.get(biome);
    if (!visual) return;
    visual.asleep = true;
    visual.awakeFor = 0;
    visual.animator.personality.energy = 0.7;
    visual.guardian.reset();
  }

  update(
    dt: number,
    playerPosition: THREE.Vector3,
    options: {
      crouching: boolean;
      /** Biome whose egg the player is currently carrying, if any. */
      carryingFrom: BiomeId[];
      /** Guardians never pursue into the safe zone. */
      playerSafe: boolean;
      /** Speed-derived difficulty scaling for this player. */
      difficultyFor: (biome: BiomeDef) => number;
      /** The player's un-upgraded sprint speed, for resolving guardian pace. */
      baseSprintSpeed: number;
    },
  ): void {
    for (const [id, visual] of this.guardians) {
      visual.guardian.difficulty = options.difficultyFor(visual.biome);
      // Resolve the chase speed from the player's sprint at this biome's gate,
      // so a guardian is always a shade slower than a just-qualified player
      // however the movement curve is later retuned. The tier table then only
      // has to describe *behaviour*, never pace.
      visual.guardian.tuning.chaseSpeed = guardianSpeedAt(
        visual.biome, sprintSpeed(visual.biome.speedGate, options.baseSprintSpeed),
      );

      const holdingMine = options.carryingFrom.includes(id);
      const disabled = visual.asleep || options.playerSafe;

      const ctx: GuardianContext = {
        playerPosition,
        playerHasMyEgg: holdingMine && !options.playerSafe,
        playerCrouching: options.crouching,
        noises: this.noises,
        disabled,
      };

      visual.guardian.update(dt, ctx);

      if (!visual.asleep) {
        visual.awakeFor += dt;
        // Once the player is home and the guardian has drifted back to its
        // nest, it lies down again and the biome resets to its calm state.
        if (
          visual.guardian.state === 'patrol' &&
          !holdingMine &&
          visual.awakeFor > 6 &&
          visual.guardian.position.distanceTo(visual.guardian.home) < 4
        ) {
          this.sleep(id);
        }
      }

      this.syncModel(visual, dt, playerPosition);
    }

    this.noises.length = 0;
  }

  private syncModel(visual: GuardianVisual, dt: number, playerPosition: THREE.Vector3): void {
    const { guardian, model, animator } = visual;
    model.position.set(guardian.position.x, guardian.position.y, guardian.position.z);

    // Models face +Y in Blender, which the exporter turns into -Z; three.js
    // rotates about Y from that same axis, so facing maps across directly.
    const targetYaw = guardian.facing;
    let delta = targetYaw - model.rotation.y;
    while (delta > Math.PI) delta -= Math.PI * 2;
    while (delta < -Math.PI) delta += Math.PI * 2;
    model.rotation.y += delta * Math.min(1, dt * 8);

    if (visual.asleep) {
      // A slumped, slowly breathing pose reads as asleep from any angle, and
      // it is the only cue the player gets that a nest is currently safe.
      model.rotation.z = 0.12;
      animator.moveSpeed = 0;
      animator.personality.energy = 0.45;
      animator.lookAt(null);
    } else {
      model.rotation.z *= Math.max(0, 1 - dt * 4);
      animator.moveSpeed = Math.hypot(guardian.velocity.x, guardian.velocity.z);
      animator.personality.energy = guardian.state === 'chase' ? 2.2 : 1.1;
      // While chasing, the guardian's head tracks the player. In first person
      // you often only glimpse it in a turn, and the head-turn is what makes
      // that glimpse land.
      animator.lookAt(guardian.state === 'chase' ? playerPosition : null);
      if (guardian.state === 'chase') animator.celebrate(dt * 0.6);
    }

    animator.update(dt);
  }

  /** The highest threat any guardian currently poses, 0..1. */
  get threat(): number {
    let max = 0;
    for (const visual of this.guardians.values()) {
      if (visual.asleep) continue;
      max = Math.max(max, visual.guardian.threat);
    }
    return max;
  }

  /** The nearest actively-chasing guardian, for the danger indicator. */
  nearestChaser(from: THREE.Vector3): GuardianVisual | null {
    let best: GuardianVisual | null = null;
    let bestDistance = Infinity;
    for (const visual of this.guardians.values()) {
      if (visual.asleep) continue;
      if (visual.guardian.state !== 'chase' && visual.guardian.state !== 'search') continue;
      const distance = visual.guardian.position.distanceTo(from);
      if (distance < bestDistance) {
        bestDistance = distance;
        best = visual;
      }
    }
    return best;
  }

  dispose(): void {
    for (const visual of this.guardians.values()) {
      visual.model.removeFromParent();
    }
    this.guardians.clear();
  }
}
