"""
Abyss Ocean -- eight things that live where the light stops.

Palette rules for this biome, applied by every builder below:

  * The base colours are cold: near-black navy, deep teal, storm grey. Nothing
    down here is warm except one swallowed tropical fish.
  * Light is the currency. The rare pet has none; from legendary up the
    creature carries its own bioluminescence -- gill slits, suckers, veins,
    eyes -- because in this biome "expensive" reads as "glowing".
  * Everything is slightly sinister. Mouths a little too wide, eyes a little
    too low, and the big ones built to look heavy.

Anatomy note: these are swimmers. Nothing here except the crab has legs, so the
leg.* slots go unused and the runtime hovers them; fins carry the motion
instead (fin.L / fin.R on the flanks, fin.tail at the back). The kraken spends
its eight arms across every slot it can reach -- fin, arm, ear, tail -- so that
all eight of them actually move.
"""

import math

from mathutils import Vector

import blockkit as bk
import kit


# ---------------------------------------------------------------------------
# Shared palette
# ---------------------------------------------------------------------------

VOID = "#0a1220"        # near-black navy -- this biome's "black"
DEEP = "#123a48"        # deep teal
CYAN = "#5ff2ff"        # bioluminescent cyan
VIOLET = "#a86bff"      # bioluminescent violet


# ---------------------------------------------------------------------------
# Local helpers.
#
# These exist because a fish is not a quadruped: eyes belong on the flanks
# rather than the front face, and limbs are struts between two joints rather
# than boxes hanging straight down. Solving each of those once here keeps eight
# builders from re-deriving the same euler angles and getting them subtly wrong.
# ---------------------------------------------------------------------------


def _neon(color, strength=3.0):
    """Cached emissive material. Strength has to be in the key or the cache lies."""
    return kit.mat(
        "abyss.glow.%s.%d" % (color.strip("#"), int(strength * 10)),
        kit.hexcol(color), rough=0.18, emission=kit.hexcol(color),
        emission_strength=strength,
    )


def _mirror(left, name):
    """The .R twin of a part built on the +X flank."""
    right = kit.duplicate(left, name, mirror=True)
    right.location = Vector((-left.location.x, left.location.y, left.location.z))
    return right


def _spot(name, loc, dims, color, strength=2.4):
    """
    An unbeveled emissive chip -- sucker, freckle, vein, joint light.

    Bevelling these would quadruple their triangle cost for a highlight nobody
    can see at 2cm across, and the whale shark alone wears twenty.
    """
    return bk.block(name, dims, loc, material=_neon(color, strength), bevel=False)


def _strut(name, a, b, thickness, color=None, material=None, taper=0.0,
           width=None):
    """
    A box drawn between two joint positions.

    Everything spindly in the biome -- crab legs, kraken arms, pincers -- is a
    chain of these. `taper` pinches the far end, which is what turns the last
    segment of a leg into a point.
    """
    ax, ay, az = a
    bx, by, bz = b
    dx, dy, dz = bx - ax, by - ay, bz - az
    length = max(math.sqrt(dx * dx + dy * dy + dz * dz), 1e-6)
    # +Z of the box is aimed down the a->b vector: polar angle away from +Z,
    # then azimuth in the ground plane. Blender's XYZ euler composes as Rz @ Ry.
    ry = math.degrees(math.atan2(math.hypot(dx, dy), dz))
    rz = math.degrees(math.atan2(dy, dx))
    obj = bk.block(name, (width or thickness, thickness, length),
                   ((ax + bx) * 0.5, (ay + by) * 0.5, (az + bz) * 0.5),
                   rot=(0, ry, rz), color=color, material=material, segments=1)
    if taper > 0:
        kit.taper(obj, axis="Z", at_min=1.0, at_max=max(0.05, 1.0 - taper))
    return obj


def side_eyes(name, at, dims, size=0.09, along=0.0, up=0.0, ratio=1.0,
              sclera="#f2fbff", iris="#0a0f18", glow=None, glint=True):
    """
    A pair of eyes painted on the LEFT and RIGHT faces of a box.

    bk.eyes() puts both eyes on one face, which is right for a mammal and wrong
    for a fish -- a fish has one eye per flank. `along` runs +Y (forward), `up`
    runs +Z. `glow` swaps the pupil for an emissive one.
    """
    parts = []
    for side, sign in (("L", 1), ("R", -1)):
        face = "left" if sign > 0 else "right"
        plane = bk.face_of(at, dims, face)
        tag = "%s.%s" % (name, side)
        parts.append(bk.face_plate(tag + ".sclera", plane, (size, size * ratio),
                                   face=face, color=sclera, depth=0.02,
                                   offset=(along, up)))
        inner = (size * 0.5, size * ratio * 0.5)
        if glow:
            parts.append(bk.face_plate(tag + ".pupil", plane, inner, face=face,
                                       material=_neon(glow, 3.6), depth=0.02,
                                       offset=(along, up), proud=bk.PROUD * 3.2))
        else:
            parts.append(bk.face_plate(tag + ".pupil", plane, inner, face=face,
                                       color=iris, depth=0.02, offset=(along, up),
                                       proud=bk.PROUD * 3.2))
            if glint:
                parts.append(bk.face_plate(
                    tag + ".glint", plane, (size * 0.2, size * 0.2), face=face,
                    color="#ffffff", depth=0.016,
                    offset=(along + size * 0.22, up + size * 0.24),
                    proud=bk.PROUD * 5,
                ))
    return parts


def gill_slits(name, at, dims, count=5, length=0.16, width=0.022, pitch=0.055,
               back=0.0, color="#08161e", material=None):
    """Vertical slits down both flanks, just behind the skull."""
    parts = []
    for side, sign in (("L", 1), ("R", -1)):
        face = "left" if sign > 0 else "right"
        plane = bk.face_of(at, dims, face)
        for i in range(count):
            t = i - (count - 1) / 2.0
            parts.append(bk.face_plate(
                "%s.%s%d" % (name, side, i), plane, (width, length), face=face,
                color=color, material=material, depth=0.016,
                offset=(back - t * pitch, 0),
            ))
    return parts


def fin_pair(name, at, length=0.3, chord=0.16, thickness=0.04, color=None,
             material=None, sweep=32.0, droop=20.0, tip_color=None):
    """
    Swept pectoral fins. `at` is the shoulder joint on the LEFT flank; the right
    one is mirrored geometry, so the pair is exactly symmetric.

    The hub block is built first and unrotated on purpose: kit.join() adopts the
    first object's transform, and set_origin_to() only lands correctly on an
    unrotated host.
    """
    rs, rd = math.radians(sweep), math.radians(droop)
    cx = at[0] + math.cos(rd) * math.cos(rs) * length * 0.5
    cy = at[1] - math.cos(rd) * math.sin(rs) * length * 0.5
    cz = at[2] - math.sin(rd) * length * 0.5
    parts = [
        bk.block(name + ".hub", (thickness * 1.8, chord * 0.7, thickness * 1.8),
                 at, color=color, material=material),
        bk.block(name + ".blade", (length, chord, thickness), (cx, cy, cz),
                 rot=(0, droop, -sweep), color=tip_color or color,
                 material=material, segments=1),
    ]
    left = kit.join(parts, name + ".L")
    kit.weld(left)
    kit.set_origin_to(left, at)
    return left, _mirror(left, name + ".R")


