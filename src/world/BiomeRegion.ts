import * as THREE from 'three';

import { ColliderWorld } from '@/core/Physics';
import { Rng } from '@/core/Rng';
import type { BiomeDef } from '@/data/biomes';

import { Builder, shade } from './Builder';

/**
 * One biome: its ground, its props, the parkour route up to the nest, and the
 * nest itself.
 *
 * Every biome is generated from its own seeded stream, so the map is identical
 * on every load and across every player, but nothing had to be placed by hand.
 * The *shape* of each biome is deliberate though, not noise: an approach the
 * player learns, a climb that costs time, and a nest platform with exactly one
 * fast way down. That last part is the whole design -- the route in should be
 * a puzzle and the route out should be a commitment.
 */

export interface NestInfo {
  /** Where the egg sits. */
  eggPosition: THREE.Vector3;
  /** Where the player must stand to steal. */
  stealPosition: THREE.Vector3;
  /** Where the guardian sleeps. */
  guardianHome: THREE.Vector3;
  /** Ground-level entrance to the biome, for signage and the return run. */
  entrance: THREE.Vector3;
  /** Radius of the biome's playable area. */
  radius: number;
}

export interface BiomeBuildResult {
  group: THREE.Group;
  nest: NestInfo;
  center: THREE.Vector3;
  /** Platforms of the escape route, high to low, for the guardian to follow. */
  descentPath: THREE.Vector3[];
}

const GROUND_RADIUS = 46;
/** No props inside this radius: the climb has to stay legible. */
const CLIMB_CLEARANCE = 24;

export class BiomeRegion {
  readonly center: THREE.Vector3;
  private readonly rng: Rng;

  constructor(readonly def: BiomeDef) {
    this.center = new THREE.Vector3(
      Math.sin(def.bearing) * def.distance,
      0,
      -Math.cos(def.bearing) * def.distance,
    );
    this.rng = new Rng(`biome:${def.id}`);
  }

  build(parent: THREE.Object3D, colliders: ColliderWorld): BiomeBuildResult {
    const builder = new Builder(colliders, `biome-${this.def.id}`);
    const palette = this.def.palette;

    this.buildGround(builder);
    this.buildApproach(builder);
    this.buildProps(builder);

    const climb = this.buildClimb(builder);
    const nest = this.buildNest(builder, climb.top);

    // A sign at the entrance naming the biome. In first person you can walk in
    // from any angle, so the zone has to announce itself in the world.
    const entrance = this.entrancePoint();
    builder.box(
      [entrance.x, 2.6, entrance.z], [5.2, 1.1, 0.35],
      { color: palette.nestAlt, roughness: 0.7 }, { solid: false },
    );
    builder.box([entrance.x - 2.4, 1.3, entrance.z], [0.42, 2.6, 0.42], palette.nest);
    builder.box([entrance.x + 2.4, 1.3, entrance.z], [0.42, 2.6, 0.42], palette.nest);

    const group = builder.build(parent);
    group.name = `biome:${this.def.id}`;

    return {
      group,
      nest: { ...nest, entrance, radius: GROUND_RADIUS },
      center: this.center.clone(),
      descentPath: climb.platforms.slice().reverse(),
    };
  }

  private entrancePoint(): THREE.Vector3 {
    // On the side of the biome facing the safe zone.
    const toBase = this.center.clone().negate().setY(0).normalize();
    return this.center.clone().addScaledVector(toBase, GROUND_RADIUS - 2).setY(0);
  }

  // -- ground ---------------------------------------------------------------

