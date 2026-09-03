"""
Starfall Rift -- the cosmic biome's eight pets.

Palette direction: deep indigo and violet ground tones, star white, with cyan
and magenta doing the neon work. Emissive is the theme, so every pet here
carries at least one `glow_block`, `gem` or `ring`, and the amount of light a
creature throws climbs with its rarity: the epic centipede has lit seams, the
divine unicorn has a gold aureole.

Most of these float rather than walk. Where a pet has no legs (the skeleton
boss, the lunar dragon) the silhouette has to do the work unaided, so those two
get the strongest read-at-24px shapes in the set -- a ribcage with a star
burning inside it, and a serpent framed by a lunar halo.

Conventions are the forest module's: build facing +Y, feet near z=0, group only
under the runtime's animation names, pivot at the joint, `bk.finish()` last.
"""

import math

import blockkit as bk
import kit

D2R = math.pi / 180.0

# The biome's shared neons. Individual pets still pick their own body colours;
# these two lights are what tie the whole roster to Starfall Rift.
CYAN = "#3ef0ff"
MAGENTA = "#ff4de0"
STARWHITE = "#f4f1ff"


# ---------------------------------------------------------------------------
# small local helpers
# ---------------------------------------------------------------------------

def _flank_constellation(name, points, links, plane_x, color=STARWHITE,
                         glow=CYAN, star=0.05):
    """
    Glowing star cubes joined by hairline bars, painted on a flank (+/-X face).

    `points` are (y, z) pairs in the flank's own plane. A link bar is built
    along Y and rotated about X into place -- getting that sign wrong turns a
    constellation into a starburst, which is exactly what the first pass did.
    """
    parts = []
    for i, (y, z) in enumerate(points):
        parts.append(bk.glow_block("%s.star%d" % (name, i),
                                   (0.018, star, star), (plane_x, y, z),
                                   color=color, strength=3.6))
    for j, (a, b) in enumerate(links):
        (ay, az), (by, bz) = points[a], points[b]
        length = max(0.02, math.hypot(by - ay, bz - az))
        angle = math.degrees(math.atan2(bz - az, by - ay))
        parts.append(bk.glow_block(
            "%s.link%d" % (name, j), (0.014, length, 0.016),
            (plane_x, (ay + by) * 0.5, (az + bz) * 0.5),
            rot=(angle, 0, 0), color=glow, strength=1.8))
    return parts


def _set_rot(obj, rot_deg):
    """Force an absolute euler on an object bk built with its own defaults."""
    obj.rotation_euler = (rot_deg[0] * D2R, rot_deg[1] * D2R, rot_deg[2] * D2R)
    return obj


# ---------------------------------------------------------------------------
# Centipede -- Epic, $1.5K/s.
# A rearing many-segmented crawler. Two things carry the read: a serrated top
# edge (one magenta spike per segment) and twelve legs that actually stick out
# past the body instead of tucking under it. The front two segments lift clear
# of the floor so the profile is an S rather than a stick.
# ---------------------------------------------------------------------------

def _centipede_leg(tag, hip, sign, limb, claw):
    """Femur out, tibia down, claw at the bottom. Two slabs plus a tip."""
    return [
        bk.slab(tag + ".femur", (0.16, 0.055, 0.055),
                (hip[0] + sign * 0.08, hip[1], hip[2] - 0.015),
                rot=(0, -sign * 26, 0), color=limb),
        bk.slab(tag + ".tibia", (0.05, 0.055, 0.2),
                (hip[0] + sign * 0.16, hip[1], hip[2] - 0.13),
                rot=(0, -sign * 7, 0), color=limb),
        bk.slab(tag + ".claw", (0.055, 0.085, 0.04),
                (hip[0] + sign * 0.17, hip[1] + 0.015, hip[2] - 0.24),
                color=claw),
    ]


def build_centipede():
    kit.reset_scene()
    root = kit.empty("root")

    shell = "#3b2c8c"
    shell_dark = "#1e1652"
    limb = "#8f6cff"
    claw = "#d9ccff"

    # (y, z, width), walking back and down from the raised head end.
    spine = [
        (0.20, 0.62, 0.30),
        (0.13, 0.46, 0.31),
        (0.01, 0.35, 0.31),
        (-0.17, 0.29, 0.29),
        (-0.35, 0.265, 0.26),
        (-0.53, 0.25, 0.22),
    ]

    body = []
    legs = {}
    for i, (y, z, w) in enumerate(spine):
        body.append(bk.block("body.seg%d" % i, (w, 0.16, w * 0.94), (0, y, z),
                             color=shell if i % 2 == 0 else shell_dark))
        # One spike per segment: the serrated top edge is the whole silhouette.
        body.append(bk.wedge("body.spike%d" % i, (0.05, 0.07, 0.13 - i * 0.012),
                             (0, y, z + w * 0.52), color=MAGENTA, taper=0.85))
        if i < len(spine) - 1:
            ny, nz, _ = spine[i + 1]
            body.append(bk.glow_block(
                "body.seam%d" % i, (w * 0.9, 0.06, w * 0.62),
                (0, (y + ny) * 0.5, (z + nz) * 0.5), color=CYAN, strength=2.8))

        for side, sign in (("L", 1), ("R", -1)):
            hip = (sign * (w * 0.42), y, z - 0.02)
            if i == 2:
                legs["leg.F%s" % side] = (
                    _centipede_leg("leg.F%s" % side, hip, sign, limb, claw), hip)
            elif i == 4:
                legs["leg.B%s" % side] = (
                    _centipede_leg("leg.B%s" % side, hip, sign, limb, claw), hip)
            else:
                body += _centipede_leg("body.limb%d%s" % (i, side), hip, sign,
                                       limb, claw)

    # A collar segment bridging the raised front to the head. Without it the
    # skull only clipped segment 0 at one corner and read as a floating box --
    # the single most common way a blocky creature falls apart.
    body.append(bk.block("body.collar", (0.26, 0.17, 0.24), (0, 0.27, 0.72),
                         color=shell_dark))
    body.append(bk.glow_block("body.collarseam", (0.23, 0.05, 0.17),
                              (0, 0.3, 0.79), color=CYAN, strength=2.8))

    head_dims = (0.3, 0.27, 0.25)
    head_at = (0, 0.4, 0.9)
    head = [bk.block("head.skull", head_dims, head_at, color=shell)]
    head.append(bk.slab("head.carapace", (0.26, 0.2, 0.05),
                        (0, head_at[1] - 0.01, head_at[2] + 0.14),
                        color=shell_dark))
    head += bk.eyes("head.eye", head_at, head_dims, spacing=0.6, height=0.035,
                    size=0.088, style="glow", iris=MAGENTA)
    head.append(bk.glow_block("head.sigil", (0.09, 0.055, 0.05),
                              (0, head_at[1] + 0.12, head_at[2] + 0.1),
                              color=CYAN, strength=3.2))
    # Mandibles: two tapered fangs curving forward and inward under the face.
    for side, sign in (("L", 1), ("R", -1)):
        head.append(bk.wedge(
            "head.fang.%s" % side, (0.055, 0.055, 0.2),
            (sign * 0.095, head_at[1] + 0.18, head_at[2] - 0.09),
            rot=(-72, sign * 18, 0), color=MAGENTA, taper=0.82))

    # Antennae ride the ear slots so the runtime waves them.
    antennae = {}
    for side, sign in (("L", 1), ("R", -1)):
        antennae["ear.%s" % side] = ([
            bk.slab("ear.%s.stalk" % side, (0.035, 0.035, 0.24),
                    (sign * 0.1, head_at[1] + 0.14, head_at[2] + 0.17),
                    rot=(-48, -sign * 16, 0), color=limb),
            bk.glow_block("ear.%s.tip" % side, (0.05, 0.05, 0.05),
                          (sign * 0.16, head_at[1] + 0.3, head_at[2] + 0.25),
                          color=CYAN, strength=3.6),
        ], (sign * 0.08, head_at[1] + 0.07, head_at[2] + 0.11))

    tail_obj = bk.tail("tail", (0, -0.6, 0.25), length=0.24, thickness=0.19,
                       color=shell_dark, style="segmented", segments=3,
                       curl=0.4)
    tail_tip = bk.glow_block("tail.tip", (0.1, 0.1, 0.1),
                             (0, -0.84, 0.31), color=MAGENTA, strength=3.2)

    groups = {
        "body": (body, (0, -0.12, 0.26)),
        "head": (head, (0, 0.24, 0.76)),
        "tail": ([tail_obj, tail_tip], (0, -0.6, 0.25)),
    }
    groups.update(antennae)
    groups.update(legs)
    bk.assemble(root, groups)
    return bk.finish(root)


