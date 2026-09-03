import * as THREE from 'three';

import { Assets } from '@/core/Assets';
import { ColliderWorld } from '@/core/Physics';
import { BIOMES, BiomeDef, BiomeId } from '@/data/biomes';

import { BiomeRegion, NestInfo } from './BiomeRegion';
import { Builder } from './Builder';
import { Kiosk, Pedestal, SAFE_RADIUS, SafeZone } from './SafeZone';

/**
 * Assembles the whole map and owns everything about it that is not gameplay
 * state: geometry, lighting, sky, and which zone the player is standing in.
 *
 * The map is one persistent world rather than streamed levels. That is a
 * deliberate copy of the reference: being able to see the Volcano glowing on
 * the horizon while you are still stealing from chickens is most of what makes
 * the progression legible, and in first person it is even stronger, because
 * the far biomes are literally on your skyline the whole game.
 */

export interface NestState {
  biome: BiomeDef;
  info: NestInfo;
  /** false while the egg is respawning. */
  hasEgg: boolean;
  respawnIn: number;
  /** The visible egg, hidden while respawning. */
  mesh: THREE.Object3D | null;
  /** Platforms from the nest down to the ground, for guardian pursuit. */
  descentPath: THREE.Vector3[];
}

export interface WorldBuild {
  pedestals: Pedestal[];
  kiosks: Kiosk[];
  spawn: THREE.Vector3;
  treadmillArea: THREE.Box3;
  nests: Map<BiomeId, NestState>;
}

/** Eggs come back on the same cadence as the reference game's day. */
export const EGG_RESPAWN_SECONDS = 45;

/** How close to a biome's centre counts as being inside it. */
const ZONE_RADIUS = 56;

export class World {
  readonly root = new THREE.Group();
  readonly colliders = new ColliderWorld();

  pedestals: Pedestal[] = [];
  kiosks: Kiosk[] = [];
  spawn = new THREE.Vector3(0, 3, 12);
  treadmillArea = new THREE.Box3();
  nests = new Map<BiomeId, NestState>();

  private sun!: THREE.DirectionalLight;
  private ambient!: THREE.HemisphereLight;
  private fillLight!: THREE.DirectionalLight;
  private sky!: THREE.Mesh;
  private fog = new THREE.Fog(0xb8e0f7, 220, 780);
  private currentZone: BiomeDef | null = null;
  private targetFogColor = new THREE.Color(0xb8e0f7);
  private targetSkyColor = new THREE.Color(0x8fd0f5);
  private targetSunColor = new THREE.Color(0xfff4d6);
  private targetSunIntensity = 2.5;
  private targetAmbientColor = new THREE.Color(0xa8ccdd);
  private targetAmbientIntensity = 0.55;

  constructor(private readonly scene: THREE.Scene, private readonly assets: Assets) {
    this.root.name = 'world';
    scene.add(this.root);
  }

  build(): WorldBuild {
    this.buildLighting();
    this.buildSky();

    this.buildBasePlain();

    const safe = new SafeZone().build(this.root, this.colliders);
    this.pedestals = safe.pedestals;
    this.kiosks = safe.kiosks;
    this.spawn = safe.spawn.clone();
    this.treadmillArea = safe.treadmillArea;

    for (const biome of BIOMES) {
      const region = new BiomeRegion(biome);
      const result = region.build(this.root, this.colliders);
      this.nests.set(biome.id, {
        biome,
        info: result.nest,
        hasEgg: true,
        respawnIn: 0,
        mesh: null,
        descentPath: result.descentPath,
      });
      this.buildConnectingRoad(biome);
    }

    return {
      pedestals: this.pedestals,
      kiosks: this.kiosks,
      spawn: this.spawn,
      treadmillArea: this.treadmillArea,
      nests: this.nests,
    };
  }

  /**
   * A continuous plain under the whole map.
   *
   * Without it the roads and biome discs hang in empty sky, which reads as a
   * broken level rather than a stylised one -- and worse, it removes the sense
   * of distance that makes the far biomes feel far. The plain is a single
   * low-resolution grid of large tiles, drawn below everything else and
   * deliberately desaturated so the biomes still pop against it.
   */
  private buildBasePlain(): void {
    const builder = new Builder(this.colliders, 'plain');
    const extent = 640;
    const tile = 40;
    const count = Math.ceil((extent * 2) / tile);

    for (let ix = 0; ix < count; ix++) {
      for (let iz = 0; iz < count; iz++) {
        const x = (ix - (count - 1) / 2) * tile;
        const z = (iz - (count - 1) / 2) * tile;
        if (Math.hypot(x, z) > extent) continue;
        const alt = (ix + iz) % 2 === 0;
        builder.box([x, 0.5, z], [tile, 1.0, tile], {
          color: alt ? '#6f7f5c' : '#657552',
          roughness: 0.98,
        }, { noShadow: true });
      }
    }
    builder.build(this.root);
  }

