"""
Emberfall Caldera -- the eight volcano pets.

Palette discipline for this biome: the *rock* is almost black (charcoal with a
purple bias, so it does not read as a hole punched in the frame), the *flesh*
under it is deep red, and every bright thing is emissive -- molten orange up to
white-hot yellow. Nothing here is mid-grey; the contrast between near-black
plates and neon seams is the whole biome.

Two rules learned the hard way while lighting these:

  * Big emissive surfaces clip to flat white and destroy the form, so anything
    larger than a hand -- wing membranes, sails, breast plates -- burns at
    strength 1.0-1.6 and only small accents (irises, crack cores, flame tips)
    go above 2.5.
  * A glowing eye on a black skull needs a darker socket behind it or it reads
    as a hole cut in the head. `_glow_eyes` is that idiom and every pet uses it.

Shared idioms factored out at the top:

  `_cracks`      molten fissures punched through a body block, poking out both
                 flanks at once so they light their own neighbourhood.
  `_flames`      tapered emissive licks -- manes, crests, hoof-fire, tail tufts.
  `_leg`         a leg whose foot can be emissive, so burning hooves animate
                 with the step cycle instead of hovering under it.
  `_dragon_wing` arched membrane wing with a scalloped trailing edge.

Build convention is the forest module's: facing +Y, feet near z=0, parts named
for the runtime animator, `bk.finish(root)` last.
"""

import math

from mathutils import Vector

import blockkit as bk
import kit


# --------------------------------------------------------------------------
# biome palette
# --------------------------------------------------------------------------

CHAR = "#0f0d12"        # deepest shadow rock -- sockets, claws, tooth gaps
ROCK = "#191519"        # charcoal basalt, the default body colour
ROCK_LIT = "#2a2432"    # the plate above the crack; slightly purple
ASH = "#4a4048"         # weathered stone, for horns read against black
BONE = "#d8ccb4"        # bull horn / tusk
DEEP_RED = "#7e1b14"    # cooled magma, the "flesh" tone
RED = "#c02015"
EMBER = "#ff4a0c"       # coolest glow
MOLTEN = "#ff7a18"      # the biome's signature orange
FLARE = "#ffb01f"       # hot
YELLOW = "#ffe14a"      # hottest -- cores and irises only
GOLD = "#ffc23a"
CRIMSON = "#d43a0c"     # phoenix shadow tone; keeps gold from going flat


def _fire_mat(color, strength=2.8):
    """A shared emissive material, so tapered wedges and decals can burn too."""
    return kit.mat(
        "fire.%s.%d" % (color.strip("#"), int(strength * 10)),
        kit.hexcol(color), rough=0.18,
        emission=kit.hexcol(color), emission_strength=strength,
    )


def _mirror(obj, name):
    """Right-side twin of a left-side limb. Every limb's FIRST block is
    unrotated, so the joined mesh carries no object rotation to un-mirror."""
    twin = kit.duplicate(obj, name, mirror=True)
    twin.location = Vector((-obj.location.x, obj.location.y, obj.location.z))
    return twin


def _weldgroup(name, parts, pivot):
    merged = kit.join(parts, name)
    kit.weld(merged)
    kit.set_origin_to(merged, pivot)
    return merged


def _glow_eyes(name, at, dims, spacing=0.6, height=0.05, size=0.07,
               iris=YELLOW, socket=CHAR, face="front", strength=3.2,
               aspect=0.8):
    """
    A hot iris on a dark sunken socket. On a black skull a bare emissive plate
    reads as a hole; the socket ring is what turns it into an eye.
    """
    plane = bk.face_of(at, dims, face)
    span = dims[0] if face in ("front", "back") else dims[1]
    parts = []
    for side, sign in (("L", 1), ("R", -1)):
        offset = (sign * span * 0.5 * spacing, height)
        parts.append(bk.face_plate(
            "%s.%s.socket" % (name, side), plane, (size * 1.75, size * 1.5),
            face=face, color=socket, depth=0.022, offset=offset))
        parts.append(bk.face_plate(
            "%s.%s.iris" % (name, side), plane, (size, size * aspect),
            face=face, material=_fire_mat(iris, strength), depth=0.02,
            offset=offset, proud=bk.PROUD * 4))
    return parts


def _cracks(name, at, dims, count=3, color=MOLTEN, width=0.03, strength=2.4,
            seed=3, span=0.74):
    """
    Molten fissures across a block: short glowing bars slightly wider than the
    host so they break both flanks at once. Deterministic, so a rebuild of the
    same pet is identical.
    """
    parts = []
    state = seed * 7919 + 17
    for i in range(count):
        state = (state * 1103515245 + 12345) & 0x7FFFFFFF
        r1 = state / 0x7FFFFFFF
        state = (state * 1103515245 + 12345) & 0x7FFFFFFF
        r2 = state / 0x7FFFFFFF
        t = ((i + 0.5) / count - 0.5) * span
        v = (r1 - 0.5) * 0.44
        length = dims[2] * (0.24 + 0.34 * r2)
        parts.append(bk.glow_block(
            "%s.%d" % (name, i), (dims[0] * 1.04, width, length),
            (at[0], at[1] + t * dims[1], at[2] + v * dims[2]),
            color=color, strength=strength * (0.85 + 0.3 * r2),
        ))
    return parts


def _flames(name, at, count=5, spread=0.3, height=0.18, width=0.07,
            colors=(EMBER, MOLTEN, FLARE), strength=2.9, axis="y", lean=0.0):
    """A row of tapered fire licks. `axis` is the axis they march along."""
    parts = []
    for i in range(count):
        t = (i + 0.5) / count
        h = height * (0.55 + 0.55 * math.sin(math.pi * t))
        offset = (t - 0.5) * spread
        parts.append(bk.wedge(
            "%s.%d" % (name, i), (width, width, h),
            (at[0] + (offset if axis == "x" else 0.0),
             at[1] + (offset if axis == "y" else 0.0),
             at[2] + h * 0.45),
            rot=(lean, 0, 0),
            material=_fire_mat(colors[i % len(colors)], strength), taper=0.88,
        ))
    return parts


def _fire_collar(name, at, dims, ring=0.1, thickness=0.075, count=8,
                 colors=(MOLTEN, EMBER, FLARE), back=0.5, strength=2.9,
                 arc=(0.62, 0.88)):
    """
    A burning ruff BEHIND a skull -- the tufts sit in the upper arc only, so
    the collar frames the face instead of swallowing it.
    """
    parts = []
    rx = dims[0] * 0.5 + ring * 0.5
    rz = dims[2] * 0.5 + ring * 0.5
    for i in range(count):
        # sweep the upper 3/4 of the circle, skipping the chin
        angle = (arc[0] + (arc[1] - arc[0]) * 0) + (i / count) * 2 * math.pi
        if math.cos(angle) < -0.72:
            continue
        parts.append(bk.wedge(
            "%s.%d" % (name, i), (thickness, thickness * 0.8, thickness * 2.1),
            (at[0] + math.sin(angle) * rx,
             at[1] - dims[1] * back,
             at[2] + math.cos(angle) * rz),
            rot=(0, math.degrees(angle), 0),
            material=_fire_mat(colors[i % len(colors)], strength), taper=0.78,
        ))
    return parts


def _leg(name, at, length=0.28, thickness=0.11, color=ROCK, foot_color=CHAR,
         foot_len=None, glow_foot=False, strength=2.4, splay=0.0):
    """One leg. `glow_foot` makes the foot emissive so it burns as it steps."""
    parts = [bk.block(name + ".hip", (thickness * 1.25, thickness * 1.25,
                                      thickness * 0.9), at, color=color)]
    parts.append(bk.block(
        name + ".shaft", (thickness, thickness, length),
        (at[0] + splay * length * 0.5, at[1], at[2] - length * 0.5),
        rot=(0, -math.degrees(math.atan(splay)), 0), color=color,
    ))
    fl = foot_len or thickness * 1.8
    foot_dims = (thickness * 1.25, fl, thickness * 0.6)
    foot_at = (at[0] + splay * length, at[1] + fl * 0.2,
               at[2] - length - thickness * 0.2)
    if glow_foot:
        parts.append(bk.glow_block(name + ".foot", foot_dims, foot_at,
                                   color=foot_color, strength=strength))
    else:
        parts.append(bk.block(name + ".foot", foot_dims, foot_at, color=foot_color))
    return _weldgroup(name, parts, at)