# ---------------------------------------------------------------------------
# Cosmic Gecko -- Legendary, $30K/s.
# Flat and wide with limbs that splay OUT before they go down -- that angle is
# the whole difference between a gecko and a generic quadruped. The skin is
# near-black so the flank constellation, a real join-the-dots figure in glowing
# white and cyan, is the brightest thing on the model.
#
# It stands high on those legs on purpose. Built belly-to-the-floor it
# normalised to 2.6 units long for 1 unit tall and spilled out of its cell in
# the index; the raised stance buys back most of that without shortening it.
# ---------------------------------------------------------------------------

def build_cosmic_gecko():
    kit.reset_scene()
    root = kit.empty("root")

    skin = "#171238"
    skin_dark = "#0c0922"
    belly = "#2c2168"
    toe = "#6a52c8"

    body_dims = (0.36, 0.46, 0.22)
    body_at = (0, -0.04, 0.38)
    body = [bk.block("body.core", body_dims, body_at, color=skin)]
    body += bk.belly("body.under", body_at, body_dims, color=belly, inset=0.8)
    # A pinched neck: without it head, body and tail run together into one
    # long dark sausage in profile.
    body.append(bk.block("body.neck", (0.22, 0.16, 0.16), (0, 0.25, 0.42),
                         color=skin_dark))
    for i in range(4):
        body.append(bk.slab("body.ridge%d" % i, (0.15 - i * 0.02, 0.09, 0.04),
                            (0, 0.11 - i * 0.12, 0.5), color=skin_dark))

    stars = [(0.12, 0.46), (0.02, 0.4), (-0.07, 0.47), (-0.18, 0.38),
             (-0.04, 0.31), (0.13, 0.32)]
    links = [(0, 1), (1, 2), (2, 3), (1, 4), (4, 5)]
    for sign in (1, -1):
        body += _flank_constellation(
            "body.con%d" % (sign > 0), stars, links,
            sign * (body_dims[0] * 0.5 + 0.014))
    body += bk.spots("body.speck", body_at, body_dims, count=5, size=0.03,
                     color=STARWHITE, seed=9, faces=("top", "back"))

    head_dims = (0.34, 0.3, 0.23)
    head_at = (0, 0.5, 0.52)
    head = [bk.block("head.skull", head_dims, head_at, color=skin)]
    head.append(bk.block("head.jaw", (0.3, 0.27, 0.07),
                         (0, head_at[1] + 0.01, head_at[2] - 0.13),
                         color=belly))
    # Lidless dome eyes proud of the skull's top corners, with a slit pupil.
    for side, sign in (("L", 1), ("R", -1)):
        head.append(bk.block("head.orb.%s" % side, (0.11, 0.14, 0.12),
                             (sign * 0.13, head_at[1] + 0.04,
                              head_at[2] + 0.08), color=skin_dark))
        head.append(bk.glow_block("head.iris.%s" % side, (0.055, 0.09, 0.09),
                                  (sign * 0.185, head_at[1] + 0.04,
                                   head_at[2] + 0.08),
                                  color=CYAN, strength=3.8))
        head.append(bk.slab("head.slit.%s" % side, (0.022, 0.02, 0.075),
                            (sign * 0.215, head_at[1] + 0.04,
                             head_at[2] + 0.08), color="#07061a"))
    head += bk.mouth("head.mouth", head_at, head_dims, width=0.22,
                     height=0.024, drop=-0.07, color="#07061a", style="line")
    head += bk.nostrils("head.nose", head_at, head_dims, spacing=0.28,
                        height=0.02, size=0.026, color="#07061a")
    # A three-star diadem continues the constellation over the crown.
    head += _flank_constellation(
        "head.con", [(0.4, 0.65), (0.48, 0.675), (0.56, 0.645)],
        [(0, 1), (1, 2)], 0.0, star=0.042)

    legs = {}
    for tag, hip_y in (("F", 0.16), ("B", -0.2)):
        for side, sign in (("L", 1), ("R", -1)):
            hip = (sign * 0.17, hip_y, 0.36)
            legs["leg.%s%s" % (tag, side)] = ([
                bk.slab("leg.%s%s.upper" % (tag, side), (0.17, 0.085, 0.075),
                        (sign * 0.25, hip_y, 0.35),
                        rot=(0, -sign * 20, 0), color=skin),
                bk.slab("leg.%s%s.shin" % (tag, side), (0.07, 0.075, 0.25),
                        (sign * 0.32, hip_y, 0.21), color=skin_dark),
                bk.slab("leg.%s%s.pad" % (tag, side), (0.14, 0.18, 0.045),
                        (sign * 0.33, hip_y + 0.025, 0.06), color=toe),
            ], hip)

    tail_obj = bk.tail("tail", (0, -0.26, 0.38), length=0.38, thickness=0.16,
                       color=skin, style="taper", tip_color=skin_dark,
                       segments=4, curl=0.16)
    tail_bands = [
        bk.glow_block("tail.band%d" % i,
                      (0.14 - i * 0.032, 0.035, 0.12 - i * 0.03),
                      (0, -0.35 - i * 0.11, 0.395 + i * 0.012),
                      color=CYAN, strength=2.6)
        for i in range(3)
    ]

    groups = {
        "body": (body, (0, -0.04, 0.3)),
        "head": (head, (0, 0.34, 0.44)),
        "tail": ([tail_obj] + tail_bands, (0, -0.26, 0.38)),
    }
    groups.update(legs)
    bk.assemble(root, groups)
    return bk.finish(root)


# ---------------------------------------------------------------------------
# Cosmic Gorilla -- Mythic, $180K/s.
# Enormous shoulders, narrow hips, arms long enough to knuckle on the floor and
# set wide enough that they never merge with the torso. The head is pushed
# clear forward of the chest and sits in the valley between the shoulder
# blocks, which is what stops an ape from rendering as one tall box.
# ---------------------------------------------------------------------------

