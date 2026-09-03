"""
Verdant Snarl -- the jungle roster.

Eight pets, from a $90/s chimp to a $3.5M/s constrictor. The biome palette is
deep green, wet bark brown and hot tropical accent (magenta / orange / yellow),
and every creature has to carry at least one of the accents so the roster reads
as one shelf rather than eight strangers.

Conventions, same as Whisperpine:
  * Build facing +Y, feet near z = 0, `finish()` normalises the height.
  * Only the runtime's part names animate: body, head, ear.L/.R, wing.L/.R,
    arm.L/.R, leg.FL/.FR/.BL/.BR, tail, fin.L/.R, fin.tail. Reusing a slot for
    something that is not literally an ear (the pineape's leaf crown, the king
    snake's crown horns) is fine and encouraged -- it is how a non-standard
    appendage gets to sway.
  * Pivot at the joint, never at the part's centre.
  * Silhouette first. The toucan is a beak, the croc is a length, the gorilla is
    a pair of shoulders, the spider is eight legs. If the outline does not say
    it, the detail will not save it.
"""

import math

import blockkit as bk
import kit


# ---------------------------------------------------------------------------
# shared helpers
#
# Spider legs, snake coils and ridged spines all need boxes that are not axis
# aligned. Doing the trig once here is far safer than eyeballing Euler triples
# a hundred times, and it keeps the per-creature code about anatomy.
# ---------------------------------------------------------------------------

def _strut(name, a, b, thick, color, taper=0.0, segments=1, squash=1.0):
    """A box spanning the segment a -> b. `squash` flattens the cross section."""
    dx, dy, dz = b[0] - a[0], b[1] - a[1], b[2] - a[2]
    length = max(math.sqrt(dx * dx + dy * dy + dz * dz), 1e-6)
    pitch = math.degrees(math.acos(max(-1.0, min(1.0, dz / length))))
    yaw = math.degrees(math.atan2(dy, dx))
    mid = ((a[0] + b[0]) * 0.5, (a[1] + b[1]) * 0.5, (a[2] + b[2]) * 0.5)
    dims = (thick, thick * squash, length)
    rot = (0, pitch, yaw)
    if taper > 0:
        return bk.wedge(name, dims, mid, rot=rot, color=color, taper=taper)
    return bk.block(name, dims, mid, rot=rot, color=color, segments=segments)


def _plate_facing(name, at, outward, size, thick, color, stand=0.0):
    """
    A flat plate whose local +Z points along `outward` -- scale plates that have
    to lie on a curved (coiled) surface rather than on a box face.

    `stand` is the distance from `at` out to the host surface. Getting this
    wrong is silent and total: the plate ends up inside the body and simply
    never renders.
    """
    length = max(math.sqrt(sum(c * c for c in outward)), 1e-6)
    ux, uy, uz = [c / length for c in outward]
    pitch = math.degrees(math.acos(max(-1.0, min(1.0, uz))))
    yaw = math.degrees(math.atan2(uy, ux))
    push = stand + thick * 0.5
    loc = (at[0] + ux * push, at[1] + uy * push, at[2] + uz * push)
    return bk.block(name, (size[0], size[1], thick), loc, rot=(0, pitch, yaw),
                    color=color, segments=1)


def _diamonds(name, at, dims, face, cols, rows, size, color, inset=0.78):
    """A lattice of 45-degree squares over one face of a box -- the pineapple
    rind, and the only cheap way to say 'textured' with flat colour."""
    plane = bk.face_of(at, dims, face)
    parts = []
    for cx in range(cols):
        for cy in range(rows):
            u = ((cx + 0.5) / cols - 0.5) * inset
            v = ((cy + 0.5) / rows - 0.5) * inset
            if face in ("left", "right"):
                loc = (plane[0] + (0.012 if face == "left" else -0.012),
                       plane[1] + u * dims[1], plane[2] + v * dims[2])
                rot = (45, 0, 0)
                box = (0.022, size, size)
            elif face in ("front", "back"):
                loc = (plane[0] + u * dims[0],
                       plane[1] + (0.012 if face == "front" else -0.012),
                       plane[2] + v * dims[2])
                rot = (0, 45, 0)
                box = (size, 0.022, size)
            else:  # top
                loc = (plane[0] + u * dims[0], plane[1] + v * dims[1],
                       plane[2] + 0.012)
                rot = (0, 0, 45)
                box = (size, size, 0.022)
            parts.append(bk.block("%s.%d_%d" % (name, cx, cy), box, loc, rot=rot,
                                  color=color, segments=1))
    return parts


# ---------------------------------------------------------------------------
# Chimpanzee -- Rare, $90/s.
# Small, hunched, long-armed. The read is arm length against a short body plus
# the two saucer ears standing off the skull; everything else is support.
# ---------------------------------------------------------------------------

