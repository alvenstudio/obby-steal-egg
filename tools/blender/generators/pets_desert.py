"""
Ashfang Dunes -- the eight desert pets.

Palette discipline for this biome: sand gold and dusty ochre carry the commons,
bleached bone does the highlights, terracotta does the shadow work, and
turquoise is *rationed* -- it only appears from Epic upward, so a player can
read rarity off the colour before they read the label.

Silhouette notes, since these eight have to be told apart at 24px:
    jerboa        two wide-set dish ears over a thumb-sized body, arcing tail
    fennec        a low quadruped that is mostly ears
    camel         stilt legs, forward-raked neck, two clearly separated humps
    dustpiper     long low sprinter, ground-eating legs, streaming scarf
    snake         banded coils under a flared hood, head thrust well forward
    sand-spider   heavy raised abdomen, knees above the back, splayed legs
    scorpion      the arch is the whole read -- stinger poised over the head
    royal-sphinx  lion mass under a hard flared nemes headdress

Two things learned the hard way while iterating on this set, worth keeping:

  * A ring of same-coloured boxes fuses into a solid drum. The snake's coils
    only read as coils because consecutive blocks alternate shade -- the
    banding, not the geometry, is what says "snake".
  * Thin dark limbs on a small body read as scaffolding, not legs. The spider's
    legs are deliberately thick and close to the body's own colour.

Conventions inherited from pets_forest: build facing +Y, feet near z=0, group
under the runtime's animation names, and pivot every part at its real joint.
"""

import math

import blockkit as bk
import kit


# ---------------------------------------------------------------------------
# shared helpers
# ---------------------------------------------------------------------------

def _segment(name, start, theta, phi, length, thick, color, taper=0.0):
    """
    One straight limb segment aimed out of `start` by spherical angles.

    theta -- tilt away from +Z, phi -- yaw from +X toward +Y (both degrees).
    Blender's XYZ euler applies Rz(Ry(v)), so rot=(0, theta, phi) points a
    Z-long box exactly along that direction. Returns (block, end_point) so
    segments chain knee-to-ankle without re-deriving the trigonometry.

    `taper` narrows the far end. A uniform-width limb box reads as a table
    leg no matter how it is angled; the taper is what makes eight of them
    read as an arthropod instead of furniture, and it costs nothing.
    """
    th, ph = math.radians(theta), math.radians(phi)
    d = (math.sin(th) * math.cos(ph), math.sin(th) * math.sin(ph), math.cos(th))
    mid = tuple(start[i] + d[i] * length * 0.5 for i in range(3))
    end = tuple(start[i] + d[i] * length for i in range(3))
    if taper > 0:
        obj = bk.wedge(name, (thick, thick, length), mid, rot=(0, theta, phi),
                       color=color, taper=taper)
    else:
        obj = bk.block(name, (thick, thick, length), mid, rot=(0, theta, phi),
                       color=color)
    return obj, end


def _mirror_group(parts, name, pivot):
    """
    Weld `parts` (built on the +X side) into one mesh, then produce its -X twin.

    Returns (left, right) with origins on the joint. This is how the arthropods
    fold eight legs into the animator's four leg slots: two adjacent legs are
    welded into one slot, which still walks convincingly and costs four
    transforms instead of eight.
    """
    left = kit.join(parts, name + ".L")
    kit.weld(left)
    kit.set_origin_to(left, pivot)
    right = kit.duplicate(left, name + ".R", mirror=True)
    right.location = kit.Vector((-left.location.x, left.location.y,
                                 left.location.z))
    return left, right


def _arc_tail(name, base, back, rise, segments=5, thick=(0.12, 0.06),
              colors=("#c69a58",), power=1.7, overlap=1.4):
    """
    A tail laid along a smooth arc sweeping back (-Y) and up or down (+/-Z).

    blockkit's `tail()` places each segment at a sampled point but leaves every
    block axis-aligned, so a strongly curled tail visibly comes apart into a
    chain of floating cubes at the tip. Here each block spans the gap between
    consecutive samples and is tilted onto the tangent -- a box whose local +Z
    is rotated by theta about X points along (-sin, cos), hence atan2(-dy, dz).

    Returns (parts, end_point, end_direction) so a tuft can be hung on the tip
    without guessing where the tip ended up.
    """
    parts = []
    prev = base
    dy = dz = 0.0
    for i in range(segments):
        u = (i + 1) / float(segments)
        nxt = (base[0], base[1] - back * u, base[2] + rise * (u ** power))
        dy, dz = nxt[1] - prev[1], nxt[2] - prev[2]
        span = max(math.hypot(dy, dz), 1e-4)
        s = thick[0] + (thick[1] - thick[0]) * (i / max(1.0, segments - 1.0))
        parts.append(bk.block(
            "%s.%d" % (name, i), (s, s, span * overlap),
            ((prev[0] + nxt[0]) * 0.5, (prev[1] + nxt[1]) * 0.5,
             (prev[2] + nxt[2]) * 0.5),
            rot=(math.degrees(math.atan2(-dy, dz)), 0, 0),
            color=colors[i % len(colors)],
        ))
        prev = nxt
    span = max(math.hypot(dy, dz), 1e-4)
    return parts, prev, (dy / span, dz / span)


def _coil(name, center, radius, count, size, colors, length=1.3, phase=0.0):
    """
    A closed ring of tangentially aligned boxes, shaded in alternating bands.

    Position at angle a is (sin a, cos a) * r and the tangent there is
    (cos a, -sin a), so a box whose long axis starts on +X wants rot Z = -a.
    `colors` cycles per block; that alternation is the only thing keeping the
    ring from fusing into a featureless drum.
    """
    parts = []
    for i in range(count):
        a = phase + (i / count) * math.tau
        parts.append(bk.block(
            "%s.%d" % (name, i), (size * length, size, size),
            (center[0] + math.sin(a) * radius,
             center[1] + math.cos(a) * radius, center[2]),
            rot=(0, 0, -math.degrees(a)), color=colors[i % len(colors)],
        ))
    return parts


# ---------------------------------------------------------------------------
# Jerboa -- Common, $6/s.
# A thimble of a body between two dish ears, balanced on spring legs. The ears
# are set wide apart on purpose: butted together they weld into one flat panel
# and the whole read collapses into "rabbit".
# ---------------------------------------------------------------------------

