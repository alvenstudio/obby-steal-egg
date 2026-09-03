import { formatMoney, formatRate } from '@/data/balance';
import { PET_BY_ID } from '@/data/pets';
import { MUTATIONS, RARITIES, SIZES } from '@/data/rarity';
import type { HudModel } from '@/game/Session';

/**
 * The heads-up display.
 *
 * Two rules govern everything here.
 *
 * First, the HUD must never be the reason a jump was missed, so the centre of
 * the screen holds only a reticle, a hold-ring and one line of prompt text.
 * Everything else lives in the corners.
 *
 * Second, first person removes peripheral vision, and this game's core tension
 * is a thing chasing you from behind. The threat vignette and the edge arc are
 * therefore not decoration -- they are the replacement for being able to see
 * over your own shoulder, and they are the only HUD elements allowed to take
 * over the screen.
 */

export class Hud {
  private root: HTMLElement;
  private moneyValue!: HTMLElement;
  private moneySub!: HTMLElement;
  private speedValue!: HTMLElement;
  private speedSub!: HTMLElement;
  private speedStat!: HTMLElement;
  private gateFill!: HTMLElement;
  private zone!: HTMLElement;
  private zoneName!: HTMLElement;
  private zoneClock!: HTMLElement;
  private prompt!: HTMLElement;
  private ringFill!: SVGCircleElement;
  private stamina!: HTMLElement;
  private staminaFill!: HTMLElement;
  private threat!: HTMLElement;
  private chase!: HTMLElement;
  private chaseArc!: HTMLElement;
  private carried!: HTMLElement;
  private toasts!: HTMLElement;
  private slots!: HTMLElement;
  private collection!: HTMLElement;
  private debug!: HTMLElement;

  private lastPromptText = '';
  private lastCarriedKey = '';
  private ringCircumference = 0;

  showDebug = false;

  constructor(container: HTMLElement) {
    this.root = document.createElement('div');
    this.root.id = 'ui';
    this.root.innerHTML = TEMPLATE;
    container.appendChild(this.root);

    const q = <T extends Element>(selector: string): T =>
      this.root.querySelector(selector) as T;

    this.moneyValue = q('#money-value');
    this.moneySub = q('#money-sub');
    this.speedValue = q('#speed-value');
    this.speedSub = q('#speed-sub');
    this.speedStat = q('#speed-stat');
    this.gateFill = q('#gate-fill');
    this.zone = q('#zone');
    this.zoneName = q('#zone-name');
    this.zoneClock = q('#zone-clock');
    this.prompt = q('#prompt');
    this.ringFill = q<SVGCircleElement>('#ring-fill');
    this.stamina = q('#stamina');
    this.staminaFill = q('#stamina-fill');
    this.threat = q('#threat');
    this.chase = q('#chase-arrow');
    this.chaseArc = q('#chase-arc');
    this.carried = q('#carried');
    this.toasts = q('#toasts');
    this.slots = q('#slots');
    this.collection = q('#collection');
    this.debug = q('#debug');

    const radius = Number(this.ringFill.getAttribute('r'));
    this.ringCircumference = 2 * Math.PI * radius;
    this.ringFill.style.strokeDasharray = String(this.ringCircumference);
    this.ringFill.style.strokeDashoffset = String(this.ringCircumference);
  }

  update(model: HudModel): void {
    this.moneyValue.textContent = formatMoney(model.money);
    this.moneySub.textContent = formatRate(model.incomePerSecond);

    this.speedValue.textContent = formatMoney(model.speed);
    this.speedSub.textContent = model.training
      ? `+${formatMoney(model.trainingRate)}/s · ${model.sprintSpeed.toFixed(1)} m/s`
      : `${model.sprintSpeed.toFixed(1)} m/s sprint`;
    this.speedStat.classList.toggle('training', model.training);

    // Progress toward the next gate is shown on a log scale, because on a
    // linear one the bar would sit at zero for 90% of every tier.
    if (model.nextBiome) {
      const from = previousGate(model.nextBiome.speedGate);
      const progress = logProgress(from, model.nextBiome.speedGate, model.speed);
      this.gateFill.style.width = `${(progress * 100).toFixed(1)}%`;
      this.gateFill.parentElement!.title =
        `${model.nextBiome.name} at ${formatMoney(model.nextBiome.speedGate)} Speed`;
    } else {
      this.gateFill.style.width = '100%';
    }

    this.zoneName.textContent = model.inSafeZone
      ? 'Safe Zone'
      : model.zone
        ? model.zone.name
        : 'The Long Road';
    this.zoneClock.textContent = model.timeOfDayLabel;
    this.zone.classList.toggle('safe', model.inSafeZone);
    this.zone.classList.toggle('night', model.nightFactor > 0.5);

    this.updatePrompt(model);
    this.updateStamina(model);
    this.updateThreat(model);
    this.updateCarried(model);

    this.slots.textContent = `${model.pedestalsUsed}/${model.pedestalsTotal} pedestals`;
    this.collection.textContent =
      `${model.collection.found}/${model.collection.total} pets found`;

    this.debug.style.display = this.showDebug ? 'block' : 'none';
    if (this.showDebug) {
      this.debug.textContent = `${model.fps.toFixed(0)} fps`;
    }
  }

