import * as THREE from 'three';

import type { ColliderWorld } from '@/core/Physics';

/**
 * Guardian AI.
 *
 * The whole game is a risk curve, and this class is the risk. It is a small
 * finite state machine deliberately kept legible rather than clever, because
 * the player must be able to build a mental model of it: "it saw me", "it
 * heard that", "it lost me, hold still". An unpredictable chaser in first
 * person just feels unfair.
 *
 * First person forces two departures from the third-person original:
 *
 *  - The player cannot see behind them, so a guardian must *announce* every
 *    state change with a sound. `onStateChange` exists for that.
 *  - The player cannot judge closing distance over their shoulder, so
 *    `threat` is published as a 0..1 value that drives heartbeat, vignette and
 *    a directional damage-style indicator.
 */

export type GuardianState =
  | 'patrol'
  | 'alert'
  | 'chase'
  | 'search'
  | 'return'
  | 'stunned'
  | 'feeding';

export interface GuardianTuning {
  patrolSpeed: number;
  chaseSpeed: number;
  /** Degrees, full cone width. */
  visionAngle: number;
  visionRange: number;
  /** Sees you regardless of angle inside this radius. */
  proximityRange: number;
  /** How far a noise carries to this guardian. */
  hearingRange: number;
  /** Seconds of continuous sight before it commits to a chase. */
  detectTime: number;
  /** Seconds it keeps hunting after losing sight. */
  searchTime: number;
  /** Distance at which the player is caught. */
  catchRadius: number;
  /** How far it will stray from its nest before giving up. */
  leash: number;
  /** Seconds it is disabled after being stunned. */
  stunDuration: number;
  /** Turn rate, radians per second. */
  turnRate: number;
  /** Extra speed while the player carries this guardian's egg. */
  enragedSpeedBonus: number;
}

export const GUARDIAN_TIERS: Record<string, GuardianTuning> = {
  // Tier tuning is deliberately coarse. What escalates across biomes is mostly
  // speed and vision; adding new *mechanics* per biome would outpace the
  // player's ability to learn them.
  drowsy: {
    patrolSpeed: 2.0, chaseSpeed: 6.4, visionAngle: 90, visionRange: 16,
    proximityRange: 3.5, hearingRange: 12, detectTime: 0.75, searchTime: 4,
    catchRadius: 1.5, leash: 42, stunDuration: 6, turnRate: 2.4,
    enragedSpeedBonus: 0.6,
  },
  watchful: {
    patrolSpeed: 2.6, chaseSpeed: 8.2, visionAngle: 105, visionRange: 22,
    proximityRange: 4.5, hearingRange: 16, detectTime: 0.55, searchTime: 6,
    catchRadius: 1.6, leash: 55, stunDuration: 5.5, turnRate: 3.0,
    enragedSpeedBonus: 0.9,
  },
  fierce: {
    patrolSpeed: 3.2, chaseSpeed: 10.1, visionAngle: 120, visionRange: 28,
    proximityRange: 5.5, hearingRange: 21, detectTime: 0.4, searchTime: 8,
    catchRadius: 1.7, leash: 70, stunDuration: 5, turnRate: 3.6,
    enragedSpeedBonus: 1.2,
  },
  relentless: {
    patrolSpeed: 3.8, chaseSpeed: 12.4, visionAngle: 140, visionRange: 34,
    proximityRange: 7, hearingRange: 26, detectTime: 0.28, searchTime: 11,
    catchRadius: 1.9, leash: 90, stunDuration: 4.5, turnRate: 4.4,
    enragedSpeedBonus: 1.6,
  },
  apex: {
    patrolSpeed: 4.4, chaseSpeed: 14.6, visionAngle: 160, visionRange: 42,
    proximityRange: 9, hearingRange: 32, detectTime: 0.18, searchTime: 14,
    catchRadius: 2.1, leash: 120, stunDuration: 4, turnRate: 5.2,
    enragedSpeedBonus: 2.0,
  },
};

export interface NoiseEvent {
  position: THREE.Vector3;
  /** Effective radius in world units. */
  loudness: number;
}

export interface GuardianContext {
  playerPosition: THREE.Vector3;
  /** True while the player is holding an egg from this guardian's nest. */
  playerHasMyEgg: boolean;
  /** Crouching player is much harder to see and hear. */
  playerCrouching: boolean;
  /** Noises raised this frame by anything in the world. */
  noises: NoiseEvent[];
  /** Set true to make the guardian ignore the player (safe zone, tutorial). */
  disabled: boolean;
}

export interface GuardianEvents {
  onStateChange?: (from: GuardianState, to: GuardianState, guardian: Guardian) => void;
  onCatch?: (guardian: Guardian) => void;
  /** Emitted on each footfall so the audio system can pan it. */
  onFootstep?: (guardian: Guardian) => void;
}

