"""
Fossil Basin -- the eight prehistoric pets.

A tar-pit dig site baked in the sun: dusty olive hide, clay brown, bone cream,
rust red and tar black, with amber as the only light in the biome. Nothing here
glows blue; when a pet needs to look charged it looks like it swallowed a lamp
made of resin.

Conventions are the forest module's, and they are not negotiable:

  * Build facing +Y, feet near z = 0, `bk.finish()` normalises the height.
  * Only the runtime's part names get their own group: body, head, ear.L/.R,
    wing.L/.R, arm.L/.R, leg.FL/.FR/.BL/.BR, tail, fin.L/.R, fin.tail.
  * Pivot at the joint, never at the part's centre. Head pivots at the neck.
  * The head sits clearly forward of and above the torso, joined by a visible
    neck block that belongs to `body`. A head sunk into the shoulders turns
    every dinosaur into the same lump.
  * Long animals are the hazard in this biome: `finish()` normalises height,
    so a creature that is three times longer than it is tall comes out huge
    next to its shelf-mates. Everything here is authored under a length:height
    ratio of about two, which is why the bronto rears its neck, the ankylosaur
    holds its club in, and the mosasaur arches its tail up into the fluke.
"""

import math

from mathutils import Vector

import blockkit as bk
import kit


# ---------------------------------------------------------------------------
# Biome palette. Every pet draws from these families so the shelf reads as one
# dig site rather than eight unrelated toys.
# ---------------------------------------------------------------------------

OLIVE = "#7d8659"
OLIVE_DARK = "#586142"
CLAY = "#9c6b45"
CLAY_DARK = "#6f4a2f"
BONE = "#e8dcc0"
BONE_DARK = "#c0ac81"
RUST = "#a8492c"
RUST_DARK = "#7c3320"
TAR = "#17161a"
TAR_SHEEN = "#2c2833"
AMBER = "#ffb02e"
AMBER_DEEP = "#ff8a1e"


# ---------------------------------------------------------------------------
# shared local helpers
# ---------------------------------------------------------------------------


def _mirror_cluster(parts, name, pivot):
    """
    Weld a hand-built cluster into one mesh with its origin at `pivot`, then
    produce the mirrored twin. This is what blockkit's limb builders do
    internally; the custom legs and paddles here need the same treatment.
    """
    left = kit.join(parts, name + ".L")
    kit.weld(left)
    kit.set_origin_to(left, pivot)
    right = kit.duplicate(left, name + ".R", mirror=True)
    right.location = Vector((-left.location.x, left.location.y, left.location.z))
    return left, right


def _teeth(name, count, x, y0, y1, z, size=0.045, length=0.07, color=BONE,
           down=True):
    """
    Two mirrored rows of fangs along a jaw edge, from y0 to y1 at height z.
    Wedges rather than plates: at icon size a tooth has to break the silhouette
    of the jaw, not just paint it.
    """
    parts = []
    for side in (1, -1):
        for i in range(count):
            t = (i + 0.5) / count
            parts.append(bk.wedge(
                "%s.%s%d" % (name, "L" if side > 0 else "R", i),
                (size, size, length),
                (side * x, y0 + (y1 - y0) * t,
                 z + (-length * 0.45 if down else length * 0.45)),
                rot=(180 if down else 0, 0, 0), color=color, taper=0.72,
            ))
    return parts


# ---------------------------------------------------------------------------
# Dodo -- Rare, $280/s.
# All the character is in the proportions: a pear of a body, useless little
# wings pinned to the flanks, and a beak nearly as long as the skull with a
# hard downward hook on the end.
# ---------------------------------------------------------------------------

def build_dodo():
    kit.reset_scene()
    root = kit.empty("root")

    down = "#96866c"        # dusty grey-olive plumage
    down_dark = "#6d5f49"   # folded wings and rump, dark enough to read
    breast = BONE
    bill = "#7d5a3a"
    bill_pale = "#d9bf88"
    shank = "#c08733"

    # One fat barrel with a heavier rump block behind it, held clear of the
    # ground on real legs. Stacking two shrinking boxes (an earlier pass) built
    # a wedding cake; one mass plus a rump reads as a bird that cannot fly.
    body_dims = (0.44, 0.48, 0.44)
    body_at = (0, -0.04, 0.48)
    body = [bk.block("body.core", body_dims, body_at, color=down)]
    body.append(bk.block("body.rump", (0.38, 0.24, 0.34), (0, -0.3, 0.46),
                         color=down_dark))
    body += bk.belly("body.breast", body_at, body_dims, color=breast, inset=0.52)
    body += bk.spots("body.mottle", body_at, body_dims, count=5, size=0.06,
                     color=down_dark, seed=7, faces=("left", "right", "top"))
    # Thin neck, part of the torso so the head pivots on top of it and reads as
    # a separate lump rather than a bump on the shoulders.
    body.append(bk.block("body.neck", (0.16, 0.16, 0.16), (0, 0.1, 0.76),
                         color=down))

    head_dims = (0.23, 0.22, 0.22)
    head_at = (0, 0.17, 0.95)
    head = [bk.block("head.skull", head_dims, head_at, color=down)]
    # The beak is longer than the skull: a heavy tapered box, then a hook that
    # turns straight down off the end. It is the whole read of the animal.
    head.append(bk.block("head.bill", (0.14, 0.3, 0.14), (0, 0.43, 0.92),
                         rot=(-9, 0, 0), color=bill))
    head.append(bk.wedge("head.hook", (0.12, 0.13, 0.16), (0, 0.56, 0.83),
                         rot=(-152, 0, 0), color=bill_pale, taper=0.55))
    head += bk.nostrils("head.nostril", (0, 0.43, 0.92), (0.14, 0.3, 0.14),
                        spacing=0.5, height=0.035, size=0.03, color="#3a2b1e")
    head += bk.eyes("head.eye", head_at, head_dims, spacing=0.66, height=0.045,
                    size=0.062, style="white", iris="#231c16", pupil_scale=0.6)
    # A darker cap over the crown -- the one marking that reads at icon size.
    head.append(bk.face_plate("head.cap", bk.face_of(head_at, head_dims, "top"),
                              (0.19, 0.17), face="top", color=down_dark,
                              depth=0.02, offset=(0, -0.01)))

    # Useless wings: one dark paddle per flank, too small to lift anything,
    # angled off the body so it survives as a shape in the silhouette.
    shoulder = (0.21, -0.02, 0.6)
    wing_l, wing_r = _mirror_cluster([
        bk.block("wing.plate", (0.07, 0.28, 0.24),
                 (shoulder[0] + 0.02, shoulder[1] - 0.04, shoulder[2] - 0.12),
                 rot=(0, -16, 0), color=down_dark),
        bk.block("wing.tip", (0.06, 0.12, 0.1),
                 (shoulder[0] + 0.07, shoulder[1] - 0.14, shoulder[2] - 0.25),
                 rot=(0, -16, 0), color=breast),
    ], "wing", shoulder)

    # Rump plume: a squat puff plus three quills fanned up over the tail.
    tail_obj = bk.tail("tail", (0, -0.4, 0.56), length=0.14, thickness=0.13,
                       color=breast, style="puff", segments=2, curl=1.0)
    quills = [bk.wedge("tail.quill%d" % i, (0.055, 0.09, 0.2),
                       (dx, -0.47, 0.68), rot=(34, 0, 0), color=BONE_DARK,
                       taper=0.72)
              for i, dx in enumerate((-0.09, 0.0, 0.09))]

    legs = bk.bird_feet("leg", (0.14, -0.02, 0.3), shin=0.28, thickness=0.08,
                        toe=0.2, color=shank)

    groups = {
        "body": (body, (0, 0, 0.26)),
        "head": (head, (0, 0.1, 0.82)),
        "wing.L": ([wing_l], tuple(wing_l.location)),
        "wing.R": ([wing_r], tuple(wing_r.location)),
        "tail": ([tail_obj] + quills, (0, -0.4, 0.56)),
    }
    for key, obj in legs.items():
        groups[key] = ([obj], tuple(obj.location))
    bk.assemble(root, groups)
    return bk.finish(root)