  private buildGround(builder: Builder): void {
    const palette = this.def.palette;
    const terrain = this.def.terrain;

    // A ring of chunky tiles rather than one slab: the seams read as ground
    // texture at this art scale, and it lets hazards be tiles too.
    const tile = 11.5;
    const tiles = Math.ceil((GROUND_RADIUS * 2) / tile);
    for (let ix = 0; ix < tiles; ix++) {
      for (let iz = 0; iz < tiles; iz++) {
        const x = this.center.x + (ix - (tiles - 1) / 2) * tile;
        const z = this.center.z + (iz - (tiles - 1) / 2) * tile;
        const dist = Math.hypot(x - this.center.x, z - this.center.z);
        if (dist > GROUND_RADIUS) continue;

        const alt = (ix + iz) % 2 === 0;
        let color = alt ? palette.ground : palette.groundAlt;
        let kind: 'solid' | 'ice' | 'kill' | 'sticky' = 'solid';
        let height = 2.0 + this.rng.float(-0.12, 0.12);

        if (terrain === 'ice') kind = 'ice';
        if (terrain === 'bone' && this.rng.bool(0.08)) {
          color = '#241c18';
          kind = 'sticky';
        }
        if ((terrain === 'lava' || terrain === 'deep') && dist > 20 && this.rng.bool(0.16)) {
          // Molten seams and abyssal trenches: lethal, and always visible from
          // a distance because they are emissive.
          color = terrain === 'lava' ? '#ff5a17' : '#0a1a24';
          kind = terrain === 'lava' ? 'kill' : 'solid';
          height = 1.55;
        }
        if (terrain === 'water' && dist > 26 && this.rng.bool(0.4)) {
          color = palette.accent;
          height = 1.3;
        }

        const emissive = color === '#ff5a17'
          ? { color, emissive: '#ff7a2a', emissiveIntensity: 1.4, roughness: 0.6 }
          : { color, roughness: 0.92 };
        builder.box([x, height * 0.5, z], [tile, height, tile], emissive, {
          kind, noShadow: true,
        });
      }
    }
  }

  /**
   * A raised causeway from the biome's edge back toward the safe zone. It is
   * the fast way home, and being *on* it while a guardian is behind you is the
   * game's best moment, so it is deliberately narrow and railing-free.
   */
  private buildApproach(builder: Builder): void {
    const palette = this.def.palette;
    const entrance = this.entrancePoint();
    const inward = this.center.clone().sub(entrance).setY(0).normalize();
    const outward = inward.clone().negate();

    const segments = 9;
    for (let i = 0; i < segments; i++) {
      const t = i / segments;
      const point = entrance.clone().addScaledVector(outward, t * 26);
      const width = 5.6 - t * 1.6;
      builder.box(
        [point.x, 2.2, point.z], [width, 0.55, 4.6],
        { color: i % 2 === 0 ? palette.nest : palette.nestAlt, roughness: 0.8 },
        { rotationY: Math.atan2(outward.x, outward.z) },
      );
    }
  }

  private buildProps(builder: Builder): void {
    const terrain = this.def.terrain;
    const palette = this.def.palette;
    const count = 46;

    for (let i = 0; i < count; i++) {
      const angle = this.rng.float(0, Math.PI * 2);
      const radius = Math.sqrt(this.rng.float(0.05, 1)) * (GROUND_RADIUS - 6);
      const x = this.center.x + Math.cos(angle) * radius;
      const z = this.center.z + Math.sin(angle) * radius;
      // Keep the whole climb clear, not just the nest column. Props growing up
      // through the parkour route are the fastest way to make an ascent
      // unreadable from the ground, which is exactly where the player reads it.
      if (Math.hypot(x - this.center.x, z - this.center.z) < CLIMB_CLEARANCE) continue;
      const y = 2.0;
      const rotation = this.rng.float(0, Math.PI);

      switch (terrain) {
        case 'meadow':
          this.tree(builder, x, y, z, rotation, palette.accent, palette.rock);
          break;
        case 'water':
          this.reed(builder, x, y, z, palette.accent, palette.accentAlt);
          break;
        case 'dunes':
          this.cactus(builder, x, y, z, rotation, palette.accent);
          break;
        case 'canopy':
          this.jungleTree(builder, x, y, z, rotation, palette.accent, palette.rock);
          break;
        case 'ice':
          this.icicle(builder, x, y, z, palette.accent, palette.accentAlt);
          break;
        case 'lava':
          this.basalt(builder, x, y, z, rotation, palette.rock, palette.accent);
          break;
        case 'deep':
          this.coral(builder, x, y, z, palette.accent, palette.accentAlt);
          break;
        case 'bone':
          this.bones(builder, x, y, z, rotation, palette.accentAlt);
          break;
        case 'void':
          this.shard(builder, x, y, z, rotation, palette.accent, palette.accentAlt);
          break;
        case 'garden':
          this.blossomTree(builder, x, y, z, rotation, palette.accent, palette.rock);
          break;
        default:
          this.pillar(builder, x, y, z, rotation, palette.rock, palette.accent);
          break;
      }
    }
  }

  // -- prop vocabulary -------------------------------------------------------

  private tree(b: Builder, x: number, y: number, z: number, rot: number,
               leaf: string, bark: string): void {
    const height = this.rng.float(3.4, 6.2);
    b.box([x, y + height * 0.5, z], [0.85, height, 0.85], bark, { rotationY: rot });
    for (let i = 0; i < 3; i++) {
      const t = i / 2;
      const size = 4.2 - t * 1.5;
      b.box([x, y + height + t * 1.5, z], [size, 1.5, size],
        { color: shade(leaf, -t * 0.05), roughness: 0.92 }, { rotationY: rot + t * 0.4 });
    }
  }

