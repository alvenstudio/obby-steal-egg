import * as THREE from 'three';

import { Assets } from '@/core/Assets';
import { AudioSystem } from '@/core/Audio';
import { Engine } from '@/core/Engine';
import { Input } from '@/core/Input';
import { BIOMES, BiomeDef, BiomeId } from '@/data/biomes';
import { PET_BY_ID } from '@/data/pets';
import { sprintSpeed, speedMultiplier } from '@/data/progression';
import { SIZES } from '@/data/rarity';
import { FirstPersonCamera } from '@/player/FirstPersonCamera';
import { DEFAULT_TUNING, PlayerController } from '@/player/PlayerController';
import { ViewModel } from '@/player/ViewModel';
import { World } from '@/world/World';
import { SAFE_RADIUS } from '@/world/SafeZone';

import { CarriedEgg, GameState } from './GameState';
import { GuardianManager } from './GuardianManager';
import { PetGarden } from './PetGarden';

/**
 * The game loop.
 *
 * Everything else in the project is a system; this is the thing that decides
 * what happens when. Its main job is the theft arc, which is deliberately five
 * beats long and always the same shape:
 *
 *   approach -> climb -> take (the guardian wakes) -> run -> cross the line
 *
 * Nothing here is allowed to interrupt that arc with a menu, a loading pause,
 * or a modal. If a mechanic cannot be expressed inside those five beats it
 * does not belong in the game.
 */

/** The reference game's day is ~4:30 with a ~13s night. */
export const DAY_SECONDS = 270;
export const NIGHT_SECONDS = 13;
/** Eggs in the garden hatch far faster during the night. */
export const NIGHT_HATCH_MULTIPLIER = 30;

export interface Prompt {
  text: string;
  /** 0..1 for a hold-to-act progress ring; null for a tap prompt. */
  progress: number | null;
  kind: 'steal' | 'kiosk' | 'pickup' | 'info';
  /** Present when the prompt cannot be acted on yet. */
  blocked?: string;
}

export interface DroppedEgg {
  egg: CarriedEgg;
  position: THREE.Vector3;
  model: THREE.Object3D;
  /** Seconds before the guardian takes it back. */
  reclaimIn: number;
}

export interface HudModel {
  money: number;
  incomePerSecond: number;
  speed: number;
  trainingRate: number;
  training: boolean;
  sprintSpeed: number;
  carried: CarriedEgg[];
  carryLimit: number;
  prompt: Prompt | null;
  threat: number;
  /** Bearing to the nearest chaser relative to the camera, radians, or null. */
  threatBearing: number | null;
  stamina: number;
  staminaMax: number;
  zone: BiomeDef | null;
  inSafeZone: boolean;
  nightFactor: number;
  timeOfDayLabel: string;
  pedestalsUsed: number;
  pedestalsTotal: number;
  nextBiome: BiomeDef | null;
  collection: { found: number; total: number };
  fps: number;
}

export interface SessionCallbacks {
  onHud: (model: HudModel) => void;
  onOpenPanel: (panel: 'shop' | 'treadmill' | 'trail' | 'rebirth' | 'index' | 'storage') => void;
  onEvent: (kind: string, payload?: unknown) => void;
}

export class Session {
  readonly state = new GameState();
  readonly world: World;
  readonly player: PlayerController;
  readonly camera: FirstPersonCamera;
  readonly viewModel: ViewModel;
  readonly garden: PetGarden;
  readonly guardians: GuardianManager;

  /** Time of day in seconds, wrapping over DAY + NIGHT. */
  clock = 0;
  paused = false;

  private dropped: DroppedEgg[] = [];
  private prompt: Prompt | null = null;
  private stealHold = 0;
  private stealTarget: BiomeId | null = null;
  private time = 0;
  private lastYaw = 0;
  private lookDelta = 0;
  private pendingDeliverFlash = 0;
  private hudAccumulator = 0;
  private lastPosition = new THREE.Vector3();

  constructor(
    private readonly engine: Engine,
    private readonly input: Input,
    private readonly assets: Assets,
    private readonly audio: AudioSystem,
    private readonly callbacks: SessionCallbacks,
  ) {
    this.world = new World(engine.scene, assets);
    const build = this.world.build();

    this.player = new PlayerController(this.world.colliders);
    this.player.teleport(build.spawn.clone().setY(build.spawn.y + 1));
    this.camera = new FirstPersonCamera(engine.size.width / engine.size.height);
    this.viewModel = new ViewModel(assets, engine.size.width / engine.size.height);

    this.garden = new PetGarden(engine.scene, assets, this.state);
    this.garden.setPedestals(build.pedestals);

    this.guardians = new GuardianManager(engine.scene, this.world.colliders, assets);
    this.guardians.spawn(build.nests);

    this.wireFeedback();

    engine.onResize((width, height) => {
      this.camera.setAspect(width / height);
      this.viewModel.setAspect(width / height);
    });
  }

