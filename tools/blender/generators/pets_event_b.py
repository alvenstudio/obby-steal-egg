"""
Limited / Event pets, part 2 -- the Mecha line.

Ten pets, and the biome's read is MANUFACTURED. Where the forest pets are made
of fur and warm cream, these are brushed metal, dark plating, hazard tape and
one hard light -- cyan for the machines that are merely machines, red for the
ones that are weapons. Three organic pets live here too (the strawberry
elephant, the krakenoid, the dreadscale) and they exist mostly so that their
mecha twins have something to rhyme with: mecha-krakenoid is built on exactly
the krakenoid's proportions, mecha-dreadscale on exactly the dreadscale's.
Standing next to each other they should read as "the same animal, rebuilt".

Conventions are the ones pets_forest.py establishes:

  * Build facing +Y, feet near z = 0, `bk.finish()` normalises the height.
  * Only the runtime's part names go into `assemble`: body, head, ear.L/.R,
    wing.L/.R, arm.L/.R, leg.FL/.FR/.BL/.BR, tail, fin.L/.R, fin.tail.
  * Pivot at the joint, never at the part's centre.

Two deliberate local deviations, both for the same reason:

  1. `kit.set_origin_to` writes a world-space offset straight into local vertex
     coordinates, so any mesh still carrying a non-unit object scale is
     displaced when its origin moves. Every join here goes through `_join`, and
     `_assemble` bakes transforms before grouping, so the numbers written below
     are the numbers that survive to the render.
  2. Blocks default to a one-segment bevel (`_b`). A hard single chamfer is the
     right look for plate armour anyway, and it halves the triangle cost, which
     is what buys the dragons their extra hundred parts.
"""

from __future__ import annotations

import math

from mathutils import Vector

import blockkit as bk
import kit


# ---------------------------------------------------------------------------
# Palette -- one paint shop for ten very different silhouettes.
# ---------------------------------------------------------------------------

HULL      = "#8b95a2"      # the big brushed-metal panels
STEEL     = "#a8b2bd"      # lit metal
STEEL_LT  = "#d6dde5"      # polished chrome, pistons, teeth
STEEL_DK  = "#66707c"      # shadowed metal, joints
PLATE     = "#3a404a"      # dark armour plate
PLATE_MID = "#525a67"      # plate highlight
PLATE_DK  = "#1d2128"      # gaps, rubber, tread
HAZARD    = "#f0b429"      # warning tape
HAZARD_DK = "#8a6512"
CYAN      = "#3fe9ff"      # friendly optic
CYAN_DK   = "#12657a"
REDG      = "#ff3524"      # hostile optic
REDD      = "#7d1408"
COPPER    = "#c9793a"      # cabling, hydraulics
BONE      = "#ded3b0"      # spurs, teeth, claws
VOIDBLK   = "#15141b"      # dreadscale hide
VOIDGREY  = "#282734"
PURPLE    = "#43225f"      # krakenoid flesh
PURPLE_LT = "#7c40a9"
PURPLE_DK = "#20112c"
EYEG      = "#c9ff4a"      # eldritch eye light
BERRY     = "#ee3550"      # strawberry
BERRY_LT  = "#ff738f"
PINK      = "#f9a3b8"      # elephant skin
LEAF      = "#4fae4a"
LEAF_DK   = "#2f7c37"
SEED      = "#ffe27a"
GOLD      = "#e9c14a"


# ---------------------------------------------------------------------------
# Construction helpers
# ---------------------------------------------------------------------------


def _b(name, dims, loc=(0, 0, 0), rot=(0, 0, 0), color=None, material=None, seg=1):
    """A block with a single-segment chamfer -- the module's default brick."""
    return bk.block(name, dims, loc, rot, color, material, bevel=True, segments=seg)


def _emit(color, strength=3.2):
    """Fetch-or-create an emissive material for a hex colour."""
    return kit.mat(
        "eb.emit.%s.%d" % (color.strip("#"), int(strength * 10)),
        kit.hexcol(color), rough=0.16,
        emission=kit.hexcol(color), emission_strength=strength,
    )


def _metal(color, rough=0.42):
    """Slightly glossier than the matte default -- reads as brushed metal."""
    return kit.mat("eb.met.%s" % color.strip("#"), kit.hexcol(color), rough=rough)


def _bake(parts):
    """Flatten rotation + scale into the mesh so origins can be moved exactly."""
    for obj in parts:
        if obj is not None and obj.type == "MESH":
            kit.apply_transforms(obj, rotation=True, scale=True)
    return parts


def _join(name, parts, pivot):
    """Weld a cluster into one animatable mesh whose origin sits at `pivot`."""
    parts = [p for p in parts if p is not None]
    _bake(parts)
    merged = kit.join(parts, name)
    kit.weld(merged)
    kit.set_origin_to(merged, pivot)
    return merged


def _mirror(obj, name):
    """The .R twin of a finished .L cluster."""
    right = kit.duplicate(obj, name, mirror=True)
    right.location = Vector((-obj.location.x, obj.location.y, obj.location.z))
    return right


def _assemble(root, groups):
    """bk.assemble, but every part is baked first so pivots land exactly."""
    prepared = {}
    for name, (parts, pivot) in groups.items():
        clean = [p for p in parts if p is not None]
        _bake(clean)
        prepared[name] = (clean, pivot)
    return bk.assemble(root, prepared)


def _tube(name, pts, sizes, colors, material=None, stretch=1.16):
    """
    A chain of blocks running through a 3D polyline.

    This is the module's most-used tool: tentacles, hydraulic legs, insect
    limbs, dragon necks and armoured tails are all one call to this. Each
    segment is a box whose local +Z is aimed down the segment, so a chain of
    them reads as a jointed limb rather than a smooth noodle.
    """
    parts = []
    for i in range(len(pts) - 1):
        a = Vector(pts[i])
        b = Vector(pts[i + 1])
        d = b - a
        length = max(d.length, 1e-4)
        s = sizes[min(i, len(sizes) - 1)]
        col = colors[i % len(colors)] if isinstance(colors, (list, tuple)) else colors
        obj = _b("%s.%d" % (name, i), (s, s, length * stretch),
                 color=(None if material is not None else col),
                 material=material)
        # `up` must differ from the track axis and must not be parallel to the
        # segment, or the twist of a straight-along-Y run is undefined.
        up = "X" if abs(d.normalized().y) > 0.94 else "Y"
        obj.rotation_euler = d.to_track_quat("Z", up).to_euler()
        obj.location = (a + b) * 0.5
        parts.append(obj)
    return parts


def _taper_block(name, dims, loc, color=None, material=None, bottom=0.5, seg=1):
    """A block pinched at its base -- berries, mantles, cones."""
    obj = _b(name, dims, loc, color=color, material=material, seg=seg)
    kit.taper(obj, axis="Z", at_min=bottom, at_max=1.0)
    return obj


def _hazard_strip(name, at, dims, count=6, axis="x", a=HAZARD, b=PLATE_DK):
    """Alternating warning blocks in a row. Unmistakable even at 24 px."""
    idx = "xyz".index(axis)
    span = dims[idx]
    parts = []
    for i in range(count):
        t = (i + 0.5) / count - 0.5
        loc = list(at)
        loc[idx] = at[idx] + t * span
        d = list(dims)
        d[idx] = span / count * 1.02
        parts.append(_b("%s.%d" % (name, i), tuple(d), tuple(loc),
                        color=(a if i % 2 == 0 else b)))
    return parts


def _optic_bar(name, at, dims, color=REDG, strength=4.0, housing=PLATE_DK):
    """A recessed sensor bar: dark housing with a hot slit inside it."""
    return [
        _b(name + ".housing", (dims[0] * 1.18, dims[1] * 0.7, dims[2] * 1.9),
           at, color=housing),
        _b(name + ".lens", dims, (at[0], at[1] + dims[1] * 0.42, at[2]),
           material=_emit(color, strength)),
    ]


def _lens(name, at, size, color=REDG, strength=4.2, depth=None):
    """One round-ish optic: a dark cup with an emissive pupil proud of it."""
    depth = depth if depth is not None else size * 0.5
    return [
        _b(name + ".cup", (size * 1.3, depth, size * 1.3), at, color=PLATE_DK),
        _b(name + ".eye", (size, depth * 0.7, size),
           (at[0], at[1] + depth * 0.4, at[2]), material=_emit(color, strength)),
    ]


def _piston(name, a, b, r=0.022, color=STEEL_LT):
    """A chrome hydraulic ram between two points."""
    va, vb = Vector(a), Vector(b)
    d = vb - va
    obj = bk.cylinder(name, r=r, h=max(d.length, 1e-3), color=color, verts=8)
    up = "X" if abs(d.normalized().y) > 0.94 else "Y"
    obj.rotation_euler = d.to_track_quat("Z", up).to_euler()
    obj.location = (va + vb) * 0.5
    return obj


def _spur(name, at, size, length, rot, color=BONE, taper=0.86):
    """A tapered bone/blade spur."""
    return bk.wedge(name, (size, size, length), at, rot=rot, color=color, taper=taper)


# Radius and height fractions along a hanging tentacle. The last two entries
# are what matter: the limb reaches its widest at 92% of the way out, then
# comes BACK under itself and lifts. That hook is the entire difference
# between a tentacle and an insect leg, and both krakens live or die on it.
_TENT_R = (0.00, 0.34, 0.70, 1.00, 0.90, 0.64, 0.46)
_TENT_H = (1.00, 0.62, 0.26, 0.04, 0.00, 0.05, 0.26)


def _tentacle_pts(base, direction, reach, floor=0.015):
    """Polyline for one hanging tentacle: out, down, then a J-hook at the tip."""
    dx, dy = direction
    norm = math.hypot(dx, dy) or 1.0
    dx, dy = dx / norm, dy / norm
    x0, y0, z0 = base
    drop = max(z0 - floor, 0.05)
    return [(x0 + dx * reach * r, y0 + dy * reach * r, floor + drop * v)
            for r, v in zip(_TENT_R, _TENT_H)]


def _suckers(name, pts, size=0.03, color="#e8c6ff", inset=0.035):
    """Pale nubs down the inner face of a tentacle."""
    parts = []
    for j, pt in enumerate(pts):
        parts.append(_b("%s.%d" % (name, j), (size, size, size),
                        (pt[0] - inset, pt[1], pt[2] - inset * 0.6),
                        color=color))
    return parts


# ===========================================================================
# Mecha Scorpio -- Event, $45M.
# The line's entry model: a flat hazard-taped carapace, eight spidery struts,
# a hydraulic tail that arcs clean over the back, and one red eye. Everything
# above the ground is silhouette; nothing is detail for detail's sake.
# ===========================================================================