# ---------------------------------------------------------------------------
# Pterodactyl -- Legendary, $22K/s.
# Wings first: the membrane span is more than twice the body length, so the
# silhouette is a kite. The head is the counterweight -- long spear beak
# forward, long bone crest back -- and the legs are almost an afterthought.
# ---------------------------------------------------------------------------

def build_pterodactyl():
    kit.reset_scene()
    root = kit.empty("root")

    hide = "#8a5c3a"
    hide_dark = CLAY_DARK
    web = RUST
    crestc = BONE
    bill = "#c9a25f"
    claw = TAR

    body_dims = (0.24, 0.42, 0.3)
    body_at = (0, -0.08, 0.54)
    body = [bk.block("body.core", body_dims, body_at, color=hide)]
    body += bk.belly("body.chest", body_at, body_dims, color=BONE_DARK, inset=0.72)
    # Neck: two blocks stepping up and forward, so the skull is clear of the
    # shoulders even when the wings are folded over the back.
    body.append(bk.block("body.neck0", (0.16, 0.17, 0.16), (0, 0.11, 0.67),
                         color=hide))
    body.append(bk.block("body.neck1", (0.15, 0.17, 0.15), (0, 0.23, 0.79),
                         color=hide))

    head_dims = (0.17, 0.26, 0.19)
    head_at = (0, 0.4, 0.91)
    head = [bk.block("head.skull", head_dims, head_at, color=hide)]
    # Spear beak, and a thin lower mandible under it so the mouth reads open.
    head.append(bk.wedge("head.beak", (0.1, 0.1, 0.33), (0, 0.68, 0.905),
                         rot=(-94, 0, 0), color=bill, taper=0.82))
    head.append(bk.block("head.jaw", (0.075, 0.24, 0.045), (0, 0.64, 0.845),
                         rot=(-6, 0, 0), color=bill))
    # The crest: one big bone blade raked back over the neck, with an amber
    # rim -- the legendary tier's signature, kept to a single glowing edge.
    head.append(bk.slab("head.crest", (0.055, 0.28, 0.26), (0, 0.29, 1.06),
                        rot=(32, 0, 0), color=crestc))
    head.append(bk.slab("head.crest.rib", (0.07, 0.05, 0.22), (0, 0.34, 1.05),
                        rot=(32, 0, 0), color=BONE_DARK))
    head.append(bk.glow_block("head.crest.rim", (0.065, 0.2, 0.028),
                              (0, 0.245, 1.15), rot=(32, 0, 0), color=AMBER,
                              strength=2.8))
    head += bk.eyes("head.eye", head_at, head_dims, spacing=0.72, height=0.05,
                    size=0.055, style="glow", iris=AMBER)

    # Wings, built by hand rather than with wings_membrane: a pterosaur's web
    # is a triangle hung off one enormous finger, and a rectangle of membrane
    # reads as a cardboard box. Tapering the web along its span is the whole
    # difference between "pterodactyl" and "brown bird".
    shoulder = (0.1, -0.02, 0.66)
    span, web_h = 0.72, 0.5
    sweep = 18.0                       # degrees the wing rakes back along -Y
    rake = math.tan(math.radians(sweep))

    def at(t, dz=0.0):
        """A point t of the way out the swept wing axis."""
        return (shoulder[0] + span * t,
                shoulder[1] - 0.05 - span * t * rake,
                shoulder[2] + dz)

    web_obj = bk.block("wing.web", (span, 0.045, web_h), at(0.5, -0.06),
                       rot=(0, -8, -sweep), color=web)
    kit.taper(web_obj, axis="X", at_min=1.0, at_max=0.38)
    wing_parts = [web_obj]
    # Leading-edge finger: stops short of the wingtip and tapers into it, so it
    # reads as bone inside the membrane rather than a broom handle poking out.
    spar = bk.block("wing.spar", (span * 0.88, 0.055, 0.06), at(0.44, 0.1),
                    rot=(0, -8, -sweep), color=BONE_DARK)
    kit.taper(spar, axis="X", at_min=1.0, at_max=0.45)
    wing_parts.append(spar)
    for i, t in enumerate((0.28, 0.54, 0.78)):
        wing_parts.append(bk.block(
            "wing.bone%d" % i, (0.04, 0.05, web_h * (0.9 - 0.5 * t)),
            at(t, -0.06 - web_h * 0.04 * t), rot=(0, -8, -sweep),
            color=BONE_DARK))
    wing_parts.append(bk.wedge("wing.claw", (0.045, 0.05, 0.11),
                               (shoulder[0] + 0.2, shoulder[1] + 0.04,
                                shoulder[2] + 0.16),
                               rot=(-70, 0, 0), color=claw, taper=0.6))
    wing_l, wing_r = _mirror_cluster(wing_parts, "wing", shoulder)

    legs = bk.legs_pair("leg", (0.09, -0.14, 0.34), length=0.28, thickness=0.07,
                        color=hide_dark, foot_color=claw, foot_length=0.15)

    # Rhamphorhynchus tail: a whip with a rudder vane on the end.
    tail_obj = bk.tail("tail", (0, -0.28, 0.52), length=0.34, thickness=0.075,
                       color=hide_dark, style="whip", segments=4, curl=0.1)
    vane = bk.slab("tail.vane", (0.025, 0.16, 0.14), (0, -0.65, 0.55),
                   color=web)

    groups = {
        "body": (body, (0, 0, 0.34)),
        "head": (head, (0, 0.28, 0.82)),
        "wing.L": ([wing_l], tuple(wing_l.location)),
        "wing.R": ([wing_r], tuple(wing_r.location)),
        "tail": ([tail_obj, vane], (0, -0.28, 0.52)),
    }
    for key, obj in legs.items():
        groups[key] = ([obj], tuple(obj.location))
    bk.assemble(root, groups)
    return bk.finish(root)