def build_cosmic_gorilla():
    kit.reset_scene()
    root = kit.empty("root")

    fur = "#4a3aa0"
    fur_dark = "#261b60"
    mask = "#b3a2e8"
    face = "#14103a"
    nebula_a = "#8a45e8"
    nebula_b = "#e04bd8"

    chest_dims = (0.62, 0.34, 0.36)
    chest_at = (0, -0.04, 0.72)
    body = [bk.block("body.chest", chest_dims, chest_at, color=fur)]
    body.append(bk.block("body.gut", (0.34, 0.3, 0.28), (0, -0.04, 0.48),
                         color=fur_dark))
    # Shoulders sit HIGHER than the skull. That hunch is the gorilla read; a
    # head perched on top of a square chest is a refrigerator.
    for side, sign in (("L", 1), ("R", -1)):
        body.append(bk.block("body.shoulder.%s" % side, (0.2, 0.31, 0.3),
                             (sign * 0.31, -0.03, 0.9), color=fur))
    body.append(bk.block("body.hump", (0.34, 0.26, 0.15), (0, -0.14, 0.96),
                         color=fur_dark))
    body.append(bk.block("body.neck", (0.2, 0.2, 0.15), (0, 0.16, 0.92),
                         color=fur_dark))
    body += bk.belly("body.plate", chest_at, chest_dims, color="#312468",
                     inset=0.66)
    # Nebula: two clouds of patches in different violets, plus a lit sternum.
    body += bk.spots("body.neb1", chest_at, chest_dims, count=5, size=0.11,
                     color=nebula_a, seed=4, faces=("left", "right", "back"))
    body += bk.spots("body.neb2", chest_at, chest_dims, count=4, size=0.07,
                     color=nebula_b, seed=17, faces=("left", "right", "front"))
    body.append(bk.glow_block("body.core", (0.11, 0.05, 0.15),
                              (0, 0.15, 0.74), color=MAGENTA, strength=2.8))

    # The head is pushed entirely clear of the chest in +Y and slung between
    # the shoulders, so there is daylight around it from every angle.
    head_dims = (0.34, 0.32, 0.3)
    head_at = (0, 0.4, 0.98)
    head = [bk.block("head.skull", head_dims, head_at, color=fur)]
    # A PALE face mask. A dark panel on a dark ape disappears at icon size;
    # this is now the brightest thing on the model after the knuckles.
    head.append(bk.face_plate("head.face", bk.face_of(head_at, head_dims,
                                                      "front"),
                              (0.27, 0.24), face="front", color=mask,
                              depth=0.035, offset=(0, -0.015)))
    head.append(bk.block("head.brow", (0.36, 0.12, 0.1),
                         (0, head_at[1] + 0.12, head_at[2] + 0.1),
                         color=fur_dark))
    muzzle_at = (0, head_at[1] + 0.17, head_at[2] - 0.08)
    muzzle_dims = (0.25, 0.16, 0.16)
    head.append(bk.block("head.muzzle", muzzle_dims, muzzle_at, color=mask))
    head += bk.nostrils("head.nose", muzzle_at, muzzle_dims, spacing=0.36,
                        height=0.035, size=0.036, color=face)
    head += bk.mouth("head.mouth", muzzle_at, muzzle_dims, width=0.15,
                     height=0.026, drop=-0.055, color=face)
    head += bk.eyes("head.eye", head_at, head_dims, spacing=0.44, height=0.075,
                    size=0.062, style="white", iris=face, sclera=CYAN,
                    pupil_scale=0.6)
    head.append(bk.glow_block("head.crown", (0.13, 0.055, 0.045),
                              (0, head_at[1] + 0.04, head_at[2] + 0.17),
                              color=nebula_b, strength=2.6))

    ears = {}
    for side, sign in (("L", 1), ("R", -1)):
        ears["ear.%s" % side] = ([
            bk.slab("ear.%s.flap" % side, (0.05, 0.12, 0.14),
                    (sign * 0.185, head_at[1] - 0.04, head_at[2] + 0.02),
                    color=mask),
        ], (sign * 0.165, head_at[1] - 0.04, head_at[2] + 0.02))

    # Arms: shoulder -> forearm -> fist, resting knuckle-down on the floor and
    # set outboard of the shoulder blocks so the silhouette has daylight in it.
    arms = {}
    for side, sign in (("L", 1), ("R", -1)):
        shoulder = (sign * 0.42, 0.02, 0.92)
        arms["arm.%s" % side] = ([
            bk.block("arm.%s.upper" % side, (0.17, 0.19, 0.46),
                     (sign * 0.44, 0.03, 0.7), rot=(0, -sign * 5, 0),
                     color=fur),
            bk.block("arm.%s.fore" % side, (0.14, 0.16, 0.34),
                     (sign * 0.47, 0.07, 0.31), color=fur_dark),
            bk.block("arm.%s.fist" % side, (0.18, 0.2, 0.15),
                     (sign * 0.48, 0.09, 0.1), color=fur_dark),
            bk.glow_block("arm.%s.knuckle" % side, (0.16, 0.08, 0.055),
                          (sign * 0.48, 0.18, 0.07), color=MAGENTA,
                          strength=3.4),
        ], shoulder)

    legs = bk.legs_pair("leg", (0.17, -0.04, 0.4), length=0.34, thickness=0.18,
                        color=fur_dark, foot_color=face, foot_length=0.28)

    groups = {
        "body": (body, (0, 0, 0.34)),
        "head": (head, (0, 0.24, 0.86)),
    }
    groups.update(ears)
    groups.update(arms)
    for key, obj in legs.items():
        groups[key] = ([obj], tuple(obj.location))
    bk.assemble(root, groups)
    return bk.finish(root)


# ---------------------------------------------------------------------------
# Ringhorn Bovid -- Cosmic, $2.2M/s.  ORIGINAL.
# A serene cow-like grazer of the rift. Its signature is orbital: a lit
# planetary ring tilted around the barrel of its body, three moonlets riding
# it, and horns that are hoops rather than points. Star-white blotches stand in
# for cow patches, which is the joke that makes the creature belong here.
# ---------------------------------------------------------------------------