  /** Called after assets finish loading, so models exist. */
  onAssetsReady(): void {
    this.world.attachEggs();
    this.guardians.dispose();
    this.guardians.spawn(this.world.nests);
    this.garden.sync();
  }

  private wireFeedback(): void {
    this.player.onLand = (impact) => {
      this.camera.onLand(impact);
      this.audio.play(impact > 18 ? 'landHard' : 'land', { volume: Math.min(1, impact / 20) });
      // A heavy landing is loud enough for a nearby guardian to investigate.
      if (impact > 10) {
        this.guardians.addNoise(this.player.state.position, 14 + impact);
      }
    };
    this.player.onJump = () => {
      this.camera.onJump();
      this.audio.play('jump', { volume: 0.4 });
    };
    this.player.onStep = (speed) => {
      this.audio.play('step', { volume: 0.22 + speed * 0.012, pitch: 0.9 + Math.random() * 0.2 });
      this.guardians.addNoise(
        this.player.state.position,
        this.player.state.crouching ? 3 : this.player.state.sprinting ? 13 : 8,
      );
    };

    this.guardians.events.onWake = (visual) => {
      this.audio.play('guardianRoar', { position: visual.guardian.position, radius: 160 });
      this.audio.play('alarm', { volume: 0.5 });
      this.camera.addShake(0.5);
      this.callbacks.onEvent('guardianWake', visual.biome);
    };
    this.guardians.events.onFootstep = (visual) => {
      this.audio.play('guardianStep', {
        position: visual.guardian.position,
        radius: 70,
        pitch: 0.7 + visual.biome.order * 0.02,
      });
    };
    this.guardians.events.onCatch = () => this.handleCaught();

    this.state.on((event) => {
      switch (event.type) {
        case 'hatched':
          this.audio.play('hatch');
          this.garden.sync();
          this.garden.celebrate(event.pet.slot, 1.4);
          this.callbacks.onEvent('hatched', event);
          break;
        case 'delivered':
          this.audio.play('purchase');
          this.garden.sync();
          break;
        case 'biomeUnlocked':
          this.audio.play('unlock');
          this.callbacks.onEvent('biomeUnlocked', event.biome);
          break;
        case 'upgrade':
          this.audio.play('purchase');
          this.garden.sync();
          this.applyUpgrades();
          break;
        case 'rebirth':
          this.audio.play('rebirth');
          this.garden.sync();
          this.applyUpgrades();
          break;
        default:
          break;
      }
    });

    this.applyUpgrades();
  }

  /** Push GameState-derived numbers into the movement systems. */
  applyUpgrades(): void {
    this.player.tuning.stamina = this.state.staminaMax;
    this.player.tuning.carryPenalty = this.state.carryDrag;
    this.player.jumpMultiplier = this.state.jumpMultiplier;
    this.player.speedMultiplier = speedMultiplier(this.state.speed);
  }

  get nightFactor(): number {
    const cycle = DAY_SECONDS + NIGHT_SECONDS;
    const t = this.clock % cycle;
    if (t < DAY_SECONDS - 12) return 0;
    if (t < DAY_SECONDS) return (t - (DAY_SECONDS - 12)) / 12;
    if (t < DAY_SECONDS + NIGHT_SECONDS - 4) return 1;
    return 1 - (t - (DAY_SECONDS + NIGHT_SECONDS - 4)) / 4;
  }

  get isNight(): boolean {
    const cycle = DAY_SECONDS + NIGHT_SECONDS;
    const t = this.clock % cycle;
    return t >= DAY_SECONDS;
  }

  // -- the frame ------------------------------------------------------------

