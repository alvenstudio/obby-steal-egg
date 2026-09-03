import * as THREE from 'three';

import type { Input } from '@/core/Input';
import type { PlayerController } from './PlayerController';

/**
 * The first-person camera.
 *
 * Everything here exists to replace information the third-person original gave
 * you for free. You cannot see your own body, so speed has to be legible as
 * FOV and bob; you cannot see yourself land, so impact has to be a dip; you
 * cannot see behind you, so being chased has to arrive as a shake and a sound.
 * Each effect is separately scalable because motion sensitivity varies a lot,
 * and the options menu exposes them.
 */

export interface CameraTuning {
  sensitivity: number;
  fovBase: number;
  fovSprint: number;
  fovCarry: number;
  bobAmount: number;
  bobSpeed: number;
  swayAmount: number;
  rollAmount: number;
  landDipAmount: number;
  smoothing: number;
  /** User-facing accessibility scales, 0..1. */
  bobScale: number;
  shakeScale: number;
}

export const DEFAULT_CAMERA_TUNING: CameraTuning = {
  sensitivity: 0.0022,
  fovBase: 78,
  fovSprint: 90,
  fovCarry: 72,
  bobAmount: 0.055,
  bobSpeed: 10.5,
  swayAmount: 0.035,
  rollAmount: 0.028,
  landDipAmount: 0.28,
  smoothing: 0.0,
  bobScale: 1,
  shakeScale: 1,
};

const MAX_PITCH = Math.PI / 2 - 0.02;

export class FirstPersonCamera {
  readonly camera: THREE.PerspectiveCamera;
  tuning: CameraTuning = { ...DEFAULT_CAMERA_TUNING };

  yaw = 0;
  pitch = 0;

  private bobPhase = 0;
  private bobOffset = new THREE.Vector3();
  private landDip = 0;
  private landDipVel = 0;
  private shake = 0;
  private shakeTime = 0;
  private roll = 0;
  private currentFov: number;
  private smoothedEye = 0;
  private targetOffset = new THREE.Vector3();
  /** Extra pitch/yaw added by effects, never by the mouse. */
  private kickPitch = 0;
  private kickYaw = 0;

  constructor(aspect: number) {
    this.camera = new THREE.PerspectiveCamera(DEFAULT_CAMERA_TUNING.fovBase, aspect, 0.05, 900);
    this.currentFov = this.tuning.fovBase;
    this.camera.rotation.order = 'YXZ';
  }

  setAspect(aspect: number): void {
    this.camera.aspect = aspect;
    this.camera.updateProjectionMatrix();
  }

  /** A one-off jolt: getting caught, a heavy landing, an explosion. */
  addShake(strength: number): void {
    this.shake = Math.min(1.4, this.shake + strength * this.tuning.shakeScale);
  }

  /** Nudge the aim, e.g. when a guardian body-checks the player. */
  addKick(pitch: number, yaw: number): void {
    this.kickPitch += pitch;
    this.kickYaw += yaw;
  }

  handleLook(input: Input): void {
    const { dx, dy } = input.consumeLook();
    if (dx === 0 && dy === 0) return;
    this.yaw -= dx * this.tuning.sensitivity;
    this.pitch -= dy * this.tuning.sensitivity;
    this.pitch = Math.max(-MAX_PITCH, Math.min(MAX_PITCH, this.pitch));
    // Keep yaw bounded so long sessions do not accumulate float error.
    if (this.yaw > Math.PI) this.yaw -= Math.PI * 2;
    else if (this.yaw < -Math.PI) this.yaw += Math.PI * 2;
  }

