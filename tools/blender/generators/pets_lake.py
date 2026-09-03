"""
Glasswater Lake -- the eight water pets.

Palette discipline for this biome: teal and aqua water, pale reed sand, and
white/soft-blue highlights. Every creature here is either a swimmer or a
wader, so the shared read is "low, wide and wet" -- flat heads, paddle feet,
fins instead of paws -- against the forest roster's upright furry silhouettes.

Same rules as pets_forest:
  * Build facing +Y, feet near z = 0, `finish()` normalises the height.
  * Only runtime part names in `assemble`: body, head, ear.L/.R, wing.L/.R,
    arm.L/.R, leg.FL/.FR/.BL/.BR, tail, fin.L/.R, fin.tail.
  * Pivots are joints, not centres.
  * Silhouette first: at icon size the lake pets have to be told apart by
    outline alone, which is why the frog is all haunch, the swan is all neck,
    the catfish is all barbel and the anglerkin is all jaw.

Two things this biome forced, both worth knowing before editing:

  1. `finish()` normalises HEIGHT, so anything built flat on the floor is
     scaled up until it is enormously wide. Water animals want to be built
     low, so every one of them here is deliberately given vertical extent --
     a tall tail fin, a domed shell, raised haunches, a lifted head -- until
     width and length are near its height. A pancake turtle scaled to one
     metre tall is two metres across and reads as a different toy line.
  2. Emissive parts clip to white fast under the preview's Standard view
     transform, and dark parts sink into the near-black background. So glow
     strengths here sit around 1.0-1.3 rather than the library's 2.6-3.2
     defaults, and even the deep-water pets are painted in lit values.
"""

import math

from mathutils import Vector

import blockkit as bk
import kit


# ---------------------------------------------------------------------------
# shared helpers
# ---------------------------------------------------------------------------


def _mirror(left, name):
    """Duplicate a finished left-side part to its right-side twin."""
    right = kit.duplicate(left, name, mirror=True)
    right.location = Vector((-left.location.x, left.location.y, left.location.z))
    return right


def _bake(obj):
    """
    Bake an object's rotation into its mesh.

    `kit.set_origin_to` shifts LOCAL vertex coordinates by a WORLD-space
    offset, which is only correct while the object is unrotated. Since
    `kit.group` runs set_origin_to on the joined mesh -- and a join inherits
    the FIRST part's transform -- a rotated first part silently teleports the
    whole group somewhere else. That is exactly what tore the leviathan and the
    swan apart into floating debris. Every rotated part produced here is baked
    so its rotation is identity and that arithmetic holds.
    """
    kit.apply_transforms(obj, location=False, rotation=True, scale=True)
    return obj


def _weld_group(name, parts, pivot):
    """
    Join `parts` into one welded mesh with its origin at `pivot`.

    Identical to `kit.group` except that the FIRST part is baked first, which
    it has to be: `kit.set_origin_to` adds a world-space offset to LOCAL vertex
    coordinates, so it is only correct when that object has identity rotation
    AND identity scale -- and every `bk.block` carries its dimensions in object
    scale. Un-baked, a group silently shifts by (scale - 1) * offset. On the
    turtle that sank the shell 0.16 into its own legs and cost a fifth of the
    pet's height, which then fed straight into the height normalisation.
    """
    parts = [q for q in parts if q is not None]
    _bake(parts[0])
    merged = kit.join(parts, name)
    kit.weld(merged)
    kit.set_origin_to(merged, pivot)
    return merged


def _assemble(root, groups):
    """bk.assemble, with the first part of every group baked first."""
    for _name, spec in groups.items():
        parts = [q for q in spec[0] if q is not None]
        if parts:
            _bake(parts[0])
    return bk.assemble(root, groups)


def _chain(name, points, widths, color, crest_color=None, crest_h=0.16,
           seam_color=None, seam_every=0, crest_every=1, depth=0.96,
           crest_side=1.0):
    """
    Lay oriented blocks along a spine given as (x, y, z) points.

    Each segment is rotated to point along its own direction in the Y-Z plane.
    That single detail is what makes an arc read as a neck or a serpent's back
    instead of a staircase of cubes, and it is reused by the swan, the angler's
    lure and the leviathan.

    `widths` is per-point; a segment uses the width of its start point.
    Optional crest wedges ride one side of each segment; optional glowing seams
    sit at the joints.

    `crest_side` matters: the perpendicular flips with the direction of travel,
    so a spine written head-to-tail puts its crest on the THROAT unless you
    pass -1. That is not a detail you can see in the numbers -- it cost a whole
    render pass of wondering where the leviathan's dorsal sail had gone.
    """
    parts = []
    for i in range(len(points) - 1):
        a, b = points[i], points[i + 1]
        dy, dz = b[1] - a[1], b[2] - a[2]
        length = math.hypot(dy, dz) or 1e-5
        uy, uz = dy / length, dz / length
        angle = math.degrees(math.atan2(-dy, dz))
        w = widths[i]
        mid = ((a[0] + b[0]) * 0.5, (a[1] + b[1]) * 0.5, (a[2] + b[2]) * 0.5)
        parts.append(_bake(bk.block(
            "%s.%d" % (name, i), (w, w * depth, length * 1.18), mid,
            rot=(angle, 0, 0), color=color)))
        if seam_color and (seam_every and i % seam_every == 0):
            parts.append(_bake(bk.glow_block(
                "%s.seam%d" % (name, i), (w * 1.04, w * depth * 1.02, 0.05),
                a, rot=(angle, 0, 0), color=seam_color, strength=1.3)))
        if crest_color and (crest_every and i % crest_every == 0):
            # The blade has to stand PERPENDICULAR to the spine. A wedge tapers
            # along its own +Z, so giving it the segment's own rotation lays the
            # fin flat along the back instead of standing it up -- quarter turn.
            px, py = -uz * crest_side, uy * crest_side
            off = w * 0.5 + crest_h * 0.36
            parts.append(_bake(bk.wedge(
                "%s.crest%d" % (name, i), (w * 0.26, length * 0.62, crest_h),
                (mid[0], mid[1] + px * off, mid[2] + py * off),
                rot=(angle + 90.0 * crest_side, 0, 0), color=crest_color,
                taper=0.66)))
    return parts


def _smile(name, head_center, head_dims, width=0.24, thickness=0.032,
           drop=-0.05, lift=0.045, color="#2b3f3a", face="front"):
    """
    An upturned mouth.

    `bk.mouth(style="grin")` drops its outer plates BELOW the centre, which is
    a frown -- fine for a grumpy pet, wrong for every friendly one here. This
    steps the corners up instead, in five plates so the curve is visible at
    icon size.
    """
    plane = bk.face_of(head_center, head_dims, face)
    parts = [bk.face_plate("%s.mid" % name, plane, (width * 0.5, thickness),
                           face=face, color=color, depth=0.02, offset=(0, drop))]
    for side, sign in (("L", 1), ("R", -1)):
        parts.append(bk.face_plate(
            "%s.%s" % (name, side), plane, (width * 0.26, thickness), face=face,
            color=color, depth=0.02,
            offset=(sign * width * 0.36, drop + lift * 0.5), proud=bk.PROUD * 2,
        ))
        parts.append(bk.face_plate(
            "%s.tip.%s" % (name, side), plane, (thickness, thickness * 1.7),
            face=face, color=color, depth=0.02,
            offset=(sign * width * 0.5, drop + lift), proud=bk.PROUD * 2,
        ))
    return parts