def build_mecha_scorpio():
    kit.reset_scene()
    root = kit.empty("root")

    body_dims = (0.50, 0.58, 0.24)
    body_at = (0, -0.04, 0.34)
    body = [_b("body.carapace", body_dims, body_at, color=PLATE, seg=2)]
    # Brushed deck plates over dark plating -- the biome's core contrast.
    body.append(_b("body.deck", (0.36, 0.48, 0.10), (0, -0.06, 0.46),
                   color=HULL))
    body.append(_b("body.spine", (0.16, 0.52, 0.08), (0, -0.06, 0.53),
                   color=PLATE_MID))
    body += _hazard_strip("body.tape", (0, 0.20, 0.50), (0.42, 0.09, 0.045),
                          count=6, axis="x")
    for side, sign in (("L", 1), ("R", -1)):
        body.append(_b("body.flank.%s" % side, (0.06, 0.48, 0.18),
                       (sign * 0.26, -0.06, 0.34), color=STEEL_DK))
    # Four static struts so the count reads as eight legs, not four.
    for i, (y, z) in enumerate(((0.00, 0.32), (-0.24, 0.32))):
        for side, sign in (("L", 1), ("R", -1)):
            body += _tube("body.strut%d.%s" % (i, side),
                          [(sign * 0.22, y, z), (sign * 0.37, y - 0.02, z + 0.14),
                           (sign * 0.43, y - 0.04, 0.0)],
                          [0.062, 0.048], [STEEL_DK, PLATE_MID])

    head_dims = (0.36, 0.26, 0.24)
    head_at = (0, 0.44, 0.44)
    head = [_b("head.case", head_dims, head_at, color=HULL, seg=2)]
    head.append(_b("head.brow", (0.38, 0.14, 0.07),
                   (0, head_at[1] + 0.02, head_at[2] + 0.15), color=PLATE))
    head += _optic_bar("head.optic", (0, head_at[1] + 0.12, head_at[2] + 0.02),
                       (0.26, 0.05, 0.09), color=REDG, strength=5.2)
    # Mandible pincers under the optic.
    for side, sign in (("L", 1), ("R", -1)):
        head.append(bk.wedge("head.mand.%s" % side, (0.055, 0.055, 0.15),
                             (sign * 0.10, head_at[1] + 0.15, head_at[2] - 0.12),
                             rot=(-80, -sign * 14, 0), color=STEEL_DK, taper=0.8))

    # Claw arms. Deliberately oversized: a scorpion without big pincers is a
    # bug, and at icon size the pincers are half the silhouette.
    arm_pivot = (0.26, 0.22, 0.36)
    parts = _tube("arm.L.strut",
                  [arm_pivot, (0.44, 0.42, 0.42), (0.43, 0.58, 0.44)],
                  [0.095, 0.085], [STEEL_DK, PLATE_MID])
    parts.append(_b("arm.L.wrist", (0.19, 0.16, 0.17), (0.42, 0.66, 0.45),
                    color=HULL))
    # An open pincer. Each shear is a thick straight base with a tapered tip
    # bent onto it, not one long wedge: mass at the hinge and a point at the
    # end is what separates a claw from an arrowhead.
    for tag, z0, ang, zt, col in (("up", 0.55, -125, 0.481, STEEL),
                                  ("lo", 0.37, -55, 0.439, STEEL_DK)):
        parts.append(_b("arm.L.jaw.%s" % tag, (0.12, 0.22, 0.12),
                        (0.42, 0.78, z0), color=col))
        parts.append(bk.wedge("arm.L.jawtip.%s" % tag, (0.10, 0.14, 0.25),
                              (0.42, 0.985, zt), rot=(ang, 0, 0),
                              color=STEEL_LT, taper=0.78))
        # Serrations on the biting face only -- three is plenty at icon size.
        for j in range(3):
            parts.append(_b("arm.L.serr.%s%d" % (tag, j), (0.095, 0.05, 0.035),
                            (0.42, 0.72 + j * 0.07,
                             z0 - 0.072 if tag == "up" else z0 + 0.072),
                            color=PLATE_DK))
    parts.append(_b("arm.L.lamp", (0.05, 0.045, 0.05), (0.42, 0.70, 0.46),
                    material=_emit(HAZARD, 3.2)))
    claw_l = _join("arm.L", parts, arm_pivot)
    claw_r = _mirror(claw_l, "arm.R")

    legs = {}
    for tag, (x, y, z) in (("FL", (0.22, 0.16, 0.32)), ("BL", (0.23, -0.12, 0.32))):
        knee_y = y + (0.03 if tag == "FL" else -0.05)
        parts = _tube("leg.%s.seg" % tag,
                      [(x, y, z), (x + 0.16, knee_y, z + 0.15),
                       (x + 0.22, knee_y + 0.03, 0.018)],
                      [0.068, 0.052], [HULL, PLATE_MID])
        parts.append(_b("leg.%s.knee" % tag, (0.08, 0.07, 0.08),
                        (x + 0.16, knee_y, z + 0.15), color=STEEL_DK))
        parts.append(_b("leg.%s.pad" % tag, (0.09, 0.11, 0.035),
                        (x + 0.22, knee_y + 0.04, 0.018), color=PLATE_DK))
        left = _join("leg.%s" % tag, parts, (x, y, z))
        legs["leg.%s" % tag] = left
        legs["leg.%sR" % tag[0]] = _mirror(left, "leg.%sR" % tag[0])

    # Metasoma: six shrinking segments arcing back, up and forward over the
    # hull. Alternating hull/plate so the joints read as separate segments.
    tail_pts = [(0, -0.36, 0.40), (0, -0.50, 0.58), (0, -0.52, 0.78),
                (0, -0.42, 0.96), (0, -0.24, 1.06), (0, -0.05, 1.06)]
    tail = _tube("tail.seg", tail_pts, [0.16, 0.145, 0.13, 0.115, 0.10],
                 [HULL, PLATE])
    for i, pt in enumerate(tail_pts[1:5]):
        tail.append(_b("tail.ring%d" % i, (0.155 - i * 0.014, 0.05,
                                           0.155 - i * 0.014),
                       pt, color=PLATE_DK))
    # Hydraulics on the underside of the arch.
    tail.append(_piston("tail.ram1", (0, -0.37, 0.36), (0, -0.52, 0.70), r=0.026))
    tail.append(_piston("tail.ram2", (0, -0.50, 0.80), (0, -0.14, 1.02), r=0.024))
    tail.append(_b("tail.bulb", (0.17, 0.19, 0.17), (0, 0.01, 1.04),
                   color=PLATE_MID))
    tail.append(bk.wedge("tail.sting", (0.075, 0.075, 0.24), (0, 0.12, 0.93),
                         rot=(-124, 0, 0), color=STEEL_LT, taper=0.9))
    tail.append(_b("tail.venom", (0.07, 0.07, 0.07), (0, 0.01, 1.14),
                   material=_emit(HAZARD, 3.8)))

    groups = {
        "body": (body, (0, -0.04, 0.26)),
        "head": (head, (0, 0.34, 0.36)),
        "arm.L": ([claw_l], tuple(claw_l.location)),
        "arm.R": ([claw_r], tuple(claw_r.location)),
        "tail": (tail, (0, -0.36, 0.40)),
    }
    for key, obj in legs.items():
        groups[key] = ([obj], tuple(obj.location))
    _assemble(root, groups)
    return bk.finish(root)


# ===========================================================================
# Drilla -- Event, $100M. ORIGINAL.
# A burrowing machine-beast. The read is the snout: a spiral drill nearly as
# long as the hull, on a chassis that runs on two tracks. Everything else --
# exhaust stacks, hazard flanks, stubby digging claws -- exists to say "this
# thing eats ground for a living".
# ===========================================================================

def build_drilla():
    kit.reset_scene()
    root = kit.empty("root")

    # Construction livery. Every other machine in this biome is gunmetal, so
    # painting the digger plant-yellow is what makes it findable on the sheet.
    hull_dims = (0.46, 0.48, 0.38)
    hull_at = (0, -0.08, 0.54)
    body = [_b("body.hull", hull_dims, hull_at, color=HAZARD, seg=2)]
    body.append(_b("body.deck", (0.42, 0.40, 0.08), (0, -0.10, 0.76),
                   color=PLATE))
    body.append(_b("body.belt", (0.48, 0.10, 0.16), (0, -0.30, 0.52),
                   color=PLATE_DK))
    body += _hazard_strip("body.tape", (0, 0.14, 0.60), (0.48, 0.06, 0.10),
                          count=6, axis="x")
    for side, sign in (("L", 1), ("R", -1)):
        body.append(_b("body.rib.%s" % side, (0.05, 0.38, 0.28),
                       (sign * 0.24, -0.12, 0.54), color=PLATE_DK))
        body.append(_b("body.step.%s" % side, (0.09, 0.14, 0.04),
                       (sign * 0.23, 0.06, 0.36), color=STEEL_DK))
    # Twin exhaust stacks: the only tall thing on the machine.
    for side, sign in (("L", 1), ("R", -1)):
        body.append(bk.cylinder("body.stack.%s" % side, r=0.045, h=0.26,
                                loc=(sign * 0.13, -0.24, 0.90), color=STEEL_DK,
                                verts=8))
        body.append(bk.cylinder("body.cap.%s" % side, r=0.055, h=0.05,
                                loc=(sign * 0.13, -0.24, 1.03), color=PLATE_DK,
                                verts=8))
        body.append(_b("body.burn.%s" % side, (0.05, 0.05, 0.03),
                       (sign * 0.13, -0.24, 1.06),
                       material=_emit("#ff8a2a", 3.0)))
    body.append(_b("body.grill", (0.30, 0.05, 0.14), (0, -0.33, 0.58),
                   color=PLATE_DK))
    for i in range(3):
        body.append(_b("body.vent%d" % i, (0.24, 0.03, 0.022),
                       (0, -0.35, 0.52 + i * 0.055),
                       material=_emit("#ff8a2a", 2.2)))

    head_dims = (0.34, 0.22, 0.26)
    head_at = (0, 0.27, 0.68)
    # The cab rides high and back so the drill has the whole front to itself.
    head = [_b("head.cab", head_dims, head_at, color=PLATE, seg=2)]
    head.append(_b("head.roof", (0.36, 0.16, 0.05),
                   (0, head_at[1] - 0.01, head_at[2] + 0.15), color=HAZARD))
    head += _optic_bar("head.visor", (0, head_at[1] + 0.10, head_at[2] + 0.03),
                       (0.24, 0.05, 0.07), color=CYAN, strength=4.4)
    # The drill itself: one clean cone with a hazard-yellow helix wound round
    # it. Stacked twisted boxes read as noise at icon size; a cone plus three
    # spiral tracks reads as a drill from any angle.
    # ENORMOUS is the brief and enormous is the read: the drill is wider than
    # the cab and two thirds as long as the whole chassis. Anything smaller
    # and the pet is just a bulldozer.
    drill_y0, drill_len, drill_r = 0.34, 0.66, 0.225
    drill_z = 0.50
    head.append(bk.cylinder("head.collar", r=0.28, h=0.11,
                            loc=(0, drill_y0, drill_z), rot=(90, 0, 0),
                            color=PLATE_DK, verts=12))
    head += _hazard_strip("head.collartape", (0, drill_y0 + 0.06, drill_z + 0.30),
                          (0.42, 0.06, 0.06), count=6, axis="x")
    head.append(kit.cone("head.drill", r1=drill_r, r2=0.014, h=drill_len,
                         loc=(0, drill_y0 + drill_len * 0.5, drill_z),
                         rot=(-90, 0, 0), material=_metal(STEEL, 0.32),
                         verts=12))
    for f in range(3):
        for i in range(5):
            t = (i + 0.35) / 5.0
            rad = drill_r * (1.0 - t) * 1.03
            ang = math.radians(f * 120 + t * 210)
            head.append(_b("head.helix%d_%d" % (f, i),
                           (0.075, 0.15, 0.075),
                           (math.sin(ang) * rad, drill_y0 + t * drill_len,
                            drill_z + math.cos(ang) * rad),
                           color=(HAZARD if i % 2 == 0 else PLATE_DK)))
    head.append(_b("head.bit", (0.055, 0.13, 0.055), (0, drill_y0 + drill_len,
                                                      drill_z),
                   color=STEEL_LT))

    # Digging claws, short and low so they do not fight the drill.
    parts = _tube("arm.L.seg", [(0.24, 0.04, 0.46), (0.33, 0.20, 0.32),
                                (0.32, 0.30, 0.22)],
                  [0.085, 0.072], [PLATE_DK, PLATE_MID])
    parts.append(_b("arm.L.knuckle", (0.11, 0.09, 0.09), (0.32, 0.32, 0.21),
                    color=HAZARD))
    for j, dx in enumerate((-0.05, 0.0, 0.05)):
        parts.append(bk.wedge("arm.L.claw%d" % j, (0.038, 0.038, 0.12),
                              (0.32 + dx, 0.38, 0.20), rot=(-72, 0, 0),
                              color=STEEL_LT, taper=0.85))
    arm_l = _join("arm.L", parts, (0.24, 0.04, 0.46))
    arm_r = _mirror(arm_l, "arm.R")

    # Tracks. One long roller frame each side, lugged like a real track.
    legs = {}
    track_pivot = (0.26, -0.06, 0.20)
    parts = [_b("leg.FL.frame", (0.15, 0.50, 0.17), track_pivot, color=PLATE_DK)]
    parts.append(_b("leg.FL.plate", (0.06, 0.44, 0.13), (0.34, -0.06, 0.20),
                    color=STEEL_DK))
    for j, y in enumerate((-0.24, -0.06, 0.14)):
        parts.append(bk.cylinder("leg.FL.roller%d" % j, r=0.075, h=0.16,
                                 loc=(0.26, y, 0.19), rot=(0, 90, 0),
                                 color=STEEL, verts=10))
    for j in range(6):
        t = (j + 0.5) / 6.0 - 0.5
        parts.append(_b("leg.FL.lug%d" % j, (0.17, 0.045, 0.035),
                        (0.26, -0.06 + t * 0.50, 0.095), color=PLATE_MID))
    track_l = _join("leg.FL", parts, track_pivot)
    track_r = _mirror(track_l, "leg.FR")
    legs["leg.FL"] = track_l
    legs["leg.FR"] = track_r

    # Counterweight tail with a vent glow, so the back is not a flat wall.
    tail = [_b("tail.block", (0.24, 0.16, 0.20), (0, -0.42, 0.52), color=PLATE_MID)]
    tail.append(_b("tail.hook", (0.10, 0.14, 0.09), (0, -0.52, 0.46),
                   color=STEEL_DK))
    tail.append(_b("tail.lamp", (0.14, 0.03, 0.04), (0, -0.51, 0.58),
                   material=_emit(HAZARD, 2.8)))

    groups = {
        "body": (body, (0, -0.08, 0.30)),
        "head": (head, (0, 0.16, 0.56)),
        "arm.L": ([arm_l], tuple(arm_l.location)),
        "arm.R": ([arm_r], tuple(arm_r.location)),
        "tail": (tail, (0, -0.34, 0.52)),
    }
    for key, obj in legs.items():
        groups[key] = ([obj], tuple(obj.location))
    _assemble(root, groups)
    return bk.finish(root)


