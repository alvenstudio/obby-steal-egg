import * as THREE from 'three';

import { Assets } from '@/core/Assets';
import { MUTATIONS, SIZES } from '@/data/rarity';
import type { CarriedEgg } from '@/game/GameState';
import type { PlayerState } from './PlayerController';

/**
 * What the player sees of themselves: the carried egg, and their own legs.
 *
 * Both exist to solve first-person-specific problems the third-person original
 * never had.
 *
 * The egg is the game's stake made physical -- you can see exactly what you are
 * about to lose. But an egg held at chest height in first person also covers
 * the part of the screen you need for platforming, so it tucks toward the
 * shoulder and fades out as the player looks down. That combination is what
 * lets the same run be both tense and jumpable.
 *
 * The legs exist because in first person you cannot see where your feet are,
 * and this game asks you to land on narrow platforms constantly. A visible
 * pair of boots below the camera turns "I think I'm near the edge" into "I can
 * see I'm near the edge".
 */

const VIEW_LAYER = 1;

export class ViewModel {
  /** A separate scene rendered over the world so held items never clip walls. */
  readonly scene = new THREE.Scene();
  readonly camera: THREE.PerspectiveCamera;

  private eggHolder = new THREE.Group();
  private legs = new THREE.Group();
  private eggModel: THREE.Object3D | null = null;
  private eggMaterials: THREE.MeshStandardMaterial[] = [];
  private currentEgg: CarriedEgg | null = null;

  private swayPos = new THREE.Vector3();
  private swayRot = new THREE.Euler();
  private bobPhase = 0;
  private carryBlend = 0;
  private hueMaterials: THREE.MeshStandardMaterial[] = [];

  showLegs = true;

  constructor(private readonly assets: Assets, aspect: number) {
    this.camera = new THREE.PerspectiveCamera(72, aspect, 0.01, 12);
    this.camera.layers.enable(VIEW_LAYER);

    this.scene.add(this.eggHolder);
    this.scene.add(this.legs);

    // The viewmodel scene has its own light rig; it must not go dark just
    // because the player walked into a shadow.
    const key = new THREE.DirectionalLight(0xffffff, 2.2);
    key.position.set(0.6, 1.2, 0.8);
    this.scene.add(key);
    const fill = new THREE.DirectionalLight(0x9fb6d4, 0.8);
    fill.position.set(-0.8, 0.2, -0.6);
    this.scene.add(fill);
    this.scene.add(new THREE.AmbientLight(0xffffff, 0.55));

    this.buildLegs();
  }

  setAspect(aspect: number): void {
    this.camera.aspect = aspect;
    this.camera.updateProjectionMatrix();
  }

  /**
   * Simple blocky boots, matching the world's art language. They are drawn in
   * the viewmodel scene so they never intersect geometry the player is
   * standing on.
   */
  private buildLegs(): void {
    const boot = new THREE.MeshStandardMaterial({ color: 0x4a3f52, roughness: 0.8 });
    const trouser = new THREE.MeshStandardMaterial({ color: 0x2f5d8a, roughness: 0.85 });

    for (const side of [-1, 1]) {
      const leg = new THREE.Group();
      const shin = new THREE.Mesh(new THREE.BoxGeometry(0.15, 0.42, 0.15), trouser);
      shin.position.set(side * 0.13, -0.42, -0.16);
      const foot = new THREE.Mesh(new THREE.BoxGeometry(0.17, 0.11, 0.28), boot);
      foot.position.set(side * 0.13, -0.66, -0.24);
      leg.add(shin, foot);
      leg.name = side < 0 ? 'leg.L' : 'leg.R';
      this.legs.add(leg);
    }
    this.legs.position.set(0, -0.15, 0);
  }

  /** Show a newly-picked-up egg, or clear it when the hands are empty. */
  setEgg(egg: CarriedEgg | null): void {
    if (egg === this.currentEgg) return;
    this.currentEgg = egg;

    if (this.eggModel) {
      this.eggHolder.remove(this.eggModel);
      this.eggModel = null;
      this.eggMaterials = [];
      this.hueMaterials = [];
    }
    if (!egg) return;

    const model = this.assets.instantiate(`models/props/egg-${egg.biome}.glb`);
    const size = SIZES[egg.size].scale;
    model.scale.setScalar(0.34 * size);
    model.position.set(0.16, -0.3, -0.62);
    model.rotation.set(0.2, 0.5, 0.12);
    this.eggHolder.add(model);
    this.eggModel = model;

    const mutation = MUTATIONS[egg.mutation];
    model.traverse((node) => {
      const mesh = node as THREE.Mesh;
      if (!mesh.isMesh) return;
      const materials = Array.isArray(mesh.material) ? mesh.material : [mesh.material];
      const cloned = materials.map((material) => {
        const clone = (material as THREE.MeshStandardMaterial).clone();
        clone.transparent = true;
        if (mutation.tint) {
          clone.color.lerp(new THREE.Color(mutation.tint), 0.5);
          clone.emissive = new THREE.Color(mutation.tint);
          clone.emissiveIntensity = mutation.emissive;
          if (mutation.animated) this.hueMaterials.push(clone);
        }
        this.eggMaterials.push(clone);
        return clone;
      });
      mesh.material = Array.isArray(mesh.material) ? cloned : cloned[0];
    });
  }