def caudal(name, at, upper=0.34, lower=0.22, chord=0.2, thickness=0.05,
           color=None, material=None, sweep=30.0, tip_color=None):
    """A vertical fish tail: big upper lobe, smaller lower lobe, both swept back."""
    s = math.radians(sweep)
    parts = [
        bk.block(name + ".hub", (thickness * 1.6, chord * 0.8, chord * 0.5), at,
                 color=color, material=material),
        bk.block(name + ".up", (thickness, chord, upper),
                 (at[0], at[1] - math.sin(s) * upper * 0.5,
                  at[2] + math.cos(s) * upper * 0.5),
                 rot=(sweep, 0, 0), color=tip_color or color, material=material,
                 segments=1),
        bk.block(name + ".dn", (thickness, chord * 0.86, lower),
                 (at[0], at[1] - math.sin(s) * lower * 0.5,
                  at[2] - math.cos(s) * lower * 0.5),
                 rot=(-sweep, 0, 0), color=tip_color or color, material=material,
                 segments=1),
    ]
    merged = kit.join(parts, name)
    kit.weld(merged)
    kit.set_origin_to(merged, at)
    return merged


def fluke(name, at, span=0.5, chord=0.24, thickness=0.055, color=None,
          material=None, lift=9.0, sweep=15.0):
    """
    A horizontal whale fluke. This is the single part that tells a whale from a
    fish in silhouette, so it is wide, notched at the centre, and swept back.
    """
    parts = [bk.block(name + ".hub", (span * 0.2, chord * 0.8, thickness * 1.5),
                      at, color=color, material=material)]
    for side, sign in (("L", 1), ("R", -1)):
        parts.append(bk.block(
            "%s.lobe.%s" % (name, side), (span * 0.46, chord, thickness),
            (at[0] + sign * span * 0.27, at[1] - chord * 0.24, at[2] + 0.012),
            rot=(0, -sign * lift, -sign * sweep), color=color, material=material,
            segments=1,
        ))
    merged = kit.join(parts, name)
    kit.weld(merged)
    kit.set_origin_to(merged, at)
    return merged


def smile(name, at, dims, width=0.16, height=0.028, drop=-0.1, color="#3a2630",
          face="front", curve=0.9):
    """
    An upturned mouth. bk.mouth's "grin" arcs the other way, and the beluga's
    entire personality lives in this one curve.
    """
    plane = bk.face_of(at, dims, face)
    parts = []
    for i in range(5):
        t = (i / 4.0) * 2 - 1
        parts.append(bk.face_plate(
            "%s.%d" % (name, i), plane, (width / 5 * 1.7, height), face=face,
            color=color, depth=0.02,
            offset=(t * width * 0.5, drop + abs(t) * height * curve),
        ))
    return parts


# ---------------------------------------------------------------------------
# Parrotfish -- Rare, $220/s.
# The one bright thing in the biome: a stack of gaudy tropical colour blocks on
# a deep, laterally-flattened disc of a body, with a fused white beak. Kept
# short and tall so it reads as "reef fish" next to seven long torpedoes.
# ---------------------------------------------------------------------------

def build_parrotfish():
    kit.reset_scene()
    root = kit.empty("root")

    teal = "#17b39e"
    green = "#2fd08a"
    magenta = "#c8459f"
    orange = "#ff8f3c"
    yellow = "#ffd85a"
    beakwhite = "#f2f7ee"

    # Narrow in X, deep in Z: a fish you look at side-on.
    body_dims = (0.21, 0.44, 0.46)
    body_at = (0, -0.08, 0.52)
    body = [bk.block("body.core", body_dims, body_at, color=teal)]
    # Gaudy banding, painted as full-width bands rather than decals so the
    # colour survives being seen edge-on.
    body.append(bk.block("body.band.magenta", (0.222, 0.09, 0.44),
                         (0, 0.06, 0.52), color=magenta))
    body.append(bk.block("body.band.orange", (0.222, 0.06, 0.42),
                         (0, -0.08, 0.51), color=orange))
    body.append(bk.block("body.band.green", (0.222, 0.07, 0.40),
                         (0, -0.20, 0.52), color=green))
    body += bk.belly("body.belly", body_at, body_dims, color=yellow, inset=0.5)
    body.append(bk.face_plate("body.underside",
                              bk.face_of(body_at, body_dims, "bottom"),
                              (0.17, 0.36), face="bottom", color=yellow,
                              depth=0.02))

    # Tail stock, so the caudal fin does not sprout straight off the disc.
    body.append(bk.block("body.peduncle", (0.12, 0.14, 0.2),
                         (0, -0.34, 0.53), color=green))

    # Dorsal ridge along the top and a matching anal fin below: the two fins
    # that make a reef fish read as a reef fish.
    # A continuous membrane whose top edge arcs. Five overlapping slabs of
    # different heights: separate spikes read as a stegosaur, and three equal
    # blocks read as castle battlements. Overlap plus variation reads as a fin.
    for i, (y, h) in enumerate(((0.1, 0.11), (0.02, 0.15), (-0.06, 0.17),
                                (-0.14, 0.14), (-0.22, 0.09))):
        body.append(bk.block("body.dorsal%d" % i, (0.058, 0.1, h),
                             (0, y, 0.75 + h * 0.5), color=yellow))
    body.append(bk.wedge("body.anal", (0.055, 0.18, 0.16),
                         (0, -0.2, 0.22), rot=(180, 0, 0), color=orange,
                         taper=0.6))
    body.append(bk.wedge("body.pelvic", (0.055, 0.1, 0.12),
                         (0, 0.0, 0.24), rot=(180, 0, 0), color=orange,
                         taper=0.6))

    head_dims = (0.22, 0.24, 0.38)
    head_at = (0, 0.2, 0.5)
    head = [bk.block("head.skull", head_dims, head_at, color=magenta)]
    head.append(bk.block("head.crown", (0.2, 0.2, 0.1), (0, 0.19, 0.68),
                         color="#8f2f9c"))
    # Gill plate at the seam -- keeps the head from melting into the body.
    for side, sign in (("L", 1), ("R", -1)):
        head.append(bk.face_plate(
            "head.gill.%s" % side,
            bk.face_of(head_at, head_dims, "left" if sign > 0 else "right"),
            (0.05, 0.3), face="left" if sign > 0 else "right",
            color="#7c2183", depth=0.02, offset=(-0.08, -0.02)))
    head += side_eyes("head.eye", head_at, head_dims, size=0.1, along=0.025,
                      up=0.085, sclera="#fff6d8", iris="#161020")
    # The beak: two fused plates with the upper one overhanging, which is the
    # parrotfish's whole gimmick and the reason it is not just a tetra.
    front = head_at[1] + head_dims[1] * 0.5
    head.append(bk.block("head.beak.up", (0.16, 0.12, 0.075),
                         (0, front + 0.05, 0.47), color=beakwhite))
    head.append(bk.block("head.beak.dn", (0.13, 0.09, 0.055),
                         (0, front + 0.035, 0.4), color="#dbe4d4"))
    head.append(bk.block("head.beak.line", (0.165, 0.115, 0.012),
                         (0, front + 0.048, 0.43), color="#5a2b3c"))

    pect_l, pect_r = fin_pair("fin", (0.105, 0.03, 0.48), length=0.19,
                              chord=0.15, thickness=0.038, color=orange,
                              sweep=30, droop=16, tip_color=yellow)
    tail_fin = caudal("fin.tail", (0, -0.42, 0.53), upper=0.24, lower=0.24,
                      chord=0.19, thickness=0.05, color=green, sweep=34,
                      tip_color=teal)

    bk.assemble(root, {
        "body": (body, (0, -0.1, 0.5)),
        "head": (head, (0, 0.06, 0.42)),
        "fin.L": ([pect_l], tuple(pect_l.location)),
        "fin.R": ([pect_r], tuple(pect_r.location)),
        "fin.tail": ([tail_fin], (0, -0.42, 0.53)),
    })
    return bk.finish(root)


