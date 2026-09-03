import * as THREE from 'three';

/**
 * Static-world collision for an axis-aligned-box level.
 *
 * The whole game is built from boxes (platforms, walls, crates, nest rims), so
 * an AABB world with a uniform-grid broadphase is both exact and fast. Nothing
 * here is a general physics engine on purpose: an obby needs *predictable*
 * collision far more than it needs a solver, and a player who can reproduce a
 * jump is worth more than one who can push a barrel.
 */

export type SurfaceKind =
  | 'solid'
  | 'ice'      // low friction
  | 'bounce'   // launches on landing
  | 'sticky'   // high friction, no slide
  | 'kill'     // resets the player
  | 'conveyor' // pushes along `drift`
  | 'crumble'; // vanishes shortly after being stood on

export interface Collider {
  id: number;
  min: THREE.Vector3;
  max: THREE.Vector3;
  kind: SurfaceKind;
  /** Conveyor push / moving-platform velocity, world units per second. */
  drift?: THREE.Vector3;
  /** Set false to disable without removing (crumbling platforms). */
  active: boolean;
  /** Free-form link back to whatever gameplay object owns this box. */
  owner?: unknown;
}

export interface MoveResult {
  position: THREE.Vector3;
  velocity: THREE.Vector3;
  grounded: boolean;
  ground: Collider | null;
  hitCeiling: boolean;
  hitWall: boolean;
  /** Surface the player is standing on, if any. */
  groundKind: SurfaceKind | null;
  /** How far the mover was stepped up this frame, for camera smoothing. */
  steppedUp: number;
}

const CELL_SIZE = 8;

function cellKey(x: number, z: number): number {
  // Pack two 16-bit signed cell coords into one number for a Map key.
  return ((x + 32768) << 16) | (z + 32768);
}

export class ColliderWorld {
  private colliders = new Map<number, Collider>();
  private grid = new Map<number, number[]>();
  private nextId = 1;

  add(
    min: THREE.Vector3,
    max: THREE.Vector3,
    kind: SurfaceKind = 'solid',
    owner?: unknown,
    drift?: THREE.Vector3,
  ): Collider {
    const collider: Collider = {
      id: this.nextId++,
      min: min.clone(),
      max: max.clone(),
      kind,
      active: true,
      owner,
      drift,
    };
    this.colliders.set(collider.id, collider);
    this.index(collider);
    return collider;
  }

  /** Convenience: a box given its centre and full size. */
  addBox(
    center: THREE.Vector3,
    size: THREE.Vector3,
    kind: SurfaceKind = 'solid',
    owner?: unknown,
  ): Collider {
    const half = size.clone().multiplyScalar(0.5);
    return this.add(center.clone().sub(half), center.clone().add(half), kind, owner);
  }

  remove(collider: Collider): void {
    this.colliders.delete(collider.id);
    this.unindex(collider);
  }

  clear(): void {
    this.colliders.clear();
    this.grid.clear();
    this.nextId = 1;
  }

  get count(): number {
    return this.colliders.size;
  }

  all(): Iterable<Collider> {
    return this.colliders.values();
  }

  private index(collider: Collider): void {
    const x0 = Math.floor(collider.min.x / CELL_SIZE);
    const x1 = Math.floor(collider.max.x / CELL_SIZE);
    const z0 = Math.floor(collider.min.z / CELL_SIZE);
    const z1 = Math.floor(collider.max.z / CELL_SIZE);
    for (let x = x0; x <= x1; x++) {
      for (let z = z0; z <= z1; z++) {
        const key = cellKey(x, z);
        let bucket = this.grid.get(key);
        if (!bucket) {
          bucket = [];
          this.grid.set(key, bucket);
        }
        bucket.push(collider.id);
      }
    }
  }

  private unindex(collider: Collider): void {
    const x0 = Math.floor(collider.min.x / CELL_SIZE);
    const x1 = Math.floor(collider.max.x / CELL_SIZE);
    const z0 = Math.floor(collider.min.z / CELL_SIZE);
    const z1 = Math.floor(collider.max.z / CELL_SIZE);
    for (let x = x0; x <= x1; x++) {
      for (let z = z0; z <= z1; z++) {
        const bucket = this.grid.get(cellKey(x, z));
        if (!bucket) continue;
        const at = bucket.indexOf(collider.id);
        if (at >= 0) bucket.splice(at, 1);
      }
    }
  }

  /** Every collider whose cell overlaps the query box. May contain duplicates. */
  query(min: THREE.Vector3, max: THREE.Vector3, out: Collider[] = []): Collider[] {
    out.length = 0;
    const seen = new Set<number>();
    const x0 = Math.floor(min.x / CELL_SIZE);
    const x1 = Math.floor(max.x / CELL_SIZE);
    const z0 = Math.floor(min.z / CELL_SIZE);
    const z1 = Math.floor(max.z / CELL_SIZE);
    for (let x = x0; x <= x1; x++) {
      for (let z = z0; z <= z1; z++) {
        const bucket = this.grid.get(cellKey(x, z));
        if (!bucket) continue;
        for (const id of bucket) {
          if (seen.has(id)) continue;
          seen.add(id);
          const collider = this.colliders.get(id);
          if (collider && collider.active) out.push(collider);
        }
      }
    }
    return out;
  }

