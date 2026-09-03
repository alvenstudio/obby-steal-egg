/**
 * Keyboard + mouse for a pointer-locked first-person game.
 *
 * Two details matter for platforming feel and are handled here rather than in
 * the player controller:
 *
 *  - `pressed()` is edge-triggered and consumed per frame, so a jump input
 *    registers exactly once even at 240fps.
 *  - mouse deltas accumulate between frames and are drained on read, so a
 *    frame hitch turns into one big look delta instead of a swallowed one.
 */

export type Action =
  | 'forward'
  | 'back'
  | 'left'
  | 'right'
  | 'jump'
  | 'sprint'
  | 'crouch'
  | 'interact'
  | 'drop'
  | 'inventory'
  | 'map'
  | 'shop'
  | 'pause';

const DEFAULT_BINDINGS: Record<string, Action> = {
  KeyW: 'forward',
  ArrowUp: 'forward',
  KeyS: 'back',
  ArrowDown: 'back',
  KeyA: 'left',
  ArrowLeft: 'left',
  KeyD: 'right',
  ArrowRight: 'right',
  Space: 'jump',
  ShiftLeft: 'sprint',
  ShiftRight: 'sprint',
  ControlLeft: 'crouch',
  KeyC: 'crouch',
  KeyE: 'interact',
  KeyQ: 'drop',
  KeyF: 'interact',
  Tab: 'inventory',
  KeyM: 'map',
  KeyB: 'shop',
  Escape: 'pause',
};

export class Input {
  readonly bindings: Record<string, Action> = { ...DEFAULT_BINDINGS };

  private down = new Set<Action>();
  private edge = new Set<Action>();
  private released = new Set<Action>();
  private mouseDx = 0;
  private mouseDy = 0;
  private wheel = 0;
  private locked = false;
  private enabled = true;
  private dragging = false;
  /** True once pointer lock has ever succeeded in this session. */
  private everLocked = false;
  /** Set when the browser refuses lock; enables the drag-to-look fallback. */
  private lockUnavailable = false;

  /** Raised when pointer lock is gained or lost, so the UI can pause. */
  onLockChange: ((locked: boolean) => void) | null = null;
  /** Raised when the browser refuses pointer lock entirely. */
  onLockFailed: (() => void) | null = null;

  constructor(private readonly element: HTMLElement) {
    window.addEventListener('keydown', this.handleKeyDown);
    window.addEventListener('keyup', this.handleKeyUp);
    window.addEventListener('blur', this.handleBlur);
    document.addEventListener('pointerlockchange', this.handlePointerLock);
    document.addEventListener('mousemove', this.handleMouseMove);
    element.addEventListener('mousedown', this.handleMouseDown);
    window.addEventListener('mouseup', this.handleMouseUp);
    element.addEventListener('contextmenu', this.handleContextMenu);
    element.addEventListener('wheel', this.handleWheel, { passive: true });
  }

  dispose(): void {
    window.removeEventListener('keydown', this.handleKeyDown);
    window.removeEventListener('keyup', this.handleKeyUp);
    window.removeEventListener('blur', this.handleBlur);
    document.removeEventListener('pointerlockchange', this.handlePointerLock);
    document.removeEventListener('mousemove', this.handleMouseMove);
    this.element.removeEventListener('mousedown', this.handleMouseDown);
    window.removeEventListener('mouseup', this.handleMouseUp);
    this.element.removeEventListener('contextmenu', this.handleContextMenu);
    this.element.removeEventListener('wheel', this.handleWheel);
  }

  get isLocked(): boolean {
    return this.locked;
  }

  requestLock(): void {
    // Modern browsers return a promise here and reject it when the document
    // cannot take pointer lock (an embedded frame, a permissions policy, a
    // request outside a user gesture). That is not fatal -- the game is
    // perfectly playable with a visible cursor -- so swallow it rather than
    // letting it surface as an unhandled rejection.
    try {
      const result = this.element.requestPointerLock() as unknown;
      if (result && typeof (result as Promise<void>).catch === 'function') {
        (result as Promise<void>).catch(() => this.failLock());
      }
    } catch {
      this.failLock();
    }
  }

  private failLock(): void {
    this.lockUnavailable = true;
    this.onLockFailed?.();
  }

  /** True once the pointer has actually been captured at least once. */
  get hasEverLocked(): boolean {
    return this.everLocked;
  }