def _glow_eyes(name, head_center, head_dims, spacing=0.56, height=0.08,
               size=0.09, color="#9df4ff", strength=1.1, face="front"):
    """
    Softly lit eyes.

    `bk.eyes(style="glow")` hardcodes emission strength 3.2, which clips to a
    flat white square under this preview's Standard view transform -- the exact
    failure that made the deep-lake pets look like they had paper eyes. Same
    plates, a third of the emission, so the colour survives.
    """
    plane = bk.face_of(head_center, head_dims, face)
    span = head_dims[0] if face in ("front", "back") else head_dims[1]
    material = kit.mat("lake.glow." + color.strip("#") + str(strength),
                       kit.hexcol(color), rough=0.25, emission=kit.hexcol(color),
                       emission_strength=strength)
    parts = []
    for side, sign in (("L", 1), ("R", -1)):
        offset = (sign * span * 0.5 * spacing, height)
        parts.append(bk.face_plate("%s.socket.%s" % (name, side), plane,
                                   (size * 1.5, size * 1.5), face=face,
                                   color="#0e1c24", depth=0.02, offset=offset))
        parts.append(bk.face_plate("%s.%s" % (name, side), plane,
                                   (size, size * 1.1), face=face,
                                   material=material, depth=0.022, offset=offset,
                                   proud=bk.PROUD * 3))
    return parts


def _webbed_feet(prefix, at, shin=0.12, thickness=0.05, web=(0.15, 0.19),
                 color="#f79b3c"):
    """
    Duck/swan paddle: a stick shin under a flat webbed slab.

    `bird_feet` splays three separate toes, which reads as a songbird. A
    waterfowl needs one continuous paddle -- it is the difference between
    "chicken" and "duck" at icon size.
    """
    parts = [
        bk.block("%s.FL.shin" % prefix, (thickness, thickness, shin),
                 (at[0], at[1], at[2] - shin * 0.5), color=color),
        bk.slab("%s.FL.web" % prefix, (web[0], web[1], thickness * 0.5),
                (at[0], at[1] + web[1] * 0.24, at[2] - shin - thickness * 0.18),
                color=color),
    ]
    left = _weld_group("%s.FL" % prefix, parts, at)
    return {"%s.FL" % prefix: left, "%s.FR" % prefix: _mirror(left, "%s.FR" % prefix)}


# ---------------------------------------------------------------------------
# Frog -- Common, $3/s.
# A frog is a mouth with haunches. Wide flat skull, eyes on turrets standing
# clear above the line of the head, and folded back legs whose knees rise above
# the back. That three-step outline -- foot, knee, eye -- is the silhouette.
# ---------------------------------------------------------------------------

def build_frog():
    kit.reset_scene()
    root = kit.empty("root")

    skin = "#57b884"
    dark = "#2f8a63"
    pale = "#f1e6c4"
    lip = "#26463b"

    body_dims = (0.4, 0.4, 0.3)
    body_at = (0, -0.16, 0.4)
    body = [bk.block("body.core", body_dims, body_at, color=skin)]
    body += bk.spots("body.spot", body_at, body_dims, count=6, size=0.075,
                     color=dark, seed=7, faces=("top", "left", "right"))
    body.append(bk.slab("body.belly", (0.34, 0.34, 0.06),
                        (0, body_at[1], body_at[2] - 0.14), color=pale))
    # A darker saddle along the back separates skull from shoulders in profile.
    body.append(bk.face_plate("body.saddle", bk.face_of(body_at, body_dims, "top"),
                              (0.3, 0.32), face="top", color=dark, depth=0.022))

    head_dims = (0.4, 0.3, 0.2)
    head_at = (0, 0.2, 0.48)
    head = [bk.block("head.skull", head_dims, head_at, color=skin)]
    head += _smile("head.mouth", head_at, head_dims, width=0.29, thickness=0.034,
                   drop=-0.04, lift=0.05, color=lip)
    head += bk.nostrils("head.nose", head_at, head_dims, spacing=0.28,
                        height=0.055, size=0.028, color=lip)
    head.append(bk.slab("head.jaw", (0.38, 0.26, 0.045),
                        (0, head_at[1], head_at[2] - 0.11), color=pale))
    head.append(bk.block("head.neck", (0.24, 0.14, 0.16), (0, 0.04, 0.42),
                         color=skin))

    # Eye turrets: two stalked domes, lifted a clear gap above the skull so the
    # eyes are a separate lump in the outline rather than paint on the face.
    top = head_at[2] + head_dims[2] * 0.5
    for side, sign in (("L", 1), ("R", -1)):
        stalk_at = (sign * 0.12, head_at[1] - 0.01, top + 0.03)
        head.append(bk.block("head.eyestalk.%s" % side, (0.11, 0.13, 0.07),
                             stalk_at, color=dark))
        turret_dims = (0.17, 0.17, 0.16)
        turret_at = (sign * 0.12, head_at[1] + 0.01, top + 0.14)
        head.append(bk.block("head.eyebump.%s" % side, turret_dims, turret_at,
                             color=skin))
        face = bk.face_of(turret_at, turret_dims, "front")
        head.append(bk.face_plate("head.eye.%s" % side, face, (0.125, 0.12),
                                  face="front", color="#f9f5e8", depth=0.02))
        head.append(bk.face_plate("head.pupil.%s" % side, face, (0.06, 0.075),
                                  face="front", color="#171620", depth=0.02,
                                  proud=bk.PROUD * 3))
        head.append(bk.face_plate("head.glint.%s" % side, face, (0.026, 0.026),
                                  face="front", color="#ffffff", depth=0.016,
                                  offset=(sign * 0.035, 0.032), proud=bk.PROUD * 5))
        head.append(bk.face_plate("head.lid.%s" % side,
                                  bk.face_of(turret_at, turret_dims, "top"),
                                  (0.15, 0.15), face="top", color=dark, depth=0.02))

    # Front legs: straight props holding the chest up off the ground.
    front = bk.legs_pair("leg", (0.14, 0.02, 0.34), length=0.28, thickness=0.06,
                         color=skin, foot_color=pale, foot_length=0.13)

    # Back legs: the knee is a deliberate lump above the backline.
    back = {}
    for side, sign in (("L", 1), ("R", -1)):
        hip = (sign * 0.2, -0.2, 0.4)
        parts = [
            bk.block("leg.B%s.haunch" % side, (0.16, 0.3, 0.26),
                     (sign * 0.23, -0.24, 0.42), color=dark),
            bk.block("leg.B%s.knee" % side, (0.14, 0.15, 0.15),
                     (sign * 0.24, -0.13, 0.5), color=skin),
            _bake(bk.block("leg.B%s.shin" % side, (0.1, 0.12, 0.34),
                           (sign * 0.24, -0.1, 0.25), rot=(20, 0, 0),
                           color=dark)),
            bk.slab("leg.B%s.foot" % side, (0.14, 0.24, 0.055),
                    (sign * 0.24, 0.02, 0.03), color=pale),
        ]
        back["leg.B%s" % side] = _weld_group("leg.B%s" % side, parts, hip)

    groups = {
        "body": (body, (0, -0.1, 0.26)),
        "head": (head, (0, 0.04, 0.4)),
    }
    for key, obj in list(front.items()) + list(back.items()):
        groups[key] = ([obj], tuple(obj.location))
    _assemble(root, groups)
    return bk.finish(root)