def build_ringhorn_bovid():
    kit.reset_scene()
    root = kit.empty("root")

    hide = "#2f2775"
    hide_dark = "#1d1750"
    muzzle = "#c3b8ef"
    hoof = "#120e33"

    body_dims = (0.46, 0.68, 0.44)
    body_at = (0, -0.06, 0.58)
    body = [bk.block("body.barrel", body_dims, body_at, color=hide)]
    body.append(bk.block("body.rump", (0.42, 0.2, 0.4), (0, -0.42, 0.58),
                         color=hide_dark))
    body.append(bk.block("body.neck", (0.26, 0.24, 0.24), (0, 0.24, 0.72),
                         color=hide))
    body.append(bk.slab("body.udder", (0.2, 0.24, 0.09), (0, -0.14, 0.36),
                        color=muzzle))
    # Star-white patches: the cow marking, restated as a night sky. Placed by
    # hand on the flanks rather than scattered -- `spots` kept dropping them on
    # the top face, which the icon camera barely sees.
    for side, sign in (("L", 1), ("R", -1)):
        which = "left" if sign > 0 else "right"
        flank = bk.face_of(body_at, body_dims, which)
        for i, (dy, dz, w, h) in enumerate(((0.15, 0.08, 0.33, 0.25),
                                            (-0.15, -0.07, 0.28, 0.2),
                                            (-0.3, 0.13, 0.14, 0.13))):
            body.append(bk.face_plate(
                "body.patch%s%d" % (side, i), flank, (w, h), face=which,
                depth=0.024, color="#ffffff", offset=(dy, dz)))
        for i, (dy, dz) in enumerate(((0.27, -0.13), (0.02, 0.15),
                                      (-0.2, -0.14))):
            body.append(bk.face_plate(
                "body.speck%s%d" % (side, i), flank, (0.05, 0.05), face=which,
                depth=0.016, color="#cfc6ff", offset=(dy, dz)))

    # The planetary ring. Two torii of different radius plus moonlets read as
    # an orbit; one lonely torus reads as a hula hoop.
    body += bk.ring("body.ring", (0, -0.06, 0.58), radius=0.64, thickness=0.036,
                    tilt=24, color=CYAN, strength=2.2)
    body += bk.ring("body.ring2", (0, -0.06, 0.58), radius=0.75,
                    thickness=0.016, tilt=24, color="#9d7bff", strength=1.5)
    for i, ang in enumerate((28.0, 158.0, 262.0)):
        rx = math.cos(ang * D2R) * 0.7
        ry = math.sin(ang * D2R) * 0.7
        body.append(bk.glow_block(
            "body.moonlet%d" % i, (0.065, 0.065, 0.065),
            (rx, -0.06 + ry * math.cos(24 * D2R), 0.58 + ry * math.sin(24 * D2R)),
            color=STARWHITE, strength=3.2))

    head_dims = (0.3, 0.3, 0.28)
    head_at = (0, 0.5, 0.86)
    head = [bk.block("head.skull", head_dims, head_at, color=hide)]
    head += bk.snout("head.snout", head_at, head_dims, width=0.25, length=0.18,
                     height=0.17, color=muzzle, drop=-0.07,
                     nose_color="#2a2255")
    head += bk.eyes("head.eye", head_at, head_dims, spacing=0.56, height=0.06,
                    size=0.08, style="white", iris="#241c52", pupil_scale=0.55)
    head.append(bk.slab("head.blaze", (0.1, 0.17, 0.05),
                        (0, head_at[1] + 0.06, head_at[2] + 0.16),
                        color=STARWHITE))

    ear_l, ear_r = bk.ears_box("ear", head_at, head_dims, size=0.12,
                               spacing=1.05, depth=0.06, color=hide_dark,
                               inner_color=muzzle)

    # Ring horns: a short post out of the skull carrying a vertical hoop.
    for side, sign in (("L", 1), ("R", -1)):
        head.append(bk.slab("head.post.%s" % side, (0.055, 0.055, 0.1),
                            (sign * 0.12, head_at[1] - 0.01, head_at[2] + 0.18),
                            color=muzzle))
        hoop = bk.ring("head.hoop.%s" % side,
                       (sign * 0.2, head_at[1] - 0.01, head_at[2] + 0.32),
                       radius=0.12, thickness=0.03, tilt=0, color=MAGENTA,
                       strength=2.8)[0]
        _set_rot(hoop, (0, 90, 0))
        head.append(hoop)

    legs = bk.legs_quad("leg", front=(0.17, 0.2, 0.4), back=(0.18, -0.26, 0.4),
                        length=0.38, thickness=0.115, color=hide_dark,
                        foot_color=hoof)
    tail_obj = bk.tail("tail", (0, -0.5, 0.66), length=0.34, thickness=0.06,
                       color=hide_dark, style="whip", tip_color=STARWHITE,
                       segments=3, curl=-0.5)

    groups = {
        "body": (body, (0, -0.1, 0.4)),
        "head": (head, (0, 0.36, 0.76)),
        "ear.L": ([ear_l], tuple(ear_l.location)),
        "ear.R": ([ear_r], tuple(ear_r.location)),
        "tail": ([tail_obj], (0, -0.5, 0.66)),
    }
    for key, obj in legs.items():
        groups[key] = ([obj], tuple(obj.location))
    bk.assemble(root, groups)
    return bk.finish(root)


# ---------------------------------------------------------------------------
# Cosmic Skeleton Boss -- Secret, $45M/s.
# A floating skeletal giant: no legs, just a wide ribcage hung in the air with
# a violet star burning inside it, long bone arms trailing to the floor, and a
# spine that tapers away underneath. The cage is deliberately open -- three
# hoops with big gaps -- so the core is visible through it from any angle.
# ---------------------------------------------------------------------------

