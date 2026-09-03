import * as THREE from 'three';

import { ColliderWorld } from '@/core/Physics';
import { Rng } from '@/core/Rng';

import { Builder, shade } from './Builder';

/**
 * The safe zone: your garden, your treadmill, your shops.
 *
 * Guardians hard-disengage at its boundary, which makes the perimeter the most
 * important line in the game. It is therefore built to be unmistakable from
 * any distance and any angle -- a raised rim, a colour change underfoot, and
 * lamp posts you can see over the terrain while sprinting home with something
 * enormous behind you.
 */

export const SAFE_RADIUS = 42;
export const GROUND_Y = 2;

export interface Pedestal {
  index: number;
  position: THREE.Vector3;
  /** Where the pet model stands. */
  petAnchor: THREE.Vector3;
}

export interface Kiosk {
  id: 'shop' | 'treadmill' | 'trail' | 'rebirth' | 'index' | 'storage';
  position: THREE.Vector3;
  /** Where the player must stand to use it. */
  usePosition: THREE.Vector3;
  label: string;
}

export interface SafeZoneBuild {
  group: THREE.Group;
  pedestals: Pedestal[];
  kiosks: Kiosk[];
  spawn: THREE.Vector3;
  /** The treadmill belt's bounding box; standing on it trains Speed. */
  treadmillArea: THREE.Box3;
}

const MAX_PEDESTALS = 36;

export class SafeZone {
  private readonly rng = new Rng('safe-zone');

  build(parent: THREE.Object3D, colliders: ColliderWorld): SafeZoneBuild {
    const builder = new Builder(colliders, 'safe-zone');

    const grass = '#5aa356';
    const grassAlt = '#4d9149';
    const stone = '#9a9186';
    const stoneDark = '#6f685f';
    const wood = '#8a6a42';
    const accent = '#ffc94a';

    this.buildGround(builder, grass, grassAlt, stone);
    this.buildPerimeter(builder, stone, accent);
    const pedestals = this.buildPedestals(builder, stone, stoneDark, wood);
    const treadmill = this.buildTreadmill(builder, stoneDark, accent);
    const kiosks = this.buildKiosks(builder, wood, stone);
    this.buildDecor(builder, grass, wood);

    const group = builder.build(parent);
    return {
      group,
      pedestals,
      kiosks,
      spawn: new THREE.Vector3(0, GROUND_Y + 0.2, 12),
      treadmillArea: treadmill,
    };
  }

  private buildGround(builder: Builder, grass: string, grassAlt: string, stone: string): void {
    const tile = 10.5;
    const tiles = Math.ceil((SAFE_RADIUS * 2) / tile) + 1;
    for (let ix = 0; ix < tiles; ix++) {
      for (let iz = 0; iz < tiles; iz++) {
        const x = (ix - (tiles - 1) / 2) * tile;
        const z = (iz - (tiles - 1) / 2) * tile;
        const dist = Math.hypot(x, z);
        if (dist > SAFE_RADIUS + tile * 0.5) continue;
        const alt = (ix + iz) % 2 === 0;
        // The inner courtyard is paved; the outer ring is lawn. The change
        // underfoot is a second, peripheral cue that you have made it home.
        const paved = dist < 16;
        const color = paved
          ? (alt ? stone : shade(stone, -0.06))
          : (alt ? grass : grassAlt);
        builder.box([x, GROUND_Y * 0.5, z], [tile, GROUND_Y, tile],
          { color, roughness: 0.94 }, { noShadow: true });
      }
    }
  }

  private buildPerimeter(builder: Builder, stone: string, accent: string): void {
    const posts = 40;
    for (let i = 0; i < posts; i++) {
      const angle = (i / posts) * Math.PI * 2;
      const x = Math.cos(angle) * SAFE_RADIUS;
      const z = Math.sin(angle) * SAFE_RADIUS;
      // A low rim rather than a wall: it must read as a boundary without ever
      // being the thing that stops you getting home.
      builder.box([x, GROUND_Y + 0.35, z], [3.4, 0.7, 1.0],
        { color: stone, roughness: 0.9 }, { rotationY: angle + Math.PI / 2 });

      if (i % 5 === 0) {
        builder.box([x, GROUND_Y + 2.4, z], [0.5, 4.2, 0.5],
          { color: shade(stone, -0.2), roughness: 0.85 });
        builder.box([x, GROUND_Y + 4.8, z], [1.1, 1.1, 1.1], {
          color: accent, emissive: accent, emissiveIntensity: 2.4, roughness: 0.4,
        }, { solid: false, noShadow: true });
      }
    }
  }

  /**
   * Pedestals sit in concentric arcs facing the middle, so a full garden reads
   * as a collection on display rather than a warehouse. Every slot the player
   * could ever buy is built up front and simply hidden until unlocked -- far
   * cheaper than rebuilding geometry on every upgrade.
   */
  private buildPedestals(
    builder: Builder, stone: string, stoneDark: string, wood: string,
  ): Pedestal[] {
    const pedestals: Pedestal[] = [];
    const rings = [
      { count: 8, radius: 11, height: 1.15 },
      { count: 12, radius: 18, height: 1.15 },
      { count: 16, radius: 25.5, height: 1.15 },
    ];

    let index = 0;
    for (const ring of rings) {
      for (let i = 0; i < ring.count && index < MAX_PEDESTALS; i++, index++) {
        const angle = (i / ring.count) * Math.PI * 2 + (ring.radius * 0.03);
        const x = Math.cos(angle) * ring.radius;
        const z = Math.sin(angle) * ring.radius;
        const y = GROUND_Y;

        builder.box([x, y + ring.height * 0.5, z], [2.3, ring.height, 2.3],
          { color: stone, roughness: 0.9 }, { rotationY: angle });
        builder.box([x, y + ring.height + 0.16, z], [2.7, 0.32, 2.7],
          { color: stoneDark, roughness: 0.85 }, { rotationY: angle });
        // A small name plaque angled toward the courtyard.
        builder.box(
          [x - Math.cos(angle) * 1.25, y + ring.height * 0.62, z - Math.sin(angle) * 1.25],
          [1.5, 0.6, 0.16], { color: wood, roughness: 0.8 },
          { rotationY: angle + Math.PI / 2, solid: false, noShadow: true },
        );

        pedestals.push({
          index,
          position: new THREE.Vector3(x, y, z),
          petAnchor: new THREE.Vector3(x, y + ring.height + 0.32, z),
        });
      }
    }
    return pedestals;
  }