  update(dt: number, player: PlayerState, pitch: number, lookDelta: number, time: number): void {
    this.bobPhase += dt * (player.grounded ? 9 + player.speed * 0.5 : 2);

    const targetBlend = player.carrying ? 1 : 0;
    this.carryBlend += (targetBlend - this.carryBlend) * Math.min(1, dt * 8);

    const speedRatio = Math.min(1, player.speed / 12);
    const bobY = Math.abs(Math.sin(this.bobPhase)) * 0.02 * speedRatio;
    const bobX = Math.cos(this.bobPhase * 0.5) * 0.016 * speedRatio;

    // Lag the held item behind the camera so fast turns feel weighty.
    this.swayPos.x += (-lookDelta * 0.35 - this.swayPos.x) * Math.min(1, dt * 10);
    this.swayPos.y += (-player.velocity.y * 0.004 - this.swayPos.y) * Math.min(1, dt * 8);
    this.swayRot.y += (-lookDelta * 0.9 - this.swayRot.y) * Math.min(1, dt * 10);
    this.swayRot.z += (lookDelta * 0.6 - this.swayRot.z) * Math.min(1, dt * 10);

    // Looking down tucks the egg toward the shoulder AND fades it out, so it
    // stops covering the platform the player is trying to land on. Neither
    // alone is enough: tucking still occludes, fading alone looks like a bug.
    const lookDownRatio = THREE.MathUtils.clamp((-pitch - 0.45) / 0.75, 0, 1);
    const tuck = lookDownRatio * 0.22;

    this.eggHolder.position.set(
      this.swayPos.x + bobX + tuck * 0.5,
      this.swayPos.y + bobY - 0.05 * (1 - this.carryBlend) - tuck * 0.35,
      -0.1 + (1 - this.carryBlend) * 0.45,
    );
    this.eggHolder.rotation.set(
      this.swayRot.x + Math.sin(this.bobPhase * 0.5) * 0.02,
      this.swayRot.y + tuck * 1.1,
      this.swayRot.z + tuck * 0.5,
    );
    this.eggHolder.visible = this.carryBlend > 0.02;

    const alpha = (1 - lookDownRatio * 0.62) * this.carryBlend;
    for (const material of this.eggMaterials) material.opacity = alpha;

    if (this.hueMaterials.length > 0) {
      const hue = (time * 0.25) % 1;
      for (const material of this.hueMaterials) material.emissive.setHSL(hue, 0.9, 0.55);
    }

    // Legs only appear when the player looks down far enough to expect them.
    const legVisibility = THREE.MathUtils.clamp((-pitch - 0.3) / 0.5, 0, 1);
    this.legs.visible = this.showLegs && legVisibility > 0.02;
    this.legs.position.y = -0.15 - (1 - legVisibility) * 0.5;

    const stride = Math.sin(this.bobPhase) * (player.grounded ? speedRatio * 0.5 : 0);
    const children = this.legs.children;
    if (children.length === 2) {
      children[0].rotation.x = stride;
      children[1].rotation.x = -stride;
    }
  }

  /**
   * Draw the held item over the finished world frame.
   *
   * `autoClear` has to be off here: WebGLRenderer.render clears colour by
   * default, so a second render pass silently erases everything drawn before
   * it. Only the depth buffer is cleared, which is what stops the egg from
   * intersecting a wall the player is standing against.
   */
  render(renderer: THREE.WebGLRenderer): void {
    const previousAutoClear = renderer.autoClear;
    renderer.autoClear = false;
    renderer.clearDepth();
    renderer.render(this.scene, this.camera);
    renderer.autoClear = previousAutoClear;
  }

  dispose(): void {
    this.scene.traverse((node) => {
      const mesh = node as THREE.Mesh;
      if (!mesh.isMesh) return;
      mesh.geometry.dispose();
    });
  }
}
