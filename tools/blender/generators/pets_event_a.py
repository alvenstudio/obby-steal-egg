"""
Limited / Event pets, part one -- nine oddities that only ever show up during
a live event, so they are allowed to be louder than any biome roster.

Palette rules this module applies everywhere:

  * Saturated novelty colours. Banana yellow next to pool blue, mango orange
    next to hot pink, chocolate brown next to cream. Nothing is muted.
  * High contrast inside a single creature. Every pet here has at least one
    pairing that would be a mistake in a "real" biome -- gold on matte black,
    lime glow on gunmetal, gold foil on chocolate.
  * The gag has to survive at icon size. A mallet, a banana peel, a pair of
    sunglasses, a mango: each of these is a shape you can read at 24px, and
    each pet is built so that shape owns the silhouette.

Rarity ladder, and what "more expensive" means visually here:
    rare      mallet-sentry   painted wood, no light
    epic      peelfin         a costume, still no light
    event     scorpio         first gold trim + one emissive point
    mythic    bellug          gold collar, emissive bell, a struck-note ring
    event     froggo          gold chain, mirrored lenses
    cosmic    mangowing       orbital halo, floating gems, glowing wingtips
    event     crawler         glowing underside, the whole belly is a lamp
    secret    cocoa-croc      gold foil, molten caramel emission
    event     crocodon        ember-cracked spikes, the biggest silhouette

Proportion note, learned from the first contact sheet: `finish()` normalises
HEIGHT, so a long flat animal comes out enormous next to a tall thin one.
Every long creature here (both crocodiles, the crawler, the scorpion) is
therefore built standing tall on its legs with a lifted tail, and the
scorpion's sting arc is capped just above its own back rather than towering
over it -- otherwise the arc wins the normalisation and the animal underneath
shrinks to a smear.
"""

import math

from mathutils import Vector

import blockkit as bk
import kit


# ---------------------------------------------------------------------------
# Local helpers.
#
# Three things this module needs that blockkit does not ship: a box drawn
# between two arbitrary joints (every insect leg here), a smile that actually
# curves upward, and cached emissive/glossy materials. Solving each once keeps
# nine builders from re-deriving the same euler angles.
# ---------------------------------------------------------------------------


def _neon(color, strength=2.8):
    """Cached emissive material. Strength belongs in the key or the cache lies."""
    return kit.mat(
        "ev.glow.%s.%d" % (color.strip("#"), int(strength * 10)),
        kit.hexcol(color), rough=0.18, emission=kit.hexcol(color),
        emission_strength=strength,
    )


def _gloss(color, rough=0.24):
    """Cached low-roughness material -- chocolate, lacquer, sunglass lenses."""
    return kit.mat("ev.gloss.%s.%d" % (color.strip("#"), int(rough * 100)),
                   kit.hexcol(color), rough=rough)


def _mirror(left, name):
    """The .R twin of a part authored on the +X flank."""
    right = kit.duplicate(left, name, mirror=True)
    right.location = Vector((-left.location.x, left.location.y, left.location.z))
    return right