def _legs_quad(prefix, front, back, length=0.28, thickness=0.11, color=ROCK,
               foot_color=CHAR, glow_foot=False, foot_len=None, splay=0.0,
               back_length=None, back_thickness=None, strength=2.4):
    out = {}
    for tag, at, ln, th in (
        ("F", front, length, thickness),
        ("B", back, back_length or length, back_thickness or thickness),
    ):
        left = _leg("%s.%sL" % (prefix, tag), at, ln, th, color, foot_color,
                    foot_len, glow_foot, strength=strength, splay=splay)
        out["%s.%sL" % (prefix, tag)] = left
        out["%s.%sR" % (prefix, tag)] = _mirror(left, "%s.%sR" % (prefix, tag))
    return out


def _arm(name, at, length=0.24, thickness=0.08, color=RED, hand_color=None,
         angle=18.0):
    rad = angle * math.pi / 180.0
    dz = math.cos(rad) * length
    dx = math.sin(rad) * length
    parts = [
        bk.block(name + ".shoulder", (thickness * 1.35, thickness * 1.35,
                                      thickness * 1.15), at, color=color),
        bk.block(name + ".shaft", (thickness, thickness, length),
                 (at[0] + dx * 0.5, at[1], at[2] - dz * 0.5),
                 rot=(0, angle, 0), color=color),
        bk.block(name + ".fist", (thickness * 1.6, thickness * 1.6, thickness * 1.4),
                 (at[0] + dx, at[1] + thickness * 0.25, at[2] - dz),
                 color=hand_color or color),
    ]
    left = _weldgroup(name + ".L", parts, at)
    return left, _mirror(left, name + ".R")


def _dragon_wing(name, at, span=0.62, drop=0.44, rise=26.0, sweep=0.16,
                 web=DEEP_RED, bone=ROCK_LIT, vein=MOLTEN, panels=4,
                 strength=0.55, thickness=0.04, claw=True):
    """
    An arched membrane wing.

    The first pass made the whole membrane emissive, and a big uniformly
    burning slab has no shading, so both dragons grew orange signboards. The
    fix is the way real lava reads: the membrane is nearly-dark cooled rock
    lit from *within* by a vein down every finger and a hot line under the
    spar. Contrast, not brightness, is what makes it a wing.

    The trailing edge is deliberately scalloped -- deepest just inboard of
    centre, falling away hard at the tip -- and each panel is dragged further
    back (`sweep`) than the last so the wing is swept, not square.
    """
    rad = math.radians(rise)
    cos_r, sin_r = math.cos(rad), math.sin(rad)
    step = span / panels
    parts = [bk.block(name + ".shoulder", (0.11, 0.15, 0.16), at, color=bone)]
    parts.append(bk.block(
        name + ".spar", (span, thickness * 1.8, thickness * 2.1),
        (at[0] + span * 0.5 * cos_r, at[1] - sweep * 0.5, at[2] + span * 0.5 * sin_r),
        rot=(0, -rise, 0), color=bone,
    ))
    for i in range(panels):
        t = (i + 0.5) / panels
        # Full depth at the root, falling away quadratically to the tip. A
        # sinusoid was tried first and got the profile backwards -- the outer
        # panels came out the deepest and the wing read as a rectangle.
        depth = drop * (1.0 - 0.62 * t * t)
        px = at[0] + span * t * cos_r
        py = at[1] - sweep * t * t
        pz = at[2] + span * t * sin_r - depth * 0.5
        parts.append(bk.glow_block(
            "%s.web%d" % (name, i), (step * 1.03, thickness, depth),
            (px, py, pz), rot=(0, -rise, 0), color=web, strength=strength,
        ))
        # Finger bone down the leading edge of the panel...
        parts.append(bk.block(
            "%s.finger%d" % (name, i),
            (thickness * 1.35, thickness * 1.7, depth * 1.06),
            (px - step * 0.5 * cos_r, py, pz + depth * 0.02),
            rot=(0, -rise, 0), color=bone,
        ))
        # ...and the molten vein that runs beside it, half the panel's depth,
        # so the fire reads as leaking *between* the fingers.
        parts.append(bk.glow_block(
            "%s.vein%d" % (name, i),
            (thickness * 1.0, thickness * 1.15, depth * 0.62),
            (px - step * 0.32 * cos_r, py, pz + depth * 0.16),
            rot=(0, -rise, 0), color=vein, strength=2.3,
        ))
        # Hot line welded under the spar: the wing's top edge glows all the way
        # out, which is what carries it at icon size.
        parts.append(bk.glow_block(
            "%s.edge%d" % (name, i), (step * 1.02, thickness * 1.1, thickness * 1.2),
            (px, py, pz + depth * 0.5 - thickness * 0.4), rot=(0, -rise, 0),
            color=vein, strength=1.9,
        ))
    if claw:
        parts.append(bk.wedge(
            name + ".claw", (thickness * 1.7, thickness * 1.7, 0.13),
            (at[0] + span * 1.03 * cos_r, at[1] - sweep,
             at[2] + span * 1.03 * sin_r + 0.05),
            rot=(0, -rise + 10, 0), color=bone, taper=0.86))
    left = _weldgroup(name + ".L", parts, at)
    return left, _mirror(left, name + ".R")


def _plume_wing(name, at, count=5, length=0.5, root_color=GOLD,
                colors=(CRIMSON, MOLTEN, FLARE, GOLD, YELLOW),
                pitch=(-30.0, 30.0), yaw=(6.0, -74.0), strength=1.1,
                width=0.15, coverts=3):
    """
    A feathered wing built as a swept fan, not a row of sticks.

    Two rules learned from the first pass, where the phoenix grew a starburst:
      * the fan must sweep BACKWARD as well as outward -- the leading feather
        points nearly straight out, the trailing one nearly straight back;
      * the trailing feathers must be the LONG ones, so the outline is a
        swept wing rather than a symmetric star.
    A short row of coverts over the roots hides the hub the feathers radiate
    from, which is the other half of the illusion.
    """
    parts = [bk.block(name + ".root", (0.13, 0.17, 0.16), at, color=root_color)]
    for i in range(count):
        t = i / max(1, count - 1)
        py = pitch[0] + (pitch[1] - pitch[0]) * t
        pz = yaw[0] + (yaw[1] - yaw[0]) * t
        ln = length * (0.74 + 0.46 * t)
        ry, rz = math.radians(py), math.radians(pz)
        half = ln * 0.5
        loc = (at[0] + half * math.cos(rz) * math.cos(ry),
               at[1] + half * math.sin(rz) * math.cos(ry),
               at[2] - half * math.sin(ry))
        parts.append(bk.glow_block(
            "%s.f%d" % (name, i), (ln, width, 0.055), loc, rot=(0, py, pz),
            color=colors[i % len(colors)],
            strength=strength * (0.85 + 0.5 * t),
        ))
    for i in range(coverts):
        t = (i + 0.5) / coverts
        pz = yaw[0] - 16 - (yaw[0] - yaw[1]) * 0.55 * t
        ln = length * 0.34
        rz = math.radians(pz)
        parts.append(bk.glow_block(
            "%s.cov%d" % (name, i), (ln, width * 1.15, 0.06),
            (at[0] + ln * 0.5 * math.cos(rz), at[1] + ln * 0.5 * math.sin(rz),
             at[2] + 0.045),
            rot=(0, -12, pz), color=root_color, strength=strength * 0.75,
        ))
    left = _weldgroup(name + ".L", parts, at)
    return left, _mirror(left, name + ".R")


# ---------------------------------------------------------------------------
# Lava Gecko -- Rare, $180/s.
# Low, wide-stanced, splay-toed. The read is a flat lizard with light leaking
# out from between its plates.
#
# The proportions here were tuned against the normalised height rather than
# guessed: the first pass came out 3.9 body-lengths long for 1.0 tall, which is
# a plank, not a pet -- at icon size the head was four pixels of a very long
# smear. Shortening the tail and standing the torso up off the floor brings it
# to a bit over 2:1, which is where the forest quadrupeds sit.
# ---------------------------------------------------------------------------