def build_jerboa():
    kit.reset_scene()
    root = kit.empty("root")

    sand = "#e7c489"
    cream = "#fcf2dc"
    ochre = "#c69a58"
    inner = "#dfa08c"
    dark = "#33261d"

    body_dims = (0.26, 0.26, 0.26)
    body_at = (0, -0.02, 0.42)
    body = [bk.block("body.core", body_dims, body_at, color=sand)]
    body += bk.belly("body.chest", body_at, body_dims, color=cream, inset=0.76)
    # A wider haunch under the torso -- gives the little body a pear taper and
    # visually roots the oversized hind legs.
    body.append(bk.block("body.haunch", (0.28, 0.22, 0.14), (0, -0.05, 0.31),
                         color=sand))
    body.append(bk.block("body.saddle", (0.2, 0.16, 0.05),
                         (0, -0.06, body_at[2] + 0.12), color=ochre))

    head_dims = (0.24, 0.2, 0.2)
    head_at = (0, 0.12, 0.65)
    head = [bk.block("head.skull", head_dims, head_at, color=sand)]
    head += bk.snout("head.snout", head_at, head_dims, width=0.11, length=0.09,
                     height=0.08, color=cream, drop=-0.04, nose_color=dark)
    head += bk.eyes("head.eye", head_at, head_dims, spacing=0.52, height=0.03,
                    size=0.08, style="dot", iris=dark)
    for side, sign in (("L", 1), ("R", -1)):
        for i, (dz, yaw) in enumerate(((0.005, 8), (-0.03, -10))):
            head.append(bk.block(
                "head.whisker.%s%d" % (side, i), (0.15, 0.012, 0.012),
                (sign * 0.15, head_at[1] + 0.07, head_at[2] - 0.05 + dz),
                rot=(0, 0, sign * yaw), color=cream,
            ))

    # spacing 0.95 puts the ear centres 0.11 out, leaving a clear gap of sky
    # between two 0.16-wide ears. Anything tighter and they merge.
    ear_l, ear_r = bk.ears_long("ear", head_at, head_dims, size=0.16,
                                spacing=0.95, length=0.34, color=sand,
                                inner_color=inner, lean=-9)

    arm_l, arm_r = bk.arms("arm", (0.11, 0.07, 0.47), length=0.13,
                           thickness=0.05, color=sand, hand_color=cream,
                           angle=24)
    legs = bk.legs_pair("leg", (0.09, -0.03, 0.31), length=0.29, thickness=0.095,
                        color=sand, foot_color=cream, foot_length=0.23)

    # The tail arcs high behind the hops instead of trailing flat, and the
    # black-and-white tuft is hung off the returned tip so it stays attached.
    tail_at = (0, -0.15, 0.45)
    tail_parts, tip, direction = _arc_tail(
        "tail", tail_at, back=0.48, rise=0.26, segments=5,
        thick=(0.115, 0.065), colors=(ochre, sand), power=1.9)
    tail_parts.append(bk.block(
        "tail.tuft.dark", (0.11, 0.11, 0.11),
        (0, tip[1] + direction[0] * 0.05, tip[2] + direction[1] * 0.05),
        color=dark))
    tail_parts.append(bk.block(
        "tail.tuft.pale", (0.13, 0.13, 0.13),
        (0, tip[1] + direction[0] * 0.15, tip[2] + direction[1] * 0.15),
        color=cream))

    groups = {
        "body": (body, (0, 0, 0.28)),
        "head": (head, (0, 0.05, 0.56)),
        "ear.L": ([ear_l], tuple(ear_l.location)),
        "ear.R": ([ear_r], tuple(ear_r.location)),
        "arm.L": ([arm_l], tuple(arm_l.location)),
        "arm.R": ([arm_r], tuple(arm_r.location)),
        "tail": (tail_parts, tail_at),
    }
    for key, obj in legs.items():
        groups[key] = ([obj], tuple(obj.location))
    bk.assemble(root, groups)
    return bk.finish(root)


# ---------------------------------------------------------------------------
# Fennec -- Uncommon, $18/s.
# Cream fox. The brief is "ears bigger than its head", so each ear spire is
# authored wider than half the skull and splayed outward, which reads as fennec
# where a pair of inward-leaning spikes reads as a cat.
# ---------------------------------------------------------------------------

def build_fennec():
    kit.reset_scene()
    root = kit.empty("root")

    coat = "#f0dcb4"
    pale = "#fffaef"
    inner = "#e5b2a0"
    ochre = "#d3aa74"
    paw = "#4c3b2b"

    body_dims = (0.28, 0.44, 0.26)
    body_at = (0, -0.08, 0.34)
    body = [bk.block("body.core", body_dims, body_at, color=coat)]
    body += bk.belly("body.chest", body_at, body_dims, color=pale, inset=0.7)
    # A dusty saddle down the spine so the torso is not one unbroken pale slab.
    body.append(bk.block("body.saddle", (0.22, 0.36, 0.05), (0, -0.08, 0.46),
                         color=ochre))
    body += bk.spots("body.dust", body_at, body_dims, count=4, size=0.05,
                     color=ochre, seed=17, faces=("left", "right"))

    head_dims = (0.26, 0.22, 0.23)
    head_at = (0, 0.33, 0.56)
    head = [bk.block("head.skull", head_dims, head_at, color=coat)]
    head += bk.snout("head.snout", head_at, head_dims, width=0.12, length=0.17,
                     height=0.1, color=pale, drop=-0.05, nose_color="#2b211c")
    head += bk.eyes("head.eye", head_at, head_dims, spacing=0.58, height=0.05,
                    size=0.072, style="white", iris="#1d1712", pupil_scale=0.56)
    head.append(bk.face_plate("head.mask", bk.face_of(head_at, head_dims, "front"),
                              (0.23, 0.032), face="front", color=ochre,
                              depth=0.016, offset=(0, -0.012)))

    # spacing 1.08 pushes the ear roots out past the skull corners; the
    # negative lean splays the tips further out again.
    ear_l, ear_r = bk.ears_pointed("ear", head_at, head_dims, size=0.21,
                                   spacing=1.08, length=0.34, color=coat,
                                   inner_color=inner, lean=-13)

    legs = bk.legs_quad("leg", front=(0.11, 0.14, 0.22), back=(0.12, -0.22, 0.22),
                        length=0.22, thickness=0.085, color=coat,
                        foot_color=paw)
    # thickness stays low: puff style triples it, and 0.13 produced a tail
    # wider than the dog it was attached to.
    tail_obj = bk.tail("tail", (0, -0.28, 0.36), length=0.34, thickness=0.075,
                       color=coat, style="puff", tip_color=ochre, segments=3,
                       curl=0.3)
    tail_tip = bk.block("tail.tip", (0.12, 0.1, 0.12), (0, -0.6, 0.44),
                        color="#6d5540")

    groups = {
        "body": (body, (0, 0, 0.22)),
        "head": (head, (0, 0.22, 0.46)),
        "ear.L": ([ear_l], tuple(ear_l.location)),
        "ear.R": ([ear_r], tuple(ear_r.location)),
        "tail": ([tail_obj, tail_tip], (0, -0.28, 0.36)),
    }
    for key, obj in legs.items():
        groups[key] = ([obj], tuple(obj.location))
    bk.assemble(root, groups)
    return bk.finish(root)


