import * as THREE from 'three';

/**
 * Procedural animation for pets, driven entirely by node names.
 *
 * Rigging and hand-animating ~100 creatures is not a sensible use of the
 * modelling budget, and skinned meshes would cost far more at runtime with 40
 * pets on screen. Instead each model exports a fixed set of named parts and
 * this animator rotates whichever ones exist. A pet with no legs simply skips
 * the step cycle; a pet with wings gets a flap for free.
 *
 * The part-name contract is documented in tools/blender/lib/kit.py.
 */

export type Gait = 'walk' | 'hop' | 'float' | 'swim' | 'fly' | 'slither' | 'roll';

export interface PetPersonality {
  gait: Gait;
  /** Idle animation rate. 1 = calm, 2 = hyperactive. */
  energy: number;
  /** Vertical idle travel, in model heights. */
  bounce: number;
  /** Hover height above the ground, in model heights. 0 = walks. */
  hover: number;
  /** How far the head tilts when idling, radians. */
  curiosity: number;
  /** Tail wag amplitude, radians. */
  waggle: number;
  /** Wing/fin beat rate multiplier. */
  flutter: number;
}

export const DEFAULT_PERSONALITY: PetPersonality = {
  gait: 'walk',
  energy: 1,
  bounce: 0.035,
  hover: 0,
  curiosity: 0.12,
  waggle: 0.28,
  flutter: 1,
};

interface Part {
  object: THREE.Object3D;
  restRotation: THREE.Euler;
  restPosition: THREE.Vector3;
}

const PART_KEYS = [
  'body', 'head',
  'ear.L', 'ear.R',
  'wing.L', 'wing.R',
  'arm.L', 'arm.R',
  'leg.FL', 'leg.FR', 'leg.BL', 'leg.BR',
  'tail', 'fin.L', 'fin.R', 'fin.tail',
] as const;

export class PetAnimator {
  readonly root: THREE.Object3D;
  personality: PetPersonality;

  /** Set by the owner each frame: how fast the pet is moving, world units/s. */
  moveSpeed = 0;
  /** 0..1 excitement, spikes when the pet pays out or is first hatched. */
  excitement = 0;

  private parts = new Map<string, Part>();
  private phase: number;
  private rootRest = new THREE.Vector3();
  private blinkTimer: number;
  private lookTarget: THREE.Vector3 | null = null;
  private headYaw = 0;
  private headPitch = 0;
  private scaleRest = new THREE.Vector3(1, 1, 1);

  constructor(root: THREE.Object3D, personality: Partial<PetPersonality> = {}, seed = 0) {
    this.root = root;
    this.personality = { ...DEFAULT_PERSONALITY, ...personality };
    // Offsetting the phase per pet stops a shelf of pets breathing in unison,
    // which reads as a single animated object rather than a collection.
    this.phase = (seed % 1000) * 0.618034 * Math.PI * 2;
    this.blinkTimer = 1 + (seed % 7) * 0.3;
    this.rootRest.copy(root.position);
    this.scaleRest.copy(root.scale);

    for (const key of PART_KEYS) {
      const object = root.getObjectByName(key);
      if (!object) continue;
      this.parts.set(key, {
        object,
        restRotation: object.rotation.clone(),
        restPosition: object.position.clone(),
      });
    }
  }

  get hasLegs(): boolean {
    return this.parts.has('leg.FL') || this.parts.has('leg.BL');
  }

  /** Make the pet glance at a world position (the player, usually). */
  lookAt(target: THREE.Vector3 | null): void {
    this.lookTarget = target;
  }

  /** Spike the excitement curve — used on hatch and on payout. */
  celebrate(strength = 1): void {
    this.excitement = Math.min(1.5, this.excitement + strength);
  }

  update(dt: number): void {
    const p = this.personality;
    this.phase += dt * p.energy * 2.4;
    this.excitement = Math.max(0, this.excitement - dt * 1.2);

    const moving = this.moveSpeed > 0.35;
    const gaitRate = moving ? Math.min(3.2, 0.7 + this.moveSpeed * 0.42) : 1;
    const stride = this.phase * gaitRate;
    const excite = this.excitement;

    this.animateRoot(dt, stride, moving, excite);
    this.animateBody(stride, moving, excite);
    this.animateHead(dt, stride, moving, excite);
    this.animateEars(stride, moving, excite);
    this.animateLimbs(stride, moving);
    this.animateWings(stride, moving, excite);
    this.animateTail(stride, moving, excite);
    this.animateFins(stride, moving);
  }