def build_lava_gecko():
    kit.reset_scene()
    root = kit.empty("root")

    body_dims = (0.36, 0.56, 0.28)
    body_at = (0, -0.04, 0.42)
    body = [bk.block("body.core", body_dims, body_at, color=ROCK)]
    # A raised spine plate: the shape that makes a flat top read as scales.
    body.append(bk.block("body.ridge", (0.2, 0.46, 0.06),
                         (0, -0.04, 0.585), color=ROCK_LIT))
    body.append(bk.block("body.neck", (0.22, 0.14, 0.19),
                         (0, 0.28, 0.45), color=ROCK_LIT))
    # The belly seam is the pet's signature, so it runs the full length as one
    # unbroken line low on both flanks -- visible from any angle but above.
    body.append(bk.glow_block("body.seam", (0.375, 0.46, 0.045),
                              (0, -0.04, 0.305), color=MOLTEN, strength=2.1))
    body.append(bk.glow_block("body.belly", (0.22, 0.4, 0.05),
                              (0, -0.04, 0.285), color=FLARE, strength=1.9))
    body += _cracks("body.crack", body_at, body_dims, count=3, color=EMBER,
                    width=0.03, seed=4)
    body += bk.spots("body.scale", body_at, body_dims, count=4, size=0.06,
                     color=ROCK_LIT, seed=9, faces=("top", "left", "right"))

    head_dims = (0.28, 0.26, 0.2)
    head_at = (0, 0.48, 0.48)
    head = [bk.block("head.skull", head_dims, head_at, color=ROCK)]
    snout_at = (0, 0.66, 0.455)
    snout_dims = (0.2, 0.14, 0.13)
    head.append(bk.block("head.snout", snout_dims, snout_at, color=ROCK_LIT))
    head += bk.nostrils("head.nose", snout_at, snout_dims, spacing=0.44,
                        height=0.02, size=0.03, color=CHAR)
    # Gecko eye turrets: knobs on the skull top, each with a molten iris.
    turret_dims = (0.34, 0.13, 0.11)
    turret_at = (0, 0.5, 0.585)
    for side, sign in (("L", 1), ("R", -1)):
        head.append(bk.block("head.turret." + side, (0.12, 0.13, 0.11),
                             (sign * 0.11, 0.5, 0.585), color=ROCK_LIT))
    head += _glow_eyes("head.eye", turret_at, turret_dims, spacing=0.64,
                       height=0.0, size=0.06, iris=YELLOW, aspect=1.0)
    # The mouth line glows, as though the jaw is never quite shut.
    head.append(bk.glow_block("head.jaw", (0.275, 0.24, 0.024),
                              (0, 0.48, 0.4), color=EMBER, strength=2.3))

    # A fat-based tail that swings out to one side. A straight tail behind a
    # straight body is one long plank; the sideways kink is what makes the
    # silhouette read as a lizard mid-scurry.
    tail_parts = []
    for i in range(5):
        t = (i + 0.5) / 5.0
        s = 0.2 * (1.0 - 0.62 * t)
        tail_parts.append(bk.block(
            "tail.seg%d" % i, (s, 0.125, s * 0.82),
            (0.24 * t * t, -0.36 - t * 0.44, 0.42 + 0.08 * t * t), color=ROCK))
        if i < 3:
            tail_parts.append(bk.glow_block(
                "tail.seam%d" % i, (s * 0.92, 0.045, 0.03),
                (0.24 * t * t, -0.39 - t * 0.44, 0.42 - s * 0.36),
                color=MOLTEN, strength=1.7))
    tail_obj = _weldgroup("tail", tail_parts, (0, -0.34, 0.42))

    # Splayed sticky toes -- the one thing that says "gecko" rather than
    # "small lizard", so they are built by hand instead of using _legs_quad.
    # The shafts are longer than a lizard's really are, on purpose: standing
    # the torso up off the floor is what keeps the profile from being a plank.
    legs = {}
    for tag, (hx, hy) in (("F", (0.2, 0.18)), ("B", (0.21, -0.2))):
        parts = [
            bk.block("leg.%sL.hip" % tag, (0.11, 0.11, 0.1), (hx, hy, 0.37),
                     color=ROCK_LIT),
            bk.block("leg.%sL.shaft" % tag, (0.08, 0.08, 0.26),
                     (hx + 0.07, hy, 0.25), rot=(0, -16, 0), color=ROCK_LIT),
        ]
        for j, spread in enumerate((-30.0, 0.0, 30.0)):
            parts.append(bk.glow_block(
                "leg.%sL.toe%d" % (tag, j), (0.045, 0.13, 0.032),
                (hx + 0.13, hy + 0.03, 0.115), rot=(0, 0, spread),
                color=EMBER, strength=1.3))
        parts.append(bk.block("leg.%sL.pad" % tag, (0.11, 0.09, 0.055),
                              (hx + 0.13, hy - 0.02, 0.12), color=CHAR))
        left = _weldgroup("leg.%sL" % tag, parts, (hx, hy, 0.37))
        legs["leg.%sL" % tag] = left
        legs["leg.%sR" % tag] = _mirror(left, "leg.%sR" % tag)

    groups = {
        "body": (body, (0, 0, 0.3)),
        "head": (head, (0, 0.36, 0.42)),
        "tail": ([tail_obj], (0, -0.34, 0.42)),
    }
    for key, obj in legs.items():
        groups[key] = ([obj], tuple(obj.location))
    bk.assemble(root, groups)
    return bk.finish(root)


# ---------------------------------------------------------------------------
# Lava Frog -- Epic, $850/s.
# All haunches. The silhouette is: hunched obsidian rump at the back, a wide
# low wedge of a head at the front, two eye domes on top, and knees that stand
# higher than the spine. Anything that flattens that stepped profile is wrong.
# ---------------------------------------------------------------------------

def build_lava_frog():
    kit.reset_scene()
    root = kit.empty("root")

    body_dims = (0.5, 0.4, 0.34)
    body_at = (0, -0.18, 0.38)
    body = [bk.block("body.core", body_dims, body_at, color=CHAR)]
    body.append(bk.block("body.back", (0.42, 0.32, 0.09), (0, -0.2, 0.57),
                         color=ROCK_LIT))
    body += _cracks("body.crack", body_at, body_dims, count=4, color=EMBER,
                    width=0.034, seed=7, span=0.72)
    body.append(bk.glow_block("body.spine", (0.055, 0.36, 0.05),
                              (0, -0.2, 0.6), color=MOLTEN, strength=2.2))

    # The head is a separate, wider, LOWER wedge -- the step between it and the
    # rump is the whole frog read.
    head_dims = (0.48, 0.36, 0.22)
    head_at = (0, 0.22, 0.34)
    head = [bk.block("head.skull", head_dims, head_at, color=CHAR)]
    # A mouth that wraps the front and both cheeks, the way a frog's does.
    head.append(bk.glow_block("head.mouth", (0.49, 0.37, 0.024),
                              (0, 0.22, 0.248), color=MOLTEN, strength=2.4))
    head.append(bk.block("head.lip", (0.45, 0.06, 0.055),
                         (0, 0.39, 0.272), color=ROCK_LIT))
    # Throat sac: cooled magma, the one big non-black surface on the pet.
    head.append(bk.block("head.throat", (0.3, 0.2, 0.13), (0, 0.28, 0.19),
                         color=DEEP_RED))
    head.append(bk.glow_block("head.throatglow", (0.22, 0.12, 0.03),
                              (0, 0.3, 0.14), color=EMBER, strength=2.0))
    # Eye domes standing proud of the skull top, read from every angle.
    dome_dims = (0.5, 0.18, 0.18)
    dome_at = (0, 0.2, 0.54)
    for side, sign in (("L", 1), ("R", -1)):
        head.append(bk.block("head.dome." + side, (0.18, 0.18, 0.18),
                             (sign * 0.16, 0.2, 0.54), color=ROCK_LIT))
        head.append(bk.block("head.domecap." + side, (0.13, 0.13, 0.04),
                             (sign * 0.16, 0.2, 0.638), color=CHAR))
    head += _glow_eyes("head.eye", dome_at, dome_dims, spacing=0.64,
                       height=0.0, size=0.09, iris=YELLOW, aspect=0.9)

    # Front legs prop the chest up; the back pair are folded jumping haunches
    # whose knees rise above the spine.
    front = {}
    left = _leg("leg.FL", (0.2, 0.24, 0.3), length=0.26, thickness=0.07,
                color=ROCK, foot_color=EMBER, glow_foot=True, foot_len=0.17,
                strength=1.3, splay=0.2)
    front["leg.FL"] = left
    front["leg.FR"] = _mirror(left, "leg.FR")

    # Folded in a Z, and the joints have to actually meet: hip low and forward,
    # thigh sloping UP and BACK to a knee that stands above the spine, shin
    # dropping steeply forward to an ankle at the floor, then a long flat foot
    # with splayed webbed toes. The first pass left the foot floating a third
    # of a body ahead of the shin, which is what made the haunch read as a wall.
    haunch = [
        bk.block("leg.BL.hip", (0.18, 0.18, 0.17), (0.26, -0.14, 0.44),
                 color=ROCK),
        bk.block("leg.BL.thigh", (0.18, 0.3, 0.2), (0.265, -0.25, 0.53),
                 rot=(-36, 0, 0), color=ROCK),
        bk.glow_block("leg.BL.crack", (0.19, 0.05, 0.13), (0.265, -0.25, 0.53),
                      rot=(-36, 0, 0), color=EMBER, strength=2.1),
        bk.block("leg.BL.knee", (0.17, 0.18, 0.18), (0.27, -0.37, 0.605),
                 color=ROCK_LIT),
        bk.block("leg.BL.shin", (0.115, 0.55, 0.145), (0.27, -0.265, 0.355),
                 rot=(-67, 0, 0), color=ROCK_LIT),
        bk.block("leg.BL.foot", (0.18, 0.3, 0.07), (0.27, -0.08, 0.05),
                 color=CHAR),
    ]
    # The webbed toes have to land BEHIND the front paws. At the first pass's
    # ankle position they overlapped them and the frog grew four feet in a row.
    for j, spread in enumerate((-26.0, 0.0, 26.0)):
        haunch.append(bk.glow_block(
            "leg.BL.toe%d" % j, (0.058, 0.2, 0.05), (0.27, 0.07, 0.05),
            rot=(0, 0, spread), color=MOLTEN, strength=1.5))
    back_left = _weldgroup("leg.BL", haunch, (0.26, -0.14, 0.44))
    back_right = _mirror(back_left, "leg.BR")

    groups = {
        "body": (body, (0, 0, 0.26)),
        "head": (head, (0, 0.06, 0.3)),
        "leg.BL": ([back_left], tuple(back_left.location)),
        "leg.BR": ([back_right], tuple(back_right.location)),
    }
    for key, obj in front.items():
        groups[key] = ([obj], tuple(obj.location))
    bk.assemble(root, groups)
    return bk.finish(root)