  /** Straight ray-vs-AABB, used for ground probes and guardian line of sight. */
  raycast(
    origin: THREE.Vector3,
    direction: THREE.Vector3,
    maxDistance: number,
  ): { collider: Collider; distance: number } | null {
    const end = origin.clone().addScaledVector(direction, maxDistance);
    const min = new THREE.Vector3(
      Math.min(origin.x, end.x), Math.min(origin.y, end.y), Math.min(origin.z, end.z),
    );
    const max = new THREE.Vector3(
      Math.max(origin.x, end.x), Math.max(origin.y, end.y), Math.max(origin.z, end.z),
    );
    const candidates = this.query(min, max);

    let best: { collider: Collider; distance: number } | null = null;
    for (const collider of candidates) {
      const hit = raySlab(origin, direction, collider.min, collider.max, maxDistance);
      if (hit !== null && (best === null || hit < best.distance)) {
        best = { collider, distance: hit };
      }
    }
    return best;
  }
}

/** Slab test. Returns entry distance, or null when the ray misses. */
export function raySlab(
  origin: THREE.Vector3,
  direction: THREE.Vector3,
  min: THREE.Vector3,
  max: THREE.Vector3,
  maxDistance: number,
): number | null {
  let tmin = 0;
  let tmax = maxDistance;
  const o = [origin.x, origin.y, origin.z];
  const d = [direction.x, direction.y, direction.z];
  const lo = [min.x, min.y, min.z];
  const hi = [max.x, max.y, max.z];

  for (let axis = 0; axis < 3; axis++) {
    if (Math.abs(d[axis]) < 1e-8) {
      if (o[axis] < lo[axis] || o[axis] > hi[axis]) return null;
      continue;
    }
    const inv = 1 / d[axis];
    let t1 = (lo[axis] - o[axis]) * inv;
    let t2 = (hi[axis] - o[axis]) * inv;
    if (t1 > t2) [t1, t2] = [t2, t1];
    tmin = Math.max(tmin, t1);
    tmax = Math.min(tmax, t2);
    if (tmin > tmax) return null;
  }
  return tmin;
}

export interface MoverShape {
  /** Half the width/depth of the player's box. */
  radius: number;
  /** Full height from feet to top of head. */
  height: number;
  /** Maximum ledge height that gets stepped over instead of blocking. */
  stepHeight: number;
}

const scratchMin = new THREE.Vector3();
const scratchMax = new THREE.Vector3();
const scratchList: Collider[] = [];

function boxFor(position: THREE.Vector3, shape: MoverShape): void {
  scratchMin.set(position.x - shape.radius, position.y, position.z - shape.radius);
  scratchMax.set(position.x + shape.radius, position.y + shape.height, position.z + shape.radius);
}

function overlaps(collider: Collider): boolean {
  return (
    scratchMin.x < collider.max.x &&
    scratchMax.x > collider.min.x &&
    scratchMin.y < collider.max.y &&
    scratchMax.y > collider.min.y &&
    scratchMin.z < collider.max.z &&
    scratchMax.z > collider.min.z
  );
}

/**
 * Move an axis-aligned box through the world.
 *
 * This wrapper exists for one reason: tunnelling. Resolution only fires when
 * the box *overlaps* something after moving, so a fast mover crossing a thin
 * platform in a single step would pass straight through it. Sprint speed
 * reaches ~40 u/s late in the game and terminal fall speed is higher still,
 * which at any realistic frame time is more than a 0.55-unit platform is
 * thick. Splitting the move into steps no larger than half the box's smallest
 * extent makes that impossible, and costs nothing at normal speeds because
 * the loop runs exactly once.
 */
export function moveBox(
  world: ColliderWorld,
  position: THREE.Vector3,
  velocity: THREE.Vector3,
  shape: MoverShape,
  dt: number,
): MoveResult {
  const travel = Math.max(
    Math.abs(velocity.x), Math.abs(velocity.y), Math.abs(velocity.z),
  ) * dt;
  const limit = Math.max(0.05, Math.min(shape.radius, shape.height * 0.5) * 0.8);
  const steps = Math.min(8, Math.max(1, Math.ceil(travel / limit)));
  if (steps === 1) return moveBoxStep(world, position, velocity, shape, dt);

  let result = moveBoxStep(world, position, velocity, shape, dt / steps);
  for (let i = 1; i < steps; i++) {
    const next = moveBoxStep(world, result.position, result.velocity, shape, dt / steps);
    // Any contact within the substep chain has to survive to the caller, or a
    // fast landing would report as airborne on the frame it actually touched.
    next.grounded = next.grounded || result.grounded;
    next.hitWall = next.hitWall || result.hitWall;
    next.hitCeiling = next.hitCeiling || result.hitCeiling;
    next.steppedUp += result.steppedUp;
    if (!next.ground && result.ground) {
      next.ground = result.ground;
      next.groundKind = result.groundKind;
    }
    result = next;
  }
  return result;
}