  private buildTreadmill(builder: Builder, frame: string, accent: string): THREE.Box3 {
    const x = 0;
    const z = -6.5;
    const y = GROUND_Y;
    const width = 4.2;
    const length = 7.5;

    builder.box([x, y + 0.45, z], [width + 1.4, 0.9, length + 1.2],
      { color: frame, roughness: 0.7, metalness: 0.25 });
    // The belt itself: a conveyor surface, so standing still on it still reads
    // as running. The gameplay effect is attached by the game loop, not here.
    builder.box([x, y + 0.98, z], [width, 0.2, length], {
      color: '#2c2f36', roughness: 0.6,
    }, { kind: 'conveyor' });

    for (let i = 0; i < 6; i++) {
      const t = (i / 5) - 0.5;
      builder.box([x, y + 1.09, z + t * (length - 1.2)], [width - 0.3, 0.06, 0.5],
        { color: '#3b3f48', roughness: 0.55 }, { solid: false, noShadow: true });
    }

    for (const side of [-1, 1]) {
      builder.box([x + side * (width / 2 + 0.55), y + 1.7, z], [0.35, 1.6, length],
        { color: frame, roughness: 0.6, metalness: 0.3 });
    }
    // Console at the front with a glowing readout.
    builder.box([x, y + 1.9, z + length / 2 + 0.4], [width + 1.0, 1.3, 0.5],
      { color: frame, roughness: 0.6, metalness: 0.3 });
    builder.box([x, y + 2.05, z + length / 2 + 0.68], [width * 0.7, 0.7, 0.1], {
      color: accent, emissive: accent, emissiveIntensity: 2.0, roughness: 0.3,
    }, { solid: false, noShadow: true });

    return new THREE.Box3(
      new THREE.Vector3(x - width / 2, y + 0.9, z - length / 2),
      new THREE.Vector3(x + width / 2, y + 3.2, z + length / 2),
    );
  }

  private buildKiosks(builder: Builder, wood: string, stone: string): Kiosk[] {
    const specs: Array<{ id: Kiosk['id']; label: string; angle: number; color: string }> = [
      { id: 'shop', label: 'Upgrades', angle: -0.7, color: '#4a90e2' },
      { id: 'treadmill', label: 'Treadmill', angle: -1.6, color: '#ffb443' },
      { id: 'trail', label: 'Trails', angle: -2.5, color: '#b072f2' },
      { id: 'index', label: 'Pet Index', angle: 0.7, color: '#6fd28a' },
      { id: 'storage', label: 'Storage', angle: 1.6, color: '#5ce1ff' },
      { id: 'rebirth', label: 'Rebirth', angle: 2.5, color: '#ff5f7e' },
    ];

    const radius = 7.2;
    const kiosks: Kiosk[] = [];
    for (const spec of specs) {
      const x = Math.cos(spec.angle) * radius;
      const z = Math.sin(spec.angle) * radius;
      const y = GROUND_Y;
      const facing = Math.atan2(-x, -z);

      builder.box([x, y + 0.9, z], [2.6, 1.8, 1.5],
        { color: wood, roughness: 0.85 }, { rotationY: facing });
      builder.box([x, y + 1.9, z], [3.0, 0.25, 1.9],
        { color: stone, roughness: 0.8 }, { rotationY: facing });
      builder.box([x, y + 3.0, z], [2.4, 1.0, 0.22], {
        color: spec.color, emissive: spec.color, emissiveIntensity: 1.6, roughness: 0.4,
      }, { rotationY: facing, solid: false, noShadow: true });
      builder.box([x - 1.2, y + 2.5, z], [0.22, 1.4, 0.22], wood,
        { rotationY: facing, solid: false });
      builder.box([x + 1.2, y + 2.5, z], [0.22, 1.4, 0.22], wood,
        { rotationY: facing, solid: false });

      const use = new THREE.Vector3(
        Math.cos(spec.angle) * (radius - 2.6),
        y,
        Math.sin(spec.angle) * (radius - 2.6),
      );
      kiosks.push({
        id: spec.id,
        position: new THREE.Vector3(x, y + 2.0, z),
        usePosition: use,
        label: spec.label,
      });
    }
    return kiosks;
  }

  private buildDecor(builder: Builder, grass: string, wood: string): void {
    for (let i = 0; i < 22; i++) {
      const angle = this.rng.float(0, Math.PI * 2);
      const radius = this.rng.float(29, SAFE_RADIUS - 3);
      const x = Math.cos(angle) * radius;
      const z = Math.sin(angle) * radius;
      const height = this.rng.float(3.2, 5.4);
      builder.box([x, GROUND_Y + height * 0.5, z], [0.75, height, 0.75], wood,
        { rotationY: this.rng.float(0, Math.PI) });
      builder.box([x, GROUND_Y + height + 0.8, z], [3.4, 1.6, 3.4],
        { color: shade(grass, -0.08), roughness: 0.92 },
        { rotationY: this.rng.float(0, Math.PI) });
    }
  }
}