def build_chimpanzee():
    kit.reset_scene()
    root = kit.empty("root")

    fur = "#4a3a2c"
    fur_lt = "#6b5340"
    skin = "#d2a878"
    skin_dk = "#9c6f52"

    body_dims = (0.32, 0.28, 0.40)
    body_at = (0, -0.03, 0.52)
    body = [bk.block("body.core", body_dims, body_at, color=fur)]
    body += bk.belly("body.chest", body_at, body_dims, color=fur_lt, inset=0.7)
    body.append(bk.block("body.hips", (0.29, 0.26, 0.18), (0, -0.04, 0.33),
                         color=fur))
    # Shoulder caps: without them the long arms look pinned onto a slab.
    for side, sign in (("L", 1), ("R", -1)):
        body.append(bk.block("body.shoulder.%s" % side, (0.12, 0.24, 0.17),
                             (sign * 0.185, 0.0, 0.68), color=fur))

    head_dims = (0.29, 0.27, 0.28)
    head_at = (0, 0.19, 0.95)
    head = [bk.block("head.skull", head_dims, head_at, color=fur)]
    head.append(bk.block("head.neck", (0.16, 0.14, 0.1), (0, 0.11, 0.79),
                         color="#2e241c"))
    face = bk.face_of(head_at, head_dims, "front")
    # Chimp face: a pale mask filling the lower two thirds, brow bar above it.
    head.append(bk.face_plate("head.face", face, (0.22, 0.19), face="front",
                              color=skin, depth=0.026, offset=(0, -0.03)))
    head.append(bk.face_plate("head.brow", face, (0.25, 0.05), face="front",
                              color=skin_dk, depth=0.03, offset=(0, 0.09),
                              proud=bk.PROUD * 2))
    head += bk.eyes("head.eye", head_at, head_dims, spacing=0.44, height=0.02,
                    size=0.055, style="white", iris="#241a14", pupil_scale=0.6)
    head.append(bk.block("head.muzzle", (0.15, 0.09, 0.09),
                         (0, head_at[1] + 0.15, head_at[2] - 0.09), color=skin))
    head += bk.mouth("head.mouth", (0, head_at[1] + 0.15, head_at[2] - 0.09),
                     (0.15, 0.09, 0.09), width=0.09, height=0.018, drop=-0.018,
                     color="#3b2820", style="grin")
    head += bk.nostrils("head.nose", (0, head_at[1] + 0.15, head_at[2] - 0.09),
                        (0.15, 0.09, 0.09), spacing=0.34, height=0.024,
                        size=0.02, color="#3b2820")
    # Scruff of hair on the crown -- keeps the skull from reading as a cube.
    for i, dx in enumerate((-0.07, 0.0, 0.07)):
        head.append(bk.block("head.scruff%d" % i, (0.06, 0.1, 0.06),
                             (dx, head_at[1] - 0.03, head_at[2] + 0.16),
                             color=fur_lt))

    # Ears: big flat saucers on the SIDES of the skull, not on top.
    ears = {}
    for side, sign in (("L", 1), ("R", -1)):
        outer = bk.block("ear.%s.outer" % side, (0.05, 0.15, 0.17),
                         (sign * 0.185, 0.17, 0.95), color=fur_lt)
        inner = bk.block("ear.%s.inner" % side, (0.03, 0.09, 0.1),
                         (sign * 0.215, 0.17, 0.95), color=skin_dk)
        ears["ear.%s" % side] = ([outer, inner], (sign * 0.15, 0.17, 0.95))

    # Long arms are the whole read: knuckles nearly at the floor.
    arm_l, arm_r = bk.arms("arm", (0.19, 0.03, 0.72), length=0.62, thickness=0.105,
                           color="#3d2f24", hand_color=skin_dk, angle=10)
    legs = bk.legs_pair("leg", (0.1, -0.01, 0.31), length=0.27, thickness=0.11,
                        color=fur, foot_color=skin_dk, foot_length=0.19)

    groups = {
        "body": (body, (0, 0, 0.3)),
        "head": (head, (0, 0.11, 0.79)),
        "arm.L": ([arm_l], tuple(arm_l.location)),
        "arm.R": ([arm_r], tuple(arm_r.location)),
    }
    groups.update(ears)
    for key, obj in legs.items():
        groups[key] = ([obj], tuple(obj.location))
    bk.assemble(root, groups)
    return bk.finish(root)


# ---------------------------------------------------------------------------
# Toucan -- Rare, $110/s.
# The beak is the entire animal: four stacked segments, orange into yellow into
# magenta into a black tip, longer than the body is deep.
# ---------------------------------------------------------------------------

def build_toucan():
    kit.reset_scene()
    root = kit.empty("root")

    coal = "#26232d"
    coal_lt = "#3f3b4b"
    bib = "#f6efd8"
    # Six bands, warm to hot to a black tip, so the beak reads as one curved
    # horn rather than four stacked toys.
    beak_cols = ("#ff8a2b", "#ff9d2b", "#ffc134", "#ffd23f", "#e0338f", "#1d1b22")

    body_dims = (0.28, 0.32, 0.38)
    body_at = (0, -0.04, 0.42)
    body = [bk.block("body.core", body_dims, body_at, color=coal)]
    # Throat bib, kept narrow -- a full-width plate turns the bird into a
    # penguin, and the beak has to stay the loudest thing on the model.
    faceplane_b = bk.face_of(body_at, body_dims, "front")
    body.append(bk.face_plate("body.bib", faceplane_b, (0.15, 0.15), face="front",
                              color=bib, depth=0.022, offset=(0, 0.07)))
    body.append(bk.face_plate("body.bib.lo", faceplane_b, (0.13, 0.05),
                              face="front", color="#ffd23f", depth=0.022,
                              offset=(0, -0.03), proud=bk.PROUD * 2))
    # Scarlet band under the bib: the toucan's one non-negotiable marking.
    body.append(bk.face_plate("body.band", faceplane_b, (0.12, 0.035),
                              face="front", color="#e0243a", depth=0.02,
                              offset=(0, -0.075), proud=bk.PROUD * 3))

    head_dims = (0.28, 0.26, 0.32)
    head_at = (0, 0.14, 0.84)
    head = [bk.block("head.skull", head_dims, head_at, color=coal)]

    # Beak: segments marching forward from the head's front face, each a little
    # smaller and tipped a little further down, so it curves. It is longer than
    # the bird is tall on purpose -- that is the whole silhouette.
    front = head_at[1] + head_dims[1] * 0.5
    seg_len = 0.12
    for i, col in enumerate(beak_cols):
        t = i / (len(beak_cols) - 1.0)
        w = 0.22 * (1 - 0.74 * t)
        h = 0.28 * (1 - 0.7 * t)
        y = front + seg_len * (i + 0.44)
        z = head_at[2] - 0.05 - 0.13 * t ** 1.6
        head.append(bk.block("head.beak%d" % i, (w, seg_len * 1.12, h), (0, y, z),
                             rot=(-11 * t, 0, 0), color=col, segments=1))
        # The mandible split, drawn as a dark lower edge per segment so it
        # tapers with the beak instead of hanging past the tip as a flat board.
        head.append(bk.block("head.keel%d" % i,
                             (w * 1.02, seg_len * 1.1, 0.014),
                             (0, y, z - h * 0.42), rot=(-11 * t, 0, 0),
                             color=coal, segments=1))
    head.append(bk.block("head.beakroot", (0.235, 0.045, 0.3),
                         (0, front + 0.016, head_at[2] - 0.04), color=coal_lt))

    # Bare blue skin patch around each eye -- the reason toucan faces read.
    faceplane = bk.face_of(head_at, head_dims, "front")
    for side, sign in (("L", 1), ("R", -1)):
        head.append(bk.face_plate("head.patch.%s" % side, faceplane, (0.09, 0.1),
                                  face="front", color="#4fc3d9", depth=0.022,
                                  offset=(sign * 0.085, 0.1)))
    head += bk.eyes("head.eye", head_at, head_dims, spacing=0.66, height=0.1,
                    size=0.055, style="white", iris="#141018", pupil_scale=0.62)

    wing_l, wing_r = bk.wings_flat("wing", (0.14, -0.03, 0.48), span=0.2,
                                   height=0.28, thickness=0.06, color=coal_lt,
                                   tip_color="#3d3a48", layers=2, tilt=8)
    tail_obj = bk.tail("tail", (0, -0.19, 0.4), length=0.3, thickness=0.12,
                       color=coal, style="flat", segments=3, curl=0.35)
    # Scarlet undertail coverts, tucked under the base rather than tipping it.
    tail_red = bk.block("tail.coverts", (0.16, 0.12, 0.05), (0, -0.24, 0.35),
                        color="#e0243a")
    # Pale rump patch above the coverts: it separates the black body from the
    # black tail, which otherwise merge into one blob from behind.
    tail_rump = bk.block("tail.rump", (0.18, 0.11, 0.07), (0, -0.22, 0.47),
                         color="#f6efd8")
    legs = bk.bird_feet("leg", (0.08, 0.0, 0.21), shin=0.15, thickness=0.045,
                        toe=0.13, color="#7fa9c4")

    groups = {
        "body": (body, (0, 0, 0.22)),
        "head": (head, (0, 0.06, 0.68)),
        "wing.L": ([wing_l], tuple(wing_l.location)),
        "wing.R": ([wing_r], tuple(wing_r.location)),
        "tail": ([tail_obj, tail_red, tail_rump], (0, -0.19, 0.4)),
    }
    for key, obj in legs.items():
        groups[key] = ([obj], tuple(obj.location))
    bk.assemble(root, groups)
    return bk.finish(root)