def _strut(name, a, b, thickness, color=None, material=None, taper=0.0,
           width=None):
    """
    A box drawn between two joint positions.

    Everything spindly in this module -- scorpion legs, crawler legs, antennae,
    claw arms -- is a chain of these. `taper` pinches the far end, which is
    what turns the last segment of a leg into a point.
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


def _smile(name, face_center, width=0.3, height=0.05, drop=-0.12, curve=0.06,
           color="#241a1e", face="front", segments=5, material=None):
    """
    A mouth whose ENDS RISE.

    bk.mouth(style="grin") drops its outer segments, which reads as a frown on
    anything with a wide face; four of the nine pets here live or die on a
    smile, so they get their own.
    """
    parts = []
    for i in range(segments):
        t = (i / (segments - 1)) * 2 - 1
        parts.append(bk.face_plate(
            "%s.%d" % (name, i), face_center,
            (width / segments * 1.35, height), face=face,
            color=color, material=material, depth=0.02,
            offset=(t * width * 0.5, drop + curve * (t * t)),
        ))
    return parts


def _teeth(name, face_center, width, height, drop, count=4, color="#fdf7e8",
           face="front"):
    """A row of blocky teeth hanging inside a mouth plate."""
    parts = []
    for i in range(count):
        t = (i + 0.5) / count - 0.5
        parts.append(bk.face_plate(
            "%s.%d" % (name, i), face_center,
            (width / count * 0.62, height), face=face, color=color,
            depth=0.018, offset=(t * width, drop), proud=bk.PROUD * 3.4,
        ))
    return parts


def _jaw_fangs(name, at, count, spread, size, length, color, down=True,
               spacing=0.07):
    """
    A row of tapered fangs standing on (or hanging from) a jaw line.
    `at` is the front of the jaw's tooth line; fangs march backward along -Y.
    """
    parts = []
    for i in range(count):
        y = at[1] - i * spacing
        for side, sign in (("L", 1), ("R", -1)):
            parts.append(bk.wedge(
                "%s.%s%d" % (name, side, i), (size, size, length),
                (sign * spread, y,
                 at[2] + (-length * 0.45 if down else length * 0.45)),
                rot=(180 if down else 0, 0, 0), color=color, taper=0.82,
            ))
    return parts


# ===========================================================================
# Mallet Sentry -- Rare, $100/s.
#
# A wooden watchman whose head is the mallet. The joke only lands if the mallet
# is genuinely oversized, so the head block is three times the torso's width --
# a wide crossbar, never a cube -- with iron end caps and a painted stripe. The
# handle sticks visibly out of the collar underneath it, which is what makes
# the head read as a tool rather than as a square face. Big square boots stop
# the whole thing from reading as a lollipop.
# ===========================================================================

def build_mallet_sentry():
    kit.reset_scene()
    root = kit.empty("root")

    wood = "#c9954f"
    wood_dk = "#8a5a2c"
    wood_lt = "#e8c88d"
    iron = "#7f8896"
    iron_dk = "#4e5665"
    paint = "#e0453c"
    gold = "#f2c141"

    # -- torso: deliberately undersized, with a sentry's badge on the chest --
    body_dims = (0.22, 0.20, 0.24)
    body_at = (0, 0.0, 0.52)
    body = [bk.block("body.core", body_dims, body_at, color=wood)]
    body.append(bk.slab("body.belt", (0.25, 0.23, 0.05),
                        (0, 0.0, 0.41), color=wood_dk))
    body.append(bk.slab("body.buckle", (0.07, 0.05, 0.05),
                        (0, 0.12, 0.41), color=gold))
    body.append(bk.slab("body.shoulders", (0.30, 0.19, 0.06),
                        (0, 0.0, 0.63), color=wood_dk))
    body.append(bk.face_plate("body.badge", bk.face_of(body_at, body_dims, "front"),
                              (0.09, 0.09), face="front", color=gold,
                              depth=0.02, offset=(0, 0.02)))
    # The handle belongs to the BODY, so the mallet pivots on top of it.
    body.append(bk.cylinder("body.handle", r=0.042, h=0.20,
                            loc=(0, 0.03, 0.74), color=wood_lt, verts=10))
    body.append(bk.slab("body.collar", (0.10, 0.10, 0.04),
                        (0, 0.03, 0.67), color=iron_dk))

    # -- head: the mallet itself, a wide crossbar lying along X -------------
    head_dims = (0.72, 0.22, 0.21)
    head_at = (0, 0.03, 0.90)
    head = [bk.block("head.mallet", head_dims, head_at, color=wood)]
    for side, sign in (("L", 1), ("R", -1)):
        head.append(bk.block("head.cap.%s" % side, (0.10, 0.25, 0.24),
                             (sign * 0.33, head_at[1], head_at[2]), color=iron))
        head.append(bk.slab("head.band.%s" % side, (0.03, 0.27, 0.26),
                            (sign * 0.26, head_at[1], head_at[2]), color=iron_dk))
        head.append(bk.slab("head.rivet.%s" % side, (0.03, 0.05, 0.05),
                            (sign * 0.383, head_at[1] + 0.05, head_at[2] + 0.06),
                            color=iron_dk))
    # Painted bands sit OUTBOARD of the face, not across it -- a stripe
    # through the middle turns the eyes into part of the paintwork.
    for side, sign in (("L", 1), ("R", -1)):
        head.append(bk.slab("head.stripe.%s" % side, (0.07, 0.235, 0.225),
                            (sign * 0.21, head_at[1], head_at[2]), color=paint))
    # Face painted on the front of the mallet head.
    head += bk.eyes("head.eye", head_at, head_dims, spacing=0.30, height=0.035,
                    size=0.058, style="white", iris="#241a14", pupil_scale=0.6)
    head += _smile("head.mouth", bk.face_of(head_at, head_dims, "front"),
                   width=0.12, height=0.026, drop=-0.07, curve=0.026,
                   color="#3d2a1c", segments=3)
    head.append(bk.slab("head.brim", (0.74, 0.06, 0.045),
                        (0, head_at[1] + 0.11, head_at[2] + 0.12), color=wood_dk))

    # -- arms: stubby, so the mallet stays the biggest thing on the model ---
    arm_l, arm_r = bk.arms("arm", (0.14, 0.0, 0.61), length=0.20, thickness=0.07,
                           color=wood_dk, hand_color=wood_lt, angle=18)

    # -- boots: wide, deep and square. The counterweight to the mallet. ----
    def boot(name, sign):
        hip = (sign * 0.10, 0.0, 0.40)
        parts = [
            bk.block(name + ".shin", (0.085, 0.085, 0.24),
                     (hip[0], hip[1], hip[2] - 0.12), color=wood_dk),
            bk.block(name + ".boot", (0.21, 0.30, 0.13),
                     (hip[0], hip[1] + 0.05, 0.09), color=wood),
            bk.slab(name + ".toecap", (0.20, 0.09, 0.10),
                    (hip[0], hip[1] + 0.17, 0.09), color=iron),
            bk.slab(name + ".sole", (0.22, 0.31, 0.035),
                    (hip[0], hip[1] + 0.05, 0.022), color=iron_dk),
        ]
        merged = kit.join(parts, name)
        kit.weld(merged)
        kit.set_origin_to(merged, hip)
        return merged

    leg_l = boot("leg.FL", 1)
    leg_r = _mirror(leg_l, "leg.FR")

    bk.assemble(root, {
        "body": (body, (0, 0, 0.34)),
        "head": (head, (0, 0.03, 0.79)),
        "arm.L": ([arm_l], tuple(arm_l.location)),
        "arm.R": ([arm_r], tuple(arm_r.location)),
        "leg.FL": ([leg_l], tuple(leg_l.location)),
        "leg.FR": ([leg_r], tuple(leg_r.location)),
    })
    return bk.finish(root)


# ===========================================================================
# Peelfin -- Epic, $400/s.
#
# A dolphin wearing a banana peel as a hood. Two shapes fight for the
# silhouette, so they are separated by axis: the dolphin is all horizontal
# (long body, low rostrum, tall dorsal, swept flukes) and the peel is all
# vertical (a cap with four strips falling off it -- one over the brow, one
# down each cheek, one down the back). Yellow on blue, no third hue.
# ===========================================================================

def build_peelfin():
    kit.reset_scene()
    root = kit.empty("root")

    blue = "#3d8fd8"
    blue_dk = "#245f96"
    pale = "#cbe8ff"
    peel = "#ffd93b"
    peel_dk = "#dda914"
    inner = "#fff6d0"
    stem = "#7a5a24"

    # -- body: a long torpedo that thins toward the flukes -----------------
    body_dims = (0.31, 0.58, 0.31)
    body_at = (0, -0.10, 0.46)
    body = [bk.block("body.core", body_dims, body_at, color=blue)]
    body.append(bk.block("body.peduncle", (0.16, 0.24, 0.16),
                         (0, -0.48, 0.44), color=blue_dk))
    body += bk.belly("body.belly", body_at, body_dims, color=pale, inset=0.72)
    for side, sign in (("L", 1), ("R", -1)):
        body.append(bk.slab("body.flank.%s" % side, (0.03, 0.44, 0.10),
                            (sign * 0.157, -0.10, 0.36), color=pale))
    # Dorsal fin -- the one part that says "dolphin" from every angle.
    body.append(bk.wedge("body.dorsal", (0.055, 0.22, 0.28),
                         (0, -0.22, 0.73), rot=(-28, 0, 0),
                         color=blue_dk, taper=0.66))

    # -- head: melon, long rostrum, and the permanent dolphin smile --------
    head_dims = (0.28, 0.26, 0.28)
    head_at = (0, 0.34, 0.54)
    head = [bk.block("head.melon", head_dims, head_at, color=blue)]
    head.append(bk.block("head.brow", (0.24, 0.18, 0.09),
                         (0, 0.32, 0.70), color=blue))
    head.append(bk.wedge("head.rostrum", (0.115, 0.115, 0.26),
                         (0, 0.60, 0.44), rot=(-90, 0, 0),
                         color=pale, taper=0.4))
    head.append(bk.slab("head.jaw", (0.105, 0.22, 0.035),
                        (0, 0.58, 0.385), color=blue_dk))
    head += bk.eyes("head.eye", head_at, head_dims, spacing=0.66, height=0.02,
                    size=0.065, style="white", iris="#14202e", pupil_scale=0.58)
    head += _smile("head.smile", bk.face_of(head_at, head_dims, "front"),
                   width=0.20, height=0.03, drop=-0.10, curve=0.04,
                   color="#1d3348", segments=5)
    head.append(bk.slab("head.blowhole", (0.05, 0.04, 0.02),
                        (0, 0.28, 0.695), color=blue_dk))

    # -- the peel: cap, brow strip, back strip, and side strips as ears ----
    head.append(bk.block("head.peelcap", (0.32, 0.30, 0.10),
                         (0, 0.34, 0.74), color=peel))
    head.append(bk.slab("head.peelcap.rim", (0.33, 0.31, 0.028),
                        (0, 0.34, 0.688), color=peel_dk))
    # The back strip DROOPS. A wedge grows along +Z, so anything under 90
    # degrees of X rotation stands up like an ear instead of falling like peel.
    back_strip = bk.block("head.peel.back", (0.15, 0.12, 0.30),
                          (0, 0.15, 0.59), rot=(16, 0, 0), color=peel)
    kit.taper(back_strip, axis="Z", at_min=0.55, at_max=1.0)
    head.append(back_strip)
    head.append(bk.slab("head.peel.back.tip", (0.10, 0.09, 0.045),
                        (0, 0.11, 0.45), color=inner))
    head.append(bk.block("head.stem", (0.06, 0.06, 0.10),
                         (0, 0.32, 0.84), color=stem))

    peel_ears = []
    for side, sign in (("L", 1), ("R", -1)):
        anchor = (sign * 0.15, 0.34, 0.74)
        parts = [
            bk.wedge("ear.%s.strip" % side, (0.11, 0.20, 0.32),
                     (sign * 0.215, 0.33, 0.56), rot=(0, -sign * 22, 0),
                     color=peel, taper=0.36),
            bk.slab("ear.%s.inner" % side, (0.035, 0.13, 0.22),
                    (sign * 0.175, 0.33, 0.58), rot=(0, -sign * 22, 0),
                    color=inner),
            bk.slab("ear.%s.tip" % side, (0.075, 0.10, 0.05),
                    (sign * 0.245, 0.33, 0.415), color=inner),
        ]
        merged = kit.join(parts, "ear.%s" % side)
        kit.weld(merged)
        kit.set_origin_to(merged, anchor)
        peel_ears.append(merged)

    fin_l, fin_r = bk.fins("fin", (0.15, 0.04, 0.38), size=0.27, thickness=0.05,
                           color=blue_dk, tilt=30)
    fluke = bk.fin_tail("fin.tail", (0, -0.58, 0.44), size=0.32, thickness=0.05,
                        color=blue_dk, lobes=2)

    bk.assemble(root, {
        "body": (body, (0, -0.10, 0.30)),
        "head": (head, (0, 0.22, 0.44)),
        "ear.L": ([peel_ears[0]], tuple(peel_ears[0].location)),
        "ear.R": ([peel_ears[1]], tuple(peel_ears[1].location)),
        "fin.L": ([fin_l], tuple(fin_l.location)),
        "fin.R": ([fin_r], tuple(fin_r.location)),
        "fin.tail": ([fluke], (0, -0.58, 0.44)),
    })
    return bk.finish(root)


# ===========================================================================
# Scorpio -- Event, $10K/s.
#
# Sleek black and gold. The read is two things and nothing else: the raised
# sting arc and the pincers, so the body between them is kept low, dark and
# deep. Gold appears only on trailing edges, the spine line, the claw trim and
# the sting -- restraint is what makes the gold look expensive rather than
# sprayed on.
# ===========================================================================

def build_scorpio():
    kit.reset_scene()
    root = kit.empty("root")

    chitin = "#20222e"
    chitin_lt = "#454b60"
    gold = "#e8b23c"
    gold_lt = "#ffdc84"
    amber = "#ffb020"

    # -- mesosoma: three deep plates, each with a gold trailing edge --------
    body = []
    for i, (dy, w, d, h) in enumerate((
        (-0.24, 0.38, 0.24, 0.24),
        (-0.02, 0.44, 0.24, 0.27),
        (0.20, 0.40, 0.22, 0.24),
    )):
        at = (0, dy, 0.42)
        body.append(bk.block("body.seg%d" % i, (w, d, h), at, color=chitin))
        # One narrow gold keel down the spine. That is the whole dorsal
        # budget -- anything wider and the shell stops reading as black.
        body.append(bk.slab("body.spine%d" % i, (0.075, d * 0.92, 0.04),
                            (0, dy, 0.425 + h * 0.5), color=gold))
        body.append(bk.slab("body.seam%d" % i, (w * 0.9, 0.035, h * 0.85),
                            (0, dy - d * 0.5, 0.42), color=chitin_lt))
        for side, sign in (("L", 1), ("R", -1)):
            body.append(bk.slab(
                "body.gloss%d.%s" % (i, side), (0.025, d * 0.7, h * 0.4),
                (sign * w * 0.5, dy, 0.42 + h * 0.16), color=chitin_lt))

    # -- head / prosoma: pushed well forward of the plates ------------------
    head_dims = (0.34, 0.24, 0.22)
    head_at = (0, 0.44, 0.44)
    head = [bk.block("head.prosoma", head_dims, head_at, color=chitin)]
    head.append(bk.slab("head.crown", (0.13, 0.21, 0.045),
                        (0, 0.44, 0.555), color=gold))
    head += bk.eyes("head.eye", head_at, head_dims, spacing=0.42, height=0.04,
                    size=0.055, style="glow", iris=amber)
    head += bk.eyes("head.eye.side", head_at, head_dims, spacing=0.82,
                    height=0.0, size=0.032, style="glow", iris=gold_lt)
    for side, sign in (("L", 1), ("R", -1)):
        head.append(bk.wedge("head.chelicera.%s" % side, (0.05, 0.05, 0.11),
                             (sign * 0.055, 0.58, 0.39), rot=(-96, 0, 0),
                             color=gold, taper=0.7))

    # -- pincers: the widest thing on the model, held forward and open -----
    def pincer(side, sign):
        shoulder = (sign * 0.18, 0.46, 0.44)
        elbow = (sign * 0.36, 0.60, 0.40)
        parts = [
            _strut("arm.%s.coxa" % side, shoulder, elbow, 0.095, color=chitin),
            bk.block("arm.%s.palm" % side, (0.21, 0.28, 0.16),
                     (sign * 0.41, 0.77, 0.39), rot=(0, 0, -sign * 14),
                     color=chitin),
            bk.slab("arm.%s.palm.trim" % side, (0.22, 0.07, 0.15),
                    (sign * 0.42, 0.89, 0.39), rot=(0, 0, -sign * 14),
                    color=gold),
            bk.wedge("arm.%s.finger.fix" % side, (0.06, 0.06, 0.24),
                     (sign * 0.49, 1.02, 0.41), rot=(-84, 0, -sign * 18),
                     color=chitin_lt, taper=0.7),
            bk.wedge("arm.%s.finger.mov" % side, (0.06, 0.06, 0.20),
                     (sign * 0.33, 1.01, 0.365), rot=(-98, 0, sign * 16),
                     color=gold, taper=0.7),
        ]
        merged = kit.join(parts, "arm.%s" % side)
        kit.weld(merged)
        kit.set_origin_to(merged, shoulder)
        return merged

    arm_l = pincer("L", 1)
    arm_r = pincer("R", -1)

    # -- eight walking legs, grouped four per animation slot ----------------
    def walk_leg(name, sign, hy, out, back):
        hip = (sign * 0.17, hy, 0.42)
        knee = (sign * (0.17 + out), hy + back * 0.5, 0.52)
        foot = (sign * (0.19 + out), hy + back, 0.02)
        parts = [
            _strut(name + ".femur", hip, knee, 0.07, color=chitin_lt),
            _strut(name + ".tibia", knee, foot, 0.058, color=chitin_lt,
                   taper=0.45),
        ]
        merged = kit.join(parts, name)
        kit.weld(merged)
        kit.set_origin_to(merged, hip)
        return merged

    front_l, front_r, back_l, back_r = [], [], [], []
    for i, (hy, out, back) in enumerate((
        (0.26, 0.17, 0.05),
        (0.11, 0.19, 0.0),
        (-0.05, 0.19, -0.07),
        (-0.21, 0.16, -0.15),
    )):
        left = walk_leg("leg.L%d" % i, 1, hy, out, back)
        right = _mirror(left, "leg.R%d" % i)
        (front_l if i < 2 else back_l).append(left)
        (front_r if i < 2 else back_r).append(right)

    # -- metasoma: five segments arcing back, up and over the plates -------
    arc = [
        (0, -0.40, 0.50), (0, -0.56, 0.66), (0, -0.56, 0.86),
        (0, -0.38, 1.00), (0, -0.13, 1.03), (0, 0.12, 0.93),
    ]
    tail_parts = []
    for i in range(len(arc) - 1):
        t = i / float(len(arc) - 2)
        tail_parts.append(_strut("tail.seg%d" % i, arc[i], arc[i + 1],
                                 0.15 - 0.04 * t, color=chitin))
        # Slim gold rings between segments, not gold barrels: the arc has to
        # stay a black chain with gold joints.
        tail_parts.append(bk.block("tail.knuckle%d" % i,
                                   (0.155 - 0.04 * t, 0.045, 0.155 - 0.04 * t),
                                   arc[i + 1], color=gold))
    tail_parts.append(bk.wedge("tail.stinger", (0.115, 0.115, 0.26),
                               (0, 0.27, 0.84), rot=(-152, 0, 0),
                               color=gold_lt, taper=0.88))
    tail_parts += bk.gem("tail.venom", (0, 0.395, 0.76), size=0.09,
                         color=amber, strength=3.8)

    bk.assemble(root, {
        "body": (body, (0, 0, 0.32)),
        "head": (head, (0, 0.33, 0.38)),
        "arm.L": ([arm_l], tuple(arm_l.location)),
        "arm.R": ([arm_r], tuple(arm_r.location)),
        "tail": (tail_parts, (0, -0.36, 0.48)),
        "leg.FL": (front_l, (0.17, 0.20, 0.42)),
        "leg.FR": (front_r, (-0.17, 0.20, 0.42)),
        "leg.BL": (back_l, (0.17, -0.12, 0.42)),
        "leg.BR": (back_r, (-0.17, -0.12, 0.42)),
    })
    return bk.finish(root)


# ===========================================================================
# Bellug -- Mythic, $40K/s.
#
# A chubby beluga wearing a bell collar. Mythic tier, so it carries light: the
# clapper is emissive and a thin ring hangs off the bell's mouth like a struck
# note. The body is deliberately over-round -- a beluga's charm is that it has
# no edges, and the only way to say that in boxes is wide, short, and bulging
# underneath, with a melon that overhangs the face.
# ===========================================================================

def build_bellug():
    kit.reset_scene()
    root = kit.empty("root")

    white = "#f2f6fa"
    shade = "#c6d9ec"
    blush = "#f9c8cd"
    gold = "#f0c04a"
    gold_dk = "#b98a22"
    chime = "#fff3b8"

    # -- body: wide, short, and hanging low in the middle -------------------
    body_dims = (0.52, 0.52, 0.48)
    body_at = (0, -0.18, 0.56)
    hull = bk.block("body.core", body_dims, body_at, color=white)
    # Fat at the chest, narrowing to the flukes -- a beluga is a teardrop.
    kit.taper(hull, axis="Y", at_min=0.68, at_max=1.0)
    body = [hull]
    body.append(bk.block("body.paunch", (0.46, 0.44, 0.20),
                         (0, -0.16, 0.34), color=white))
    body.append(bk.slab("body.cape", (0.34, 0.42, 0.045),
                        (0, -0.20, 0.79), color=shade))
    # A shaded groove where the melon meets the back -- without it the head
    # and torso weld into one featureless white cube at icon size.
    body.append(bk.block("body.neck.groove", (0.40, 0.05, 0.36),
                         (0, 0.09, 0.60), color=shade))
    body.append(bk.block("body.peduncle", (0.21, 0.24, 0.20),
                         (0, -0.53, 0.54), color=shade))
    for side, sign in (("L", 1), ("R", -1)):
        body.append(bk.slab("body.crease.%s" % side, (0.03, 0.38, 0.12),
                            (sign * 0.262, -0.18, 0.42), color=shade))

    # -- head: a big soft melon set well forward, with a tiny happy face ---
    head_dims = (0.40, 0.36, 0.38)
    head_at = (0, 0.34, 0.66)
    melon = bk.block("head.melon", head_dims, head_at, color=white)
    kit.taper(melon, axis="Z", at_min=1.0, at_max=0.86)
    head = [melon]
    head.append(bk.block("head.crown", (0.32, 0.30, 0.14),
                         (0, 0.30, 0.90), color=white))
    head.append(bk.block("head.jaw", (0.32, 0.24, 0.12),
                         (0, 0.44, 0.475), color=shade))
    head += bk.eyes("head.eye", head_at, head_dims, spacing=0.52, height=0.045,
                    size=0.062, style="white", iris="#1a2430", pupil_scale=0.62)
    head += bk.cheeks("head.cheek", head_at, head_dims, spacing=0.74,
                      height=-0.05, size=0.105, color=blush)
    head += _smile("head.smile", bk.face_of(head_at, head_dims, "front"),
                   width=0.25, height=0.034, drop=-0.115, curve=0.05,
                   color="#2b3a4a", segments=5)
    head.append(bk.slab("head.blowhole", (0.06, 0.05, 0.02),
                        (0, 0.24, 0.972), color=shade))

    # -- collar: a chunky gold band round the neck, bell hung under the chin
    collar = []
    for i in range(10):
        angle = (i / 10.0) * math.tau
        collar.append(bk.block(
            "body.collar%d" % i, (0.085, 0.07, 0.085),
            (math.sin(angle) * 0.255, 0.13, 0.58 + math.cos(angle) * 0.255),
            rot=(0, math.degrees(angle), 0), color=gold,
        ))
    collar.append(bk.block("body.collar.knot", (0.12, 0.09, 0.10),
                           (0, 0.16, 0.85), color=gold_dk))
    # The bell: strap, tapered cup, lip and a lit clapper -- hung out front
    # under the chin where the 3/4 hero angle can actually see it.
    collar.append(bk.block("body.bell.strap", (0.055, 0.055, 0.13),
                           (0, 0.38, 0.44), color=gold_dk))
    collar.append(bk.wedge("body.bell.cup", (0.21, 0.20, 0.20),
                           (0, 0.40, 0.30), rot=(180, 0, 0), color=gold,
                           taper=0.44))
    collar.append(bk.slab("body.bell.lip", (0.23, 0.22, 0.045),
                          (0, 0.40, 0.203), color=gold_dk))
    collar += bk.gem("body.bell.clapper", (0, 0.40, 0.185), size=0.09,
                     color=chime, strength=3.8)
    collar += bk.gem("body.spark.L", (0.24, 0.42, 0.30), size=0.055,
                     color=chime, strength=3.2)
    collar += bk.gem("body.spark.R", (-0.21, 0.38, 0.15), size=0.045,
                     color=chime, strength=3.2)
    body += collar

    fin_l, fin_r = bk.fins("fin", (0.25, 0.02, 0.40), size=0.34, thickness=0.07,
                           color=shade, tilt=34)
    fluke = bk.fin_tail("fin.tail", (0, -0.66, 0.54), size=0.40, thickness=0.07,
                        color=shade, lobes=2)

    bk.assemble(root, {
        "body": (body, (0, -0.18, 0.34)),
        "head": (head, (0, 0.17, 0.50)),
        "fin.L": ([fin_l], tuple(fin_l.location)),
        "fin.R": ([fin_r], tuple(fin_r.location)),
        "fin.tail": ([fluke], (0, -0.66, 0.54)),
    })
    return bk.finish(root)


# ===========================================================================
# Froggo -- Event, $50K/s.
#
# A big grinning green frog in sunglasses. Frogs read from three things: a
# mouth wider than the skull, eyes ON TOP rather than in front, and folded
# rear thighs sitting higher than the knees. The sunglasses bar spans both eye
# domes as one piece, because two separate lenses vanish at icon size, and a
# gold chain slung across the chest supplies the mandatory absurdity.
# ===========================================================================

def build_froggo():
    kit.reset_scene()
    root = kit.empty("root")

    green = "#5ecb3a"
    green_dk = "#2b8c1e"
    green_lt = "#96e969"
    belly = "#eaf5bd"
    shades = "#141018"
    lens = "#2a2f3c"
    gold = "#f5cb46"

    # -- body: wide, low and squat, pulled back so the head overhangs ------
    body_dims = (0.58, 0.44, 0.32)
    body_at = (0, -0.12, 0.30)
    body = [bk.block("body.core", body_dims, body_at, color=green)]
    body += bk.belly("body.belly", body_at, body_dims, color=belly, inset=0.8)
    body.append(bk.slab("body.underbelly", (0.48, 0.38, 0.05),
                        (0, -0.12, 0.155), color=belly))
    body.append(bk.slab("body.back", (0.50, 0.36, 0.045),
                        (0, -0.14, 0.462), color=green_dk))
    body += bk.spots("body.wart", body_at, body_dims, count=6, size=0.075,
                     color=green_dk, seed=7, faces=("top", "left", "right"))
    # Gold chain, slung proud of the chest face so it never sinks into the
    # torso; the pendant is the low point of the curve.
    for i in range(7):
        t = (i / 6.0) * 2 - 1
        body.append(bk.block("body.chain%d" % i, (0.06, 0.05, 0.06),
                             (t * 0.21, 0.118, 0.36 - (1 - t * t) * 0.11),
                             color=gold))
    body.append(bk.slab("body.pendant", (0.10, 0.055, 0.10),
                        (0, 0.128, 0.215), color=gold))

    # -- head: wider than the body, overhanging it forward and above -------
    head_dims = (0.60, 0.34, 0.25)
    head_at = (0, 0.30, 0.58)
    head = [bk.block("head.skull", head_dims, head_at, color=green)]
    head.append(bk.slab("head.lip", (0.60, 0.32, 0.05),
                        (0, 0.30, 0.463), color=green_lt))
    head += _smile("head.grin", bk.face_of(head_at, head_dims, "front"),
                   width=0.48, height=0.055, drop=-0.055, curve=0.08,
                   color="#1c2a12", segments=7)
    head += _teeth("head.tooth", bk.face_of(head_at, head_dims, "front"),
                   width=0.20, height=0.038, drop=-0.028, count=2,
                   color="#f7fbe6")
    # Eye domes on TOP of the skull, not on the face.
    for side, sign in (("L", 1), ("R", -1)):
        head.append(bk.block("head.dome.%s" % side, (0.23, 0.22, 0.19),
                             (sign * 0.18, 0.28, 0.79), color=green))
        head.append(bk.slab("head.dome.rim.%s" % side, (0.24, 0.23, 0.03),
                            (sign * 0.18, 0.28, 0.695), color=green_dk))
    # One sunglass bar across both domes, plus temples down the sides.
    head.append(bk.block("head.shades", (0.54, 0.055, 0.14),
                         (0, 0.395, 0.805), color=shades))
    for side, sign in (("L", 1), ("R", -1)):
        head.append(bk.slab("head.lens.%s" % side, (0.21, 0.02, 0.10),
                            (sign * 0.17, 0.426, 0.805),
                            material=_gloss(lens, 0.12)))
        head.append(bk.slab("head.glint.%s" % side, (0.05, 0.02, 0.065),
                            (sign * 0.215, 0.438, 0.825), rot=(0, -22, 0),
                            material=_neon("#d8f6ff", 1.6)))
        head.append(bk.slab("head.temple.%s" % side, (0.035, 0.20, 0.035),
                            (sign * 0.283, 0.30, 0.805), color=shades))
        head.append(bk.slab("head.nostril.%s" % side, (0.032, 0.03, 0.026),
                            (sign * 0.05, 0.472, 0.625), color=green_dk))

    # -- rear legs folded high, front legs propping the chest up -----------
    def rear_leg(name, sign):
        hip = (sign * 0.27, -0.16, 0.34)
        parts = [
            bk.block(name + ".thigh", (0.16, 0.26, 0.25),
                     (sign * 0.29, -0.16, 0.31), rot=(0, -sign * 8, 0),
                     color=green),
            bk.block(name + ".shin", (0.12, 0.24, 0.14),
                     (sign * 0.29, -0.02, 0.13), color=green_dk),
            bk.slab(name + ".foot", (0.18, 0.26, 0.055),
                    (sign * 0.29, 0.13, 0.035), color=green_lt),
            bk.slab(name + ".web", (0.20, 0.10, 0.035),
                    (sign * 0.29, 0.24, 0.035), color=green_lt),
        ]
        merged = kit.join(parts, name)
        kit.weld(merged)
        kit.set_origin_to(merged, hip)
        return merged

    def front_leg(name, sign):
        hip = (sign * 0.20, 0.08, 0.24)
        parts = [
            bk.block(name + ".arm", (0.075, 0.075, 0.21),
                     (sign * 0.21, 0.10, 0.14), rot=(0, -sign * 6, 0),
                     color=green),
            bk.slab(name + ".hand", (0.13, 0.15, 0.045),
                    (sign * 0.22, 0.15, 0.028), color=green_lt),
        ]
        merged = kit.join(parts, name)
        kit.weld(merged)
        kit.set_origin_to(merged, hip)
        return merged

    rear_l = rear_leg("leg.BL", 1)
    rear_r = _mirror(rear_l, "leg.BR")
    front_l = front_leg("leg.FL", 1)
    front_r = _mirror(front_l, "leg.FR")

    bk.assemble(root, {
        "body": (body, (0, -0.12, 0.16)),
        "head": (head, (0, 0.14, 0.47)),
        "leg.BL": ([rear_l], tuple(rear_l.location)),
        "leg.BR": ([rear_r], tuple(rear_r.location)),
        "leg.FL": ([front_l], tuple(front_l.location)),
        "leg.FR": ([front_r], tuple(front_r.location)),
    })
    return bk.finish(root)


# ===========================================================================
# Mangowing -- Cosmic, $800K/s.
#
# A parrot whose body IS a mango: tall, fat at the bottom, orange fading to
# hot pink on the shoulder and yellow on the belly, with the fruit's stem and
# leaf serving as the crest. Cosmic tier, so it wears the full signature -- a
# tilted halo orbiting the fruit, floating gems, and emissive wing and tail
# tips.
# ===========================================================================

def build_mangowing():
    kit.reset_scene()
    root = kit.empty("root")

    mango = "#ff8a1e"
    mango_r = "#ff3f62"
    mango_y = "#ffd23a"
    mango_dk = "#cc5209"
    leaf = "#3fbf4a"
    stem = "#7a5a2a"
    beak = "#3f3540"
    beak_lt = "#7a6b76"
    halo = "#ffd36a"

    # -- body: the fruit. Tall, fat at the bottom, blushed on the shoulder --
    body_dims = (0.44, 0.40, 0.54)
    body_at = (0, -0.04, 0.58)
    fruit = bk.block("body.mango", body_dims, body_at, color=mango)
    # The mango profile: heavy at the base, pinched toward the stem.
    kit.taper(fruit, axis="Z", at_min=1.14, at_max=0.70)
    body = [fruit]
    body.append(bk.block("body.cheek", (0.42, 0.38, 0.20),
                         (0, -0.02, 0.34), color=mango_y))
    body.append(bk.block("body.blush", (0.30, 0.26, 0.16),
                         (0, -0.07, 0.79), color=mango_r))
    body += bk.belly("body.breast", body_at, body_dims, color=mango_y, inset=0.74)
    for side, sign in (("L", 1), ("R", -1)):
        body.append(bk.slab("body.seam.%s" % side, (0.03, 0.30, 0.26),
                            (sign * 0.228, -0.04, 0.50), color=mango_dk))
    body.append(bk.block("body.neck", (0.19, 0.19, 0.14),
                         (0, 0.10, 0.88), color=mango_r))
    # Cosmic signature: a tilted halo orbiting the fruit, plus loose gems.
    body += bk.ring("body.orbit", (0, -0.04, 0.40), radius=0.48,
                    thickness=0.030, tilt=6, color=halo, strength=2.8)
    body += bk.gem("body.spark.L", (0.46, -0.26, 0.98), size=0.095,
                   color=halo, strength=3.4)
    body += bk.gem("body.spark.R", (-0.44, -0.30, 0.30), size=0.08,
                   color=mango_r, strength=3.0)

    # -- head: small, high and forward, so the fruit stays the body --------
    head_dims = (0.30, 0.28, 0.28)
    head_at = (0, 0.22, 1.02)
    head = [bk.block("head.skull", head_dims, head_at, color=mango_r)]
    head.append(bk.face_plate("head.cere", bk.face_of(head_at, head_dims, "front"),
                              (0.26, 0.15), face="front", color=mango_y,
                              depth=0.022, offset=(0, 0.03)))
    head += bk.eyes("head.eye", head_at, head_dims, spacing=0.56, height=0.055,
                    size=0.072, style="white", iris="#1c1218", pupil_scale=0.5)
    # Hooked parrot beak: an upper curve, a hook tip, and a short lower jaw.
    head.append(bk.wedge("head.beak.upper", (0.17, 0.19, 0.22),
                         (0, 0.42, 0.99), rot=(-120, 0, 0), color=beak, taper=0.34))
    head.append(bk.block("head.beak.hook", (0.08, 0.085, 0.12),
                         (0, 0.435, 0.865), rot=(20, 0, 0), color=beak))
    head.append(bk.slab("head.beak.lower", (0.135, 0.13, 0.055),
                        (0, 0.385, 0.905), color=beak_lt))
    # The gag: the mango's stem and leaf ARE the crest.
    head.append(bk.block("head.stem", (0.055, 0.055, 0.15),
                         (0, 0.14, 1.22), rot=(-14, 0, 0), color=stem))
    head.append(bk.slab("head.leaf.L", (0.18, 0.10, 0.035),
                        (0.11, 0.08, 1.30), rot=(0, 26, 18), color=leaf))
    head.append(bk.slab("head.leaf.R", (0.15, 0.09, 0.035),
                        (-0.10, 0.16, 1.27), rot=(0, -30, -14), color=leaf))
    head += bk.crest("head.plume", head_at, head_dims, count=3, height=0.14,
                     width=0.05, color=mango_y, back=-0.05, spacing=0.075)

    # -- wings: three stepped plates splayed out, tipped with a lit feather -
    wing_parts = {}
    for side, sign in (("L", 1), ("R", -1)):
        anchor = (sign * 0.20, 0.0, 0.74)
        parts = [
            bk.block("wing.%s.f0" % side, (0.36, 0.07, 0.40),
                     (sign * 0.40, 0.01, 0.66), rot=(0, -sign * 12, 0),
                     color=mango),
            bk.block("wing.%s.f1" % side, (0.30, 0.06, 0.30),
                     (sign * 0.51, -0.09, 0.48), rot=(0, -sign * 20, 0),
                     color=mango_r),
            bk.block("wing.%s.f2" % side, (0.23, 0.055, 0.20),
                     (sign * 0.58, -0.18, 0.33), rot=(0, -sign * 28, 0),
                     color=mango_y),
            bk.block("wing.%s.tip" % side, (0.18, 0.05, 0.06),
                     (sign * 0.615, -0.24, 0.255), rot=(0, -sign * 28, 0),
                     material=_neon(halo, 2.6)),
        ]
        merged = kit.join(parts, "wing.%s" % side)
        kit.weld(merged)
        kit.set_origin_to(merged, anchor)
        wing_parts[side] = merged

    tail_parts = [
        bk.block("tail.f0", (0.21, 0.30, 0.055), (0, -0.36, 0.46),
                 rot=(-10, 0, 0), color=mango_r),
        bk.block("tail.f1", (0.16, 0.26, 0.05), (0, -0.58, 0.40),
                 rot=(-12, 0, 0), color=mango_y),
        bk.block("tail.f2", (0.10, 0.20, 0.045), (0, -0.76, 0.35),
                 rot=(-14, 0, 0), material=_neon(halo, 2.0)),
    ]

    legs = bk.bird_feet("leg", (0.10, 0.04, 0.26), shin=0.18, thickness=0.05,
                        toe=0.14, color="#c98a2a")

    groups = {
        "body": (body, (0, 0, 0.30)),
        "head": (head, (0, 0.10, 0.88)),
        "wing.L": ([wing_parts["L"]], tuple(wing_parts["L"].location)),
        "wing.R": ([wing_parts["R"]], tuple(wing_parts["R"].location)),
        "tail": (tail_parts, (0, -0.24, 0.48)),
    }
    for key, obj in legs.items():
        groups[key] = ([obj], tuple(obj.location))
    bk.assemble(root, groups)
    return bk.finish(root)


# ===========================================================================
# Crawler -- Event, $1.5M/s.
#
# A many-legged armoured bug. The top half is deliberately dead matte gunmetal
# so that the entire underside -- a continuous acid-green lamp running the
# length of the body -- is the only light source. The thorax arches over the
# middle pair of legs, which is what keeps a ten-legged animal from reading as
# a flat plank. Ten legs, five per flank, across the four leg slots.
# ===========================================================================

def build_crawler():
    kit.reset_scene()
    root = kit.empty("root")

    chitin = "#252b3a"
    plate = "#4d5c7b"
    plate_lt = "#8ea0c4"
    glow = "#7dff8c"
    glow_dim = "#3fd070"

    # -- four armour segments on an arch, each with a lit rim under it ------
    body = []
    segs = (
        (0.24, 0.40, 0.22, 0.21, 0.46),
        (0.04, 0.46, 0.22, 0.25, 0.52),
        (-0.16, 0.44, 0.22, 0.24, 0.50),
        (-0.36, 0.36, 0.20, 0.20, 0.44),
    )
    for i, (dy, w, d, h, z) in enumerate(segs):
        at = (0, dy, z)
        body.append(bk.block("body.seg%d" % i, (w, d, h), at, color=chitin))
        body.append(bk.slab("body.plate%d" % i, (w * 0.82, d * 0.9, 0.05),
                            (0, dy, z + h * 0.5), color=plate))
        body.append(bk.slab("body.ridge%d" % i, (0.075, d * 0.8, 0.03),
                            (0, dy, z + 0.03 + h * 0.5), color=plate_lt))
        # The lamp: a strip on the belly, plus a slit up each flank.
        body.append(bk.glow_block("body.lamp%d" % i, (w * 0.68, d * 0.92, 0.06),
                                  (0, dy, z - h * 0.5 - 0.015), color=glow,
                                  strength=3.0))
        for side, sign in (("L", 1), ("R", -1)):
            body.append(bk.glow_block(
                "body.slit%d.%s" % (i, side), (0.028, d * 0.62, 0.055),
                (sign * w * 0.5, dy, z - h * 0.22), color=glow_dim,
                strength=2.4))

    # One unbroken keel of light running the whole underside. Four separate
    # chips read as damage; a continuous bar reads as a creature that glows.
    body.append(bk.glow_block("body.keel", (0.24, 0.98, 0.05),
                              (0, -0.06, 0.30), color=glow, strength=3.2))

    # -- head: armoured wedge, four lit eyes, a pair of mandibles -----------
    head_dims = (0.34, 0.24, 0.22)
    head_at = (0, 0.48, 0.44)
    head = [bk.block("head.helm", head_dims, head_at, color=plate)]
    head.append(bk.slab("head.brow", (0.32, 0.11, 0.055),
                        (0, 0.46, 0.565), color=plate_lt))
    head.append(bk.wedge("head.snout", (0.24, 0.22, 0.14),
                         (0, 0.64, 0.40), rot=(-90, 0, 0), color=chitin,
                         taper=0.35))
    head += bk.eyes("head.eye", head_at, head_dims, spacing=0.46, height=0.03,
                    size=0.058, style="glow", iris=glow)
    head += bk.eyes("head.eye.side", head_at, head_dims, spacing=0.82,
                    height=-0.03, size=0.034, style="glow", iris=glow_dim)
    for side, sign in (("L", 1), ("R", -1)):
        head.append(bk.wedge("head.mandible.%s" % side, (0.055, 0.055, 0.19),
                             (sign * 0.10, 0.71, 0.365), rot=(-100, 0, sign * 22),
                             color=plate_lt, taper=0.72))
    head.append(bk.glow_block("head.core", (0.11, 0.03, 0.045),
                              (0, 0.612, 0.50), color=glow, strength=3.4))

    # -- antennae ride the ear slots so they sweep when the pet moves ------
    antennae = []
    for side, sign in (("L", 1), ("R", -1)):
        anchor = (sign * 0.11, 0.54, 0.55)
        parts = [
            _strut("ear.%s.base" % side, anchor,
                   (sign * 0.26, 0.62, 0.76), 0.038, color=chitin),
            _strut("ear.%s.tip" % side, (sign * 0.26, 0.62, 0.76),
                   (sign * 0.35, 0.47, 0.90), 0.03, color=plate_lt, taper=0.5),
            bk.block("ear.%s.bead" % side, (0.052, 0.052, 0.052),
                     (sign * 0.36, 0.45, 0.92), material=_neon(glow, 3.0)),
        ]
        merged = kit.join(parts, "ear.%s" % side)
        kit.weld(merged)
        kit.set_origin_to(merged, anchor)
        antennae.append(merged)

    # -- ten legs: five per flank, tall enough to lift the lamp off the floor
    def bug_leg(name, sign, hy, out, hz):
        hip = (sign * 0.21, hy, hz)
        knee = (sign * (0.21 + out), hy + 0.03, hz + 0.12)
        foot = (sign * (0.23 + out), hy + 0.07, 0.02)
        parts = [
            _strut(name + ".femur", hip, knee, 0.075, color=plate_lt),
            _strut(name + ".tibia", knee, foot, 0.062, color=plate, taper=0.4),
            bk.block(name + ".joint", (0.085, 0.085, 0.085),
                     (sign * (0.21 + out), hy + 0.03, hz + 0.12), color=plate_lt),
        ]
        merged = kit.join(parts, name)
        kit.weld(merged)
        kit.set_origin_to(merged, hip)
        return merged

    front_l, front_r, back_l, back_r = [], [], [], []
    for i, (hy, out, hz) in enumerate((
        (0.30, 0.12, 0.38), (0.15, 0.15, 0.42), (0.0, 0.16, 0.42),
        (-0.17, 0.15, 0.40), (-0.34, 0.12, 0.36),
    )):
        left = bug_leg("leg.L%d" % i, 1, hy, out, hz)
        right = _mirror(left, "leg.R%d" % i)
        (front_l if i < 3 else back_l).append(left)
        (front_r if i < 3 else back_r).append(right)

    # -- abdomen tip rides the tail slot so the back end sways --------------
    tail_parts = [
        bk.block("tail.seg", (0.27, 0.19, 0.16), (0, -0.53, 0.40), color=chitin),
        bk.slab("tail.plate", (0.23, 0.17, 0.05), (0, -0.53, 0.485), color=plate),
        bk.glow_block("tail.lamp", (0.17, 0.15, 0.045), (0, -0.53, 0.322),
                      color=glow, strength=3.0),
        bk.wedge("tail.spike", (0.09, 0.09, 0.20), (0, -0.68, 0.47),
                 rot=(112, 0, 0), color=plate_lt, taper=0.8),
    ]
    tail_parts += bk.gem("tail.ember", (0, -0.775, 0.545), size=0.065,
                         color=glow, strength=3.6)

    bk.assemble(root, {
        "body": (body, (0, 0, 0.32)),
        "head": (head, (0, 0.36, 0.38)),
        "ear.L": ([antennae[0]], tuple(antennae[0].location)),
        "ear.R": ([antennae[1]], tuple(antennae[1].location)),
        "tail": (tail_parts, (0, -0.45, 0.42)),
        "leg.FL": (front_l, (0.20, 0.15, 0.43)),
        "leg.FR": (front_r, (-0.20, 0.15, 0.43)),
        "leg.BL": (back_l, (0.20, -0.25, 0.40)),
        "leg.BR": (back_r, (-0.20, -0.25, 0.40)),
    })
    return bk.finish(root)


# ===========================================================================
# Cocoa Croc -- Secret, $20M/s.
#
# A crocodile cast in chocolate. Everything above the waterline is glossy dark
# couverture moulded into bar squares, the belly is cream filling, and someone
# has taken bites out of it: each bite is a cream crater ringed by scalloped
# tooth marks with molten caramel glowing inside. Gold foil still clings to
# the tail base. Built short-bodied, standing tall on its legs with a lifted
# curled tail, so the height normalisation does not blow it up next to the
# smaller pets.
# ===========================================================================

def build_cocoa_croc():
    kit.reset_scene()
    root = kit.empty("root")

    choc_dk = "#361d10"
    choc = "#5d3620"
    choc_lt = "#8a5230"
    cream = "#f4e2bf"
    cream_dk = "#dcc196"
    gold = "#ecc95f"
    gold_dk = "#a8862f"
    caramel = "#ffa22e"

    glossy = _gloss(choc, 0.22)
    glossy_dk = _gloss(choc_dk, 0.2)

    def bite(name, center, dims, face, count=5, radius=0.11, size=0.055):
        """A cream crater ringed by scalloped tooth marks, molten in the middle."""
        plane = bk.face_of(center, dims, face)
        parts = [bk.face_plate(name + ".crater", plane,
                               (radius * 1.8, radius * 1.6), face=face,
                               color=cream, depth=0.02)]
        for i in range(count):
            a = math.pi * (0.12 + 0.76 * (i / float(count - 1)))
            parts.append(bk.face_plate(
                "%s.scallop%d" % (name, i), plane, (size, size), face=face,
                color=cream_dk, depth=0.018,
                offset=(math.cos(a) * radius, math.sin(a) * radius - 0.01),
                proud=bk.PROUD * 2.4,
            ))
        parts.append(bk.face_plate(
            name + ".molten", plane, (radius * 0.75, radius * 0.5), face=face,
            material=_neon(caramel, 2.6), depth=0.02, proud=bk.PROUD * 3.6,
        ))
        return parts

    # -- body: short, deep and lifted, not a plank --------------------------
    body_dims = (0.40, 0.44, 0.34)
    body_at = (0, -0.02, 0.44)
    body = [bk.block("body.core", body_dims, body_at, material=glossy)]
    body.append(bk.block("body.belly", (0.34, 0.40, 0.11),
                         (0, -0.02, 0.295), color=cream))
    for side, sign in (("L", 1), ("R", -1)):
        body.append(bk.slab("body.belly.edge.%s" % side, (0.03, 0.42, 0.10),
                            (sign * 0.202, -0.02, 0.345), color=cream))
    # Moulded squares -- this is a bar of chocolate that happens to be a croc.
    for row in range(3):
        for col in (-1, 1):
            body.append(bk.slab(
                "body.square.%d.%d" % (row, col), (0.155, 0.115, 0.05),
                (col * 0.09, 0.12 - row * 0.135, 0.635), material=glossy_dk))
    # The signature bite: taken out of the top of the back, where the 3/4 hero
    # angle looks straight into it. A second, smaller one on the flank.
    body += bite("body.bite.back", body_at, body_dims, "top",
                 count=5, radius=0.11, size=0.052)
    body += bite("body.bite.flank", (0, -0.14, 0.44), (0.40, 0.22, 0.34), "left",
                 count=5, radius=0.075, size=0.042)
    body.append(bk.block("body.neck", (0.27, 0.17, 0.22),
                         (0, 0.24, 0.56), material=glossy))

    # -- head: raised on the neck, long snout carried well forward ---------
    skull_dims = (0.30, 0.24, 0.20)
    skull_at = (0, 0.42, 0.62)
    head = [bk.block("head.skull", skull_dims, skull_at, material=glossy)]
    head.append(bk.block("head.snout", (0.24, 0.38, 0.115),
                         (0, 0.71, 0.555), material=glossy))
    head.append(bk.block("head.jaw", (0.22, 0.36, 0.06),
                         (0, 0.70, 0.468), material=glossy_dk))
    head.append(bk.slab("head.gumline", (0.24, 0.34, 0.022),
                        (0, 0.70, 0.502), color=cream_dk))
    head.append(bk.slab("head.nostrils", (0.12, 0.06, 0.03),
                        (0, 0.87, 0.615), material=glossy_dk))
    # Cream teeth showing along the upper jaw line.
    for i in range(5):
        for side, sign in (("L", 1), ("R", -1)):
            head.append(bk.wedge(
                "head.tooth.%s%d" % (side, i), (0.034, 0.034, 0.065),
                (sign * 0.112, 0.85 - i * 0.08, 0.482), rot=(180, 0, 0),
                color=cream, taper=0.8))
    # Eyes on raised turrets, lit like warm caramel -- the "secret" tell.
    for side, sign in (("L", 1), ("R", -1)):
        head.append(bk.block("head.turret.%s" % side, (0.10, 0.11, 0.08),
                             (sign * 0.09, 0.46, 0.755), material=glossy_dk))
    head += bk.eyes("head.eye", (0, 0.46, 0.765), (0.32, 0.11, 0.08),
                    spacing=0.56, height=0.0, size=0.058, style="glow",
                    iris=caramel)
    head.append(bk.slab("head.browridge", (0.32, 0.11, 0.04),
                        (0, 0.42, 0.735), material=glossy_dk))
    head += bite("head.bite", skull_at, skull_dims, "left",
                 count=4, radius=0.055, size=0.032)

    # -- tail: lifted in a curl, foil-wrapped at the base, scuted on top ---
    tail_parts = [bk.tail("tail.body", (0, -0.20, 0.44), length=0.46,
                          thickness=0.20, color=choc, style="taper",
                          segments=4, curl=0.62)]
    tail_parts.append(bk.block("tail.foil", (0.28, 0.15, 0.28),
                               (0, -0.24, 0.45), color=gold))
    tail_parts.append(bk.slab("tail.foil.crimp", (0.30, 0.04, 0.30),
                              (0, -0.32, 0.455), color=gold_dk))
    # Torn foil: three ragged tabs peeling off the wrapper's forward edge.
    for i, (fx, fz, fr) in enumerate(((0.13, 0.14, -34), (-0.10, 0.05, 26),
                                      (0.03, -0.13, 12))):
        tail_parts.append(bk.slab("tail.foil.tear%d" % i, (0.10, 0.03, 0.09),
                                  (fx, -0.15, 0.45 + fz), rot=(0, fr, 0),
                                  color=gold))
    for i, (ty, tz, th) in enumerate((
        (-0.40, 0.55, 0.10), (-0.52, 0.62, 0.08), (-0.63, 0.73, 0.065),
    )):
        tail_parts.append(bk.wedge("tail.scute%d" % i, (0.055, 0.07, th),
                                   (0, ty, tz), rot=(-14, 0, 0),
                                   color=choc_lt, taper=0.65))

    legs = bk.legs_quad("leg", front=(0.16, 0.13, 0.34), back=(0.17, -0.16, 0.34),
                        length=0.29, thickness=0.115, color=choc_lt,
                        foot_color=cream_dk)

    groups = {
        "body": (body, (0, 0, 0.28)),
        "head": (head, (0, 0.30, 0.56)),
        "tail": (tail_parts, (0, -0.22, 0.44)),
    }
    for key, obj in legs.items():
        groups[key] = ([obj], tuple(obj.location))
    bk.assemble(root, groups)
    return bk.finish(root)


# ===========================================================================
# Crocodon -- Event, $30M/s.
#
# The roster's brute: a hulking bipedal crocodile. Built as a wedge -- huge
# shoulders and jaw at the front, tapering into a counterweight tail -- so it
# leans into the camera even standing still. The spine spikes rise to a peak
# over the shoulders, and ember light bleeds out from between the plates.
# ===========================================================================

def build_crocodon():
    kit.reset_scene()
    root = kit.empty("root")

    scale = "#416b4c"
    scale_dk = "#26402f"
    scale_lt = "#6fa377"
    belly = "#d9cba0"
    bone = "#efe3c2"
    bone_dk = "#c2b189"
    ember = "#ff7a2e"

    # -- torso: shoulders far wider than hips, hunched forward -------------
    torso_dims = (0.52, 0.44, 0.48)
    torso_at = (0, 0.02, 0.70)
    body = [bk.block("body.torso", torso_dims, torso_at, color=scale)]
    body.append(bk.block("body.shoulders", (0.70, 0.38, 0.24),
                         (0, 0.04, 0.94), color=scale))
    body.append(bk.block("body.hips", (0.46, 0.32, 0.36),
                         (0, -0.26, 0.54), color=scale_dk))
    body += bk.belly("body.plate", torso_at, torso_dims, color=belly, inset=0.78)
    for i in range(4):
        body.append(bk.slab("body.abplate%d" % i, (0.27, 0.03, 0.055),
                            (0, 0.245, 0.57 + i * 0.085), color=bone_dk))
    for side, sign in (("L", 1), ("R", -1)):
        body.append(bk.slab("body.trap.%s" % side, (0.05, 0.32, 0.17),
                            (sign * 0.342, 0.04, 0.90), color=scale_lt))
        # Pale scute plates on the flanks: without them the torso is one
        # unbroken green mass at any distance.
        for i, (py, pz) in enumerate(((0.14, 0.74), (-0.02, 0.66),
                                      (0.10, 0.56))):
            body.append(bk.slab("body.scute.%s%d" % (side, i),
                                (0.03, 0.17, 0.11),
                                (sign * 0.262, py, pz), color=scale_lt))
    # Spine spikes: rise over the shoulders, then march down the back.
    spikes = ((0.14, 0.19, 1.07), (0.02, 0.28, 1.11), (-0.12, 0.32, 1.06),
              (-0.27, 0.24, 0.92), (-0.40, 0.17, 0.76))
    for i, (sy, sh, sz) in enumerate(spikes):
        body.append(bk.wedge("body.spike%d" % i, (0.095, 0.12, sh),
                             (0, sy, sz), rot=(-16, 0, 0), color=bone, taper=0.72))
        body.append(bk.glow_block("body.crack%d" % i, (0.105, 0.04, 0.035),
                                  (0, sy, sz - sh * 0.5), color=ember,
                                  strength=2.6))
    for side, sign in (("L", 1), ("R", -1)):
        body.append(bk.wedge("body.shoulderspike.%s" % side, (0.075, 0.085, 0.18),
                             (sign * 0.32, 0.06, 1.07), rot=(0, -sign * 30, 0),
                             color=bone_dk, taper=0.7))

    # -- head: a slab of jaw carried out in front of the chest -------------
    skull_dims = (0.36, 0.30, 0.28)
    skull_at = (0, 0.38, 1.06)
    head = [bk.block("head.skull", skull_dims, skull_at, color=scale)]
    head.append(bk.block("head.snout", (0.31, 0.44, 0.19),
                         (0, 0.73, 1.00), color=scale))
    head.append(bk.block("head.jaw", (0.29, 0.42, 0.11),
                         (0, 0.72, 0.865), color=belly))
    head.append(bk.slab("head.lip", (0.32, 0.43, 0.035),
                        (0, 0.73, 0.915), color=scale_dk))
    head.append(bk.slab("head.nostrils", (0.14, 0.07, 0.035),
                        (0, 0.93, 1.11), color=scale_dk))
    head.append(bk.slab("head.brow", (0.38, 0.13, 0.065),
                        (0, 0.38, 1.215), color=bone_dk))
    head += bk.eyes("head.eye", (0, 0.42, 1.15), (0.36, 0.13, 0.10),
                    spacing=0.56, height=0.0, size=0.062, style="glow",
                    iris=ember)
    # Interlocking fangs: upper hanging down, lower standing up.
    head += _jaw_fangs("head.fang.up", (0, 0.90, 0.915), count=5, spread=0.135,
                       size=0.048, length=0.105, color=bone, down=True,
                       spacing=0.095)
    head += _jaw_fangs("head.fang.low", (0, 0.86, 0.915), count=4, spread=0.125,
                       size=0.042, length=0.085, color=bone, down=False,
                       spacing=0.095)
    for side, sign in (("L", 1), ("R", -1)):
        head.append(bk.wedge("head.horn.%s" % side, (0.065, 0.075, 0.19),
                             (sign * 0.15, 0.27, 1.27), rot=(24, -sign * 22, 0),
                             color=bone, taper=0.75))
    head.append(bk.glow_block("head.throat", (0.15, 0.04, 0.05),
                              (0, 0.53, 0.875), color=ember, strength=2.4))

    # -- arms: heavy, with three bone claws each ---------------------------
    arm_l, arm_r = bk.arms("arm", (0.33, 0.08, 0.88), length=0.38,
                           thickness=0.15, color=scale, hand_color=scale_dk,
                           angle=16)
    claw_groups = {"L": [], "R": []}
    hand = (0.33 + math.sin(16 * bk.D2R) * 0.38, 0.08,
            0.88 - math.cos(16 * bk.D2R) * 0.38)
    for side, sign in (("L", 1), ("R", -1)):
        for i, dx in enumerate((-0.055, 0.0, 0.055)):
            claw_groups[side].append(bk.wedge(
                "arm.%s.claw%d" % (side, i), (0.038, 0.038, 0.12),
                (sign * (hand[0] + dx * 0.8), hand[1] + 0.11, hand[2] - 0.04),
                rot=(-116, 0, sign * dx * 180), color=bone, taper=0.8))

    # -- legs: thick digitigrade columns with clawed feet ------------------
    def brute_leg(name, sign):
        hip = (sign * 0.21, -0.08, 0.52)
        parts = [
            bk.block(name + ".thigh", (0.23, 0.30, 0.34),
                     (sign * 0.21, -0.11, 0.39), color=scale),
            bk.block(name + ".shin", (0.16, 0.18, 0.26),
                     (sign * 0.21, 0.01, 0.17), color=scale_dk),
            bk.block(name + ".foot", (0.23, 0.32, 0.09),
                     (sign * 0.21, 0.13, 0.05), color=scale),
            bk.slab(name + ".heel", (0.17, 0.10, 0.07),
                    (sign * 0.21, -0.05, 0.045), color=scale_dk),
        ]
        for i, dx in enumerate((-0.065, 0.0, 0.065)):
            parts.append(bk.wedge(
                name + ".claw%d" % i, (0.048, 0.048, 0.095),
                (sign * (0.21 + dx), 0.30, 0.045), rot=(-96, 0, 0),
                color=bone, taper=0.8))
        merged = kit.join(parts, name)
        kit.weld(merged)
        kit.set_origin_to(merged, hip)
        return merged

    leg_l = brute_leg("leg.FL", 1)
    leg_r = _mirror(leg_l, "leg.FR")

    tail_parts = [bk.tail("tail.body", (0, -0.40, 0.54), length=0.56,
                          thickness=0.25, color=scale, style="taper",
                          segments=4, curl=0.14)]
    for i, (ty, tz, th) in enumerate((
        (-0.54, 0.69, 0.15), (-0.67, 0.70, 0.125), (-0.80, 0.72, 0.10),
        (-0.92, 0.75, 0.08),
    )):
        tail_parts.append(bk.wedge("tail.scute%d" % i, (0.07, 0.085, th),
                                   (0, ty, tz), rot=(-10, 0, 0),
                                   color=bone_dk, taper=0.7))

    bk.assemble(root, {
        "body": (body, (0, 0, 0.44)),
        "head": (head, (0, 0.22, 0.95)),
        "arm.L": ([arm_l] + claw_groups["L"], tuple(arm_l.location)),
        "arm.R": ([arm_r] + claw_groups["R"], tuple(arm_r.location)),
        "tail": (tail_parts, (0, -0.40, 0.54)),
        "leg.FL": ([leg_l], tuple(leg_l.location)),
        "leg.FR": ([leg_r], tuple(leg_r.location)),
    })
    return bk.finish(root)


PETS = {
    "mallet-sentry": build_mallet_sentry,
    "peelfin": build_peelfin,
    "scorpio": build_scorpio,
    "bellug": build_bellug,
    "froggo": build_froggo,
    "mangowing": build_mangowing,
    "crawler": build_crawler,
    "cocoa-croc": build_cocoa_croc,
    "crocodon": build_crocodon,
}
