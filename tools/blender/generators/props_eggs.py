"""
Eggs -- one per biome, plus the shared cracked/hatching variants.

An egg is on screen at three very different scales: sitting in a nest fifty
metres away, filling a third of the screen while carried, and cracking open on
a pedestal. So the read has to come from the silhouette and the shell pattern,
not from detail: each biome's egg is a distinct shape AND a distinct pattern,
because colour alone stops working the moment the player is colour-blind or
the biome is dark.
"""

import math

import blockkit as bk
import kit


def _shell(name, color, tall=1.0, wide=1.0, segments=7):
    """
    A blocky egg: a stack of boxes whose width follows an egg profile. Reads as
    a smooth ovoid at any distance while staying in the voxel language.
    """
    parts = []
    height = 1.0 * tall
    for i in range(segments):
        t = (i + 0.5) / segments
        # Egg profile: fat and round at the bottom, tapering to a narrower top.
        radius = math.sin(math.pi * (0.12 + t * 0.82)) * (1.0 - 0.22 * t)
        w = radius * 0.78 * wide
        parts.append(bk.block(
            "%s.%d" % (name, i), (w, w, height / segments * 1.06),
            (0, 0, height * (t - 0.5) + height * 0.5),
            color=color,
        ))
    return parts


def _finish(root, parts_by_group):
    bk.assemble(root, parts_by_group)
    kit.normalize_height(root, 1.0)
    return root


def _egg(color, accent, decorate=None, tall=1.0, wide=1.0, glow=None):
    kit.reset_scene()
    root = kit.empty("root")
    parts = _shell("body.shell", color, tall=tall, wide=wide)
    if decorate:
        parts += decorate(color, accent)
    if glow:
        parts.append(bk.glow_block("body.core", (0.2, 0.2, 0.2), (0, 0, 0.45),
                                   color=glow, strength=3.0))
    return _finish(root, {"body": (parts, (0, 0, 0))})


# --- pattern vocabulary -----------------------------------------------------


def _speckles(seed, color, count=7, size=0.11):
    def decorate(_base, accent):
        parts = []
        state = seed * 7919 + 3
        for i in range(count):
            state = (state * 1103515245 + 12345) & 0x7FFFFFFF
            angle = (state / 0x7FFFFFFF) * math.tau
            state = (state * 1103515245 + 12345) & 0x7FFFFFFF
            h = 0.18 + (state / 0x7FFFFFFF) * 0.66
            r = math.sin(math.pi * (0.12 + h * 0.82)) * 0.4
            parts.append(bk.block(
                "body.spot%d" % i, (size, size, size * 0.5),
                (math.cos(angle) * r, math.sin(angle) * r, h),
                rot=(0, 0, math.degrees(angle)), color=accent,
            ))
        return parts
    _ = color
    return decorate


def _bands(count=3, thickness=0.09):
    def decorate(_base, accent):
        parts = []
        for i in range(count):
            t = (i + 1) / (count + 1)
            radius = math.sin(math.pi * (0.12 + t * 0.82)) * (1.0 - 0.22 * t)
            w = radius * 0.8
            parts.append(bk.block(
                "body.band%d" % i, (w, w, thickness), (0, 0, t), color=accent,
            ))
        return parts
    return decorate


def _zigzag(rows=2):
    def decorate(_base, accent):
        parts = []
        for row in range(rows):
            h = 0.32 + row * 0.3
            radius = math.sin(math.pi * (0.12 + h * 0.82)) * 0.42
            for i in range(8):
                angle = (i / 8) * math.tau
                parts.append(bk.block(
                    "body.zz%d_%d" % (row, i), (0.13, 0.09, 0.1),
                    (math.cos(angle) * radius, math.sin(angle) * radius,
                     h + (0.05 if i % 2 else -0.05)),
                    rot=(0, 0, math.degrees(angle)), color=accent,
                ))
        return parts
    return decorate


def _plates(count=6):
    def decorate(_base, accent):
        parts = []
        for i in range(count):
            angle = (i / count) * math.tau
            h = 0.3 + (i % 3) * 0.2
            radius = math.sin(math.pi * (0.12 + h * 0.82)) * 0.4
            parts.append(bk.block(
                "body.plate%d" % i, (0.2, 0.14, 0.2),
                (math.cos(angle) * radius, math.sin(angle) * radius, h),
                rot=(0, 0, math.degrees(angle)), color=accent,
            ))
        return parts
    return decorate