# ===========================================================================
# Strawberry Elephant -- Eternal, $110M.
# The one sweet thing in the biome. Its whole body is the berry: a fat,
# seeded, bottom-pinched block under a green calyx, with leaf ears and a
# proper elephant head bolted to the front of it. Eternal rarity buys it gold
# anklets and a handful of seeds that actually glow.
# ===========================================================================

def build_strawberry_elephant():
    kit.reset_scene()
    root = kit.empty("root")

    body_dims = (0.56, 0.52, 0.62)
    body_at = (0, -0.08, 0.52)
    body = [_taper_block("body.berry", body_dims, body_at, color=BERRY,
                         bottom=0.44, seg=2)]
    body.append(_b("body.blush", (0.42, 0.04, 0.38), (0, 0.17, 0.58),
                   color=BERRY_LT))
    body += bk.spots("body.seed", body_at, body_dims, count=14, size=0.046,
                     color=SEED, seed=7, faces=("front", "left", "right", "back"))
    # Three seeds are lit. Cheap, and it is what makes the pet look eternal.
    for i, (dx, dy, dz) in enumerate(((0.23, 0.10, 0.68), (-0.21, 0.02, 0.50),
                                      (0.13, -0.27, 0.62))):
        body.append(_b("body.spark%d" % i, (0.045, 0.045, 0.045), (dx, dy, dz),
                       material=_emit(SEED, 3.4)))
    # Calyx: six flat leaves lying on the crown of the berry, plus a stem.
    for i in range(6):
        ang = i * 60.0
        rad = 0.17
        body.append(_b("body.calyx%d" % i, (0.14, 0.24, 0.05),
                       (math.sin(math.radians(ang)) * rad,
                        -0.08 + math.cos(math.radians(ang)) * rad, 0.845),
                       rot=(0, 0, ang), color=LEAF))
    body.append(_b("body.calyx.hub", (0.17, 0.17, 0.055), (0, -0.08, 0.865),
                   color=LEAF_DK))
    body.append(_b("body.stem", (0.06, 0.06, 0.13), (0, -0.08, 0.95),
                   color=LEAF_DK))

    head_dims = (0.29, 0.25, 0.27)
    head_at = (0, 0.32, 0.58)
    head = [_b("head.skull", head_dims, head_at, color=PINK, seg=2)]
    head.append(_b("head.dome", (0.23, 0.20, 0.08), (0, 0.31, 0.73), color=PINK))
    # Eternal rarity has to read from the face, which is where the eye goes
    # first -- but a flat gold plate on the forehead reads as a sticky
    # note. Eight studs around the crown and one lit stone at the brow.
    for i in range(8):
        ang = i * 45.0
        head.append(_b("head.circlet%d" % i, (0.055, 0.055, 0.06),
                       (math.sin(math.radians(ang)) * 0.115,
                        0.31 + math.cos(math.radians(ang)) * 0.095, 0.77),
                       rot=(0, 0, ang), color=GOLD))
    head.append(_b("head.jewelmount", (0.10, 0.07, 0.10), (0, 0.40, 0.80),
                   color=GOLD))
    head += bk.gem("head.jewel", (0, 0.44, 0.81), size=0.105,
                   color=BERRY, strength=4.4)
    head += bk.eyes("head.eye", head_at, head_dims, spacing=0.58, height=0.04,
                    size=0.058, style="white", iris="#3a2028", pupil_scale=0.55)
    # Trunk: five shrinking segments curling down and out over the berry.
    trunk_pts = [(0, 0.41, 0.52), (0, 0.50, 0.42), (0, 0.53, 0.31),
                 (0, 0.49, 0.21), (0, 0.41, 0.15)]
    head += _tube("head.trunk", trunk_pts, [0.125, 0.11, 0.095, 0.08],
                  [PINK, "#f5b9c8"])
    head.append(_b("head.trunktip", (0.07, 0.07, 0.055), (0, 0.37, 0.14),
                   color="#f5b9c8"))
    for side, sign in (("L", 1), ("R", -1)):
        head.append(bk.wedge("head.tusk.%s" % side, (0.045, 0.045, 0.16),
                             (sign * 0.10, 0.45, 0.45), rot=(-104, 0, -sign * 10),
                             color="#fff6e2", taper=0.85))

    # Leaf ears. Stepped slabs rather than one lozenge, so the outline reads
    # as a leaf instead of a green kite.
    ear_pivot = (0.14, 0.29, 0.62)
    parts = [_b("ear.L.blade", (0.26, 0.05, 0.23), (0.27, 0.25, 0.58),
                rot=(0, -22, -8), color=LEAF)]
    parts.append(_b("ear.L.lobe", (0.18, 0.045, 0.16), (0.34, 0.23, 0.44),
                   rot=(0, -30, -8), color=LEAF))
    parts.append(_b("ear.L.tip", (0.10, 0.04, 0.09), (0.38, 0.21, 0.33),
                   rot=(0, -34, -8), color=LEAF_DK))
    parts.append(_b("ear.L.vein", (0.03, 0.035, 0.32), (0.30, 0.22, 0.49),
                   rot=(0, -26, -8), color=LEAF_DK))
    parts.append(_b("ear.L.stalk", (0.07, 0.06, 0.07), (0.17, 0.28, 0.62),
                   color=LEAF_DK))
    ear_l = _join("ear.L", parts, ear_pivot)
    ear_r = _mirror(ear_l, "ear.R")

    legs = {}
    for tag, (x, y) in (("FL", (0.18, 0.10)), ("BL", (0.19, -0.24))):
        parts = [_b("leg.%s.shaft" % tag, (0.15, 0.15, 0.24), (x, y, 0.14),
                    color=PINK)]
        parts.append(_b("leg.%s.foot" % tag, (0.17, 0.18, 0.07), (x, y + 0.01, 0.035),
                        color="#f5b9c8"))
        parts.append(_b("leg.%s.cuff" % tag, (0.16, 0.16, 0.03), (x, y, 0.085),
                        color="#e6c9d2"))
        left = _join("leg.%s" % tag, parts, (x, y, 0.26))
        legs["leg.%s" % tag] = left
        legs["leg.%sR" % tag[0]] = _mirror(left, "leg.%sR" % tag[0])

    tail = [_b("tail.rope", (0.045, 0.20, 0.045), (0, -0.38, 0.44),
               rot=(24, 0, 0), color=PINK)]
    tail.append(_b("tail.tuft", (0.08, 0.08, 0.09), (0, -0.46, 0.36), color=LEAF))

    groups = {
        "body": (body, (0, -0.08, 0.24)),
        "head": (head, (0, 0.21, 0.48)),
        "ear.L": ([ear_l], tuple(ear_l.location)),
        "ear.R": ([ear_r], tuple(ear_r.location)),
        "tail": (tail, (0, -0.30, 0.46)),
    }
    for key, obj in legs.items():
        groups[key] = ([obj], tuple(obj.location))
    _assemble(root, groups)
    return bk.finish(root)


# ===========================================================================
# Mecha Froggo -- Event, $155M.
# A frog rebuilt as a hopping drone. Wide, low, coiled: the hind legs fold up
# behind the shoulders on visible rams, and the whole face is one cyan visor
# band with two turret eyes sitting on top of the skull the way a frog's do.
# ===========================================================================

def build_mecha_froggo():
    kit.reset_scene()
    root = kit.empty("root")

    # Low, wide and short: a frog's mass sits between its shoulders and its
    # folded haunches, so the torso is barely longer than it is wide.
    body_dims = (0.56, 0.44, 0.28)
    body_at = (0, -0.04, 0.34)
    body = [_b("body.shell", body_dims, body_at, color=HULL, seg=2)]
    # A stepped dome instead of one flat lid: a frog's back is a curve, and a
    # single slab up there was the thing making this read as a crouching dog.
    body.append(_b("body.back", (0.46, 0.38, 0.09), (0, -0.06, 0.50),
                   color=PLATE))
    body.append(_b("body.dome", (0.32, 0.28, 0.08), (0, -0.04, 0.57),
                   color=PLATE_MID))
    for side, sign in (("L", 1), ("R", -1)):
        body.append(_b("body.gill.%s" % side, (0.045, 0.20, 0.035),
                       (sign * 0.28, -0.02, 0.36), material=_emit(CYAN, 3.0)))
    body += bk.belly("body.plate", body_at, body_dims, color=STEEL_LT, inset=0.7)
    # Reactor core in the chest -- the frog's lit throat sac.
    body.append(_b("body.corering", (0.22, 0.05, 0.19), (0, 0.16, 0.33),
                   color=PLATE_DK))
    body.append(_b("body.core", (0.15, 0.04, 0.12), (0, 0.18, 0.33),
                  material=_emit(CYAN, 4.6)))
    body += _hazard_strip("body.tape", (0, -0.20, 0.585), (0.32, 0.07, 0.035),
                          count=6, axis="x")

    head_dims = (0.38, 0.24, 0.19)
    head_at = (0, 0.34, 0.56)
    head = [_b("head.case", head_dims, head_at, color=PLATE, seg=2)]
    head.append(_b("head.jaw", (0.36, 0.22, 0.06),
                   (0, head_at[1] + 0.01, head_at[2] - 0.12), color=PLATE_MID))
    head += _optic_bar("head.visor", (0, head_at[1] + 0.11, head_at[2] + 0.01),
                       (0.29, 0.05, 0.06), color=CYAN, strength=4.6)
    head.append(_b("head.grin", (0.28, 0.03, 0.025),
                   (0, head_at[1] + 0.13, head_at[2] - 0.11), color=PLATE_DK))
    # Turret eyes. A frog's eyes stand off the skull; these are stalked
    # housings with the lens facing forward-up, and they carry the read.
    for side, sign in (("L", 1), ("R", -1)):
        head.append(_b("head.stalk.%s" % side, (0.075, 0.075, 0.07),
                       (sign * 0.17, head_at[1] - 0.02, head_at[2] + 0.12),
                       color=STEEL_DK))
        head.append(_b("head.turret.%s" % side, (0.17, 0.17, 0.16),
                       (sign * 0.17, head_at[1] - 0.01, head_at[2] + 0.23),
                       color=HULL))
        head += _lens("head.tlens.%s" % side,
                      (sign * 0.17, head_at[1] + 0.075, head_at[2] + 0.24),
                      0.098, color=CYAN, strength=4.8, depth=0.06)
        head.append(_b("head.cap.%s" % side, (0.18, 0.18, 0.034),
                       (sign * 0.17, head_at[1] - 0.01, head_at[2] + 0.32),
                       color=PLATE_DK))

    # Hind legs. The knee has to stand clearly ABOVE the back or the pose
    # reads as a dog: hip low, knee up behind the shoulder, ankle down front.
    legs = {}
    # The knee has to stand clearly OUTSIDE and ABOVE the back, or the pose
    # is a dog's. Hip low and inboard, knee high and wide, ankle forward.
    hip = (0.24, -0.10, 0.34)
    parts = _tube("leg.BL.seg", [hip, (0.38, -0.32, 0.66), (0.31, -0.06, 0.13)],
                  [0.15, 0.11], [HULL, PLATE])
    parts.append(_b("leg.BL.knee", (0.18, 0.17, 0.17), (0.38, -0.32, 0.66),
                    color=PLATE_MID))
    parts.append(_b("leg.BL.cap", (0.19, 0.10, 0.05), (0.38, -0.32, 0.76),
                    color=HAZARD))
    parts.append(_piston("leg.BL.ram", (0.24, -0.18, 0.42), (0.31, -0.10, 0.18),
                         r=0.028))
    # Webbed foot: a wide splayed plate with three toes standing proud of it.
    parts.append(_b("leg.BL.foot", (0.22, 0.30, 0.055), (0.31, 0.08, 0.032),
                    color=PLATE))
    for j, dx in enumerate((-0.075, 0.0, 0.075)):
        parts.append(_b("leg.BL.toe%d" % j, (0.05, 0.16, 0.05),
                        (0.31 + dx, 0.24, 0.034), color=STEEL_DK))
        parts.append(_b("leg.BL.web%d" % j, (0.05, 0.05, 0.03),
                        (0.31 + dx, 0.33, 0.030), color=CYAN_DK))
    leg_bl = _join("leg.BL", parts, hip)
    legs["leg.BL"] = leg_bl
    legs["leg.BR"] = _mirror(leg_bl, "leg.BR")

    # Front arms: short, straight, three-toed, planted well forward.
    shoulder = (0.21, 0.10, 0.36)
    parts = _tube("arm.L.seg", [shoulder, (0.24, 0.20, 0.19), (0.23, 0.24, 0.05)],
                  [0.085, 0.068], [HULL, PLATE])
    for j, dx in enumerate((-0.045, 0.0, 0.045)):
        parts.append(_b("arm.L.toe%d" % j, (0.033, 0.11, 0.04),
                        (0.23 + dx, 0.32, 0.032), color=STEEL_DK))
    arm_l = _join("arm.L", parts, shoulder)
    arm_r = _mirror(arm_l, "arm.R")

    groups = {
        "body": (body, (0, -0.04, 0.22)),
        "head": (head, (0, 0.23, 0.48)),
        "arm.L": ([arm_l], tuple(arm_l.location)),
        "arm.R": ([arm_r], tuple(arm_r.location)),
    }
    for key, obj in legs.items():
        groups[key] = ([obj], tuple(obj.location))
    _assemble(root, groups)
    return bk.finish(root)


