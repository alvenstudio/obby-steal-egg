"""
Generates src/data/pets.ts from docs/research/pets-roster.json.

The roster is the single source of truth for name/biome/rarity/income. This
script layers on the things the runtime needs but the roster does not carry:
a model path, a locomotion personality for the procedural animator, and a
pedestal scale. Keeping it generated means the roster and the game can never
disagree about how many pets exist.

    python tools/gen_pets.py
"""

from __future__ import annotations

import io
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

BIOME_ID = {
    "Forest": "forest", "Lake": "lake", "Desert": "desert", "Jungle": "jungle",
    "Snow": "snow", "Volcano": "volcano", "Abyss Ocean": "abyss",
    "Prehistoric": "prehistoric", "Cosmic": "cosmic",
    "Cherry Blossom": "blossom", "Titan Temple": "titan", "Event": "event",
}

# Locomotion is chosen per creature rather than per biome: a Frog and a Duckling
# share a pond but should not share a walk cycle.
SWIMMERS = {
    "frog", "catfish", "turtle", "parrotfish", "swordfish", "shark", "orca",
    "whale-shark", "beluga-whale", "koi", "kraken", "leviathan", "mosasaurus",
    "mutant-shark", "crustacia", "mantaris", "anglerkin", "axolotl",
    "abyssal-maja", "krakenoid", "mecha-krakenoid", "peelfin", "bellug",
    "duckling", "swan", "penguin", "walrus", "lava-frog", "froggo",
    "mecha-froggo",
}
FLIERS = {
    "bird", "burrowing-owl", "toucan", "crane", "pterodactyl", "snowy-owl",
    "phoenix", "ice-dragon", "lava-dragon", "cosmic-dragon",
    "eternal-lunar-dragon", "nightflame", "dreadscale", "mecha-dreadscale",
    "mangowing", "dodo",
}
FLOATERS = {
    "unicorn", "kitsune", "cosmic-skeleton-boss", "ringhorn-bovid",
    "cosmic-gecko", "cosmic-gorilla", "centipede",
}
HOPPERS = {"jerboa", "frog", "lava-frog", "froggo", "mecha-froggo", "chili-imp"}
SLITHERERS = {"snake", "king-snake", "tarpitan"}
MANY_LEGGED = {
    "spider", "sand-spider", "scorpion", "spideron", "crawler", "mecha-crawler",
    "centipede", "scorpio", "mecha-scorpio", "crustacia",
}

# Pets whose silhouette is fundamentally big; used for pedestal scale so a
# Mammoth does not render the same size as a Jerboa.
BULK = {
    "mammoth": 1.5, "king-mammoth": 1.7, "bronto": 1.9, "triceratops": 1.6,
    "t-rex": 1.7, "mosasaurus": 1.7, "whale-shark": 1.8, "beluga-whale": 1.6,
    "kraken": 1.8, "leviathan": 1.8, "gorilla-king": 1.6, "rhinotaur": 1.6,
    "bear": 1.3, "polar-bear": 1.35, "gorilla": 1.3, "cosmic-gorilla": 1.4,
    "walrus": 1.3, "orca": 1.5, "shark": 1.4, "mutant-shark": 1.6,
    "cerberus": 1.5, "yeti": 1.5, "nightflame": 1.7, "dreadscale": 1.7,
    "mecha-dreadscale": 1.7, "strawberry-elephant": 1.5, "camel": 1.3,
    "ankylosaurus": 1.4, "sabertooth-tiger": 1.25, "tiger": 1.25,
    "flaming-bull": 1.3, "crocodile": 1.35, "crocodon": 1.5,
    "mecha-crocodon": 1.5, "swordfish": 1.3, "stag": 1.35, "unicorn": 1.35,
    "kitsune": 1.4, "phoenix": 1.4, "ice-dragon": 1.5, "lava-dragon": 1.5,
    "cosmic-dragon": 1.5, "eternal-lunar-dragon": 1.55, "royal-sphinx": 1.5,
    "bladehide": 1.45, "mantaris": 1.4, "spideron": 1.35, "drilla": 1.3,
    "chicken": 0.85, "jerboa": 0.7, "frog": 0.75, "duckling": 0.7,
    "bird": 0.75, "catfish": 0.85, "fennec": 0.85, "burrowing-owl": 0.8,
}


def personality(pet_id: str, rarity: str) -> dict:
    if pet_id in SLITHERERS:
        gait = "slither"
    elif pet_id in FLOATERS:
        gait = "float"
    elif pet_id in FLIERS:
        gait = "fly"
    elif pet_id in SWIMMERS:
        gait = "swim"
    elif pet_id in HOPPERS:
        gait = "hop"
    else:
        gait = "walk"

    # Rarer pets read as more "charged": faster idle, more hover, brighter aura.
    rank = [
        "common", "uncommon", "rare", "epic", "legendary",
        "mythic", "cosmic", "secret", "eternal", "divine", "event",
    ].index(rarity)
    energy = round(0.82 + rank * 0.055, 3)
    hover = 0.0
    if gait in ("float", "fly"):
        hover = round(0.22 + rank * 0.02, 3)
    elif gait == "swim":
        hover = round(0.14 + rank * 0.012, 3)

    return {
        "gait": gait,
        "energy": energy,
        "bounce": round(0.028 + (0.02 if gait == "hop" else 0.0), 3),
        "hover": hover,
        "curiosity": round(0.09 + (0.06 if rank < 4 else 0.02), 3),
        "waggle": round(0.34 if gait == "walk" else 0.2, 3),
        "flutter": round(1.0 + (0.55 if gait == "fly" else 0.0), 3),
    }