# ---------------------------------------------------------------------------
# Camel -- Rare, $75/s.
# Tall and slow. The two humps are pushed apart until there is a visible saddle
# of sky between them; butted together they read as one lumpy back.
# ---------------------------------------------------------------------------

def build_camel():
    kit.reset_scene()
    root = kit.empty("root")

    coat = "#d2a768"
    ochre = "#b1843c"
    bone = "#e7d5b0"
    hoof = "#5b4732"
    dark = "#2f241c"

    body_dims = (0.34, 0.58, 0.32)
    body_at = (0, -0.04, 0.66)
    body = [bk.block("body.core", body_dims, body_at, color=coat)]
    body.append(bk.block("body.hump.f", (0.28, 0.22, 0.26), (0, 0.14, 0.94),
                         color=ochre))
    body.append(bk.block("body.hump.b", (0.26, 0.2, 0.2), (0, -0.18, 0.9),
                         color=ochre))
    body += bk.belly("body.flank", body_at, body_dims, color=bone, inset=0.58)

    # Neck: four shrinking blocks climbing forward out of the shoulders, plus
    # a shaggy bib where it meets the chest.
    neck_lean = -32.0
    for i in range(4):
        t = float(i)
        body.append(bk.block(
            "body.neck%d" % i, (0.16 - t * 0.011, 0.16 - t * 0.011, 0.17),
            (0, 0.24 + t * 0.075, 0.8 + t * 0.115), rot=(neck_lean, 0, 0),
            color=coat,
        ))
    body.append(bk.block("body.bib", (0.19, 0.13, 0.14), (0, 0.28, 0.79),
                         rot=(-28, 0, 0), color=bone))

    head_dims = (0.17, 0.25, 0.2)
    head_at = (0, 0.55, 1.2)
    head = [bk.block("head.skull", head_dims, head_at, color=coat)]
    head += bk.snout("head.muzzle", head_at, head_dims, width=0.13, length=0.15,
                     height=0.13, color=bone, drop=-0.06, nose_color=dark)
    head += bk.nostrils("head.nostril", (0, 0.755, 1.14), (0.13, 0.15, 0.13),
                        spacing=0.44, height=0.03, size=0.032, color=dark)
    # Sleepy lids: a heavy horizontal bar with a brow ridge sat right on it.
    head += bk.eyes("head.eye", head_at, head_dims, spacing=0.62, height=0.05,
                    size=0.08, style="sleepy", iris=dark)
    for side, sign in (("L", 1), ("R", -1)):
        head.append(bk.block("head.brow.%s" % side, (0.055, 0.06, 0.03),
                             (sign * 0.055, head_at[1] + 0.1, head_at[2] + 0.077),
                             color=ochre))
    ear_l, ear_r = bk.ears_box("ear", head_at, head_dims, size=0.075,
                               spacing=0.95, depth=0.04, color=coat,
                               inner_color=bone, lean=-18)

    legs = bk.legs_quad("leg", front=(0.13, 0.2, 0.5), back=(0.14, -0.22, 0.5),
                        length=0.5, thickness=0.09, color=coat,
                        foot_color=hoof)
    # Knee calluses ride on the body so they hold still while the legs swing.
    for tag, (kx, ky) in (("FL", (0.13, 0.2)), ("FR", (-0.13, 0.2)),
                          ("BL", (0.14, -0.22)), ("BR", (-0.14, -0.22))):
        body.append(bk.block("body.knee.%s" % tag, (0.11, 0.11, 0.07),
                             (kx, ky, 0.3), color=ochre))

    # A short rope of a tail that hangs rather than sticks out, with the
    # camel's black switch on the end.
    tail_at = (0, -0.32, 0.78)
    tail_parts, tip, direction = _arc_tail(
        "tail", tail_at, back=0.2, rise=-0.4, segments=4,
        thick=(0.08, 0.055), colors=(coat,), power=0.7)
    tail_parts.append(bk.block(
        "tail.switch", (0.075, 0.075, 0.12),
        (0, tip[1] + direction[0] * 0.06, tip[2] + direction[1] * 0.06),
        color=dark))

    groups = {
        "body": (body, (0, 0, 0.38)),
        "head": (head, (0, 0.45, 1.06)),
        "ear.L": ([ear_l], tuple(ear_l.location)),
        "ear.R": ([ear_r], tuple(ear_r.location)),
        "tail": (tail_parts, tail_at),
    }
    for key, obj in legs.items():
        groups[key] = ([obj], tuple(obj.location))
    bk.assemble(root, groups)
    return bk.finish(root)


# ---------------------------------------------------------------------------
# Dustpiper -- Epic, $325/s. ORIGINAL.
# A lean dune-runner bird: long low body, ground-eating legs, a ragged crest
# that never lies flat, and a turquoise dust-scarf streaming off the neck.
# The scarf is the rarity tell -- first pet in the biome allowed turquoise.
# ---------------------------------------------------------------------------