# ---------------------------------------------------------------------------
# Swordfish -- Epic, $1.1K/s.
# All the read is in two features: a bill half as long as the fish, and a sail
# dorsal that stands taller than the body is deep. Everything else stays lean.
# ---------------------------------------------------------------------------

def build_swordfish():
    kit.reset_scene()
    root = kit.empty("root")

    blue = "#22509e"
    navy = "#122c5e"
    silver = "#dbe6f4"
    bill = "#9fb2cc"

    body_dims = (0.24, 0.6, 0.32)
    body_at = (0, -0.14, 0.52)
    body = [bk.block("body.core", body_dims, body_at, color=blue)]
    body.append(bk.block("body.back", (0.2, 0.56, 0.1), (0, -0.14, 0.65),
                         color=navy))
    body.append(bk.block("body.rear", (0.15, 0.28, 0.2), (0, -0.55, 0.52),
                         color=blue))
    body.append(bk.block("body.peduncle", (0.09, 0.16, 0.12), (0, -0.74, 0.52),
                         color=navy))
    body.append(bk.face_plate("body.belly",
                              bk.face_of(body_at, body_dims, "bottom"),
                              (0.19, 0.5), face="bottom", color=silver,
                              depth=0.022))
    # Lateral line, lit: the first pet in the rarity ladder to carry any glow.
    for side, sign in (("L", 1), ("R", -1)):
        face = "left" if sign > 0 else "right"
        body.append(bk.face_plate(
            "body.line.%s" % side, bk.face_of(body_at, body_dims, face),
            (0.5, 0.018), face=face, material=_neon(CYAN, 2.2), depth=0.016,
            offset=(0, -0.02)))

    # Sail dorsal: six slabs whose footprints OVERLAP, so the fin reads as one
    # continuous membrane with a stepped top edge rather than a row of spikes.
    # The glow runs up the sail as rays, the way a sailfish's does; putting it
    # along the top edge instead made a dotted arc floating off the fish.
    sail = ((0.17, 0.2), (0.06, 0.3), (-0.05, 0.36), (-0.16, 0.33),
            (-0.27, 0.25), (-0.38, 0.15))
    for i, (y, h) in enumerate(sail):
        body.append(bk.block("body.sail%d" % i, (0.05, 0.13, h),
                             (0, y, 0.66 + h * 0.5), color=navy))
        if i % 2 == 0:
            body.append(_spot("body.sailray%d" % i, (0, y, 0.66 + h * 0.48),
                              (0.056, 0.018, h * 0.8), CYAN, 1.1))
    # Small second dorsal + anal fins near the tail.
    body.append(bk.wedge("body.dorsal2", (0.045, 0.12, 0.11), (0, -0.56, 0.68),
                         color=navy, taper=0.6))
    body.append(bk.wedge("body.anal", (0.045, 0.13, 0.13), (0, -0.5, 0.34),
                         rot=(180, 0, 0), color=navy, taper=0.6))
    body.append(bk.wedge("body.pelvic", (0.05, 0.1, 0.14), (0, 0.02, 0.32),
                         rot=(180, 0, 0), color=navy, taper=0.6))

    head_dims = (0.22, 0.26, 0.3)
    head_at = (0, 0.29, 0.53)
    head = [bk.block("head.skull", head_dims, head_at, color=blue)]
    head.append(bk.block("head.cap", (0.19, 0.24, 0.08), (0, 0.29, 0.66),
                         color=navy))
    head.append(bk.block("head.jaw", (0.13, 0.16, 0.09), (0, 0.44, 0.43),
                         color=silver))
    head += side_eyes("head.eye", head_at, head_dims, size=0.095, along=0.03,
                      up=0.045, sclera="#f4f9ff", iris="#101a2c")
    head += gill_slits("head.gill", head_at, head_dims, count=4, length=0.17,
                       width=0.02, pitch=0.045, back=-0.075, color="#0e2440")
    # The bill. Long, square-sectioned, tapered to a point, with a dark tip.
    fronty = head_at[1] + head_dims[1] * 0.5
    head.append(bk.wedge("head.bill", (0.062, 0.07, 0.5),
                         (0, fronty + 0.25, 0.545), rot=(-90, 0, 0), color=bill,
                         taper=0.72))
    head.append(bk.block("head.billbase", (0.1, 0.09, 0.09),
                         (0, fronty + 0.04, 0.545), color=bill))

    pect_l, pect_r = fin_pair("fin", (0.12, 0.11, 0.46), length=0.34,
                              chord=0.11, thickness=0.035, color=navy,
                              sweep=42, droop=24, tip_color=blue)
    tail_fin = caudal("fin.tail", (0, -0.84, 0.52), upper=0.32, lower=0.28,
                      chord=0.17, thickness=0.05, color=navy, sweep=38,
                      tip_color=blue)

    bk.assemble(root, {
        "body": (body, (0, -0.2, 0.5)),
        "head": (head, (0, 0.12, 0.46)),
        "fin.L": ([pect_l], tuple(pect_l.location)),
        "fin.R": ([pect_r], tuple(pect_r.location)),
        "fin.tail": ([tail_fin], (0, -0.84, 0.52)),
    })
    return bk.finish(root)


# ---------------------------------------------------------------------------
# Shark -- Legendary, $15K/s.
# Deliberately the most conservative design in the module: classic grey over
# white, tall triangular dorsal, overhanging snout with a toothy grin under it.
# The legendary charge is restrained -- lit gill slits and a cyan pupil.
# ---------------------------------------------------------------------------