# ---------------------------------------------------------------------------
# Ankylosaurus -- Mythic, $120K/s.
# A coffee table with a mace on the back. Low, wide, plated; the head is a
# small armoured wedge pushed well forward of the shell so the two never merge,
# and the club is carried high so the outline is not a flat rectangle.
# ---------------------------------------------------------------------------

def build_ankylosaurus():
    kit.reset_scene()
    root = kit.empty("root")

    hide = OLIVE_DARK
    plate = "#8d6b41"
    plate_hi = "#a98352"
    spike = BONE_DARK
    under = "#8a7e57"

    body_dims = (0.5, 0.56, 0.28)
    body_at = (0, -0.04, 0.36)
    body = [bk.block("body.core", body_dims, body_at, color=hide)]
    body += bk.belly("body.chest", body_at, body_dims, color=under, inset=0.6)
    # The carapace: one dome slab, two rows of knobs, and a spike fringe.
    body.append(bk.slab("body.shell", (0.47, 0.53, 0.14), (0, -0.04, 0.52),
                        color=plate))
    for iy, y in enumerate((0.14, -0.04, -0.22)):
        for sx in (1, -1):
            body.append(bk.block("body.knob%d%d" % (iy, sx > 0),
                                 (0.1, 0.11, 0.07), (sx * 0.13, y, 0.59),
                                 color=plate_hi))
        # Flank spikes point out and slightly up -- the fringe that stops the
        # body reading as a plain slab from the side.
        for sx in (1, -1):
            body.append(bk.wedge("body.spike%d%d" % (iy, sx > 0),
                                 (0.1, 0.12, 0.17), (sx * 0.25, y, 0.44),
                                 rot=(0, sx * 64, 0), color=spike, taper=0.75))
    # Mythic tier: amber heat leaking from the seams between the plates.
    for i, y in enumerate((0.06, -0.14)):
        body.append(bk.glow_block("body.seam%d" % i, (0.34, 0.035, 0.035),
                                  (0, y, 0.585), color=AMBER_DEEP, strength=2.2))

    head_dims = (0.28, 0.24, 0.2)
    head_at = (0, 0.42, 0.35)
    body.append(bk.block("body.neck", (0.26, 0.16, 0.2), (0, 0.25, 0.36),
                         color=hide))
    head = [bk.block("head.skull", head_dims, head_at, color=hide)]
    head.append(bk.slab("head.helm", (0.27, 0.22, 0.06), (0, 0.41, 0.46),
                        color=plate))
    # Four corner horns, the ankylosaur's actual skull furniture.
    for sx in (1, -1):
        head.append(bk.wedge("head.horn.b%d" % (sx > 0), (0.07, 0.07, 0.11),
                             (sx * 0.12, 0.33, 0.5), rot=(22, sx * 30, 0),
                             color=spike, taper=0.7))
        head.append(bk.wedge("head.horn.c%d" % (sx > 0), (0.07, 0.07, 0.1),
                             (sx * 0.15, 0.45, 0.32), rot=(0, sx * 78, 0),
                             color=spike, taper=0.7))
    head.append(bk.block("head.beak", (0.18, 0.09, 0.08), (0, 0.56, 0.3),
                         color="#3f3527"))
    head += bk.eyes("head.eye", head_at, head_dims, spacing=0.66, height=0.02,
                    size=0.05, style="dot", iris="#221c14")

    # Club tail: four shortening segments carried on a shallow rise, then the
    # mace. An earlier pass arced it up like a periscope and the club read as a
    # flag on a pole -- a club has to look heavy, so it stays low and near.
    tail_base = (0, -0.3, 0.4)
    tail_parts = []
    for i, (dy, dz, s) in enumerate(((0.02, 0.0, 0.25), (0.13, 0.03, 0.22),
                                     (0.23, 0.06, 0.19), (0.32, 0.09, 0.17))):
        tail_parts.append(bk.block("tail.seg%d" % i, (s, 0.15, s * 0.82),
                                   (0, tail_base[1] - dy, tail_base[2] + dz),
                                   color=hide))
    club_at = (0, tail_base[1] - 0.44, tail_base[2] + 0.12)
    tail_parts.append(bk.block("tail.club", (0.3, 0.26, 0.24), club_at,
                               color=plate))
    for sx in (1, -1):
        tail_parts.append(bk.wedge("tail.clubspike%d" % (sx > 0),
                                   (0.11, 0.12, 0.16),
                                   (sx * 0.16, club_at[1], club_at[2]),
                                   rot=(0, sx * 76, 0), color=spike, taper=0.7))
    tail_parts.append(bk.wedge("tail.clubtop", (0.12, 0.12, 0.14),
                               (0, club_at[1], club_at[2] + 0.15),
                               color=spike, taper=0.7))

    legs = bk.legs_quad("leg", front=(0.19, 0.16, 0.24), back=(0.2, -0.2, 0.24),
                        length=0.2, thickness=0.13, color=hide, foot_color=plate)

    groups = {
        "body": (body, (0, 0, 0.22)),
        "head": (head, (0, 0.3, 0.3)),
        "tail": (tail_parts, tail_base),
    }
    for key, obj in legs.items():
        groups[key] = ([obj], tuple(obj.location))
    bk.assemble(root, groups)
    return bk.finish(root)