  update(player: PlayerController, dt: number, strafe: number): void {
    const s = player.state;
    const t = this.tuning;

    // --- head bob ----------------------------------------------------------
    const speedRatio = Math.min(1, s.speed / 11);
    if (s.grounded && s.speed > 0.5) {
      this.bobPhase += dt * t.bobSpeed * (0.6 + speedRatio * 0.8);
    } else {
      // Ease the bob out rather than snapping it to zero mid-step.
      this.bobPhase += dt * 2.0;
    }
    const bobStrength = (s.grounded ? speedRatio : 0) * t.bobAmount * t.bobScale;
    this.bobOffset.set(
      Math.cos(this.bobPhase * 0.5) * bobStrength * 0.9,
      Math.abs(Math.sin(this.bobPhase)) * bobStrength * -1.0,
      0,
    );

    // --- landing dip (critical-damped spring) ------------------------------
    const stiffness = 190;
    const damping = 22;
    this.landDipVel += (-this.landDip * stiffness - this.landDipVel * damping) * dt;
    this.landDip += this.landDipVel * dt;

    // --- strafe roll -------------------------------------------------------
    const targetRoll = -strafe * t.rollAmount * (s.grounded ? 1 : 0.55);
    this.roll += (targetRoll - this.roll) * Math.min(1, dt * 9);

    // --- shake -------------------------------------------------------------
    if (this.shake > 0) {
      this.shakeTime += dt * 34;
      this.shake = Math.max(0, this.shake - dt * 2.4);
    }

    // --- FOV ---------------------------------------------------------------
    let targetFov = t.fovBase;
    if (s.sprinting) targetFov = t.fovSprint;
    if (s.carrying) targetFov = Math.min(targetFov, t.fovCarry);
    if (s.stunTimer > 0) targetFov = t.fovBase - 8;
    this.currentFov += (targetFov - this.currentFov) * Math.min(1, dt * 7);
    if (Math.abs(this.currentFov - this.camera.fov) > 0.01) {
      this.camera.fov = this.currentFov;
      this.camera.updateProjectionMatrix();
    }

    // --- kick decay --------------------------------------------------------
    this.kickPitch *= Math.max(0, 1 - dt * 6);
    this.kickYaw *= Math.max(0, 1 - dt * 6);

    // --- assemble the transform -------------------------------------------
    const eye = player.eyeHeight;
    // Smooth the crouch transition and step-ups; a hard snap reads as a glitch.
    this.smoothedEye += (eye - this.smoothedEye) * Math.min(1, dt * 12);
    if (Math.abs(this.smoothedEye - eye) < 0.001) this.smoothedEye = eye;

    this.targetOffset.copy(this.bobOffset);
    this.targetOffset.y += this.landDip;

    const shakeAmount = this.shake * this.shake * 0.06;
    const shakeX = Math.sin(this.shakeTime * 1.7) * shakeAmount;
    const shakeY = Math.cos(this.shakeTime * 2.3) * shakeAmount;

    this.camera.position.set(
      s.position.x + this.targetOffset.x,
      s.position.y + this.smoothedEye + this.targetOffset.y,
      s.position.z + this.targetOffset.z,
    );

    this.camera.rotation.set(
      this.pitch + this.kickPitch + shakeY,
      this.yaw + this.kickYaw + shakeX,
      this.roll + Math.sin(this.bobPhase * 0.5) * t.swayAmount * t.bobScale * 0.35,
      'YXZ',
    );
  }

  /** Called by the player controller's land callback. */
  onLand(impact: number): void {
    const strength = Math.min(1, impact / 24);
    this.landDip -= this.tuning.landDipAmount * strength * this.tuning.bobScale;
    this.landDipVel -= strength * 1.4;
    if (impact > 18) this.addShake(strength * 0.5);
  }

  onJump(): void {
    this.landDip += 0.04 * this.tuning.bobScale;
  }

  /** World-space forward, ignoring pitch — used for movement and interaction. */
  forward(out = new THREE.Vector3()): THREE.Vector3 {
    return out.set(-Math.sin(this.yaw), 0, -Math.cos(this.yaw));
  }

  /** Full look direction including pitch, for raycasting what you're aiming at. */
  lookDirection(out = new THREE.Vector3()): THREE.Vector3 {
    const cosPitch = Math.cos(this.pitch);
    return out.set(
      -Math.sin(this.yaw) * cosPitch,
      Math.sin(this.pitch),
      -Math.cos(this.yaw) * cosPitch,
    ).normalize();
  }
}