# ---------------------------------------------------------------------------
# Flaming Bull -- Legendary, $9.5K/s.
# Mass forward: huge chest, shoulder hump, low heavy head, narrow hips. The
# horns are pale BONE rather than dark stone -- on a black bull they are the
# only thing that survives being shrunk to an icon, so they get the width.
# ---------------------------------------------------------------------------

def build_flaming_bull():
    kit.reset_scene()
    root = kit.empty("root")

    body_dims = (0.44, 0.62, 0.42)
    body_at = (0, -0.14, 0.62)
    body = [bk.block("body.core", body_dims, body_at, color=ROCK)]
    chest_dims = (0.56, 0.36, 0.52)
    chest_at = (0, 0.22, 0.64)
    body.append(bk.block("body.chest", chest_dims, chest_at, color=ROCK))
    body.append(bk.block("body.hump", (0.42, 0.28, 0.16), (0, 0.14, 0.9),
                         color=ROCK_LIT))
    body += _cracks("body.crack", chest_at, chest_dims, count=3, color=EMBER,
                    width=0.036, seed=5, span=0.6)
    body += _cracks("body.rump", body_at, body_dims, count=3, color=EMBER,
                    width=0.032, seed=12, span=0.66)
    body += bk.belly("body.brisket", chest_at, chest_dims, color=DEEP_RED,
                     inset=0.62)
    # Flame mane: licks marching down the spine, plus a fringe over each
    # shoulder, so the fire has volume from the side as well as head-on.
    body += _flames("body.mane", (0, 0.04, 0.98), count=6, spread=0.46,
                    height=0.26, width=0.09, axis="y", lean=-10)
    body += _flames("body.ruff", (0, 0.24, 0.86), count=4, spread=0.44,
                    height=0.15, width=0.075, axis="x", lean=-20)
    body.append(bk.block("body.neck", (0.3, 0.22, 0.3), (0, 0.44, 0.68),
                         color=ROCK_LIT))

    head_dims = (0.34, 0.32, 0.3)
    head_at = (0, 0.66, 0.62)
    head = [bk.block("head.skull", head_dims, head_at, color=ROCK)]
    muzzle_at = (0, 0.88, 0.54)
    muzzle_dims = (0.26, 0.18, 0.18)
    head.append(bk.block("head.muzzle", muzzle_dims, muzzle_at, color=DEEP_RED))
    head += bk.nostrils("head.nose", muzzle_at, muzzle_dims, spacing=0.44,
                        height=-0.01, size=0.048, color=CHAR)
    # Jets of flame off the nostrils -- the snorting signature.
    for side, sign in (("L", 1), ("R", -1)):
        head.append(bk.wedge(
            "head.snort." + side, (0.055, 0.16, 0.055),
            (sign * 0.06, 1.02, 0.53), rot=(-90, 0, 0),
            material=_fire_mat(MOLTEN, 3.0), taper=0.82,
        ))
    head += _glow_eyes("head.eye", head_at, head_dims, spacing=0.62,
                       height=0.05, size=0.07, iris=EMBER)
    head.append(bk.face_plate("head.brow", bk.face_of(head_at, head_dims, "front"),
                              (0.32, 0.07), face="front", color=CHAR,
                              depth=0.032, offset=(0, 0.14)))
    # Horns: three segments per side that actually chain, sweeping OUT nearly
    # horizontally and then hooking up into a burning tip. The sign convention
    # matters -- a positive Y rotation carries a block's +Z end toward +X, so
    # the left horn needs +lean and the right -lean, or the pair grows inward
    # and reads as two grey slabs bolted to the cheeks.
    for side, sign in (("L", 1), ("R", -1)):
        head.append(bk.block("head.hornbase." + side, (0.15, 0.15, 0.13),
                             (sign * 0.16, 0.68, 0.7), color=BONE))
        head.append(bk.block("head.hornmid." + side, (0.115, 0.13, 0.26),
                             (sign * 0.26, 0.7, 0.735),
                             rot=(0, sign * 70, 0), color=BONE))
        head.append(bk.wedge("head.horntip." + side, (0.1, 0.115, 0.28),
                             (sign * 0.436, 0.72, 0.895),
                             rot=(0, sign * 28, 0), color=BONE, taper=0.6))
        head.append(bk.wedge("head.hornfire." + side, (0.09, 0.09, 0.2),
                             (sign * 0.5, 0.73, 1.07), rot=(0, sign * 10, 0),
                             material=_fire_mat(FLARE, 2.8), taper=0.86))
    # Gold nose ring: the small expensive detail that says "legendary".
    head += bk.ring("head.nosering", (0, 0.94, 0.44), radius=0.055,
                    thickness=0.016, tilt=90, color=GOLD, strength=1.2)

    legs = _legs_quad("leg", front=(0.2, 0.24, 0.44), back=(0.18, -0.3, 0.42),
                      length=0.38, thickness=0.135, color=ROCK,
                      foot_color=MOLTEN, glow_foot=True, strength=1.6,
                      foot_len=0.2, back_thickness=0.125)
    tail_obj = bk.tail("tail", (0, -0.44, 0.68), length=0.36, thickness=0.085,
                       color=ROCK, style="whip", segments=4, curl=0.18)
    tail_fire = _flames("tail.fire", (0, -0.82, 0.66), count=3, spread=0.1,
                        height=0.19, width=0.075, axis="y", lean=-30)

    groups = {
        "body": (body, (0, 0, 0.36)),
        "head": (head, (0, 0.5, 0.52)),
        "tail": ([tail_obj] + tail_fire, (0, -0.44, 0.68)),
    }
    for key, obj in legs.items():
        groups[key] = ([obj], tuple(obj.location))
    bk.assemble(root, groups)
    return bk.finish(root)


# ---------------------------------------------------------------------------
# Lava Iguana -- Legendary, $11K/s.
# Deliberately unlike the gecko: taller off the ground, a heavy jowled head on
# a real neck, a swinging dewlap, and one continuous glowing sail from skull to
# tail tip. The sail IS the silhouette; everything else supports it.
# ---------------------------------------------------------------------------