# ---------------------------------------------------------------------------
# Crocodile -- Epic, $420/s.
# Long, low, and the only pet on the shelf whose length beats its height by two
# to one. Ridged back, wedge snout held open on a row of teeth.
# ---------------------------------------------------------------------------

def build_crocodile():
    kit.reset_scene()
    root = kit.empty("root")

    hide = "#3f6b39"
    hide_dk = "#2a4a29"
    scute = "#274524"
    belly = "#c3cf92"
    tooth = "#f6f3e2"

    body_dims = (0.36, 0.52, 0.24)
    body_at = (0, -0.04, 0.4)
    body = [bk.block("body.core", body_dims, body_at, color=hide)]
    # Flank strip: the pale underside seen from the side, which is what sells
    # "reptile" more than any top detail at icon size.
    for side, sign in (("L", 1), ("R", -1)):
        body.append(bk.block("body.flank.%s" % side, (0.03, 0.46, 0.07),
                             (sign * 0.175, -0.04, 0.31), color=belly))
    # Dorsal ridge: two rows of scutes, taller at the shoulders.
    for i in range(6):
        t = i / 5.0
        y = 0.18 - t * 0.44
        h = 0.16 - 0.05 * t
        for sign in (1, -1):
            body.append(bk.wedge("body.scute%d%s" % (i, "L" if sign > 0 else "R"),
                                 (0.075, 0.085, h), (sign * 0.08, y, 0.52 + h * 0.4),
                                 color=scute, taper=0.7))
    body += bk.spots("body.warts", body_at, body_dims, count=5, size=0.045,
                     color=hide_dk, seed=7, faces=("top", "left", "right"))

    # Head: pushed well forward of the torso so the neck gap is visible.
    skull_at = (0, 0.4, 0.45)
    skull_dims = (0.3, 0.24, 0.2)
    head = [bk.block("head.skull", skull_dims, skull_at, color=hide)]
    snout_at = (0, 0.63, 0.43)
    snout_dims = (0.22, 0.26, 0.12)
    head.append(bk.block("head.snout", snout_dims, snout_at, color=hide))
    head.append(bk.block("head.jaw", (0.2, 0.26, 0.06), (0, 0.62, 0.34),
                         rot=(5, 0, 0), color=hide_dk))
    head += bk.nostrils("head.nose", snout_at, snout_dims, spacing=0.4,
                        height=0.09, size=0.03, color="#1d2a1a", face="top")
    # Teeth: alternating up/down pegs along the jaw line, both sides.
    for i in range(5):
        y = 0.53 + i * 0.055
        for sign in (1, -1):
            head.append(bk.block("head.toothU%d%s" % (i, sign), (0.028, 0.03, 0.055),
                                 (sign * 0.093, y, 0.37), color=tooth, segments=1))
            head.append(bk.block("head.toothD%d%s" % (i, sign), (0.026, 0.03, 0.045),
                                 (sign * 0.09, y - 0.028, 0.4), color=tooth,
                                 segments=1))
    # Eye turrets on TOP of the skull, the way a real croc watches the water.
    for side, sign in (("L", 1), ("R", -1)):
        head.append(bk.block("head.turret.%s" % side, (0.09, 0.1, 0.08),
                             (sign * 0.095, 0.44, 0.58), color=hide))
        head.append(bk.glow_block("head.eye.%s" % side, (0.055, 0.06, 0.02),
                                  (sign * 0.095, 0.45, 0.625), color="#d8e64a",
                                  strength=2.2))
        head.append(bk.block("head.slit.%s" % side, (0.012, 0.05, 0.026),
                             (sign * 0.095, 0.45, 0.633), color="#161a10",
                             segments=1))
    head.append(bk.block("head.brow", (0.28, 0.06, 0.05), (0, 0.35, 0.57),
                         color=scute))

    legs = bk.legs_quad("leg", front=(0.19, 0.14, 0.33), back=(0.2, -0.2, 0.33),
                        length=0.27, thickness=0.105, color=hide_dk,
                        foot_color=belly)

    tail_obj = bk.tail("tail", (0, -0.3, 0.4), length=0.32, thickness=0.21,
                       color=hide, style="taper", tip_color=hide_dk, segments=4,
                       curl=0.55)
    tail_ridge = []
    for i in range(4):
        t = (i + 0.5) / 4.0
        tail_ridge.append(bk.wedge("tail.scute%d" % i,
                                   (0.065, 0.075, 0.13 - 0.05 * t),
                                   (0, -0.3 - 0.32 * t, 0.54 + 0.16 * t * t),
                                   color=scute, taper=0.7))

    groups = {
        "body": (body, (0, 0, 0.32)),
        "head": (head, (0, 0.28, 0.42)),
        "tail": ([tail_obj] + tail_ridge, (0, -0.3, 0.4)),
    }
    for key, obj in legs.items():
        groups[key] = ([obj], tuple(obj.location))
    bk.assemble(root, groups)
    return bk.finish(root)