# ---------------------------------------------------------------------------
# Triceratops -- Cosmic, $1.2M/s.
# The frill is the pet. It is built as one big raked slab with a scalloped
# knob rim, sat behind and above the skull so the horns read against it. Cosmic
# tier gets amber resin gems set into the rim and lit eyes.
# ---------------------------------------------------------------------------

def build_triceratops():
    kit.reset_scene()
    root = kit.empty("root")

    hide = "#9a6a44"
    hide_dark = CLAY_DARK
    frill = "#b08050"
    frill_rim = RUST
    horn = "#ece0c2"
    under = BONE_DARK

    body_dims = (0.46, 0.58, 0.42)
    body_at = (0, -0.1, 0.5)
    body = [bk.block("body.core", body_dims, body_at, color=hide)]
    body += bk.belly("body.chest", body_at, body_dims, color=under, inset=0.68)
    body += bk.stripes("body.band", body_at, body_dims, count=3, width=0.05,
                       color="#7f5537", axis="y")
    # Heavy shoulder hump -- ceratopsians carry the frill's weight up front.
    body.append(bk.slab("body.hump", (0.4, 0.3, 0.1), (0, 0.06, 0.72),
                        color=hide))
    body.append(bk.block("body.neck", (0.3, 0.18, 0.26), (0, 0.22, 0.62),
                         color=hide))

    head_dims = (0.34, 0.32, 0.3)
    head_at = (0, 0.44, 0.62)
    head = [bk.block("head.skull", head_dims, head_at, color=hide)]

    # Frill: a shield much taller and wider than the skull, raked back over the
    # shoulders and painted a shade off the body so the two separate. It has to
    # be big -- at half this size it read as a hat.
    # Tapered so it fans out toward the top: a straight rectangle read as a
    # signboard bolted to the skull.
    frill_slab = bk.slab("head.frill", (0.82, 0.09, 0.62), (0, 0.26, 0.94),
                         rot=(22, 0, 0), color=frill)
    kit.taper(frill_slab, axis="Z", at_min=0.62, at_max=1.0)
    head.append(frill_slab)
    frill_face = bk.slab("head.frill.face", (0.62, 0.05, 0.44), (0, 0.315, 0.95),
                         rot=(22, 0, 0), color="#d5a171")
    kit.taper(frill_face, axis="Z", at_min=0.6, at_max=1.0)
    head.append(frill_face)
    # Scalloped rim: knobs marching around the outer arc.
    for i in range(9):
        a = math.radians(-100 + i * 25)
        head.append(bk.block(
            "head.frill.knob%d" % i, (0.085, 0.08, 0.09),
            (math.sin(a) * 0.42, 0.26 - math.cos(a) * 0.135,
             0.94 + math.cos(a) * 0.32),
            color=frill_rim,
        ))
    # Cosmic signature: amber resin veins radiating up the frill in mirrored
    # pairs. Horizontal bars here (an earlier pass) turned the frill into a
    # second glowing face that swamped the real one.
    for sx in (1, -1):
        for i, (dx, h, z) in enumerate(((0.1, 0.18, 0.9), (0.21, 0.13, 0.87))):
            head.append(bk.glow_block(
                "head.vein%d%d" % (i, sx > 0), (0.028, 0.05, h),
                (sx * dx, 0.36, z), rot=(22, sx * 7, 0),
                color=AMBER_DEEP, strength=1.8))
        head += bk.gem("head.gem%d" % (sx > 0), (sx * 0.34, 0.29, 1.14),
                       size=0.085, color=AMBER, strength=3.2)

    # Brow horns swept forward off the face, nose horn short and blunt, parrot
    # beak below. The brow pair starts low on the skull so it reads against the
    # frill instead of sprouting out of it.
    for sx in (1, -1):
        head.append(bk.wedge("head.brow%d" % (sx > 0), (0.085, 0.085, 0.42),
                             (sx * 0.12, 0.72, 0.82), rot=(-62, -sx * 9, 0),
                             color=horn, taper=0.86))
    head.append(bk.wedge("head.nosehorn", (0.095, 0.095, 0.17), (0, 0.6, 0.68),
                         rot=(-24, 0, 0), color=horn, taper=0.8))
    head.append(bk.wedge("head.beak", (0.15, 0.13, 0.18), (0, 0.6, 0.5),
                         rot=(-118, 0, 0), color="#5c452e", taper=0.62))
    head += bk.eyes("head.eye", head_at, head_dims, spacing=0.72, height=0.0,
                    size=0.066, style="white", iris="#1e170f", pupil_scale=0.55)
    head.append(bk.slab("head.brow.ridge", (0.34, 0.17, 0.055), (0, 0.52, 0.76),
                        color=hide_dark))

    legs = bk.legs_quad("leg", front=(0.17, 0.16, 0.34), back=(0.18, -0.26, 0.34),
                        length=0.32, thickness=0.14, color=hide,
                        foot_color=hide_dark)
    tail_obj = bk.tail("tail", (0, -0.4, 0.52), length=0.34, thickness=0.17,
                       color=hide, style="taper", tip_color=hide_dark,
                       segments=3, curl=0.2)

    groups = {
        "body": (body, (0, 0, 0.3)),
        "head": (head, (0, 0.3, 0.56)),
        "tail": ([tail_obj], (0, -0.4, 0.52)),
    }
    for key, obj in legs.items():
        groups[key] = ([obj], tuple(obj.location))
    bk.assemble(root, groups)
    return bk.finish(root)


# ---------------------------------------------------------------------------
# Bronto -- Cosmic, $1.5M/s.
# Everything hangs off one decision: the neck is taller than the rest of the
# animal is long. The head is deliberately too small, the legs are pillars, and
# the tail is a six-segment counterweight so the outline is a suspension bridge.
# ---------------------------------------------------------------------------