def build_dustpiper():
    kit.reset_scene()
    root = kit.empty("root")

    dust = "#b98d55"
    deep = "#845f33"
    bone = "#ece0c6"
    terra = "#c2683c"
    turq = "#2fd3c8"
    turq_d = "#1c9d96"
    dark = "#37291b"

    body_dims = (0.22, 0.52, 0.24)
    body_at = (0, -0.08, 0.5)
    body = [bk.block("body.core", body_dims, body_at, color=dust)]
    body += bk.belly("body.breast", body_at, body_dims, color=bone, inset=0.66)
    body += bk.stripes("body.bar", body_at, body_dims, count=3, width=0.035,
                       color=deep, axis="y")

    # Neck: three blocks raking forward so the head clears the shoulders by a
    # clear span of air rather than sitting on them.
    for i in range(3):
        t = float(i)
        body.append(bk.block("body.neck%d" % i, (0.13, 0.13, 0.14),
                             (0, 0.14 + t * 0.055, 0.62 + t * 0.105),
                             rot=(-27, 0, 0), color=dust))

    # Dust-scarf: knot at the throat, two ragged ends streaming back and down.
    body.append(bk.block("body.scarf.knot", (0.19, 0.13, 0.11),
                         (0, 0.19, 0.68), rot=(-22, 0, 0), color=turq))
    for side, sign in (("L", 1), ("R", -1)):
        body.append(bk.block("body.scarf.%s0" % side, (0.05, 0.28, 0.045),
                             (sign * 0.055, -0.02, 0.72), rot=(-9, 0, sign * 5),
                             color=turq))
        body.append(bk.block("body.scarf.%s1" % side, (0.04, 0.2, 0.035),
                             (sign * 0.08, -0.26, 0.67), rot=(-16, 0, sign * 10),
                             color=turq_d))

    head_dims = (0.19, 0.19, 0.18)
    head_at = (0, 0.32, 0.9)
    head = [bk.block("head.skull", head_dims, head_at, color=dust)]
    head += bk.beak("head.beak", head_at, head_dims, width=0.075, length=0.25,
                    height=0.065, color=dark, drop=-0.02, taper=0.58)
    head += bk.eyes("head.eye", head_at, head_dims, spacing=0.66, height=0.03,
                    size=0.07, style="white", iris="#171009", pupil_scale=0.5)
    # A terracotta warpaint streak running back from each eye.
    for side, sign in (("L", 1), ("R", -1)):
        f = "left" if sign > 0 else "right"
        head.append(bk.face_plate(
            "head.streak.%s" % side, bk.face_of(head_at, head_dims, f),
            (0.14, 0.035), face=f, color=terra, depth=0.016,
            offset=(-0.02, 0.02),
        ))
    # Ragged crest: five spines of jumbled height, all raked backwards.
    for i, (dy, h, lean) in enumerate(((0.05, 0.1, -18), (0.01, 0.16, -26),
                                       (-0.03, 0.12, -34), (-0.06, 0.17, -42),
                                       (-0.09, 0.09, -52))):
        head.append(bk.wedge("head.crest%d" % i, (0.035, 0.05, h),
                             (0, head_at[1] + dy, head_at[2] + 0.1 + h * 0.4),
                             rot=(lean, 0, 0), color=deep, taper=0.75))

    wing_l, wing_r = bk.wings_flat("wing", (0.1, -0.06, 0.56), span=0.14,
                                   height=0.26, thickness=0.06, color=dust,
                                   tip_color=deep, layers=2, tilt=5)
    legs = bk.bird_feet("leg", (0.08, -0.02, 0.4), shin=0.38, thickness=0.055,
                        toe=0.18, color=terra)

    # Tail: kept dark and low so it reads as trailing feathers. Bone shows only
    # on three small tip slabs -- a full pale segment floated off as a plank.
    tail_at = (0, -0.3, 0.5)
    tail_obj = bk.tail("tail", tail_at, length=0.42, thickness=0.1,
                       color=deep, style="flat", segments=3, curl=0.28)
    tail_tips = []
    for i, dx in enumerate((-0.08, 0.0, 0.08)):
        tail_tips.append(bk.block("tail.tip%d" % i, (0.055, 0.12, 0.04),
                                  (dx, -0.76, 0.6 + abs(dx) * 0.12),
                                  color=bone))

    groups = {
        "body": (body, (0, 0, 0.3)),
        "head": (head, (0, 0.24, 0.78)),
        "wing.L": ([wing_l], tuple(wing_l.location)),
        "wing.R": ([wing_r], tuple(wing_r.location)),
        "tail": ([tail_obj] + tail_tips, tail_at),
    }
    for key, obj in legs.items():
        groups[key] = ([obj], tuple(obj.location))
    bk.assemble(root, groups)
    return bk.finish(root)


# ---------------------------------------------------------------------------
# Snake -- Legendary, $3.6K/s.
# Two banded coils on the sand, an S of neck rising out of the middle, a flared
# cobra hood and a head thrust well forward of it. Legendary signature:
# turquoise glow scales in the coil and gold trim down the hood.
# ---------------------------------------------------------------------------