  update(dt: number): void {
    if (this.paused) return;
    this.time += dt;

    const wasNight = this.isNight;
    this.clock += dt;
    const nowNight = this.isNight;
    if (nowNight && !wasNight) this.onNightfall();
    if (!nowNight && wasNight) this.onDaybreak();

    this.camera.handleLook(this.input);
    this.lookDelta = this.camera.yaw - this.lastYaw;
    this.lastYaw = this.camera.yaw;

    this.player.yaw = this.camera.yaw;
    this.player.speedMultiplier = speedMultiplier(this.state.speed);
    this.player.state.carrying = this.state.carried.length > 0;
    this.player.update(this.input, dt);

    const position = this.player.state.position;
    this.state.stats.distanceRun += this.lastPosition.distanceTo(position);
    this.lastPosition.copy(position);

    const inSafe = this.world.inSafeZone(position);
    this.updateTreadmill(inSafe);

    this.guardians.update(dt, position, {
      crouching: this.player.state.crouching,
      carryingFrom: this.state.carried.map((egg) => egg.biome),
      playerSafe: inSafe,
      difficultyFor: () => 1,
      baseSprintSpeed: DEFAULT_TUNING.sprintSpeed,
    });

    this.world.update(dt, position, this.nightFactor);
    this.updateDroppedEggs(dt);
    this.updateInteractions(dt, inSafe);

    this.state.update(dt);
    // Night hatches eggs far faster, which is what makes the day/night flip a
    // beat rather than a lighting change: the garden is suddenly the place to
    // be. The extra time is applied on top of the normal tick rather than by
    // scaling dt, so income and training keep running at real time.
    if (this.isNight) {
      const bonus = dt * (NIGHT_HATCH_MULTIPLIER - 1);
      for (const egg of this.state.hatching) egg.remaining -= bonus;
    }

    if (inSafe && this.state.carried.length > 0) this.deliver();

    this.garden.setLookTarget(inSafe ? position : null);
    this.garden.update(dt, this.time);

    const strafe = this.input.moveAxis().x;
    this.camera.update(this.player, dt, strafe);
    this.viewModel.setEgg(this.state.carried[0] ?? null);
    this.viewModel.update(dt, this.player.state, this.camera.pitch, this.lookDelta, this.time);

    this.audio.setListener(this.camera.camera.position, this.camera.forward());

    if (this.pendingDeliverFlash > 0) this.pendingDeliverFlash -= dt;

    this.hudAccumulator += dt;
    if (this.hudAccumulator > 1 / 20) {
      this.hudAccumulator = 0;
      this.callbacks.onHud(this.buildHud(inSafe));
    }

    this.input.endFrame();
  }

  render(): void {
    this.engine.renderer.render(this.engine.scene, this.camera.camera);
    this.viewModel.camera.quaternion.identity();
    this.viewModel.render(this.engine.renderer);
  }

  // -- day / night ----------------------------------------------------------

  private onNightfall(): void {
    // Night closes the map: guardians go home, nests refill, and anyone caught
    // out in the biomes is walked back. It is the game's only forced pause and
    // it doubles as the reset that makes each day feel like a fresh run.
    this.guardians.sleepAll();
    for (const nest of this.world.nests.values()) {
      nest.hasEgg = true;
      nest.respawnIn = 0;
      if (nest.mesh) nest.mesh.visible = true;
    }
    this.audio.play('checkpoint');
    this.state.notice('Night falls. Every nest has refilled.', 'good');
    this.callbacks.onEvent('night');

    if (!this.world.inSafeZone(this.player.state.position)) {
      this.player.teleport(this.world.spawn.clone().setY(this.world.spawn.y + 1));
      this.camera.addShake(0.3);
      this.state.notice('The dark walked you home.', 'info');
    }
  }

  private onDaybreak(): void {
    this.audio.play('unlock', { volume: 0.4 });
    this.callbacks.onEvent('day');
  }

  // -- interactions ---------------------------------------------------------

  private updateTreadmill(inSafe: boolean): void {
    const position = this.player.state.position;
    const onBelt = inSafe && this.world.treadmillArea.containsPoint(
      new THREE.Vector3(position.x, position.y + 0.4, position.z),
    );
    // Training requires actually running, not just standing on the belt. It is
    // the one place the game asks for input during an idle phase, and it keeps
    // the treadmill from being a pure AFK button.
    const running = this.player.state.speed > 1.2;
    this.state.training = onBelt && running;
  }

  private updateInteractions(dt: number, inSafe: boolean): void {
    this.prompt = null;
    const position = this.player.state.position;

    if (inSafe) {
      this.updateKioskPrompt(position);
      if (!this.prompt) this.updateTreadmillPrompt();
      this.stealHold = 0;
      this.stealTarget = null;
      return;
    }

    if (this.updatePickupPrompt(position)) return;
    this.updateStealPrompt(dt, position);
  }

  private updateKioskPrompt(position: THREE.Vector3): void {
    for (const kiosk of this.world.kiosks) {
      if (position.distanceTo(kiosk.usePosition) > 3.4) continue;
      this.prompt = { text: `Open ${kiosk.label}`, progress: null, kind: 'kiosk' };
      if (this.input.pressed('interact')) {
        this.audio.play('coin', { volume: 0.4 });
        this.callbacks.onOpenPanel(kiosk.id);
      }
      return;
    }
  }