def build_bronto():
    kit.reset_scene()
    root = kit.empty("root")

    hide = "#6f7a58"
    hide_dark = "#4e5740"
    under = "#b0a67f"
    ridge = RUST_DARK

    body_dims = (0.54, 0.68, 0.5)
    body_at = (0, -0.16, 0.68)
    body = [bk.block("body.core", body_dims, body_at, color=hide)]
    body += bk.belly("body.chest", body_at, body_dims, color=under, inset=0.62)
    body.append(bk.slab("body.hump", (0.46, 0.56, 0.12), (0, -0.14, 0.96),
                        color=hide_dark))
    # Pale underside painted along the flanks' lower edge, so the bulk reads as
    # a body with a shaded belly rather than one flat olive slab.
    body.append(bk.slab("body.under", (0.5, 0.6, 0.08), (0, -0.16, 0.46),
                        color=under))
    body += bk.spots("body.dapple", body_at, body_dims, count=6, size=0.08,
                     color="#87936a", seed=21, faces=("left", "right", "top"))

    # The neck: five shrinking blocks on a rising arc. Built into `body` so the
    # head's pivot sits at the top vertebra rather than at the shoulder.
    neck = ((0.28, 0.2, 0.92), (0.25, 0.28, 1.09), (0.22, 0.36, 1.24),
            (0.19, 0.44, 1.37), (0.165, 0.53, 1.49))
    for i, (s, y, z) in enumerate(neck):
        body.append(bk.block("body.neck%d" % i, (s, s * 1.15, s), (0, y, z),
                             color=hide))
        # Cosmic tier: amber resin nodes running the length of the spine, one
        # per vertebra, so the neck reads as a strung line of lights.
        body.append(bk.glow_block("body.node%d" % i, (0.055, 0.06, 0.055),
                                  (0, y - s * 0.55, z + s * 0.52),
                                  color=AMBER, strength=2.8))
    for i, y in enumerate((-0.04, -0.2, -0.36)):
        body.append(bk.wedge("body.ridge%d" % i, (0.09, 0.11, 0.14),
                             (0, y, 1.04), color=ridge, taper=0.7))
    # Two resin slabs set into the shoulders -- the cosmic tier needs to look
    # like it is worth a million a second from across the room.
    for sx in (1, -1):
        body += bk.gem("body.gem%d" % (sx > 0), (sx * 0.19, 0.0, 0.98),
                       size=0.12, color=AMBER_DEEP, strength=3.0)

    head_dims = (0.15, 0.21, 0.14)
    head_at = (0, 0.63, 1.57)
    head = [bk.block("head.skull", head_dims, head_at, color=hide)]
    head.append(bk.block("head.snout", (0.12, 0.13, 0.105), (0, 0.77, 1.55),
                         color=hide_dark))
    head += bk.nostrils("head.nostril", (0, 0.77, 1.55), (0.12, 0.13, 0.105),
                        spacing=0.5, height=0.02, size=0.025, color="#241f18")
    head += bk.eyes("head.eye", head_at, head_dims, spacing=0.9, height=0.02,
                    size=0.042, style="glow", iris=AMBER)
    head.append(bk.wedge("head.crest", (0.055, 0.065, 0.09), (0, 0.57, 1.66),
                         rot=(18, 0, 0), color=ridge, taper=0.7))

    # Pillar legs, thick and set wide: at sauropod scale a thin leg reads as a
    # table leg and the whole animal loses its weight.
    legs = bk.legs_quad("leg", front=(0.22, 0.16, 0.5), back=(0.23, -0.42, 0.5),
                        length=0.5, thickness=0.2, color=hide,
                        foot_color=hide_dark)
    tail_obj = bk.tail("tail", (0, -0.48, 0.72), length=0.84, thickness=0.25,
                       color=hide, style="taper", tip_color=hide_dark,
                       segments=6, curl=0.24)

    groups = {
        "body": (body, (0, 0, 0.44)),
        "head": (head, (0, 0.55, 1.52)),
        "tail": ([tail_obj], (0, -0.48, 0.72)),
    }
    for key, obj in legs.items():
        groups[key] = ([obj], tuple(obj.location))
    bk.assemble(root, groups)
    return bk.finish(root)


# ---------------------------------------------------------------------------
# T-Rex -- Secret, $25M/s.
# Head, legs, tail. The arms exist purely as a joke and are sized accordingly.
# The jaw hangs open with two rows of fangs, because a closed mouth on a rex
# at 24 pixels is just a brick.
# ---------------------------------------------------------------------------