# ---------------------------------------------------------------------------
# Gorilla -- Legendary, $4.8K/s.
# A triangle standing on knuckles: enormous shoulders, arms to the floor, legs
# you can barely see. Silverback plate and gold cuffs carry the rarity.
# ---------------------------------------------------------------------------

def build_gorilla():
    kit.reset_scene()
    root = kit.empty("root")

    # Warm charcoal rather than the blue-black a gorilla wants in isolation:
    # on this shelf it has to sit next to bark brown and jade without going
    # grey-purple, and the silver band is what supplies the cool note.
    fur = "#453a35"
    fur_lt = "#5f524a"
    silver = "#aab3c1"
    silver_dk = "#7c8593"
    face_col = "#1f1a1c"
    gold = "#ffc93c"

    # Shoulders first: a wide slab with capped deltoids, sitting on a narrow
    # waist. The taper from 0.82 wide down to 0.44 is the entire silhouette.
    chest_dims = (0.62, 0.42, 0.3)
    chest_at = (0, 0.0, 0.64)
    body = [bk.block("body.chest", chest_dims, chest_at, color=fur)]
    # The silverback proper: a full band of pale fur capping the shoulders, so
    # it reads from every angle instead of only from above.
    body.append(bk.block("body.saddle", (0.63, 0.43, 0.17), (0, -0.01, 0.87),
                         color=silver))
    body.append(bk.block("body.saddlelip", (0.65, 0.44, 0.04), (0, -0.01, 0.775),
                         color=silver_dk))
    for side, sign in (("L", 1), ("R", -1)):
        body.append(bk.block("body.delt.%s" % side, (0.22, 0.36, 0.24),
                             (sign * 0.32, 0.0, 0.7), color=fur))
        body.append(bk.block("body.delttop.%s" % side, (0.23, 0.37, 0.14),
                             (sign * 0.32, 0.0, 0.87), color=silver))
    body.append(bk.block("body.waist", (0.44, 0.34, 0.3), (0, -0.02, 0.38),
                         color=fur))
    body.append(bk.block("body.spine", (0.22, 0.05, 0.34), (0, -0.21, 0.62),
                         color=silver_dk))
    body += bk.belly("body.pecs", chest_at, chest_dims, color=fur_lt, inset=0.7)
    # Chest emblem -- a legendary needs one thing that emits.
    body += bk.gem("body.emblem", (0, 0.24, 0.64), size=0.12, color="#7dffb0",
                   strength=2.8)

    # A gorilla's head is huge and sits FORWARD of the shoulders, not on top of
    # them; perched high it reads as a chimney.
    head_dims = (0.4, 0.36, 0.36)
    head_at = (0, 0.38, 0.98)
    head = [bk.block("head.skull", head_dims, head_at, color=fur)]
    head.append(bk.block("head.crest", (0.16, 0.3, 0.1), (0, 0.35, 1.19),
                         color=fur_lt))
    head.append(bk.block("head.neck", (0.26, 0.22, 0.16), (0, 0.2, 0.88),
                         color="#2b2422"))
    faceplane = bk.face_of(head_at, head_dims, "front")
    head.append(bk.face_plate("head.face", faceplane, (0.28, 0.24), face="front",
                              color=face_col, depth=0.028, offset=(0, -0.02)))
    head.append(bk.face_plate("head.brow", faceplane, (0.33, 0.075), face="front",
                              color="#8a7d72", depth=0.036, offset=(0, 0.12),
                              proud=bk.PROUD * 2))
    head += bk.eyes("head.eye", head_at, head_dims, spacing=0.44, height=0.025,
                    size=0.075, style="glow", iris="#ffb638")
    muzzle_at = (0, head_at[1] + 0.18, head_at[2] - 0.1)
    muzzle_dims = (0.22, 0.1, 0.13)
    head.append(bk.block("head.muzzle", muzzle_dims, muzzle_at, color=face_col))
    head += bk.nostrils("head.nose", muzzle_at, muzzle_dims, spacing=0.4,
                        height=0.025, size=0.033, color="#191115")
    head += bk.mouth("head.mouth", muzzle_at, muzzle_dims, width=0.13,
                     height=0.02, drop=-0.038, color="#191115")
    for side, sign in (("L", 1), ("R", -1)):
        head.append(bk.block("head.ear.%s" % side, (0.04, 0.09, 0.1),
                             (sign * 0.21, 0.32, 0.98), color=fur_lt))

    arm_l, arm_r = bk.arms("arm", (0.34, 0.11, 0.78), length=0.7, thickness=0.17,
                           color="#332b27", hand_color=face_col, angle=7)
    cuffs = {}
    for side, sign in (("L", 1), ("R", -1)):
        cuffs[side] = bk.block("arm.%s.cuff" % side, (0.21, 0.21, 0.065),
                               (sign * 0.425, 0.11, 0.2), color=gold)

    legs = bk.legs_pair("leg", (0.17, -0.06, 0.32), length=0.24, thickness=0.155,
                        color="#332b27", foot_color=fur_lt, foot_length=0.24)

    groups = {
        "body": (body, (0, 0, 0.34)),
        "head": (head, (0, 0.26, 0.84)),
        "arm.L": ([arm_l, cuffs["L"]], tuple(arm_l.location)),
        "arm.R": ([arm_r, cuffs["R"]], tuple(arm_r.location)),
    }
    for key, obj in legs.items():
        groups[key] = ([obj], tuple(obj.location))
    bk.assemble(root, groups)
    return bk.finish(root)


# ---------------------------------------------------------------------------
# Pineape -- Legendary, $5.5K/s. ORIGINAL.
# A small ape wearing a pineapple: rind shell over the torso, a rind helmet with
# the face looking out of it, and a leaf crown that sways on the ear channels.
# ---------------------------------------------------------------------------