def build_lava_iguana():
    kit.reset_scene()
    root = kit.empty("root")

    body_dims = (0.36, 0.76, 0.32)
    body_at = (0, -0.1, 0.52)
    body = [bk.block("body.core", body_dims, body_at, color=ROCK)]
    body.append(bk.block("body.plate", (0.3, 0.62, 0.08), (0, -0.1, 0.66),
                         color=ROCK_LIT))
    body.append(bk.block("body.neck", (0.26, 0.24, 0.28), (0, 0.36, 0.6),
                         color=ROCK_LIT))
    body += _cracks("body.crack", body_at, body_dims, count=5, color=EMBER,
                    width=0.03, seed=21, span=0.82)
    body += bk.stripes("body.band", body_at, body_dims, count=3, width=0.055,
                       color=DEEP_RED, axis="y")
    # The sail: spine height swells over the shoulders and tapers back.
    for i in range(9):
        t = i / 8.0
        h = 0.1 + 0.17 * math.sin(math.pi * (0.15 + 0.8 * t))
        body.append(bk.wedge(
            "body.sail%d" % i, (0.05, 0.075, h), (0, 0.38 - t * 0.8, 0.68 + h * 0.42),
            material=_fire_mat(MOLTEN if i % 2 else FLARE, 2.6), taper=0.8,
        ))

    head_dims = (0.32, 0.34, 0.3)
    head_at = (0, 0.62, 0.72)
    head = [bk.block("head.skull", head_dims, head_at, color=ROCK)]
    jaw_at = (0, 0.66, 0.55)
    jaw_dims = (0.3, 0.36, 0.12)
    head.append(bk.block("head.jaw", jaw_dims, jaw_at, color=ROCK_LIT))
    head.append(bk.glow_block("head.gape", (0.305, 0.34, 0.032),
                              (0, 0.66, 0.615), color=EMBER, strength=2.4))
    # Dewlap: the throat fan that makes an iguana an iguana. Big enough to be
    # a silhouette element in its own right.
    head.append(bk.block("head.dewlap", (0.16, 0.2, 0.22), (0, 0.62, 0.38),
                         rot=(16, 0, 0), color=DEEP_RED))
    head.append(bk.glow_block("head.dewglow", (0.17, 0.05, 0.16),
                              (0, 0.7, 0.37), rot=(16, 0, 0), color=EMBER,
                              strength=2.0))
    head += _glow_eyes("head.eye", head_at, head_dims, spacing=0.66,
                       height=0.07, size=0.075, iris=YELLOW)
    head += bk.nostrils("head.nose", head_at, head_dims, spacing=0.3,
                        height=-0.03, size=0.032, color=CHAR)
    # Chunky jowl scales along the jawline -- the other iguana tell.
    for side, sign in (("L", 1), ("R", -1)):
        for i in range(3):
            head.append(bk.block(
                "head.scale.%s%d" % (side, i), (0.055, 0.075, 0.075),
                (sign * 0.17, 0.56 + i * 0.09, 0.62), color=ASH))
    head += [bk.wedge("head.sail%d" % i, (0.05, 0.075, 0.14 - 0.025 * i),
                      (0, 0.64 - i * 0.11, 0.9),
                      material=_fire_mat(FLARE, 2.8), taper=0.82)
             for i in range(2)]

    legs = _legs_quad("leg", front=(0.22, 0.26, 0.46), back=(0.23, -0.32, 0.46),
                      length=0.32, thickness=0.1, color=ROCK_LIT,
                      foot_color=EMBER, glow_foot=True, strength=1.3,
                      foot_len=0.21, splay=0.28)

    tail_obj = bk.tail("tail", (0, -0.5, 0.52), length=0.64, thickness=0.17,
                       color=ROCK, style="taper", segments=5, curl=0.22)
    tail_sail = []
    for i in range(4):
        t = i / 3.0
        h = 0.13 - 0.075 * t
        tail_sail.append(bk.wedge(
            "tail.sail%d" % i, (0.042, 0.07, h),
            (0, -0.58 - t * 0.38, 0.55 + t * 0.07 + h * 0.4),
            material=_fire_mat(MOLTEN, 2.5), taper=0.8,
        ))

    groups = {
        "body": (body, (0, 0, 0.36)),
        "head": (head, (0, 0.46, 0.6)),
        "tail": ([tail_obj] + tail_sail, (0, -0.5, 0.52)),
    }
    for key, obj in legs.items():
        groups[key] = ([obj], tuple(obj.location))
    bk.assemble(root, groups)
    return bk.finish(root)


# ---------------------------------------------------------------------------
# Chili Imp -- Mythic, $55K/s. ORIGINAL.
# A furious little devil who IS a chili pepper: a glossy red pod for a torso
# tapering to a curled point, and the pepper's green calyx worn on the skull
# like a cap with the stem standing straight up. Green-on-red is the only
# non-fire colour pair in the biome, which is exactly why it reads as mythic.
#
# Rebuilt after the first pass came out spindly. Three things were wrong and
# all three were proportion, not detail: the pod was narrower than the skull so
# the head appeared to float; the legs were tucked inside the pod's taper and
# vanished entirely; and a $55K pet in a fire biome had almost no fire on it.
# Now the pod is the widest thing on the model, the legs are planted a clear
# pod-width apart, and the pepper is lit from the inside like a lantern.
# ---------------------------------------------------------------------------

def build_chili_imp():
    kit.reset_scene()
    root = kit.empty("root")

    pod = "#cc1a18"
    pod_dark = "#8e0f14"
    stem = "#4aa032"
    stem_dark = "#2f7222"

    # The pod: built upside down and flipped, broad at the shoulders and
    # tapering to a point between the legs. That taper is the whole gag, so it
    # gets the width budget and everything else is hung off it.
    body = [bk.wedge("body.pod", (0.5, 0.44, 0.54), (0, -0.02, 0.5),
                     rot=(180, 0, 0), color=pod, taper=0.5)]
    # Pepper creases: narrow grooves, NOT panels. Big plates on a body this
    # small swallow the taper and it stops being a pepper.
    for dx in (-0.13, 0.0, 0.13):
        body.append(bk.block("body.crease%+0.2f" % dx, (0.032, 0.03, 0.4),
                             (dx, 0.2, 0.56), color=pod_dark))
    # Heat leaks between the creases. Slivers, not slabs -- but wide enough now
    # that the pod reads as a lantern with something burning inside it.
    for dx in (-0.075, 0.075):
        body.append(bk.glow_block("body.seam%+0.2f" % dx, (0.045, 0.06, 0.36),
                                  (dx, 0.18, 0.54), color=EMBER, strength=2.0))
    body.append(bk.glow_block("body.vent", (0.28, 0.05, 0.05), (0, 0.2, 0.32),
                              color=MOLTEN, strength=2.2))
    # The pod's point, curling back between the legs.
    body.append(bk.wedge("body.tip", (0.15, 0.17, 0.2), (0, -0.1, 0.24),
                         rot=(148, 0, 0), color=pod_dark, taper=0.75))
    body.append(bk.block("body.shoulders", (0.5, 0.36, 0.13), (0, -0.01, 0.76),
                         color=pod_dark))
    # A wide, short neck. The first pass used a 0.15 stub and the skull looked
    # like it was hovering an inch above the collar.
    body.append(bk.block("body.neck", (0.24, 0.24, 0.09), (0, 0.0, 0.84),
                         color=pod))
    # Rage tufts off the shoulders: the fire this pet was missing entirely.
    body += _flames("body.rage", (0, -0.1, 0.8), count=3, spread=0.44,
                    height=0.2, width=0.085, axis="x", lean=-18)

    head_dims = (0.36, 0.32, 0.3)
    head_at = (0, 0.03, 1.0)
    head = [bk.block("head.skull", head_dims, head_at, color=pod)]
    # Yellow sclera under a slanted brow: at this size the eyes carry the
    # entire "permanently furious" brief on their own.
    head += bk.eyes("head.eye", head_at, head_dims, spacing=0.56, height=0.05,
                    size=0.09, style="angry", iris="#1a0d10", sclera=YELLOW,
                    pupil_scale=0.5, glint=False)
    head += bk.mouth("head.mouth", head_at, head_dims, width=0.21, height=0.042,
                     drop=-0.1, color="#2a0a0c", style="open", teeth=3,
                     teeth_color="#fff3d0")
    for side, sign in (("L", 1), ("R", -1)):
        head.append(bk.wedge("head.horn." + side, (0.06, 0.06, 0.15),
                             (sign * 0.17, -0.02, 1.13),
                             rot=(0, sign * 34, 0), color=pod_dark, taper=0.85))
    # The calyx cap: a green collar on the crown with four sepals hanging off
    # it, then the stem. This is what makes the whole pet read as a pepper.
    head.append(bk.block("head.cap", (0.34, 0.3, 0.065), (0, 0.03, 1.18),
                         color=stem))
    for i in range(4):
        angle = math.radians(i * 90 + 45)
        head.append(bk.wedge(
            "head.sepal%d" % i, (0.09, 0.09, 0.14),
            (math.sin(angle) * 0.15, 0.03 + math.cos(angle) * 0.14, 1.15),
            rot=(-math.cos(angle) * 34, -math.sin(angle) * 34, 0),
            color=stem_dark, taper=0.75,
        ))
    head.append(bk.block("head.stem", (0.085, 0.085, 0.21), (0, 0.0, 1.31),
                         rot=(-12, 0, 0), color=stem))
    head.append(bk.wedge("head.stemtip", (0.07, 0.07, 0.11), (0, -0.05, 1.45),
                         rot=(-22, 0, 0), color=stem_dark, taper=0.8))

    # Real bat wings, not the nubs of the first pass: dark membrane, molten
    # veins, and long enough to break the pod's outline from behind.
    wing_l, wing_r = _dragon_wing(
        "wing", (0.2, -0.2, 0.8), span=0.36, drop=0.28, rise=34, sweep=0.1,
        web=pod_dark, bone="#5c0a10", vein=MOLTEN, panels=2, strength=0.7,
        thickness=0.034, claw=False)

    arm_l, arm_r = _arm("arm", (0.26, 0.02, 0.74), length=0.24, thickness=0.09,
                        color=pod, hand_color=pod_dark, angle=22)
    # A burning fist on each hand -- the imp is holding its own temper.
    fire_l = bk.wedge("arm.fire.L", (0.09, 0.09, 0.16), (0.34, 0.06, 0.53),
                      rot=(-14, 0, 0), material=_fire_mat(FLARE, 2.8),
                      taper=0.86)
    fire_r = kit.duplicate(fire_l, "arm.fire.R", mirror=True)
    fire_r.location = Vector((-fire_l.location.x, fire_l.location.y,
                              fire_l.location.z))

    # Legs planted a clear pod-width apart so they sit outside the taper and
    # are actually visible; clawed, with the claws lit.
    legs = {}
    parts = [
        bk.block("leg.FL.thigh", (0.115, 0.13, 0.2), (0.19, 0.0, 0.42),
                 color=pod_dark),
        bk.block("leg.FL.shin", (0.095, 0.1, 0.22), (0.2, 0.0, 0.22),
                 color=pod_dark),
        bk.block("leg.FL.foot", (0.12, 0.19, 0.07), (0.2, 0.04, 0.08),
                 color="#5c0a10"),
    ]
    for j, spread in enumerate((-24.0, 0.0, 24.0)):
        parts.append(bk.glow_block(
            "leg.FL.claw%d" % j, (0.035, 0.1, 0.035), (0.2, 0.15, 0.07),
            rot=(0, 0, spread), color=FLARE, strength=1.8))
    left_leg = _weldgroup("leg.FL", parts, (0.19, 0.0, 0.48))
    legs["leg.FL"] = left_leg
    legs["leg.FR"] = _mirror(left_leg, "leg.FR")

    tail_obj = bk.tail("tail", (0, -0.2, 0.44), length=0.32, thickness=0.06,
                       color=pod_dark, style="whip", segments=4, curl=0.55)
    tail_tip = bk.wedge("tail.spade", (0.13, 0.04, 0.16), (0, -0.5, 0.63),
                        rot=(-72, 0, 0), material=_fire_mat(MOLTEN, 3.0),
                        taper=0.62)

    groups = {
        "body": (body, (0, 0, 0.24)),
        "head": (head, (0, -0.02, 0.86)),
        "wing.L": ([wing_l], tuple(wing_l.location)),
        "wing.R": ([wing_r], tuple(wing_r.location)),
        "arm.L": ([arm_l, fire_l], tuple(arm_l.location)),
        "arm.R": ([arm_r, fire_r], tuple(arm_r.location)),
        "tail": ([tail_obj, tail_tip], (0, -0.2, 0.44)),
    }
    for key, obj in legs.items():
        groups[key] = ([obj], tuple(obj.location))
    bk.assemble(root, groups)
    return bk.finish(root)