  private updatePrompt(model: HudModel): void {
    const prompt = model.prompt;
    if (!prompt) {
      this.prompt.classList.remove('show');
      this.ringFill.style.strokeDashoffset = String(this.ringCircumference);
      this.lastPromptText = '';
      return;
    }

    const key = prompt.kind === 'info' ? '' : '<kbd>E</kbd>';
    const blocked = prompt.blocked
      ? `<div class="blocked">${escapeHtml(prompt.blocked)}</div>`
      : '';
    const html = `${key}${escapeHtml(prompt.text)}${blocked}`;
    if (html !== this.lastPromptText) {
      this.prompt.innerHTML = html;
      this.lastPromptText = html;
    }
    this.prompt.classList.add('show');

    const progress = prompt.progress ?? 0;
    this.ringFill.style.strokeDashoffset =
      String(this.ringCircumference * (1 - progress));
  }

  private updateStamina(model: HudModel): void {
    const ratio = model.staminaMax > 0 ? model.stamina / model.staminaMax : 1;
    const show = ratio < 0.995;
    this.stamina.classList.toggle('show', show);
    this.stamina.classList.toggle('low', ratio < 0.3);
    this.staminaFill.style.width = `${(ratio * 100).toFixed(1)}%`;
  }

  private updateThreat(model: HudModel): void {
    const active = model.threat > 0.12;
    this.threat.classList.toggle('on', active);
    this.threat.style.opacity = active ? String(Math.min(1, model.threat * 0.9)) : '0';

    if (model.threatBearing !== null && model.threat > 0.15) {
      this.chase.classList.add('on');
      // The arc rotates to sit on the screen edge in the guardian's direction;
      // straight behind you puts it at the bottom.
      const degrees = (model.threatBearing * 180) / Math.PI;
      this.chaseArc.style.transform = `rotate(${degrees}deg)`;
      this.chaseArc.style.opacity = String(Math.min(1, 0.4 + model.threat));
    } else {
      this.chase.classList.remove('on');
    }
  }

  private updateCarried(model: HudModel): void {
    const key = model.carried.map((egg) => `${egg.petId}:${egg.size}:${egg.mutation}`).join('|');
    if (key === this.lastCarriedKey) return;
    this.lastCarriedKey = key;

    this.carried.innerHTML = '';
    for (const egg of model.carried) {
      const def = PET_BY_ID[egg.petId];
      const rarity = def ? RARITIES[def.rarity] : RARITIES.common;
      const chip = document.createElement('div');
      chip.className = 'egg-chip';
      chip.style.borderLeftColor = rarity.color;
      // The species is deliberately hidden until it hatches: knowing you are
      // carrying a Divine would make being caught unbearable rather than
      // exciting. Rarity alone is enough to raise the stakes.
      const bits = [SIZES[egg.size].name, MUTATIONS[egg.mutation].name]
        .filter(Boolean)
        .join(' ');
      chip.innerHTML =
        `<div class="name">${escapeHtml(rarity.name)} Egg</div>` +
        `<div class="meta">${escapeHtml(bits || 'unmarked')}</div>`;
      this.carried.appendChild(chip);
    }
  }

  toast(title: string, sub = '', tone: 'info' | 'good' | 'bad' = 'info', big = false): void {
    const element = document.createElement('div');
    element.className = `toast ${tone}${big ? ' big' : ''}`;
    element.innerHTML =
      `<div class="title">${escapeHtml(title)}</div>` +
      (sub ? `<div class="sub">${escapeHtml(sub)}</div>` : '');
    this.toasts.appendChild(element);

    window.setTimeout(() => {
      element.classList.add('leaving');
      window.setTimeout(() => element.remove(), 320);
    }, big ? 4200 : 2800);

    // Never let the stack grow past what fits on screen.
    while (this.toasts.children.length > 6) {
      this.toasts.firstElementChild?.remove();
    }
  }

  setVisible(visible: boolean): void {
    this.root.style.display = visible ? 'block' : 'none';
  }
}

function previousGate(gate: number): number {
  // Gates climb by roughly an order of magnitude; the previous one is a good
  // enough origin for a progress bar without threading the whole list through.
  return gate / 12;
}

function logProgress(from: number, to: number, value: number): number {
  const a = Math.log10(Math.max(1, from));
  const b = Math.log10(Math.max(10, to));
  const v = Math.log10(Math.max(1, value));
  return Math.max(0, Math.min(1, (v - a) / Math.max(0.0001, b - a)));
}

export function escapeHtml(value: string): string {
  return value
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

const TEMPLATE = `
  <div class="corner tl">
    <div class="stat money">
      <div class="label">Money</div>
      <div class="value" id="money-value">0</div>
      <div class="sub" id="money-sub">0/s</div>
    </div>
    <div id="carried"></div>
  </div>

  <div class="corner tc">
    <div class="zone" id="zone">
      <span id="zone-name">Safe Zone</span>
      <span class="clock" id="zone-clock"></span>
    </div>
  </div>

  <div class="corner tr">
    <div class="stat speed" id="speed-stat">
      <div class="label">Speed</div>
      <div class="value" id="speed-value">0</div>
      <div class="sub" id="speed-sub"></div>
      <div class="gate-bar"><i id="gate-fill"></i></div>
    </div>
  </div>

  <div class="corner br">
    <div class="stat">
      <div class="label">Garden</div>
      <div class="sub" id="slots">0/4 pedestals</div>
      <div class="sub" id="collection">0/107 pets found</div>
    </div>
  </div>

  <div id="threat"></div>
  <div id="chase-arrow"><div class="arc" id="chase-arc"></div></div>

  <div id="reticle">
    <svg viewBox="0 0 34 34">
      <circle class="track" cx="17" cy="17" r="14"></circle>
      <circle class="fill" id="ring-fill" cx="17" cy="17" r="14"
              transform="rotate(-90 17 17)"></circle>
    </svg>
    <div class="dot"></div>
  </div>

  <div id="stamina"><i id="stamina-fill"></i></div>
  <div id="prompt"></div>
  <div id="toasts"></div>
  <div id="debug"></div>
`;