def build_pineape():
    kit.reset_scene()
    root = kit.empty("root")

    fur = "#6b4a2e"
    fur_lt = "#8f6740"
    skin = "#d8a874"
    rind = "#f2b43a"
    rind_dk = "#c47c1c"
    leaf = "#3fa34a"
    leaf_lt = "#68c95a"
    glow = "#c6ff4d"

    # Ape underneath, mostly hidden -- but the limbs have to read as fur.
    body = [bk.block("body.torso", (0.28, 0.24, 0.32), (0, 0.0, 0.44), color=fur)]

    shell_dims = (0.44, 0.4, 0.46)
    shell_at = (0, -0.02, 0.48)
    body.append(bk.block("body.shell", shell_dims, shell_at, color=rind))
    body += _diamonds("body.rind.L", shell_at, shell_dims, "left", 3, 3, 0.085,
                      rind_dk)
    body += _diamonds("body.rind.R", shell_at, shell_dims, "right", 3, 3, 0.085,
                      rind_dk)
    body += _diamonds("body.rind.B", shell_at, shell_dims, "back", 3, 3, 0.085,
                      rind_dk)
    body += _diamonds("body.rind.F", shell_at, shell_dims, "front", 3, 2, 0.075,
                      rind_dk, inset=0.86)
    # Shell rim and the gem set into the chest.
    body.append(bk.block("body.rim", (0.47, 0.43, 0.045), (0, -0.02, 0.7),
                         color=rind_dk))
    body += bk.gem("body.core", (0, 0.22, 0.5), size=0.12, color=glow, strength=3.0)

    head_dims = (0.25, 0.23, 0.25)
    head_at = (0, 0.15, 0.85)
    head = [bk.block("head.skull", head_dims, head_at, color=fur)]
    faceplane = bk.face_of(head_at, head_dims, "front")
    head.append(bk.face_plate("head.face", faceplane, (0.19, 0.16), face="front",
                              color=skin, depth=0.026, offset=(0, -0.02)))
    head += bk.eyes("head.eye", head_at, head_dims, spacing=0.46, height=0.03,
                    size=0.05, style="white", iris="#2a1c12", pupil_scale=0.6)
    head.append(bk.block("head.muzzle", (0.12, 0.08, 0.07),
                         (0, head_at[1] + 0.14, head_at[2] - 0.07), color=skin))
    head += bk.mouth("head.mouth", (0, head_at[1] + 0.14, head_at[2] - 0.07),
                     (0.12, 0.08, 0.07), width=0.08, height=0.016, drop=-0.014,
                     color="#3b2820", style="grin")
    # Helmet: a rind cap that overhangs the brow, plus cheek guards.
    helm_dims = (0.34, 0.32, 0.16)
    helm_at = (0, 0.12, 1.03)
    head.append(bk.block("head.helm", helm_dims, helm_at, color=rind))
    head += _diamonds("head.helm.L", helm_at, helm_dims, "left", 3, 2, 0.07, rind_dk)
    head += _diamonds("head.helm.R", helm_at, helm_dims, "right", 3, 2, 0.07, rind_dk)
    head += _diamonds("head.helm.F", helm_at, helm_dims, "front", 3, 2, 0.07, rind_dk)
    head.append(bk.block("head.visor", (0.36, 0.06, 0.05), (0, 0.28, 0.96),
                         color=rind_dk))
    for side, sign in (("L", 1), ("R", -1)):
        head.append(bk.block("head.guard.%s" % side, (0.05, 0.26, 0.16),
                             (sign * 0.155, 0.13, 0.88), color=rind))

    # Leaf crown on the ear channels so it sways when the pet moves.
    crown = {}
    for side, sign in (("L", 1), ("R", -1)):
        parts = []
        for i, (lean, length, back) in enumerate(((18, 0.4, 0.02),
                                                  (48, 0.31, -0.1),
                                                  (33, 0.35, 0.15))):
            tip_z = 1.13 + length * 0.46
            parts.append(bk.wedge(
                "ear.%s.leaf%d" % (side, i), (0.08, 0.055, length),
                (sign * (0.05 + 0.02 * i), 0.09 + back, tip_z),
                rot=(0, -sign * lean, 0), color=leaf if i % 2 else leaf_lt,
                taper=0.85,
            ))
        # The spark sits ON the tallest leaf's tip, not floating beside it.
        parts.append(bk.glow_block(
            "ear.%s.spark" % side, (0.045, 0.045, 0.045),
            (sign * 0.115, 0.11, 1.31), color=glow, strength=2.6))
        crown["ear.%s" % side] = (parts, (sign * 0.05, 0.1, 1.11))
    # One centre leaf stays with the head so the crown never looks split.
    head.append(bk.wedge("head.leaf", (0.075, 0.055, 0.34), (0, 0.06, 1.3),
                         rot=(-6, 0, 0), color=leaf, taper=0.85))

    arm_l, arm_r = bk.arms("arm", (0.26, 0.06, 0.6), length=0.34, thickness=0.1,
                           color=fur, hand_color=fur_lt, angle=17)
    legs = bk.legs_pair("leg", (0.11, 0.0, 0.3), length=0.27, thickness=0.11,
                        color=fur, foot_color=fur_lt, foot_length=0.19)

    groups = {
        "body": (body, (0, 0, 0.28)),
        "head": (head, (0, 0.08, 0.72)),
        "arm.L": ([arm_l], tuple(arm_l.location)),
        "arm.R": ([arm_r], tuple(arm_r.location)),
    }
    groups.update(crown)
    for key, obj in legs.items():
        groups[key] = ([obj], tuple(obj.location))
    bk.assemble(root, groups)
    return bk.finish(root)


# ---------------------------------------------------------------------------
# Spider -- Mythic, $22K/s.
# Eight legs, arched high above a glossy black body, red hourglass burning on
# the abdomen. The four animation channels each drive a pair of legs.
# ---------------------------------------------------------------------------