# ---------------------------------------------------------------------------
# Cerberus -- Secret, $8M/s.
# Three heads on one body. The centre head takes the "head" slot; the flanking
# pair take "ear.L"/"ear.R" so the animator's ear-flop drives them -- three
# heads lagging behind the body is exactly the motion this wants.
#
# The failure mode is the heads merging into one wide mass, so the side pair
# sit a head-width out, a head-height down, and yawed outward, and each keeps
# its own fire collar to separate it from its neighbour.
# ---------------------------------------------------------------------------

def _cerberus_head(prefix, at, dims, outward=0.0, scale=1.0):
    """One hound head: skull, muzzle, glowing eyes, fire collar, small horns."""
    # The skull stays axis-aligned so its face decals sit flat; only the muzzle
    # is yawed, which is enough to point each head away from its neighbour.
    parts = [bk.block(prefix + ".skull", dims, at, color=CHAR)]
    yaw = math.radians(outward)
    # Long muzzles, pushed well clear of the skull. Three short snouts side by
    # side blur into one lump; three long ones read as three animals.
    muzzle_dims = (dims[0] * 0.6, dims[1] * 0.95, dims[2] * 0.44)
    reach = dims[1] * 0.82
    muzzle_at = (at[0] + math.sin(yaw) * reach,
                 at[1] + math.cos(yaw) * reach,
                 at[2] - dims[2] * 0.24)
    parts.append(bk.block(prefix + ".muzzle", muzzle_dims, muzzle_at,
                          rot=(0, 0, -outward), color=ROCK))
    parts.append(bk.glow_block(
        prefix + ".gape", (muzzle_dims[0] * 0.9, muzzle_dims[1] * 0.94, 0.028),
        (muzzle_at[0], muzzle_at[1], muzzle_at[2] - muzzle_dims[2] * 0.2),
        rot=(0, 0, -outward), color=MOLTEN, strength=2.6))
    parts += bk.nostrils(prefix + ".nose", muzzle_at, muzzle_dims, spacing=0.4,
                         height=0.035, size=0.03 * scale, color=CHAR)
    for i in range(3):
        t = (i + 0.5) / 3
        parts.append(bk.block(
            "%s.tooth%d" % (prefix, i),
            (muzzle_dims[0] * 0.17, 0.022, 0.04 * scale),
            (muzzle_at[0] + math.cos(yaw) * muzzle_dims[0] * (t - 0.5) * 0.8,
             muzzle_at[1] + muzzle_dims[1] * 0.44,
             muzzle_at[2] - muzzle_dims[2] * 0.32),
            rot=(0, 0, -outward), color="#f2e6cf"))
    parts += _glow_eyes(prefix + ".eye", at, dims, spacing=0.58,
                        height=0.05 * scale, size=0.062 * scale, iris=EMBER)
    parts.append(bk.wedge(prefix + ".earL", (0.05, 0.05, 0.12 * scale),
                          (at[0] + dims[0] * 0.34, at[1] - dims[1] * 0.24,
                           at[2] + dims[2] * 0.58),
                          rot=(0, -20, 0), color=ROCK, taper=0.8))
    parts.append(bk.wedge(prefix + ".earR", (0.05, 0.05, 0.12 * scale),
                          (at[0] - dims[0] * 0.34, at[1] - dims[1] * 0.24,
                           at[2] + dims[2] * 0.58),
                          rot=(0, 20, 0), color=ROCK, taper=0.8))
    # Collar tuft count scales with the head. Nine tufts on all three heads
    # merged into one wall of orange behind the skulls; the outer heads get a
    # sparser, shorter ruff so each face keeps its own frame.
    parts += _fire_collar(prefix + ".mane", at, dims, ring=0.11 * scale,
                          thickness=(0.095 if scale >= 1.0 else 0.075) * scale,
                          count=9 if scale >= 1.0 else 6, back=0.62,
                          strength=2.6 if scale >= 1.0 else 2.2)
    return parts