# ===========================================================================
# Mecha Crawler -- Event, $320M.
# A segmented multi-leg hunter. The body is a train of shrinking armour rings
# with a red scanner bar for a face, and the front third rears up so the
# silhouette is not a flat log.
# ===========================================================================

def build_mecha_crawler():
    kit.reset_scene()
    root = kit.empty("root")

    # Six shrinking rings from the raised shoulder back to the thruster.
    seg_spec = (
        (0.10, 0.44, 0.46, 0.36),
        (-0.08, 0.43, 0.44, 0.35),
        (-0.26, 0.39, 0.39, 0.31),
        (-0.43, 0.33, 0.33, 0.26),
    )
    body = []
    for i, (y, z, w, h) in enumerate(seg_spec):
        body.append(_b("body.seg%d" % i, (w, 0.17, h), (0, y, z),
                       color=(HULL if i % 2 == 0 else PLATE_MID),
                       seg=(2 if i == 0 else 1)))
        body.append(_b("body.ring%d" % i, (w * 0.9, 0.06, h * 1.05),
                       (0, y + 0.09, z), color=PLATE_DK))
        body.append(bk.wedge("body.dorsal%d" % i, (w * 0.34, 0.13, 0.17),
                             (0, y, z + h * 0.5 + 0.07),
                             color=(STEEL_LT if i % 2 == 0 else HAZARD),
                             taper=0.55))
        # A lit slot down each flank. Segmentation you cannot see is not
        # segmentation, and grey-on-grey plate joins vanish at icon size.
        for side, sign in (("L", 1), ("R", -1)):
            body.append(_b("body.slot%d.%s" % (i, side), (0.035, 0.11, 0.04),
                           (sign * w * 0.5, y, z - h * 0.20),
                           material=_emit(CYAN, 3.4)))
            body.append(_b("body.cheekplate%d.%s" % (i, side),
                           (0.04, 0.14, h * 0.5),
                           (sign * w * 0.5, y, z + h * 0.12),
                           color=PLATE_DK))
    body += _hazard_strip("body.tape", (0, 0.10, 0.28), (0.46, 0.05, 0.05),
                          count=6, axis="x")
    # Four static legs so the count reads as "many".
    for i, y in enumerate((-0.06, -0.34)):
        for side, sign in (("L", 1), ("R", -1)):
            body += _tube("body.strut%d.%s" % (i, side),
                          [(sign * 0.19, y, 0.38), (sign * 0.33, y, 0.46),
                           (sign * 0.38, y - 0.02, 0.0)],
                          [0.06, 0.046], [STEEL_DK, PLATE])

    head_dims = (0.34, 0.28, 0.24)
    head_at = (0, 0.37, 0.56)
    head = [_b("head.case", head_dims, head_at, color=HULL, seg=2)]
    head.append(_b("head.crown", (0.30, 0.18, 0.07),
                   (0, head_at[1] - 0.02, head_at[2] + 0.14), color=PLATE))
    # The scanner: one wide red slit with a brighter tracking pip inside it.
    head += _optic_bar("head.scan", (0, head_at[1] + 0.13, head_at[2] + 0.02),
                       (0.28, 0.05, 0.06), color=REDG, strength=4.8)
    head.append(_b("head.pip", (0.04, 0.03, 0.04), (0.07, head_at[1] + 0.17,
                                                    head_at[2] + 0.02),
                   material=_emit("#fff0a0", 5.4)))
    for side, sign in (("L", 1), ("R", -1)):
        head.append(bk.wedge("head.mand.%s" % side, (0.07, 0.07, 0.24),
                             (sign * 0.12, head_at[1] + 0.22, head_at[2] - 0.11),
                             rot=(-84, -sign * 26, 0), color=STEEL_LT, taper=0.82))
        head.append(_b("head.cheek.%s" % side, (0.055, 0.18, 0.15),
                       (sign * 0.17, head_at[1] + 0.02, head_at[2] - 0.02),
                       color=PLATE_DK))

    # Antennae in the ear slots so they sway when it moves.
    ant_pivot = (0.09, 0.31, 0.67)
    parts = _tube("ear.L.rod", [ant_pivot, (0.19, 0.35, 0.82), (0.24, 0.31, 0.92)],
                  [0.026, 0.02], [STEEL_DK, STEEL])
    parts.append(_b("ear.L.tip", (0.038, 0.038, 0.038), (0.25, 0.30, 0.94),
                    material=_emit(REDG, 3.8)))
    ear_l = _join("ear.L", parts, ant_pivot)
    ear_r = _mirror(ear_l, "ear.R")

    legs = {}
    for tag, y in (("FL", 0.08), ("BL", -0.24)):
        z = 0.43 if tag == "FL" else 0.37
        parts = _tube("leg.%s.seg" % tag,
                      [(0.19, y, z), (0.34, y + 0.02, z + 0.12),
                       (0.40, y + 0.04, 0.015)],
                      [0.06, 0.046], [STEEL_DK, PLATE])
        parts.append(_b("leg.%s.pad" % tag, (0.08, 0.10, 0.032),
                        (0.40, y + 0.05, 0.015), color=PLATE_DK))
        left = _join("leg.%s" % tag, parts, (0.19, y, z))
        legs["leg.%s" % tag] = left
        legs["leg.%sR" % tag[0]] = _mirror(left, "leg.%sR" % tag[0])

    tail_pts = [(0, -0.51, 0.31), (0, -0.63, 0.27), (0, -0.73, 0.22)]
    tail = _tube("tail.seg", tail_pts, [0.28, 0.22], [PLATE_MID, HULL])
    tail.append(bk.cylinder("tail.nozzle", r=0.11, h=0.08, loc=(0, -0.80, 0.20),
                            rot=(90, 0, 0), color=PLATE_DK, verts=10))
    tail.append(_b("tail.burn", (0.13, 0.05, 0.13), (0, -0.86, 0.20),
                   material=_emit(CYAN, 4.4)))
    tail.append(_b("tail.trail", (0.08, 0.10, 0.08), (0, -0.93, 0.20),
                   material=_emit("#a9f6ff", 2.2)))

    groups = {
        "body": (body, (0, -0.12, 0.26)),
        "head": (head, (0, 0.24, 0.48)),
        "ear.L": ([ear_l], tuple(ear_l.location)),
        "ear.R": ([ear_r], tuple(ear_r.location)),
        "tail": (tail, (0, -0.47, 0.32)),
    }
    for key, obj in legs.items():
        groups[key] = ([obj], tuple(obj.location))
    _assemble(root, groups)
    return bk.finish(root)


# ===========================================================================
# Krakenoid -- Event, $500M.
# The organic half of the kraken pair. A tall pinched mantle leaning back over
# a low brow full of mismatched eyes, and eight tentacles that all leave the
# body at different angles so nothing about it looks manufactured.
# ===========================================================================

# Where the eldritch eyes sit on the brow: (x, z-offset, size).
_KRAKEN_EYES = (
    (-0.02, 0.075, 0.115),
    (0.150, 0.015, 0.080),
    (-0.145, 0.045, 0.062),
    (0.070, -0.070, 0.052),
    (-0.055, -0.090, 0.044),
    (0.180, -0.080, 0.036),
    (-0.175, -0.045, 0.040),
)


