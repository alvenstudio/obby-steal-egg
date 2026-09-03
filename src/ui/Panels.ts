import { formatMoney, formatRate } from '@/data/balance';
import { BIOMES, BIOME_BY_ID } from '@/data/biomes';
import { PETS } from '@/data/pets';
import {
  TRAILS, TREADMILLS, UPGRADES, UPGRADE_ORDER, UpgradeId,
  previewRebirth, rebirthCost, upgradeCostAt,
} from '@/data/progression';
import { MUTATIONS, RARITIES, SIZES } from '@/data/rarity';
import type { GameState, OwnedPet } from '@/game/GameState';

import { escapeHtml } from './Hud';

export type PanelId = 'shop' | 'treadmill' | 'trail' | 'rebirth' | 'index' | 'storage';

/**
 * The shop, treadmill, trail, rebirth, index and storage panels.
 *
 * All six share one container and one render pass because they share one job:
 * show a number, show what it becomes, show the price. The reference game's
 * shops are a wall of buttons; the thing worth improving is making the
 * *consequence* legible, so every row states the effect at the current level
 * and the effect one level up rather than just a price.
 */

export interface PanelCallbacks {
  onClose: () => void;
  onChanged: () => void;
}

export class Panels {
  private root: HTMLElement;
  private body: HTMLElement;
  private title: HTMLElement;
  private hint: HTMLElement;
  private current: PanelId | null = null;

  constructor(
    container: HTMLElement,
    private readonly state: GameState,
    private readonly callbacks: PanelCallbacks,
  ) {
    this.root = document.createElement('div');
    this.root.id = 'panels';
    this.root.innerHTML = `
      <div class="panel">
        <header>
          <h2 id="panel-title">Upgrades</h2>
          <span class="hint" id="panel-hint"></span>
          <button class="close" id="panel-close">Close · Esc</button>
        </header>
        <div class="body" id="panel-body"></div>
      </div>
    `;
    container.appendChild(this.root);

    this.body = this.root.querySelector('#panel-body') as HTMLElement;
    this.title = this.root.querySelector('#panel-title') as HTMLElement;
    this.hint = this.root.querySelector('#panel-hint') as HTMLElement;

    (this.root.querySelector('#panel-close') as HTMLElement)
      .addEventListener('click', () => this.close());
    this.root.addEventListener('click', (event) => {
      if (event.target === this.root) this.close();
    });
  }

  get isOpen(): boolean {
    return this.current !== null;
  }

  open(panel: PanelId): void {
    this.current = panel;
    this.root.classList.add('open');
    this.render();
  }

  close(): void {
    if (!this.current) return;
    this.current = null;
    this.root.classList.remove('open');
    this.callbacks.onClose();
  }

  /** Re-render in place; called after every purchase so prices stay live. */
  render(): void {
    if (!this.current) return;
    switch (this.current) {
      case 'shop': this.renderShop(); break;
      case 'treadmill': this.renderTreadmill(); break;
      case 'trail': this.renderTrail(); break;
      case 'rebirth': this.renderRebirth(); break;
      case 'index': this.renderIndex(); break;
      case 'storage': this.renderStorage(); break;
    }
  }

  private setHeader(title: string, hint: string): void {
    this.title.textContent = title;
    this.hint.textContent = hint;
  }

  private button(
    label: string,
    cost: number | null,
    enabled: boolean,
    onClick: () => void,
    maxed = false,
  ): HTMLButtonElement {
    const button = document.createElement('button');
    button.className = `buy${maxed ? ' max' : ''}`;
    button.textContent = cost === null ? label : `${label} ${formatMoney(cost)}`;
    button.disabled = !enabled;
    button.addEventListener('click', () => {
      onClick();
      this.callbacks.onChanged();
      this.render();
    });
    return button;
  }

  // -- upgrades -------------------------------------------------------------

