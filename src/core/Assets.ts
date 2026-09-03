import * as THREE from 'three';
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js';

/**
 * Model loading and instancing.
 *
 * Two things this does beyond wrapping GLTFLoader:
 *
 *  1. Every .glb is loaded once and cloned per use, sharing geometry and
 *     materials. A base with 40 pets on pedestals would otherwise upload the
 *     same buffers 40 times.
 *  2. A missing model resolves to a visibly wrong magenta placeholder instead
 *     of throwing. During a 100-model build it matters enormously that one
 *     unbuilt pet does not take the whole game down with it.
 */

export interface ModelHandle {
  /** The loaded prototype. Do not add this to the scene; clone it. */
  prototype: THREE.Object3D;
  /** Bounding box in model space, computed once. */
  bounds: THREE.Box3;
  /** Named parts the runtime animator can drive. */
  parts: string[];
  missing: boolean;
}

const PLACEHOLDER_COLOR = 0xff00d4;

export class Assets {
  private readonly loader = new GLTFLoader();
  private readonly cache = new Map<string, Promise<ModelHandle>>();
  private readonly ready = new Map<string, ModelHandle>();
  private placeholder: THREE.Object3D | null = null;

  /** Set of paths that failed, so the UI can report an incomplete build. */
  readonly failures = new Set<string>();

  constructor(private readonly baseUrl = '') {}

  /** Kick off loading without waiting; useful for warming a biome. */
  preload(paths: string[]): Promise<ModelHandle[]> {
    return Promise.all(paths.map((path) => this.load(path)));
  }

  load(path: string): Promise<ModelHandle> {
    const existing = this.cache.get(path);
    if (existing) return existing;

    const url = this.baseUrl + path;
    const promise = new Promise<ModelHandle>((resolve) => {
      this.loader.load(
        url,
        (gltf) => {
          const root = gltf.scene;
          root.traverse((node) => {
            if ((node as THREE.Mesh).isMesh) {
              const mesh = node as THREE.Mesh;
              mesh.castShadow = true;
              mesh.receiveShadow = true;
              // Blender exports one material per part; make sure they render
              // as the flat, unlit-ish surfaces the art direction expects.
              const materials = Array.isArray(mesh.material) ? mesh.material : [mesh.material];
              for (const material of materials) {
                if ((material as THREE.MeshStandardMaterial).isMeshStandardMaterial) {
                  const standard = material as THREE.MeshStandardMaterial;
                  standard.envMapIntensity = 0.35;
                  standard.flatShading = false;
                }
              }
            }
          });
          const handle: ModelHandle = {
            prototype: root,
            bounds: new THREE.Box3().setFromObject(root),
            parts: collectPartNames(root),
            missing: false,
          };
          this.ready.set(path, handle);
          resolve(handle);
        },
        undefined,
        () => {
          this.failures.add(path);
          const handle: ModelHandle = {
            prototype: this.getPlaceholder(),
            bounds: new THREE.Box3(
              new THREE.Vector3(-0.4, 0, -0.4),
              new THREE.Vector3(0.4, 0.8, 0.4),
            ),
            parts: [],
            missing: true,
          };
          this.ready.set(path, handle);
          resolve(handle);
        },
      );
    });

    this.cache.set(path, promise);
    return promise;
  }

  /** Synchronous access for anything already loaded. */
  get(path: string): ModelHandle | null {
    return this.ready.get(path) ?? null;
  }

  /**
   * A fresh instance sharing geometry/material with the prototype.
   * `THREE.Object3D.clone()` already shares geometry and materials by
   * reference, which is exactly what we want here.
   */
  instantiate(path: string): THREE.Object3D {
    const handle = this.ready.get(path);
    if (!handle) return this.getPlaceholder().clone();
    return handle.prototype.clone(true);
  }

  private getPlaceholder(): THREE.Object3D {
    if (this.placeholder) return this.placeholder;
    const group = new THREE.Group();
    group.name = 'root';
    const body = new THREE.Mesh(
      new THREE.BoxGeometry(0.6, 0.6, 0.6),
      new THREE.MeshStandardMaterial({ color: PLACEHOLDER_COLOR, roughness: 0.5 }),
    );
    body.name = 'body';
    body.position.y = 0.3;
    body.castShadow = true;
    group.add(body);
    this.placeholder = group;
    return group;
  }
}

function collectPartNames(root: THREE.Object3D): string[] {
  const names: string[] = [];
  root.traverse((node) => {
    if (node.name && node !== root) names.push(node.name);
  });
  return names;
}

/** Recolour every material on a clone without touching the shared prototype. */
export function tintInstance(
  instance: THREE.Object3D,
  transform: (material: THREE.MeshStandardMaterial) => void,
): void {
  const seen = new Set<THREE.Material>();
  instance.traverse((node) => {
    const mesh = node as THREE.Mesh;
    if (!mesh.isMesh) return;
    const materials = Array.isArray(mesh.material) ? mesh.material : [mesh.material];
    const replaced = materials.map((material) => {
      if (seen.has(material)) return material;
      const clone = (material as THREE.MeshStandardMaterial).clone();
      transform(clone);
      seen.add(clone);
      return clone;
    });
    mesh.material = Array.isArray(mesh.material) ? replaced : replaced[0];
  });
}

/** Dispose everything a discarded instance uniquely owns. */
export function disposeInstance(instance: THREE.Object3D, disposeGeometry = false): void {
  instance.traverse((node) => {
    const mesh = node as THREE.Mesh;
    if (!mesh.isMesh) return;
    if (disposeGeometry) mesh.geometry.dispose();
  });
}