  private animateRoot(dt: number, stride: number, moving: boolean, excite: number): void {
    const p = this.personality;
    let y = this.rootRest.y;
    let tilt = 0;

    switch (p.gait) {
      case 'hop': {
        // A clamped sine spends most of its time on the ground, which reads as
        // a hop rather than a bob.
        const hop = Math.max(0, Math.sin(stride * 2.1));
        y += hop * (moving ? 0.22 : 0.06) * (1 + excite * 0.5);
        tilt = -hop * 0.18;
        break;
      }
      case 'float':
      case 'fly':
        y += p.hover + Math.sin(this.phase * 1.15) * (p.bounce * 3.2 + excite * 0.05);
        tilt = Math.sin(this.phase * 0.7) * 0.05;
        break;
      case 'swim':
        y += p.hover + Math.sin(this.phase * 1.5) * p.bounce * 2.4;
        break;
      case 'slither':
        y += Math.abs(Math.sin(stride * 1.6)) * p.bounce * 1.2;
        break;
      case 'roll':
        this.root.rotation.x -= dt * this.moveSpeed * 1.6;
        break;
      default:
        y += Math.abs(Math.sin(stride * 2)) * (moving ? p.bounce * 1.6 : p.bounce);
        break;
    }

    y += excite * 0.09 * Math.abs(Math.sin(this.phase * 6));
    this.root.position.y = y;
    if (p.gait !== 'roll') this.root.rotation.x = tilt;
  }

  private animateBody(stride: number, moving: boolean, excite: number): void {
    const body = this.parts.get('body');
    if (!body) return;
    // Breathing: squash and stretch conserving rough volume.
    const breath = Math.sin(this.phase * 0.9) * 0.022 * this.personality.energy;
    const puff = excite * 0.05;
    body.object.scale.set(
      1 - breath * 0.6 + puff * 0.4,
      1 + breath + puff,
      1 - breath * 0.6 + puff * 0.4,
    );
    body.object.rotation.z = body.restRotation.z + (moving ? Math.sin(stride) * 0.045 : 0);
  }

  private animateHead(dt: number, stride: number, moving: boolean, excite: number): void {
    const head = this.parts.get('head');
    if (!head) return;
    const p = this.personality;

    let targetYaw = 0;
    let targetPitch = 0;

    if (this.lookTarget) {
      const world = new THREE.Vector3();
      head.object.getWorldPosition(world);
      const toTarget = this.lookTarget.clone().sub(world);
      const parentQuat = new THREE.Quaternion();
      (head.object.parent ?? this.root).getWorldQuaternion(parentQuat);
      toTarget.applyQuaternion(parentQuat.invert());
      targetYaw = Math.atan2(toTarget.x, toTarget.z);
      targetPitch = -Math.atan2(toTarget.y, Math.hypot(toTarget.x, toTarget.z));
      // Necks do not swivel 180 degrees; clamp so pets do not look possessed.
      targetYaw = THREE.MathUtils.clamp(targetYaw, -0.85, 0.85);
      targetPitch = THREE.MathUtils.clamp(targetPitch, -0.5, 0.45);
    } else {
      targetYaw = Math.sin(this.phase * 0.43) * p.curiosity;
      targetPitch = Math.sin(this.phase * 0.31 + 1.2) * p.curiosity * 0.5;
    }

    const responsiveness = Math.min(1, dt * (this.lookTarget ? 7 : 3));
    this.headYaw += (targetYaw - this.headYaw) * responsiveness;
    this.headPitch += (targetPitch - this.headPitch) * responsiveness;

    const bob = moving ? Math.sin(stride * 2 + 0.6) * 0.06 : 0;
    head.object.rotation.set(
      head.restRotation.x + this.headPitch + bob - excite * 0.12,
      head.restRotation.y + this.headYaw,
      head.restRotation.z + Math.sin(this.phase * 0.6) * 0.04,
    );

    this.blinkTimer -= dt;
    if (this.blinkTimer < 0) this.blinkTimer = 2.5 + Math.random() * 3.5;
  }