  private renderShop(): void {
    this.setHeader('Upgrades', `${formatMoney(this.state.money)} available`);
    this.body.innerHTML = '';

    for (const id of UPGRADE_ORDER) {
      const spec = UPGRADES[id as UpgradeId];
      const level = this.state.upgrades[id as UpgradeId];
      const maxed = level >= spec.maxLevel;
      const cost = upgradeCostAt(id as UpgradeId, level);

      const row = document.createElement('div');
      row.className = 'row';
      // Showing "now -> next" rather than a bare price is the difference
      // between a shop and a slot machine.
      const nextEffect = maxed ? '' : ` → ${spec.effect(level + 1)}`;
      row.innerHTML = `
        <div class="info">
          <div class="name">${escapeHtml(spec.name)}</div>
          <div class="desc">${escapeHtml(spec.description)}</div>
          <div class="effect">${escapeHtml(spec.effect(level) + nextEffect)}</div>
        </div>
        <div class="lvl">Lv ${level}/${spec.maxLevel}</div>
      `;
      row.appendChild(
        maxed
          ? this.button('Maxed', null, false, () => {}, true)
          : this.button('Buy', cost, this.state.money >= cost,
              () => this.state.buyUpgrade(id as UpgradeId)),
      );
      this.body.appendChild(row);
    }
  }

  // -- treadmill ------------------------------------------------------------

  private renderTreadmill(): void {
    this.setHeader(
      'Treadmill',
      `Training at ${formatMoney(this.state.trainingRatePerSecond)} Speed/s`,
    );
    this.body.innerHTML = '';

    const intro = document.createElement('div');
    intro.className = 'row';
    intro.innerHTML = `
      <div class="info">
        <div class="name">Speed is the only key</div>
        <div class="desc">Money cannot buy Speed directly. It buys a faster belt,
        and the belt buys Speed. Every biome opens at a Speed number, and that
        same number is what lets you outrun the thing guarding it.</div>
        <div class="effect">Run on the belt in the safe zone to train.</div>
      </div>
    `;
    this.body.appendChild(intro);

    for (const [index, tier] of TREADMILLS.entries()) {
      const owned = index <= this.state.treadmillTier;
      const next = index === this.state.treadmillTier + 1;
      if (!owned && !next) continue;

      const row = document.createElement('div');
      row.className = 'row';
      row.style.borderLeft = `3px solid ${tier.color}`;
      row.innerHTML = `
        <div class="info">
          <div class="name">${escapeHtml(tier.name)} <span class="pill">Tier ${index}</span></div>
          <div class="effect">×${tier.rate} training rate</div>
        </div>
        <div class="lvl">${owned ? 'Owned' : ''}</div>
      `;
      if (!owned) {
        row.appendChild(this.button('Upgrade', tier.cost,
          this.state.money >= tier.cost, () => this.state.buyTreadmill()));
      }
      this.body.appendChild(row);
    }

    this.appendGateTable();
  }

  private appendGateTable(): void {
    const heading = document.createElement('div');
    heading.className = 'index-biome';
    heading.textContent = 'Speed gates';
    this.body.appendChild(heading);

    for (const biome of BIOMES) {
      const unlocked = this.state.speed >= biome.speedGate;
      const row = document.createElement('div');
      row.className = 'row';
      row.style.borderLeft = `3px solid ${biome.palette.accent}`;
      row.style.opacity = unlocked ? '1' : '0.62';
      const remaining = Math.max(0, biome.speedGate - this.state.speed);
      const eta = this.state.trainingRatePerSecond > 0
        ? remaining / this.state.trainingRatePerSecond
        : Infinity;
      row.innerHTML = `
        <div class="info">
          <div class="name">${escapeHtml(biome.name)}</div>
          <div class="desc">${escapeHtml(biome.tagline)}</div>
          <div class="effect">${formatMoney(biome.speedGate)} Speed${
            unlocked ? ' · open' : ` · ${formatDuration(eta)} of training away`
          }</div>
        </div>
        <div class="lvl">${unlocked ? '✓' : '🔒'}</div>
      `;
      this.body.appendChild(row);
    }
  }