def build_shark():
    kit.reset_scene()
    root = kit.empty("root")

    grey = "#7f8d9b"
    slate = "#5c6a79"
    white = "#eef4f8"
    gum = "#2b1f28"

    body_dims = (0.32, 0.58, 0.4)
    body_at = (0, -0.06, 0.56)
    body = [bk.block("body.core", body_dims, body_at, color=grey)]
    body.append(bk.block("body.back", (0.28, 0.56, 0.1), (0, -0.06, 0.72),
                         color=slate))
    body.append(bk.block("body.rear", (0.18, 0.32, 0.24), (0, -0.5, 0.56),
                         color=grey))
    body.append(bk.block("body.peduncle", (0.1, 0.18, 0.14), (0, -0.72, 0.56),
                         color=slate))
    # White belly, wrapping a little way up the flanks like the real animal.
    body.append(bk.face_plate("body.belly",
                              bk.face_of(body_at, body_dims, "bottom"),
                              (0.27, 0.52), face="bottom", color=white,
                              depth=0.024))
    for side, sign in (("L", 1), ("R", -1)):
        face = "left" if sign > 0 else "right"
        body.append(bk.face_plate(
            "body.flank.%s" % side, bk.face_of(body_at, body_dims, face),
            (0.5, 0.1), face=face, color=white, depth=0.02, offset=(0, -0.14)))

    # Dorsal: tall, swept back, tapered. The single most recognisable box here.
    body.append(bk.wedge("body.dorsal", (0.07, 0.26, 0.36), (0, 0.02, 0.92),
                         rot=(16, 0, 0), color=slate, taper=0.75))
    body.append(bk.wedge("body.dorsal2", (0.05, 0.12, 0.12), (0, -0.5, 0.74),
                         color=slate, taper=0.6))
    body.append(bk.wedge("body.anal", (0.05, 0.13, 0.13), (0, -0.48, 0.36),
                         rot=(180, 0, 0), color=slate, taper=0.6))
    body.append(bk.wedge("body.pelvic", (0.06, 0.14, 0.15), (0, -0.16, 0.34),
                         rot=(180, 0, 0), color=grey, taper=0.5))

    head_dims = (0.3, 0.3, 0.34)
    head_at = (0, 0.36, 0.56)
    head = [bk.block("head.skull", head_dims, head_at, color=grey)]
    head.append(bk.block("head.crown", (0.27, 0.28, 0.08), (0, 0.36, 0.71),
                         color=slate))
    # Snout overhangs the mouth -- that overhang is what makes it a shark and
    # not a dolphin, so it is a separate tapered block, not a face decal.
    head.append(bk.wedge("head.snout", (0.26, 0.2, 0.3), (0, 0.66, 0.635),
                         rot=(-82, 0, 0), color=grey, taper=0.55))
    head += side_eyes("head.eye", head_at, head_dims, size=0.062, along=0.07,
                      up=0.06, sclera="#0f161e", glow=CYAN)
    head += gill_slits("head.gill", head_at, head_dims, count=5, length=0.17,
                       width=0.02, pitch=0.045, back=-0.075,
                       material=_neon("#3fbfb4", 1.2))
    # The grin: a dark maw across the front face with a row of teeth above it,
    # sitting in the shadow of the snout.
    head += bk.mouth("head.mouth", head_at, head_dims, width=0.24, height=0.035,
                     drop=-0.1, color=gum, style="open", teeth=6,
                     teeth_color="#fbfff4")
    head.append(bk.face_plate("head.chin",
                              bk.face_of(head_at, head_dims, "bottom"),
                              (0.22, 0.24), face="bottom", color=white,
                              depth=0.02))

    pect_l, pect_r = fin_pair("fin", (0.14, 0.1, 0.46), length=0.34,
                              chord=0.17, thickness=0.042, color=grey,
                              sweep=34, droop=28, tip_color=slate)
    tail_fin = caudal("fin.tail", (0, -0.82, 0.56), upper=0.4, lower=0.22,
                      chord=0.19, thickness=0.052, color=slate, sweep=32,
                      tip_color=grey)

    bk.assemble(root, {
        "body": (body, (0, -0.1, 0.54)),
        "head": (head, (0, 0.2, 0.5)),
        "fin.L": ([pect_l], tuple(pect_l.location)),
        "fin.R": ([pect_r], tuple(pect_r.location)),
        "fin.tail": ([tail_fin], (0, -0.82, 0.56)),
    })
    return bk.finish(root)


# ---------------------------------------------------------------------------
# Orca -- Mythic, $80K/s.
# The patches ARE the pet. Everything is either near-black or near-white with a
# hard edge between them: eye patch, saddle, chin, belly. The dorsal is
# deliberately oversized -- it is the tallest thing in the biome.
# ---------------------------------------------------------------------------

def build_orca():
    kit.reset_scene()
    root = kit.empty("root")

    black = "#12161f"
    charcoal = "#1d2430"
    white = "#f5f9fd"
    saddle = "#a9bacb"

    body_dims = (0.42, 0.64, 0.46)
    body_at = (0, -0.08, 0.62)
    body = [bk.block("body.core", body_dims, body_at, color=black)]
    body.append(bk.block("body.rear", (0.24, 0.32, 0.28), (0, -0.54, 0.62),
                         color=black))
    body.append(bk.block("body.peduncle", (0.13, 0.2, 0.17), (0, -0.76, 0.62),
                         color=charcoal))
    # Belly: a genuine white block WIDER than the torso, so it shows as a band
    # up the lower flanks. Made narrower than the body it disappears inside it
    # entirely, which is how the first pass lost half the orca's markings.
    body.append(bk.block("body.belly", (0.44, 0.62, 0.16), (0, -0.1, 0.44),
                         color=white))
    body.append(bk.block("body.vent", (0.26, 0.28, 0.16), (0, -0.52, 0.53),
                         color=white))
    # Saddle patch behind the dorsal -- the third of the three orca marks.
    body.append(bk.face_plate("body.saddle",
                              bk.face_of(body_at, body_dims, "top"),
                              (0.24, 0.2), face="top", color=saddle,
                              depth=0.022, offset=(0, -0.16)))
    # Mythic charge: one violet seam where black meets white. Subtle enough not
    # to fight the two-tone read, bright enough to say "not just a whale".
    for side, sign in (("L", 1), ("R", -1)):
        face = "left" if sign > 0 else "right"
        body.append(bk.face_plate(
            "body.seam.%s" % side, bk.face_of(body_at, body_dims, face),
            (0.58, 0.013), face=face, material=_neon(VIOLET, 2.0), depth=0.016,
            offset=(-0.02, -0.088), proud=bk.PROUD * 4))

    # The dorsal. Tall, straight, barely swept: an adult male's.
    body.append(bk.wedge("body.dorsal", (0.09, 0.24, 0.46), (0, 0.02, 1.06),
                         rot=(9, 0, 0), color=black, taper=0.35))
    body.append(_spot("body.dorsal.edge", (0, -0.09, 1.13), (0.094, 0.02, 0.2),
                      VIOLET, 1.6))

    head_dims = (0.38, 0.3, 0.4)
    head_at = (0, 0.34, 0.6)
    head = [bk.block("head.skull", head_dims, head_at, color=black)]
    head.append(bk.block("head.brow", (0.34, 0.2, 0.1), (0, 0.32, 0.79),
                         color=charcoal))
    head.append(bk.block("head.snout", (0.3, 0.16, 0.26), (0, 0.55, 0.57),
                         color=black))
    head.append(bk.block("head.chin", (0.32, 0.15, 0.11), (0, 0.55, 0.44),
                         color=white))
    head.append(bk.block("head.throat", (0.4, 0.2, 0.11), (0, 0.4, 0.42),
                         color=white))
    for side, sign in (("L", 1), ("R", -1)):
        face = "left" if sign > 0 else "right"
        plane = bk.face_of(head_at, head_dims, face)
        # The eye patch: a big white oval set high and forward. The actual eye
        # is a small dark chip at its lower front corner.
        head.append(bk.face_plate("head.patch.%s" % side, plane, (0.19, 0.095),
                                  face=face, color=white, depth=0.024,
                                  offset=(0.02, 0.095)))
        head.append(bk.face_plate("head.eye.%s" % side, plane, (0.05, 0.05),
                                  face=face, color="#0a0d13", depth=0.02,
                                  offset=(0.09, 0.04), proud=bk.PROUD * 4))
        # Mouth line: a long shallow drop along the jaw.
        head.append(bk.face_plate("head.jaw.%s" % side, plane, (0.26, 0.02),
                                  face=face, color=charcoal, depth=0.018,
                                  offset=(0.0, -0.11)))

    pect_l, pect_r = fin_pair("fin", (0.19, 0.14, 0.53), length=0.34,
                              chord=0.21, thickness=0.05, color=black,
                              sweep=28, droop=32)
    tail_fin = fluke("fin.tail", (0, -0.9, 0.62), span=0.52, chord=0.23,
                     thickness=0.055, color=black)

    bk.assemble(root, {
        "body": (body, (0, -0.12, 0.6)),
        "head": (head, (0, 0.18, 0.54)),
        "fin.L": ([pect_l], tuple(pect_l.location)),
        "fin.R": ([pect_r], tuple(pect_r.location)),
        "fin.tail": ([tail_fin], (0, -0.9, 0.62)),
    })
    return bk.finish(root)