  private jungleTree(b: Builder, x: number, y: number, z: number, rot: number,
                     leaf: string, bark: string): void {
    const height = this.rng.float(7, 13);
    b.box([x, y + height * 0.5, z], [1.05, height, 1.05], bark, { rotationY: rot });
    b.box([x, y + height + 0.9, z], [6.5, 1.8, 6.5], leaf, { rotationY: rot });
    b.box([x, y + height + 2.3, z], [4.4, 1.4, 4.4], shade(leaf, 0.06), { rotationY: rot * 1.7 });
    // Hanging vines: pure decoration, but they sell the density.
    for (let i = 0; i < 3; i++) {
      const vx = x + this.rng.float(-2.4, 2.4);
      const vz = z + this.rng.float(-2.4, 2.4);
      const len = this.rng.float(2, 5);
      b.box([vx, y + height - len * 0.5 + 0.5, vz], [0.2, len, 0.2],
        shade(leaf, -0.12), { decorative: true, noShadow: true });
    }
  }

  private reed(b: Builder, x: number, y: number, z: number,
               stem: string, tip: string): void {
    const count = this.rng.int(2, 5);
    for (let i = 0; i < count; i++) {
      const height = this.rng.float(1.6, 3.4);
      const rx = x + this.rng.float(-1.2, 1.2);
      const rz = z + this.rng.float(-1.2, 1.2);
      b.box([rx, y + height * 0.5, rz], [0.22, height, 0.22], stem,
        { decorative: true, noShadow: true });
      b.box([rx, y + height + 0.25, rz], [0.34, 0.6, 0.34], tip,
        { decorative: true, noShadow: true });
    }
  }

  private cactus(b: Builder, x: number, y: number, z: number, rot: number,
                 color: string): void {
    const height = this.rng.float(2.4, 4.6);
    b.box([x, y + height * 0.5, z], [1.0, height, 1.0], color, { rotationY: rot });
    if (this.rng.bool(0.6)) {
      const side = this.rng.bool() ? 1 : -1;
      b.box([x + side * 0.95, y + height * 0.62, z], [0.9, 0.75, 0.75], color,
        { rotationY: rot });
      b.box([x + side * 1.32, y + height * 0.92, z], [0.75, 1.5, 0.75], color,
        { rotationY: rot });
    }
  }

  private icicle(b: Builder, x: number, y: number, z: number,
                 color: string, tip: string): void {
    const height = this.rng.float(1.8, 4.5);
    b.box([x, y + height * 0.5, z], [1.1, height, 1.1],
      { color, roughness: 0.35, opacity: 0.94, transparent: true });
    b.box([x, y + height + 0.6, z], [0.6, 1.2, 0.6],
      { color: tip, roughness: 0.25 });
  }

  private basalt(b: Builder, x: number, y: number, z: number, rot: number,
                 rock: string, glow: string): void {
    const height = this.rng.float(1.8, 4.8);
    b.box([x, y + height * 0.5, z], [2.0, height, 2.0], rock, { rotationY: rot });
    if (this.rng.bool(0.45)) {
      b.box([x, y + height * 0.35, z], [2.06, 0.35, 2.06],
        { color: glow, emissive: glow, emissiveIntensity: 2.2, roughness: 0.5 },
        { solid: false, noShadow: true });
    }
  }

  private coral(b: Builder, x: number, y: number, z: number,
                color: string, glow: string): void {
    const height = this.rng.float(1.6, 4.2);
    b.box([x, y + height * 0.5, z], [1.1, height, 1.1], color);
    const arms = this.rng.int(2, 4);
    for (let i = 0; i < arms; i++) {
      const angle = (i / arms) * Math.PI * 2;
      b.box(
        [x + Math.cos(angle) * 0.9, y + height * 0.75, z + Math.sin(angle) * 0.9],
        [0.55, height * 0.55, 0.55],
        { color: glow, emissive: glow, emissiveIntensity: 1.5, roughness: 0.5 },
        { decorative: true, noShadow: true },
      );
    }
  }