# ---------------------------------------------------------------------------
# Duckling -- Common, $4/s.
# All head and fluff. Oversized round skull, stub wings that could not possibly
# fly, flat spatula bill, orange paddles.
# ---------------------------------------------------------------------------

def build_duckling():
    kit.reset_scene()
    root = kit.empty("root")

    down = "#f9de8b"
    downdark = "#e8c561"
    cream = "#fff3c4"
    bill = "#f79b3c"

    # Barrel body: a core block with a narrower cap and base so the profile
    # steps in at top and bottom instead of being a plain crate.
    body_dims = (0.34, 0.38, 0.28)
    body_at = (0, -0.06, 0.32)
    body = [bk.block("body.core", body_dims, body_at, color=down)]
    body.append(bk.block("body.crown", (0.26, 0.3, 0.09), (0, -0.06, 0.5),
                         color=down))
    body.append(bk.block("body.base", (0.26, 0.3, 0.08), (0, -0.05, 0.17),
                         color=downdark))
    body.append(bk.slab("body.tummy", (0.24, 0.3, 0.06), (0, -0.02, 0.21),
                        color=cream))
    # Down tufts: little blocks off the rump so the outline is fuzzy.
    for i, (dx, dy, dz, s) in enumerate(((-0.1, -0.24, 0.42, 0.1),
                                         (0.08, -0.26, 0.46, 0.11),
                                         (0.0, -0.2, 0.53, 0.09),
                                         (-0.06, -0.22, 0.55, 0.075),
                                         (0.1, -0.18, 0.36, 0.085))):
        body.append(bk.block("body.fluff%d" % i, (s, s, s * 0.85), (dx, dy, dz),
                             rot=(0, 0, 18 * i), color=downdark))

    head_dims = (0.3, 0.28, 0.28)
    head_at = (0, 0.14, 0.7)
    head = [bk.block("head.skull", head_dims, head_at, color=down)]
    head.append(bk.block("head.neck", (0.16, 0.16, 0.12), (0, 0.05, 0.53),
                         color=down))
    head.append(bk.face_plate("head.cap", bk.face_of(head_at, head_dims, "top"),
                              (0.2, 0.18), face="top", color=downdark, depth=0.02))
    head += bk.eyes("head.eye", head_at, head_dims, spacing=0.62, height=0.055,
                    size=0.075, style="white", iris="#1d1a22", pupil_scale=0.6)
    # A duck bill is flat and blunt, so barely any taper.
    head += bk.beak("head.bill", head_at, head_dims, width=0.19, length=0.17,
                    height=0.06, color=bill, drop=-0.06, taper=0.12)
    head.append(bk.slab("head.bill.tip", (0.15, 0.055, 0.04),
                        (0, head_at[1] + 0.25, head_at[2] - 0.062),
                        color="#df812a"))
    head += bk.nostrils("head.nose", (0, head_at[1] + 0.2, head_at[2] - 0.048),
                        (0.19, 0.06, 0.06), spacing=0.4, height=0.02,
                        size=0.022, color="#c4701f", face="top")
    head += bk.cheeks("head.blush", head_at, head_dims, spacing=0.8,
                      height=-0.02, size=0.07, color="#f6c98d")
    for i, (dx, dy, dz, tilt) in enumerate(((0.0, -0.07, 0.2, 26),
                                            (-0.05, -0.06, 0.19, 40),
                                            (0.05, -0.05, 0.18, 14))):
        head.append(bk.wedge("head.tuft%d" % i, (0.055, 0.07, 0.13 - i * 0.02),
                             (dx, head_at[1] + dy, head_at[2] + dz),
                             rot=(tilt, 0, 0), color=downdark, taper=0.7))

    # Wing stubs: short and hugging the flank. Made too big they read as paper
    # cards taped to a duck; the point is a nub with a darker trailing edge.
    wing_l, wing_r = bk.wings_flat("wing", (0.13, -0.04, 0.36), span=0.15,
                                   height=0.25, thickness=0.075, color=down,
                                   tip_color=downdark, layers=3, tilt=8)
    tail = bk.tail("tail", (0, -0.2, 0.38), length=0.1, thickness=0.085,
                   color=downdark, style="puff", segments=1, curl=0.8)
    legs = _webbed_feet("leg", (0.09, 0.0, 0.16), shin=0.12, thickness=0.05,
                        web=(0.14, 0.18), color=bill)

    groups = {
        "body": (body, (0, 0, 0.16)),
        "head": (head, (0, 0.06, 0.52)),
        "wing.L": ([wing_l], tuple(wing_l.location)),
        "wing.R": ([wing_r], tuple(wing_r.location)),
        "tail": ([tail], (0, -0.24, 0.4)),
    }
    for key, obj in legs.items():
        groups[key] = ([obj], tuple(obj.location))
    _assemble(root, groups)
    return bk.finish(root)


# ---------------------------------------------------------------------------
# Catfish -- Uncommon, $12/s.
# Chunky bottom-dweller propped up on its pectoral and pelvic fins, the way a
# real catfish rests on gravel. Two earlier attempts failed differently: a flat
# swimming fish normalises into a two-metre-wide pancake, and a reared one
# reads as a fish falling over. Standing on its fins gets the height without
# either problem, and the broad flat head plus four barbels do the naming.
# ---------------------------------------------------------------------------