  private updateTreadmillPrompt(): void {
    if (!this.state.training) return;
    this.prompt = {
      text: 'Training Speed',
      progress: null,
      kind: 'info',
    };
  }

  private updatePickupPrompt(position: THREE.Vector3): boolean {
    for (const drop of this.dropped) {
      if (position.distanceTo(drop.position) > 3) continue;
      this.prompt = { text: 'Pick the egg back up', progress: null, kind: 'pickup' };
      if (this.input.pressed('interact') && this.state.canCarryMore()) {
        this.state.carried.push(drop.egg);
        drop.model.removeFromParent();
        this.dropped.splice(this.dropped.indexOf(drop), 1);
        this.audio.play('grab');
        this.guardians.wake(drop.egg.biome);
      }
      return true;
    }
    return false;
  }

  private updateStealPrompt(dt: number, position: THREE.Vector3): void {
    let target: { biome: BiomeDef; distance: number } | null = null;
    for (const nest of this.world.nests.values()) {
      if (!nest.hasEgg) continue;
      const distance = position.distanceTo(nest.info.stealPosition);
      if (distance > 4.2) continue;
      if (!target || distance < target.distance) {
        target = { biome: nest.biome, distance };
      }
    }

    if (!target) {
      this.stealHold = 0;
      this.stealTarget = null;
      return;
    }

    const biome = target.biome;
    if (!this.state.isBiomeUnlocked(biome.id)) {
      this.prompt = {
        text: biome.name,
        progress: null,
        kind: 'steal',
        blocked: `Needs ${formatSpeed(biome.speedGate)} Speed`,
      };
      return;
    }
    if (!this.state.canCarryMore()) {
      this.prompt = {
        text: 'Hands full', progress: null, kind: 'steal',
        blocked: 'Take what you have home first',
      };
      return;
    }

    if (this.input.held('interact')) {
      if (this.stealTarget !== biome.id) {
        this.stealTarget = biome.id;
        this.stealHold = 0;
      }
      this.stealHold += dt;
      if (this.stealHold >= biome.stealTime) {
        this.performSteal(biome);
        return;
      }
    } else {
      this.stealHold = Math.max(0, this.stealHold - dt * 2.5);
    }

    this.prompt = {
      text: 'Hold to take the egg',
      progress: Math.min(1, this.stealHold / biome.stealTime),
      kind: 'steal',
    };
  }

  private performSteal(biome: BiomeDef): void {
    if (!this.world.takeEggFrom(biome.id)) return;
    const egg = this.state.takeEgg(biome.id);
    this.stealHold = 0;
    this.stealTarget = null;
    if (!egg) return;

    // The wake IS the alarm. No countdown, no detection meter: the moment the
    // egg leaves the nest the run has started, and the player knows it because
    // something very large just stood up behind them.
    this.guardians.wake(biome.id);
    this.audio.play('steal');
    this.camera.addShake(0.25);
    this.callbacks.onEvent('stole', { biome, egg });
  }

  private deliver(): void {
    const placed = this.state.deliverCarried();
    if (placed > 0) {
      this.audio.play('levelUp');
      this.pendingDeliverFlash = 1.2;
      this.garden.sync();
      this.callbacks.onEvent('delivered', placed);
    }
  }

  private handleCaught(): void {
    const dropped = this.state.dropCarried();
    const position = this.player.state.position.clone();

    for (const [index, egg] of dropped.entries()) {
      const model = this.assets.instantiate(`models/props/egg-${egg.biome}.glb`);
      model.scale.setScalar(1.1 * SIZES[egg.size].scale);
      const spot = position.clone().add(new THREE.Vector3(
        Math.cos(index * 2.4) * 1.4, 0.4, Math.sin(index * 2.4) * 1.4,
      ));
      model.position.copy(spot);
      this.engine.scene.add(model);
      // A grace window before the guardian takes it back: being caught should
      // cost you tempo, not the whole run, and a desperate re-grab while it
      // lumbers toward the egg is the best comeback moment in the game.
      this.dropped.push({ egg, position: spot, model, reclaimIn: 12 });
    }

    this.player.stun(2.6);
    this.camera.addShake(1.2);
    this.camera.addKick(-0.22, (Math.random() - 0.5) * 0.3);
    this.audio.play('caught');
    this.state.notice(
      dropped.length > 0 ? 'Caught! You dropped the egg.' : 'Caught!',
      'bad',
    );
    this.callbacks.onEvent('caught', dropped.length);
  }