const UP = new THREE.Vector3(0, 1, 0);

export class Guardian {
  readonly position = new THREE.Vector3();
  readonly velocity = new THREE.Vector3();
  /** Facing, radians. Separate from velocity so it can turn without sliding. */
  facing = 0;

  state: GuardianState = 'patrol';
  tuning: GuardianTuning;
  events: GuardianEvents = {};

  /** 0..1 — how close this guardian is to catching the player right now. */
  threat = 0;
  /** 0..1 detection meter; reaching 1 in `alert` commits to a chase. */
  awareness = 0;

  /** The nest this guardian defends; it always returns here. */
  readonly home = new THREE.Vector3();
  /** Extra difficulty multiplier applied by biome tier and player progress. */
  difficulty = 1;

  private waypoints: THREE.Vector3[] = [];
  private waypointIndex = 0;
  private stateTimer = 0;
  private lastKnown = new THREE.Vector3();
  private stunTimer = 0;
  private footstepAccumulator = 0;
  private idleTimer = 0;
  private scratch = new THREE.Vector3();

  constructor(
    home: THREE.Vector3,
    tier: keyof typeof GUARDIAN_TIERS,
    private readonly world: ColliderWorld,
  ) {
    this.home.copy(home);
    this.position.copy(home);
    this.tuning = { ...GUARDIAN_TIERS[tier] };
    this.lastKnown.copy(home);
  }

  /** A ring of patrol points around the nest. */
  setPatrolRing(radius: number, count = 6, seedAngle = 0): void {
    this.waypoints = [];
    for (let i = 0; i < count; i++) {
      const angle = seedAngle + (i / count) * Math.PI * 2;
      this.waypoints.push(
        new THREE.Vector3(
          this.home.x + Math.cos(angle) * radius,
          this.home.y,
          this.home.z + Math.sin(angle) * radius,
        ),
      );
    }
  }

  setPatrolPath(points: THREE.Vector3[]): void {
    this.waypoints = points.map((p) => p.clone());
    this.waypointIndex = 0;
  }

  stun(seconds = this.tuning.stunDuration): void {
    this.stunTimer = seconds;
    this.transition('stunned');
    this.velocity.set(0, 0, 0);
  }

  reset(): void {
    this.position.copy(this.home);
    this.velocity.set(0, 0, 0);
    this.awareness = 0;
    this.threat = 0;
    this.transition('patrol');
  }

  get speed(): number {
    const base = this.state === 'chase' ? this.tuning.chaseSpeed : this.tuning.patrolSpeed;
    return base * this.difficulty;
  }

  update(dt: number, ctx: GuardianContext): void {
    this.stateTimer += dt;

    if (this.stunTimer > 0) {
      this.stunTimer -= dt;
      this.velocity.multiplyScalar(Math.max(0, 1 - dt * 6));
      this.integrate(dt);
      this.threat = 0;
      if (this.stunTimer <= 0) this.transition('return');
      return;
    }

    if (ctx.disabled) {
      this.awareness = Math.max(0, this.awareness - dt);
      if (this.state !== 'patrol' && this.state !== 'return') this.transition('return');
    } else {
      this.sense(dt, ctx);
    }

    switch (this.state) {
      case 'patrol':
        this.doPatrol(dt);
        break;
      case 'alert':
        this.doAlert(dt);
        break;
      case 'chase':
        this.doChase(dt, ctx);
        break;
      case 'search':
        this.doSearch(dt);
        break;
      case 'return':
        this.doReturn(dt);
        break;
      case 'feeding':
        this.doFeeding(dt);
        break;
      default:
        break;
    }

    this.integrate(dt);
    this.updateThreat(ctx);
  }

  // ---- senses --------------------------------------------------------------

  private sense(dt: number, ctx: GuardianContext): void {
    const sees = this.canSee(ctx.playerPosition, ctx.playerCrouching);
    const heard = this.hears(ctx);

    if (sees) {
      // A guardian whose egg is being carried locks on immediately: the theft
      // itself is the alarm, so there is no stealthy escape once you commit.
      const rate = ctx.playerHasMyEgg ? 4 : 1 / Math.max(0.05, this.tuning.detectTime);
      this.awareness = Math.min(1, this.awareness + dt * rate);
      this.lastKnown.copy(ctx.playerPosition);
    } else if (heard) {
      this.awareness = Math.min(0.85, this.awareness + dt * 1.4);
      this.lastKnown.copy(heard);
    } else {
      const decay = this.state === 'chase' ? 0.45 : 0.8;
      this.awareness = Math.max(0, this.awareness - dt * decay);
    }

    if (ctx.playerHasMyEgg && this.state !== 'chase') {
      this.lastKnown.copy(ctx.playerPosition);
      this.transition('chase');
      return;
    }

    if (this.awareness >= 1 && this.state !== 'chase') {
      this.transition('chase');
    } else if (this.awareness > 0.15 && (this.state === 'patrol' || this.state === 'return')) {
      this.transition('alert');
    } else if (this.state === 'chase' && !sees && this.awareness <= 0.3) {
      this.transition('search');
    }
  }

