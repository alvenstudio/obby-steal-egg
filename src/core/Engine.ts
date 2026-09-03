import * as THREE from 'three';

/**
 * Renderer, clock and the fixed-step game loop.
 *
 * Movement runs at a fixed 120Hz step while rendering runs as fast as the
 * display allows. An obby lives or dies on jumps being reproducible, and a
 * variable-dt integrator makes the same input produce different arcs on
 * different machines.
 */

export interface EngineOptions {
  canvas: HTMLCanvasElement;
  /** Fixed simulation step, seconds. */
  step?: number;
  /** Never simulate more than this much wall time in one frame. */
  maxCatchUp?: number;
  shadows?: boolean;
}

export type UpdateFn = (dt: number) => void;
export type RenderFn = (alpha: number, dt: number) => void;

export class Engine {
  readonly renderer: THREE.WebGLRenderer;
  readonly scene: THREE.Scene;
  readonly clock = new THREE.Clock();

  /** Rolling average frame time, milliseconds. */
  frameMs = 0;
  fps = 0;

  private readonly step: number;
  private readonly maxCatchUp: number;
  private accumulator = 0;
  private running = false;
  private rafId = 0;
  private updateFn: UpdateFn = () => {};
  private renderFn: RenderFn = () => {};
  private resizeHandlers: Array<(w: number, h: number) => void> = [];
  private fpsSamples = 0;
  private fpsAccum = 0;

  constructor(options: EngineOptions) {
    this.step = options.step ?? 1 / 120;
    this.maxCatchUp = options.maxCatchUp ?? 0.25;

    this.renderer = new THREE.WebGLRenderer({
      canvas: options.canvas,
      antialias: true,
      powerPreference: 'high-performance',
      stencil: false,
    });
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    // The art is flat and stylised; filmic tone mapping would wash the palette
    // out exactly the way it did in the Blender previews.
    this.renderer.toneMapping = THREE.NoToneMapping;
    this.renderer.outputColorSpace = THREE.SRGBColorSpace;
    if (options.shadows !== false) {
      this.renderer.shadowMap.enabled = true;
      this.renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    }

    this.scene = new THREE.Scene();

    window.addEventListener('resize', this.handleResize);
    this.handleResize();
  }

  get size(): { width: number; height: number } {
    return {
      width: this.renderer.domElement.clientWidth || window.innerWidth,
      height: this.renderer.domElement.clientHeight || window.innerHeight,
    };
  }

  onResize(handler: (width: number, height: number) => void): void {
    this.resizeHandlers.push(handler);
    const { width, height } = this.size;
    handler(width, height);
  }

  setPixelRatio(scale: number): void {
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio * scale, 2));
    this.handleResize();
  }

  start(update: UpdateFn, render: RenderFn): void {
    this.updateFn = update;
    this.renderFn = render;
    if (this.running) return;
    this.running = true;
    this.clock.start();
    this.rafId = requestAnimationFrame(this.tick);
  }

  stop(): void {
    this.running = false;
    cancelAnimationFrame(this.rafId);
  }

  dispose(): void {
    this.stop();
    window.removeEventListener('resize', this.handleResize);
    this.renderer.dispose();
  }

  private tick = (): void => {
    if (!this.running) return;
    this.rafId = requestAnimationFrame(this.tick);

    let frame = this.clock.getDelta();
    if (frame > this.maxCatchUp) frame = this.maxCatchUp;

    this.fpsAccum += frame;
    this.fpsSamples++;
    if (this.fpsAccum >= 0.5) {
      this.fps = this.fpsSamples / this.fpsAccum;
      this.frameMs = (this.fpsAccum / this.fpsSamples) * 1000;
      this.fpsAccum = 0;
      this.fpsSamples = 0;
    }

    this.accumulator += frame;
    let steps = 0;
    while (this.accumulator >= this.step && steps < 8) {
      this.updateFn(this.step);
      this.accumulator -= this.step;
      steps++;
    }
    // If we blew the step budget (tab was backgrounded, a huge stall), drop the
    // backlog rather than spiralling: catching up would teleport the player.
    if (steps >= 8) this.accumulator = 0;

    this.renderFn(this.accumulator / this.step, frame);
  };

  private handleResize = (): void => {
    const width = window.innerWidth;
    const height = window.innerHeight;
    this.renderer.setSize(width, height, false);
    for (const handler of this.resizeHandlers) handler(width, height);
  };
}
