import './ui/styles.css';

import { Assets } from '@/core/Assets';
import { AudioSystem } from '@/core/Audio';
import { Engine } from '@/core/Engine';
import { Input } from '@/core/Input';
import { formatMoney } from '@/data/balance';
import type { BiomeDef } from '@/data/biomes';
import { PET_BY_ID } from '@/data/pets';
import { RARITIES } from '@/data/rarity';
import { Session } from '@/game/Session';
import type { GameEvent, OwnedPet } from '@/game/GameState';
import { Hud } from '@/ui/Hud';
import { PanelId, Panels } from '@/ui/Panels';
import { SaveStore } from '@/game/SaveStore';

/**
 * Bootstrap: wire the engine, the session and the UI together, then hand
 * control to the loop.
 *
 * Loading is split in two on purpose. The core manifest -- eggs and the eleven
 * guardian models -- is what the player must have before they can be dropped
 * into the world; the remaining ~100 pets stream in behind the start button so
 * the game is playable in a couple of seconds rather than after downloading
 * the entire bestiary.
 */

const canvas = document.getElementById('view') as HTMLCanvasElement;
const overlay = document.getElementById('overlay') as HTMLElement;
const startButton = document.getElementById('start') as HTMLButtonElement;
const loadingText = document.getElementById('loading') as HTMLElement;
const loadingBar = document.getElementById('loading-bar') as HTMLElement;

const engine = new Engine({ canvas });
const input = new Input(canvas);
const assets = new Assets(import.meta.env.BASE_URL ?? './');
const audio = new AudioSystem();
const store = new SaveStore();

let hud: Hud;
let panels: Panels;
let session: Session;
let started = false;

async function boot(): Promise<void> {
  loadingText.textContent = 'Loading models…';

  const core = Session.coreManifest();
  await loadWithProgress(core, 0, 0.55);

  session = new Session(engine, input, assets, audio, {
    onHud: (model) => hud.update(model),
    onOpenPanel: (panel) => openPanel(panel),
    onEvent: (kind, payload) => handleGameEvent(kind, payload),
  });

  hud = new Hud(document.body);
  panels = new Panels(document.body, session.state, {
    onClose: () => closePanel(),
    onChanged: () => {
      session.applyUpgrades();
      session.garden.sync();
      store.save(session.state);
    },
  });

  session.state.on(onStateEvent);

  const restored = store.load(session.state);
  if (restored) {
    const away = store.secondsSinceSave();
    const earned = session.state.applyOffline(away);
    if (earned > 0) {
      pendingWelcome = {
        title: 'Welcome back',
        sub: `${formatMoney(earned)} earned while you were away`,
      };
    }
  }
  session.applyUpgrades();

  loadingText.textContent = 'Building the world…';
  session.onAssetsReady();

  startButton.disabled = false;
  startButton.textContent = restored ? 'Continue' : 'Start stealing';
  loadingText.textContent = `${core.length} core models ready · the rest load as you play`;
  loadingBar.style.width = '100%';

  // The long tail streams in behind the start button.
  void loadWithProgress(Session.assetManifest(), 0.55, 1).then(() => {
    session.onAssetsReady();
    session.garden.sync();
    if (assets.failures.size > 0) {
      hud.toast(
        `${assets.failures.size} models missing`,
        'Run "npm run models" to build them',
        'bad',
      );
    }
  });

  if (import.meta.env.DEV) {
    // A handle for poking at a running game from the console. Dev-only, so it
    // never ships, but invaluable for checking a biome you would otherwise
    // have to train for an hour to reach.
    (window as unknown as Record<string, unknown>).game = {
      session, engine, assets, store, hud, panels,
      teleport: (x: number, y: number, z: number) => session.teleportTo(x, y, z),
      goto: (biome: string) => session.gotoBiome(biome as never),
      look(yaw: number, pitch = 0) {
        session.camera.yaw = yaw;
        session.camera.pitch = pitch;
      },
      give(money: number) { session.state.addMoney(money); },
      setSpeed(value: number) {
        session.state.speed = value;
        session.applyUpgrades();
      },
    };
  }

  engine.start(
    (dt) => {
      if (!started) return;
      session.update(dt);
    },
    () => {
      if (!started) return;
      session.render();
    },
  );
}

let pendingWelcome: { title: string; sub: string } | null = null;