  private bones(b: Builder, x: number, y: number, z: number, rot: number,
                color: string): void {
    if (this.rng.bool(0.45)) {
      // Ribcage: an arch you can actually run through.
      for (let i = 0; i < 5; i++) {
        const t = i / 4;
        const h = 3.4 - Math.abs(t - 0.5) * 2.2;
        b.box([x + (t - 0.5) * 5, y + h * 0.5, z], [0.42, h, 0.42], color,
          { rotationY: rot });
      }
      b.box([x, y + 3.2, z], [5.2, 0.42, 0.42], color, { rotationY: rot });
    } else {
      b.box([x, y + 0.8, z], [2.4, 1.6, 1.8], color, { rotationY: rot });
      b.box([x, y + 1.7, z], [1.3, 0.5, 1.3], shade(color, -0.08), { rotationY: rot });
    }
  }

  private shard(b: Builder, x: number, y: number, z: number, rot: number,
                rock: string, glow: string): void {
    const height = this.rng.float(2.5, 7);
    b.box([x, y + height * 0.5, z], [1.4, height, 1.4], rock,
      { rotationY: rot });
    b.box([x, y + height + 0.7, z], [0.7, 1.4, 0.7],
      { color: glow, emissive: glow, emissiveIntensity: 2.4, roughness: 0.3 },
      { noShadow: true });
  }

  private blossomTree(b: Builder, x: number, y: number, z: number, rot: number,
                      blossom: string, bark: string): void {
    const height = this.rng.float(4, 7);
    b.box([x, y + height * 0.5, z], [0.8, height, 0.8], bark, { rotationY: rot });
    for (let i = 0; i < 4; i++) {
      const angle = rot + (i / 4) * Math.PI * 2;
      b.box(
        [x + Math.cos(angle) * 1.7, y + height + 0.3, z + Math.sin(angle) * 1.7],
        [3.0, 1.0, 3.0], shade(blossom, i % 2 ? 0.05 : -0.02),
        { rotationY: angle, noShadow: true },
      );
    }
    b.box([x, y + height + 1.1, z], [3.2, 1.0, 3.2], blossom, { noShadow: true });
  }

  private pillar(b: Builder, x: number, y: number, z: number, rot: number,
                 stone: string, glow: string): void {
    const height = this.rng.float(3, 9);
    const broken = this.rng.bool(0.4);
    b.box([x, y + height * 0.5, z], [1.8, height, 1.8], stone, { rotationY: rot });
    b.box([x, y + height + 0.3, z], [2.4, 0.6, 2.4], shade(stone, 0.08),
      { rotationY: rot });
    if (!broken) {
      b.box([x, y + height + 1.0, z], [0.9, 0.9, 0.9],
        { color: glow, emissive: glow, emissiveIntensity: 2.0, roughness: 0.4 },
        { noShadow: true });
    }
  }

  // -- the climb ------------------------------------------------------------

  /**
   * A spiral of platforms rising to the nest.
   *
   * Gaps grow with biome order, but only up to what the player's Speed at that
   * gate can clear -- the jump has to be intimidating, never impossible. The
   * last platform is deliberately placed so that the *only* quick way down is
   * a straight drop toward the causeway, which is what turns the escape into a
   * decision instead of a retrace.
   */
  private buildClimb(builder: Builder): { top: THREE.Vector3; platforms: THREE.Vector3[] } {
    const palette = this.def.palette;
    const order = this.def.order;
    const steps = 6 + Math.min(6, Math.floor(order * 0.7));
    const platforms: THREE.Vector3[] = [];

    const startAngle = this.rng.float(0, Math.PI * 2);
    const radius = 15 + order * 0.5;
    const rise = 2.6 + order * 0.16;

    for (let i = 0; i < steps; i++) {
      const t = i / (steps - 1);
      const angle = startAngle + t * Math.PI * 1.65;
      const r = radius * (1 - t * 0.55);
      const x = this.center.x + Math.cos(angle) * r;
      const z = this.center.z + Math.sin(angle) * r;
      const y = 2.4 + rise * i;

      const size = 4.6 - t * 1.6;
      let kind: 'solid' | 'ice' | 'bounce' | 'crumble' = 'solid';
      let color = i % 2 === 0 ? palette.nest : palette.nestAlt;

      // One bounce pad partway up in every biome past the first: it is the
      // shortcut the player learns, and the thing that makes the run home fast.
      if (i === Math.floor(steps * 0.55) && order > 0) {
        kind = 'bounce';
        color = palette.accentAlt;
      } else if (this.def.terrain === 'ice' && i % 3 === 1) {
        kind = 'ice';
        color = palette.accent;
      }

      builder.box([x, y, z], [size, 0.7, size], {
        color,
        roughness: kind === 'ice' ? 0.2 : 0.85,
        emissive: kind === 'bounce' ? color : undefined,
        emissiveIntensity: kind === 'bounce' ? 1.2 : 0,
      }, { kind });

      // A support column under every platform. Floating slabs read as debris;
      // columns read as a structure, and they give the player a vertical
      // reference for how high they have climbed -- which first person
      // otherwise takes away entirely.
      if (i > 0) {
        const columnHeight = y - 2.2;
        if (columnHeight > 0.6) {
          builder.box([x, 2.2 + columnHeight * 0.5, z], [0.85, columnHeight, 0.85],
            { color: palette.rock, roughness: 0.9 }, { solid: false, noShadow: true });
        }
      }

      platforms.push(new THREE.Vector3(x, y + 0.35, z));
    }

    // An arch over the first platform. Without an obvious entrance the player
    // circles the base looking for "the way up"; with one they just go.
    const first = platforms[0];
    const toCenter = Math.atan2(this.center.x - first.x, this.center.z - first.z);
    for (const side of [-1, 1]) {
      builder.box(
        [first.x + Math.cos(toCenter) * side * 2.6, first.y + 2.2,
         first.z - Math.sin(toCenter) * side * 2.6],
        [0.6, 4.4, 0.6], { color: palette.nestAlt, roughness: 0.8 },
      );
    }
    builder.box([first.x, first.y + 4.6, first.z], [6.0, 0.7, 1.0],
      { color: palette.accent, roughness: 0.75 },
      { rotationY: toCenter, solid: false });

    return { top: platforms[platforms.length - 1].clone(), platforms };
  }