def ts_string(value: str) -> str:
    return "'" + value.replace("\\", "\\\\").replace("'", "\\'") + "'"


def main() -> None:
    roster_path = os.path.join(ROOT, "docs", "research", "pets-roster.json")
    pets = json.load(io.open(roster_path, encoding="utf-8"))

    lines = [
        "/**",
        " * The full pet roster -- GENERATED, do not edit by hand.",
        " *",
        " * Source of truth: docs/research/pets-roster.json",
        " * Regenerate with: python tools/gen_pets.py",
        " *",
        " * `income` is the base payout per second for a Normal, unmutated pet.",
        " * Size and mutation rolls multiply it at hatch time (see data/rarity).",
        " */",
        "",
        "import type { BiomeId } from './biomes';",
        "import type { RarityId } from './rarity';",
        "import type { Gait } from '@/fx/PetAnimator';",
        "",
        "export interface PetPersonalitySpec {",
        "  gait: Gait;",
        "  energy: number;",
        "  bounce: number;",
        "  hover: number;",
        "  curiosity: number;",
        "  waggle: number;",
        "  flutter: number;",
        "}",
        "",
        "export interface PetDef {",
        "  id: string;",
        "  name: string;",
        "  biome: BiomeId;",
        "  rarity: RarityId;",
        "  /** Base income per second before size and mutation multipliers. */",
        "  income: number;",
        "  /** Path to the .glb, relative to the site root. */",
        "  model: string;",
        "  /** Display scale on a pedestal and when following the player. */",
        "  scale: number;",
        "  personality: PetPersonalitySpec;",
        "}",
        "",
        "export const PETS: PetDef[] = [",
    ]

    for pet in sorted(pets, key=lambda p: (p["income"], p["name"])):
        pid = pet["id"]
        biome = BIOME_ID[pet["biome"]]
        p = personality(pid, pet["rarity"])
        scale = BULK.get(pid, 1.0)
        lines.append("  {")
        lines.append("    id: %s," % ts_string(pid))
        lines.append("    name: %s," % ts_string(pet["name"]))
        lines.append("    biome: %s," % ts_string(biome))
        lines.append("    rarity: %s," % ts_string(pet["rarity"]))
        lines.append("    income: %d," % pet["income"])
        lines.append("    model: %s," % ts_string("models/pets/%s.glb" % pid))
        lines.append("    scale: %s," % scale)
        lines.append("    personality: {")
        lines.append("      gait: %s, energy: %s, bounce: %s, hover: %s,"
                     % (ts_string(p["gait"]), p["energy"], p["bounce"], p["hover"]))
        lines.append("      curiosity: %s, waggle: %s, flutter: %s,"
                     % (p["curiosity"], p["waggle"], p["flutter"]))
        lines.append("    },")
        lines.append("  },")

    lines += [
        "];",
        "",
        "export const PET_BY_ID: Record<string, PetDef> = Object.fromEntries(",
        "  PETS.map((pet) => [pet.id, pet]),",
        ");",
        "",
        "/** Every pet obtainable from a given biome's eggs. */",
        "export function petsOfBiome(biome: BiomeId): PetDef[] {",
        "  return PETS.filter((pet) => pet.biome === biome);",
        "}",
        "",
        "/** Pets of one biome at one rarity -- the pool a hatch draws from. */",
        "export function petsOfBiomeRarity(biome: BiomeId, rarity: RarityId): PetDef[] {",
        "  return PETS.filter((pet) => pet.biome === biome && pet.rarity === rarity);",
        "}",
        "",
        "export const TOTAL_PETS = PETS.length;",
        "",
    ]

    out_path = os.path.join(ROOT, "src", "data", "pets.ts")
    io.open(out_path, "w", encoding="utf-8", newline="\n").write("\n".join(lines))
    print("wrote %s (%d pets)" % (out_path, len(pets)))

    # A manifest the Blender build reads, so model generation and gameplay data
    # can never disagree about which pets exist.
    manifest = [
        {
            "id": p["id"], "name": p["name"],
            "biome": BIOME_ID[p["biome"]], "rarity": p["rarity"],
            "income": p["income"], "scale": BULK.get(p["id"], 1.0),
        }
        for p in pets
    ]
    manifest_path = os.path.join(ROOT, "tools", "blender", "pet_manifest.json")
    io.open(manifest_path, "w", encoding="utf-8", newline="\n").write(
        json.dumps(manifest, ensure_ascii=False, indent=1))
    print("wrote %s" % manifest_path)


if __name__ == "__main__":
    main()