def build_snake():
    kit.reset_scene()
    root = kit.empty("root")

    scale = "#dcb45a"
    band = "#7a4a1c"
    belly = "#f0e2bc"
    lapis = "#20408c"
    gold = "#f7cf4d"
    turq = "#2fd3c8"

    # Three shrinking loops stacked into a tapering spiral. Two concentric
    # rings of the same size read as a tiered cake; a third, tighter loop on
    # top is what turns the stack back into a coil that is going somewhere.
    # The strong light/dark alternation per block does the rest -- a
    # single-colour ring of boxes fuses into a featureless drum.
    body = _coil("body.coil0", (0, -0.05, 0.12), 0.35, 9, 0.23,
                 (scale, band), length=1.25)
    body += _coil("body.coil1", (0, -0.03, 0.3), 0.245, 7, 0.21,
                  (band, scale), length=1.25, phase=0.45)
    body += _coil("body.coil2", (0, -0.01, 0.46), 0.17, 5, 0.18,
                  (scale, band), length=1.2, phase=0.95)
    # Pale belly plates on the outer front arc, where the camera actually is.
    # Radii here are the coils' OUTER surface (centre radius + half a block),
    # not the centreline -- placed on the centreline they sink out of sight.
    for i, a in enumerate((-36, 0, 36)):
        r = math.radians(a)
        body.append(bk.block("body.plate%d" % i, (0.14, 0.06, 0.13),
                             (math.sin(r) * 0.47, -0.05 + math.cos(r) * 0.47,
                              0.11), rot=(0, 0, -a), color=belly))
    for i, (a, rad, z) in enumerate(((62, 0.36, 0.31), (214, 0.36, 0.31),
                                     (140, 0.27, 0.47))):
        r = math.radians(a)
        body.append(bk.glow_block(
            "body.spark%d" % i, (0.07, 0.07, 0.055),
            (math.sin(r) * rad, -0.02 + math.cos(r) * rad, z),
            color=turq, strength=2.4,
        ))
    # Neck: two banded blocks rising out of the top of the spiral.
    for i in range(2):
        t = float(i)
        body.append(bk.block("body.neck%d" % i, (0.17 - t * 0.012,
                                                 0.17 - t * 0.012, 0.14),
                             (0, 0.02 + t * 0.012, 0.57 + t * 0.12),
                             color=band if i % 2 else scale))

    # Hood: one wide flared slab, gold-edged, carrying the lapis spectacle
    # marks. The head then sits a clear 0.24 forward of it.
    hood_at = (0, 0.0, 0.83)
    hood_dims = (0.52, 0.1, 0.3)
    head = [bk.block("head.hood", hood_dims, hood_at, color=band)]
    for side, sign in (("L", 1), ("R", -1)):
        # Thin gold edge plus a gold top corner. A full gold rim all the way
        # round turned the hood into a picture frame with a snake in it.
        head.append(bk.block("head.hood.edge.%s" % side, (0.04, 0.06, 0.28),
                             (sign * 0.25, 0.0, hood_at[2]), color=gold))
        head.append(bk.block("head.hood.corner.%s" % side, (0.17, 0.06, 0.045),
                             (sign * 0.17, 0.0, hood_at[2] + 0.155),
                             color=gold))
        # Sloped shoulders under each side, which is what turns a rectangle
        # into the flared trapezoid a cobra hood actually is.
        head.append(bk.block("head.hood.flare.%s" % side, (0.22, 0.09, 0.06),
                             (sign * 0.2, 0.0, hood_at[2] - 0.14),
                             rot=(0, sign * 36, 0), color=band))
        head.append(bk.face_plate(
            "head.hood.mark.%s" % side, bk.face_of(hood_at, hood_dims, "front"),
            (0.12, 0.12), face="front", color=lapis, depth=0.022,
            offset=(sign * 0.15, 0.03),
        ))

    head_dims = (0.22, 0.26, 0.17)
    head_at = (0, 0.24, 0.81)
    head.append(bk.block("head.skull", head_dims, head_at, color=scale))
    head.append(bk.block("head.jaw", (0.19, 0.22, 0.06),
                         (0, head_at[1] + 0.02, head_at[2] - 0.09), color=belly))
    head += bk.eyes("head.eye", head_at, head_dims, spacing=0.7, height=0.045,
                    size=0.06, style="glow", iris=gold)
    head += bk.mouth("head.mouth", head_at, head_dims, width=0.14, height=0.022,
                     drop=-0.06, color="#2a1c14")
    for side, sign in (("L", 1), ("R", -1)):
        head.append(bk.block("head.tongue.%s" % side, (0.018, 0.15, 0.018),
                             (sign * 0.024, head_at[1] + 0.21, head_at[2] - 0.06),
                             rot=(0, 0, sign * 14), color="#e04b52"))

    # The tail flicks out of the back of the ground loop.
    tail_at = (0.16, -0.4, 0.12)
    tail_parts, tip, direction = _arc_tail(
        "tail", tail_at, back=0.3, rise=0.2, segments=4,
        thick=(0.15, 0.07), colors=(band, scale), power=1.8)
    tail_parts.append(bk.block(
        "tail.rattle", (0.08, 0.08, 0.09),
        (tail_at[0], tip[1] + direction[0] * 0.05,
         tip[2] + direction[1] * 0.05), color=gold))

    bk.assemble(root, {
        "body": (body, (0, 0, 0.11)),
        "head": (head, (0, 0.0, 0.68)),
        "tail": (tail_parts, tail_at),
    })
    return bk.finish(root)


# ---------------------------------------------------------------------------
# Sand Spider -- Mythic, $16K/s.
# A heavy raised abdomen with the knees arching above the back -- the pose that
# separates a spider from a beetle at icon size. Legs are deliberately thick
# and close to the body's own colour; thin dark ones read as scaffolding.
# The eight legs fold two-at-a-time into the animator's four leg slots.
# ---------------------------------------------------------------------------

