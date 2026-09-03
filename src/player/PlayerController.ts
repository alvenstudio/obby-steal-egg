import * as THREE from 'three';

import { ColliderWorld, MoveResult, MoverShape, moveBox } from '@/core/Physics';
import type { Input } from '@/core/Input';

/**
 * First-person movement.
 *
 * The reference game is third-person, where you can see your feet and the
 * platform edge you are aiming at. First person takes that away, so this
 * controller has to give it back through forgiveness rather than precision:
 * coyote time, jump buffering, real air control, and a ledge mantle. Those
 * four are the difference between "the jump felt unfair" and "I missed".
 */

export interface PlayerTuning {
  walkSpeed: number;
  sprintSpeed: number;
  crouchSpeed: number;
  /** Ground acceleration, units/s^2. High = snappy, low = floaty. */
  accelGround: number;
  accelAir: number;
  frictionGround: number;
  frictionAir: number;
  gravity: number;
  jumpSpeed: number;
  /** Extra gravity while falling, so the arc is snappy rather than moon-like. */
  fallMultiplier: number;
  /** Gravity multiplier when the jump key is released early. */
  lowJumpMultiplier: number;
  coyoteTime: number;
  jumpBuffer: number;
  maxAirJumps: number;
  /** Seconds of sprint available before stamina runs out. 0 = unlimited. */
  stamina: number;
  staminaRegen: number;
  eyeHeight: number;
  crouchEyeHeight: number;
  radius: number;
  height: number;
  crouchHeight: number;
  stepHeight: number;
  /** How much the carried egg slows the player, as a fraction. */
  carryPenalty: number;
  mantleReach: number;
}

export const DEFAULT_TUNING: PlayerTuning = {
  walkSpeed: 7.2,
  sprintSpeed: 11.4,
  crouchSpeed: 3.6,
  accelGround: 70,
  accelAir: 26,
  frictionGround: 11,
  frictionAir: 0.6,
  gravity: 26,
  jumpSpeed: 9.4,
  fallMultiplier: 1.7,
  lowJumpMultiplier: 2.4,
  coyoteTime: 0.13,
  jumpBuffer: 0.16,
  maxAirJumps: 0,
  stamina: 4.5,
  staminaRegen: 0.55,
  eyeHeight: 1.62,
  crouchEyeHeight: 0.95,
  radius: 0.38,
  height: 1.85,
  crouchHeight: 1.1,
  stepHeight: 0.52,
  carryPenalty: 0.22,
  mantleReach: 1.15,
};

export interface PlayerState {
  position: THREE.Vector3;
  velocity: THREE.Vector3;
  grounded: boolean;
  crouching: boolean;
  sprinting: boolean;
  stamina: number;
  /** Horizontal speed this frame, for head-bob and FOV. */
  speed: number;
  /** Set while the player is carrying a stolen egg. */
  carrying: boolean;
  /** Seconds of forced immobility after being caught. */
  stunTimer: number;
  landedHard: boolean;
  justJumped: boolean;
  mantling: boolean;
}

export class PlayerController {
  readonly state: PlayerState = {
    position: new THREE.Vector3(0, 2, 0),
    velocity: new THREE.Vector3(),
    grounded: false,
    crouching: false,
    sprinting: false,
    stamina: DEFAULT_TUNING.stamina,
    speed: 0,
    carrying: false,
    stunTimer: 0,
    landedHard: false,
    justJumped: false,
    mantling: false,
  };

  tuning: PlayerTuning = { ...DEFAULT_TUNING };

  /** Multipliers applied by upgrades; kept separate so upgrades compose. */
  speedMultiplier = 1;
  jumpMultiplier = 1;

  /** Yaw in radians, owned by the camera but needed to orient movement. */
  yaw = 0;

  private coyote = 0;
  private buffered = -1;
  private airJumps = 0;
  private jumpHeld = false;
  private mantleTimer = 0;
  private mantleTarget = new THREE.Vector3();
  private mantleFrom = new THREE.Vector3();
  private lastResult: MoveResult | null = null;
  private wasGrounded = false;

  /** Fired when the player lands; `impact` is the downward speed absorbed. */
  onLand: ((impact: number) => void) | null = null;
  onJump: (() => void) | null = null;
  onStep: ((speed: number) => void) | null = null;
  private stepAccumulator = 0;

  constructor(private readonly world: ColliderWorld) {}

  get shape(): MoverShape {
    return {
      radius: this.tuning.radius,
      height: this.state.crouching ? this.tuning.crouchHeight : this.tuning.height,
      stepHeight: this.tuning.stepHeight,
    };
  }

  get eyeHeight(): number {
    return this.state.crouching ? this.tuning.crouchEyeHeight : this.tuning.eyeHeight;
  }

  get groundKind() {
    return this.lastResult?.groundKind ?? null;
  }