def build_spider():
    kit.reset_scene()
    root = kit.empty("root")

    chitin = "#15121b"
    chitin_lt = "#2b2536"
    red = "#e0243a"

    abdomen_at = (0, -0.36, 0.7)
    abdomen_dims = (0.56, 0.54, 0.48)
    body = [bk.block("body.abdomen", abdomen_dims, abdomen_at, color=chitin)]
    body.append(bk.block("body.waist", (0.18, 0.17, 0.16), (0, -0.06, 0.64),
                         color=chitin_lt))
    # Hourglass: three emissive plates, wide-narrow-wide, on the back.
    for i, (w, h, dz) in enumerate(((0.22, 0.08, 0.11), (0.08, 0.07, 0.0),
                                    (0.2, 0.08, -0.11))):
        body.append(bk.glow_block("body.mark%d" % i, (w, 0.02, h),
                                  (0, abdomen_at[1] - abdomen_dims[1] * 0.5 - 0.01,
                                   abdomen_at[2] + dz),
                                  color=red, strength=2.4))
    for i, (w, d, dy) in enumerate(((0.22, 0.08, 0.11), (0.08, 0.07, 0.0),
                                    (0.2, 0.08, -0.11))):
        body.append(bk.glow_block("body.markT%d" % i, (w, d, 0.02),
                                  (0, abdomen_at[1] + dy,
                                   abdomen_at[2] + abdomen_dims[2] * 0.5 + 0.01),
                                  color=red, strength=2.0))
    body += bk.spots("body.sheen", abdomen_at, abdomen_dims, count=4, size=0.06,
                     color=chitin_lt, seed=4, faces=("left", "right", "top"))

    # Cephalothorax doubles as the head so it can tilt and lunge.
    ceph_at = (0, 0.13, 0.62)
    ceph_dims = (0.38, 0.36, 0.28)
    head = [bk.block("head.ceph", ceph_dims, ceph_at, color=chitin)]
    head.append(bk.block("head.carapace", (0.34, 0.3, 0.05), (0, 0.13, 0.78),
                         color=chitin_lt))
    # Eight eyes: a row of four big ones with four small ones above.
    faceplane = bk.face_of(ceph_at, ceph_dims, "front")
    for i, dx in enumerate((-0.09, -0.03, 0.03, 0.09)):
        size = 0.055 if abs(dx) < 0.06 else 0.042
        head.append(bk.face_plate(
            "head.eye%d" % i, faceplane, (size, size), face="front",
            material=kit.mat("spider.eye", kit.hexcol(red), rough=0.15,
                             emission=kit.hexcol(red), emission_strength=3.4),
            depth=0.02, offset=(dx, -0.01), proud=bk.PROUD * 3))
    for i, dx in enumerate((-0.1, -0.035, 0.035, 0.1)):
        head.append(bk.face_plate(
            "head.eyeT%d" % i, faceplane, (0.03, 0.03), face="front",
            material=kit.mat("spider.eye", kit.hexcol(red), rough=0.15,
                             emission=kit.hexcol(red), emission_strength=3.4),
            depth=0.018, offset=(dx, 0.055), proud=bk.PROUD * 3))
    # Fangs and pedipalps hanging under the front of the carapace.
    for side, sign in (("L", 1), ("R", -1)):
        head.append(bk.wedge("head.fang.%s" % side, (0.05, 0.055, 0.16),
                             (sign * 0.07, 0.29, 0.46), rot=(18, 0, 0),
                             color=chitin_lt, taper=0.8))
        head.append(_strut("head.palp.%s" % side, (sign * 0.16, 0.26, 0.58),
                           (sign * 0.24, 0.4, 0.4), 0.055, chitin))

    # Eight legs: knee arched well above the body, foot planted on the floor.
    # Two legs share each animation channel, front pair and back pair per side.
    leg_specs = (
        ("leg.FL", 1, ((0.18, 0.2, 0.62, 54), (0.19, 0.06, 0.62, 22))),
        ("leg.FR", -1, ((0.18, 0.2, 0.62, 54), (0.19, 0.06, 0.62, 22))),
        ("leg.BL", 1, ((0.19, -0.11, 0.62, -18), (0.18, -0.26, 0.62, -50))),
        ("leg.BR", -1, ((0.19, -0.11, 0.62, -18), (0.18, -0.26, 0.62, -50))),
    )
    legs = {}
    for name, sign, spec in leg_specs:
        parts = []
        pivot = None
        for i, (hx, hy, hz, theta) in enumerate(spec):
            rad = math.radians(theta)
            hip = (sign * hx, hy, hz)
            if pivot is None:
                pivot = hip
            reach = 0.54 if hy > 0 else 0.46
            knee = (hip[0] + sign * math.cos(rad) * reach * 0.58,
                    hip[1] + math.sin(rad) * reach * 0.58,
                    0.94 if hy > 0 else 0.88)
            foot = (hip[0] + sign * math.cos(rad) * reach,
                    hip[1] + math.sin(rad) * reach, 0.03)
            parts.append(_strut("%s.femur%d" % (name, i), hip, knee, 0.068, chitin))
            parts.append(_strut("%s.tibia%d" % (name, i), knee, foot, 0.055,
                                chitin, taper=0.5))
            parts.append(bk.block("%s.joint%d" % (name, i),
                                  (0.075, 0.075, 0.06), knee, color=chitin_lt,
                                  segments=1))
        legs[name] = (parts, pivot)

    groups = {
        "body": (body, (0, -0.14, 0.62)),
        "head": (head, (0, -0.04, 0.61)),
    }
    groups.update(legs)
    bk.assemble(root, groups)
    return bk.finish(root)


# ---------------------------------------------------------------------------
# Tiger -- Mythic, $28K/s.
# Heavy quadruped, orange over a white belly, black bars everywhere including
# the face and tail. Amber eyes and a spine of ember stripes carry the tier.
# ---------------------------------------------------------------------------