def build_sand_spider():
    kit.reset_scene()
    root = kit.empty("root")

    sand = "#dcb87e"
    tan = "#b98b52"
    deep = "#8a6236"
    dark = "#4f3620"
    bone = "#f2ead4"
    turq = "#2fd3c8"
    amber = "#ffc451"

    hip_z = 0.54

    # The abdomen is an egg, not a box: a narrower cap above and below the main
    # block gives it a bevelled profile. A flat-topped abdomen sitting level
    # with the leg roots reads as a tabletop with legs screwed into it.
    abdomen_at = (0, -0.42, 0.68)
    abdomen_dims = (0.46, 0.5, 0.44)
    body = [bk.block("body.abdomen", abdomen_dims, abdomen_at, color=sand)]
    body.append(bk.block("body.abdomen.crown", (0.34, 0.38, 0.14),
                         (0, -0.42, 0.955), color=sand))
    body.append(bk.block("body.abdomen.keel", (0.34, 0.38, 0.13),
                         (0, -0.42, 0.4), color=tan))
    # Dune chevrons down the abdomen, plus mythic glow veins along the flanks.
    for i in range(3):
        t = float(i)
        body.append(bk.block("body.chevron%d" % i,
                             (0.28 - t * 0.065, 0.06, 0.06),
                             (0, -0.28 - t * 0.15, 0.92 - t * 0.035),
                             color=deep))
    for side, sign in (("L", 1), ("R", -1)):
        body.append(bk.glow_block("body.vein.%s" % side, (0.04, 0.34, 0.04),
                                  (sign * 0.245, -0.42, 0.72),
                                  rot=(0, 0, sign * 6), color=turq,
                                  strength=2.2))
    body.append(bk.block("body.thorax", (0.32, 0.3, 0.24), (0, 0.0, 0.54),
                         color=tan))
    body.append(bk.block("body.waist", (0.14, 0.14, 0.14), (0, -0.19, 0.56),
                         color=dark))

    head_dims = (0.3, 0.18, 0.22)
    head_at = (0, 0.22, 0.52)
    head = [bk.block("head.carapace", head_dims, head_at, color=deep)]
    face = bk.face_of(head_at, head_dims, "front")
    eye_mat = kit.mat("spider.eye", kit.hexcol(amber), rough=0.15,
                      emission=kit.hexcol(amber), emission_strength=3.6)
    # Eight eyes: two big principal ones over a row of six small ocelli.
    for side, sign in (("L", 1), ("R", -1)):
        head.append(bk.face_plate("head.eye.%s" % side, face, (0.08, 0.08),
                                  face="front", material=eye_mat, depth=0.022,
                                  offset=(sign * 0.055, 0.035)))
    for i in range(6):
        t = (i / 5.0 - 0.5)
        head.append(bk.face_plate(
            "head.oc%d" % i, face, (0.032, 0.032), face="front",
            material=eye_mat, depth=0.018,
            offset=(t * 0.22, 0.1 - abs(t) * 0.05),
        ))
    for side, sign in (("L", 1), ("R", -1)):
        head.append(bk.block("head.chelicera.%s" % side, (0.08, 0.1, 0.1),
                             (sign * 0.06, head_at[1] + 0.05, head_at[2] - 0.15),
                             color=tan))
        # Short inward-curving fangs. Long straight ones read as boar tusks.
        head.append(bk.wedge("head.fang.%s" % side, (0.05, 0.05, 0.13),
                             (sign * 0.055, head_at[1] + 0.07, head_at[2] - 0.25),
                             rot=(14, sign * 16, 0), color=bone, taper=0.9))
        head.append(bk.block("head.palp.%s" % side, (0.055, 0.22, 0.055),
                             (sign * 0.17, head_at[1] + 0.05, head_at[2] - 0.11),
                             rot=(22, 0, sign * 24), color=dark))

    # Legs: a steep femur up to a knee that clears the back, then a long, near
    # vertical tibia down to the sand. Steep tibias keep the overall footprint
    # narrow -- splayed ones made the whole animal wider than it was tall and
    # it collapsed into a trestle. Two adjacent legs share each slot.
    leg_yaws = (66.0, 26.0, -18.0, -62.0)
    leg_anchor_y = (0.14, 0.03, -0.07, -0.16)
    slots = {}
    for slot, indices in (("F", (0, 1)), ("B", (2, 3))):
        parts = []
        for i in indices:
            start = (0.14, leg_anchor_y[i], hip_z)
            femur, knee = _segment("leg.%s%d.fem" % (slot, i), start, 32.0,
                                   leg_yaws[i], 0.3, 0.08, deep, taper=0.25)
            tibia, _foot = _segment("leg.%s%d.tib" % (slot, i), knee, 160.0,
                                    leg_yaws[i], 0.72, 0.07, tan, taper=0.55)
            joint = bk.block("leg.%s%d.knee" % (slot, i), (0.1, 0.1, 0.1),
                             knee, color=dark)
            parts += [femur, tibia, joint]
        left, right = _mirror_group(
            parts, "leg.%s" % slot,
            (0.14, sum(leg_anchor_y[i] for i in indices) / 2.0, hip_z))
        slots["leg.%sL" % slot] = left
        slots["leg.%sR" % slot] = right

    groups = {
        "body": (body, (0, -0.18, 0.32)),
        "head": (head, (0, 0.14, 0.5)),
    }
    for key, obj in slots.items():
        groups[key] = ([obj], tuple(obj.location))
    bk.assemble(root, groups)
    return bk.finish(root)


# ---------------------------------------------------------------------------
# Scorpion -- Mythic, $18.5K/s.
# The arched metasoma is the entire silhouette, so it rides an explicit
# circular arc that sweeps up behind the body and hangs the stinger forward
# over the head. Claws take the arm slots; the eight walking legs take the
# four leg slots, two apiece.
# ---------------------------------------------------------------------------