  // -- trails ---------------------------------------------------------------

  private renderTrail(): void {
    this.setHeader('Trails', 'Multiplies your training rate');
    this.body.innerHTML = '';

    for (const [index, trail] of TRAILS.entries()) {
      const owned = index <= this.state.trailTier;
      const next = index === this.state.trailTier + 1;
      if (!owned && !next) continue;

      const row = document.createElement('div');
      row.className = 'row';
      row.style.borderLeft = `3px solid ${trail.color}`;
      row.innerHTML = `
        <div class="info">
          <div class="name">${escapeHtml(trail.name)}</div>
          <div class="effect">×${trail.multiplier} training rate</div>
        </div>
        <div class="lvl">${owned ? (index === this.state.trailTier ? 'Equipped' : 'Owned') : ''}</div>
      `;
      if (!owned) {
        row.appendChild(this.button('Buy', trail.cost,
          this.state.money >= trail.cost, () => this.state.buyTrail()));
      }
      this.body.appendChild(row);
    }
  }

  // -- rebirth --------------------------------------------------------------

  private renderRebirth(): void {
    this.setHeader('Rebirth', `${this.state.rebirths} completed`);
    this.body.innerHTML = '';

    const next = this.state.rebirths + 1;
    const preview = previewRebirth(
      this.state.rebirths, this.state.speed, this.state.incomeMultiplier,
    );
    const cost = rebirthCost(next);
    const affordable = this.state.money >= cost;

    const row = document.createElement('div');
    row.className = 'row';
    row.innerHTML = `
      <div class="info">
        <div class="name">Rebirth ${next}</div>
        <div class="desc">Resets your money, pets, treadmill and trail. Keeps your
        pedestals and your index, and hands back a slice of your Speed so the
        climb is shorter every time.</div>
        <div class="effect">
          Income ×${preview.incomeBefore.toFixed(2)} → ×${preview.incomeAfter.toFixed(2)} ·
          keep ${formatMoney(preview.keptSpeed)} Speed ·
          +${preview.luckGain.toFixed(2)} luck
        </div>
      </div>
    `;
    row.appendChild(this.button('Rebirth', cost, affordable, () => {
      if (this.state.canRebirth()) this.state.rebirth();
    }));
    this.body.appendChild(row);

    const stats = document.createElement('div');
    stats.className = 'row';
    stats.innerHTML = `
      <div class="info">
        <div class="name">Run so far</div>
        <div class="effect">
          ${this.state.stats.eggsStolen} eggs stolen ·
          ${this.state.stats.timesCaught} times caught ·
          ${this.state.stats.petsHatched} hatched ·
          ${formatMoney(this.state.stats.totalEarned)} earned ·
          ${formatRate(this.state.incomePerSecond)} now
        </div>
      </div>
    `;
    this.body.appendChild(stats);
  }

  // -- pet index ------------------------------------------------------------

  private renderIndex(): void {
    const progress = this.state.collectionProgress;
    this.setHeader('Pet Index', `${progress.found} of ${progress.total} discovered`);
    this.body.innerHTML = '';

    const order = [...BIOMES.map((biome) => biome.id), 'event' as const];
    for (const biomeId of order) {
      const pets = PETS.filter((pet) => pet.biome === biomeId);
      if (pets.length === 0) continue;
      const biome = BIOME_BY_ID[biomeId];
      const found = pets.filter((pet) => this.state.discovered.has(pet.id)).length;

      const heading = document.createElement('div');
      heading.className = 'index-biome';
      heading.textContent =
        `${biome ? biome.name : 'Limited & Event'} — ${found}/${pets.length}`;
      this.body.appendChild(heading);

      const grid = document.createElement('div');
      grid.className = 'index-grid';
      for (const pet of [...pets].sort((a, b) => a.income - b.income)) {
        const known = this.state.discovered.has(pet.id);
        const rarity = RARITIES[pet.rarity];
        const card = document.createElement('div');
        card.className = `pet-card${known ? '' : ' locked'}`;
        card.style.borderLeftColor = rarity.color;
        card.innerHTML = `
          <div class="name">${escapeHtml(known ? pet.name : '???')}</div>
          <div class="rarity" style="color:${rarity.color}">${escapeHtml(rarity.name)}</div>
          <div class="income">${known ? formatRate(pet.income) : '—'}</div>
        `;
        grid.appendChild(card);
      }
      this.body.appendChild(grid);
    }
  }