def build_tiger():
    kit.reset_scene()
    root = kit.empty("root")

    coat = "#ee8226"
    coat_dk = "#c65f13"
    cream = "#fdf3e2"
    ink = "#1a1418"
    amber = "#ffc23c"

    body_dims = (0.42, 0.68, 0.42)
    body_at = (0, -0.06, 0.56)
    body = [bk.block("body.core", body_dims, body_at, color=coat)]
    body.append(bk.block("body.shoulder", (0.46, 0.24, 0.42), (0, 0.16, 0.58),
                         color=coat))
    body += bk.belly("body.chest", body_at, body_dims, color=cream, inset=0.68)
    body += bk.stripes("body.bar", body_at, body_dims, count=8, width=0.028,
                       color=ink, axis="y")
    body += bk.stripes("body.bar2", (0, 0.16, 0.58), (0.46, 0.24, 0.42), count=2,
                       width=0.03, color=ink, axis="y")
    # Ember stripes: three low-strength emissive bars along the spine. Mythic
    # pets have to look charged without stopping being a tiger.
    body.append(bk.glow_block("body.ember", (0.045, 0.56, 0.018),
                              (0, -0.06, 0.775), color=amber, strength=1.5))

    head_dims = (0.36, 0.3, 0.33)
    head_at = (0, 0.48, 0.82)
    head = [bk.block("head.skull", head_dims, head_at, color=coat)]
    # Cheek ruff: two flared slabs that widen the head into a proper cat mask.
    for side, sign in (("L", 1), ("R", -1)):
        head.append(bk.block("head.ruff.%s" % side, (0.06, 0.17, 0.22),
                             (sign * 0.205, 0.44, 0.76), rot=(0, -sign * 14, 0),
                             color=cream))
        for i in range(2):
            head.append(bk.block("head.ruffbar%d.%s" % (i, side),
                                 (0.05, 0.035, 0.19),
                                 (sign * 0.215, 0.4 + i * 0.075, 0.76),
                                 color=ink, segments=1))
    faceplane = bk.face_of(head_at, head_dims, "front")
    head.append(bk.face_plate("head.mask", faceplane, (0.24, 0.13), face="front",
                              color=cream, depth=0.024, offset=(0, -0.06)))
    head += bk.eyes("head.eye", head_at, head_dims, spacing=0.5, height=0.06,
                    size=0.062, style="glow", iris=amber)
    head += bk.snout("head.snout", head_at, head_dims, width=0.16, length=0.11,
                     height=0.1, color=cream, drop=-0.09, nose_color="#e07a86")
    head += bk.mouth("head.mouth", (0, head_at[1] + 0.2, head_at[2] - 0.09),
                     (0.16, 0.11, 0.1), width=0.09, height=0.02, drop=-0.04,
                     color="#2a1a1e")
    for side, sign in (("L", 1), ("R", -1)):
        head.append(bk.wedge("head.fang.%s" % side, (0.03, 0.035, 0.07),
                             (sign * 0.045, head_at[1] + 0.22, head_at[2] - 0.155),
                             rot=(180, 0, 0), color=cream, taper=0.7))
        # Forehead bars -- the tiger's signature marking.
        for i in range(2):
            head.append(bk.face_plate(
                "head.bar%d.%s" % (i, side), faceplane, (0.035, 0.08),
                face="front", color=ink, depth=0.02,
                offset=(sign * (0.045 + i * 0.06), 0.13), proud=bk.PROUD * 2))
    ear_l, ear_r = bk.ears_box("ear", head_at, head_dims, size=0.095,
                               spacing=0.6, depth=0.055, color=coat_dk,
                               inner_color=cream)

    legs = bk.legs_quad("leg", front=(0.15, 0.2, 0.36), back=(0.16, -0.26, 0.36),
                        length=0.34, thickness=0.125, color=coat,
                        foot_color=cream)

    tail_obj = bk.tail("tail", (0, -0.38, 0.6), length=0.44, thickness=0.11,
                       color=coat, style="taper", tip_color=ink, segments=5,
                       curl=0.55)
    tail_bars = []
    for i in range(4):
        t = (i + 0.6) / 5.0
        tail_bars.append(bk.block("tail.bar%d" % i, (0.115, 0.04, 0.115),
                                  (0, -0.38 - 0.44 * t, 0.6 + 0.44 * 0.55 * t * t),
                                  color=ink, segments=1))

    groups = {
        "body": (body, (0, 0, 0.34)),
        "head": (head, (0, 0.34, 0.68)),
        "ear.L": ([ear_l], tuple(ear_l.location)),
        "ear.R": ([ear_r], tuple(ear_r.location)),
        "tail": ([tail_obj] + tail_bars, (0, -0.38, 0.6)),
    }
    for key, obj in legs.items():
        groups[key] = ([obj], tuple(obj.location))
    bk.assemble(root, groups)
    return bk.finish(root)


# ---------------------------------------------------------------------------
# King Snake -- Secret, $3.5M/s.
# The showpiece. An emerald constrictor sitting on a wide coil with the front
# third reared up, gold scutes climbing the throat, a crown ridge and a halo.
# The coil is deliberately low and wide: the rear-up is the silhouette, and a
# tall coil eats the height the neck needs to read.
# ---------------------------------------------------------------------------