def build_scorpion():
    kit.reset_scene()
    root = kit.empty("root")

    shell = "#c2683c"
    deep = "#8d4324"
    dark = "#5b2c19"
    bone = "#efe0c0"
    amber = "#ffc451"
    turq = "#2fd3c8"

    body_z = 0.26

    body = [bk.block("body.carapace", (0.38, 0.3, 0.17), (0, 0.14, body_z),
                     color=shell)]
    # Mesosoma: four tapering plates marching backward, alternately shaded.
    for i in range(4):
        t = float(i)
        body.append(bk.block("body.seg%d" % i,
                             (0.34 - t * 0.038, 0.12, 0.15 - t * 0.013),
                             (0, -0.03 - t * 0.115, body_z - t * 0.005),
                             color=deep if i % 2 else shell))

    head_dims = (0.26, 0.15, 0.14)
    head_at = (0, 0.36, body_z + 0.02)
    head = [bk.block("head.plate", head_dims, head_at, color=deep)]
    head += bk.eyes("head.eye", head_at, head_dims, spacing=0.5, height=0.0,
                    size=0.05, style="glow", iris=amber, face="top")
    for side, sign in (("L", 1), ("R", -1)):
        head.append(bk.block("head.jaw.%s" % side, (0.055, 0.1, 0.055),
                             (sign * 0.055, head_at[1] + 0.11, head_at[2] - 0.04),
                             rot=(0, 0, sign * 13), color=bone))

    # Claws on the arm slots: a reaching upper arm, a heavy palm, two jaws with
    # a real gap between them so the pincer reads as open.
    claws = []
    for side, sign in (("L", 1), ("R", -1)):
        anchor = (sign * 0.17, 0.2, body_z)
        parts = [
            bk.block("arm.%s.upper" % side, (0.1, 0.24, 0.1),
                     (sign * 0.26, 0.31, body_z + 0.01), rot=(0, 0, sign * -16),
                     color=deep),
            bk.block("arm.%s.palm" % side, (0.19, 0.24, 0.15),
                     (sign * 0.33, 0.51, body_z + 0.02), color=shell),
            bk.wedge("arm.%s.jaw0" % side, (0.07, 0.07, 0.22),
                     (sign * 0.27, 0.68, body_z + 0.06),
                     rot=(-96, 0, sign * -14), color=bone, taper=0.72),
            bk.wedge("arm.%s.jaw1" % side, (0.065, 0.065, 0.19),
                     (sign * 0.4, 0.66, body_z - 0.02),
                     rot=(-96, 0, sign * 18), color=bone, taper=0.72),
        ]
        merged = kit.join(parts, "arm.%s" % side)
        kit.weld(merged)
        kit.set_origin_to(merged, anchor)
        claws.append(merged)

    # Metasoma. Samples ride a circle behind the body; the tangent at each
    # sample gives the block's tilt, so the arch reads as one continuous curve
    # instead of a staircase. The sweep runs past vertical to -266 degrees so
    # the stinger ends up in front of the head, not behind the rump.
    centre = (0.0, -0.14, 0.54)
    radius = 0.34
    tail_parts = []
    a_start, a_end, count = -30.0, -266.0, 7
    for i in range(count):
        a = a_start + (a_end - a_start) * (i / float(count - 1))
        r = math.radians(a)
        pos = (0.0, centre[1] + radius * math.sin(r),
               centre[2] - radius * math.cos(r))
        s = 0.14 - 0.008 * i
        tail_parts.append(bk.block(
            "tail.seg%d" % i, (s, s, 0.15), pos, rot=(90.0 + a, 0, 0),
            color=deep if i % 2 else shell,
        ))
    r_end = math.radians(a_end)
    tip = (0.0, centre[1] + radius * math.sin(r_end) + 0.06,
           centre[2] - radius * math.cos(r_end) - 0.06)
    tail_parts.append(bk.block("tail.bulb", (0.14, 0.14, 0.14), tip, color=shell))
    tail_parts.append(bk.wedge("tail.sting", (0.065, 0.065, 0.2),
                               (tip[0], tip[1] + 0.08, tip[2] - 0.11),
                               rot=(146.0, 0, 0), color=dark, taper=0.9))
    tail_parts += bk.gem("tail.venom", (tip[0], tip[1] - 0.01, tip[2] + 0.1),
                         size=0.1, color=turq, strength=3.6)
    tail_obj = kit.join(tail_parts, "tail")
    kit.weld(tail_obj)

    # Eight low walking legs, folded two per animation slot.
    leg_yaws = (54.0, 22.0, -12.0, -46.0)
    leg_anchor_y = (0.2, 0.09, -0.02, -0.14)
    slots = {}
    for slot, indices in (("F", (0, 1)), ("B", (2, 3))):
        parts = []
        for i in indices:
            start = (0.15, leg_anchor_y[i], body_z)
            # Two blocks per leg, no foot cap: eight tarsal blocks cost ~700
            # triangles and vanish under the body at any real viewing angle.
            femur, knee = _segment("leg.%s%d.fem" % (slot, i), start, 56.0,
                                   leg_yaws[i], 0.19, 0.065, deep, taper=0.2)
            tibia, _foot = _segment("leg.%s%d.tib" % (slot, i), knee, 158.0,
                                    leg_yaws[i], 0.36, 0.06, shell, taper=0.6)
            parts.append(femur)
            parts.append(tibia)
        left, right = _mirror_group(
            parts, "leg.%s" % slot,
            (0.15, sum(leg_anchor_y[i] for i in indices) / 2.0, body_z))
        slots["leg.%sL" % slot] = left
        slots["leg.%sR" % slot] = right

    groups = {
        "body": (body, (0, -0.1, 0.18)),
        "head": (head, (0, 0.28, body_z)),
        "arm.L": ([claws[0]], tuple(claws[0].location)),
        "arm.R": ([claws[1]], tuple(claws[1].location)),
        "tail": ([tail_obj], (0, -0.34, body_z)),
    }
    for key, obj in slots.items():
        groups[key] = ([obj], tuple(obj.location))
    bk.assemble(root, groups)
    return bk.finish(root)


# ---------------------------------------------------------------------------
# Royal Sphinx -- Cosmic, $280K/s.
# The biome's showpiece. Lion mass under a hard flared nemes headdress striped
# in gold and lapis, a broad usekh collar, gold anklets and a halo ring. Every
# expensive material in the palette lands on this model and nowhere else.
# ---------------------------------------------------------------------------