  /**
   * A paved road from the safe zone out to each biome's entrance.
   *
   * These exist purely so the run home has a shape. Without them the map is an
   * undifferentiated plain and every escape is a straight line across nothing;
   * with them there is a route, landmarks that tell you how far you have left,
   * and the specific relief of your feet hitting stone.
   */
  private buildConnectingRoad(biome: BiomeDef): void {
    const builder = new Builder(this.colliders, `road-${biome.id}`);
    const dir = new THREE.Vector3(Math.sin(biome.bearing), 0, -Math.cos(biome.bearing));
    const from = SAFE_RADIUS - 2;
    const to = biome.distance - 46;
    const step = 8;
    const count = Math.max(1, Math.floor((to - from) / step));

    for (let i = 0; i <= count; i++) {
      const t = i / count;
      const d = from + (to - from) * t;
      const x = dir.x * d;
      const z = dir.z * d;
      const width = 7.5 - t * 1.5;
      builder.box([x, 1.0, z], [width, 2.0, step],
        {
          color: i % 2 === 0 ? '#8b8378' : '#7d766c',
          roughness: 0.95,
        },
        { rotationY: biome.bearing, noShadow: true });

      // Mile markers every few segments, lit so they work as night beacons.
      if (i % 4 === 2) {
        for (const side of [-1, 1]) {
          const ox = x + Math.cos(biome.bearing) * side * (width * 0.5 + 1.1);
          const oz = z + Math.sin(biome.bearing) * side * (width * 0.5 + 1.1);
          builder.box([ox, 3.0, oz], [0.4, 4.0, 0.4], '#6b6259');
          builder.box([ox, 5.2, oz], [0.9, 0.9, 0.9], {
            color: biome.palette.accentAlt,
            emissive: biome.palette.accentAlt,
            emissiveIntensity: 2.2,
            roughness: 0.35,
          }, { solid: false, noShadow: true });
        }
      }
    }
    builder.build(this.root);
  }

  // -- lighting -------------------------------------------------------------

  private buildLighting(): void {
    this.ambient = new THREE.HemisphereLight(0xa8ccdd, 0x40382e, 0.55);
    this.scene.add(this.ambient);

    this.sun = new THREE.DirectionalLight(0xfff4d6, 2.5);
    this.sun.position.set(40, 70, 25);
    this.sun.castShadow = true;
    this.sun.shadow.mapSize.set(2048, 2048);
    // The shadow camera follows the player rather than covering the whole map:
    // a 1100-unit-wide world would need a shadow texel the size of a house.
    const extent = 60;
    this.sun.shadow.camera.left = -extent;
    this.sun.shadow.camera.right = extent;
    this.sun.shadow.camera.top = extent;
    this.sun.shadow.camera.bottom = -extent;
    this.sun.shadow.camera.near = 1;
    this.sun.shadow.camera.far = 220;
    this.sun.shadow.bias = -0.0009;
    this.sun.shadow.normalBias = 0.035;
    this.scene.add(this.sun);
    this.scene.add(this.sun.target);

    // A dim opposing fill so shadowed faces keep their hue instead of going
    // muddy. With flat matte materials this is what stops the world reading
    // as two-tone.
    this.fillLight = new THREE.DirectionalLight(0x9fb6d4, 0.45);
    this.fillLight.position.set(-50, 30, -40);
    this.scene.add(this.fillLight);

    this.scene.fog = this.fog;
  }

  private buildSky(): void {
    // An inverted sphere rather than a scene background, so it can be tinted
    // per zone and lerped smoothly as the player crosses a boundary.
    const geometry = new THREE.SphereGeometry(700, 24, 16);
    const material = new THREE.MeshBasicMaterial({
      color: 0x8fd0f5,
      side: THREE.BackSide,
      fog: false,
      depthWrite: false,
    });
    this.sky = new THREE.Mesh(geometry, material);
    this.sky.name = 'sky';
    this.sky.renderOrder = -1000;
    this.scene.add(this.sky);
  }