  private buildNest(builder: Builder, top: THREE.Vector3): Omit<NestInfo, 'entrance' | 'radius'> {
    const palette = this.def.palette;
    const platformY = top.y + 2.4;
    const pad = new THREE.Vector3(this.center.x, platformY, this.center.z);

    // The nest platform itself: wide enough to fight for footing on, small
    // enough that a panicked backwards step is a real risk.
    builder.box([pad.x, pad.y - 0.45, pad.z], [11, 0.9, 11],
      { color: palette.nest, roughness: 0.88 });
    // The nest sits on a broad plinth that reaches the ground. It is the
    // biome's landmark -- the thing you navigate by from the road -- so it
    // needs mass, not a pole.
    const plinthHeight = pad.y - 2.2;
    builder.box([pad.x, 2.2 + plinthHeight * 0.5, pad.z],
      [5.2, plinthHeight, 5.2],
      { color: palette.rock, roughness: 0.92 }, { solid: false, noShadow: true });
    builder.box([pad.x, pad.y - 1.1, pad.z], [7.4, 1.4, 7.4],
      { color: shade(palette.rock, -0.06), roughness: 0.9 }, { solid: false });

    // A ring of woven twigs / stones around the egg.
    const ringCount = 14;
    for (let i = 0; i < ringCount; i++) {
      const angle = (i / ringCount) * Math.PI * 2;
      const r = 2.5;
      builder.box(
        [pad.x + Math.cos(angle) * r, pad.y + 0.5, pad.z + Math.sin(angle) * r],
        [1.5, 0.9, 0.55], { color: palette.nestAlt, roughness: 0.9 },
        { rotationY: angle + Math.PI / 2 },
      );
    }
    builder.box([pad.x, pad.y + 0.28, pad.z], [4.4, 0.35, 4.4],
      { color: shade(palette.nestAlt, -0.1), roughness: 0.92 });

    // A short ramp from the last climb platform onto the nest pad, so the final
    // approach is a commitment rather than a coin-flip jump.
    const toPad = pad.clone().sub(top).setY(0);
    const rampAngle = Math.atan2(toPad.x, toPad.z);
    const rampMid = top.clone().lerp(pad, 0.5);
    builder.box([rampMid.x, (top.y + pad.y) * 0.5 - 0.2, rampMid.z],
      [3.2, 0.6, toPad.length() + 1.5],
      { color: palette.nestAlt, roughness: 0.85 }, { rotationY: rampAngle });

    const guardianHome = new THREE.Vector3(
      pad.x + Math.cos(this.def.bearing + 1.2) * 3.6,
      pad.y + 0.6,
      pad.z + Math.sin(this.def.bearing + 1.2) * 3.6,
    );

    return {
      eggPosition: new THREE.Vector3(pad.x, pad.y + 1.0, pad.z),
      stealPosition: new THREE.Vector3(pad.x, pad.y + 0.5, pad.z),
      guardianHome,
    };
  }
}
