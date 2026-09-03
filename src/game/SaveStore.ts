import { GameState, SAVE_VERSION, SaveData } from './GameState';

/**
 * localStorage persistence.
 *
 * Saving is deliberately forgiving: a corrupt, truncated or older save is
 * discarded rather than thrown, because for a browser game "your progress
 * crashed the page" is a far worse outcome than "your progress is gone". The
 * save is also written on every meaningful event rather than only on a timer,
 * since the common way to leave a browser game is closing the tab mid-run.
 */

const KEY = 'obby-steal-egg:save:v3';
const LEGACY_KEYS = ['obby-steal-egg:save:v1', 'obby-steal-egg:save:v2'];

export class SaveStore {
  private lastSavedAt = 0;
  private available: boolean;

  constructor() {
    this.available = probeStorage();
  }

  save(state: GameState): boolean {
    if (!this.available) return false;
    try {
      const data = state.toSave();
      this.lastSavedAt = data.savedAt;
      localStorage.setItem(KEY, JSON.stringify(data));
      return true;
    } catch {
      // Quota exceeded or storage disabled mid-session; stop trying so we do
      // not throw on every autosave tick for the rest of the run.
      this.available = false;
      return false;
    }
  }

  load(state: GameState): boolean {
    if (!this.available) return false;
    const raw = localStorage.getItem(KEY);
    if (!raw) {
      this.clearLegacy();
      return false;
    }
    try {
      const data = JSON.parse(raw) as SaveData;
      if (!data || typeof data !== 'object') return false;
      if (data.version !== SAVE_VERSION) {
        // No migration path yet; a fresh start beats a subtly broken economy.
        localStorage.removeItem(KEY);
        return false;
      }
      state.load(data);
      this.lastSavedAt = Number(data.savedAt) || Date.now();
      return true;
    } catch {
      localStorage.removeItem(KEY);
      return false;
    }
  }

  /** How long the tab was closed, for offline earnings. */
  secondsSinceSave(): number {
    if (!this.lastSavedAt) return 0;
    return Math.max(0, (Date.now() - this.lastSavedAt) / 1000);
  }

  clear(): void {
    if (!this.available) return;
    localStorage.removeItem(KEY);
    this.clearLegacy();
  }

  private clearLegacy(): void {
    for (const key of LEGACY_KEYS) {
      try {
        localStorage.removeItem(key);
      } catch {
        /* ignore */
      }
    }
  }

  /** Export the current save so a player can move it between browsers. */
  exportString(state: GameState): string {
    return btoa(unescape(encodeURIComponent(JSON.stringify(state.toSave()))));
  }

  importString(state: GameState, encoded: string): boolean {
    try {
      const json = decodeURIComponent(escape(atob(encoded.trim())));
      const data = JSON.parse(json) as SaveData;
      if (data.version !== SAVE_VERSION) return false;
      state.load(data);
      this.save(state);
      return true;
    } catch {
      return false;
    }
  }
}

function probeStorage(): boolean {
  try {
    const probe = '__probe__';
    localStorage.setItem(probe, '1');
    localStorage.removeItem(probe);
    return true;
  } catch {
    // Private browsing, blocked cookies, or a sandboxed iframe. The game still
    // runs; it just will not remember anything.
    return false;
  }
}