# ---------------------------------------------------------------------------
# Whale Shark -- Cosmic, $700K/s.
# Bulk plus a head wider than the body, plus the checkerboard of spots. At
# cosmic tier the spots stop being paint and start being lights, which is the
# cheapest possible way to make "huge and gentle" also look expensive.
# ---------------------------------------------------------------------------

def build_whale_shark():
    kit.reset_scene()
    root = kit.empty("root")

    hide = "#1a3d50"
    dark = "#102734"
    pale = "#cfdfe4"
    lume = "#8ef6ff"

    body_dims = (0.5, 0.78, 0.48)
    body_at = (0, -0.16, 0.6)
    body = [bk.block("body.core", body_dims, body_at, color=hide)]
    body.append(bk.block("body.back", (0.44, 0.76, 0.1), (0, -0.16, 0.79),
                         color=dark))
    body.append(bk.block("body.rear", (0.26, 0.32, 0.3), (0, -0.68, 0.6),
                         color=hide))
    body.append(bk.block("body.peduncle", (0.13, 0.2, 0.22), (0, -0.9, 0.6),
                         color=dark))
    body.append(bk.block("body.underside", (0.42, 0.72, 0.1), (0, -0.16, 0.4),
                         color=pale))
    # Longitudinal ridges: whale sharks are keeled, and two long thin blocks
    # per flank do more for the silhouette than any amount of surface detail.
    for side, sign in (("L", 1), ("R", -1)):
        for i, z in enumerate((0.72, 0.58)):
            body.append(bk.block("body.ridge.%s%d" % (side, i),
                                 (0.05, 0.72, 0.05),
                                 (sign * 0.23, -0.16, z), color=dark))

    # The spot grid. Rows down the back and both flanks, all emissive.
    for i in range(4):
        y = 0.12 - i * 0.21
        for j, x in enumerate((-0.12, 0.12)):
            body.append(_spot("body.lume.t%d%d" % (i, j), (x, y, 0.845),
                              (0.055, 0.055, 0.022), lume, 2.2))
    for side, sign in (("L", 1), ("R", -1)):
        for i in range(3):
            y = 0.02 - i * 0.24
            for j, z in enumerate((0.71, 0.57)):
                body.append(_spot("body.lume.%s%d%d" % (side, i, j),
                                  (sign * 0.256, y, z), (0.022, 0.055, 0.055),
                                  lume, 2.2))

    body.append(bk.wedge("body.dorsal", (0.08, 0.26, 0.34), (0, -0.28, 0.96),
                         rot=(18, 0, 0), color=dark, taper=0.72))
    body.append(bk.wedge("body.dorsal2", (0.05, 0.13, 0.13), (0, -0.74, 0.76),
                         color=dark, taper=0.6))
    body.append(bk.wedge("body.pelvic", (0.06, 0.16, 0.16), (0, -0.36, 0.34),
                         rot=(180, 0, 0), color=dark, taper=0.5))

    # Head: wider than the torso and flat on top. That step outward is the
    # whale shark's entire profile.
    head_dims = (0.58, 0.28, 0.34)
    head_at = (0, 0.36, 0.57)
    head = [bk.block("head.skull", head_dims, head_at, color=hide)]
    head.append(bk.block("head.crown", (0.54, 0.26, 0.09), (0, 0.36, 0.75),
                         color=dark))
    fronty = head_at[1] + head_dims[1] * 0.5
    # A vast, gentle, slightly dopey mouth: dark gap with a pale lip under it.
    head.append(bk.face_plate("head.maw",
                              bk.face_of(head_at, head_dims, "front"),
                              (0.5, 0.1), face="front", color="#07161d",
                              depth=0.022, offset=(0, -0.03)))
    head.append(bk.block("head.lip", (0.56, 0.09, 0.07), (0, fronty + 0.02, 0.42),
                         color=pale))
    head.append(bk.block("head.jaw", (0.5, 0.14, 0.08), (0, fronty - 0.03, 0.38),
                         color=pale))
    # Eyes right out at the corners of that wide head, and tiny.
    head += side_eyes("head.eye", head_at, head_dims, size=0.055, along=0.07,
                      up=0.01, sclera="#0d1f28", glow=lume)
    # Gills are plain dark cuts. Lit, five slats next to the mouth read as a
    # radiator grille and steal the show from the spots, which are the point.
    head += gill_slits("head.gill", head_at, head_dims, count=5, length=0.19,
                       width=0.02, pitch=0.048, back=-0.06, color="#0a2029")
    for i, x in enumerate((-0.09, 0.09)):
        head.append(_spot("head.lume%d" % i, (x, 0.36, 0.8),
                          (0.05, 0.05, 0.022), lume, 2.2))

    pect_l, pect_r = fin_pair("fin", (0.23, 0.12, 0.5), length=0.42,
                              chord=0.19, thickness=0.045, color=dark,
                              sweep=36, droop=24, tip_color=hide)
    tail_fin = caudal("fin.tail", (0, -1.02, 0.6), upper=0.44, lower=0.24,
                      chord=0.21, thickness=0.055, color=dark, sweep=28,
                      tip_color=hide)
    # A ring of light clasped round the tail stock. Sized to hug the peduncle:
    # any wider and it floats free of the body and reads as a lost hula hoop.
    body += bk.ring("body.band", (0, -0.86, 0.6), radius=0.135, thickness=0.016,
                    tilt=90, color=lume, strength=1.8)

    bk.assemble(root, {
        "body": (body, (0, -0.2, 0.58)),
        "head": (head, (0, 0.2, 0.5)),
        "fin.L": ([pect_l], tuple(pect_l.location)),
        "fin.R": ([pect_r], tuple(pect_r.location)),
        "fin.tail": ([tail_fin], (0, -1.02, 0.6)),
    })
    return bk.finish(root)


# ---------------------------------------------------------------------------
# Beluga Whale -- Cosmic, $850K/s.
# White, no dorsal fin (a ridge instead), a melon you could rest a cup on, and
# the smile. The neck is real: belugas can turn their heads, so the head block
# is set clearly forward of the body with a narrower collar between them.
# ---------------------------------------------------------------------------