def build_cosmic_skeleton_boss():
    kit.reset_scene()
    root = kit.empty("root")

    bone = "#ede6d3"
    bone_dark = "#bcb098"
    socket = "#0d0920"
    core = "#b06bff"

    body = []
    body.append(bk.block("body.pelvis", (0.36, 0.22, 0.16), (0, -0.05, 0.34),
                         color=bone))
    for side, sign in (("L", 1), ("R", -1)):
        body.append(bk.slab("body.hip.%s" % side, (0.08, 0.19, 0.22),
                            (sign * 0.21, -0.05, 0.43),
                            rot=(0, -sign * 16, 0), color=bone_dark))
    for i in range(5):
        body.append(bk.slab("body.vert%d" % i, (0.13, 0.14, 0.09),
                            (0, -0.11, 0.5 + i * 0.12), color=bone_dark))
    # Ribcage: three wide hoops with 0.10 of daylight between them.
    for i in range(3):
        z = 0.58 + 0.16 * i
        w = 0.26 - 0.022 * i
        for side, sign in (("L", 1), ("R", -1)):
            body.append(bk.slab("body.rib%d.%s" % (i, side), (0.07, 0.36, 0.075),
                                (sign * w, -0.03, z), color=bone))
        body.append(bk.slab("body.ribfront%d" % i, (w * 1.9, 0.07, 0.075),
                            (0, 0.16, z), color=bone))
    # No full-length sternum: it was the one part standing between the camera
    # and the core. Two short stubs hold the cage together and leave the middle
    # of the chest wide open.
    for z in (0.9, 0.58):
        body.append(bk.slab("body.sternum%d" % int(z * 100), (0.07, 0.06, 0.12),
                            (0, 0.19, z), color=bone_dark))
    # The burning core, caged between the ribs and backed by a lit spine plate
    # so it glows through the gaps from behind as well as through the front.
    # Strength 7 blew the gem out to pure white and lost the violet entirely;
    # 3.6 keeps the colour while still reading as the brightest thing here.
    body += bk.gem("body.core", (0, 0.07, 0.74), size=0.34, color=core,
                   strength=3.6)
    body.append(bk.glow_block("body.aura", (0.26, 0.05, 0.24), (0, -0.1, 0.74),
                              color="#6a2fd4", strength=2.0))
    for i, (dx, dy, dz) in enumerate(((0.2, 0.05, 0.94), (-0.23, -0.04, 0.6),
                                      (0.07, 0.16, 0.5), (-0.1, 0.1, 1.0))):
        body.append(bk.glow_block("body.ash%d" % i, (0.05, 0.05, 0.05),
                                  (dx, dy, dz), color=MAGENTA, strength=3.6))
    # Shoulder girdle and neck.
    body.append(bk.slab("body.collar", (0.62, 0.09, 0.075), (0, 0.03, 1.0),
                        color=bone))
    for side, sign in (("L", 1), ("R", -1)):
        body.append(bk.block("body.pauldron.%s" % side, (0.19, 0.21, 0.17),
                             (sign * 0.36, 0.0, 0.98), color=bone))
    for i in range(3):
        body.append(bk.slab("body.neck%d" % i, (0.11, 0.11, 0.075),
                            (0, 0.05, 1.06 + i * 0.075), color=bone_dark))

    head_dims = (0.38, 0.34, 0.3)
    head_at = (0, 0.18, 1.38)
    head = [bk.block("head.cranium", head_dims, head_at, color=bone)]
    head.append(bk.slab("head.brow", (0.39, 0.09, 0.07),
                        (0, head_at[1] + 0.17, head_at[2] + 0.09),
                        color=bone_dark))
    head.append(bk.block("head.jaw", (0.31, 0.28, 0.09), (0, 0.22, 1.19),
                         color=bone_dark))
    face = bk.face_of(head_at, head_dims, "front")
    core_mat = kit.mat("skel.core", kit.hexcol(core), rough=0.2,
                       emission=kit.hexcol(core), emission_strength=5.5)
    for side, sign in (("L", 1), ("R", -1)):
        head.append(bk.face_plate("head.socket.%s" % side, face, (0.13, 0.115),
                                  face="front", color=socket, depth=0.03,
                                  offset=(sign * 0.095, 0.015)))
        head.append(bk.face_plate("head.spark.%s" % side, face, (0.07, 0.06),
                                  face="front", material=core_mat, depth=0.022,
                                  offset=(sign * 0.095, 0.015),
                                  proud=bk.PROUD * 5))
    head.append(bk.face_plate("head.nasal", face, (0.055, 0.07), face="front",
                              color=socket, depth=0.02, offset=(0, -0.07)))
    head += bk.mouth("head.teeth", head_at, head_dims, width=0.26, height=0.03,
                     drop=-0.125, color=socket, style="open", teeth=5,
                     teeth_color=bone)

    # Crown horns, swept back off the skull; they ride the ear slots.
    crown = {}
    for side, sign in (("L", 1), ("R", -1)):
        parts = []
        for k in range(3):
            t = k / 2.0
            parts.append(bk.slab(
                "ear.%s.horn%d" % (side, k),
                (0.085 - 0.016 * k, 0.085 - 0.016 * k, 0.16),
                (sign * (0.15 + 0.04 * t), head_at[1] - 0.08 - 0.21 * t,
                 head_at[2] + 0.14 + 0.08 * t),
                rot=(62 + 14 * k, -sign * 12, 0), color=bone))
        parts.append(bk.glow_block("ear.%s.ember" % side, (0.06, 0.06, 0.06),
                                   (sign * 0.21, head_at[1] - 0.42,
                                    head_at[2] + 0.27),
                                   color=core, strength=3.8))
        crown["ear.%s" % side] = (parts, (sign * 0.15, head_at[1] - 0.05,
                                          head_at[2] + 0.12))

    arms = {}
    for side, sign in (("L", 1), ("R", -1)):
        shoulder = (sign * 0.36, 0.0, 0.97)
        parts = [
            bk.slab("arm.%s.humerus" % side, (0.09, 0.1, 0.4),
                    (sign * 0.4, -0.02, 0.78), rot=(0, -sign * 9, 0),
                    color=bone),
            bk.block("arm.%s.elbow" % side, (0.11, 0.11, 0.1),
                     (sign * 0.44, -0.01, 0.55), color=bone_dark),
            bk.slab("arm.%s.radius" % side, (0.075, 0.085, 0.35),
                    (sign * 0.46, 0.03, 0.37), color=bone),
            bk.slab("arm.%s.palm" % side, (0.14, 0.16, 0.075),
                    (sign * 0.47, 0.07, 0.16), color=bone_dark),
        ]
        for f in range(3):
            parts.append(bk.slab(
                "arm.%s.finger%d" % (side, f), (0.032, 0.038, 0.15),
                (sign * (0.42 + f * 0.05), 0.1, 0.055), color=bone))
        parts.append(bk.glow_block("arm.%s.claw" % side, (0.13, 0.06, 0.032),
                                   (sign * 0.47, 0.12, -0.03), color=core,
                                   strength=3.2))
        arms["arm.%s" % side] = (parts, shoulder)

    # The dangling spine that stands in for legs.
    tail_parts = []
    for i, (y, z, s) in enumerate(((-0.12, 0.24, 0.11), (-0.17, 0.15, 0.095),
                                   (-0.22, 0.07, 0.075), (-0.26, 0.0, 0.06))):
        tail_parts.append(bk.slab("tail.vert%d" % i, (s, s * 1.1, 0.08),
                                  (0, y, z), color=bone_dark))
    tail_parts.append(bk.glow_block("tail.wisp", (0.055, 0.055, 0.08),
                                    (0, -0.29, -0.07), color=core,
                                    strength=3.6))

    groups = {
        "body": (body, (0, -0.05, 0.34)),
        "head": (head, (0, 0.09, 1.21)),
        "tail": (tail_parts, (0, -0.08, 0.3)),
    }
    groups.update(crown)
    groups.update(arms)
    bk.assemble(root, groups)
    return bk.finish(root)


# ---------------------------------------------------------------------------
# Cosmic Dragon -- Secret, $60M/s.
# A four-legged star dragon. The wings are not membranes: each is a fan of five
# emissive blades, longest in the middle, swept progressively backward -- solid
# light, and far more striking than a webbed wing at this scale. Star scales
# speckle a near-black hide and a magenta crest runs the spine into the tail.
# ---------------------------------------------------------------------------

