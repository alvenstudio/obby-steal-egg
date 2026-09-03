import * as THREE from 'three';
import { mergeGeometries } from 'three/examples/jsm/utils/BufferGeometryUtils.js';

import { ColliderWorld, SurfaceKind } from '@/core/Physics';

/**
 * Level geometry builder.
 *
 * The whole map is axis-aligned boxes, so this accumulates them per colour and
 * emits one merged mesh per material at the end. A biome that would otherwise
 * be two thousand separate draw calls becomes about a dozen.
 *
 * It also registers the matching collider as each box is added, which is the
 * point: level geometry and collision are described once, together, and cannot
 * drift apart the way they do when the art and the collision are separate
 * passes.
 */

export interface BoxOptions {
  /** Register a collider for this box. Default true. */
  solid?: boolean;
  kind?: SurfaceKind;
  /** Rotation about Y, radians. Rotated boxes get an AABB that contains them. */
  rotationY?: number;
  /** Skip the collider but keep the visual (foliage, banners, decals). */
  decorative?: boolean;
  owner?: unknown;
  /** Emissive strength for neon parts. */
  emissive?: number;
  /** Render but do not cast shadows — cheap for small clutter. */
  noShadow?: boolean;
}

export interface MaterialSpec {
  color: string;
  roughness?: number;
  metalness?: number;
  emissive?: string;
  emissiveIntensity?: number;
  transparent?: boolean;
  opacity?: number;
  flat?: boolean;
}

const boxGeometry = new THREE.BoxGeometry(1, 1, 1);

export class Builder {
  readonly group = new THREE.Group();

  private buckets = new Map<string, { spec: MaterialSpec; geometries: THREE.BufferGeometry[]; noShadow: boolean }>();
  private matrix = new THREE.Matrix4();
  private quaternion = new THREE.Quaternion();
  private euler = new THREE.Euler();
  private scale = new THREE.Vector3();
  private position = new THREE.Vector3();
  private colliderCount = 0;

  constructor(
    private readonly colliders: ColliderWorld,
    name = 'chunk',
  ) {
    this.group.name = name;
  }

  get boxCount(): number {
    let total = 0;
    for (const bucket of this.buckets.values()) total += bucket.geometries.length;
    return total;
  }

  get colliders_(): number {
    return this.colliderCount;
  }

  /**
   * Add one box. `center` is its centre, `size` its full extents.
   *
   * Materials are keyed by their spec so two calls with the same colour share
   * a bucket; passing a fresh object each time is fine.
   */
  box(
    center: THREE.Vector3 | [number, number, number],
    size: THREE.Vector3 | [number, number, number],
    material: MaterialSpec | string,
    options: BoxOptions = {},
  ): this {
    const spec: MaterialSpec = typeof material === 'string' ? { color: material } : material;
    const key = materialKey(spec, options.noShadow ?? false);

    let bucket = this.buckets.get(key);
    if (!bucket) {
      bucket = { spec, geometries: [], noShadow: options.noShadow ?? false };
      this.buckets.set(key, bucket);
    }

    const c = Array.isArray(center) ? this.position.set(center[0], center[1], center[2])
      : this.position.copy(center);
    const s = Array.isArray(size) ? this.scale.set(size[0], size[1], size[2])
      : this.scale.copy(size);

    const rotationY = options.rotationY ?? 0;
    this.euler.set(0, rotationY, 0);
    this.quaternion.setFromEuler(this.euler);
    this.matrix.compose(c, this.quaternion, s);

    const geometry = boxGeometry.clone();
    geometry.applyMatrix4(this.matrix);
    bucket.geometries.push(geometry);

    if (options.solid !== false && !options.decorative) {
      // A rotated box gets the AABB that contains it. Slightly generous
      // collision on angled props is far better than the player clipping into
      // a rock, and nothing in the level design depends on tight fits.
      const half = rotationY === 0
        ? new THREE.Vector3(s.x * 0.5, s.y * 0.5, s.z * 0.5)
        : rotatedHalfExtents(s, rotationY);
      this.colliders.add(
        c.clone().sub(half),
        c.clone().add(half),
        options.kind ?? 'solid',
        options.owner,
      );
      this.colliderCount++;
    }

    return this;
  }