def build_catfish():
    kit.reset_scene()
    root = kit.empty("root")

    skin = "#6a9aa6"
    dark = "#3a6773"
    pale = "#ecdfb6"
    fin = "#47808d"

    body_dims = (0.36, 0.42, 0.32)
    body_at = (0, -0.04, 0.46)
    body = [bk.block("body.core", body_dims, body_at, color=skin)]
    body += bk.belly("body.belly", body_at, body_dims, color=pale, inset=0.6)
    body += bk.stripes("body.band", body_at, body_dims, count=2, width=0.05,
                       color=dark, axis="y")
    # A dark dorsal surface: fish are countershaded, and it separates the trunk
    # from the pale sand belly at any distance.
    body.append(bk.face_plate("body.back", bk.face_of(body_at, body_dims, "top"),
                              (0.3, 0.36), face="top", color=dark, depth=0.022))
    body.append(bk.block("body.mid", (0.26, 0.2, 0.26), (0, -0.34, 0.46),
                         color=skin))
    body.append(bk.block("body.peduncle", (0.16, 0.16, 0.17), (0, -0.5, 0.46),
                         color=dark))
    body.append(bk.slab("body.underbelly", (0.3, 0.5, 0.07), (0, -0.14, 0.32),
                        color=pale))
    # Tall dorsal ridge -- half this pet's height lives here.
    body.append(bk.wedge("body.dorsal", (0.06, 0.26, 0.24), (0, -0.06, 0.74),
                         rot=(10, 0, 0), color=fin, taper=0.72))
    body.append(bk.wedge("body.adipose", (0.05, 0.13, 0.1), (0, -0.36, 0.65),
                         rot=(-14, 0, 0), color=fin, taper=0.7))
    # Pelvic fins: stubby props that carry the belly clear of the sand.
    for side, sign in (("L", 1), ("R", -1)):
        body.append(_bake(bk.block("body.pelvic.%s" % side, (0.09, 0.18, 0.3),
                                   (sign * 0.16, -0.2, 0.18),
                                   rot=(0, -sign * 14, 0), color=fin)))
        body.append(bk.slab("body.pelvic.%s.foot" % side, (0.13, 0.2, 0.05),
                            (sign * 0.19, -0.18, 0.035), color=fin))

    # Head: wider than the trunk and half its height. That contrast, plus the
    # barbels, is the entire catfish read.
    head_dims = (0.44, 0.32, 0.24)
    head_at = (0, 0.32, 0.42)
    head = [bk.block("head.skull", head_dims, head_at, color=skin)]
    head.append(bk.slab("head.cheek", (0.46, 0.3, 0.07),
                        (0, head_at[1] - 0.02, head_at[2] - 0.1), color=pale))
    head.append(bk.face_plate("head.crown", bk.face_of(head_at, head_dims, "top"),
                              (0.38, 0.26), face="top", color=dark, depth=0.02))
    head += bk.eyes("head.eye", head_at, head_dims, spacing=0.7, height=0.055,
                    size=0.065, style="white", iris="#141b20", pupil_scale=0.62)
    head.append(bk.face_plate("head.mouth", bk.face_of(head_at, head_dims, "front"),
                              (0.36, 0.055), face="front", color="#22333a",
                              depth=0.02, offset=(0, -0.062)))
    # Barbels: two long uppers sweeping out and forward, two short chin pairs.
    for side, sign in (("L", 1), ("R", -1)):
        head.append(_bake(bk.block(
            "head.barbel.%s" % side, (0.04, 0.44, 0.04),
            (sign * 0.26, 0.5, 0.48), rot=(-18, 0, sign * 36), color=fin)))
        head.append(_bake(bk.block(
            "head.chinbarbel.%s" % side, (0.032, 0.26, 0.032),
            (sign * 0.14, 0.46, 0.3), rot=(30, 0, sign * 24), color=fin)))

    # Pectorals splayed down and out: the front pair of props.
    fin_l, fin_r = bk.fins("fin", (0.16, 0.16, 0.34), size=0.22, thickness=0.05,
                           color=fin, tilt=64)
    # Forked caudal: an up lobe and a down lobe, not a vertical sail.
    tail_parts = [
        bk.block("fin.tail.stem", (0.12, 0.14, 0.14), (0, -0.6, 0.46),
                 color=dark),
        _bake(bk.slab("fin.tail.upper", (0.055, 0.24, 0.22), (0, -0.72, 0.58),
                      rot=(-42, 0, 0), color=fin)),
        _bake(bk.slab("fin.tail.lower", (0.055, 0.24, 0.2), (0, -0.72, 0.34),
                      rot=(42, 0, 0), color=fin)),
        bk.slab("fin.tail.rib", (0.075, 0.06, 0.2), (0, -0.67, 0.46), color=dark),
    ]
    tail_fin = _weld_group("fin.tail", tail_parts, (0, -0.56, 0.46))

    groups = {
        "body": (body, (0, -0.04, 0.32)),
        "head": (head, (0, 0.14, 0.4)),
        "fin.L": ([fin_l], tuple(fin_l.location)),
        "fin.R": ([fin_r], tuple(fin_r.location)),
        "fin.tail": ([tail_fin], (0, -0.56, 0.46)),
    }
    _assemble(root, groups)
    return bk.finish(root)


# ---------------------------------------------------------------------------
# Turtle -- Rare, $60/s.
# The shell is the pet: three stepped tiers that read as a dome, a narrow rim
# that does not hide the legs, and a head carried high on a real neck.
# ---------------------------------------------------------------------------

def build_turtle():
    kit.reset_scene()
    root = kit.empty("root")

    shell_c = "#215d5c"
    shell_hi = "#2c7570"
    shell_top = "#3a8f83"
    rim = "#8fdcc8"
    skin = "#8ed4a2"
    pale = "#e9f4dd"
    dark = "#1f4b49"

    # Three shrinking tiers. A stepped ziggurat reads as a dome at this scale
    # and keeps every silhouette edge crisp.
    tier0_at, tier0 = (0, -0.05, 0.5), (0.46, 0.52, 0.2)
    tier1_at, tier1 = (0, -0.05, 0.64), (0.34, 0.4, 0.12)
    tier2_at, tier2 = (0, -0.05, 0.73), (0.2, 0.26, 0.08)
    body = [
        bk.block("body.shell", tier0, tier0_at, color=shell_c),
        bk.block("body.tier1", tier1, tier1_at, color=shell_hi),
        bk.block("body.tier2", tier2, tier2_at, color=shell_top),
    ]
    body.append(bk.face_plate("body.scute.top", bk.face_of(tier2_at, tier2, "top"),
                              (0.13, 0.17), face="top", color=rim, depth=0.022))
    # Scute seams: dark bands around the big tier, in both axes.
    body += bk.stripes("body.seamy", tier0_at,
                       (tier0[0] * 1.01, tier0[1], tier0[2] * 1.01),
                       count=2, width=0.035, color=dark, axis="y")
    body += bk.stripes("body.seamx", tier0_at,
                       (tier0[0], tier0[1] * 1.01, tier0[2] * 1.01),
                       count=1, width=0.035, color=dark, axis="x")
    # Narrow rim: flares just past the shell, never past the legs.
    body.append(bk.block("body.rim", (0.52, 0.58, 0.07), (0, -0.05, 0.38),
                         color=rim))
    body.append(bk.slab("body.plastron", (0.4, 0.46, 0.06), (0, -0.05, 0.32),
                        color=pale))

    head_dims = (0.24, 0.26, 0.22)
    head_at = (0, 0.42, 0.56)
    head = [bk.block("head.skull", head_dims, head_at, color=skin)]
    head.append(bk.block("head.neck", (0.17, 0.2, 0.17), (0, 0.26, 0.5),
                         color=skin))
    head += bk.eyes("head.eye", head_at, head_dims, spacing=0.56, height=0.05,
                    size=0.065, style="white", iris="#16211c", pupil_scale=0.58)
    head += _smile("head.beak", head_at, head_dims, width=0.15, thickness=0.03,
                   drop=-0.06, lift=0.034, color="#3f5c46")
    head += bk.nostrils("head.nose", head_at, head_dims, spacing=0.26,
                        height=0.0, size=0.022, color="#3f5c46")
    head.append(bk.face_plate("head.crown", bk.face_of(head_at, head_dims, "top"),
                              (0.18, 0.18), face="top", color="#5faa7d", depth=0.02))

    legs = bk.legs_quad("leg", front=(0.22, 0.14, 0.34), back=(0.23, -0.2, 0.34),
                        length=0.23, thickness=0.14, color=skin, foot_color=pale)
    tail_obj = bk.tail("tail", (0, -0.34, 0.44), length=0.17, thickness=0.09,
                       color=skin, style="taper", segments=2, curl=0.2)

    groups = {
        "body": (body, (0, -0.05, 0.3)),
        "head": (head, (0, 0.24, 0.48)),
        "tail": ([tail_obj], (0, -0.34, 0.44)),
    }
    for key, obj in legs.items():
        groups[key] = ([obj], tuple(obj.location))
    _assemble(root, groups)
    return bk.finish(root)