def build_beluga_whale():
    kit.reset_scene()
    root = kit.empty("root")

    white = "#f3f7fa"
    shade = "#d3e0e9"
    grey = "#b9cbd8"
    lip = "#c9a8b2"

    # The back line is deliberately LOW. The melon has to clear it by a visible
    # margin or the dome merges into the torso and the whole pet becomes a
    # fridge -- which is exactly what the first pass looked like.
    body_dims = (0.44, 0.5, 0.48)
    body_at = (0, -0.14, 0.56)
    body = [bk.block("body.core", body_dims, body_at, color=white)]
    body.append(bk.block("body.rear", (0.25, 0.26, 0.3), (0, -0.47, 0.56),
                         color=white))
    body.append(bk.block("body.peduncle", (0.14, 0.18, 0.18), (0, -0.65, 0.56),
                         color=shade))
    # Wider than the torso on purpose, so the shaded underside reads as a
    # waterline down the flanks instead of hiding inside the body.
    body.append(bk.block("body.underside", (0.455, 0.48, 0.14), (0, -0.14, 0.39),
                         color=shade))
    # No dorsal fin -- a low knuckled ridge instead. That absence is the pet's
    # most identifiable feature, so the ridge has to be visible enough to read
    # as a deliberate choice rather than a missing part.
    for i in range(4):
        y = -0.04 - i * 0.13
        h = 0.06 - i * 0.008
        body.append(bk.block("body.ridge%d" % i, (0.09, 0.1, h),
                             (0, y, 0.79 + h * 0.5), color=grey))
        body.append(_spot("body.ridge.lume%d" % i, (0, y, 0.79 + h),
                          (0.07, 0.08, 0.016), CYAN, 1.8))
    # Cosmic charge, kept gentle: a soft cyan waterline down each flank.
    for side, sign in (("L", 1), ("R", -1)):
        face = "left" if sign > 0 else "right"
        body.append(bk.face_plate(
            "body.lume.%s" % side, bk.face_of(body_at, body_dims, face),
            (0.46, 0.016), face=face, material=_neon(CYAN, 1.9), depth=0.016,
            offset=(-0.02, -0.16)))

    # Collar: narrower than both the body and the head, which is what makes the
    # head read as a head instead of the front of a tube.
    body.append(bk.block("body.collar", (0.32, 0.1, 0.36), (0, 0.15, 0.57),
                         color=shade))

    head_dims = (0.32, 0.26, 0.3)
    head_at = (0, 0.34, 0.58)
    head = [bk.block("head.skull", head_dims, head_at, color=white)]
    # The melon. Three blocks that shrink in BOTH width and depth as they rise,
    # with the widest one bulging furthest forward: that is what domes it. The
    # first pass stacked equal-width boxes and built a cake with a cabin on top.
    # The snout then tucks in under the overhang and the profile is a beluga.
    for i, (y, z, w, d, h) in enumerate(((0.41, 0.77, 0.36, 0.36, 0.19),
                                         (0.4, 0.91, 0.29, 0.28, 0.11),
                                         (0.39, 0.99, 0.2, 0.19, 0.06))):
        head.append(bk.block("head.melon%d" % i, (w, d, h), (0, y, z),
                             color=white))
    # A shadow-toned soffit under the melon's overhang. White-on-white, the
    # brow and the snout merge into one lump; this one dark sliver separates
    # them and is most of what sells the profile.
    head.append(bk.block("head.melon.soffit", (0.3, 0.11, 0.045),
                         (0, 0.55, 0.655), color=shade))
    snout_dims = (0.2, 0.15, 0.12)
    snout_at = (0, 0.53, 0.5)
    head.append(bk.block("head.snout", snout_dims, snout_at, color=white))
    head += side_eyes("head.eye", head_at, head_dims, size=0.058, along=0.04,
                      up=0.0, sclera="#1b232e", iris="#0a0f16", glint=True)
    # The smile goes on the SNOUT, not the skull: the skull's front face is
    # behind the snout block, so a mouth painted there is never seen.
    head += smile("head.smile", snout_at, snout_dims, width=0.16, height=0.028,
                  drop=-0.02, color="#7c5b66", curve=0.9)
    head.append(bk.block("head.lip", (0.16, 0.1, 0.035), (0, 0.545, 0.435),
                         color=lip))
    head.append(_spot("head.blow", (0, 0.28, 0.905), (0.07, 0.05, 0.02),
                      CYAN, 1.6))
    # Three drifting bubbles, grouped with the head so they bob with it.
    for i, (x, y, z, s) in enumerate(((0.12, 0.62, 0.8, 0.06),
                                      (-0.06, 0.7, 0.9, 0.045),
                                      (0.05, 0.76, 0.97, 0.03))):
        head += bk.gem("head.bubble%d" % i, (x, y, z), size=s, color=CYAN,
                       strength=2.6)

    flip_l, flip_r = fin_pair("fin", (0.2, 0.08, 0.47), length=0.32,
                              chord=0.2, thickness=0.05, color=grey,
                              sweep=24, droop=34, tip_color=shade)
    tail_fin = fluke("fin.tail", (0, -0.78, 0.56), span=0.5, chord=0.23,
                     thickness=0.055, color=white)

    bk.assemble(root, {
        "body": (body, (0, -0.16, 0.55)),
        "head": (head, (0, 0.18, 0.5)),
        "fin.L": ([flip_l], tuple(flip_l.location)),
        "fin.R": ([flip_r], tuple(flip_r.location)),
        "fin.tail": ([tail_fin], (0, -0.78, 0.56)),
    })
    return bk.finish(root)


# ---------------------------------------------------------------------------
# Kraken -- Secret, $15M/s.
# One enormous hooded head and EIGHT arms. Eight is the whole point, so every
# animatable slot the runtime offers gets one: fin.L/R, arm.L/R, ear.L/R, tail
# and fin.tail. The two arm.* slots carry the longer clubbed hunting arms.
# ---------------------------------------------------------------------------

MANTLE = "#2a1a44"
HOOD = "#3b2464"
FLESH = "#155765"
SUCKER = "#7ff6ff"


def _tentacle(name, base, direction, reach=0.42, drop=0.46, curl=0.16,
              thickness=0.12, segments=4, color=MANTLE, tip_color=None,
              club=False):
    """
    One arm: a chain of shrinking struts sweeping out along `direction` (a
    unit-ish (dx, dy) in the ground plane), falling, then curling up at the tip.
    Suckers are lit chips on the underside of each segment.

    The origin is left at `base` so the runtime swings the whole arm from where
    it meets the head.
    """
    dx, dy = direction
    points = [base]
    for i in range(1, segments + 1):
        t = i / float(segments)
        out = t ** 0.78
        # Falls, bottoms out around three-quarters of the way along, then lifts:
        # a straight droop reads as a table leg, and the lift is what says
        # "this thing is swimming".
        points.append((base[0] + dx * reach * out,
                       base[1] + dy * reach * out,
                       base[2] - drop * t + curl * t * t))

    parts = [bk.block(name + ".root", (thickness * 1.1, thickness * 1.1,
                                       thickness * 0.9), base, color=color)]
    for i in range(segments):
        s = thickness * (1.0 - 0.6 * (i / float(segments)))
        last = i == segments - 1
        parts.append(_strut("%s.s%d" % (name, i), points[i], points[i + 1], s,
                            color=(tip_color if last and tip_color else color),
                            taper=0.45 if (last and not club) else 0.0))
        mid = ((points[i][0] + points[i + 1][0]) * 0.5,
               (points[i][1] + points[i + 1][1]) * 0.5,
               (points[i][2] + points[i + 1][2]) * 0.5)
        parts.append(_spot("%s.sk%d" % (name, i), (mid[0], mid[1],
                                                   mid[2] - s * 0.48),
                           (s * 0.3, s * 0.3, s * 0.18), SUCKER, 1.9))
    if club:
        tip = points[-1]
        parts.append(bk.block(name + ".club", (thickness * 0.9, thickness * 1.9,
                                               thickness * 0.5),
                              tip, color=tip_color or color))
        parts.append(_spot(name + ".club.lume", (tip[0], tip[1],
                                                 tip[2] - thickness * 0.28),
                           (thickness * 0.55, thickness * 1.2, thickness * 0.16),
                           SUCKER, 2.2))

    merged = kit.join(parts, name)
    kit.weld(merged)
    kit.set_origin_to(merged, base)
    return merged