def build_krakenoid():
    kit.reset_scene()
    root = kit.empty("root")

    # Mantle: pinched at the base, leaning back over the brow.
    mantle_at = (0, -0.22, 0.70)
    body = [_taper_block("body.mantle", (0.44, 0.40, 0.62), mantle_at,
                         color=PURPLE, bottom=0.58, seg=2)]
    body[0].rotation_euler = (math.radians(-13), 0, 0)
    # The hood comes to a point. A flat-topped mantle is a rucksack.
    body.append(bk.wedge("body.crown", (0.30, 0.28, 0.24), (0, -0.31, 1.06),
                         color=PURPLE_LT, taper=0.55))
    body.append(bk.wedge("body.spike", (0.12, 0.12, 0.15), (0, -0.33, 1.24),
                         color=PURPLE_DK, taper=0.85))
    for side, sign in (("L", 1), ("R", -1)):
        body.append(bk.wedge("body.fin.%s" % side, (0.05, 0.26, 0.30),
                             (sign * 0.23, -0.26, 0.90), rot=(0, sign * 34, 0),
                             color=PURPLE_LT, taper=0.6))
    body += bk.spots("body.pore", mantle_at, (0.44, 0.40, 0.54), count=8,
                     size=0.05, color=PURPLE_DK, seed=13,
                     faces=("left", "right", "back"))
    body.append(_b("body.gill", (0.30, 0.05, 0.06), (0, -0.02, 0.52),
                   color=PURPLE_DK))
    # Two extra tentacles trailing behind, welded into the body, so the
    # creature reads as eight-limbed from every angle rather than four.
    for side, sign in (("L", 1), ("R", -1)):
        pts = _tentacle_pts((sign * 0.16, -0.14, 0.44), (sign * 0.72, -0.70),
                            0.56)
        body += _tube("body.tent.%s" % side, pts,
                      [0.085, 0.070, 0.056, 0.042, 0.031, 0.022],
                      [PURPLE, PURPLE_DK])

    head_dims = (0.42, 0.30, 0.32)
    head_at = (0, 0.16, 0.56)
    head = [_b("head.brow", head_dims, head_at, color=PURPLE_LT, seg=2)]
    head.append(_b("head.ridge", (0.44, 0.22, 0.08), (0, 0.14, 0.73),
                   color=PURPLE))
    face_y = head_at[1] + head_dims[1] * 0.5
    for i, (dx, dz, size) in enumerate(_KRAKEN_EYES):
        head.append(_b("head.socket%d" % i, (size * 1.5, 0.04, size * 1.5),
                       (dx, face_y, head_at[2] + dz), color=PURPLE_DK))
        head.append(_b("head.eye%d" % i, (size, 0.035, size),
                       (dx, face_y + 0.03, head_at[2] + dz),
                       material=_emit(EYEG, 3.8)))
        head.append(_b("head.slit%d" % i, (size * 0.22, 0.03, size * 0.8),
                       (dx, face_y + 0.05, head_at[2] + dz), color=PURPLE_DK))
    # Beak, under the eye mass.
    head.append(bk.wedge("head.beak.up", (0.13, 0.11, 0.14), (0, 0.30, 0.38),
                         rot=(-118, 0, 0), color="#1b1220", taper=0.7))
    head.append(bk.wedge("head.beak.lo", (0.11, 0.09, 0.11), (0, 0.28, 0.30),
                         rot=(-64, 0, 0), color="#2c1d33", taper=0.7))

    # The two striking arms REAR, they do not hang: up out of the shoulder,
    # forward over the beak, then hooking down and back in. Two raised limbs
    # above the eye-line are what stop the silhouette reading as a spider.
    arm_pivot = (0.17, 0.24, 0.56)
    arm_pts = [arm_pivot, (0.31, 0.44, 0.74), (0.39, 0.64, 0.80),
               (0.41, 0.80, 0.71), (0.35, 0.88, 0.55), (0.25, 0.85, 0.45)]
    parts = _tube("arm.L.seg", arm_pts, [0.105, 0.088, 0.072, 0.056, 0.042],
                  [PURPLE_LT, PURPLE])
    parts += _suckers("arm.L.sucker", arm_pts[1:5], size=0.032)
    arm_l = _join("arm.L", parts, arm_pivot)
    arm_r = _mirror(arm_l, "arm.R")

    legs = {}
    # Four hanging tentacles on splayed headings, each with the J-hook tip.
    leg_spec = {
        "FL": ((0.11, 0.26, 0.46), (0.72, 0.85), 0.64),
        "BL": ((0.16, 0.12, 0.46), (1.00, 0.05), 0.58),
    }
    for tag, (base, heading, reach) in leg_spec.items():
        pts = _tentacle_pts(base, heading, reach)
        parts = _tube("leg.%s.seg" % tag, pts,
                      [0.110, 0.092, 0.072, 0.052, 0.038, 0.027],
                      [PURPLE_LT, PURPLE])
        parts += _suckers("leg.%s.sucker" % tag, pts[1:4], size=0.026,
                          inset=0.03)
        left = _join("leg.%s" % tag, parts, base)
        legs["leg.%s" % tag] = left
        legs["leg.%sR" % tag[0]] = _mirror(left, "leg.%sR" % tag[0])

    groups = {
        "body": (body, (0, -0.14, 0.30)),
        "head": (head, (0, 0.04, 0.44)),
        "arm.L": ([arm_l], tuple(arm_l.location)),
        "arm.R": ([arm_r], tuple(arm_r.location)),
    }
    for key, obj in legs.items():
        groups[key] = ([obj], tuple(obj.location))
    _assemble(root, groups)
    return bk.finish(root)


# ===========================================================================
# Mecha Crocodon -- Event, $680M.
# Armoured crocodile. Long plated hull, a dorsal ridge of blade fins, twin
# shoulder cannons, and a jaw that hangs open on two visible chrome rams.
# ===========================================================================

def build_mecha_crocodon():
    kit.reset_scene()
    root = kit.empty("root")

    body_dims = (0.44, 0.52, 0.26)
    body_at = (0, -0.12, 0.36)
    body = [_b("body.hull", body_dims, body_at, color=PLATE_MID, seg=2)]
    body.append(_b("body.back", (0.34, 0.46, 0.09), (0, -0.12, 0.50),
                   color=HULL))
    body += bk.belly("body.plate", body_at, body_dims, color=STEEL_DK, inset=0.7)
    # Dorsal blade fins, shrinking toward the tail. Tall enough to be the
    # crocodile's silhouette from the side.
    for i in range(5):
        t = i / 4.0
        body.append(bk.wedge("body.fin%d" % i, (0.06, 0.10, 0.20 - 0.06 * t),
                             (0, 0.05 - i * 0.11, 0.58 - 0.01 * i),
                             color=STEEL, taper=0.6))
    for side, sign in (("L", 1), ("R", -1)):
        body.append(_b("body.skirt.%s" % side, (0.06, 0.46, 0.14),
                       (sign * 0.23, -0.12, 0.32), color=HULL))
        body.append(_b("body.vent.%s" % side, (0.035, 0.24, 0.035),
                       (sign * 0.26, -0.12, 0.34), material=_emit(REDD, 2.6)))
    body += _hazard_strip("body.tape", (0, -0.34, 0.55), (0.30, 0.07, 0.035),
                          count=6, axis="x")
    # Shoulder cannons, mounted high so the machine outranks its own jaws.
    for side, sign in (("L", 1), ("R", -1)):
        body.append(_b("body.cannon.%s" % side, (0.15, 0.20, 0.16),
                       (sign * 0.20, 0.02, 0.64), color=PLATE_MID))
        body += _hazard_strip("body.gtape.%s" % side, (sign * 0.20, 0.02, 0.725),
                              (0.14, 0.18, 0.03), count=4, axis="y")
        for j, dx in enumerate((-0.038, 0.038)):
            body.append(bk.cylinder("body.barrel.%s%d" % (side, j), r=0.028,
                                    h=0.22, loc=(sign * 0.20 + dx, 0.20, 0.64),
                                    rot=(90, 0, 0), color=STEEL_DK, verts=8))
            body.append(_b("body.muzzle.%s%d" % (side, j), (0.038, 0.03, 0.038),
                           (sign * 0.20 + dx, 0.32, 0.64),
                           material=_emit(REDG, 3.4)))

    # The head is one long flat wedge held well clear of the chest. A croc
    # that shares a column with its shoulders just reads as a dog.
    head_dims = (0.28, 0.22, 0.20)
    head_at = (0, 0.38, 0.44)
    head = [_b("head.skull", head_dims, head_at, color=HULL, seg=2)]
    head.append(_b("head.upper", (0.24, 0.30, 0.09), (0, 0.63, 0.44),
                   color=PLATE_MID))
    head += _hazard_strip("head.tape", (0, 0.63, 0.495), (0.22, 0.28, 0.03),
                          count=5, axis="y")
    head.append(_b("head.snout", (0.17, 0.22, 0.075), (0, 0.89, 0.44),
                   color=STEEL_DK))
    head.append(_b("head.nostril", (0.11, 0.05, 0.05), (0, 1.00, 0.46),
                   color=PLATE_DK))
    head.append(_b("head.snoutlamp", (0.09, 0.16, 0.025), (0, 0.90, 0.482),
                   material=_emit(REDG, 3.6)))
    for side, sign in (("L", 1), ("R", -1)):
        head.append(_b("head.snoutrib.%s" % side, (0.025, 0.20, 0.05),
                       (sign * 0.088, 0.89, 0.45), color=HULL))
    # Gape: a dark gap with the lower jaw hinged open under it.
    head.append(_b("head.gape", (0.20, 0.44, 0.035), (0, 0.72, 0.375),
                   color=PLATE_DK))
    head.append(_b("head.lower", (0.21, 0.42, 0.075), (0, 0.71, 0.325),
                   rot=(6, 0, 0), color=STEEL_DK))
    for j in range(6):
        t = (j + 0.5) / 6.0 - 0.5
        y = 0.60 + t * 0.34
        head.append(bk.wedge("head.tooth.u%d" % j, (0.032, 0.032, 0.06),
                             (0.085 - abs(t) * 0.02, y, 0.395),
                             rot=(180, 0, 0), color=STEEL_LT, taper=0.8))
        head.append(bk.wedge("head.tooth.uR%d" % j, (0.032, 0.032, 0.06),
                             (-0.085 + abs(t) * 0.02, y, 0.395),
                             rot=(180, 0, 0), color=STEEL_LT, taper=0.8))
        # Lower teeth interleave with the upper ones -- a gape with only
        # one row of teeth reads as a letterbox, not a mouth.
        for lx in (0.075, -0.075):
            head.append(bk.wedge("head.tooth.l%d_%d" % (j, lx > 0),
                                 (0.028, 0.028, 0.055),
                                 (lx - abs(t) * 0.015 * (1 if lx > 0 else -1),
                                  y + 0.028, 0.355),
                                 color=STEEL_LT, taper=0.8))
    # Jaw actuators, visible on both cheeks.
    for side, sign in (("L", 1), ("R", -1)):
        head.append(_piston("head.ram.%s" % side, (sign * 0.15, 0.40, 0.44),
                            (sign * 0.11, 0.54, 0.32), r=0.026))
        head.append(_b("head.cheek.%s" % side, (0.05, 0.18, 0.14),
                       (sign * 0.15, 0.40, 0.45), color=PLATE))
    # Crocodile eyes: mounted on top of the skull, not the front of it.
    for side, sign in (("L", 1), ("R", -1)):
        head.append(_b("head.hood.%s" % side, (0.11, 0.12, 0.08),
                       (sign * 0.09, 0.40, 0.58), color=PLATE))
        head.append(_b("head.eye.%s" % side, (0.07, 0.08, 0.035),
                       (sign * 0.09, 0.41, 0.625), material=_emit(REDG, 4.8)))
    head.append(_b("head.vent", (0.20, 0.03, 0.04), (0, 0.28, 0.52),
                   material=_emit(REDD, 2.4)))

    legs = {}
    for tag, y in (("FL", 0.06), ("BL", -0.28)):
        parts = _tube("leg.%s.seg" % tag,
                      [(0.21, y, 0.32), (0.33, y + 0.02, 0.24),
                       (0.35, y + 0.06, 0.06)],
                      [0.105, 0.085], [PLATE_MID, STEEL_DK])
        parts.append(_b("leg.%s.foot" % tag, (0.14, 0.18, 0.05),
                        (0.35, y + 0.10, 0.03), color=PLATE))
        for j, dx in enumerate((-0.045, 0.0, 0.045)):
            parts.append(bk.wedge("leg.%s.claw%d" % (tag, j), (0.03, 0.03, 0.075),
                                  (0.35 + dx, 0.20 + y, 0.03), rot=(-96, 0, 0),
                                  color=STEEL_LT, taper=0.85))
        left = _join("leg.%s" % tag, parts, (0.21, y, 0.32))
        legs["leg.%s" % tag] = left
        legs["leg.%sR" % tag[0]] = _mirror(left, "leg.%sR" % tag[0])

    tail_pts = [(0, -0.38, 0.36), (0, -0.52, 0.34), (0, -0.64, 0.29),
                (0, -0.74, 0.22), (0, -0.81, 0.13)]
    tail = _tube("tail.seg", tail_pts, [0.24, 0.20, 0.16, 0.12],
                 [PLATE, PLATE_MID])
    for i in range(4):
        tail.append(bk.wedge("tail.fin%d" % i, (0.05, 0.09, 0.19 - 0.03 * i),
                             (0, -0.46 - i * 0.115, 0.48 - i * 0.045),
                             rot=(14 * i, 0, 0), color=STEEL, taper=0.6))
    tail.append(_b("tail.tip", (0.07, 0.10, 0.07), (0, -0.85, 0.10),
                   color=STEEL_DK))

    groups = {
        "body": (body, (0, -0.12, 0.24)),
        "head": (head, (0, 0.26, 0.40)),
        "tail": (tail, (0, -0.34, 0.36)),
    }
    for key, obj in legs.items():
        groups[key] = ([obj], tuple(obj.location))
    _assemble(root, groups)
    return bk.finish(root)


# ===========================================================================
# Mecha Krakenoid -- Event, $1B.
# The krakenoid rebuilt in steel, on deliberately the same proportions: same
# leaning mantle, same low brow, same eight limbs. What changed is that the
# eyes became a machined optic cluster, the tentacles became segmented cable,
# and the mantle grew a reactor.
# ===========================================================================