  /**
   * Whether the browser has refused pointer lock, in which case the game falls
   * back to hold-to-look. Embedded frames and some permissions policies deny
   * lock outright, and refusing to run at all in that case would be a much
   * worse outcome than a slightly clumsier camera.
   */
  get isLockUnavailable(): boolean {
    return this.lockUnavailable;
  }

  releaseLock(): void {
    if (document.pointerLockElement) document.exitPointerLock();
  }

  /**
   * Menus call this so movement keys stop reaching the player while a panel
   * is open, without tearing down the listeners.
   */
  setEnabled(value: boolean): void {
    this.enabled = value;
    if (!value) {
      this.down.clear();
      this.edge.clear();
      this.mouseDx = 0;
      this.mouseDy = 0;
    }
  }

  held(action: Action): boolean {
    return this.enabled && this.down.has(action);
  }

  /** True once per physical press. */
  pressed(action: Action): boolean {
    return this.enabled && this.edge.has(action);
  }

  wasReleased(action: Action): boolean {
    return this.enabled && this.released.has(action);
  }

  /** Movement as a normalized 2D vector: x = strafe, y = forward. */
  moveAxis(): { x: number; y: number } {
    let x = 0;
    let y = 0;
    if (this.held('forward')) y += 1;
    if (this.held('back')) y -= 1;
    if (this.held('right')) x += 1;
    if (this.held('left')) x -= 1;
    const len = Math.hypot(x, y);
    return len > 1 ? { x: x / len, y: y / len } : { x, y };
  }

  /** Accumulated mouse movement since the last call, in pixels. */
  consumeLook(): { dx: number; dy: number } {
    const out = { dx: this.mouseDx, dy: this.mouseDy };
    this.mouseDx = 0;
    this.mouseDy = 0;
    return out;
  }

  consumeWheel(): number {
    const out = this.wheel;
    this.wheel = 0;
    return out;
  }

  /** Call at the very end of each frame to clear edge-triggered state. */
  endFrame(): void {
    this.edge.clear();
    this.released.clear();
  }

  private handleKeyDown = (event: KeyboardEvent): void => {
    const action = this.bindings[event.code];
    if (!action) return;
    // Tab would move focus out of the canvas; Space would scroll the page.
    if (event.code === 'Tab' || event.code === 'Space') event.preventDefault();
    if (event.repeat) return;
    this.down.add(action);
    this.edge.add(action);
  };

  private handleKeyUp = (event: KeyboardEvent): void => {
    const action = this.bindings[event.code];
    if (!action) return;
    this.down.delete(action);
    this.released.add(action);
  };

  private handleBlur = (): void => {
    this.down.clear();
    this.edge.clear();
  };

  private handlePointerLock = (): void => {
    this.locked = document.pointerLockElement === this.element;
    if (this.locked) {
      this.everLocked = true;
      this.lockUnavailable = false;
    } else {
      this.down.clear();
    }
    this.onLockChange?.(this.locked);
  };

  private handleMouseMove = (event: MouseEvent): void => {
    // Locked: raw deltas. Unlocked: only while dragging, so the cursor can
    // still be used on the HUD without swinging the camera.
    if (!this.locked && !this.dragging) return;
    this.mouseDx += event.movementX;
    this.mouseDy += event.movementY;
  };

  private handleMouseDown = (event: MouseEvent): void => {
    if (event.button === 2) {
      this.dragging = true;
      return;
    }
    if (event.button !== 0) return;
    if (!this.locked) {
      this.dragging = true;
      // Without lock, a left-drag looks around; a click that does not turn
      // into a drag still counts as an interact on mouseup.
      return;
    }
    this.down.add('interact');
    this.edge.add('interact');
    // A click is instantaneous; release on the next frame so `held` does not
    // latch on until the mouseup arrives.
    window.setTimeout(() => this.down.delete('interact'), 0);
  };

  private handleMouseUp = (event: MouseEvent): void => {
    if (event.button === 2) {
      this.dragging = false;
      return;
    }
    if (event.button !== 0) return;
    if (!this.locked && this.dragging) {
      this.dragging = false;
      this.down.add('interact');
      this.edge.add('interact');
      window.setTimeout(() => this.down.delete('interact'), 0);
    }
  };

  private handleContextMenu = (event: Event): void => {
    // Right-drag is a look control here, so the browser menu must not open.
    event.preventDefault();
  };

  private handleWheel = (event: WheelEvent): void => {
    this.wheel += Math.sign(event.deltaY);
  };
}