# ---------------------------------------------------------------------------
# Anglerkin -- Epic, $260/s.  ORIGINAL.
# A stout deep-lake angler: two thirds head, an underbite jaw crowded with peg
# teeth, and a stalk that arcs the lantern out in FRONT of its own face -- if
# the bulb sits over the skull the whole idea disappears. The stalk is a
# lighter teal than the hide for the same reason.
# ---------------------------------------------------------------------------

def build_anglerkin():
    kit.reset_scene()
    root = kit.empty("root")

    hide = "#28596f"
    hidedark = "#1a3e50"
    stalk_c = "#4d90a6"
    belly = "#8fdcd6"
    tooth = "#f4f7ef"
    lantern = "#9df4ff"
    fin = "#3d7f96"

    # Rear body: deliberately small, so the head reads as enormous.
    body_dims = (0.32, 0.32, 0.34)
    body_at = (0, -0.26, 0.46)
    body = [bk.block("body.core", body_dims, body_at, color=hide)]
    body.append(bk.block("body.peduncle", (0.17, 0.18, 0.19), (0, -0.46, 0.46),
                         color=hidedark))
    body += bk.spots("body.wart", body_at, body_dims, count=4, size=0.06,
                     color=hidedark, seed=13, faces=("top", "left", "right"))
    for i, t in enumerate((0.0, 0.36, 0.72)):
        body.append(bk.wedge("body.spike%d" % i, (0.05, 0.06, 0.13 - i * 0.025),
                             (0, -0.16 - t * 0.3, 0.64 - i * 0.01),
                             rot=(26, 0, 0), color=fin, taper=0.8))
    # Perch fins: the anglerkin squats on its pectorals like a toad.
    legs = {}
    for side, sign in (("FL", 1), ("FR", -1)):
        parts = [
            bk.block("leg.%s.stub" % side, (0.11, 0.13, 0.2),
                     (sign * 0.17, -0.08, 0.17), color=fin),
            bk.slab("leg.%s.web" % side, (0.15, 0.22, 0.05),
                    (sign * 0.19, -0.02, 0.045), rot=(0, 0, sign * 16), color=fin),
        ]
        legs["leg.%s" % side] = _weld_group(
            "leg.%s" % side, parts, (sign * 0.17, -0.08, 0.27))

    # Head: a bucket. Wider, deeper and taller than the whole rear body.
    head_dims = (0.48, 0.42, 0.42)
    head_at = (0, 0.14, 0.52)
    head = [bk.block("head.skull", head_dims, head_at, color=hide)]
    head.append(bk.slab("head.brow", (0.5, 0.36, 0.07),
                        (0, head_at[1] - 0.01, head_at[2] + 0.21), color=hidedark))
    head += _glow_eyes("head.eye", head_at, head_dims, spacing=0.54,
                       height=0.1, size=0.085, color=lantern, strength=1.1)
    head += bk.spots("head.wart", head_at, head_dims, count=4, size=0.055,
                     color=hidedark, seed=21, faces=("top", "left", "right"))

    # Underbite: the lower jaw juts well past the snout and carries the pegs.
    jaw_dims = (0.46, 0.4, 0.16)
    jaw_at = (0, 0.26, 0.32)
    head.append(bk.block("head.jaw", jaw_dims, jaw_at, color=hidedark))
    head.append(bk.slab("head.gum", (0.4, 0.3, 0.04), (0, 0.28, 0.4),
                        color="#4b1f30"))
    head.append(bk.face_plate("head.chin", bk.face_of(jaw_at, jaw_dims, "front"),
                              (0.34, 0.09), face="front", color=belly, depth=0.02,
                              offset=(0, -0.025)))
    # Peg teeth: five up from the jaw, four down from the lip, interleaved.
    for i in range(5):
        head.append(bk.wedge("head.tooth.up%d" % i, (0.044, 0.05, 0.1),
                             ((i - 2) * 0.088, 0.42, 0.45), color=tooth, taper=0.55))
    for i in range(4):
        head.append(bk.wedge("head.tooth.dn%d" % i, (0.042, 0.048, 0.09),
                             ((i - 1.5) * 0.088, 0.352, 0.42), rot=(180, 0, 0),
                             color=tooth, taper=0.55))
    head.append(bk.slab("head.lip", (0.44, 0.11, 0.055), (0, 0.345, 0.475),
                        color=hidedark))

    # The lure: an arc off the brow that carries the lantern forward and down,
    # so it hangs in front of the mouth where a real angler dangles it.
    lure_pts = [(0, 0.02, 0.76), (0, 0.08, 0.96), (0, 0.26, 1.06),
                (0, 0.5, 1.02), (0, 0.63, 0.9)]
    head += _chain("head.stalk", lure_pts, [0.07, 0.065, 0.06, 0.055], stalk_c)
    head.append(bk.block("head.bulb.cap", (0.17, 0.17, 0.07), (0, 0.68, 0.9),
                         color=stalk_c))
    head.append(bk.glow_block("head.bulb", (0.16, 0.16, 0.16), (0, 0.68, 0.79),
                              color=lantern, strength=1.0))
    head += bk.gem("head.spark", (0, 0.68, 0.79), size=0.12, color=lantern,
                   strength=0.9)
    # Two motes drifting off the lantern; epic pets get a little charge.
    head += bk.gem("head.mote0", (0.16, 0.64, 0.98), size=0.05, color=lantern,
                   strength=0.9)
    head += bk.gem("head.mote1", (-0.12, 0.74, 0.62), size=0.04, color=lantern,
                   strength=0.9)

    fin_l, fin_r = bk.fins("fin", (0.23, 0.06, 0.54), size=0.22, thickness=0.05,
                           color=fin, tilt=16)
    # A tall vertical tail fan, so the rear end still has a silhouette.
    tail_parts = [
        bk.block("fin.tail.stem", (0.12, 0.14, 0.14), (0, -0.56, 0.46),
                 color=hidedark),
        bk.slab("fin.tail.fan", (0.05, 0.2, 0.42), (0, -0.66, 0.54),
                rot=(-14, 0, 0), color=fin),
        bk.slab("fin.tail.rib", (0.07, 0.05, 0.3), (0, -0.63, 0.5), color=hidedark),
    ]
    tail_fin = _weld_group("fin.tail", tail_parts, (0, -0.54, 0.46))

    groups = {
        "body": (body, (0, -0.24, 0.22)),
        "head": (head, (0, -0.05, 0.34)),
        "fin.L": ([fin_l], tuple(fin_l.location)),
        "fin.R": ([fin_r], tuple(fin_r.location)),
        "fin.tail": ([tail_fin], (0, -0.54, 0.46)),
    }
    for key, obj in legs.items():
        groups[key] = ([obj], tuple(obj.location))
    _assemble(root, groups)
    return bk.finish(root)