  private updateDroppedEggs(dt: number): void {
    for (let i = this.dropped.length - 1; i >= 0; i--) {
      const drop = this.dropped[i];
      drop.reclaimIn -= dt;
      drop.model.rotation.y += dt * 1.1;
      drop.model.position.y = drop.position.y + Math.sin(this.time * 2.2) * 0.08;
      if (drop.reclaimIn <= 0) {
        drop.model.removeFromParent();
        this.dropped.splice(i, 1);
        this.state.notice('The guardian took its egg back.', 'bad');
        this.guardians.sleep(drop.egg.biome);
      }
    }
  }

  // -- HUD ------------------------------------------------------------------

  private buildHud(inSafe: boolean): HudModel {
    const chaser = this.guardians.nearestChaser(this.player.state.position);
    let bearing: number | null = null;
    if (chaser) {
      const to = chaser.guardian.position.clone().sub(this.player.state.position);
      // Relative to where the camera is looking, so the indicator answers
      // "which way do I turn", not "which compass direction is it".
      bearing = Math.atan2(to.x, to.z) - (this.camera.yaw + Math.PI);
      while (bearing > Math.PI) bearing -= Math.PI * 2;
      while (bearing < -Math.PI) bearing += Math.PI * 2;
    }

    const cycle = DAY_SECONDS + NIGHT_SECONDS;
    const t = this.clock % cycle;
    const label = t < DAY_SECONDS
      ? `Day · ${Math.ceil(DAY_SECONDS - t)}s`
      : `Night · ${Math.ceil(cycle - t)}s`;

    return {
      money: this.state.money,
      incomePerSecond: this.state.incomePerSecond,
      speed: this.state.speed,
      trainingRate: this.state.trainingRatePerSecond,
      training: this.state.training,
      sprintSpeed: sprintSpeed(this.state.speed, DEFAULT_TUNING.sprintSpeed),
      carried: this.state.carried,
      carryLimit: this.state.carryLimit,
      prompt: this.prompt,
      threat: this.guardians.threat,
      threatBearing: bearing,
      stamina: this.player.state.stamina,
      staminaMax: this.state.staminaMax,
      zone: this.world.zoneAt(this.player.state.position),
      inSafeZone: inSafe,
      nightFactor: this.nightFactor,
      timeOfDayLabel: label,
      pedestalsUsed: this.state.placedPets.length + this.state.hatching.length,
      pedestalsTotal: this.state.pedestalSlots,
      nextBiome: BIOMES.find((biome) => this.state.speed < biome.speedGate) ?? null,
      collection: this.state.collectionProgress,
      fps: this.engine.fps,
    };
  }

  /** Every model path the game needs, for the loading screen. */
  static assetManifest(): string[] {
    const paths = new Set<string>();
    for (const pet of Object.values(PET_BY_ID)) paths.add(pet.model);
    for (const biome of BIOMES) paths.add(`models/props/egg-${biome.id}.glb`);
    paths.add('models/props/egg-event.glb');
    paths.add('models/props/egg-cracked.glb');
    return [...paths];
  }

  /** Only the assets needed before the player can move. */
  static coreManifest(): string[] {
    const paths = new Set<string>();
    for (const biome of BIOMES) {
      paths.add(`models/props/egg-${biome.id}.glb`);
      const pet = PET_BY_ID[biome.guardianPet];
      if (pet) paths.add(pet.model);
    }
    return [...paths];
  }

  /** Drop the player at an arbitrary point; used by the dev console. */
  teleportTo(x: number, y: number, z: number): void {
    this.player.teleport(new THREE.Vector3(x, y, z));
  }

  /** Put the player on a biome's nest platform. */
  gotoBiome(id: BiomeId): boolean {
    const nest = this.world.nests.get(id);
    if (!nest) return false;
    const at = nest.info.stealPosition;
    this.player.teleport(new THREE.Vector3(at.x, at.y + 1.2, at.z + 4));
    return true;
  }

  respawn(): void {
    this.player.teleport(this.world.spawn.clone().setY(this.world.spawn.y + 1));
    this.camera.addShake(0.2);
  }

  dispose(): void {
    this.guardians.dispose();
    this.garden.dispose();
    this.viewModel.dispose();
    this.world.dispose();
  }
}

function formatSpeed(value: number): string {
  if (value < 1000) return String(value);
  const units = ['', 'K', 'M', 'B', 'T'];
  let n = value;
  let tier = 0;
  while (n >= 1000 && tier < units.length - 1) {
    n /= 1000;
    tier++;
  }
  return `${n % 1 === 0 ? n : n.toFixed(1)}${units[tier]}`;
}

export { SAFE_RADIUS };