  teleport(to: THREE.Vector3): void {
    this.state.position.copy(to);
    this.state.velocity.set(0, 0, 0);
    this.mantleTimer = 0;
    this.state.mantling = false;
  }

  stun(seconds: number): void {
    this.state.stunTimer = Math.max(this.state.stunTimer, seconds);
    this.state.velocity.x = 0;
    this.state.velocity.z = 0;
  }

  update(input: Input, dt: number): void {
    const s = this.state;
    const t = this.tuning;
    s.landedHard = false;
    s.justJumped = false;

    if (s.stunTimer > 0) {
      s.stunTimer -= dt;
      s.velocity.x = 0;
      s.velocity.z = 0;
      s.velocity.y -= t.gravity * dt;
      this.integrate(dt);
      return;
    }

    if (this.mantleTimer > 0) {
      this.advanceMantle(dt);
      return;
    }

    // --- input ------------------------------------------------------------
    const axis = input.moveAxis();
    const wantsJump = input.pressed('jump');
    this.jumpHeld = input.held('jump');

    const wantsCrouch = input.held('crouch');
    if (s.crouching && !wantsCrouch && !this.blockedStandingUp()) s.crouching = false;
    else if (wantsCrouch) s.crouching = true;

    const moving = axis.x !== 0 || axis.y !== 0;
    const canSprint = t.stamina <= 0 || s.stamina > 0;
    s.sprinting = input.held('sprint') && moving && !s.crouching && canSprint;

    if (t.stamina > 0) {
      if (s.sprinting) s.stamina = Math.max(0, s.stamina - dt);
      else s.stamina = Math.min(t.stamina, s.stamina + dt * t.staminaRegen * t.stamina);
    }

    // --- desired horizontal velocity --------------------------------------
    let target = s.crouching
      ? t.crouchSpeed
      : s.sprinting
        ? t.sprintSpeed
        : t.walkSpeed;
    target *= this.speedMultiplier;
    if (s.carrying) target *= 1 - t.carryPenalty;
    if (this.lastResult?.groundKind === 'sticky') target *= 0.75;

    const sin = Math.sin(this.yaw);
    const cos = Math.cos(this.yaw);
    // Camera-relative: yaw 0 looks down -Z, so forward is (-sin, -cos).
    const wishX = axis.x * cos - axis.y * sin;
    const wishZ = -axis.x * sin - axis.y * cos;

    const onIce = this.lastResult?.groundKind === 'ice';
    const accel = s.grounded ? (onIce ? t.accelGround * 0.18 : t.accelGround) : t.accelAir;
    const friction = s.grounded ? (onIce ? 0.4 : t.frictionGround) : t.frictionAir;

    this.applyAcceleration(wishX, wishZ, target, accel, friction, dt);

    // --- jumping -----------------------------------------------------------
    if (s.grounded) {
      this.coyote = t.coyoteTime;
      this.airJumps = 0;
    } else {
      this.coyote -= dt;
    }

    if (wantsJump) this.buffered = t.jumpBuffer;
    else if (this.buffered >= 0) this.buffered -= dt;

    if (this.buffered >= 0) {
      const canGroundJump = s.grounded || this.coyote > 0;
      const canAirJump = !canGroundJump && this.airJumps < t.maxAirJumps;
      if (canGroundJump || canAirJump) {
        s.velocity.y = t.jumpSpeed * this.jumpMultiplier;
        if (this.lastResult?.groundKind === 'bounce') s.velocity.y *= 1.55;
        if (!canGroundJump) this.airJumps++;
        this.buffered = -1;
        this.coyote = 0;
        s.grounded = false;
        s.justJumped = true;
        this.onJump?.();
      }
    }

    // --- gravity with a snappier fall --------------------------------------
    let gravity = t.gravity;
    if (s.velocity.y < 0) gravity *= t.fallMultiplier;
    else if (s.velocity.y > 0 && !this.jumpHeld) gravity *= t.lowJumpMultiplier;
    s.velocity.y -= gravity * dt;
    s.velocity.y = Math.max(s.velocity.y, -55);

    this.integrate(dt);

    // --- mantle onto a ledge we are pressed against ------------------------
    if (!s.grounded && s.velocity.y < 1.5 && moving && this.tryMantle()) return;

    if (input.pressed('jump') && !s.grounded) this.buffered = t.jumpBuffer;
  }