# ---------------------------------------------------------------------------
# Swan -- Epic, $320/s.
# Everything is the neck: a long thin S built with `_chain` inside the head
# group, so the whole curve sways from the shoulder. The hull is kept low and
# the wings are held high and pale-tipped, because white-on-white is the one
# way this pet can lose its shape.
# ---------------------------------------------------------------------------

def build_swan():
    kit.reset_scene()
    root = kit.empty("root")

    white = "#f8f9fc"
    shade = "#cfdaea"
    blue = "#a9c6e0"
    bill = "#ef8f3a"
    knob = "#22222c"

    body_dims = (0.34, 0.6, 0.28)
    body_at = (0, -0.14, 0.36)
    body = [bk.block("body.hull", body_dims, body_at, color=white)]
    # A darker keel and a waterline band give the white hull internal edges --
    # without them the whole pet is one unreadable white mass.
    body.append(bk.block("body.keel", (0.28, 0.5, 0.13), (0, -0.14, 0.21),
                         color=shade))
    body.append(bk.slab("body.waterline", (0.36, 0.56, 0.04), (0, -0.14, 0.28),
                        color=blue))
    body.append(bk.block("body.stern", (0.24, 0.26, 0.3), (0, -0.4, 0.5),
                         rot=(-24, 0, 0), color=white))
    body.append(bk.block("body.shoulder", (0.28, 0.22, 0.22), (0, 0.14, 0.46),
                         color=white))
    body.append(bk.wedge("body.bow", (0.26, 0.2, 0.2), (0, 0.24, 0.34),
                         rot=(-90, 0, 0), color=white, taper=0.35))

    # Folded wings, built by hand rather than with `wings_flat`: the stepped
    # library wing fans three plates outward, which on a swan reads as broken
    # shards floating beside the boat. A swan's wing is one closed shape lying
    # along the flank with its top edge above the back.
    wings = []
    for side, sign in (("L", 1), ("R", -1)):
        anchor = (sign * 0.16, -0.04, 0.46)
        parts = [
            bk.slab("wing.%s.main" % side, (0.08, 0.44, 0.3),
                    (sign * 0.19, -0.12, 0.48), color=shade),
            bk.slab("wing.%s.cover" % side, (0.07, 0.3, 0.24),
                    (sign * 0.16, 0.02, 0.54), color=white),
            bk.slab("wing.%s.tip" % side, (0.065, 0.2, 0.15),
                    (sign * 0.2, -0.34, 0.54), color=blue),
        ]
        wings.append(_weld_group("wing.%s" % side, parts, anchor))
    wing_l, wing_r = wings

    head_dims = (0.16, 0.22, 0.17)
    head_at = (0, 0.2, 1.24)
    neck_pts = [(0, 0.14, 0.5), (0, 0.05, 0.7), (0, 0.02, 0.9),
                (0, 0.07, 1.06), (0, 0.14, 1.16)]
    head = _chain("head.neck", neck_pts, [0.15, 0.14, 0.13, 0.125], white)
    head.append(bk.block("head.skull", head_dims, head_at, color=white))
    head += bk.eyes("head.eye", head_at, head_dims, spacing=0.72, height=0.035,
                    size=0.048, style="dot", iris="#1b1b23")
    head += bk.beak("head.bill", head_at, head_dims, width=0.09, length=0.2,
                    height=0.07, color=bill, drop=-0.035, taper=0.4)
    # The black knob and mask at the base of the bill: the species marking.
    head.append(bk.block("head.knob", (0.08, 0.07, 0.085),
                         (0, head_at[1] + 0.09, head_at[2] + 0.06), color=knob))
    head.append(bk.face_plate("head.mask", bk.face_of(head_at, head_dims, "front"),
                              (0.1, 0.08), face="front", color=knob, depth=0.02,
                              offset=(0, -0.03)))

    tail_obj = _bake(bk.wedge("tail", (0.22, 0.24, 0.12), (0, -0.56, 0.56),
                              rot=(-110, 0, 0), color=shade, taper=0.5))
    kit.set_origin_to(tail_obj, (0, -0.46, 0.52))  # baked: origin move is exact
    legs = _webbed_feet("leg", (0.11, -0.06, 0.22), shin=0.15, thickness=0.06,
                        web=(0.17, 0.22), color=bill)

    groups = {
        "body": (body, (0, -0.14, 0.2)),
        "head": (head, (0, 0.16, 0.44)),
        "wing.L": ([wing_l], tuple(wing_l.location)),
        "wing.R": ([wing_r], tuple(wing_r.location)),
        "tail": ([tail_obj], (0, -0.46, 0.52)),
    }
    for key, obj in legs.items():
        groups[key] = ([obj], tuple(obj.location))
    _assemble(root, groups)
    return bk.finish(root)


# ---------------------------------------------------------------------------
# Axolotl -- Legendary, $2.8K/s.
# Pink, permanently smiling, crowned by six feathery gill stalks and trailing a
# paddle tail. The gills are grouped as ear.L/ear.R so the animator waves them;
# reusing an animation slot for a non-ear is the difference between a toy and a
# pet. Stood up on real legs so the gills do not make it wider than it is tall.
# ---------------------------------------------------------------------------