def build_t_rex():
    kit.reset_scene()
    root = kit.empty("root")

    hide = "#8a5230"
    hide_dark = "#5e3620"
    back = OLIVE_DARK
    under = BONE_DARK
    tooth = BONE

    body_dims = (0.38, 0.6, 0.44)
    body_at = (0, 0.02, 0.68)
    body = [bk.block("body.core", body_dims, body_at, color=hide)]
    body += bk.belly("body.chest", body_at, body_dims, color=under, inset=0.6)
    # Dark dorsal banding with ember light between the bands: the secret tier's
    # signature, kept on the back so it never fights with the face. Full-depth
    # bands (an earlier pass) wrapped the flanks and read as a green saddle.
    for i, y in enumerate((0.2, 0.02, -0.16)):
        body.append(bk.slab("body.band%d" % i, (0.4, 0.08, 0.18), (0, y, 0.83),
                            color=back))
    for i, y in enumerate((0.11, -0.07)):
        body.append(bk.glow_block("body.ember%d" % i, (0.3, 0.04, 0.04),
                                  (0, y, 0.9), color=AMBER_DEEP, strength=2.4))
    body.append(bk.block("body.neck0", (0.25, 0.2, 0.25), (0, 0.34, 0.82),
                         color=hide))
    body.append(bk.block("body.neck1", (0.23, 0.2, 0.23), (0, 0.46, 0.94),
                         color=hide))

    # The skull is deliberately oversized -- a rex whose head matches its body
    # reads as a lizard. Deep jaw, heavy brow, and the snout pushed well past
    # the neck so nothing about it merges into the shoulders.
    head_dims = (0.34, 0.44, 0.34)
    head_at = (0, 0.64, 1.06)
    head = [bk.block("head.skull", head_dims, head_at, color=hide)]
    head.append(bk.block("head.snout", (0.26, 0.28, 0.22), (0, 0.96, 1.05),
                         color=hide))
    head.append(bk.slab("head.ridge", (0.28, 0.38, 0.07), (0, 0.8, 1.22),
                        color=hide_dark))
    for sx in (1, -1):
        head.append(bk.wedge("head.brow%d" % (sx > 0), (0.08, 0.14, 0.1),
                             (sx * 0.13, 0.77, 1.22), rot=(0, -sx * 16, 0),
                             color=hide_dark, taper=0.6))
    head += bk.nostrils("head.nostril", (0, 0.96, 1.05), (0.26, 0.28, 0.22),
                        spacing=0.46, height=0.06, size=0.04, color="#2a1c12")
    head += bk.eyes("head.eye", head_at, head_dims, spacing=0.8, height=0.085,
                    size=0.06, style="glow", iris=AMBER)
    # Jaw hung open, upper fangs down and lower fangs up into the gap.
    head.append(bk.block("head.jaw", (0.28, 0.42, 0.1), (0, 0.82, 0.79),
                         rot=(-8, 0, 0), color=hide_dark))
    head.append(bk.face_plate("head.gums", bk.face_of((0, 0.82, 0.79),
                                                     (0.28, 0.42, 0.1), "top"),
                              (0.22, 0.34), face="top", color="#3a1f19",
                              depth=0.02))
    head += _teeth("head.fang", 3, 0.105, 0.74, 1.06, 0.885, size=0.055,
                   length=0.085, color=tooth, down=True)
    head += _teeth("head.jawfang", 3, 0.1, 0.74, 1.0, 0.835, size=0.048,
                   length=0.07, color=tooth, down=False)

    # Tiny arms, held clear of the chest so they are visible as a joke rather
    # than lost in the torso.
    arm_l, arm_r = bk.arms("arm", (0.2, 0.3, 0.74), length=0.16,
                           thickness=0.06, color=hide, hand_color=tooth,
                           angle=34)

    # Legs are built by hand: a rex needs a deep thigh mass and a birdlike
    # shin, which the generic leg builder's single shaft cannot give.
    hip = (0.14, -0.06, 0.62)
    leg_parts = [
        bk.block("leg.thigh", (0.17, 0.28, 0.34), (hip[0], hip[1] - 0.02, 0.5),
                 color=hide),
        bk.block("leg.knee", (0.13, 0.15, 0.12), (hip[0], hip[1] + 0.04, 0.34),
                 color=hide_dark),
        bk.block("leg.shin", (0.1, 0.12, 0.22), (hip[0], hip[1] + 0.08, 0.22),
                 color=hide_dark),
        bk.block("leg.foot", (0.14, 0.24, 0.09), (hip[0], hip[1] + 0.18, 0.075),
                 color=hide_dark),
    ]
    for i, dx in enumerate((-0.045, 0.0, 0.045)):
        leg_parts.append(bk.wedge("leg.claw%d" % i, (0.04, 0.04, 0.07),
                                  (hip[0] + dx, hip[1] + 0.31, 0.06),
                                  rot=(-96, 0, 0), color=tooth, taper=0.6))
    leg_l, leg_r = _mirror_cluster(leg_parts, "leg", hip)

    # Long, heavy, held off the ground: the counterweight that makes the pose
    # read as a hunting stance rather than a standing lizard.
    tail_obj = bk.tail("tail", (0, -0.3, 0.7), length=0.72, thickness=0.25,
                       color=hide, style="taper", tip_color=hide_dark,
                       segments=6, curl=0.2)

    groups = {
        "body": (body, (0, 0, 0.4)),
        "head": (head, (0, 0.46, 0.92)),
        "arm.L": ([arm_l], tuple(arm_l.location)),
        "arm.R": ([arm_r], tuple(arm_r.location)),
        "leg.FL": ([leg_l], tuple(leg_l.location)),
        "leg.FR": ([leg_r], tuple(leg_r.location)),
        "tail": ([tail_obj], (0, -0.3, 0.7)),
    }
    bk.assemble(root, groups)
    return bk.finish(root)


# ---------------------------------------------------------------------------
# Tarpitan -- Secret, $32M/s. ORIGINAL.
# What the basin makes when a beast dies in the pits and does not stop walking:
# a tar-soaked quadruped whose hide has slumped off the bone. Bare cream skull,
# ribs standing out of the flanks, an amber resin core burning in the chest,
# and tar drooling off the belly and jaw in frozen strings.
# ---------------------------------------------------------------------------