  private canSee(target: THREE.Vector3, crouching: boolean): boolean {
    const toTarget = this.scratch.copy(target).sub(this.position);
    toTarget.y = 0;
    const distance = toTarget.length();

    let range = this.tuning.visionRange * this.difficulty;
    let proximity = this.tuning.proximityRange;
    if (crouching) {
      range *= 0.55;
      proximity *= 0.6;
    }
    if (distance > range) return false;
    if (distance > proximity) {
      toTarget.normalize();
      const facingVec = this.scratch.clone().set(Math.sin(this.facing), 0, Math.cos(this.facing));
      const cos = toTarget.dot(facingVec);
      const halfAngle = Math.cos((this.tuning.visionAngle * 0.5 * Math.PI) / 180);
      if (cos < halfAngle) return false;
    }
    return this.hasLineOfSight(target);
  }

  private hasLineOfSight(target: THREE.Vector3): boolean {
    const from = this.position.clone().setY(this.position.y + 1.1);
    const to = target.clone().setY(target.y + 0.9);
    const direction = to.clone().sub(from);
    const distance = direction.length();
    if (distance < 0.01) return true;
    direction.divideScalar(distance);
    const hit = this.world.raycast(from, direction, distance - 0.2);
    return hit === null;
  }

  private hears(ctx: GuardianContext): THREE.Vector3 | null {
    const range = this.tuning.hearingRange * this.difficulty * (ctx.playerCrouching ? 0.5 : 1);
    let best: THREE.Vector3 | null = null;
    let bestDistance = Infinity;
    for (const noise of ctx.noises) {
      const distance = this.position.distanceTo(noise.position);
      if (distance > Math.min(range, noise.loudness)) continue;
      if (distance < bestDistance) {
        bestDistance = distance;
        best = noise.position;
      }
    }
    return best;
  }

  // ---- behaviours ----------------------------------------------------------

  private doPatrol(dt: number): void {
    if (this.waypoints.length === 0) {
      this.faceTowards(this.home.x + Math.sin(this.stateTimer * 0.4) * 5,
        this.home.z + Math.cos(this.stateTimer * 0.4) * 5, dt);
      this.velocity.set(0, 0, 0);
      return;
    }
    const target = this.waypoints[this.waypointIndex];
    if (this.position.distanceTo(target) < 1.4) {
      this.waypointIndex = (this.waypointIndex + 1) % this.waypoints.length;
      // Pausing at each waypoint gives the player a readable window to move.
      this.idleTimer = 0.9 + (this.waypointIndex % 3) * 0.4;
    }
    if (this.idleTimer > 0) {
      this.idleTimer -= dt;
      this.velocity.multiplyScalar(Math.max(0, 1 - dt * 8));
      return;
    }
    this.steerTowards(target, this.speed, dt);
  }

  private doAlert(dt: number): void {
    // Stop, turn to look. This is the player's cue to break line of sight.
    this.velocity.multiplyScalar(Math.max(0, 1 - dt * 5));
    this.faceTowards(this.lastKnown.x, this.lastKnown.z, dt);
    if (this.awareness <= 0.02) this.transition('return');
  }

  private doChase(dt: number, ctx: GuardianContext): void {
    const strayed = this.position.distanceTo(this.home) > this.tuning.leash * this.difficulty;
    if (strayed && !ctx.playerHasMyEgg) {
      this.transition('return');
      return;
    }
    let speed = this.speed;
    if (ctx.playerHasMyEgg) speed += this.tuning.enragedSpeedBonus;
    this.steerTowards(this.lastKnown, speed, dt);

    if (this.position.distanceTo(ctx.playerPosition) < this.tuning.catchRadius) {
      this.events.onCatch?.(this);
      this.transition('feeding');
    }
  }

  private doSearch(dt: number): void {
    if (this.stateTimer > this.tuning.searchTime) {
      this.transition('return');
      return;
    }
    // Sweep outward from the last known position rather than standing on it:
    // circling is what gives a hidden player a reason to keep holding still.
    const sweep = this.stateTimer * 1.6;
    const radius = 2 + this.stateTimer * 1.1;
    const target = this.scratch.set(
      this.lastKnown.x + Math.cos(sweep) * radius,
      this.position.y,
      this.lastKnown.z + Math.sin(sweep) * radius,
    );
    this.steerTowards(target, this.tuning.patrolSpeed * 1.4 * this.difficulty, dt);
  }