def build_mecha_krakenoid():
    kit.reset_scene()
    root = kit.empty("root")

    mantle_at = (0, -0.22, 0.72)
    body = [_taper_block("body.mantle", (0.44, 0.40, 0.64), mantle_at,
                         color=PLATE_MID, bottom=0.60, seg=2)]
    body[0].rotation_euler = (math.radians(-13), 0, 0)
    # Same pointed hood as the organic twin, machined: a cowl, a mast and a
    # hazard-lit beacon where the flesh version has a horn.
    body.append(bk.wedge("body.crown", (0.34, 0.32, 0.34), (0, -0.32, 1.12),
                         color=HULL, taper=0.62))
    body += _hazard_strip("body.cowl", (0, -0.32, 1.00), (0.30, 0.24, 0.04),
                          count=5, axis="x")
    body.append(_b("body.mast", (0.04, 0.04, 0.18), (0, -0.33, 1.38),
                   color=STEEL_DK))
    body.append(_b("body.beacon", (0.06, 0.06, 0.06), (0, -0.33, 1.48),
                   material=_emit(REDG, 4.6)))
    # Reactor spine: three vents burning through the mantle plate.
    for i in range(3):
        body.append(_b("body.vent%d" % i, (0.20, 0.035, 0.035),
                       (0, -0.05 + i * 0.005, 0.58 + i * 0.11),
                       material=_emit(CYAN, 3.4)))
    body.append(_b("body.core.ring", (0.20, 0.06, 0.20), (0, -0.02, 0.74),
                   color=PLATE_DK))
    body.append(_b("body.core", (0.13, 0.05, 0.13), (0, 0.01, 0.74),
                   material=_emit(CYAN, 5.0)))
    for side, sign in (("L", 1), ("R", -1)):
        body.append(bk.wedge("body.fin.%s" % side, (0.05, 0.26, 0.30),
                             (sign * 0.23, -0.26, 0.92), rot=(0, sign * 34, 0),
                             color=STEEL_DK, taper=0.6))
        body.append(_b("body.rib.%s" % side, (0.05, 0.32, 0.32),
                       (sign * 0.21, -0.22, 0.68), color=PLATE_MID))
    body += _hazard_strip("body.tape", (0, -0.02, 0.50), (0.34, 0.07, 0.035),
                          count=6, axis="x")
    for side, sign in (("L", 1), ("R", -1)):
        pts = _tentacle_pts((sign * 0.16, -0.16, 0.46), (sign * 0.72, -0.70),
                            0.56)
        body += _tube("body.cable.%s" % side, pts,
                      [0.082, 0.068, 0.054, 0.040, 0.030, 0.021],
                      [PLATE_MID, STEEL_DK])

    head_dims = (0.42, 0.30, 0.32)
    head_at = (0, 0.16, 0.56)
    head = [_b("head.case", head_dims, head_at, color=HULL, seg=2)]
    head.append(_b("head.hood", (0.44, 0.22, 0.09), (0, 0.14, 0.74),
                   color=PLATE_MID))
    face_y = head_at[1] + head_dims[1] * 0.5
    # Optic cluster: same layout as the krakenoid's eyes, machined.
    for i, (dx, dz, size) in enumerate(_KRAKEN_EYES):
        colour = REDG if i < 3 else CYAN
        head.append(_b("head.mount%d" % i, (size * 1.5, 0.045, size * 1.5),
                       (dx, face_y, head_at[2] + dz), color=PLATE_DK))
        head.append(_b("head.lens%d" % i, (size, 0.035, size),
                       (dx, face_y + 0.032, head_at[2] + dz),
                       material=_emit(colour, 4.2)))
    head.append(_b("head.brace", (0.40, 0.04, 0.03), (0, face_y + 0.02, 0.42),
                   color=STEEL_DK))
    # Cutting beak: two chrome shears.
    head.append(bk.wedge("head.shear.up", (0.13, 0.11, 0.15), (0, 0.30, 0.38),
                         rot=(-118, 0, 0), color=STEEL_LT, taper=0.7))
    head.append(bk.wedge("head.shear.lo", (0.11, 0.09, 0.12), (0, 0.28, 0.29),
                         rot=(-62, 0, 0), color=STEEL, taper=0.7))
    for side, sign in (("L", 1), ("R", -1)):
        head.append(_piston("head.ram.%s" % side, (sign * 0.13, 0.24, 0.44),
                            (sign * 0.08, 0.31, 0.31), r=0.02))

    # Cable arms on exactly the organic twin's rearing arc, with a machined
    # knuckle and a cyan node at every joint instead of suckers.
    arm_pivot = (0.17, 0.24, 0.58)
    arm_pts = [arm_pivot, (0.31, 0.44, 0.76), (0.39, 0.64, 0.82),
               (0.41, 0.80, 0.73), (0.35, 0.88, 0.57), (0.25, 0.85, 0.47)]
    parts = _tube("arm.L.seg", arm_pts, [0.100, 0.084, 0.068, 0.054, 0.040],
                  [HULL, PLATE_MID])
    for j, pt in enumerate(arm_pts[1:5]):
        parts.append(_b("arm.L.knuckle%d" % j,
                        (0.082 - j * 0.014, 0.05, 0.082 - j * 0.014),
                        pt, color=STEEL))
        parts.append(_b("arm.L.node%d" % j, (0.030, 0.030, 0.030),
                        (pt[0] - 0.035, pt[1], pt[2] - 0.03),
                        material=_emit(CYAN, 3.4)))
    parts.append(bk.wedge("arm.L.hook", (0.045, 0.045, 0.13),
                          (0.23, 0.83, 0.42), rot=(-140, 0, 0),
                          color=STEEL_LT, taper=0.85))
    arm_l = _join("arm.L", parts, arm_pivot)
    arm_r = _mirror(arm_l, "arm.R")

    legs = {}
    leg_spec = {
        "FL": ((0.11, 0.26, 0.48), (0.72, 0.85), 0.64),
        "BL": ((0.16, 0.12, 0.48), (1.00, 0.05), 0.58),
    }
    for tag, (base, heading, reach) in leg_spec.items():
        pts = _tentacle_pts(base, heading, reach)
        parts = _tube("leg.%s.seg" % tag, pts,
                      [0.105, 0.088, 0.068, 0.050, 0.036, 0.026],
                      [HULL, PLATE_MID])
        for j, pt in enumerate(pts[1:4]):
            parts.append(_b("leg.%s.node%d" % (tag, j), (0.026, 0.026, 0.026),
                            (pt[0] - 0.03, pt[1], pt[2] - 0.02),
                            material=_emit(CYAN, 3.0)))
        parts.append(_b("leg.%s.tip" % tag, (0.05, 0.05, 0.05), pts[-1],
                        color=STEEL))
        left = _join("leg.%s" % tag, parts, base)
        legs["leg.%s" % tag] = left
        legs["leg.%sR" % tag[0]] = _mirror(left, "leg.%sR" % tag[0])

    groups = {
        "body": (body, (0, -0.14, 0.30)),
        "head": (head, (0, 0.04, 0.44)),
        "arm.L": ([arm_l], tuple(arm_l.location)),
        "arm.R": ([arm_r], tuple(arm_r.location)),
    }
    for key, obj in legs.items():
        groups[key] = ([obj], tuple(obj.location))
    _assemble(root, groups)
    return bk.finish(root)


# ===========================================================================
# Dreadscale -- Event, $2B.
# A dragon of black scale and bone. Rearing, long-necked, wings half open,
# with a spine of bone spurs running unbroken from the skull to the tail
# blade and red firelight leaking out of every gap in it.
# ===========================================================================