def build_tarpitan():
    kit.reset_scene()
    root = kit.empty("root")

    hide = TAR
    sheen = TAR_SHEEN
    bone = BONE
    bone_dim = BONE_DARK

    body_dims = (0.42, 0.6, 0.4)
    body_at = (0, -0.04, 0.54)
    body = [bk.block("body.core", body_dims, body_at, color=hide)]
    # Exposed ribcage: four bone staves per flank, standing proud of the tar.
    for sx in (1, -1):
        for i, y in enumerate((0.16, 0.04, -0.08, -0.2)):
            body.append(bk.block("body.rib%d%d" % (i, sx > 0),
                                 (0.05, 0.07, 0.34), (sx * 0.205, y, 0.55),
                                 rot=(0, sx * 12, 0), color=bone))
    # Vertebrae marching along the spine, then tar slumped over the shoulders.
    for i, y in enumerate((0.18, 0.06, -0.06, -0.18, -0.3)):
        body.append(bk.wedge("body.spine%d" % i, (0.07, 0.08, 0.1),
                             (0, y, 0.76), color=bone_dim, taper=0.65))
    body.append(bk.slab("body.slick", (0.4, 0.34, 0.08), (0, 0.06, 0.74),
                        color=sheen))
    # The core: amber resin burning behind the ribs, sitting proud of the chest.
    body.append(bk.glow_block("body.core.light", (0.17, 0.07, 0.15),
                              (0, 0.28, 0.55), color=AMBER, strength=3.6))
    body.append(bk.block("body.core.rim", (0.23, 0.05, 0.21), (0, 0.25, 0.55),
                         color=bone_dim))
    # Frozen drips off the underside -- the shape that says "soaked", not "black".
    for i, (dx, dy, ln) in enumerate(((0.13, 0.14, 0.2), (-0.1, 0.02, 0.28),
                                      (0.06, -0.12, 0.16), (-0.14, -0.24, 0.23),
                                      (0.17, -0.06, 0.15))):
        body.append(bk.wedge("body.drip%d" % i, (0.06, 0.06, ln),
                             (dx, dy, 0.34 - ln * 0.45), rot=(180, 0, 0),
                             color=sheen, taper=0.72))
    # Embers showing through the seams between the ribs: the tar is only a
    # crust, and the thing under it is still burning.
    for sx in (1, -1):
        for i, y in enumerate((0.1, -0.02, -0.14)):
            body.append(bk.glow_block("body.crack%d%d" % (i, sx > 0),
                                      (0.03, 0.045, 0.14), (sx * 0.2, y, 0.55),
                                      color=AMBER_DEEP, strength=2.2))
    body.append(bk.block("body.neck0", (0.17, 0.17, 0.17), (0, 0.2, 0.68),
                         color=hide))
    body.append(bk.block("body.neck1", (0.155, 0.16, 0.155), (0, 0.31, 0.78),
                         color=sheen))

    head_dims = (0.26, 0.3, 0.26)
    head_at = (0, 0.44, 0.86)
    head = [bk.block("head.skull", head_dims, head_at, color=bone)]
    head.append(bk.block("head.snout", (0.18, 0.2, 0.15), (0, 0.66, 0.83),
                         color=bone))
    head.append(bk.block("head.jaw", (0.16, 0.22, 0.055), (0, 0.65, 0.72),
                         rot=(-8, 0, 0), color=bone_dim))
    head += _teeth("head.fang", 2, 0.06, 0.6, 0.72, 0.762, size=0.038,
                   length=0.055, color=bone, down=True)
    # Empty sockets with an ember sunk in each -- the amber eyes.
    head += bk.eyes("head.socket", head_at, head_dims, spacing=0.56,
                    height=0.045, size=0.095, style="dot", iris="#0e0d10")
    for sx in (1, -1):
        head.append(bk.face_plate(
            "head.ember%d" % (sx > 0), bk.face_of(head_at, head_dims, "front"),
            (0.05, 0.05), face="front",
            material=kit.mat("tarpit.ember", kit.hexcol(AMBER), rough=0.2,
                             emission=kit.hexcol(AMBER), emission_strength=4.0),
            depth=0.02, offset=(sx * 0.073, 0.045), proud=bk.PROUD * 4,
        ))
    head += bk.nostrils("head.nostril", (0, 0.66, 0.83), (0.18, 0.2, 0.15),
                        spacing=0.42, height=0.03, size=0.03, color="#0e0d10")
    # Tar poured over the crown and hanging off the jaw.
    head.append(bk.slab("head.slick", (0.24, 0.26, 0.06), (0, 0.42, 1.0),
                        color=sheen))
    for sx in (1, -1):
        head.append(bk.wedge("head.horn%d" % (sx > 0), (0.06, 0.06, 0.19),
                             (sx * 0.1, 0.36, 1.09), rot=(16, sx * 20, 0),
                             color=bone_dim, taper=0.78))
        head.append(bk.wedge("head.drip%d" % (sx > 0), (0.045, 0.045, 0.14),
                             (sx * 0.07, 0.63, 0.63), rot=(180, 0, 0),
                             color=sheen, taper=0.7))

    legs = bk.legs_quad("leg", front=(0.16, 0.18, 0.36), back=(0.17, -0.22, 0.36),
                        length=0.34, thickness=0.115, color=hide,
                        foot_color=bone_dim)

    tail_obj = bk.tail("tail", (0, -0.34, 0.6), length=0.42, thickness=0.14,
                       color=hide, style="taper", tip_color=sheen, segments=4,
                       curl=0.35)
    tail_bones = [bk.wedge("tail.bone%d" % i, (0.055, 0.06, 0.09),
                           (0, -0.42 - i * 0.11, 0.68 + i * 0.045),
                           color=bone_dim, taper=0.65)
                  for i in range(3)]

    groups = {
        "body": (body, (0, 0, 0.34)),
        "head": (head, (0, 0.32, 0.76)),
        "tail": ([tail_obj] + tail_bones, (0, -0.34, 0.6)),
    }
    for key, obj in legs.items():
        groups[key] = ([obj], tuple(obj.location))
    bk.assemble(root, groups)
    return bk.finish(root)


# ---------------------------------------------------------------------------
# Mosasaurus -- Eternal, $180M/s.
# The showpiece. A torpedo arched from raised jaws through a deep chest to a
# tail that sweeps up into a vertical fluke, so the outline is a long S rather
# than a plank. Four paddles, a bone-crest dorsal ridge, amber bioluminescence
# down both flanks -- the eternal tier should look lit from inside.
# ---------------------------------------------------------------------------