  /** Which biome the player is standing in, or null for the open road. */
  zoneAt(position: THREE.Vector3): BiomeDef | null {
    if (position.length() < SAFE_RADIUS + 8) return null;
    let closest: BiomeDef | null = null;
    let closestDistance = Infinity;
    for (const nest of this.nests.values()) {
      const biome = nest.biome;
      // Measure to the biome's centre on the ground plane; height must not
      // count, or standing on top of the nest would read as leaving the zone.
      const dx = position.x - Math.sin(biome.bearing) * biome.distance;
      const dz = position.z + Math.cos(biome.bearing) * biome.distance;
      const distance = Math.hypot(dx, dz);
      if (distance < ZONE_RADIUS && distance < closestDistance) {
        closestDistance = distance;
        closest = biome;
      }
    }
    return closest;
  }

  inSafeZone(position: THREE.Vector3): boolean {
    return Math.hypot(position.x, position.z) < SAFE_RADIUS;
  }

  /** Update lighting, sky and fog toward the player's current zone. */
  update(dt: number, playerPosition: THREE.Vector3, nightFactor: number): void {
    const zone = this.zoneAt(playerPosition);
    if (zone !== this.currentZone) {
      this.currentZone = zone;
      const palette = zone
        ? zone.palette
        : {
            sky: '#8fd0f5', fog: '#b8e0f7', sun: '#fff4d6', sunIntensity: 2.5,
            ambient: '#a8ccdd', ambientIntensity: 0.55,
          };
      this.targetSkyColor.set(palette.sky);
      this.targetFogColor.set(palette.fog);
      this.targetSunColor.set(palette.sun);
      this.targetSunIntensity = palette.sunIntensity;
      this.targetAmbientColor.set(palette.ambient);
      this.targetAmbientIntensity = palette.ambientIntensity;
    }

    // Crossing a biome boundary should feel like walking into weather, not
    // like a cut, so everything eases rather than snapping.
    const ease = Math.min(1, dt * 1.6);
    const night = 1 - nightFactor * 0.72;

    (this.sky.material as THREE.MeshBasicMaterial).color.lerp(
      scratchColor.copy(this.targetSkyColor).multiplyScalar(night), ease,
    );
    this.fog.color.lerp(scratchColor.copy(this.targetFogColor).multiplyScalar(night), ease);
    this.sun.color.lerp(this.targetSunColor, ease);
    this.sun.intensity += (this.targetSunIntensity * (1 - nightFactor * 0.85) - this.sun.intensity) * ease;
    this.ambient.color.lerp(this.targetAmbientColor, ease);
    this.ambient.intensity +=
      (this.targetAmbientIntensity * (1 - nightFactor * 0.5) - this.ambient.intensity) * ease;

    this.sky.position.copy(playerPosition);

    // Keep the shadow frustum centred ahead of the player.
    this.sun.position.set(
      playerPosition.x + 45, playerPosition.y + 75, playerPosition.z + 30,
    );
    this.sun.target.position.copy(playerPosition);
    this.sun.target.updateMatrixWorld();

    for (const nest of this.nests.values()) {
      if (nest.hasEgg) continue;
      nest.respawnIn -= dt;
      if (nest.respawnIn <= 0) {
        nest.hasEgg = true;
        if (nest.mesh) nest.mesh.visible = true;
      }
    }
  }

  takeEggFrom(biome: BiomeId): boolean {
    const nest = this.nests.get(biome);
    if (!nest || !nest.hasEgg) return false;
    nest.hasEgg = false;
    nest.respawnIn = EGG_RESPAWN_SECONDS;
    if (nest.mesh) nest.mesh.visible = false;
    return true;
  }

  /** Attach the visible egg models once assets have loaded. */
  attachEggs(): void {
    for (const nest of this.nests.values()) {
      if (nest.mesh) continue;
      const model = this.assets.instantiate(`models/props/egg-${nest.biome.id}.glb`);
      model.position.copy(nest.info.eggPosition);
      model.scale.setScalar(1.35);
      model.name = `egg:${nest.biome.id}`;
      model.visible = nest.hasEgg;
      this.root.add(model);
      nest.mesh = model;
    }
  }

  dispose(): void {
    this.root.traverse((node) => {
      const mesh = node as THREE.Mesh;
      if (!mesh.isMesh) return;
      mesh.geometry.dispose();
    });
    this.root.removeFromParent();
    this.colliders.clear();
  }
}

const scratchColor = new THREE.Color();