def build_cosmic_dragon():
    kit.reset_scene()
    root = kit.empty("root")

    scale = "#261e5e"
    scale_dark = "#150f38"
    under = "#463a97"
    claw = "#ddd6ff"

    body_dims = (0.44, 0.64, 0.4)
    body_at = (0, -0.08, 0.56)
    body = [bk.block("body.core", body_dims, body_at, color=scale)]
    body.append(bk.block("body.chest", (0.46, 0.26, 0.42), (0, 0.16, 0.6),
                         color=scale))
    body += bk.belly("body.under", (0, 0.16, 0.6), (0.46, 0.26, 0.42),
                     color=under, inset=0.72)
    body.append(bk.block("body.neck0", (0.25, 0.22, 0.25), (0, 0.3, 0.8),
                         color=scale))
    body.append(bk.block("body.neck1", (0.22, 0.2, 0.22), (0, 0.44, 0.98),
                         color=scale))
    body += bk.spots("body.star", body_at, body_dims, count=8, size=0.05,
                     color=STARWHITE, seed=13, faces=("left", "right", "top"))
    for i in range(5):
        h = 0.15 - abs(i - 2) * 0.026
        body.append(bk.wedge("body.crest%d" % i, (0.048, 0.08, h),
                             (0, 0.14 - i * 0.15, 0.76 + h * 0.4),
                             color=MAGENTA, taper=0.8))

    head_dims = (0.3, 0.32, 0.26)
    head_at = (0, 0.62, 1.14)
    head = [bk.block("head.skull", head_dims, head_at, color=scale)]
    head.append(bk.block("head.snout", (0.21, 0.24, 0.16),
                         (0, head_at[1] + 0.25, head_at[2] - 0.05),
                         color=scale_dark))
    head.append(bk.slab("head.jaw", (0.19, 0.22, 0.06),
                        (0, head_at[1] + 0.24, head_at[2] - 0.15),
                        color=under))
    for i in range(4):
        head.append(bk.slab("head.tooth%d" % i, (0.024, 0.024, 0.055),
                            (-0.05 + i * 0.033, head_at[1] + 0.33,
                             head_at[2] - 0.115), color=STARWHITE))
    head += bk.nostrils("head.nose",
                        (0, head_at[1] + 0.25, head_at[2] - 0.05),
                        (0.21, 0.24, 0.16), spacing=0.4, height=0.045,
                        size=0.032, color="#0a0722")
    head += bk.eyes("head.eye", head_at, head_dims, spacing=0.62, height=0.05,
                    size=0.08, style="glow", iris=CYAN)
    for side, sign in (("L", 1), ("R", -1)):
        head.append(bk.wedge("head.spine.%s" % side, (0.042, 0.042, 0.1),
                             (sign * 0.12, head_at[1] + 0.02,
                              head_at[2] + 0.16),
                             rot=(24, -sign * 18, 0), color=claw, taper=0.8))

    horns = {}
    for side, sign in (("L", 1), ("R", -1)):
        horns["ear.%s" % side] = ([
            bk.wedge("ear.%s.horn" % side, (0.065, 0.065, 0.28),
                     (sign * 0.11, head_at[1] - 0.12, head_at[2] + 0.18),
                     rot=(46, -sign * 16, 0), color=claw, taper=0.88),
            bk.glow_block("ear.%s.tip" % side, (0.045, 0.045, 0.045),
                          (sign * 0.15, head_at[1] - 0.3, head_at[2] + 0.28),
                          color=CYAN, strength=3.4),
        ], (sign * 0.1, head_at[1] - 0.06, head_at[2] + 0.1))

    # Wings of solid light: five blades, longest in the middle, sweeping back.
    wings = {}
    # A dim broad plane with bright ribs laid over it. Bare radiating blades
    # read as a firework; the filled plane is what makes this say "wing", and
    # keeping the whole thing emissive is what makes it solid light.
    rib_plan = ((-24.0, 0.5), (-2.0, 0.64), (20.0, 0.62), (44.0, 0.46))
    span, mid = 0.58, 14.0
    for side, sign in (("L", 1), ("R", -1)):
        shoulder = (sign * 0.2, 0.0, 0.8)
        parts = [
            bk.block("wing.%s.root" % side, (0.11, 0.15, 0.15),
                     (sign * 0.22, -0.02, 0.8), color=scale_dark),
            bk.glow_block(
                "wing.%s.web" % side, (span, 0.026, 0.42),
                (sign * (0.2 + math.cos(mid * D2R) * span * 0.5), -0.12,
                 0.8 + math.sin(mid * D2R) * span * 0.5),
                rot=(0, -sign * mid, 0), color="#27c8f5", strength=1.2),
        ]
        for j, (th, length) in enumerate(rib_plan):
            dx = math.cos(th * D2R) * length * 0.5
            dz = math.sin(th * D2R) * length * 0.5
            parts.append(bk.glow_block(
                "wing.%s.rib%d" % (side, j), (length, 0.03, 0.055),
                (sign * (0.2 + dx), -0.08, 0.8 + dz),
                rot=(0, -sign * th, 0),
                color=CYAN if j % 2 == 0 else "#a8ecff", strength=3.2))
        wings["wing.%s" % side] = (parts, shoulder)

    legs = bk.legs_quad("leg", front=(0.18, 0.2, 0.38), back=(0.19, -0.26, 0.38),
                        length=0.34, thickness=0.115, color=scale_dark,
                        foot_color=claw)

    tail_obj = bk.tail("tail", (0, -0.4, 0.54), length=0.52, thickness=0.15,
                       color=scale, style="taper", tip_color=scale_dark,
                       segments=5, curl=0.3)
    tail_fin = [
        bk.glow_block("tail.fin%d" % i, (0.065, 0.14, 0.18 - i * 0.06),
                      (0, -0.84 - i * 0.11, 0.68 + i * 0.035),
                      color=MAGENTA, strength=3.0)
        for i in range(2)
    ]

    groups = {
        "body": (body, (0, -0.08, 0.34)),
        "head": (head, (0, 0.5, 1.04)),
        "tail": ([tail_obj] + tail_fin, (0, -0.4, 0.54)),
    }
    groups.update(horns)
    groups.update(wings)
    for key, obj in legs.items():
        groups[key] = ([obj], tuple(obj.location))
    bk.assemble(root, groups)
    return bk.finish(root)


# ---------------------------------------------------------------------------
# Eternal Lunar Dragon -- Eternal, $250M/s.
# Deliberately NOT the cosmic dragon in silver. A legless eastern serpent posed
# in a true S: tail flicked up at the back, belly dipping to the floor in the
# middle, neck rising at the front, and a head half again wider than the neck
# that carries it, standing inside a glowing lunar halo.
#
# Three separated value groups do the reading: a mid-blue body, a white head
# and neck, and gold for the horns, spine tips and belly plates. An all-silver
# version of this was unreadable mush at any size.
# ---------------------------------------------------------------------------