def build_king_snake():
    kit.reset_scene()
    root = kit.empty("root")

    jade = "#2f9c52"
    jade_dk = "#176437"
    jade_lt = "#59c979"
    gold = "#ffcc3d"
    gold_dk = "#c08c15"
    ember = "#d7ff5c"

    # --- the coil ---------------------------------------------------------
    # A wide, low base of three stacked rings, each a closed loop of tangential
    # boxes. A continuous spiral reads as a heap at icon size; discrete rings
    # read as coils, and keeping the stack short leaves room for the rear-up,
    # which is what actually says "constrictor" in an outline.
    rings = ((0.45, 0.14, 10, 0.28), (0.36, 0.32, 9, 0.25), (0.27, 0.48, 8, 0.22))
    body = []
    ring_pts = []
    for r_i, (radius, z, count, thick) in enumerate(rings):
        pts = []
        for i in range(count + 1):
            angle = (i / float(count)) * 2.0 * math.pi + r_i * 0.45
            pts.append((math.cos(angle) * radius, math.sin(angle) * radius, z))
        ring_pts.append(pts)
        for i in range(count):
            body.append(_strut("body.r%dc%d" % (r_i, i), pts[i], pts[i + 1],
                               thick, jade if r_i % 2 == 0 else jade_dk))
            # Gold scutes ride the outside of the two pale rings only; on every
            # ring the gold stops reading as regalia and starts reading as loot.
            mid = tuple((pts[i][k] + pts[i + 1][k]) * 0.5 for k in range(3))
            if r_i == 0 and i % 2 == 0:
                body.append(_plate_facing(
                    "body.scute%d_%d" % (r_i, i), mid, (mid[0], mid[1], 0.0),
                    (thick * 0.5, thick * 0.62), 0.045, gold,
                    stand=thick * 0.46))
            elif r_i % 2 == 1 and i % 2 == 1:
                body.append(_plate_facing(
                    "body.band%d_%d" % (r_i, i), mid, (mid[0], mid[1], 0.0),
                    (thick * 0.34, thick * 0.86), 0.035, jade_lt,
                    stand=thick * 0.46))

    # --- neck: the coil leaves the stack and rears up and forward ---------
    neck_pts = [(0.0, 0.24, 0.5), (0.0, 0.08, 0.7), (0.0, 0.04, 0.9),
                (0.0, 0.13, 1.06), (0.0, 0.24, 1.15)]
    for i in range(len(neck_pts) - 1):
        body.append(_strut("body.neck%d" % i, neck_pts[i], neck_pts[i + 1],
                           0.245 - 0.018 * i, jade if i % 2 else jade_dk))
    # Gold throat scutes climbing the front of the neck.
    for i, (y, z) in enumerate(((0.18, 0.63), (0.15, 0.8), (0.16, 0.96),
                                (0.25, 1.1))):
        body.append(bk.block("body.throat%d" % i, (0.16, 0.06, 0.11),
                             (0, y, z), rot=(14 * i, 0, 0), color=gold,
                             segments=1))
    body += bk.gem("body.heart", (0, 0.19, 0.88), size=0.11, color=ember,
                   strength=2.8)

    # --- head -------------------------------------------------------------
    skull_at = (0, 0.38, 1.26)
    skull_dims = (0.52, 0.42, 0.33)
    head = [bk.block("head.skull", skull_dims, skull_at, color=jade)]
    head.append(bk.block("head.snout", (0.38, 0.28, 0.25), (0, 0.69, 1.24),
                         color=jade))
    head.append(bk.wedge("head.tip", (0.31, 0.23, 0.19), (0, 0.86, 1.23),
                         rot=(-90, 0, 0), color=jade_lt, taper=0.5))
    head.append(bk.block("head.jaw", (0.37, 0.46, 0.09), (0, 0.62, 1.07),
                         color=jade_dk))
    head.append(bk.block("head.chin", (0.29, 0.37, 0.065), (0, 0.6, 1.03),
                         color=gold_dk, segments=1))
    # Hood: gold-rimmed mantle plates flaring off the neck under the jaw. Not
    # constrictor anatomy -- regalia, and it is what makes the rear-up read as
    # a king rather than a green pipe.
    for side, sign in (("L", 1), ("R", -1)):
        head.append(bk.block("head.hood.%s" % side, (0.12, 0.28, 0.34),
                             (sign * 0.28, 0.2, 1.08), rot=(0, -sign * 26, 0),
                             color=jade_dk))
        head.append(bk.block("head.hoodrim.%s" % side, (0.05, 0.3, 0.07),
                             (sign * 0.35, 0.2, 1.22), rot=(0, -sign * 26, 0),
                             color=gold, segments=1))
    # Forked tongue.
    for sign in (1, -1):
        head.append(bk.block("head.tongue%d" % sign, (0.026, 0.21, 0.024),
                             (sign * 0.04, 0.99, 1.09), rot=(0, 0, sign * 9),
                             color="#e0338f", segments=1))
    # Eyes: glowing slits set into gold sockets on the upper sides of the skull.
    for side, sign in (("L", 1), ("R", -1)):
        head.append(bk.block("head.socket.%s" % side, (0.08, 0.19, 0.15),
                             (sign * 0.25, 0.46, 1.33), color=gold_dk))
        head.append(bk.glow_block("head.eye.%s" % side, (0.055, 0.155, 0.11),
                                  (sign * 0.288, 0.46, 1.33), color=ember,
                                  strength=3.4))
        head.append(bk.block("head.slit.%s" % side, (0.032, 0.03, 0.085),
                             (sign * 0.316, 0.46, 1.33), color="#10240f",
                             segments=1))
    # Crown ridge down the centre of the skull.
    for i in range(4):
        t = i / 3.0
        head.append(bk.wedge("head.crown%d" % i, (0.085, 0.095, 0.2 - 0.06 * t),
                             (0, 0.2 + t * 0.32, 1.46 - 0.02 * t),
                             rot=(18 - 26 * t, 0, 0), color=gold, taper=0.75))
    head.append(bk.block("head.browplate", (0.5, 0.11, 0.07), (0, 0.47, 1.43),
                         color=gold))
    # Halo: the one floating element on the shelf, so "secret" reads instantly.
    head += bk.ring("head.halo", (0, 0.32, 1.62), radius=0.29, thickness=0.034,
                    tilt=0.0, color=gold, strength=2.8)

    # Crown horns on the ear channels so the regalia sways with the head.
    crown = {}
    for side, sign in (("L", 1), ("R", -1)):
        parts = [
            bk.wedge("ear.%s.horn" % side, (0.1, 0.1, 0.4),
                     (sign * 0.31, 0.26, 1.52), rot=(-14, -sign * 28, 0),
                     color=gold, taper=0.8),
            bk.wedge("ear.%s.spur" % side, (0.08, 0.08, 0.22),
                     (sign * 0.42, 0.13, 1.42), rot=(6, -sign * 64, 0),
                     color=gold_dk, taper=0.8),
        ]
        parts += bk.gem("ear.%s.jewel" % side, (sign * 0.42, 0.3, 1.67),
                        size=0.095, color=ember, strength=3.0)
        crown["ear.%s" % side] = (parts, (sign * 0.22, 0.28, 1.36))

    # --- tail: the loose end of the coil, lifted clear of the stack --------
    tail_root = ring_pts[0][0]
    tail_pts = [tail_root, (0.56, -0.28, 0.24), (0.46, -0.54, 0.44),
                (0.26, -0.62, 0.66)]
    tail_parts = []
    for i in range(len(tail_pts) - 1):
        tail_parts.append(_strut("tail.seg%d" % i, tail_pts[i], tail_pts[i + 1],
                                 0.25 - 0.055 * i, jade if i % 2 else jade_dk,
                                 taper=0.3 if i == 2 else 0.0))
    tail_parts.append(bk.wedge("tail.tip", (0.1, 0.1, 0.21), (0.2, -0.62, 0.8),
                               rot=(-22, 0, 0), color=gold, taper=0.85))

    groups = {
        "body": (body, (0, 0, 0.2)),
        "head": (head, (0, 0.22, 1.13)),
        "tail": (tail_parts, tail_root),
    }
    groups.update(crown)
    bk.assemble(root, groups)
    return bk.finish(root)

PETS = {
    "chimpanzee": build_chimpanzee,
    "toucan": build_toucan,
    "crocodile": build_crocodile,
    "gorilla": build_gorilla,
    "pineape": build_pineape,
    "spider": build_spider,
    "tiger": build_tiger,
    "king-snake": build_king_snake,
}