def build_dreadscale():
    kit.reset_scene()
    root = kit.empty("root")

    chest_at = (0, 0.02, 0.74)
    body = [_b("body.chest", (0.42, 0.44, 0.50), chest_at, color=VOIDBLK, seg=2)]
    body.append(_b("body.hips", (0.38, 0.34, 0.36), (0, -0.32, 0.52),
                   color=VOIDGREY, seg=2))
    body.append(_b("body.waist", (0.32, 0.20, 0.32), (0, -0.16, 0.62),
                   color=VOIDBLK))
    # Bone breastplate + the fire behind it.
    for i in range(4):
        body.append(_b("body.rib%d" % i, (0.30 - i * 0.02, 0.05, 0.05),
                       (0, 0.24, 0.90 - i * 0.12), color=BONE))
    body.append(_b("body.forge", (0.16, 0.05, 0.26), (0, 0.23, 0.76),
                   material=_emit(REDG, 3.0)))
    for side, sign in (("L", 1), ("R", -1)):
        body.append(_b("body.shoulder.%s" % side, (0.10, 0.24, 0.24),
                       (sign * 0.20, 0.06, 0.86), color=VOIDGREY))
        body.append(bk.wedge("body.spur.%s" % side, (0.05, 0.05, 0.16),
                             (sign * 0.20, 0.02, 1.02), rot=(24, -sign * 26, 0),
                             color=BONE, taper=0.85))
    # Spine spurs from the shoulders back to the hips.
    for i in range(5):
        t = i / 4.0
        body.append(bk.wedge("body.spine%d" % i, (0.05, 0.06, 0.15 - 0.03 * t),
                             (0, 0.14 - i * 0.13, 0.99 - t * 0.30),
                             rot=(-18 - 8 * i, 0, 0), color=BONE, taper=0.8))
    for i in range(3):
        body.append(_b("body.crack%d" % i, (0.05, 0.20, 0.02),
                       (0.19 - i * 0.02, -0.06 - i * 0.10, 0.68 + i * 0.05),
                       material=_emit(REDD, 2.4)))
        body.append(_b("body.crackR%d" % i, (0.05, 0.20, 0.02),
                       (-0.19 + i * 0.02, -0.06 - i * 0.10, 0.68 + i * 0.05),
                       material=_emit(REDD, 2.4)))

    # Neck rises forward out of the chest; head sits well clear of it.
    neck_pts = [(0, 0.16, 0.96), (0, 0.28, 1.10), (0, 0.40, 1.20)]
    head = _tube("head.neck", neck_pts, [0.19, 0.16], [VOIDBLK, VOIDGREY])
    head_dims = (0.30, 0.34, 0.28)
    head_at = (0, 0.58, 1.26)
    head.append(_b("head.skull", head_dims, head_at, color=VOIDBLK, seg=2))
    head.append(_b("head.upper", (0.23, 0.30, 0.13), (0, 0.86, 1.24),
                   color=VOIDGREY))
    head.append(_b("head.lower", (0.19, 0.28, 0.08), (0, 0.84, 1.12),
                   rot=(9, 0, 0), color=VOIDGREY))
    head.append(_b("head.maw", (0.17, 0.22, 0.035), (0, 0.84, 1.18),
                   material=_emit(REDG, 4.0)))
    head.append(_b("head.throat", (0.16, 0.10, 0.10), (0, 0.44, 1.12),
                   material=_emit(REDD, 2.4)))
    for j in range(4):
        t = (j + 0.5) / 4.0 - 0.5
        head.append(bk.wedge("head.tooth.u%d" % j, (0.03, 0.03, 0.06),
                             (t * 0.17, 0.82 + abs(t) * 0.05, 1.165),
                             rot=(180, 0, 0), color=BONE, taper=0.8))
        head.append(bk.wedge("head.tooth.l%d" % j, (0.028, 0.028, 0.055),
                             (t * 0.15, 0.82 + abs(t) * 0.05, 1.14),
                             color=BONE, taper=0.8))
    head += bk.nostrils("head.nose", (0, 0.99, 1.24), (0.22, 0.10, 0.13),
                        spacing=0.5, height=0.02, size=0.032, color="#0b0a0e")
    for side, sign in (("L", 1), ("R", -1)):
        head.append(_b("head.socket.%s" % side, (0.11, 0.06, 0.09),
                       (sign * 0.13, 0.72, 1.33), color="#0b0a0e"))
        head.append(_b("head.eye.%s" % side, (0.07, 0.045, 0.05),
                       (sign * 0.13, 0.75, 1.33), material=_emit(REDG, 5.4)))
        head.append(_b("head.jawspike.%s" % side, (0.035, 0.12, 0.035),
                       (sign * 0.14, 0.66, 1.13), rot=(0, 0, sign * 16),
                       color=BONE))
    # Horns: two long bone sweeps off the back of the skull.
    for side, sign in (("L", 1), ("R", -1)):
        head += _tube("head.horn.%s" % side,
                      [(sign * 0.13, 0.50, 1.40), (sign * 0.21, 0.34, 1.54),
                       (sign * 0.25, 0.14, 1.58)],
                      [0.065, 0.048], [BONE, "#efe6c8"])
        head.append(bk.wedge("head.hornv.%s" % side, (0.04, 0.04, 0.12),
                             (sign * 0.26, 0.05, 1.58), rot=(-104, 0, 0),
                             color="#efe6c8", taper=0.9))
        head.append(bk.wedge("head.frill.%s" % side, (0.03, 0.09, 0.12),
                             (sign * 0.16, 0.48, 1.14), rot=(0, -sign * 40, 0),
                             color=BONE, taper=0.7))

    # Membrane wings: a webbed slab with three bone fingers and a leading spar.
    wing_pivot = (0.20, 0.02, 0.96)
    parts = [_b("wing.L.web", (0.72, 0.04, 0.54), (0.58, -0.06, 1.02),
                rot=(0, -26, 0), color="#332a3d")]
    parts.append(_b("wing.L.web2", (0.44, 0.035, 0.36), (0.86, -0.14, 0.72),
                    rot=(0, -42, 0), color="#241e2e"))
    # Three trailing points. A membrane with a straight back edge is a
    # sail; the scallops are what make it a wing.
    for j, (x, z, sz) in enumerate(((0.48, 0.60, 0.22), (0.72, 0.72, 0.19),
                                    (0.92, 0.84, 0.15))):
        parts.append(bk.wedge("wing.L.point%d" % j, (sz * 0.5, 0.04, sz),
                              (x, -0.06, z), rot=(180, 0, 0),
                              color="#241e2e", taper=0.75))
    # Bone claws along the leading edge -- the only pale note on the wing.
    for j, (x, z) in enumerate(((0.36, 1.26), (0.66, 1.24))):
        parts.append(bk.wedge("wing.L.hook%d" % j, (0.035, 0.035, 0.10),
                              (x, 0.0, z), rot=(-96, -18, 0), color=BONE,
                              taper=0.85))
    parts.append(_b("wing.L.spar", (0.78, 0.055, 0.065), (0.58, -0.02, 1.22),
                    rot=(0, -14, 0), color="#6a5d78"))
    # Thin fingers. Fat ones turn the wing into a bone rack rather than a
    # membrane with bones in it.
    for j in range(3):
        t = (j + 1) / 4.0
        parts.append(_b("wing.L.finger%d" % j, (0.032, 0.05, 0.50 - 0.06 * j),
                        (0.24 + t * 0.70, -0.06, 1.04 - t * 0.12),
                        rot=(0, 8 + 14 * j, 0),
                        color="#4a4256"))
    parts.append(bk.wedge("wing.L.claw", (0.045, 0.045, 0.15), (1.00, 0.0, 1.24),
                          rot=(-90, -40, 0), color="#efe6c8", taper=0.85))
    wing_l = _join("wing.L", parts, wing_pivot)
    wing_r = _mirror(wing_l, "wing.R")

    # Small clawed forelimbs.
    arm_pivot = (0.18, 0.16, 0.76)
    parts = _tube("arm.L.seg", [arm_pivot, (0.26, 0.30, 0.60), (0.24, 0.34, 0.44)],
                  [0.075, 0.06], [VOIDGREY, VOIDBLK])
    for j, dx in enumerate((-0.04, 0.0, 0.04)):
        parts.append(bk.wedge("arm.L.claw%d" % j, (0.028, 0.028, 0.10),
                              (0.24 + dx, 0.38, 0.40), rot=(-118, 0, 0),
                              color=BONE, taper=0.85))
    arm_l = _join("arm.L", parts, arm_pivot)
    arm_r = _mirror(arm_l, "arm.R")

    legs = {}
    hip = (0.20, -0.30, 0.52)
    parts = _tube("leg.BL.seg",
                  [hip, (0.25, -0.46, 0.40), (0.23, -0.24, 0.16)],
                  [0.14, 0.11], [VOIDGREY, VOIDBLK])
    parts.append(_b("leg.BL.foot", (0.15, 0.24, 0.07), (0.23, -0.14, 0.04),
                    color=VOIDBLK))
    for j, dx in enumerate((-0.05, 0.0, 0.05)):
        parts.append(bk.wedge("leg.BL.claw%d" % j, (0.032, 0.032, 0.10),
                              (0.23 + dx, -0.02, 0.04), rot=(-96, 0, 0),
                              color=BONE, taper=0.85))
    leg_bl = _join("leg.BL", parts, hip)
    legs["leg.BL"] = leg_bl
    legs["leg.BR"] = _mirror(leg_bl, "leg.BR")

    tail_pts = [(0, -0.46, 0.52), (0, -0.62, 0.46), (0, -0.78, 0.38),
                (0, -0.90, 0.28), (0, -0.98, 0.17)]
    tail = _tube("tail.seg", tail_pts, [0.20, 0.16, 0.125, 0.09],
                 [VOIDBLK, VOIDGREY])
    for i in range(4):
        tail.append(bk.wedge("tail.spur%d" % i, (0.045, 0.055, 0.13 - 0.02 * i),
                             (0, -0.53 - i * 0.15, 0.60 - i * 0.09),
                             rot=(-42 - 12 * i, 0, 0), color=BONE, taper=0.8))
    tail.append(bk.wedge("tail.blade", (0.06, 0.09, 0.22), (0, -1.03, 0.09),
                         rot=(-58, 0, 0), color=BONE, taper=0.75))

    groups = {
        "body": (body, (0, -0.06, 0.46)),
        "head": (head, (0, 0.14, 0.96)),
        "wing.L": ([wing_l], tuple(wing_l.location)),
        "wing.R": ([wing_r], tuple(wing_r.location)),
        "arm.L": ([arm_l], tuple(arm_l.location)),
        "arm.R": ([arm_r], tuple(arm_r.location)),
        "tail": (tail, (0, -0.42, 0.52)),
    }
    for key, obj in legs.items():
        groups[key] = ([obj], tuple(obj.location))
    _assemble(root, groups)
    return bk.finish(root)


# ===========================================================================
# Mecha Dreadscale -- Event, $4B. The most valuable pet in the game.
# Built on the dreadscale's exact skeleton so the pair reads as one animal
# twice, then given everything the biome has: layered plate over a black
# frame, a reactor burning in the chest, jet-vented wings with lit thruster
# pods, twin cannons off the shoulders, hazard tape on the armour, and a
# tail that ends in an afterburner instead of a blade.
# ===========================================================================