def build_cerberus():
    kit.reset_scene()
    root = kit.empty("root")

    body_dims = (0.6, 0.74, 0.5)
    body_at = (0, -0.28, 0.74)
    body = [bk.block("body.core", body_dims, body_at, color=CHAR)]
    chest_dims = (0.78, 0.42, 0.58)
    chest_at = (0, 0.18, 0.8)
    body.append(bk.block("body.chest", chest_dims, chest_at, color=CHAR))
    # A gold slave-collar across the shoulders: the one expensive-looking,
    # non-fire material on the pet, and the thing that says "secret" at icon
    # size when the three skulls have blurred into one mass.
    # It has to stand PROUD of the chest on every axis or it does not exist in
    # the render -- but a bright band that tall also reads as a saddle blanket,
    # so the strap itself is a dark bronze and only the studs are gold.
    body.append(bk.block("body.collar", (0.84, 0.13, 0.64), (0, 0.34, 0.84),
                         color="#3c2f14"))
    for i in range(6):
        angle = (i / 6.0) * 2 * math.pi
        body.append(bk.wedge(
            "body.spike%d" % i, (0.075, 0.075, 0.15),
            (math.sin(angle) * 0.45, 0.36, 0.84 + math.cos(angle) * 0.35),
            rot=(0, math.degrees(angle), 0),
            material=_fire_mat(GOLD, 1.7), taper=0.8))
    body += _cracks("body.crack", body_at, body_dims, count=5, color=EMBER,
                    width=0.036, seed=13, span=0.8)
    body += _cracks("body.chestcrack", chest_at, chest_dims, count=2,
                    color=MOLTEN, width=0.038, seed=31, span=0.5)
    body += bk.belly("body.brisket", chest_at, chest_dims, color=DEEP_RED,
                     inset=0.58)
    # A fire spine across the shoulders ties the three necks into one animal.
    # The hip fire sits BEHIND the shoulders so it never competes with the
    # three collars for the eye.
    body += _flames("body.spine", (0, -0.34, 1.0), count=4, spread=0.34,
                    height=0.18, width=0.08, axis="y", lean=-12)
    # Three necks off one set of shoulders: the centre one climbs, the outer
    # pair reach out sideways. That spread is what stops the skulls merging.
    body.append(bk.block("body.neck.C", (0.24, 0.34, 0.36), (0, 0.4, 1.06),
                         rot=(-30, 0, 0), color=ROCK))
    # The side necks reach a long way OUT as well as forward. At the first
    # pass's 0.28 they started inside the chest and the outer skulls sat on
    # the shoulders, so the three heads fused into one lump; a full skull-width
    # of clear air between each pair is what separates them.
    # The outer necks climb as well as splay: heads level with the shoulder
    # line rather than tucked down beside the ribs, so the three skulls make a
    # triangle instead of a row of lumps against the chest.
    for tag, sign in (("L", 1), ("R", -1)):
        body.append(bk.block("body.neck." + tag, (0.23, 0.58, 0.25),
                             (sign * 0.42, 0.6, 0.98),
                             rot=(-6, 0, -sign * 38), color=ROCK))

    head = _cerberus_head("head", (0, 0.84, 1.4), (0.31, 0.31, 0.31))
    left_head = _cerberus_head("ear.L", (0.6, 0.9, 1.0), (0.28, 0.28, 0.28),
                               outward=42, scale=0.9)
    right_head = _cerberus_head("ear.R", (-0.6, 0.9, 1.0), (0.28, 0.28, 0.28),
                                outward=-42, scale=0.9)

    legs = _legs_quad("leg", front=(0.26, 0.24, 0.54), back=(0.24, -0.44, 0.52),
                      length=0.48, thickness=0.15, color=ROCK,
                      foot_color=EMBER, glow_foot=True, strength=1.4,
                      foot_len=0.23, back_thickness=0.14)

    tail_obj = bk.tail("tail", (0, -0.58, 0.8), length=0.44, thickness=0.13,
                       color=CHAR, style="spike", segments=4, curl=0.35,
                       tip_color=ROCK)
    tail_fire = _flames("tail.fire", (0, -0.92, 0.92), count=3, spread=0.14,
                        height=0.18, width=0.075, axis="y", lean=-20)

    groups = {
        "body": (body, (0, 0, 0.42)),
        "head": (head, (0, 0.62, 1.18)),
        "ear.L": (left_head, (0.3, 0.44, 0.96)),
        "ear.R": (right_head, (-0.3, 0.44, 0.96)),
        "tail": ([tail_obj] + tail_fire, (0, -0.58, 0.8)),
    }
    for key, obj in legs.items():
        groups[key] = ([obj], tuple(obj.location))
    bk.assemble(root, groups)
    return bk.finish(root)


# ---------------------------------------------------------------------------
# Phoenix -- Eternal, $85M/s.
# Everything is the tail: a seven-feather fan taller than the bird itself. The
# discipline here is tonal -- crimson at the roots, gold in the middle, yellow
# only at the tips. All-yellow at high emission clips to a flat white blob and
# loses every edge, which is exactly what the first pass did.
# ---------------------------------------------------------------------------

def build_phoenix():
    kit.reset_scene()
    root = kit.empty("root")

    # An eternal must not have a dull core. The first pass painted the torso
    # crimson so the gold plumage would pop off it, and the bird came out
    # brown; the fix is to make the BODY the gold and let crimson survive only
    # as the shadow line under the breast.
    body_dims = (0.32, 0.34, 0.44)
    body_at = (0, 0.02, 0.64)
    body = [bk.block("body.core", body_dims, body_at, color=GOLD)]
    body.append(bk.block("body.mantle", (0.33, 0.24, 0.22), (0, 0.0, 0.79),
                         color=FLARE))
    body.append(bk.glow_block("body.breast", (0.24, 0.07, 0.3),
                              (0, 0.2, 0.62), color=FLARE, strength=1.15))
    body.append(bk.glow_block("body.heart", (0.11, 0.1, 0.11), (0, 0.16, 0.66),
                              color=YELLOW, strength=2.8))
    body.append(bk.block("body.shadow", (0.3, 0.1, 0.12), (0, 0.12, 0.44),
                         color=CRIMSON))
    body.append(bk.block("body.rump", (0.28, 0.22, 0.28), (0, -0.17, 0.6),
                         color=MOLTEN))
    # Shoulder ruff -- short upward feathers where the wings meet the body.
    body += _flames("body.ruff", (0, 0.02, 0.86), count=5, spread=0.28,
                    height=0.13, width=0.07, axis="x",
                    colors=(FLARE, GOLD, MOLTEN), strength=2.2)
    # A crimson ruff at the throat. Without it the gold torso runs straight
    # into the gold crown and the head has no edge to be found by.
    body.append(bk.block("body.throat", (0.27, 0.2, 0.1), (0, 0.11, 0.89),
                         color=CRIMSON))

    head_dims = (0.25, 0.24, 0.25)
    head_at = (0, 0.15, 1.02)
    # A crimson skull under a gold crown. Painting the head gold like the body
    # made the bird one continuous lump of the same value; the darker face is
    # what lets the eyes and beak be found at all.
    head = [bk.block("head.skull", head_dims, head_at, color=CRIMSON)]
    head.append(bk.block("head.crown", (0.26, 0.19, 0.09), (0, 0.13, 1.12),
                         color=GOLD))
    head.append(bk.block("head.cheek", (0.27, 0.1, 0.09), (0, 0.16, 0.95),
                         color=MOLTEN))
    head += _glow_eyes("head.eye", head_at, head_dims, spacing=0.62,
                       height=0.03, size=0.055, iris="#fff6d0", socket=CRIMSON,
                       strength=2.6, aspect=1.0)
    # A big pale-gold beak. The first pass used a dark brown one that simply
    # disappeared against the crimson face at any distance.
    head += bk.beak("head.beak", head_at, head_dims, width=0.105, length=0.23,
                    height=0.1, color="#ffd873", drop=-0.08, taper=0.7)
    # Crest: three rising flame feathers, tallest in the middle.
    for i, (dy, h, col) in enumerate(((0.05, 0.15, YELLOW), (-0.03, 0.22, FLARE),
                                      (-0.11, 0.14, MOLTEN))):
        head.append(bk.wedge(
            "head.crest%d" % i, (0.055, 0.08, h),
            (0, head_at[1] + dy, 1.12 + h * 0.4), rot=(-14, 0, 0),
            material=_fire_mat(col, 2.6), taper=0.85,
        ))

    # Broad plumes, not spikes: each feather is nearly as deep as it is long,
    # so the five overlap into one wing with a scalloped trailing edge.
    # The wings are painted a full tone DOWN from the body -- crimson roots
    # into molten -- so the gold torso reads in front of them and the yellow
    # tail fan reads behind. Three values, three shapes; a phoenix painted all
    # one gold is a single bright blob at icon size.
    # Raised, not outstretched: every feather sits above the horizontal so the
    # pair make a heraldic V. Wings held out flat read as arms.
    wing_l, wing_r = _plume_wing("wing", (0.17, 0.02, 0.8), count=4,
                                 length=0.54, root_color=CRIMSON,
                                 colors=(CRIMSON, "#e0480c", MOLTEN, FLARE),
                                 pitch=(-38.0, 4.0), yaw=(8.0, -72.0),
                                 strength=1.0, width=0.18, coverts=2)

    # The fan: feathers radiating from one base, sweeping up and back, the
    # outer pair yawed sideways so the fan has width as well as height.
    base = (0, -0.28, 0.66)
    fan = [bk.block("tail.stub", (0.15, 0.13, 0.15), base, color=CRIMSON)]
    colors = (FLARE, MOLTEN, GOLD, YELLOW, GOLD, MOLTEN, FLARE)
    for i in range(7):
        t = i / 6.0
        pitch = -78 + 86 * t                 # -78 = straight up and back
        yaw = (t - 0.5) * 58
        length = 0.72 - 0.22 * abs(t - 0.5) * 2
        ax, az = math.radians(pitch), math.radians(yaw)
        half = length * 0.5
        loc = (base[0] + half * math.sin(az) * math.cos(ax),
               base[1] - half * math.cos(az) * math.cos(ax),
               base[2] - half * math.sin(ax))
        fan.append(bk.glow_block(
            "tail.feather%d" % i, (0.075, length, 0.038), loc,
            rot=(pitch, 0, yaw), color=colors[i], strength=1.3,
        ))
        # A hotter eye-spot near each feather's tip.
        tip = (base[0] + half * 1.74 * math.sin(az) * math.cos(ax),
               base[1] - half * 1.74 * math.cos(az) * math.cos(ax),
               base[2] - half * 1.74 * math.sin(ax))
        fan.append(bk.glow_block("tail.eye%d" % i, (0.09, 0.09, 0.05), tip,
                                 rot=(pitch, 0, yaw), color=YELLOW,
                                 strength=2.8))

    # Long bright talons. A phoenix standing on two invisible stubs looks like
    # it is sitting in a bush; the legs are part of the expensive read.
    legs = bk.bird_feet("leg", (0.11, 0.04, 0.44), shin=0.3, thickness=0.06,
                        toe=0.19, color="#ffb43a")

    groups = {
        "body": (body, (0, 0, 0.44)),
        "head": (head, (0, 0.08, 0.88)),
        "wing.L": ([wing_l], tuple(wing_l.location)),
        "wing.R": ([wing_r], tuple(wing_r.location)),
        "tail": (fan, base),
    }
    for key, obj in legs.items():
        groups[key] = ([obj], tuple(obj.location))
    bk.assemble(root, groups)
    return bk.finish(root)