/**
 * One collision step, resolving a single axis at a time.
 *
 * Axis-separated resolution is what makes wall-sliding feel right: blocking X
 * does not eat the player's Z motion, so running into a corner still slides
 * you along it rather than stopping you dead.
 */
function moveBoxStep(
  world: ColliderWorld,
  position: THREE.Vector3,
  velocity: THREE.Vector3,
  shape: MoverShape,
  dt: number,
): MoveResult {
  const result: MoveResult = {
    position: position.clone(),
    velocity: velocity.clone(),
    grounded: false,
    ground: null,
    hitCeiling: false,
    hitWall: false,
    groundKind: null,
    steppedUp: 0,
  };

  const pos = result.position;
  const vel = result.velocity;

  // --- vertical ------------------------------------------------------------
  const dy = vel.y * dt;
  if (dy !== 0) {
    pos.y += dy;
    boxFor(pos, shape);
    scratchMin.y -= Math.max(0, -dy);
    scratchMax.y += Math.max(0, dy);
    world.query(scratchMin, scratchMax, scratchList);
    boxFor(pos, shape);

    for (const collider of scratchList) {
      if (!overlaps(collider)) continue;
      if (dy <= 0) {
        pos.y = collider.max.y;
        vel.y = 0;
        result.grounded = true;
        result.ground = collider;
        result.groundKind = collider.kind;
      } else {
        pos.y = collider.min.y - shape.height;
        vel.y = Math.min(vel.y, 0);
        result.hitCeiling = true;
      }
      boxFor(pos, shape);
    }
  }

  // --- horizontal, one axis at a time --------------------------------------
  for (const axis of ['x', 'z'] as const) {
    const delta = vel[axis] * dt;
    if (delta === 0) continue;
    const before = pos[axis];
    pos[axis] += delta;

    boxFor(pos, shape);
    scratchMin[axis] = Math.min(scratchMin[axis], before - shape.radius);
    scratchMax[axis] = Math.max(scratchMax[axis], before + shape.radius);
    world.query(scratchMin, scratchMax, scratchList);
    boxFor(pos, shape);

    for (const collider of scratchList) {
      if (!overlaps(collider)) continue;

      // Try to step over low ledges before treating this as a wall. Without
      // this, every 0.2-unit lip in the obby reads as an invisible barrier.
      const rise = collider.max.y - pos.y;
      if (rise > 0 && rise <= shape.stepHeight) {
        const stepped = pos.y + rise + 1e-4;
        const savedY = pos.y;
        pos.y = stepped;
        boxFor(pos, shape);
        let blocked = false;
        for (const other of scratchList) {
          if (other === collider) continue;
          if (overlaps(other)) {
            blocked = true;
            break;
          }
        }
        if (!blocked) {
          result.steppedUp += rise;
          result.grounded = true;
          result.ground = collider;
          result.groundKind = collider.kind;
          continue;
        }
        pos.y = savedY;
        boxFor(pos, shape);
      }

      pos[axis] = delta > 0
        ? collider.min[axis] - shape.radius - 1e-4
        : collider.max[axis] + shape.radius + 1e-4;
      vel[axis] = 0;
      result.hitWall = true;
      boxFor(pos, shape);
    }
  }

  // --- ground probe --------------------------------------------------------
  // A separate short downward probe keeps `grounded` true while walking across
  // seams between platforms, where the vertical pass alone would flicker.
  if (!result.grounded && vel.y <= 0.001) {
    boxFor(pos, shape);
    scratchMin.y -= 0.12;
    world.query(scratchMin, scratchMax, scratchList);
    for (const collider of scratchList) {
      if (!overlaps(collider)) continue;
      const gap = pos.y - collider.max.y;
      if (gap >= -0.02 && gap <= 0.12) {
        pos.y = collider.max.y;
        result.grounded = true;
        result.ground = collider;
        result.groundKind = collider.kind;
        vel.y = 0;
        break;
      }
    }
  }

  return result;
}

/** True when the box at `position` intersects anything solid. */
export function isBlocked(
  world: ColliderWorld,
  position: THREE.Vector3,
  shape: MoverShape,
): boolean {
  boxFor(position, shape);
  world.query(scratchMin, scratchMax, scratchList);
  boxFor(position, shape);
  for (const collider of scratchList) {
    if (overlaps(collider)) return true;
  }
  return false;
}

/** Drop `position` straight down onto the first surface beneath it. */
export function snapToGround(
  world: ColliderWorld,
  position: THREE.Vector3,
  maxDrop = 40,
): number | null {
  const hit = world.raycast(
    position.clone().add(new THREE.Vector3(0, 0.2, 0)),
    new THREE.Vector3(0, -1, 0),
    maxDrop,
  );
  return hit ? position.y + 0.2 - hit.distance : null;
}