def build_mosasaurus():
    kit.reset_scene()
    root = kit.empty("root")

    hide = "#3f4a3c"
    hide_dark = "#2b332b"
    under = "#d3c9a6"
    fin_c = RUST_DARK
    tooth = BONE

    # --- torso: three blocks stepping down and back from the shoulders
    body = [
        bk.block("body.chest", (0.36, 0.34, 0.38), (0, 0.14, 0.62), color=hide),
        bk.block("body.mid", (0.34, 0.34, 0.34), (0, -0.16, 0.56), color=hide),
        bk.block("body.rear", (0.27, 0.3, 0.28), (0, -0.44, 0.54), color=hide),
    ]
    body.append(bk.slab("body.belly", (0.24, 0.8, 0.07), (0, -0.1, 0.42),
                        color=under))
    body.append(bk.block("body.neck", (0.3, 0.2, 0.3), (0, 0.4, 0.68),
                         color=hide))
    # Dorsal crest of bone fins along the back.
    for i, (y, z, h) in enumerate(((0.24, 0.83, 0.12), (0.02, 0.79, 0.15),
                                   (-0.2, 0.74, 0.13), (-0.4, 0.7, 0.1))):
        body.append(bk.wedge("body.crest%d" % i, (0.05, 0.14, h), (0, y, z),
                             color=BONE_DARK, taper=0.7))
    # Eternal signature: amber light running the flanks, sized down and
    # staggered -- four equal bars in a row read as windows on a bus.
    for sx in (1, -1):
        for i, (y, z, w) in enumerate(((0.2, 0.62, 0.09), (0.02, 0.57, 0.07),
                                       (-0.18, 0.6, 0.06), (-0.34, 0.55, 0.05))):
            body.append(bk.glow_block(
                "body.lume%d%d" % (i, sx > 0), (0.035, w, 0.045),
                (sx * 0.175, y, z), color=AMBER, strength=2.8))
    body += bk.spots("body.mottle", (0, -0.16, 0.56), (0.34, 0.34, 0.34),
                     count=5, size=0.07, color=hide_dark, seed=13,
                     faces=("top", "left", "right"))

    # --- head: long toothed jaws, held above the shoulders
    head_dims = (0.3, 0.3, 0.27)
    head_at = (0, 0.62, 0.76)
    head = [bk.block("head.skull", head_dims, head_at, color=hide)]
    head.append(bk.block("head.upperjaw", (0.24, 0.3, 0.14), (0, 0.86, 0.78),
                         rot=(4, 0, 0), color=hide))
    head.append(bk.slab("head.snoutridge", (0.14, 0.26, 0.05), (0, 0.86, 0.855),
                        rot=(4, 0, 0), color=hide_dark))
    head.append(bk.block("head.lowerjaw", (0.2, 0.28, 0.08), (0, 0.85, 0.63),
                         rot=(-9, 0, 0), color=under))
    head += _teeth("head.fang", 3, 0.085, 0.78, 0.96, 0.712, size=0.045,
                   length=0.07, color=tooth, down=True)
    head += _teeth("head.jawfang", 3, 0.08, 0.78, 0.93, 0.68, size=0.04,
                   length=0.06, color=tooth, down=False)
    head += bk.eyes("head.eye", head_at, head_dims, spacing=0.8, height=0.05,
                    size=0.06, style="glow", iris=AMBER)
    for sx in (1, -1):
        head.append(bk.wedge("head.brow%d" % (sx > 0), (0.07, 0.13, 0.08),
                             (sx * 0.12, 0.68, 0.9), rot=(0, -sx * 18, 0),
                             color=hide_dark, taper=0.6))
    # Resin crown set INTO the skull's top face; floated behind the head in an
    # earlier pass it just looked like a bug in the scene.
    head += bk.gem("head.crown", (0, 0.63, 0.89), size=0.1, color=AMBER_DEEP,
                   strength=3.4)

    # --- paddles: a flat blade with a bone spar, mirrored front and back
    def paddle(tag, at, size, tilt):
        parts = [
            bk.slab("%s.blade" % tag, (size, size * 0.78, 0.055),
                    (at[0] + size * 0.46, at[1], at[2] - size * 0.2),
                    rot=(0, -tilt, 10), color=fin_c),
            bk.block("%s.spar" % tag, (size * 0.55, 0.05, 0.055),
                     (at[0] + size * 0.3, at[1] + size * 0.2,
                      at[2] - size * 0.12),
                     rot=(0, -tilt, 10), color=BONE_DARK),
        ]
        return _mirror_cluster(parts, tag, at)

    fin_l, fin_r = paddle("fin", (0.17, 0.16, 0.52), 0.38, 26)
    hind_l, hind_r = paddle("leg.B", (0.14, -0.4, 0.48), 0.28, 24)

    # --- tail: four segments sweeping back and up into a vertical fluke
    tail_base = (0, -0.58, 0.54)
    tail_parts = []
    for i, (dy, dz, s) in enumerate(((0.02, 0.03, 0.24), (0.15, 0.13, 0.2),
                                     (0.27, 0.25, 0.16), (0.38, 0.37, 0.12))):
        tail_parts.append(bk.block("tail.seg%d" % i, (s * 0.8, 0.16, s),
                                   (0, tail_base[1] - dy, tail_base[2] + dz),
                                   color=hide if i < 2 else hide_dark))
    tail_parts.append(bk.slab("tail.keel", (0.04, 0.4, 0.1),
                              (0, tail_base[1] - 0.22, tail_base[2] + 0.02),
                              rot=(-24, 0, 0), color=BONE_DARK))

    # Fluke: a crescent, not a flag. Two lobes leaning away from each other off
    # the last vertebra, the upper one taller, so the tail ends in a shape
    # instead of a post.
    fluke_at = (0, tail_base[1] - 0.44, tail_base[2] + 0.45)
    fluke = [
        bk.slab("fin.tail.up", (0.05, 0.26, 0.36),
                (0, fluke_at[1] - 0.07, fluke_at[2] + 0.16), rot=(-26, 0, 0),
                color=fin_c),
        bk.slab("fin.tail.low", (0.05, 0.22, 0.24),
                (0, fluke_at[1] + 0.02, fluke_at[2] - 0.13), rot=(22, 0, 0),
                color=fin_c),
        bk.slab("fin.tail.spar", (0.06, 0.07, 0.3),
                (0, fluke_at[1] + 0.02, fluke_at[2] + 0.04), rot=(-8, 0, 0),
                color=BONE_DARK),
        bk.glow_block("fin.tail.lume", (0.065, 0.05, 0.24),
                      (0, fluke_at[1] - 0.12, fluke_at[2] + 0.2),
                      rot=(-26, 0, 0), color=AMBER_DEEP, strength=3.0),
    ]

    groups = {
        "body": (body, (0, 0, 0.4)),
        "head": (head, (0, 0.48, 0.68)),
        "fin.L": ([fin_l], tuple(fin_l.location)),
        "fin.R": ([fin_r], tuple(fin_r.location)),
        "leg.BL": ([hind_l], tuple(hind_l.location)),
        "leg.BR": ([hind_r], tuple(hind_r.location)),
        "tail": (tail_parts, tail_base),
        "fin.tail": (fluke, fluke_at),
    }
    bk.assemble(root, groups)
    return bk.finish(root)


PETS = {
    "dodo": build_dodo,
    "pterodactyl": build_pterodactyl,
    "ankylosaurus": build_ankylosaurus,
    "triceratops": build_triceratops,
    "bronto": build_bronto,
    "t-rex": build_t_rex,
    "tarpitan": build_tarpitan,
    "mosasaurus": build_mosasaurus,
}