def build_eternal_lunar_dragon():
    kit.reset_scene()
    root = kit.empty("root")

    hide = "#7f93cd"
    hide_dark = "#54659d"
    silver = "#f1f4fd"
    gold = "#ffd76e"
    moonglow = "#dfeaff"
    wing = "#a8c8ff"

    # (y, z, thickness) traced along the S, tail end first. The dip to z=0.17
    # in the middle is what puts a belly on the floor and keeps this from
    # reading as a stack of boxes.
    coils = [
        (-0.62, 0.3, 0.2),
        (-0.42, 0.2, 0.26),
        (-0.18, 0.17, 0.31),
        (0.04, 0.3, 0.32),
        (0.16, 0.55, 0.28),
    ]
    body = []
    for i, (y, z, w) in enumerate(coils):
        body.append(bk.block("body.coil%d" % i, (w, 0.24, w), (0, y, z),
                             color=hide if i % 2 else hide_dark))
    # The neck is deliberately narrow -- two thirds of the barrel's width, and
    # white where the body is blue.
    body.append(bk.block("body.neck0", (0.21, 0.22, 0.22), (0, 0.22, 0.78),
                         color=silver))
    body.append(bk.block("body.neck1", (0.18, 0.19, 0.19), (0, 0.26, 0.96),
                         color=silver))
    # Glowing spine tips the whole length, in the wings' pale blue so the gold
    # horns above them still stand alone.
    for i, (y, z, h) in enumerate(((-0.58, 0.42, 0.08), (-0.4, 0.35, 0.09),
                                   (-0.18, 0.34, 0.1), (0.03, 0.48, 0.1),
                                   (0.14, 0.71, 0.09), (0.2, 0.9, 0.07))):
        body.append(bk.glow_block("body.fin%d" % i, (0.045, 0.1, h), (0, y, z),
                                  color=wing, strength=2.6))
    for z, y in ((0.5, 0.28), (0.72, 0.32), (0.92, 0.35)):
        body.append(bk.slab("body.belly%d" % int(z * 100), (0.15, 0.045, 0.13),
                            (0, y, z), color=gold))
    # A gold crescent on the chest, built as an arc of shrinking blocks.
    for k in range(5):
        ang = 214.0 + k * 33.0
        size = 0.05 - abs(k - 2) * 0.011
        body.append(bk.glow_block(
            "body.crescent%d" % k, (size, 0.04, size + 0.02),
            (math.cos(ang * D2R) * 0.11, 0.3,
             0.61 + math.sin(ang * D2R) * 0.11),
            color=gold, strength=2.6))

    # The moon, as a standing halo rather than a filled disc. A solid white
    # circle either swallowed the white skull in front of it or, pushed back
    # far enough to clear it, floated free of the model like a stray prop. A
    # ring solves both: it frames the head instead of competing with it.
    # Pale blue throughout: a gold outer ring made this twin the unicorn's
    # aureole two cells away on the index, and the eternal tier has to look
    # like its own thing.
    for name, radius, thick, colour, power in (
            ("body.moonring", 0.4, 0.04, moonglow, 3.2),
            ("body.moongilt", 0.44, 0.016, "#eef4ff", 2.4)):
        hoop = bk.ring(name, (0, 0.02, 1.16), radius=radius, thickness=thick,
                       tilt=0, color=colour, strength=power)[0]
        _set_rot(hoop, (90, 0, 0))
        body.append(hoop)
    for i, ang in enumerate((28.0, 152.0, 264.0)):
        body.append(bk.glow_block(
            "body.mote%d" % i, (0.055, 0.055, 0.055),
            (math.cos(ang * D2R) * 0.5, 0.02,
             1.16 + math.sin(ang * D2R) * 0.5),
            color=moonglow, strength=3.4))

    # The head is half again wider than the neck. That jump is the single
    # change that took this from "lumpy column" to "dragon".
    head_dims = (0.3, 0.34, 0.27)
    head_at = (0, 0.42, 1.16)
    head = [bk.block("head.skull", head_dims, head_at, color=silver)]
    head.append(bk.block("head.muzzle", (0.2, 0.24, 0.16),
                         (0, head_at[1] + 0.26, head_at[2] - 0.05),
                         color=hide))
    head.append(bk.slab("head.jaw", (0.18, 0.22, 0.06),
                        (0, head_at[1] + 0.25, head_at[2] - 0.14),
                        color=hide_dark))
    head += bk.nostrils("head.nose",
                        (0, head_at[1] + 0.26, head_at[2] - 0.05),
                        (0.2, 0.24, 0.16), spacing=0.4, height=0.04,
                        size=0.03, color="#3d4a7c")
    head += bk.eyes("head.eye", head_at, head_dims, spacing=0.6, height=0.05,
                    size=0.085, style="glow", iris="#7fb0ff")
    head.append(bk.glow_block("head.gem", (0.075, 0.05, 0.06),
                              (0, head_at[1] + 0.08, head_at[2] + 0.15),
                              color=gold, strength=3.0))
    # Trailing whiskers -- cheap, and they say "eastern dragon" immediately.
    for side, sign in (("L", 1), ("R", -1)):
        head.append(bk.slab("head.whisker.%s" % side, (0.028, 0.22, 0.028),
                            (sign * 0.13, head_at[1] + 0.29, head_at[2] - 0.09),
                            rot=(0, 0, sign * 22), color=gold))

    # Crescent horns: three blocks on a tight arc sweeping up and back, in
    # GOLD. In silver on a silver skull they vanished into the head.
    crescents = {}
    for side, sign in (("L", 1), ("R", -1)):
        parts = []
        cy, cz = head_at[1] - 0.09, head_at[2] + 0.05
        for k in range(3):
            ang = 44.0 + k * 44.0
            size = 0.068 - k * 0.011
            parts.append(bk.slab(
                "ear.%s.arc%d" % (side, k), (size, size * 1.3, 0.12),
                (sign * (0.1 + 0.014 * k), cy + math.cos(ang * D2R) * 0.17,
                 cz + math.sin(ang * D2R) * 0.17),
                rot=(ang - 90, 0, 0), color=gold))
        crescents["ear.%s" % side] = (parts, (sign * 0.11, cy, cz + 0.06))

    # Small clawed forelimbs held up against the chest.
    arms = {}
    for side, sign in (("L", 1), ("R", -1)):
        shoulder = (sign * 0.14, 0.18, 0.66)
        arms["arm.%s" % side] = ([
            bk.slab("arm.%s.upper" % side, (0.09, 0.1, 0.24),
                    (sign * 0.21, 0.21, 0.57), rot=(0, -sign * 26, 0),
                    color=hide_dark),
            bk.slab("arm.%s.claw" % side, (0.11, 0.14, 0.075),
                    (sign * 0.26, 0.24, 0.45), color=gold),
        ], shoulder)

    # Moonlight wings: three stepped emissive plates each side, in a bluer
    # white than the body so they separate from it instead of merging.
    wings = {}
    for side, sign in (("L", 1), ("R", -1)):
        shoulder = (sign * 0.16, 0.02, 0.6)
        parts = []
        for j, (th, length) in enumerate(((-6.0, 0.56), (20.0, 0.5),
                                          (46.0, 0.36))):
            dx = math.cos(th * D2R) * length * 0.5
            dz = math.sin(th * D2R) * length * 0.5
            parts.append(bk.glow_block(
                "wing.%s.plate%d" % (side, j), (length, 0.034, 0.12),
                (sign * (0.16 + dx), 0.0 - 0.06 * j, 0.6 + dz),
                rot=(0, -sign * th, 0), color=wing, strength=3.2))
        wings["wing.%s" % side] = (parts, shoulder)

    # The tail continues the S upward off the back. The fin sits ON the last
    # segment rather than trailing behind it -- free-floating blades read as
    # detached debris in profile.
    tail_obj = bk.tail("tail", (0, -0.72, 0.32), length=0.2, thickness=0.2,
                       color=hide_dark, style="taper", tip_color=hide,
                       segments=2, curl=0.55)
    tail_fin = [
        bk.glow_block("tail.blade0", (0.06, 0.17, 0.23), (0, -0.86, 0.4),
                      color=wing, strength=2.6),
        bk.glow_block("tail.blade1", (0.055, 0.12, 0.14), (0, -0.93, 0.47),
                      color=wing, strength=2.6),
    ]

    groups = {
        "body": (body, (0, -0.1, 0.2)),
        "head": (head, (0, 0.3, 1.04)),
        "tail": ([tail_obj] + tail_fin, (0, -0.72, 0.32)),
    }
    groups.update(crescents)
    groups.update(arms)
    groups.update(wings)
    bk.assemble(root, groups)
    return bk.finish(root)


# ---------------------------------------------------------------------------
# Unicorn -- Divine, $1B/s.
# The most expensive-looking thing in the biome, so it gets the full treatment:
# a tall, long-legged white horse, a gold spiral horn built from stacked
# rotating blocks, a gold aureole standing behind the head, gold hooves, and a
# mane and tail that run the whole spectrum in big legible slabs. Everything
# else in the rift is dark and neon; this one is bright, which is what puts it
# at the top of the tree at a glance.
# ---------------------------------------------------------------------------

