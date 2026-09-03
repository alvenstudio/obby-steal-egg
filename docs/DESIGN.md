# Design notes

Why the game is built the way it is, and where it deliberately diverges from
the source design analysed in [`REFERENCE-ANALYSIS.md`](REFERENCE-ANALYSIS.md).

---

## 1. What was kept, and why

**One gating stat.** The source gates all eleven biomes on Speed and nothing
else — no money price, no rebirth wall. This is the best idea in the design and
it survives intact. The same number that opens a zone is the number that lets
you escape it, so the player is never handed content they cannot play, and the
whole progression collapses into one legible question: *am I fast enough yet?*

**Money buys rate, not Speed.** Cash cannot buy Speed directly. It buys
treadmill tiers and trail multipliers, which raise how fast training produces
Speed. That keeps the two currencies from collapsing into one and gives the pet
economy an actual job.

**The guardian sleeps.** No detection meter, no sight cone, no stealth. The
guardian wakes the instant the egg leaves the nest. This is a much better fit
for first person than a stealth system would be: the player is never punished
for information they could not see, and the encounter reduces to one clean
question — can I outrun this?

**Multiplicative rolls on every hatch.** Rarity × size × mutation means a
Titanic Rainbow Common can beat a plain Legendary, so no pull is a pure loss.

**The night reset.** A ~4:30 day and a ~13s night, during which every nest
refills and eggs hatch 30× faster. It is the only forced pause in the game and
it doubles as the beat that makes each day feel like a fresh run.

---

## 2. What changed, and why

### Guardian speed is a ratio, not a number

The source's guardian speeds are absolute values per biome. That is a latent
bug for any implementation whose movement curve is logarithmic in Speed — which
any implementation's must be, because Speed climbs to seven billion and the map
does not. A linear guardian table silently overtakes the player in the late
biomes and makes them unwinnable.

Here `guardianSpeedRatio` stores a *fraction of the player's sprint at that
biome's gate* and `guardianSpeedAt()` resolves it. "You escape by a hair at the
gate, and overtraining buys comfort" is then true by construction at every
tier, and retuning the movement curve cannot break it. A test enforces it.

The tutorial biome is deliberately generous (0.62); the ratio then tightens
monotonically to 0.97 at Titan Temple.

### Single-player, so PvP theft becomes PvE tension

The source advertises stealing from other players' bases. Without a server that
is not available, so the tension it provided is replaced by:

- **The dropped-egg window.** Being caught does not delete the egg. It drops at
  your feet with a 12-second timer before the guardian reclaims it. A desperate
  re-grab while something enormous lumbers toward it is the best comeback beat
  in the game, and it turns a catch into a cost in tempo rather than a wipe.
- **Storage instead of loss.** A full garden means new eggs stay in your hands,
  not that they evaporate.

### Biomes are money-free but the *map* is the gate too

The source's biomes have no lock at all — you can walk in and die. That is kept,
but each biome's nest sits at the top of a climb whose gaps scale with biome
order, so an under-levelled player physically cannot reach the egg. The lock is
level design rather than a UI check, which is much more honest in first person.

### An 8th Cherry Blossom pet

The source's public pet data lists seven pets for Cherry Blossom while its zone
page implies an eighth. An original Eternal-tier pet (**Oni Tiger**) fills the
slot so every biome has a uniform roster of eight.

---

## 3. First-person conversion

Third person hands the player three things for free that had to be rebuilt.

| Lost | Replacement |
|---|---|
| Seeing your own feet on a ledge | Viewmodel legs that fade in as you look down; coyote time (0.13s), jump buffering (0.16s), variable jump height, air control, and a 1.15-unit ledge mantle |
| Seeing what you are carrying | The egg is held in view — but it tucks toward the shoulder *and* fades to 38% as you pitch down, so it never covers the platform you are aiming at |
| Seeing behind you | A threat vignette scaled by proximity, a directional arc at the screen edge pointing at the nearest chaser, and fully positional guardian audio |

The last one matters most. The chase is the entire game and it comes from
behind, so **positional audio is a mechanic here, not decoration**: guardian
footfalls are panned and distance-attenuated so you can hear which side it is
closing from before you can see it.

Motion effects (head bob, shake) are separately scalable via `bobScale` and
`shakeScale` on the camera, because motion sensitivity varies a lot and this
genre's audience skews young.