# ---------------------------------------------------------------------------
# Lava Dragon -- Eternal, $100M/s.
# The roster's showpiece. Two things were wrong with the first pass and both
# are about mass: the neck climbed almost vertically, so after height
# normalisation the torso was a quarter of the model and the beast read as a
# thin black tower; and the wing membranes burned at full strength, which made
# them shadeless orange boards.
#
# So: the neck reaches FORWARD rather than up, putting the skull out over the
# front feet like something about to bite; the torso, limbs and tail are all
# thickened; and the wings come from the rebuilt `_dragon_wing`, dark webs with
# molten veins. Budget runs high here on purpose, but it stays under 6000.
# ---------------------------------------------------------------------------

def build_lava_dragon():
    kit.reset_scene()
    root = kit.empty("root")

    body_dims = (0.54, 0.9, 0.5)
    body_at = (0, -0.22, 0.74)
    body = [bk.block("body.core", body_dims, body_at, color=CHAR)]
    body.append(bk.block("body.chest", (0.64, 0.42, 0.58), (0, 0.26, 0.78),
                         color=CHAR))
    body += _cracks("body.crack", body_at, body_dims, count=3, color=EMBER,
                    width=0.046, seed=17, span=0.8)
    # Belly scutes: a ladder of cooled plates with one unbroken molten line
    # running between them from throat to vent.
    for i in range(3):
        body.append(bk.block("body.scute%d" % i, (0.36, 0.19, 0.055),
                             (0, 0.1 - i * 0.26, 0.5), color=ROCK_LIT))
    body.append(bk.glow_block("body.gut", (0.3, 0.74, 0.045), (0, -0.18, 0.505),
                              color=MOLTEN, strength=1.9))
    # The neck: four blocks arcing UP then OUT, so the skull ends up ahead of
    # the shoulders rather than above them.
    for i, (y, z, s) in enumerate(((0.4, 0.92, 0.3), (0.54, 1.04, 0.28),
                                   (0.68, 1.14, 0.26), (0.8, 1.22, 0.24))):
        body.append(bk.block("body.neck%d" % i, (s, 0.26, s), (0, y, z),
                             rot=(-52, 0, 0), color=ROCK))
        body.append(bk.glow_block("body.throat%d" % i, (s * 0.55, 0.12, 0.05),
                                  (0, y + 0.06, z - s * 0.48), color=FLARE,
                                  strength=2.2))
    # Dorsal spines, shoulders to hips.
    for i in range(4):
        t = i / 3.0
        h = 0.15 + 0.19 * math.sin(math.pi * (0.2 + 0.75 * t))
        body.append(bk.wedge(
            "body.spine%d" % i, (0.07, 0.11, h),
            (0, 0.3 - t * 0.94, 0.99 + h * 0.42), rot=(-14, 0, 0),
            color=ROCK_LIT, taper=0.82))
    body.append(bk.glow_block("body.spineseam", (0.085, 0.98, 0.055),
                              (0, -0.18, 0.995), color=EMBER, strength=2.0))

    head_dims = (0.34, 0.32, 0.32)
    head_at = (0, 0.98, 1.34)
    head = [bk.block("head.skull", head_dims, head_at, color=CHAR)]
    snout_at = (0, 1.25, 1.28)
    snout_dims = (0.27, 0.3, 0.19)
    head.append(bk.block("head.snout", snout_dims, snout_at, color=ROCK))
    head.append(bk.block("head.jaw", (0.24, 0.31, 0.09), (0, 1.24, 1.155),
                         rot=(6, 0, 0), color=ROCK_LIT))
    # The throat is lit from inside, so the gape is the hottest colour on the
    # pet -- it is the "glowing throat" the brief asks for, seen head-on.
    head.append(bk.glow_block("head.gape", (0.235, 0.3, 0.04),
                              (0, 1.24, 1.207), color=YELLOW, strength=2.6))
    for i in (0, 1):
        head.append(bk.block("head.tooth%d" % i, (0.036, 0.03, 0.06),
                             (snout_dims[0] * (i - 0.5) * 0.5, 1.37, 1.196),
                             color="#f4e8d2"))
    head += bk.nostrils("head.nose", snout_at, snout_dims, spacing=0.42,
                        height=0.05, size=0.042, color=CHAR)
    head += _glow_eyes("head.eye", head_at, head_dims, spacing=0.66,
                       height=0.05, size=0.08, iris=YELLOW, strength=3.0)
    head.append(bk.face_plate("head.brow", bk.face_of(head_at, head_dims, "front"),
                              (0.35, 0.07), face="front", color=ROCK_LIT,
                              depth=0.034, offset=(0, 0.145)))
    # Horns swept back over the neck, plus a cheek spike and a jaw ember.
    for side, sign in (("L", 1), ("R", -1)):
        head.append(bk.block("head.hornbase." + side, (0.09, 0.09, 0.1),
                             (sign * 0.14, 0.92, 1.5), color=ASH))
        head.append(bk.wedge("head.horn." + side, (0.08, 0.09, 0.38),
                             (sign * 0.17, 0.76, 1.58), rot=(58, -sign * 16, 0),
                             color=ASH, taper=0.84))
        head.append(bk.glow_block("head.cheek." + side, (0.05, 0.18, 0.05),
                                  (sign * 0.172, 1.0, 1.3), color=EMBER,
                                  strength=2.1))

    # The wings carry the whole "massive" read, so they get a span wider than
    # the animal is long and enough sweep that the tips reach past the hips.
    wing_l, wing_r = _dragon_wing("wing", (0.29, 0.0, 0.98), span=1.2,
                                  drop=0.86, rise=27, sweep=0.5, web=DEEP_RED,
                                  bone=ROCK_LIT, vein=MOLTEN, panels=3,
                                  strength=0.5, thickness=0.055)

    legs = _legs_quad("leg", front=(0.28, 0.3, 0.58), back=(0.3, -0.44, 0.58),
                      length=0.52, thickness=0.17, color=ROCK,
                      foot_color=EMBER, glow_foot=True, strength=1.4,
                      foot_len=0.27, back_thickness=0.19)

    tail_obj = bk.tail("tail", (0, -0.68, 0.74), length=0.94, thickness=0.24,
                       color=CHAR, style="taper", segments=5, curl=0.16)
    tail_extra = [bk.glow_block("tail.seam", (0.21, 0.96, 0.055),
                                (0, -1.06, 0.76), color=MOLTEN, strength=2.0)]
    for i in (0, 1):
        t = float(i)
        tail_extra.append(bk.wedge(
            "tail.spine%d" % i, (0.065, 0.09, 0.18 - 0.04 * i),
            (0, -0.84 - t * 0.5, 0.87 + t * 0.03), rot=(-18, 0, 0),
            color=ROCK_LIT, taper=0.82))
    # Tail blade: a burning spade rather than a taper, so the far end of the
    # longest part of the animal still carries at icon size.
    tail_extra.append(bk.wedge(
        "tail.blade", (0.2, 0.05, 0.34), (0, -1.62, 0.94), rot=(-96, 0, 0),
        material=_fire_mat(MOLTEN, 2.4), taper=0.7))
    tail_extra += _flames("tail.ember", (0, -1.5, 0.9), count=2, spread=0.12,
                          height=0.18, width=0.075, axis="y", lean=-60)

    groups = {
        "body": (body, (0, 0, 0.4)),
        "head": (head, (0, 0.84, 1.2)),
        "wing.L": ([wing_l], tuple(wing_l.location)),
        "wing.R": ([wing_r], tuple(wing_r.location)),
        "tail": ([tail_obj] + tail_extra, (0, -0.68, 0.74)),
    }
    for key, obj in legs.items():
        groups[key] = ([obj], tuple(obj.location))
    bk.assemble(root, groups)
    return bk.finish(root)


PETS = {
    "lava-gecko": build_lava_gecko,
    "lava-frog": build_lava_frog,
    "flaming-bull": build_flaming_bull,
    "lava-iguana": build_lava_iguana,
    "chili-imp": build_chili_imp,
    "cerberus": build_cerberus,
    "phoenix": build_phoenix,
    "lava-dragon": build_lava_dragon,
}