async function loadWithProgress(paths: string[], from: number, to: number): Promise<void> {
  let done = 0;
  await Promise.all(
    paths.map((path) =>
      assets.load(path).then(() => {
        done++;
        const ratio = from + (to - from) * (done / paths.length);
        loadingBar.style.width = `${(ratio * 100).toFixed(1)}%`;
      }),
    ),
  );
}

// ---------------------------------------------------------------- lifecycle

function start(): void {
  if (started) return;
  started = true;
  overlay.classList.add('hidden');
  audio.unlock();
  audio.startAmbience(96, 1);
  input.requestLock();

  if (pendingWelcome) {
    hud.toast(pendingWelcome.title, pendingWelcome.sub, 'good', true);
    pendingWelcome = null;
  } else {
    hud.toast(
      'Take an egg from the Whisperpine nest',
      'Follow the road north. Hold E at the nest.',
      'info',
      true,
    );
  }
}

startButton.addEventListener('click', () => start());

input.onLockChange = (locked) => {
  if (!started) return;
  // Losing the pointer is the pause: there is no separate pause menu, because
  // the only reason to stop is that you clicked away.
  session.paused = !locked && !panels.isOpen;
  if (!locked && !panels.isOpen) {
    overlay.classList.remove('hidden');
    startButton.textContent = 'Resume';
    started = false;
  }
};

function openPanel(panel: PanelId): void {
  panels.open(panel);
  session.paused = true;
  input.setEnabled(false);
  input.releaseLock();
}

function closePanel(): void {
  session.paused = false;
  input.setEnabled(true);
  input.requestLock();
  store.save(session.state);
}

window.addEventListener('keydown', (event) => {
  if (event.code === 'Escape' && panels.isOpen) {
    event.preventDefault();
    panels.close();
    return;
  }
  if (!started) return;
  if (event.code === 'F3') {
    event.preventDefault();
    hud.showDebug = !hud.showDebug;
  }
  if (event.code === 'KeyR' && event.shiftKey) {
    event.preventDefault();
    session.respawn();
  }
});

// ------------------------------------------------------------------- events

function onStateEvent(event: GameEvent): void {
  switch (event.type) {
    case 'notice':
      hud.toast(event.text, '', event.tone ?? 'info');
      break;
    case 'biomeUnlocked': {
      const biome = event.biome as BiomeDef;
      hud.toast(`${biome.name} is open`, biome.tagline, 'good', true);
      break;
    }
    case 'rebirth':
      hud.toast(`Rebirth ${event.count}`, 'Everything is faster now.', 'good', true);
      break;
    default:
      break;
  }
}

function handleGameEvent(kind: string, payload?: unknown): void {
  switch (kind) {
    case 'stole': {
      const biome = (payload as { biome: BiomeDef }).biome;
      hud.toast('RUN', `${biome.guardian} is awake`, 'bad', true);
      break;
    }
    case 'caught':
      if ((payload as number) > 0) hud.toast('Egg dropped', 'Grab it before it does', 'bad');
      break;
    case 'delivered':
      hud.toast('Delivered', `${payload} egg${payload === 1 ? '' : 's'} in the nest`, 'good');
      store.save(session.state);
      break;
    case 'hatched': {
      const { pet, isNew } = payload as { pet: OwnedPet; isNew: boolean };
      const def = PET_BY_ID[pet.petId];
      const rarity = def ? RARITIES[def.rarity] : RARITIES.common;
      hud.toast(
        session.state.displayName(pet),
        `${rarity.name}${isNew ? ' · NEW' : ''} · ${formatMoney(session.state.petIncome(pet))}/s`,
        isNew ? 'good' : 'info',
        rarity.rank >= 4,
      );
      store.save(session.state);
      break;
    }
    case 'guardianWake': {
      const biome = payload as BiomeDef;
      audio.startAmbience(biome.ambienceHz * 0.6, 1.4);
      break;
    }
    case 'night':
      hud.toast('Night', 'Nests refilled · eggs hatch 30× faster', 'good', true);
      break;
    default:
      break;
  }
}

// Periodic autosave, plus one on the way out.
window.setInterval(() => {
  if (started) store.save(session.state);
}, 20_000);
window.addEventListener('beforeunload', () => {
  if (session) store.save(session.state);
});

void boot();