def build_kraken():
    kit.reset_scene()
    root = kit.empty("root")

    # Mantle: a long hood swept back over the head. Four shrinking blocks along
    # a leaning axis, ending in a point -- built as a stack rather than one
    # tapered box because a single taper reads as a witch's hat.
    # A wide shoulder block carrying one long tapered cone. Stacking four
    # shrinking boxes instead built a visible staircase -- a pagoda, not a
    # squid -- so the hood above the shoulders is a single continuous taper.
    body = [bk.block("body.mantle.base", (0.48, 0.36, 0.3), (0, -0.16, 0.78),
                     color=MANTLE)]
    body.append(bk.wedge("body.mantle.hood", (0.44, 0.36, 0.54),
                         (0, -0.3, 1.06), rot=(16, 0, 0), color=MANTLE,
                         taper=0.82))
    # Squid fins ride high and tilt UP the cone. Wide and horizontal halfway
    # down, they read as the brim of a wizard's hat instead of swimming fins.
    for side, sign in (("L", 1), ("R", -1)):
        body.append(bk.wedge("body.mfin.%s" % side, (0.22, 0.26, 0.055),
                             (sign * 0.13, -0.37, 1.13),
                             rot=(26, -sign * 42, 0), color=HOOD, taper=0.6))
    # Glowing runes: vertical strips up the flanks of the hood. Run them across
    # it instead and the mantle reads as a striped party hat.
    for side, sign in (("L", 1), ("R", -1)):
        # The x radius has to shrink with the hood's taper, or the top rune
        # floats in mid-air beside the cone.
        for i, (x, y, z, h) in enumerate(((0.2, -0.19, 0.82, 0.2),
                                          (0.135, -0.28, 0.98, 0.15),
                                          (0.072, -0.36, 1.12, 0.1))):
            body.append(_spot("body.rune.%s%d" % (side, i), (sign * x, y, z),
                              (0.02, 0.05, h), VIOLET, 2.6))

    # Head: wider than the mantle base and pushed well forward of it, so the
    # brow ledge and the two lamps sit on their own silhouette.
    head_dims = (0.52, 0.38, 0.34)
    head_at = (0, 0.14, 0.62)
    head = [bk.block("head.skull", head_dims, head_at, color=HOOD)]
    head.append(bk.block("head.brow", (0.56, 0.26, 0.09), (0, 0.12, 0.83),
                         color=MANTLE))
    head.append(bk.block("head.cheek", (0.46, 0.26, 0.14), (0, 0.18, 0.46),
                         color=FLESH))
    for side, sign in (("L", 1), ("R", -1)):
        face = "left" if sign > 0 else "right"
        plane = bk.face_of(head_at, head_dims, face)
        # Socket first, then the lamp, then the slit: three stacked plates so
        # the glow has a dark surround and does not just blow out to white.
        head.append(bk.face_plate("head.socket.%s" % side, plane, (0.25, 0.22),
                                  face=face, color="#150c26", depth=0.024,
                                  offset=(0.04, 0.01)))
        head.append(bk.face_plate("head.eye.%s" % side, plane, (0.2, 0.17),
                                  face=face, material=_neon("#41d6e6", 2.2),
                                  depth=0.022, offset=(0.04, 0.01),
                                  proud=bk.PROUD * 3))
        # Horizontal slit pupil -- cephalopod, and instantly less cuddly.
        head.append(bk.face_plate("head.slit.%s" % side, plane, (0.16, 0.042),
                                  face=face, color="#07101c", depth=0.02,
                                  offset=(0.04, 0.01), proud=bk.PROUD * 5))
    # Beak, tucked in among the arm roots.
    head.append(bk.wedge("head.beak", (0.11, 0.11, 0.15), (0, 0.22, 0.4),
                         rot=(-152, 0, 0), color="#0a0e16", taper=0.72))

    # Eight arms. Direction is (x, y) in the ground plane; the front pair is
    # longest, the arm.* pair carries the clubbed hunting tips, the rear pair
    # trails shortest.
    specs = (
        ("fin.L",    (0.40, 0.92), 0.5, 0.52, 0.145, False),
        ("fin.R",    (-0.40, 0.92), 0.5, 0.52, 0.145, False),
        ("arm.L",    (0.9, 0.44), 0.62, 0.46, 0.135, True),
        ("arm.R",    (-0.9, 0.44), 0.62, 0.46, 0.135, True),
        ("ear.L",    (0.99, -0.16), 0.52, 0.5, 0.13, False),
        ("ear.R",    (-0.99, -0.16), 0.52, 0.5, 0.13, False),
        ("tail",     (0.5, -0.87), 0.44, 0.48, 0.12, False),
        ("fin.tail", (-0.5, -0.87), 0.44, 0.48, 0.12, False),
    )
    arms = {}
    for slot, direction, reach, drop, thick, club in specs:
        base = (direction[0] * 0.2, 0.12 + direction[1] * 0.18, 0.42)
        arms[slot] = (_tentacle("arm." + slot.replace(".", "_"), base, direction,
                                reach=reach, drop=drop, curl=0.34,
                                thickness=thick, segments=5, color=HOOD,
                                tip_color=FLESH, club=club), base)

    groups = {
        "body": (body, (0, -0.16, 0.68)),
        "head": (head, (0, -0.05, 0.56)),
    }
    for slot, (obj, base) in arms.items():
        groups[slot] = ([obj], base)
    bk.assemble(root, groups)
    return bk.finish(root)


# ---------------------------------------------------------------------------
# Abyssal Maja -- Eternal, $130M/s.  ORIGINAL.
# A colossal armoured spider-crab. Eight spindly walking legs whose knees arch
# higher than the shell, two long chelipeds out front, and a carapace lit from
# inside. The knees being the tallest point is the whole silhouette: nothing
# else in the game is a wide, spiky, upside-down bowl on stilts.
#
# Four legs take the animated leg.* slots; the middle and rear pairs are welded
# into the body, which keeps the mesh count sane without losing the eight-leg
# read.
# ---------------------------------------------------------------------------

SHELL = "#141f31"
PLATE = "#1d4a57"
RIM = "#2f7f8c"
CHITIN = "#0d1524"
JOINT = "#28405a"


def _crab_leg(name, hip, knee, toe, thickness=0.055, color=CHITIN,
              joint=JOINT, glow=CYAN):
    """
    One walking leg: a stubby coxa, a femur that rises outward to a knee above
    the shell, then a long tapered tibia stabbing down to the floor.

    The coxa is built first and unrotated so the joined mesh has a clean
    transform for set_origin_to() and for mirroring.
    """
    parts = [bk.block(name + ".coxa",
                      (thickness * 2.2, thickness * 2.0, thickness * 2.0),
                      hip, color=joint)]
    parts.append(_strut(name + ".femur", hip, knee, thickness * 1.2,
                        color=color))
    # An armoured sleeve over the top of the femur. Eight all-black sticks read
    # as a spider; the teal shoulder segment is what makes them crab legs.
    sleeve = (hip[0] + (knee[0] - hip[0]) * 0.5,
              hip[1] + (knee[1] - hip[1]) * 0.5,
              hip[2] + (knee[2] - hip[2]) * 0.5)
    parts.append(_strut(name + ".armour", hip, sleeve, thickness * 1.55,
                        color=PLATE))
    parts.append(_strut(name + ".tibia", knee, toe, thickness * 0.9,
                        color=color, taper=0.62))
    # Knee light. Deliberately small: at 1.5x the leg thickness these read as
    # eight floating ice cubes and the leg arch disappears behind them.
    if glow:
        parts.append(_spot(name + ".knee", knee,
                           (thickness * 0.8, thickness * 0.8, thickness * 0.8),
                           glow, 2.0))
    merged = kit.join(parts, name)
    kit.weld(merged)
    kit.set_origin_to(merged, hip)
    return merged