RAINBOW = ["#ff4d64", "#ff9a2e", "#ffe14d", "#4ee07c", "#3ec8ff", "#a865ff"]


def build_unicorn():
    kit.reset_scene()
    root = kit.empty("root")

    coat = "#fdfcff"
    shade = "#e0d9f4"
    muzzle = "#f4e9ff"
    gold = "#ffc94d"

    gold_mat = kit.mat("uni.gold", kit.hexcol(gold), rough=0.26, metal=0.75,
                       emission=kit.hexcol("#ffb02e"), emission_strength=0.8)

    body_dims = (0.36, 0.62, 0.4)
    body_at = (0, -0.06, 0.66)
    body = [bk.block("body.barrel", body_dims, body_at, color=coat)]
    body.append(bk.block("body.chest", (0.36, 0.22, 0.36), (0, 0.2, 0.68),
                         color=coat))
    body.append(bk.block("body.rump", (0.35, 0.17, 0.37), (0, -0.4, 0.68),
                         color=shade))
    body.append(bk.block("body.neck0", (0.22, 0.23, 0.25), (0, 0.29, 0.9),
                         color=coat))
    body.append(bk.block("body.neck1", (0.2, 0.2, 0.22), (0, 0.37, 1.06),
                         color=coat))
    body += bk.belly("body.barding", (0, 0.2, 0.68), (0.36, 0.22, 0.36),
                     color=shade, inset=0.6)
    # Gold barding: a medallion with a gem, and two shoulder studs. Trim, not
    # armour -- the horse still has to read as a horse.
    body.append(bk.block("body.medal", (0.12, 0.05, 0.12), (0, 0.32, 0.7),
                         material=gold_mat, segments=1))
    body += bk.gem("body.jewel", (0, 0.37, 0.7), size=0.1, color="#ff7ae0",
                   strength=3.2)
    for side, sign in (("L", 1), ("R", -1)):
        body.append(bk.slab("body.stud.%s" % side, (0.045, 0.14, 0.075),
                            (sign * 0.19, 0.02, 0.82), material=gold_mat))

    # Rainbow mane: seven fat slabs down the crest of the neck, standing proud
    # behind it so the colour is visible in profile and from the front.
    # The mane follows the crest of the NECK. Running it straight back drops
    # the last four slabs inside the barrel, where no camera ever sees them.
    for i in range(7):
        t = i / 6.0
        body.append(bk.slab(
            "body.mane%d" % i, (0.155, 0.17, 0.22 - 0.04 * t),
            (0, 0.3 - t * 0.2, 1.27 - t * 0.36),
            rot=(-14, 0, 0), color=RAINBOW[i % len(RAINBOW)]))

    head_dims = (0.21, 0.3, 0.23)
    head_at = (0, 0.46, 1.2)
    head = [bk.block("head.skull", head_dims, head_at, color=coat)]
    muzzle_at = (0, head_at[1] + 0.23, head_at[2] - 0.07)
    muzzle_dims = (0.17, 0.23, 0.16)
    head.append(bk.block("head.muzzle", muzzle_dims, muzzle_at, color=muzzle))
    head += bk.nostrils("head.nose", muzzle_at, muzzle_dims, spacing=0.4,
                        height=0.035, size=0.028, color="#b79ad0")
    head += bk.mouth("head.mouth", muzzle_at, muzzle_dims, width=0.085,
                     height=0.02, drop=-0.05, color="#b79ad0")
    head += bk.eyes("head.eye", head_at, head_dims, spacing=0.8, height=0.05,
                    size=0.065, style="white", iris="#3b2f6b", pupil_scale=0.5)
    for side, sign in (("L", 1), ("R", -1)):
        head.append(bk.slab("head.lash.%s" % side, (0.022, 0.08, 0.022),
                            (sign * 0.108, head_at[1] + 0.03,
                             head_at[2] + 0.12), material=gold_mat))
    ear_l, ear_r = bk.ears_pointed("ear", head_at, head_dims, size=0.07,
                                   spacing=0.66, length=0.15, color=coat,
                                   inner_color="#e8b6ff", lean=6)

    # The spiral horn: seven stacked blocks, each rotated further round than
    # the last. Stacked-and-twisted is the only way a voxel horn spirals.
    for i in range(7):
        t = i / 6.0
        s = 0.09 * (1 - 0.72 * t)
        head.append(bk.block("head.horn%d" % i, (s, s, 0.058),
                             (0, 0.55 + 0.013 * i, 1.32 + i * 0.051),
                             rot=(0, 0, 27 * i), material=gold_mat,
                             segments=1))
    head.append(bk.glow_block("head.hornspark", (0.032, 0.032, 0.045),
                              (0, 0.64, 1.67), color="#fff2c2", strength=4.4))
    # Forelock, between the ears, in the mane's colours.
    for i in range(2):
        head.append(bk.slab("head.forelock%d" % i, (0.075, 0.1, 0.1),
                            (-0.038 + i * 0.076, head_at[1] + 0.1,
                             head_at[2] + 0.15),
                            rot=(-24, 0, 0), color=RAINBOW[i]))

    # Aureole: a gold ring standing behind the head. This single part is what
    # makes the pet look like a $1B item rather than a white pony.
    halo = bk.ring("head.halo", (0, 0.22, 1.28), radius=0.29, thickness=0.024,
                   tilt=0, color=gold, strength=2.6)[0]
    _set_rot(halo, (90, 0, 0))
    head.append(halo)

    legs = bk.legs_quad("leg", front=(0.14, 0.2, 0.48), back=(0.15, -0.28, 0.48),
                        length=0.46, thickness=0.1, color=coat,
                        foot_color=gold)

    # Rainbow tail: six slabs falling and flaring behind the rump, full run of
    # the spectrum so it reads as rainbow and not as "an orange block".
    tail_parts = [bk.slab("tail.dock", (0.12, 0.13, 0.13), (0, -0.44, 0.86),
                          color=shade)]
    for i in range(6):
        t = i / 5.0
        tail_parts.append(bk.slab(
            "tail.fall%d" % i, (0.16 - 0.014 * i, 0.15, 0.17),
            (0, -0.52 - t * 0.14, 0.82 - t * 0.56),
            rot=(16 * t, 0, 0), color=RAINBOW[i]))

    groups = {
        "body": (body, (0, 0, 0.44)),
        "head": (head, (0, 0.38, 1.08)),
        "ear.L": ([ear_l], tuple(ear_l.location)),
        "ear.R": ([ear_r], tuple(ear_r.location)),
        "tail": (tail_parts, (0, -0.44, 0.86)),
    }
    for key, obj in legs.items():
        groups[key] = ([obj], tuple(obj.location))
    bk.assemble(root, groups)
    return bk.finish(root)


PETS = {
    "centipede": build_centipede,
    "cosmic-gecko": build_cosmic_gecko,
    "cosmic-gorilla": build_cosmic_gorilla,
    "ringhorn-bovid": build_ringhorn_bovid,
    "cosmic-skeleton-boss": build_cosmic_skeleton_boss,
    "cosmic-dragon": build_cosmic_dragon,
    "eternal-lunar-dragon": build_eternal_lunar_dragon,
    "unicorn": build_unicorn,
}