  private applyAcceleration(
    wishX: number,
    wishZ: number,
    target: number,
    accel: number,
    friction: number,
    dt: number,
  ): void {
    const vel = this.state.velocity;
    const wishLen = Math.hypot(wishX, wishZ);

    if (wishLen > 0) {
      const dirX = wishX / wishLen;
      const dirZ = wishZ / wishLen;
      const current = vel.x * dirX + vel.z * dirZ;
      const add = Math.min(target * wishLen - current, accel * dt);
      if (add > 0) {
        vel.x += dirX * add;
        vel.z += dirZ * add;
      }
    }

    // Friction only opposes motion; applying it before acceleration would make
    // the player feel like they are wading even at full stick.
    const speed = Math.hypot(vel.x, vel.z);
    if (speed > 0.001) {
      const drop = speed * friction * dt;
      const scale = Math.max(0, speed - drop) / speed;
      vel.x *= scale;
      vel.z *= scale;
    }

    // Cap only the ground plane so a bounce pad's vertical launch survives.
    const capped = Math.hypot(vel.x, vel.z);
    const maxSpeed = target * 1.35;
    if (capped > maxSpeed) {
      const scale = maxSpeed / capped;
      vel.x *= scale;
      vel.z *= scale;
    }
  }

  private integrate(dt: number): void {
    const s = this.state;
    const before = s.velocity.y;
    this.wasGrounded = s.grounded;

    const result = moveBox(this.world, s.position, s.velocity, this.shape, dt);
    this.lastResult = result;
    s.position.copy(result.position);
    s.velocity.copy(result.velocity);
    s.grounded = result.grounded;
    s.speed = Math.hypot(s.velocity.x, s.velocity.z);

    if (result.groundKind === 'conveyor' && result.ground?.drift) {
      s.position.addScaledVector(result.ground.drift, dt);
    }

    if (!this.wasGrounded && s.grounded) {
      const impact = -before;
      if (impact > 1) this.onLand?.(impact);
      if (impact > 22) s.landedHard = true;
      if (result.groundKind === 'bounce') s.velocity.y = Math.min(impact * 0.85 + 6, 22);
    }

    if (s.grounded && s.speed > 0.6) {
      this.stepAccumulator += s.speed * dt;
      const stride = s.sprinting ? 2.4 : 1.9;
      if (this.stepAccumulator > stride) {
        this.stepAccumulator = 0;
        this.onStep?.(s.speed);
      }
    } else {
      this.stepAccumulator = 0;
    }
  }

  private blockedStandingUp(): boolean {
    const probe = {
      radius: this.tuning.radius,
      height: this.tuning.height,
      stepHeight: 0,
    };
    const test = moveBox(this.world, this.state.position, new THREE.Vector3(), probe, 0);
    return test.hitCeiling;
  }

  /**
   * If the player is airborne, moving forward, and there is a standable ledge
   * just above head height within reach, pull them up onto it. In first person
   * you cannot see your own hands grab a lip, so this has to be generous or it
   * reads as the game ignoring you.
   */
  private tryMantle(): boolean {
    const s = this.state;
    const t = this.tuning;
    const forward = new THREE.Vector3(-Math.sin(this.yaw), 0, -Math.cos(this.yaw));
    const speedDir = new THREE.Vector3(s.velocity.x, 0, s.velocity.z);
    if (speedDir.lengthSq() < 0.5) return false;
    speedDir.normalize();
    if (speedDir.dot(forward) < 0.35) return false;

    for (let lift = 0.6; lift <= t.mantleReach + 0.9; lift += 0.28) {
      const probe = s.position.clone()
        .addScaledVector(forward, t.radius + 0.42)
        .setY(s.position.y + lift);
      const ground = this.world.raycast(
        probe.clone().setY(probe.y + 0.55),
        new THREE.Vector3(0, -1, 0),
        0.8,
      );
      if (!ground) continue;
      const top = probe.y + 0.55 - ground.distance;
      if (top <= s.position.y + 0.15) continue;
      if (top - s.position.y > t.mantleReach + 0.9) continue;

      const landing = probe.clone().setY(top + 0.02);
      const clear = moveBox(this.world, landing, new THREE.Vector3(), this.shape, 0);
      if (clear.hitCeiling || clear.hitWall) continue;

      this.mantleFrom.copy(s.position);
      this.mantleTarget.copy(landing);
      this.mantleTimer = 0.001;
      s.mantling = true;
      s.velocity.set(0, 0, 0);
      return true;
    }
    return false;
  }

  private advanceMantle(dt: number): void {
    const duration = 0.26;
    this.mantleTimer += dt;
    const t = Math.min(1, this.mantleTimer / duration);
    // Up first, then forward, so the player visibly clears the lip.
    const rise = Math.min(1, t / 0.6);
    const push = Math.max(0, (t - 0.45) / 0.55);
    this.state.position.set(
      this.mantleFrom.x + (this.mantleTarget.x - this.mantleFrom.x) * push,
      this.mantleFrom.y + (this.mantleTarget.y - this.mantleFrom.y) * rise,
      this.mantleFrom.z + (this.mantleTarget.z - this.mantleFrom.z) * push,
    );
    if (t >= 1) {
      this.mantleTimer = 0;
      this.state.mantling = false;
      this.state.grounded = true;
      this.state.position.copy(this.mantleTarget);
    }
  }
}