def _cheliped(name, shoulder, elbow, wrist, thickness=0.06):
    """A claw arm: upper arm, forearm, palm, and two pincer prongs."""
    parts = [bk.block(name + ".shoulder",
                      (thickness * 2.0, thickness * 1.8, thickness * 1.8),
                      shoulder, color=JOINT)]
    parts.append(_strut(name + ".upper", shoulder, elbow, thickness * 1.2,
                        color=CHITIN))
    parts.append(_strut(name + ".fore", elbow, wrist, thickness * 1.05,
                        color=CHITIN))
    # The pincer has to open: two prongs with daylight between them, or the
    # whole arm just reads as another leg.
    palm = (wrist[0], wrist[1] + 0.08, wrist[2] + 0.01)
    parts.append(bk.block(name + ".palm", (0.095, 0.19, 0.12), palm,
                          color=PLATE))
    parts.append(_strut(name + ".prong.up", (palm[0], palm[1] + 0.07, palm[2] + 0.045),
                        (palm[0] + 0.01, palm[1] + 0.26, palm[2] + 0.1),
                        0.042, color=CHITIN, taper=0.6))
    parts.append(_strut(name + ".prong.dn", (palm[0], palm[1] + 0.07, palm[2] - 0.04),
                        (palm[0] + 0.01, palm[1] + 0.25, palm[2] - 0.07),
                        0.038, color=CHITIN, taper=0.6))
    parts.append(_spot(name + ".lume", (palm[0], palm[1] - 0.01, palm[2] + 0.062),
                       (0.05, 0.12, 0.014), VIOLET, 2.2))
    merged = kit.join(parts, name)
    kit.weld(merged)
    kit.set_origin_to(merged, shoulder)
    return merged


def build_abyssal_maja():
    kit.reset_scene()
    root = kit.empty("root")

    # Carapace: a stepped dome, spiked around the rim, veined with violet light.
    # It has to be big -- eight legs will happily eat a small shell alive, and
    # then the pet reads as a spider rather than a crab.
    body = [bk.block("body.carapace", (0.56, 0.54, 0.24), (0, -0.02, 0.7),
                     color=PLATE)]
    body.append(bk.block("body.rim", (0.58, 0.5, 0.06), (0, -0.02, 0.6),
                         color=RIM))
    body.append(bk.block("body.dome", (0.44, 0.44, 0.2), (0, -0.03, 0.88),
                         color=PLATE))
    body.append(bk.block("body.crest", (0.26, 0.3, 0.09), (0, -0.04, 1.0),
                         color=SHELL))
    body.append(bk.block("body.abdomen", (0.34, 0.32, 0.14), (0, -0.06, 0.54),
                         color=CHITIN))
    body.append(bk.block("body.brow", (0.42, 0.14, 0.11), (0, 0.23, 0.72),
                         color=SHELL))
    # Rim spikes. Seven around the shell, longest at the shoulders.
    for i, (x, y, lean, size) in enumerate((
            (0.29, 0.12, 38, 0.16), (-0.29, 0.12, -38, 0.16),
            (0.31, -0.12, 48, 0.18), (-0.31, -0.12, -48, 0.18),
            (0.17, -0.29, 28, 0.14), (-0.17, -0.29, -28, 0.14))):
        body.append(bk.wedge("body.spike%d" % i, (0.06, 0.06, size),
                             (x, y, 0.72), rot=(0, lean, 0), color=CHITIN,
                             taper=0.85))
    body.append(bk.wedge("body.spike.back", (0.065, 0.065, 0.2),
                         (0, -0.3, 0.84), rot=(-40, 0, 0), color=CHITIN,
                         taper=0.85))
    # Bioluminescent veins across the shell, and two gem shards on the crest.
    for i, (x, y, w, d) in enumerate(((0.0, 0.08, 0.032, 0.3),
                                      (0.15, -0.04, 0.032, 0.22),
                                      (-0.15, -0.04, 0.032, 0.22),
                                      (0.0, -0.18, 0.26, 0.032))):
        body.append(_spot("body.vein%d" % i, (x, y, 0.986), (w, d, 0.02),
                          VIOLET, 2.6))
    # Light spilling out from beneath the shell. Free grandeur: it lands on the
    # legs and gives the eternal pet a lit underside nothing else here has.
    body.append(_spot("body.underglow", (0, -0.04, 0.472), (0.36, 0.34, 0.02),
                      VIOLET, 2.0))
    for i, x in enumerate((0.08, -0.08)):
        body += bk.gem("body.shard%d" % i, (x, -0.05, 1.07), size=0.062,
                       color=VIOLET, strength=2.6)

    # Head cluster: rostrum, mandibles and two eyestalks, set proud of the shell
    # at the front so the animator's head-bob has something to move.
    head_dims = (0.28, 0.2, 0.18)
    head_at = (0, 0.34, 0.63)
    head = [bk.block("head.face", head_dims, head_at, color=CHITIN)]
    head.append(bk.wedge("head.rostrum", (0.13, 0.11, 0.22), (0, 0.47, 0.6),
                         rot=(-78, 0, 0), color=PLATE, taper=0.75))
    for side, sign in (("L", 1), ("R", -1)):
        head.append(bk.block("head.mandible.%s" % side, (0.055, 0.11, 0.07),
                             (sign * 0.075, 0.42, 0.55), rot=(0, sign * 16, 0),
                             color=SHELL))
        # Eyestalks: posts that clear the brow, each with a lit bead on top.
        # Below the brow line they simply vanish into the shell.
        head.append(bk.block("head.stalk.%s" % side, (0.05, 0.05, 0.2),
                             (sign * 0.095, 0.3, 0.82), rot=(0, -sign * 11, 0),
                             color=CHITIN))
        head.append(_spot("head.eye.%s" % side, (sign * 0.115, 0.3, 0.935),
                          (0.075, 0.075, 0.075), CYAN, 3.0))
    head.append(_spot("head.maw", (0, 0.44, 0.585), (0.11, 0.02, 0.05),
                      VIOLET, 2.2))

    # Eight legs. Pairs 1 and 3 animate; pairs 2 and 4 are welded into the body
    # so the mesh count stays reasonable.
    leg_spec = (
        ("leg.FL", "leg.FR", (0.26, 0.2, 0.68), (0.46, 0.32, 1.0), (0.6, 0.46, 0.02)),
        (None, None, (0.28, 0.06, 0.66), (0.5, 0.06, 0.97), (0.64, 0.12, 0.02)),
        ("leg.BL", "leg.BR", (0.27, -0.1, 0.66), (0.49, -0.18, 0.93), (0.62, -0.3, 0.02)),
        (None, None, (0.24, -0.24, 0.64), (0.42, -0.36, 0.87), (0.52, -0.58, 0.02)),
    )
    legs = {}
    for i, (ls, rs, hip, knee, toe) in enumerate(leg_spec):
        left = _crab_leg("leg.%d.L" % i, hip, knee, toe, thickness=0.055)
        right = _mirror(left, "leg.%d.R" % i)
        if ls is None:                      # welded into the shell, not animated
            body += [left, right]
        else:
            legs[ls] = (left, hip)
            legs[rs] = (right, (-hip[0], hip[1], hip[2]))

    arm_l = _cheliped("arm.L", (0.26, 0.26, 0.62), (0.46, 0.46, 0.42),
                      (0.36, 0.66, 0.28))
    arm_r = _mirror(arm_l, "arm.R")

    groups = {
        "body": (body, (0, -0.05, 0.62)),
        "head": (head, (0, 0.2, 0.6)),
        "arm.L": ([arm_l], tuple(arm_l.location)),
        "arm.R": ([arm_r], tuple(arm_r.location)),
    }
    for slot, (obj, pivot) in legs.items():
        groups[slot] = ([obj], pivot)
    bk.assemble(root, groups)
    return bk.finish(root)


PETS = {
    "parrotfish": build_parrotfish,
    "swordfish": build_swordfish,
    "shark": build_shark,
    "orca": build_orca,
    "whale-shark": build_whale_shark,
    "beluga-whale": build_beluga_whale,
    "kraken": build_kraken,
    "abyssal-maja": build_abyssal_maja,
}