def build_axolotl():
    kit.reset_scene()
    root = kit.empty("root")

    pink = "#f7a8c8"
    deep = "#e07aa8"
    pale = "#ffe6f1"
    gill = "#ff86b8"
    glow = "#8ff2ff"

    body_dims = (0.3, 0.42, 0.26)
    body_at = (0, -0.12, 0.42)
    body = [bk.block("body.core", body_dims, body_at, color=pink)]
    body.append(bk.block("body.rear", (0.22, 0.22, 0.22), (0, -0.4, 0.44),
                         color=pink))
    body.append(bk.slab("body.belly", (0.26, 0.38, 0.055), (0, -0.12, 0.3),
                        color=pale))
    for i, t in enumerate((0.0, 0.3, 0.6)):
        body.append(bk.slab("body.crest%d" % i, (0.04, 0.17, 0.12 - i * 0.012),
                            (0, -0.02 - t * 0.44, 0.61 + i * 0.01), color=deep))
    # Legendary charge: aqua bubbles drifting off its back. Kept dim so they
    # read as water-blue rather than blowing out to white.
    body += bk.gem("body.bubble0", (0.18, -0.3, 0.76), size=0.075, color=glow,
                   strength=1.0)
    body += bk.gem("body.bubble1", (-0.13, -0.1, 0.82), size=0.055, color=glow,
                   strength=1.0)
    body += bk.gem("body.bubble2", (0.06, -0.46, 0.88), size=0.042, color=glow,
                   strength=1.0)

    head_dims = (0.36, 0.28, 0.24)
    head_at = (0, 0.24, 0.44)
    head = [bk.block("head.skull", head_dims, head_at, color=pink)]
    head.append(bk.slab("head.jaw", (0.34, 0.24, 0.055),
                        (0, head_at[1], head_at[2] - 0.13), color=pale))
    head += bk.eyes("head.eye", head_at, head_dims, spacing=0.6, height=0.05,
                    size=0.052, style="white", iris="#221520", pupil_scale=0.66)
    head += _smile("head.smile", head_at, head_dims, width=0.24, thickness=0.03,
                   drop=-0.045, lift=0.05, color="#c9527f")
    head += bk.cheeks("head.cheek", head_at, head_dims, spacing=0.76,
                      height=-0.05, size=0.085, color="#ff8fb8")

    # Gill stalks: three per side, each a rod with a paddle fan and a glow tip,
    # swept back as well as out so the pet is not wider than it is tall.
    gills = []
    for side, sign in (("L", 1), ("R", -1)):
        anchor = (sign * 0.16, 0.16, 0.48)
        parts = []
        for i, (dz, yaw, ln) in enumerate(((0.1, 22, 0.14), (0.0, 4, 0.16),
                                           (-0.08, -18, 0.13))):
            cx = sign * (0.17 + ln * 0.5)
            cz = 0.48 + dz
            parts.append(bk.block(
                "ear.%s.stalk%d" % (side, i), (ln, 0.05, 0.05),
                (cx, 0.12 - i * 0.03, cz),
                rot=(0, 0, sign * yaw) if i else (0, 0, 0), color=deep,
            ))
            tip = (sign * (0.19 + ln), 0.09 - i * 0.04, cz + dz * 0.2)
            parts.append(_bake(bk.slab(
                "ear.%s.fan%d" % (side, i), (0.13, 0.11, 0.06), tip,
                rot=(0, 0, sign * (yaw + 12)), color=gill)))
            parts.append(bk.glow_block(
                "ear.%s.tip%d" % (side, i), (0.055, 0.055, 0.055),
                (tip[0] + sign * 0.08, tip[1] - 0.02, tip[2]), color=glow,
                strength=1.2))
        gills.append(_weld_group("ear.%s" % side, parts, anchor))

    legs = bk.legs_quad("leg", front=(0.15, 0.06, 0.3), back=(0.16, -0.3, 0.3),
                        length=0.26, thickness=0.07, color=pink, foot_color=pale)

    # Tail: a paddle trailing back and barely lifting. Built tall it reads as a
    # sail and swallows the whole animal, which is what an earlier pass did.
    tail_parts = [
        bk.block("tail.stem", (0.15, 0.22, 0.18), (0, -0.56, 0.45), color=pink),
        bk.slab("tail.fin0", (0.06, 0.26, 0.3), (0, -0.74, 0.48), color=deep),
        bk.slab("tail.fin1", (0.05, 0.18, 0.22), (0, -0.9, 0.52), color=gill),
    ]
    tail_obj = _weld_group("tail", tail_parts, (0, -0.48, 0.44))

    groups = {
        "body": (body, (0, -0.12, 0.3)),
        "head": (head, (0, 0.1, 0.36)),
        "ear.L": ([gills[0]], tuple(gills[0].location)),
        "ear.R": ([gills[1]], tuple(gills[1].location)),
        "tail": ([tail_obj], (0, -0.48, 0.44)),
    }
    for key, obj in legs.items():
        groups[key] = ([obj], tuple(obj.location))
    _assemble(root, groups)
    return bk.finish(root)


# ---------------------------------------------------------------------------
# Leviathan -- Cosmic, $220K/s.
# The showpiece: an armoured serpent breaching the lake. One plated spine rears
# into a tall neck at the front, humps back down through the waterline and
# lifts again into the fluke. Three passes to learn that a coiled pile of
# blocks reads as rubble while a single arc reads as a sea serpent at 24px.
# ---------------------------------------------------------------------------