def build_mecha_dreadscale():
    kit.reset_scene()
    root = kit.empty("root")

    # ---- torso -----------------------------------------------------------
    # Same skeleton as the organic twin, one size up and rearing harder: the
    # hips sit low and back, the chest stands nearly vertical, and everything
    # above the shoulder line is deliberately kept clear so the head has air
    # around it. Crowding the skull was what made the first pass read as a
    # scrapheap rather than a war machine.
    # Value matters more than hue here. A torso in the darkest plate colour
    # becomes a hole between two pale wings on the contact sheet, so the big
    # masses are mid-grey and the DARK tone is reserved for the recesses.
    chest_at = (0, 0.02, 0.86)
    body = [_b("body.chest", (0.52, 0.50, 0.60), chest_at, color=PLATE_MID,
               seg=2)]
    body.append(_b("body.hips", (0.46, 0.42, 0.44), (0, -0.36, 0.54),
                   color=HULL, seg=2))
    body.append(_b("body.waist", (0.36, 0.24, 0.34), (0, -0.17, 0.68),
                   color=PLATE))
    # Layered skirt armour over the hips -- weight the organic twin lacks.
    for i in range(3):
        body.append(_b("body.skirt%d" % i, (0.48 - i * 0.05, 0.11, 0.15),
                       (0, -0.26 - i * 0.12, 0.44 - i * 0.05),
                       rot=(-14 - 8 * i, 0, 0), color=HULL))
    for side, sign in (("L", 1), ("R", -1)):
        body.append(_b("body.flank.%s" % side, (0.07, 0.46, 0.38),
                       (sign * 0.27, -0.04, 0.80), color=HULL))
        body.append(_b("body.grille.%s" % side, (0.035, 0.30, 0.24),
                       (sign * 0.31, -0.02, 0.78), color=PLATE_DK))

    # ---- the reactor -----------------------------------------------------
    # One part has to carry a four-billion-dollar price tag, so this is it:
    # a white-hot core in a machined collar, ringed by a hazard-gold halo and
    # bolted into a pale armour frame. It is the first thing the eye finds on
    # the sheet and the thing the 24px icon is recognised by.
    body.append(_b("body.frame", (0.40, 0.08, 0.40), (0, 0.26, 0.88),
                   color=HULL))
    body.append(_b("body.collar", (0.28, 0.07, 0.28), (0, 0.30, 0.88),
                   color=STEEL_DK))
    body += bk.gem("body.core", (0, 0.35, 0.88), size=0.22, color=REDG,
                   strength=7.0)
    body += bk.ring("body.halo", (0, 0.33, 0.88), radius=0.25, thickness=0.024,
                    tilt=90, color=HAZARD, strength=3.2)
    for i in range(4):
        ang = 45 + i * 90
        body.append(_b("body.bolt%d" % i, (0.055, 0.055, 0.055),
                       (math.sin(math.radians(ang)) * 0.19, 0.28,
                        0.88 + math.cos(math.radians(ang)) * 0.19),
                       color=GOLD))

    # ---- shoulders and cannons ------------------------------------------
    # Pauldrons stop at z=1.14 and the jaw starts at 1.40. That gap is the
    # entire reason the head reads as a head and not as more shoulder.
    for side, sign in (("L", 1), ("R", -1)):
        body.append(_b("body.pauldron.%s" % side, (0.18, 0.34, 0.28),
                       (sign * 0.26, 0.02, 0.96), color=PLATE_MID, seg=2))
        body += _hazard_strip("body.tape.%s" % side,
                              (sign * 0.26, 0.02, 1.115), (0.17, 0.30, 0.04),
                              count=5, axis="y")
        body.append(_b("body.pauldron2.%s" % side, (0.15, 0.28, 0.11),
                       (sign * 0.29, 0.02, 0.83), rot=(0, -sign * 16, 0),
                       color=HULL))
        # Swept OUT, not up: an upward spike fights the horns for the skyline.
        body.append(bk.wedge("body.spike.%s" % side, (0.07, 0.07, 0.26),
                             (sign * 0.40, 0.00, 1.05), rot=(10, -sign * 74, 0),
                             color=STEEL_LT, taper=0.85))
        # Shoulder cannons, outboard and level, muzzles well clear of the jaw.
        body.append(_b("body.gun.%s" % side, (0.13, 0.26, 0.13),
                       (sign * 0.34, -0.06, 1.07), rot=(-8, 0, 0),
                       color=PLATE_DK))
        body.append(bk.cylinder("body.barrel.%s" % side, r=0.038, h=0.30,
                                loc=(sign * 0.34, 0.15, 1.10), rot=(82, 0, 0),
                                color=STEEL_DK, verts=8))
        body.append(_b("body.muzzle.%s" % side, (0.055, 0.045, 0.055),
                       (sign * 0.34, 0.31, 1.11), material=_emit(REDG, 4.0)))
        body.append(_b("body.magazine.%s" % side, (0.10, 0.12, 0.10),
                       (sign * 0.34, -0.20, 1.04), color=HAZARD))

    # Spine: steel blades instead of bone spurs, each with a lit root.
    for i in range(6):
        t = i / 5.0
        body.append(bk.wedge("body.blade%d" % i, (0.06, 0.085, 0.22 - 0.04 * t),
                             (0, 0.14 - i * 0.14, 1.12 - t * 0.42),
                             rot=(-18 - 8 * i, 0, 0), color=GOLD, taper=0.75))
        body.append(_b("body.spark%d" % i, (0.045, 0.055, 0.022),
                       (0, 0.14 - i * 0.14, 1.05 - t * 0.41),
                       material=_emit(REDG, 3.2)))
    for i in range(3):
        for side, sign in (("L", 1), ("R", -1)):
            body.append(_b("body.vent.%s%d" % (side, i), (0.05, 0.18, 0.035),
                           (sign * (0.28 - i * 0.015), -0.08 - i * 0.12,
                            0.74 + i * 0.05),
                           material=_emit(REDD, 2.8)))

    # ---- neck and head ---------------------------------------------------
    # Everything above the shoulders is paid for twice: the pet is normalised
    # by HEIGHT, so a taller skyline shrinks the wings, the reactor and the
    # jaw along with it. The head therefore sits as low as it can while still
    # standing clear of the pauldrons.
    neck_pts = [(0, 0.18, 1.02), (0, 0.30, 1.16), (0, 0.40, 1.28)]
    head = _tube("head.neck", neck_pts, [0.21, 0.17], [PLATE_DK, PLATE_MID])
    for i, pt in enumerate(neck_pts[:2]):
        head.append(_b("head.collar%d" % i, (0.26, 0.07, 0.26),
                       (pt[0], pt[1] + 0.06, pt[2] + 0.08), color=STEEL_DK))
    head_dims = (0.38, 0.36, 0.31)
    head_at = (0, 0.58, 1.38)
    head.append(_b("head.skull", head_dims, head_at, color=PLATE_MID,
                   seg=2))
    head.append(_b("head.helm", (0.42, 0.32, 0.12), (0, 0.56, 1.60),
                   color=STEEL))
    head.append(_b("head.browtrim", (0.40, 0.10, 0.05), (0, 0.72, 1.53),
                   color=GOLD))
    head.append(bk.wedge("head.crest", (0.08, 0.24, 0.19), (0, 0.46, 1.71),
                         rot=(-26, 0, 0), color=GOLD, taper=0.7))
    head.append(_b("head.upper", (0.28, 0.32, 0.15), (0, 0.86, 1.35),
                   color=HULL))
    head.append(_b("head.lower", (0.24, 0.28, 0.10), (0, 0.82, 1.21),
                   rot=(9, 0, 0), color=STEEL_DK))
    head.append(_b("head.maw", (0.18, 0.22, 0.035), (0, 0.82, 1.28),
                   material=_emit(REDG, 4.6)))
    for j in range(4):
        t = (j + 0.5) / 4.0 - 0.5
        head.append(bk.wedge("head.tooth.u%d" % j, (0.032, 0.032, 0.065),
                             (t * 0.17, 0.80 + abs(t) * 0.05, 1.265),
                             rot=(180, 0, 0), color=STEEL_LT, taper=0.8))
        head.append(bk.wedge("head.tooth.l%d" % j, (0.03, 0.03, 0.06),
                             (t * 0.15, 0.80 + abs(t) * 0.05, 1.24),
                             color=STEEL_LT, taper=0.8))
    head += bk.nostrils("head.nose", (0, 1.00, 1.35), (0.24, 0.10, 0.14),
                        spacing=0.5, height=0.02, size=0.034, color=PLATE_DK)
    # Optic visor plus two separate hot eyes behind it -- more machine than
    # the organic twin's simple sockets.
    head += _optic_bar("head.visor", (0, 0.75, 1.47), (0.30, 0.05, 0.06),
                       color=REDG, strength=5.6)
    for side, sign in (("L", 1), ("R", -1)):
        head.append(_b("head.eye.%s" % side, (0.048, 0.04, 0.038),
                       (sign * 0.17, 0.735, 1.47), material=_emit(HAZARD, 4.4)))
        head.append(_piston("head.ram.%s" % side, (sign * 0.14, 0.62, 1.35),
                            (sign * 0.11, 0.74, 1.24), r=0.024))
        head.append(_b("head.cheek.%s" % side, (0.055, 0.17, 0.14),
                       (sign * 0.15, 0.62, 1.34), color=PLATE_DK))
        head.append(bk.wedge("head.tusk.%s" % side, (0.04, 0.04, 0.14),
                             (sign * 0.15, 0.76, 1.22), rot=(-118, 0, sign * 14),
                             color=STEEL_LT, taper=0.85))
    # Horns rebuilt as swept steel with a lit tip.
    for side, sign in (("L", 1), ("R", -1)):
        head += _tube("head.horn.%s" % side,
                      [(sign * 0.15, 0.50, 1.55), (sign * 0.27, 0.32, 1.70),
                       (sign * 0.34, 0.10, 1.74)],
                      [0.085, 0.058], [GOLD, STEEL_LT])
        head.append(bk.wedge("head.hornv.%s" % side, (0.04, 0.04, 0.12),
                             (sign * 0.35, 0.01, 1.74), rot=(-104, 0, 0),
                             color=STEEL_LT, taper=0.9))
        head.append(_b("head.horntip.%s" % side, (0.038, 0.038, 0.038),
                       (sign * 0.35, -0.06, 1.74), material=_emit(REDG, 3.8)))

    # ---- wings -----------------------------------------------------------
    # The widest thing in the library. Panels are HULL, not PLATE: a dark wing
    # on a dark background is a hole in the silhouette, and the wingspan is
    # most of why this pet reads as the top of the ladder.
    wing_pivot = (0.24, -0.02, 1.00)
    parts = [_b("wing.L.panel", (0.86, 0.055, 0.58), (0.68, -0.08, 1.04),
                rot=(0, -30, 0), color=STEEL)]
    parts.append(_b("wing.L.panel2", (0.50, 0.05, 0.40), (1.02, -0.18, 0.72),
                   rot=(0, -48, 0), color=HULL))
    parts.append(_b("wing.L.armour", (0.34, 0.065, 0.26), (0.42, 0.02, 1.14),
                   rot=(0, -22, 0), color=STEEL_DK))
    parts.append(_b("wing.L.spar", (0.94, 0.07, 0.085), (0.68, -0.01, 1.30),
                   rot=(0, -16, 0), color=GOLD))
    parts.append(_b("wing.L.edge", (0.84, 0.05, 0.04), (0.68, -0.12, 1.20),
                   rot=(0, -28, 0), material=_emit(REDG, 2.6)))
    for j in range(4):
        t = (j + 1) / 5.0
        parts.append(_b("wing.L.rib%d" % j, (0.045, 0.06, 0.56 - 0.07 * j),
                        (0.28 + t * 0.84, -0.07, 1.06 - t * 0.14),
                        rot=(0, 8 + 13 * j, 0), color=GOLD))
    # Scalloped trailing edge. Without these three points the wing is a
    # rectangle bolted to a robot; with them the outline is a dragon's.
    for j, (x, z, s) in enumerate(((0.58, 0.50, 0.26), (0.82, 0.63, 0.22),
                                   (1.04, 0.76, 0.18))):
        parts.append(bk.wedge("wing.L.point%d" % j, (s * 0.5, 0.05, s),
                              (x, -0.08, z), rot=(180, 0, 0), color=PLATE_MID,
                              taper=0.75))
    # Thruster pods: pod, hazard band, jet, and a trail block behind it. Three
    # per wing is what makes the thing read as powered, not merely armoured.
    for j, (x, z) in enumerate(((0.44, 1.06), (0.84, 0.92), (0.28, 0.84))):
        parts.append(_b("wing.L.pod%d" % j, (0.11, 0.24, 0.11), (x, -0.12, z),
                        color=PLATE_MID))
        parts.append(_b("wing.L.band%d" % j, (0.12, 0.05, 0.12), (x, -0.02, z),
                        color=HAZARD))
        parts.append(_b("wing.L.jet%d" % j, (0.085, 0.05, 0.085),
                        (x, -0.25, z - 0.01), material=_emit(REDG, 5.4)))
        parts.append(_b("wing.L.trail%d" % j, (0.06, 0.13, 0.06),
                        (x, -0.37, z - 0.02), material=_emit("#ff9a5a", 2.8)))
    parts.append(bk.wedge("wing.L.claw", (0.05, 0.05, 0.17), (1.20, 0.0, 1.32),
                          rot=(-90, -40, 0), color=STEEL_LT, taper=0.85))
    wing_l = _join("wing.L", parts, wing_pivot)
    wing_r = _mirror(wing_l, "wing.R")

    arm_pivot = (0.19, 0.16, 0.80)
    parts = _tube("arm.L.seg", [arm_pivot, (0.28, 0.32, 0.64), (0.26, 0.36, 0.48)],
                  [0.085, 0.068], [HULL, PLATE_MID])
    parts.append(_b("arm.L.guard", (0.12, 0.13, 0.12), (0.25, 0.26, 0.58),
                    color=STEEL_DK))
    for j, dx in enumerate((-0.04, 0.0, 0.04)):
        parts.append(bk.wedge("arm.L.claw%d" % j, (0.032, 0.032, 0.12),
                              (0.26 + dx, 0.41, 0.44), rot=(-118, 0, 0),
                              color=STEEL_LT, taper=0.85))
    arm_l = _join("arm.L", parts, arm_pivot)
    arm_r = _mirror(arm_l, "arm.R")

    legs = {}
    hip = (0.22, -0.32, 0.54)
    parts = _tube("leg.BL.seg",
                  [hip, (0.28, -0.50, 0.40), (0.25, -0.24, 0.16)],
                  [0.16, 0.12], [HULL, PLATE_MID])
    parts.append(_piston("leg.BL.ram", (0.22, -0.40, 0.47), (0.25, -0.26, 0.20),
                         r=0.028))
    parts.append(_b("leg.BL.knee", (0.16, 0.14, 0.14), (0.28, -0.50, 0.40),
                    color=STEEL_DK))
    parts.append(_b("leg.BL.foot", (0.17, 0.26, 0.075), (0.25, -0.13, 0.04),
                    color=PLATE_MID))
    for j, dx in enumerate((-0.055, 0.0, 0.055)):
        parts.append(bk.wedge("leg.BL.claw%d" % j, (0.036, 0.036, 0.12),
                              (0.25 + dx, 0.0, 0.04), rot=(-96, 0, 0),
                              color=STEEL_LT, taper=0.85))
    leg_bl = _join("leg.BL", parts, hip)
    legs["leg.BL"] = leg_bl
    legs["leg.BR"] = _mirror(leg_bl, "leg.BR")

    tail_pts = [(0, -0.48, 0.54), (0, -0.66, 0.48), (0, -0.84, 0.39),
                (0, -0.98, 0.28), (0, -1.08, 0.16)]
    tail = _tube("tail.seg", tail_pts, [0.22, 0.18, 0.14, 0.10],
                 [PLATE, PLATE_MID])
    for i in range(4):
        tail.append(_b("tail.ring%d" % i, (0.21 - i * 0.035, 0.045,
                                           0.21 - i * 0.035),
                       (0, -0.58 - i * 0.16, 0.51 - i * 0.10), color=STEEL_DK))
        tail.append(bk.wedge("tail.blade%d" % i, (0.048, 0.065, 0.15 - 0.02 * i),
                             (0, -0.56 - i * 0.16, 0.63 - i * 0.10),
                             rot=(-42 - 12 * i, 0, 0), color=STEEL, taper=0.75))
    tail.append(bk.cylinder("tail.nozzle", r=0.085, h=0.10, loc=(0, -1.13, 0.11),
                            rot=(56, 0, 0), color=PLATE_DK, verts=10))
    tail.append(_b("tail.burn", (0.10, 0.07, 0.10), (0, -1.20, 0.07),
                   material=_emit(REDG, 5.2)))
    tail.append(_b("tail.trail", (0.065, 0.12, 0.065), (0, -1.29, 0.03),
                   material=_emit("#ff9a5a", 2.8)))

    groups = {
        "body": (body, (0, -0.06, 0.48)),
        "head": (head, (0, 0.14, 0.98)),
        "wing.L": ([wing_l], tuple(wing_l.location)),
        "wing.R": ([wing_r], tuple(wing_r.location)),
        "arm.L": ([arm_l], tuple(arm_l.location)),
        "arm.R": ([arm_r], tuple(arm_r.location)),
        "tail": (tail, (0, -0.44, 0.54)),
    }
    for key, obj in legs.items():
        groups[key] = ([obj], tuple(obj.location))
    _assemble(root, groups)
    return bk.finish(root)

PETS = {
    "mecha-scorpio": build_mecha_scorpio,
    "drilla": build_drilla,
    "strawberry-elephant": build_strawberry_elephant,
    "mecha-froggo": build_mecha_froggo,
    "mecha-crawler": build_mecha_crawler,
    "krakenoid": build_krakenoid,
    "mecha-crocodon": build_mecha_crocodon,
    "mecha-krakenoid": build_mecha_krakenoid,
    "dreadscale": build_dreadscale,
    "mecha-dreadscale": build_mecha_dreadscale,
}