def _spikes(count=5, length=0.2):
    def decorate(_base, accent):
        parts = []
        for i in range(count):
            angle = (i / count) * math.tau
            h = 0.55 + (i % 2) * 0.16
            radius = math.sin(math.pi * (0.12 + h * 0.82)) * 0.36
            parts.append(bk.wedge(
                "body.spike%d" % i, (0.12, 0.12, length),
                (math.cos(angle) * radius * 1.15, math.sin(angle) * radius * 1.15, h),
                rot=(math.degrees(math.sin(angle)) * 0.4, -50, math.degrees(angle)),
                color=accent, taper=0.85,
            ))
        return parts
    return decorate


def _glowveins(count=4, color="#ff8a1f"):
    def decorate(_base, _accent):
        parts = []
        for i in range(count):
            angle = (i / count) * math.tau
            for j in range(3):
                h = 0.22 + j * 0.26
                radius = math.sin(math.pi * (0.12 + h * 0.82)) * 0.4
                parts.append(bk.glow_block(
                    "body.vein%d_%d" % (i, j), (0.1, 0.1, 0.17),
                    (math.cos(angle) * radius, math.sin(angle) * radius, h),
                    rot=(0, 0, math.degrees(angle)), color=color, strength=2.6,
                ))
        return parts
    return decorate


# --- per-biome eggs ---------------------------------------------------------


def egg_forest():
    return _egg("#fff3d6", "#8fb96a", _speckles(1, None, count=8))


def egg_lake():
    return _egg("#dff4f5", "#3fa8d8", _bands(3, 0.11), tall=1.06, wide=0.96)


def egg_desert():
    return _egg("#f2dfae", "#c47a3c", _zigzag(2), tall=1.02)


def egg_jungle():
    return _egg("#d8e8b4", "#1f8f4a", _plates(7), wide=1.04)


def egg_snow():
    return _egg("#eef7ff", "#7fc4e8", _speckles(5, None, count=6, size=0.13),
                tall=1.04, glow="#a8e8ff")


def egg_volcano():
    return _egg("#3a2a28", "#ff6a1f", _glowveins(4, "#ff8a1f"), tall=1.0)


def egg_abyss():
    return _egg("#14313e", "#1fa8b8", _speckles(9, None, count=9, size=0.1),
                glow="#68e8ff")


def egg_prehistoric():
    return _egg("#c9b184", "#7a5a34", _plates(8), wide=1.08, tall=0.98)


def egg_cosmic():
    return _egg("#2b2450", "#8a6bff", _speckles(13, None, count=10, size=0.09),
                glow="#5ce1ff")


def egg_blossom():
    return _egg("#fff0f5", "#ff9ec4", _bands(2, 0.1), tall=1.05)


def egg_titan():
    return _egg("#4a4238", "#d4a03c", _spikes(6, 0.24), tall=1.02, glow="#ff7a3c")


def egg_event():
    return _egg("#ffe9f7", "#ff8ae0", _zigzag(3), tall=1.03, glow="#ff8ae0")


def egg_cracked():
    """The mid-hatch state: same silhouette with a jagged split near the top."""
    kit.reset_scene()
    root = kit.empty("root")
    parts = _shell("body.shell", "#fff3d6", segments=7)
    for i in range(6):
        angle = (i / 6) * math.tau
        radius = math.sin(math.pi * (0.12 + 0.68 * 0.82)) * 0.42
        parts.append(bk.block(
            "body.crack%d" % i, (0.16, 0.05, 0.12),
            (math.cos(angle) * radius, math.sin(angle) * radius,
             0.68 + (0.05 if i % 2 else -0.04)),
            rot=(0, 0, math.degrees(angle)), color="#2b2118",
        ))
    return _finish(root, {"body": (parts, (0, 0, 0))})


PROPS = {
    "props/egg-forest": egg_forest,
    "props/egg-lake": egg_lake,
    "props/egg-desert": egg_desert,
    "props/egg-jungle": egg_jungle,
    "props/egg-snow": egg_snow,
    "props/egg-volcano": egg_volcano,
    "props/egg-abyss": egg_abyss,
    "props/egg-prehistoric": egg_prehistoric,
    "props/egg-cosmic": egg_cosmic,
    "props/egg-blossom": egg_blossom,
    "props/egg-titan": egg_titan,
    "props/egg-event": egg_event,
    "props/egg-cracked": egg_cracked,
}