  // -- storage --------------------------------------------------------------

  private renderStorage(): void {
    const stored = this.state.storedPets;
    this.setHeader('Storage', `${stored.length} pets waiting for a pedestal`);
    this.body.innerHTML = '';

    if (stored.length === 0) {
      const empty = document.createElement('div');
      empty.className = 'row';
      empty.innerHTML = `<div class="info"><div class="name">Nothing in storage</div>
        <div class="desc">Pets land here when every pedestal is taken. Buy more
        pedestals in Upgrades, or swap one out below.</div></div>`;
      this.body.appendChild(empty);
    }

    const placed = [...this.state.placedPets].sort(
      (a, b) => this.state.petIncome(a) - this.state.petIncome(b),
    );

    for (const pet of [...stored].sort(
      (a, b) => this.state.petIncome(b) - this.state.petIncome(a),
    )) {
      this.body.appendChild(this.petRow(pet, placed[0]));
    }

    if (placed.length > 0) {
      const heading = document.createElement('div');
      heading.className = 'index-biome';
      heading.textContent = 'On display';
      this.body.appendChild(heading);
      for (const pet of [...placed].reverse()) {
        this.body.appendChild(this.petRow(pet, undefined));
      }
    }
  }

  private petRow(pet: OwnedPet, swapWith: OwnedPet | undefined): HTMLElement {
    const def = this.state.definition(pet);
    const rarity = def ? RARITIES[def.rarity] : RARITIES.common;
    const row = document.createElement('div');
    row.className = 'row';
    row.style.borderLeft = `3px solid ${rarity.color}`;
    const income = this.state.petIncome(pet);
    const tags = [SIZES[pet.size].name, MUTATIONS[pet.mutation].name].filter(Boolean);
    row.innerHTML = `
      <div class="info">
        <div class="name">${escapeHtml(this.state.displayName(pet))}</div>
        <div class="desc" style="color:${rarity.color}">${escapeHtml(rarity.name)}${
          tags.length ? ` · ${escapeHtml(tags.join(' · '))}` : ''
        }</div>
        <div class="effect">${formatRate(income)}</div>
      </div>
      <div class="lvl">${pet.slot >= 0 ? `Slot ${pet.slot + 1}` : 'Stored'}</div>
    `;

    if (pet.slot < 0) {
      const free = this.state.firstFreeSlot();
      if (free >= 0) {
        row.appendChild(this.button('Place', null, true, () => { pet.slot = free; }));
      } else if (swapWith && this.state.petIncome(swapWith) < income) {
        // Only offer the swap when it is actually an upgrade; a button that
        // silently makes you poorer is a trap, not a feature.
        row.appendChild(this.button('Swap in', null, true, () => {
          const slot = swapWith.slot;
          swapWith.slot = -1;
          pet.slot = slot;
        }));
      }
    } else {
      row.appendChild(this.button('Store', null, true, () => { pet.slot = -1; }));
    }
    return row;
  }
}

function formatDuration(seconds: number): string {
  if (!Number.isFinite(seconds)) return 'a while';
  if (seconds < 60) return `${Math.ceil(seconds)}s`;
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m`;
  const hours = Math.floor(minutes / 60);
  return `${hours}h ${minutes % 60}m`;
}