  private animateEars(stride: number, moving: boolean, excite: number): void {
    const swing = moving ? Math.sin(stride * 2.2) * 0.16 : Math.sin(this.phase * 0.8) * 0.05;
    const perk = excite * 0.25;
    for (const [key, sign] of [['ear.L', 1], ['ear.R', -1]] as const) {
      const part = this.parts.get(key);
      if (!part) continue;
      part.object.rotation.set(
        part.restRotation.x + swing - perk,
        part.restRotation.y,
        part.restRotation.z + sign * (swing * 0.5 + Math.sin(this.phase * 1.3) * 0.03),
      );
    }
  }

  private animateLimbs(stride: number, moving: boolean): void {
    if (!moving) {
      for (const key of ['leg.FL', 'leg.FR', 'leg.BL', 'leg.BR', 'arm.L', 'arm.R']) {
        const part = this.parts.get(key);
        if (part) part.object.rotation.copy(part.restRotation);
      }
      return;
    }
    // Diagonal pairs move together — a trot, which reads better than a walk at
    // the speeds pets actually travel.
    const swing = 0.55;
    const pairs: Array<[string, number]> = [
      ['leg.FL', 0],
      ['leg.BR', 0],
      ['leg.FR', Math.PI],
      ['leg.BL', Math.PI],
      ['arm.L', Math.PI],
      ['arm.R', 0],
    ];
    for (const [key, offset] of pairs) {
      const part = this.parts.get(key);
      if (!part) continue;
      part.object.rotation.x = part.restRotation.x + Math.sin(stride * 2 + offset) * swing;
    }
  }

  private animateWings(stride: number, moving: boolean, excite: number): void {
    const p = this.personality;
    const flying = p.gait === 'fly' || p.gait === 'float';
    const rate = flying ? 6.2 : moving ? 3.4 : 1.1;
    const amount = (flying ? 0.55 : moving ? 0.32 : 0.09) * p.flutter + excite * 0.25;
    const beat = Math.sin(this.phase * rate + stride * 0.2);
    for (const [key, sign] of [['wing.L', 1], ['wing.R', -1]] as const) {
      const part = this.parts.get(key);
      if (!part) continue;
      part.object.rotation.set(
        part.restRotation.x,
        part.restRotation.y,
        part.restRotation.z + sign * beat * amount,
      );
    }
  }

  private animateTail(stride: number, moving: boolean, excite: number): void {
    const part = this.parts.get('tail');
    if (!part) return;
    const p = this.personality;
    const rate = moving ? 4.2 : 1.6;
    const amount = p.waggle * (moving ? 1 : 0.55) + excite * 0.4;
    part.object.rotation.set(
      part.restRotation.x + Math.sin(this.phase * rate * 0.6) * amount * 0.3,
      part.restRotation.y + Math.sin(this.phase * rate) * amount,
      part.restRotation.z,
    );
    void stride;
  }

  private animateFins(stride: number, moving: boolean): void {
    const rate = moving ? 5.5 : 2.4;
    const amount = moving ? 0.32 : 0.14;
    for (const [key, sign] of [['fin.L', 1], ['fin.R', -1]] as const) {
      const part = this.parts.get(key);
      if (!part) continue;
      part.object.rotation.z = part.restRotation.z + sign * Math.sin(this.phase * rate) * amount;
    }
    const caudal = this.parts.get('fin.tail');
    if (caudal) {
      caudal.object.rotation.y =
        caudal.restRotation.y + Math.sin(this.phase * rate * 0.8) * amount * 1.6;
    }
    void stride;
  }

  /** Restore every part to its authored pose. */
  reset(): void {
    for (const part of this.parts.values()) {
      part.object.rotation.copy(part.restRotation);
      part.object.position.copy(part.restPosition);
      part.object.scale.set(1, 1, 1);
    }
    this.root.position.copy(this.rootRest);
    this.root.scale.copy(this.scaleRest);
    this.root.rotation.set(0, this.root.rotation.y, 0);
  }
}