  /** A flat platform: convenience for the obby, which is nearly all of these. */
  platform(
    x: number, y: number, z: number,
    width: number, depth: number,
    material: MaterialSpec | string,
    thickness = 0.6,
    options: BoxOptions = {},
  ): this {
    return this.box([x, y - thickness * 0.5, z], [width, thickness, depth], material, options);
  }

  /** Four walls around a rectangle — arenas, pens, ruins. */
  enclosure(
    center: THREE.Vector3, width: number, depth: number, height: number,
    thickness: number, material: MaterialSpec | string, options: BoxOptions = {},
  ): this {
    const y = center.y + height * 0.5;
    this.box([center.x, y, center.z - depth / 2], [width, height, thickness], material, options);
    this.box([center.x, y, center.z + depth / 2], [width, height, thickness], material, options);
    this.box([center.x - width / 2, y, center.z], [thickness, height, depth], material, options);
    this.box([center.x + width / 2, y, center.z], [thickness, height, depth], material, options);
    return this;
  }

  /** Finalise into merged meshes and add them to `parent`. */
  build(parent: THREE.Object3D): THREE.Group {
    for (const [key, bucket] of this.buckets) {
      if (bucket.geometries.length === 0) continue;
      const merged = bucket.geometries.length === 1
        ? bucket.geometries[0]
        : mergeGeometries(bucket.geometries, false);
      if (!merged) continue;
      merged.computeBoundingSphere();

      const mesh = new THREE.Mesh(merged, makeMaterial(bucket.spec));
      mesh.name = `${this.group.name}:${key}`;
      mesh.castShadow = !bucket.noShadow;
      mesh.receiveShadow = true;
      this.group.add(mesh);

      // The per-box clones have been merged; release them.
      if (bucket.geometries.length > 1) {
        for (const geometry of bucket.geometries) geometry.dispose();
      }
      bucket.geometries.length = 0;
    }
    parent.add(this.group);
    return this.group;
  }

  dispose(): void {
    this.group.traverse((node) => {
      const mesh = node as THREE.Mesh;
      if (!mesh.isMesh) return;
      mesh.geometry.dispose();
      const materials = Array.isArray(mesh.material) ? mesh.material : [mesh.material];
      for (const material of materials) material.dispose();
    });
    this.group.removeFromParent();
    this.buckets.clear();
  }
}

function rotatedHalfExtents(size: THREE.Vector3, rotationY: number): THREE.Vector3 {
  const cos = Math.abs(Math.cos(rotationY));
  const sin = Math.abs(Math.sin(rotationY));
  return new THREE.Vector3(
    (size.x * cos + size.z * sin) * 0.5,
    size.y * 0.5,
    (size.x * sin + size.z * cos) * 0.5,
  );
}

function materialKey(spec: MaterialSpec, noShadow: boolean): string {
  return [
    spec.color,
    spec.roughness ?? 0.85,
    spec.metalness ?? 0,
    spec.emissive ?? '',
    spec.emissiveIntensity ?? 0,
    spec.opacity ?? 1,
    spec.flat ? 'f' : 's',
    noShadow ? 'n' : 'c',
  ].join('|');
}

const materialCache = new Map<string, THREE.MeshStandardMaterial>();

export function makeMaterial(spec: MaterialSpec): THREE.MeshStandardMaterial {
  const key = materialKey(spec, false);
  const cached = materialCache.get(key);
  if (cached) return cached;

  const material = new THREE.MeshStandardMaterial({
    color: new THREE.Color(spec.color),
    roughness: spec.roughness ?? 0.85,
    metalness: spec.metalness ?? 0,
    flatShading: spec.flat ?? false,
    transparent: spec.transparent ?? (spec.opacity !== undefined && spec.opacity < 1),
    opacity: spec.opacity ?? 1,
  });
  if (spec.emissive) {
    material.emissive = new THREE.Color(spec.emissive);
    material.emissiveIntensity = spec.emissiveIntensity ?? 1;
  }
  materialCache.set(key, material);
  return material;
}

/** Nudge a hex colour's lightness — for stripes, bands and shaded faces. */
export function shade(hex: string, amount: number): string {
  const color = new THREE.Color(hex);
  const hsl = { h: 0, s: 0, l: 0 };
  color.getHSL(hsl);
  color.setHSL(hsl.h, hsl.s, THREE.MathUtils.clamp(hsl.l + amount, 0, 1));
  return `#${color.getHexString()}`;
}