def build_leviathan():
    kit.reset_scene()
    root = kit.empty("root")

    # Lit values, not deep-water values, and real separation between them. An
    # earlier pass painted the plates #1f4f60: against the preview's near-black
    # background the entire serpent vanished and only its seams rendered.
    plate = "#2b6b7e"
    plate_hi = "#4f9fb0"
    scale_pale = "#dff4ec"
    glow = "#6ff2ff"
    horn = "#f2fbff"
    crest = "#a8f0ea"

    # The spine, written head-first. Note the crest_side=-1 on every chain:
    # the crest perpendicular flips with the direction of travel.
    neck_pts = [(0, 0.3, 1.52), (0, 0.2, 1.2), (0, 0.15, 0.86), (0, 0.18, 0.52)]
    arc_pts = [(0, 0.18, 0.52), (0, 0.06, 0.28), (0, -0.22, 0.28),
               (0, -0.5, 0.42), (0, -0.66, 0.42)]
    tail_pts = [(0, -0.66, 0.42), (0, -0.84, 0.34), (0, -1.02, 0.46),
                (0, -1.12, 0.7)]

    body = _chain("body.neck", neck_pts, [0.28, 0.3, 0.32], plate,
                  crest_color=crest, crest_h=0.44, seam_color=glow,
                  seam_every=2, crest_side=-1.0)
    body += _chain("body.arc", arc_pts, [0.34, 0.36, 0.36, 0.32], plate,
                   crest_color=crest, crest_h=0.32, seam_color=glow,
                   seam_every=2, crest_side=-1.0)
    # Pale throat plates up the front of the neck: a column this dark needs a
    # light underside or it reads as one silhouette-less mass.
    for i, (y, z, w) in enumerate(((0.44, 1.4, 0.2), (0.36, 1.1, 0.22),
                                   (0.3, 0.8, 0.24), (0.32, 0.54, 0.24))):
        body.append(bk.slab("body.throat%d" % i, (w, 0.06, 0.22), (0, y, z),
                            color=scale_pale))
    for i, y in enumerate((0.04, -0.2, -0.44)):
        body.append(bk.slab("body.belly%d" % i, (0.26, 0.18, 0.05),
                            (0, y, 0.13 + abs(y) * 0.1), color=scale_pale))
    # Armour ribs hooping the thickest part of the arc.
    for i, (y, z, w) in enumerate(((0.08, 0.3, 0.4), (-0.22, 0.3, 0.4),
                                   (-0.5, 0.42, 0.36))):
        body.append(bk.block("body.rib%d" % i, (w, 0.06, w * 0.92), (0, y, z),
                             color=plate_hi))

    head_dims = (0.42, 0.42, 0.36)
    head_at = (0, 0.44, 1.68)
    head = [bk.block("head.skull", head_dims, head_at, color=plate_hi)]
    # Long muzzle as its own lower, narrower block -- a tapered skull alone has
    # no profile from the side, which is the only angle a pet is usually seen.
    head.append(bk.block("head.muzzle", (0.3, 0.3, 0.22), (0, 0.74, 1.62),
                         color=plate))
    head.append(_bake(bk.wedge("head.snout", (0.26, 0.2, 0.2), (0, 0.94, 1.62),
                               rot=(-96, 0, 0), color=plate, taper=0.5)))
    head.append(bk.block("head.jaw", (0.28, 0.4, 0.11), (0, 0.74, 1.51),
                         color=plate_hi))
    head.append(bk.slab("head.gum", (0.24, 0.34, 0.04), (0, 0.75, 1.57),
                        color="#3a1f34"))
    for i in range(4):
        head.append(bk.wedge("head.tooth%d" % i, (0.045, 0.05, 0.1),
                             ((i - 1.5) * 0.08, 0.9, 1.57), color=horn,
                             taper=0.6))
    for side, sign in (("L", 1), ("R", -1)):
        head.append(_bake(bk.wedge("head.fang.%s" % side, (0.05, 0.06, 0.13),
                                   (sign * 0.14, 0.76, 1.52), rot=(180, 0, 0),
                                   color=horn, taper=0.6)))
    head += _glow_eyes("head.eye", head_at, head_dims, spacing=0.66,
                       height=0.06, size=0.1, color=glow, strength=1.2)
    head.append(bk.slab("head.brow", (0.46, 0.34, 0.08),
                        (0, head_at[1] - 0.02, head_at[2] + 0.2), color=plate))
    head.append(bk.glow_block("head.crown", (0.14, 0.14, 0.06), (0, 0.36, 1.9),
                              color=glow, strength=1.2))
    # A frill collar around the base of the skull: five fanned blades, the one
    # shape that turns a horned box into a sea serpent.
    for i, ang in enumerate((-72, -38, 0, 38, 72)):
        rad = math.radians(ang)
        head.append(_bake(bk.wedge(
            "head.frill%d" % i, (0.11, 0.1, 0.28),
            (math.sin(rad) * 0.27, 0.3 - math.cos(rad) * 0.06,
             1.7 + math.cos(rad) * 0.24),
            rot=(-14, -ang * 0.9, 0), color=crest, taper=0.6)))

    # Horns as ear.L/.R so they sway: a swept spike plus a cheek spur.
    horns = []
    for side, sign in (("L", 1), ("R", -1)):
        anchor = (sign * 0.13, 0.42, 1.84)
        parts = [
            bk.block("ear.%s.base" % side, (0.1, 0.12, 0.12),
                     (sign * 0.14, 0.42, 1.86), color=plate),
            _bake(bk.wedge("ear.%s.spike" % side, (0.1, 0.1, 0.46),
                           (sign * 0.28, 0.26, 2.0), rot=(44, -sign * 26, 0),
                           color=horn, taper=0.84)),
            _bake(bk.wedge("ear.%s.spur" % side, (0.07, 0.07, 0.22),
                           (sign * 0.3, 0.48, 1.78), rot=(74, -sign * 40, 0),
                           color=horn, taper=0.78)),
        ]
        horns.append(_weld_group("ear.%s" % side, parts, anchor))

    # Pectoral fins where the neck leaves the water: big swept manta blades.
    fin_l, fin_r = bk.fins("fin", (0.17, 0.1, 0.64), size=0.46, thickness=0.06,
                           color=crest, tilt=34)

    # Tail: continues the spine up out of the water into a two-lobed fluke.
    tail_parts = [bk.block("tail.root", (0.3, 0.24, 0.28), (0, -0.68, 0.42),
                           color=plate)]
    tail_parts += _chain("tail.seg", tail_pts, [0.28, 0.24, 0.18], plate_hi,
                         crest_color=crest, crest_h=0.22, seam_color=glow,
                         seam_every=2, crest_side=-1.0)
    tail_parts.append(_bake(bk.slab("tail.fluke.up", (0.06, 0.26, 0.34),
                                    (0, -1.18, 0.9), rot=(-22, 0, 0),
                                    color=crest)))
    tail_parts.append(_bake(bk.slab("tail.fluke.dn", (0.06, 0.22, 0.24),
                                    (0, -1.22, 0.6), rot=(30, 0, 0),
                                    color=crest)))
    tail_obj = _weld_group("tail", tail_parts, (0, -0.64, 0.42))

    # Cosmic signature: a halo ring at the shoulder and orbiting shards.
    body += bk.ring("body.halo", (0, 0.2, 1.06), radius=0.42, thickness=0.032,
                    tilt=68, color=glow, strength=1.1)
    body += bk.gem("body.shard0", (0.48, 0.14, 1.28), size=0.13, color=glow,
                   strength=1.0)
    body += bk.gem("body.shard1", (-0.42, 0.38, 0.94), size=0.1, color=glow,
                   strength=1.0)
    body += bk.gem("body.shard2", (0.28, -0.54, 0.96), size=0.09, color=glow,
                   strength=1.0)

    groups = {
        "body": (body, (0, 0.1, 0.2)),
        "head": (head, (0, 0.3, 1.5)),
        "ear.L": ([horns[0]], tuple(horns[0].location)),
        "ear.R": ([horns[1]], tuple(horns[1].location)),
        "fin.L": ([fin_l], tuple(fin_l.location)),
        "fin.R": ([fin_r], tuple(fin_r.location)),
        "tail": ([tail_obj], (0, -0.64, 0.42)),
    }
    _assemble(root, groups)
    return bk.finish(root)


PETS = {
    "frog": build_frog,
    "duckling": build_duckling,
    "catfish": build_catfish,
    "turtle": build_turtle,
    "anglerkin": build_anglerkin,
    "swan": build_swan,
    "axolotl": build_axolotl,
    "leviathan": build_leviathan,
}