  private doReturn(dt: number): void {
    const target = this.waypoints.length > 0
      ? this.waypoints[this.waypointIndex]
      : this.home;
    if (this.position.distanceTo(target) < 1.6) {
      this.transition('patrol');
      return;
    }
    this.steerTowards(target, this.tuning.patrolSpeed * 1.2 * this.difficulty, dt);
  }

  private doFeeding(dt: number): void {
    // A short cooldown after a catch so the player gets a clean restart rather
    // than being immediately re-grabbed at the respawn point.
    this.velocity.multiplyScalar(Math.max(0, 1 - dt * 4));
    if (this.stateTimer > 2.2) {
      this.awareness = 0;
      this.transition('return');
    }
  }

  // ---- motion --------------------------------------------------------------

  private steerTowards(target: THREE.Vector3, speed: number, dt: number): void {
    const desired = this.scratch.copy(target).sub(this.position);
    desired.y = 0;
    const distance = desired.length();
    if (distance < 0.001) return;
    desired.divideScalar(distance).multiplyScalar(speed);

    // Accelerate toward the desired velocity rather than snapping to it, so a
    // guardian rounding a corner overshoots slightly and can be juked.
    const responsiveness = Math.min(1, dt * 5.5);
    this.velocity.x += (desired.x - this.velocity.x) * responsiveness;
    this.velocity.z += (desired.z - this.velocity.z) * responsiveness;
    this.faceTowards(target.x, target.z, dt);
    this.avoidObstacles(dt);
  }

  /**
   * Cheap whisker avoidance. Real navmesh pathing is overkill for open biomes
   * with sparse cover, but a chaser that grinds into a rock forever looks
   * broken, so two feelers are enough to slide around it.
   */
  private avoidObstacles(dt: number): void {
    const speed = Math.hypot(this.velocity.x, this.velocity.z);
    if (speed < 0.2) return;
    const dir = new THREE.Vector3(this.velocity.x / speed, 0, this.velocity.z / speed);
    const origin = this.position.clone().setY(this.position.y + 0.9);
    const ahead = 2.4;

    for (const sign of [-1, 1]) {
      const angle = sign * 0.42;
      const probe = new THREE.Vector3(
        dir.x * Math.cos(angle) - dir.z * Math.sin(angle),
        0,
        dir.x * Math.sin(angle) + dir.z * Math.cos(angle),
      );
      const hit = this.world.raycast(origin, probe, ahead);
      if (hit) {
        const push = new THREE.Vector3().crossVectors(UP, probe).multiplyScalar(-sign);
        const strength = (1 - hit.distance / ahead) * speed * 3.2 * dt * 6;
        this.velocity.addScaledVector(push, strength);
      }
    }
  }

  private faceTowards(x: number, z: number, dt: number): void {
    const desired = Math.atan2(x - this.position.x, z - this.position.z);
    let delta = desired - this.facing;
    while (delta > Math.PI) delta -= Math.PI * 2;
    while (delta < -Math.PI) delta += Math.PI * 2;
    const maxTurn = this.tuning.turnRate * dt;
    this.facing += THREE.MathUtils.clamp(delta, -maxTurn, maxTurn);
  }

  private integrate(dt: number): void {
    const speed = Math.hypot(this.velocity.x, this.velocity.z);
    if (speed > 0.01) {
      const next = this.position.clone().addScaledVector(this.velocity, dt);
      // Guardians are ground-bound; clamp them to whatever is underfoot rather
      // than running a second physics body.
      const probe = this.world.raycast(
        next.clone().setY(next.y + 1.6),
        new THREE.Vector3(0, -1, 0),
        4.5,
      );
      if (probe) next.y = next.y + 1.6 - probe.distance;
      const blocked = this.world.raycast(
        this.position.clone().setY(this.position.y + 0.9),
        new THREE.Vector3(this.velocity.x / speed, 0, this.velocity.z / speed),
        0.75,
      );
      if (!blocked) this.position.copy(next);
      else this.velocity.multiplyScalar(0.35);

      this.footstepAccumulator += speed * dt;
      if (this.footstepAccumulator > 1.9) {
        this.footstepAccumulator = 0;
        this.events.onFootstep?.(this);
      }
    }
  }

  private updateThreat(ctx: GuardianContext): void {
    if (this.state !== 'chase' && this.state !== 'search') {
      this.threat = Math.max(this.threat - 0.02, this.awareness * 0.35);
      return;
    }
    const distance = this.position.distanceTo(ctx.playerPosition);
    const danger = THREE.MathUtils.clamp(1 - distance / 26, 0, 1);
    this.threat = this.state === 'chase' ? Math.max(danger, 0.35) : danger * 0.5;
  }

  private transition(next: GuardianState): void {
    if (this.state === next) return;
    const previous = this.state;
    this.state = next;
    this.stateTimer = 0;
    this.events.onStateChange?.(previous, next, this);
  }
}