def build_royal_sphinx():
    kit.reset_scene()
    root = kit.empty("root")

    sand = "#e0bd82"
    tan = "#c99a55"
    gold = "#f2c53d"
    gold_d = "#c2952a"
    lapis = "#20408c"
    lapis_l = "#3466cf"
    bone = "#f6ecd6"
    turq = "#2fd3c8"

    # Lion mass: a narrow waist between a deep chest and a heavy haunch, so the
    # torso is not one flat slab from the side.
    body_dims = (0.38, 0.5, 0.34)
    body_at = (0, -0.14, 0.56)
    body = [bk.block("body.core", body_dims, body_at, color=sand)]
    body.append(bk.block("body.chest", (0.44, 0.24, 0.42), (0, 0.16, 0.6),
                         color=sand))
    body.append(bk.block("body.haunch", (0.46, 0.28, 0.4), (0, -0.36, 0.57),
                         color=sand))
    body += bk.belly("body.underside", body_at, body_dims, color=bone, inset=0.5)
    body.append(bk.block("body.spine", (0.1, 0.62, 0.05), (0, -0.16, 0.79),
                         color=tan))
    # Usekh collar: a broad banded disc across the chest and shoulders.
    body.append(bk.block("body.collar", (0.48, 0.16, 0.3), (0, 0.24, 0.66),
                         color=gold))
    for i, (dz, col) in enumerate(((0.09, lapis), (0.0, turq), (-0.09, lapis))):
        body.append(bk.block("body.collar.band%d" % i, (0.49, 0.12, 0.04),
                             (0, 0.26, 0.66 + dz), color=col))
    body.append(bk.block("body.collar.drop", (0.14, 0.11, 0.11), (0, 0.27, 0.48),
                         color=gold_d))
    body += bk.gem("body.collar.jewel", (0, 0.34, 0.48), size=0.11, color=turq,
                   strength=3.0)

    head_dims = (0.3, 0.26, 0.3)
    head_at = (0, 0.44, 1.0)
    head = [bk.block("head.skull", head_dims, head_at, color=sand)]
    face = bk.face_of(head_at, head_dims, "front")
    # A pale pharaoh face plate, so the head reads as a mask, not a muzzle.
    head.append(bk.face_plate("head.face", face, (0.25, 0.23), face="front",
                              color=bone, depth=0.028))
    head += bk.eyes("head.eye", head_at, head_dims, spacing=0.5, height=0.035,
                    size=0.085, style="white", iris=lapis, pupil_scale=0.5)
    # Kohl liner: a bar running out from each eye toward the temple.
    for side, sign in (("L", 1), ("R", -1)):
        head.append(bk.face_plate(
            "head.kohl.%s" % side, face, (0.13, 0.028), face="front",
            color=lapis, depth=0.02, offset=(sign * 0.115, 0.042),
            proud=bk.PROUD * 4,
        ))
    head.append(bk.block("head.nose", (0.05, 0.055, 0.075),
                         (0, head_at[1] + 0.15, head_at[2] - 0.03), color=tan))
    head += bk.mouth("head.mouth", head_at, head_dims, width=0.11, height=0.024,
                     drop=-0.095, color="#7a5238")
    # False beard: the pharaonic chin post, hung clear of the collar.
    head.append(bk.block("head.beard", (0.08, 0.09, 0.2),
                         (0, head_at[1] + 0.11, head_at[2] - 0.25),
                         rot=(10, 0, 0), color=gold))
    head.append(bk.block("head.beard.tie", (0.09, 0.1, 0.035),
                         (0, head_at[1] + 0.115, head_at[2] - 0.155),
                         color=lapis))

    # Nemes headdress. Crown cap, brow band, then striped lappets flaring down
    # beside the face -- the flare is what says "pharaoh" at 24px.
    head.append(bk.block("head.nemes.cap", (0.38, 0.34, 0.13),
                         (0, head_at[1] - 0.02, head_at[2] + 0.2), color=gold))
    for i, dx in enumerate((-0.115, 0.0, 0.115)):
        head.append(bk.block("head.nemes.stripe%d" % i, (0.05, 0.35, 0.04),
                             (dx, head_at[1] - 0.02, head_at[2] + 0.275),
                             color=lapis))
    head.append(bk.block("head.nemes.brow", (0.4, 0.07, 0.11),
                         (0, head_at[1] + 0.15, head_at[2] + 0.155), color=gold))
    for side, sign in (("L", 1), ("R", -1)):
        head.append(bk.block("head.nemes.lappet.%s" % side, (0.11, 0.22, 0.36),
                             (sign * 0.22, head_at[1] + 0.03, head_at[2] - 0.07),
                             rot=(0, sign * 8, 0), color=gold))
        for j, dz in enumerate((0.07, -0.02, -0.11)):
            head.append(bk.block(
                "head.nemes.lband.%s%d" % (side, j), (0.125, 0.21, 0.034),
                (sign * 0.226, head_at[1] + 0.03, head_at[2] - 0.07 + dz),
                color=lapis_l if j % 2 else lapis,
            ))
        head.append(bk.block("head.nemes.tail.%s" % side, (0.1, 0.16, 0.22),
                             (sign * 0.18, head_at[1] - 0.22, head_at[2] - 0.17),
                             color=gold_d))
    # Uraeus: the rearing cobra on the brow, with a turquoise eye-gem.
    head.append(bk.wedge("head.uraeus", (0.065, 0.065, 0.15),
                         (0, head_at[1] + 0.18, head_at[2] + 0.26),
                         rot=(-22, 0, 0), color=gold_d, taper=0.6))
    head += bk.gem("head.uraeus.gem", (0, head_at[1] + 0.21, head_at[2] + 0.22),
                   size=0.075, color=turq, strength=3.4)
    # Halo: the cosmic-tier tell, a gold ring riding above the crown.
    head += bk.ring("head.halo", (0, head_at[1] - 0.05, head_at[2] + 0.44),
                    radius=0.27, thickness=0.024, tilt=74.0, color=gold,
                    strength=2.2)

    legs = bk.legs_quad("leg", front=(0.16, 0.22, 0.36), back=(0.17, -0.34, 0.36),
                        length=0.36, thickness=0.13, color=sand,
                        foot_color=tan)
    for tag, (ax, ay) in (("FL", (0.16, 0.22)), ("FR", (-0.16, 0.22)),
                          ("BL", (0.17, -0.34)), ("BR", (-0.17, -0.34))):
        body.append(bk.block("body.anklet.%s" % tag, (0.155, 0.155, 0.06),
                             (ax, ay, 0.11), color=gold))

    tail_at = (0, -0.48, 0.66)
    tail_parts, tip, direction = _arc_tail(
        "tail", tail_at, back=0.34, rise=0.32, segments=5,
        thick=(0.1, 0.055), colors=(sand,), power=1.9)
    tail_parts.append(bk.block(
        "tail.tuft", (0.13, 0.13, 0.13),
        (0, tip[1] + direction[0] * 0.07, tip[2] + direction[1] * 0.07),
        color=gold))

    groups = {
        "body": (body, (0, 0, 0.34)),
        "head": (head, (0, 0.3, 0.86)),
        "tail": (tail_parts, tail_at),
    }
    for key, obj in legs.items():
        groups[key] = ([obj], tuple(obj.location))
    bk.assemble(root, groups)
    return bk.finish(root)


PETS = {
    "jerboa": build_jerboa,
    "fennec": build_fennec,
    "camel": build_camel,
    "dustpiper": build_dustpiper,
    "snake": build_snake,
    "sand-spider": build_sand_spider,
    "scorpion": build_scorpion,
    "royal-sphinx": build_royal_sphinx,
}