---

## 4. Art pipeline

The reference is visually "Roblox blocky-plus": eight to twenty stacked
axis-aligned boxes with flat painted faces, matte plastic, no textures. That is
matched deliberately rather than substituted with smooth low-poly.

Three rules keep a hundred separately-authored creatures looking like one toy
line, all enforced by `blockkit.py`:

1. **Consistent bevel**, keyed to each box's smallest dimension, so a tiny beak
   and a huge torso catch light the same way.
2. **Proud face decals.** Eyes, markings and mouths are thin plates pushed a
   hair out of the surface they sit on. Flush decals z-fight; sunken ones
   vanish. `face_plate()` solves it once, and `face_of()` hands callers the
   exact face centre so nobody re-derives half-extent arithmetic by hand.
3. **Snapped proportions** from a shared unit grid.

Models face **+Y** in Blender, which the glTF exporter maps to −Z — the forward
axis Three.js expects — so a pet authored facing +Y walks correctly at runtime
with no fixup.

### Procedural animation instead of rigging

Rigging and hand-animating 107 creatures would have been the entire art budget,
and 40 skinned meshes on screen would cost far more at runtime. Instead every
model exports the same named parts and `PetAnimator` rotates whichever exist:

```
root, body, head, ear.L/.R, wing.L/.R, arm.L/.R,
leg.FL/.FR/.BL/.BR, tail, fin.L/.R, fin.tail
```

A pet with no legs skips the step cycle; one with wings gets a flap for free.
Gait, energy, hover, curiosity and waggle are per-pet, so an Axolotl and a
Mammoth do not idle identically. Phase is offset per instance so a shelf of
pets does not breathe in unison — that single detail is the difference between
"a collection" and "one animated object duplicated".

---

## 5. Original creations

The source roster includes meme characters from another franchise. Those slots
are filled with original creatures of the same tier and theme:

| Replaces a meme slot | Original | Biome / tier |
|---|---|---|
| — | **Branchwalker** | Forest, Legendary — a walking tree, ember-knot eyes, antler branches |
| — | **Anglerkin** | Lake, Epic — deep-lake angler with a lantern lure |
| — | **Dustpiper** | Desert, Epic — striding desert roadrunner |
| — | **Pineape** | Jungle, Legendary — ape wearing a pineapple shell |
| — | **Chili Imp** | Volcano, Mythic — chili-pepper devil, permanently furious |
| — | **Ringhorn Bovid** | Cosmic, Cosmic — bovine with a planetary ring |
| — | **Tarpitan** | Prehistoric, Secret — tar-soaked fossil beast |
| — | **Abyssal Maja** | Abyss, Eternal — colossal bioluminescent spider-crab |
| — | **Mallet Sentry**, **Peelfin**, **Bellug**, **Mangowing**, **Cocoa Croc** | Event pool |

The entire **Titan Temple** roster (Spideron, Crustacia, Bladehide, Mantaris,
Rhinotaur, Gorilla King, Nightflame) is original, as is **Oni Tiger**.

---

## 6. Tuning

Every curve is a closed-form function in `src/data/`, never a hand-written
table, so the whole economy can be retuned by moving a handful of constants.
The tests assert *relationships* — costs rise monotonically, rarer pays more,
the guardian is always slower than a just-qualified player — rather than pinned
constants that would rot on the first retune.

Deliberately compressed against the source: the reference is built for months
of play. This is tuned so a determined player reaches Titan Temple in a few
hours. `BASE_TRAINING_RATE`, the treadmill rate ladder and `SECONDS_TO_NEXT_BIOME`
are the knobs.

### Known open questions

- **Trail multipliers** apply to training rate only, not movement. The source's
  behaviour here is genuinely ambiguous across every source checked.
- **The Cosmic gate** (700M) is a 39× jump from Prehistoric — the harshest wall
  in the chain. It is kept for fidelity, but it is the first number to retune if
  playtesting stalls there.
- **Crumble platforms** are implemented in the physics `SurfaceKind` union but
  are not yet placed by the biome generator.

---

## 7. Deliberate omissions

Cut because they need a server, or because they would break the five-beat arc:

- PvP base raids, leaderboards, trading
- Fusing pets, and the pet-index claim rewards
- Gamepasses and any monetisation surface
- Mobile touch controls (the game is keyboard + mouse only)
