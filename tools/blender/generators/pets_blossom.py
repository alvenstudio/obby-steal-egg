"""
Cherry Blossom Terrace -- eight pets, epic through eternal.

The biome's palette is deliberately narrow: sakura pink, cream white, lacquer
red, deep charcoal and gold leaf. That restraint is the point -- the terrace is
meant to read as a lacquered garden shrine, not a candy shop, so colour does
the work of *placement* (a single red crown patch, one gold torc) rather than
of quantity.

Conventions inherited from pets_forest, and non-negotiable:

  * Build facing +Y. Feet near z = 0; `finish()` normalises the height.
  * Only the runtime's part names appear at the top level of `assemble`:
    body, head, ear.L/.R, wing.L/.R, arm.L/.R, leg.FL/.FR/.BL/.BR, tail,
    fin.L/.R, fin.tail. Everything else is welded into one of those.
  * Pivots are joints, not centroids. Head pivots at the neck, ears at the
    skull, tails at the rump.
  * Silhouette first. Each of these has one shape that carries it at icon
    size: the crane's stilt legs, the red panda's ringed tail, the stag's
    antler spread, the kitsune's nine-tail fan.

One proportion rule that bites hard here: `finish()` normalises HEIGHT, so a
creature that is long and flat gets scaled up until it dwarfs everything on the
shelf. The salamander is therefore built with an arched back and a raised head
-- still by far the longest pet in the biome, but roughly twice its height
rather than four times it.

Rarity is expressed as *charge*, not as clutter: the epic crane is pure paint,
the cosmic pets gain emissive eyes and a halo, and the divine kitsune gets
floating flame. Gold leaf is the shared "expensive" accent across the top four.
"""

import math

import blockkit as bk
import kit

# The terrace palette. Every pet below draws from these; a colour that is not
# a near neighbour of one of them does not belong in this biome.
CREAM = "#fbf5ea"
SNOW = "#ffffff"
PETAL = "#f6a8c0"
PETAL_LIGHT = "#ffd9e6"
PETAL_DEEP = "#e0708f"
LACQUER = "#c4302b"
LACQUER_DEEP = "#8e1f1c"
CHARCOAL = "#2a2328"
CHARCOAL_SOFT = "#453b44"
GOLD = "#e6bf62"
GOLD_BRIGHT = "#f7dd94"


def _blossom(name, at, size=0.11, color=PETAL, core=GOLD_BRIGHT):
    """
    A four-petal cherry blossom, built as a tiny pinwheel of slabs.

    Cheap -- five thin slabs -- but instantly readable as a flower because the
    petals are offset around a contrasting centre. Used to hang flowers on the
    stag's antlers and to trim the mythic-and-up pets.
    """
    parts = []
    for i in range(4):
        angle = i * 90.0
        dx = math.sin(math.radians(angle)) * size * 0.42
        dy = math.cos(math.radians(angle)) * size * 0.42
        parts.append(bk.slab(
            "%s.p%d" % (name, i), (size * 0.66, size * 0.66, size * 0.22),
            (at[0] + dx, at[1] + dy, at[2]), rot=(0, 0, angle), color=color,
        ))
    parts.append(bk.slab(name + ".core", (size * 0.28, size * 0.28, size * 0.32),
                         at, color=core))
    return parts


# ---------------------------------------------------------------------------
# Crane -- Epic, $4K/s.
# Everything about this bird is length: stilt legs, a four-block neck, and a
# body no bigger than its own head. The only colour is the red crown patch and
# the black shawl of folded secondaries, which is exactly how a real
# red-crowned crane is marked -- and at icon size those two dark/bright hits
# are the difference between "crane" and "white stick".
# ---------------------------------------------------------------------------

def build_crane():
    kit.reset_scene()
    root = kit.empty("root")

    plume = CREAM
    ink = CHARCOAL
    crown = LACQUER
    shank = "#3b3138"

    # Torso is small and carried high; the legs are more than half the height.
    body_dims = (0.33, 0.48, 0.33)
    body_at = (0, -0.05, 0.84)
    body = [bk.block("body.core", body_dims, body_at, color=plume)]
    body += bk.belly("body.breast", body_at, body_dims, color=SNOW, inset=0.62)
    # The black shawl -- big and squared off, because it is the only dark mass
    # on an otherwise white bird and it has to survive being 24px tall.
    body.append(bk.block("body.shawl", (0.36, 0.28, 0.26),
                         (0, -0.19, 0.94), color=ink))
    body.append(bk.block("body.shawl.lip", (0.38, 0.06, 0.1),
                         (0, -0.06, 0.96), color="#575059"))

    # Neck: four blocks stepping up and forward, thinning as they rise. Kept in
    # the body group so the head pivot lands cleanly on top of the last one.
    for i in range(5):
        t = i / 4.0
        w = 0.155 - 0.04 * t
        body.append(bk.block("body.neck%d" % i, (w, w, 0.155),
                             (0, 0.05 + 0.09 * t, 1.05 + i * 0.145),
                             rot=(-9, 0, 0), color=plume))
    # Black nape stripe running up the back of the neck.
    body.append(bk.block("body.nape", (0.08, 0.045, 0.56),
                         (0, 0.0, 1.22), rot=(-9, 0, 0), color=ink))

    head_dims = (0.2, 0.23, 0.21)
    head_at = (0, 0.34, 1.78)
    head = [bk.block("head.skull", head_dims, head_at, color=plume)]
    # The signature: a scarlet cap on the crown, nothing else red on the bird.
    head.append(bk.block("head.crown", (0.16, 0.18, 0.06), (0, 0.34, 1.9),
                         color=crown))
    # Black cheek strap under the eye, the way the real bird is marked.
    for side, sign in (("L", 1), ("R", -1)):
        facing = "left" if sign > 0 else "right"
        head.append(bk.face_plate(
            "head.cheek.%s" % side, bk.face_of(head_at, head_dims, facing),
            (0.18, 0.075), face=facing, color=ink, depth=0.02,
            offset=(-0.025, -0.05)))
    head += bk.eyes("head.eye", head_at, head_dims, spacing=0.64, height=0.035,
                    size=0.058, style="dot", iris="#1b161b")
    # A long dagger beak; length here is what stops the head reading as a cube.
    head += bk.beak("head.beak", head_at, head_dims, width=0.065, length=0.3,
                    height=0.065, color="#3f3730", drop=-0.015, taper=0.6)

    # Wings folded along the flanks, black at the trailing tip.
    wing_l, wing_r = bk.wings_flat("wing", (0.15, -0.05, 0.9), span=0.14,
                                   height=0.38, thickness=0.07, color=plume,
                                   tip_color=ink, layers=3, tilt=5)

    # The bustle: three drooping black plumes over the rump, not a real tail.
    tail_parts = [bk.block("tail.core", (0.2, 0.22, 0.16), (0, -0.32, 0.82),
                           color=plume)]
    for i, (dx, drop) in enumerate(((-0.09, -0.02), (0.0, 0.0), (0.09, -0.02))):
        tail_parts.append(bk.wedge(
            "tail.plume%d" % i, (0.095, 0.095, 0.32),
            (dx, -0.44, 0.72 + drop), rot=(-104, 0, 0), color=ink, taper=0.55))

    # Stilt legs. A 0.6 shin against a 1.8-tall bird is the whole silhouette.
    legs = bk.bird_feet("leg", (0.085, 0.0, 0.7), shin=0.6, thickness=0.06,
                        toe=0.19, color=shank)

    groups = {
        "body": (body, (0, 0, 0.68)),
        "head": (head, (0, 0.24, 1.68)),
        "wing.L": ([wing_l], tuple(wing_l.location)),
        "wing.R": ([wing_r], tuple(wing_r.location)),
        "tail": (tail_parts, (0, -0.28, 0.84)),
    }
    for key, obj in legs.items():
        groups[key] = ([obj], tuple(obj.location))
    bk.assemble(root, groups)
    return bk.finish(root)


# ---------------------------------------------------------------------------
# Salamander -- Legendary, $74K/s.
# Long body, low stance -- but with an arched back and a lifted head, so height
# normalisation does not blow it up into a bus. The legs are stubs set on wide
# hips; the head is broader than the torso, which is what separates "amphibian"
# from "lizard". Legendary charge is a row of ember spots burning down the
# spine, echoed by two cheek marks and glowing eyes.
# ---------------------------------------------------------------------------

def build_salamander():
    kit.reset_scene()
    root = kit.empty("root")

    skin = LACQUER
    skin_deep = LACQUER_DEEP
    under = "#f6e6cf"
    ember = "#ffb347"

    # Torso: a long block with a raised ribcage arch over the shoulders.
    body_dims = (0.26, 0.4, 0.24)
    body_at = (0, -0.04, 0.38)
    body = [bk.block("body.core", body_dims, body_at, color=skin)]
    body.append(bk.block("body.ribs", (0.31, 0.24, 0.26), (0, 0.08, 0.39),
                         color=skin))
    body.append(bk.block("body.hips", (0.3, 0.2, 0.26), (0, -0.22, 0.38),
                         color=skin))
    # The neck is deliberately NARROWER than both the ribs and the skull. That
    # pinch is the only thing stopping a long low animal from reading as one
    # continuous red log.
    body.append(bk.block("body.neck", (0.16, 0.14, 0.17), (0, 0.27, 0.46),
                         color=skin))
    # Fire-salamander blotching: irregular cream patches scattered over the
    # back and flanks, not the tidy roof-rack row a straight line would give.
    for i, (x, y, z, w, d) in enumerate((
        (0.085, 0.13, 0.523, 0.1, 0.12),
        (-0.09, 0.0, 0.512, 0.11, 0.13),
        (0.095, -0.15, 0.518, 0.1, 0.12),
        (-0.08, -0.29, 0.512, 0.09, 0.1),
    )):
        body.append(bk.slab("body.blotch%d" % i, (w, d, 0.03), (x, y, z),
                            color=under))
    for side, sign in (("L", 1), ("R", -1)):
        body.append(bk.slab("body.flankdot.%s" % side, (0.03, 0.13, 0.11),
                            (sign * 0.162, 0.09, 0.4), color=under))
        body.append(bk.slab("body.flankdot2.%s" % side, (0.03, 0.11, 0.1),
                            (sign * 0.157, -0.24, 0.39), color=under))
    # Three embers down the spine. Deliberately NOT paired with cream patches
    # on the same face -- blotches and embers competing along one ridge turned
    # the back into a luggage rack.
    for i, (x, y) in enumerate(((0.0, 0.08), (0.07, -0.1), (-0.07, -0.26))):
        body.append(bk.glow_block("body.ember%d" % i, (0.085, 0.085, 0.03),
                                  (x, y, 0.512), color=ember, strength=3.6))

    # Wide flat skull, deliberately broader than the torso AND far broader than
    # the neck it sits on -- an amphibian's head, not a lizard's snout.
    head_dims = (0.34, 0.26, 0.19)
    head_at = (0, 0.48, 0.55)
    head = [bk.block("head.skull", head_dims, head_at, color=skin)]
    head.append(bk.block("head.jaw", (0.29, 0.25, 0.07), (0, 0.48, 0.452),
                         color=under))
    # Bulging eyes sitting proud on TOP of the skull, not on its face -- the
    # single cue that separates a salamander head from a generic snout.
    for side, sign in (("L", 1), ("R", -1)):
        head.append(bk.block("head.bulge.%s" % side, (0.11, 0.11, 0.09),
                             (sign * 0.115, 0.52, 0.685), color=skin))
        head.append(bk.glow_block("head.eye.%s" % side, (0.072, 0.072, 0.034),
                                  (sign * 0.115, 0.52, 0.742), color="#ffcf5c",
                                  strength=3.6))
    head += bk.mouth("head.mouth", head_at, head_dims, width=0.22, height=0.026,
                     drop=-0.055, color="#5c1815")
    head += bk.nostrils("head.nose", head_at, head_dims, spacing=0.34,
                        height=0.04, size=0.03, color="#5c1815")
    # Two cream cheek blotches carry the body's marking onto the skull.
    for side, sign in (("L", 1), ("R", -1)):
        head.append(bk.slab("head.mark.%s" % side, (0.075, 0.14, 0.036),
                            (sign * 0.14, 0.43, 0.645), color=under))

    # Splayed stubby legs -- wide hips, short shafts, big flat feet.
    legs = bk.legs_quad("leg", front=(0.18, 0.16, 0.32), back=(0.19, -0.2, 0.32),
                        length=0.26, thickness=0.085, color=skin_deep,
                        foot_color=under)
    tail_obj = bk.tail("tail", (0, -0.3, 0.38), length=0.38, thickness=0.19,
                       color=skin, style="taper", tip_color=skin_deep,
                       segments=4, curl=0.4)

    groups = {
        "body": (body, (0, -0.16, 0.38)),
        "head": (head, (0, 0.34, 0.5)),
        "tail": ([tail_obj], (0, -0.3, 0.38)),
    }
    for key, obj in legs.items():
        groups[key] = ([obj], tuple(obj.location))
    bk.assemble(root, groups)
    return bk.finish(root)


# ---------------------------------------------------------------------------
# Red Panda -- Mythic, $450K/s.
# A round rust body with a head almost as wide as it is, a cream bandit mask
# with rust tear-stripes, and a banded tail held up in an arc so it clears the
# body instead of dragging behind it. The mythic tell is a gold-leaf torc and
# one blossom tucked over an ear -- placed, not scattered.
# ---------------------------------------------------------------------------

def build_red_panda():
    kit.reset_scene()
    root = kit.empty("root")

    rust = "#b6552c"
    rust_deep = "#8c3a1c"
    face_cream = "#f7ead6"
    paw = CHARCOAL

    body_dims = (0.38, 0.5, 0.36)
    body_at = (0, -0.06, 0.44)
    body = [bk.block("body.core", body_dims, body_at, color=rust)]
    body.append(bk.block("body.chest", (0.34, 0.16, 0.3), (0, 0.2, 0.42),
                         color=rust))
    # Dark undercarriage: red pandas are near-black from the chest down.
    body += bk.belly("body.bib", body_at, body_dims, color=paw, inset=0.6)
    body.append(bk.block("body.underside", (0.34, 0.44, 0.11), (0, -0.06, 0.28),
                         color=paw))
    # Gold torc across the chest -- the mythic accent. It has to sit BELOW the
    # skull and in FRONT of the chest block; tucked up at the neck it lands
    # inside the head's own volume and never renders at all.
    body.append(bk.block("body.torc", (0.3, 0.08, 0.09), (0, 0.27, 0.52),
                         color=GOLD))
    body.append(bk.block("body.torc.bell", (0.1, 0.09, 0.1), (0, 0.29, 0.44),
                         color=GOLD_BRIGHT))

    head_dims = (0.36, 0.3, 0.31)
    head_at = (0, 0.36, 0.7)
    head = [bk.block("head.skull", head_dims, head_at, color=rust)]
    face = bk.face_of(head_at, head_dims, "front")
    # The mask: a broad cream plate low on the face, a rust brow band above it,
    # then rust tear-stripes dropping from each eye. Painting the stripes ON
    # the mask is what makes the marking read at icon size instead of turning
    # into one pale blob.
    # depth/proud here are deliberately small: the mask is the BASE layer, and
    # the eyes and snout that follow have to sit proud of it, not inside it.
    head.append(bk.face_plate("head.mask", face, (0.33, 0.21), face="front",
                              color=face_cream, depth=0.018, offset=(0, -0.03),
                              proud=bk.PROUD * 0.4))
    head.append(bk.face_plate("head.brow", face, (0.33, 0.075), face="front",
                              color=rust, depth=0.022, offset=(0, 0.11)))
    for side, sign in (("L", 1), ("R", -1)):
        tear = bk.face_plate("head.tear.%s" % side, face, (0.055, 0.14),
                             face="front", color=rust, depth=0.02,
                             offset=(sign * 0.1, -0.03), proud=bk.PROUD * 3)
        tear.rotation_euler.y = sign * 9 * bk.D2R
        head.append(tear)
    head += bk.eyes("head.eye", head_at, head_dims, spacing=0.5, height=0.045,
                    size=0.065, style="white", iris="#1d1418", pupil_scale=0.6)
    head += bk.snout("head.snout", head_at, head_dims, width=0.13, length=0.1,
                     height=0.085, color=face_cream, drop=-0.1,
                     nose_color="#241a1e")
    ear_l, ear_r = bk.ears_box("ear", head_at, head_dims, size=0.15,
                               spacing=0.66, depth=0.065, color=rust,
                               inner_color=face_cream)
    head += _blossom("head.flower", (0.2, 0.34, 0.94), size=0.12)

    legs = bk.legs_quad("leg", front=(0.14, 0.14, 0.28), back=(0.15, -0.2, 0.28),
                        length=0.22, thickness=0.115, color=paw, foot_color=paw)

    # The tail is the icon: as long as the body, thick, banded, and arced UP so
    # it breaks the outline instead of hiding inside it.
    tail_base = (0, -0.28, 0.5)
    tail_len, tail_lift = 0.58, 0.4
    tail_parts = []
    bands = 7
    for i in range(bands):
        t = (i + 0.5) / bands
        w = 0.23 - 0.075 * t
        tail_parts.append(bk.block(
            "tail.band%d" % i, (w, tail_len / bands * 1.2, w),
            (0, tail_base[1] - tail_len * t, tail_base[2] + tail_lift * t * t),
            color=(rust if i % 2 == 0 else face_cream)))
    tail_parts.append(bk.block("tail.tip", (0.13, 0.1, 0.13),
                               (0, tail_base[1] - tail_len - 0.03,
                                tail_base[2] + tail_lift * 1.08),
                               color=rust_deep))

    groups = {
        "body": (body, (0, -0.1, 0.28)),
        "head": (head, (0, 0.24, 0.56)),
        "ear.L": ([ear_l], tuple(ear_l.location)),
        "ear.R": ([ear_r], tuple(ear_r.location)),
        "tail": (tail_parts, tail_base),
    }
    for key, obj in legs.items():
        groups[key] = ([obj], tuple(obj.location))
    bk.assemble(root, groups)
    return bk.finish(root)


# ---------------------------------------------------------------------------
# Snowy Owl -- Cosmic, $7.5M/s.
# A white bird on a dark shelf is one step away from being a featureless blob,
# so almost every decision here is about breaking the white up: charcoal
# barring across the breast and wings, a dark mask ring around each eye, and
# eyes that actually emit amber. The cosmic charge is a gold halo standing
# behind the skull.
# ---------------------------------------------------------------------------

def build_snowy_owl():
    kit.reset_scene()
    root = kit.empty("root")

    down = "#f9f6f1"
    speck = "#3c3138"
    amber = "#ffb43c"

    body_dims = (0.44, 0.36, 0.5)
    body_at = (0, -0.02, 0.5)
    body = [bk.block("body.core", body_dims, body_at, color=down)]
    # Barrelled belly: wider than the shoulders, which is what stops an upright
    # bird from reading as a rectangular appliance.
    body.append(bk.block("body.belly", (0.52, 0.44, 0.3), (0, -0.01, 0.38),
                         color=down))
    body.append(bk.block("body.shoulders", (0.4, 0.32, 0.16), (0, -0.02, 0.72),
                         color=down))
    body += bk.belly("body.breast", body_at, body_dims, color=SNOW, inset=0.74)
    # Chevron flecks rather than horizontal bars: staggered slanted pairs.
    # Straight bands across a white breast read as a radiator grille; offset
    # chevrons read as plumage.
    breast = bk.face_of(body_at, body_dims, "front")
    for i in range(4):
        z = 0.645 - i * 0.115
        dx = 0.05 if i % 2 else -0.05
        for slot, sign in ((0, 1), (1, -1)):
            fleck = bk.face_plate(
                "body.fleck%d_%d" % (i, slot), breast, (0.075, 0.03),
                face="front", color=speck, depth=0.02,
                offset=(dx + sign * 0.075, z - body_at[2]),
                proud=bk.PROUD * 3)
            fleck.rotation_euler.y = sign * 26 * bk.D2R
            body.append(fleck)
    body += bk.spots("body.speck", (0, -0.01, 0.44), (0.48, 0.4, 0.5), count=9,
                     size=0.065, color=speck, seed=17,
                     faces=("left", "right", "back"))
    # Feathered trousers -- snowy owls are downed right to the toes.
    body.append(bk.block("body.cuffs", (0.34, 0.26, 0.16), (0, 0.0, 0.23),
                         color=down))
    # A narrow SHADED collar pinching the torso off from the skull. Making it
    # merely a slightly different white was not enough -- it needs to be a dark
    # enough line to survive being 24px tall, or the owl loses its head.
    body.append(bk.block("body.collar", (0.26, 0.22, 0.08), (0, 0.04, 0.81),
                         color="#a9a096"))

    # The skull is markedly wider than the torso -- that width is "owl".
    head_dims = (0.54, 0.35, 0.37)
    head_at = (0, 0.14, 1.05)
    head = [bk.block("head.skull", head_dims, head_at, color=down)]
    face = bk.face_of(head_at, head_dims, "front")
    head.append(bk.face_plate("head.disc.rim", face, (0.54, 0.36), face="front",
                              color="#b8afa4", depth=0.026,
                              proud=bk.PROUD * 0.4))
    head.append(bk.face_plate("head.disc", face, (0.48, 0.3), face="front",
                              color=SNOW, depth=0.03, proud=bk.PROUD * 2))
    # The eyes are three explicit stacked blocks at known Y depths -- socket,
    # emissive iris, pupil -- rather than face plates. `face_plate`'s `proud`
    # offsets are tiny and easy to invert by accident, and an inverted socket
    # plate hides the glow entirely, which turns a snowy owl into a fridge with
    # two black rectangles for eyes.
    front = face[1]
    for side, sign in (("L", 1), ("R", -1)):
        eye_x = sign * 0.14
        head.append(bk.block("head.socket.%s" % side, (0.2, 0.03, 0.2),
                             (eye_x, front + 0.03, 1.045), color=speck))
        head.append(bk.glow_block("head.iris.%s" % side, (0.155, 0.03, 0.165),
                                  (eye_x, front + 0.05, 1.045), color=amber,
                                  strength=3.4))
        head.append(bk.block("head.pupil.%s" % side, (0.06, 0.03, 0.08),
                             (eye_x, front + 0.068, 1.045), color="#1c1216"))
        head.append(bk.block("head.glint.%s" % side, (0.028, 0.03, 0.028),
                             (eye_x + 0.048, front + 0.068, 1.095), color=SNOW))
    head += bk.beak("head.beak", head_at, head_dims, width=0.065, length=0.12,
                    height=0.075, color="#31282e", drop=-0.14, taper=0.72)
    # A charcoal chevron across the crown finishes the break-up of the white.
    for side, sign in (("L", 1), ("R", -1)):
        head.append(bk.face_plate(
            "head.crown.%s" % side, bk.face_of(head_at, head_dims, "top"),
            (0.14, 0.05), face="top", color=speck, depth=0.02,
            offset=(sign * 0.11, -0.02)))
    head += bk.spots("head.speck", head_at, head_dims, count=5, size=0.05,
                     color=speck, seed=5, faces=("left", "right"))
    # Cosmic halo: one gold ring standing on edge behind the skull.
    head += bk.ring("head.halo", (0, -0.16, 1.08), radius=0.38, thickness=0.028,
                    tilt=90.0, color=GOLD, strength=2.0)

    # Wings pushed well off the flanks and barred dark at the trailing edge.
    # Wings are built by hand instead of through `wings_flat`, because the dark
    # primaries have to be part of the same mesh: a white wing folded against a
    # white body has no outline without them. Building the left side and
    # mirroring once also avoids the name collision that comes from joining
    # extra parts onto a pair `wings_flat` has already named -- the leftover
    # original wing.R survives, Blender renames the new one wing.R.001, and the
    # runtime silently drops a limb it can no longer find by name.
    wing_at = (0.26, -0.02, 0.62)
    wing_parts = []
    for i in range(2):
        t = float(i)
        wing_parts.append(bk.block(
            "wing.f%d" % i,
            (0.16 * (1 - 0.18 * t), 0.08, 0.44 * (1 - 0.22 * t)),
            (wing_at[0] + 0.08, wing_at[1] - 0.1 * t, wing_at[2] - 0.13 * t),
            rot=(0, -10 - 8 * t, 0), color=(down if i == 0 else "#ece4d8")))
    for i in range(3):
        wing_parts.append(bk.block(
            "wing.bar%d" % i, (0.055, 0.075, 0.2),
            (0.33 + i * 0.035, -0.06, 0.44 - i * 0.03),
            rot=(0, -14 - i * 6, 0), color=speck))
    wing_l = kit.join(wing_parts, "wing.L")
    kit.weld(wing_l)
    kit.set_origin_to(wing_l, wing_at)
    wing_r = kit.duplicate(wing_l, "wing.R", mirror=True)
    wing_r.location = (-wing_l.location.x, wing_l.location.y, wing_l.location.z)
    # Two petals drifting past a wing, frozen mid-fall.
    petals = _blossom("body.petal", (0.38, 0.2, 0.9), size=0.11,
                      color=PETAL_LIGHT)

    legs = bk.bird_feet("leg", (0.12, 0.03, 0.22), shin=0.1, thickness=0.065,
                        toe=0.17, color="#c9a86a")

    groups = {
        "body": (body + petals, (0, 0, 0.24)),
        "head": (head, (0, 0.02, 0.86)),
        "wing.L": ([wing_l], tuple(wing_l.location)),
        "wing.R": ([wing_r], tuple(wing_r.location)),
    }
    for key, obj in legs.items():
        groups[key] = ([obj], tuple(obj.location))
    bk.assemble(root, groups)
    return bk.finish(root)


# ---------------------------------------------------------------------------
# Koi -- Cosmic, $12M/s.
# No legs: this one swims, hovering above a glowing ripple ring that both reads
# as water and gives the silhouette a base to sit on. The fins are oversized on
# purpose -- a koi at icon size is a white lozenge plus enormous flags.
# ---------------------------------------------------------------------------

def build_koi():
    kit.reset_scene()
    root = kit.empty("root")

    scale_w = "#fbf8f4"
    kohaku = "#e8622a"
    kohaku_deep = "#c14a1c"
    fin_c = "#fde8dd"
    ripple = "#9fd8ff"

    # The body is a chain of four shrinking blocks so it tapers like a fish
    # instead of sitting there as a brick.
    body = []
    for name, dims, at in (
        ("core", (0.28, 0.3, 0.34), (0, 0.1, 0.6)),
        ("mid", (0.24, 0.26, 0.3), (0, -0.16, 0.6)),
        ("rear", (0.17, 0.22, 0.23), (0, -0.38, 0.595)),
        ("peduncle", (0.11, 0.18, 0.15), (0, -0.55, 0.59)),
    ):
        body.append(bk.block("body." + name, dims, at, color=scale_w))
    # Kohaku markings: two big orange saddles rather than confetti spotting.
    body.append(bk.block("body.mark0", (0.29, 0.2, 0.35), (0, 0.06, 0.605),
                         color=kohaku))
    body.append(bk.block("body.mark1", (0.19, 0.13, 0.245), (0, -0.33, 0.6),
                         color=kohaku))
    body.append(bk.slab("body.mark2", (0.25, 0.1, 0.31), (0, -0.2, 0.6),
                        color=kohaku_deep))
    # Dorsal fin: a long low blade running the length of the back.
    body.append(bk.wedge("body.dorsal", (0.045, 0.46, 0.19),
                         (0, -0.06, 0.85), color=fin_c, taper=0.5))
    body.append(bk.wedge("body.pelvic", (0.045, 0.2, 0.14),
                         (0, -0.18, 0.38), rot=(180, 0, 0), color=fin_c,
                         taper=0.5))
    # The ripple: two emissive tori at water level. They double as the model's
    # floor contact, so the koi visibly hovers instead of balancing on a fin.
    body += bk.ring("body.ripple", (0, -0.06, 0.06), radius=0.44,
                    thickness=0.026, tilt=0.0, color=ripple, strength=1.8)
    body += bk.ring("body.ripple2", (0, -0.06, 0.05), radius=0.28,
                    thickness=0.016, tilt=0.0, color="#cceeff", strength=1.4)

    head_dims = (0.3, 0.26, 0.32)
    head_at = (0, 0.4, 0.61)
    head = [bk.block("head.skull", head_dims, head_at, color=scale_w)]
    # The red crown patch that makes a koi a tancho koi -- one dot, dead centre.
    head.append(bk.block("head.tancho", (0.16, 0.16, 0.045), (0, 0.4, 0.79),
                         color=LACQUER))
    lip_at, lip_dims = (0, 0.56, 0.575), (0.15, 0.1, 0.11)
    head.append(bk.block("head.lips", lip_dims, lip_at, color=kohaku))
    head.append(bk.face_plate("head.mouth", bk.face_of(lip_at, lip_dims, "front"),
                              (0.08, 0.04), face="front", color="#7d2d12",
                              depth=0.02))
    head += bk.eyes("head.eye", head_at, head_dims, spacing=0.88, height=0.03,
                    size=0.075, style="white", iris="#1a1418", pupil_scale=0.66)
    for side, sign in (("L", 1), ("R", -1)):
        facing = "left" if sign > 0 else "right"
        # Gill plate: a dark arc marking where head ends and body begins.
        head.append(bk.face_plate(
            "head.gill.%s" % side, bk.face_of(head_at, head_dims, facing),
            (0.065, 0.24), face=facing, color=kohaku_deep, depth=0.02,
            offset=(-0.09, 0)))
        # Barbels: two glowing gold whiskers trailing back from the mouth.
        head.append(bk.glow_block(
            "head.barbel.%s" % side, (0.022, 0.2, 0.022),
            (sign * 0.065, 0.6, 0.53), rot=(-16, 0, sign * 22),
            color=GOLD_BRIGHT, strength=2.2))

    # Enormous pectoral fins, angled down and back like a glider's wings.
    fin_l, fin_r = bk.fins("fin", (0.13, 0.16, 0.57), size=0.36, thickness=0.045,
                           color=fin_c, tilt=30.0)
    tail_fin = bk.fin_tail("fin.tail", (0, -0.62, 0.59), size=0.46,
                           thickness=0.05, color=fin_c, lobes=2)
    tail_extra = [bk.slab("fin.tail.wash", (0.055, 0.22, 0.24),
                          (0, -0.71, 0.59), color=kohaku)]
    for i, (up, drop) in enumerate(((1, 0.2), (-1, 0.2))):
        tail_extra.append(bk.slab(
            "fin.tail.trail%d" % i, (0.045, 0.26, 0.2),
            (0, -0.92, 0.59 + up * drop), rot=(up * 34, 0, 0), color=fin_c))

    groups = {
        "body": (body, (0, -0.2, 0.6)),
        "head": (head, (0, 0.26, 0.6)),
        "fin.L": ([fin_l], tuple(fin_l.location)),
        "fin.R": ([fin_r], tuple(fin_r.location)),
        "fin.tail": ([tail_fin] + tail_extra, (0, -0.62, 0.59)),
    }
    bk.assemble(root, groups)
    return bk.finish(root)


# ---------------------------------------------------------------------------
# Stag -- Secret, $145M/s.
# The showpiece of the terrace: a pale ceremonial deer whose antlers spread
# WIDER than the animal is long. Spread beats height here -- a tall rack just
# shrinks the body under height normalisation, whereas a wide one fills the
# icon. Gold tips, blossom hung along the beams, glowing eyes. The antlers ride
# the ear.L/ear.R slots so the runtime sways them.
# ---------------------------------------------------------------------------

def build_stag():
    kit.reset_scene()
    root = kit.empty("root")

    coat = "#efe4d4"
    coat_deep = "#d0bda4"
    beam = "#c9b596"
    hoof = CHARCOAL
    eye_glow = "#ffd27a"

    body_dims = (0.44, 0.68, 0.46)
    body_at = (0, -0.08, 0.92)
    body = [bk.block("body.core", body_dims, body_at, color=coat)]
    body.append(bk.block("body.shoulder", (0.48, 0.28, 0.52), (0, 0.18, 0.96),
                         color=coat))
    body.append(bk.block("body.rump", (0.42, 0.24, 0.42), (0, -0.36, 0.92),
                         color=coat))
    body += bk.belly("body.chest", body_at, body_dims, color=CREAM, inset=0.6)
    # Dapples down the flanks -- a deer's one texture, done as flat plates.
    body += bk.spots("body.dapple", body_at, body_dims, count=6, size=0.06,
                     color=coat_deep, seed=23, faces=("left", "right"))

    # The caparison. A cream deer on a pale shelf is a blank silhouette with a
    # blank interior, so the shrine cloth does two jobs: it puts the biome's
    # lacquer red on the largest flat area the model has, and it gives the eye
    # somewhere to land between the antlers and the legs.
    cloth_at = (0, -0.1, 1.14)
    body.append(bk.slab("body.cloth", (0.5, 0.46, 0.07), cloth_at,
                        color=LACQUER))
    body.append(bk.slab("body.cloth.trim", (0.53, 0.08, 0.075),
                        (0, 0.11, 1.142), color=GOLD))
    body.append(bk.slab("body.cloth.trim2", (0.53, 0.08, 0.075),
                        (0, -0.31, 1.142), color=GOLD))
    for side, sign in (("L", 1), ("R", -1)):
        # Skirts hanging down each flank, hemmed in gold.
        body.append(bk.slab("body.skirt.%s" % side, (0.07, 0.42, 0.26),
                            (sign * 0.235, -0.1, 1.0), color=LACQUER))
        body.append(bk.slab("body.hem.%s" % side, (0.075, 0.42, 0.06),
                            (sign * 0.238, -0.1, 0.89), color=GOLD))
    body += _blossom("body.cloth.bloom", (0.14, -0.02, 1.185), size=0.13,
                     color=PETAL_LIGHT)
    body += _blossom("body.cloth.bloom2", (-0.13, -0.22, 1.185), size=0.11,
                     color=PETAL)
    # Neck: three blocks climbing forward, carrying the head well clear of the
    # shoulder. Without this the antlers sit on the back and the pose dies.
    for i in range(3):
        t = i / 2.0
        body.append(bk.block("body.neck%d" % i, (0.24 - 0.02 * t, 0.21, 0.21),
                             (0, 0.3 + t * 0.11, 1.14 + t * 0.14),
                             rot=(-34, 0, 0), color=coat))
    body.append(bk.block("body.collar", (0.28, 0.09, 0.26), (0, 0.3, 1.12),
                         rot=(-34, 0, 0), color=GOLD))
    body.append(bk.block("body.pendant", (0.1, 0.07, 0.1), (0, 0.42, 1.05),
                         color=GOLD_BRIGHT))

    head_dims = (0.25, 0.32, 0.25)
    head_at = (0, 0.52, 1.42)
    head = [bk.block("head.skull", head_dims, head_at, color=coat)]
    muzzle_at, muzzle_dims = (0, 0.72, 1.36), (0.18, 0.2, 0.17)
    head.append(bk.block("head.muzzle", muzzle_dims, muzzle_at, color=CREAM))
    head.append(bk.face_plate(
        "head.nose", bk.face_of(muzzle_at, muzzle_dims, "front"),
        (0.11, 0.065), face="front", color="#2b2126", depth=0.022,
        offset=(0, 0.03)))
    head += bk.eyes("head.eye", head_at, head_dims, spacing=0.98, height=0.03,
                    size=0.07, style="glow", iris=eye_glow)
    # Long deer ears, low and swept back, clearly distinct from antler beams.
    for side, sign in (("L", 1), ("R", -1)):
        head.append(bk.wedge("head.ear.%s" % side, (0.065, 0.11, 0.2),
                             (sign * 0.17, 0.42, 1.53),
                             rot=(18, -sign * 58, 0), color=coat, taper=0.5))
    head.append(bk.face_plate("head.band", bk.face_of(head_at, head_dims, "front"),
                              (0.23, 0.05), face="front", color=GOLD_BRIGHT,
                              depth=0.024, offset=(0, 0.09)))

    # Antlers: a beam sweeping out and back, four tines, gold at the tips, two
    # blossoms hung on each side. Width is the point -- tips reach |x| ~= 0.58.
    antlers = []
    for side, sign in (("L", 1), ("R", -1)):
        base = (sign * 0.1, 0.46, 1.55)
        parts = [
            bk.block("ear.%s.beam" % side, (0.095, 0.095, 0.32),
                     (sign * 0.2, 0.4, 1.63), rot=(12, -sign * 40, 0),
                     color=beam),
            bk.block("ear.%s.beam2" % side, (0.085, 0.085, 0.32),
                     (sign * 0.43, 0.28, 1.73), rot=(22, -sign * 62, 0),
                     color=beam),
            bk.wedge("ear.%s.tine0" % side, (0.07, 0.07, 0.26),
                     (sign * 0.23, 0.6, 1.68), rot=(-46, -sign * 20, 0),
                     color=beam, taper=0.55),
            bk.wedge("ear.%s.tine1" % side, (0.068, 0.068, 0.26),
                     (sign * 0.41, 0.46, 1.84), rot=(-14, -sign * 26, 0),
                     color=beam, taper=0.55),
            bk.wedge("ear.%s.tine2" % side, (0.066, 0.066, 0.26),
                     (sign * 0.57, 0.24, 1.85), rot=(20, -sign * 30, 0),
                     color=GOLD, taper=0.55),
            bk.wedge("ear.%s.tine3" % side, (0.062, 0.062, 0.22),
                     (sign * 0.51, 0.0, 1.75), rot=(48, -sign * 26, 0),
                     color=GOLD, taper=0.55),
            bk.block("ear.%s.tip" % side, (0.075, 0.075, 0.08),
                     (sign * 0.6, 0.24, 1.96), color=GOLD_BRIGHT),
        ]
        parts += _blossom("ear.%s.bloom0" % side, (sign * 0.3, 0.54, 1.78),
                          size=0.17)
        parts += _blossom("ear.%s.bloom1" % side, (sign * 0.49, 0.3, 1.92),
                          size=0.15, color=PETAL_LIGHT)
        merged = kit.join(parts, "ear.%s" % side)
        kit.weld(merged)
        kit.set_origin_to(merged, base)
        antlers.append(merged)

    legs = bk.legs_quad("leg", front=(0.17, 0.24, 0.72), back=(0.18, -0.32, 0.72),
                        length=0.64, thickness=0.105, color=coat,
                        foot_color=hoof)
    tail_obj = bk.tail("tail", (0, -0.48, 0.98), length=0.17, thickness=0.11,
                       color=CREAM, style="puff", segments=2, curl=0.6)

    groups = {
        "body": (body, (0, -0.1, 0.62)),
        "head": (head, (0, 0.42, 1.28)),
        "ear.L": ([antlers[0]], tuple(antlers[0].location)),
        "ear.R": ([antlers[1]], tuple(antlers[1].location)),
        "tail": ([tail_obj], (0, -0.48, 0.98)),
    }
    for key, obj in legs.items():
        groups[key] = ([obj], tuple(obj.location))
    bk.assemble(root, groups)
    return bk.finish(root)


# ---------------------------------------------------------------------------
# Kitsune -- Divine, $1.8B/s.
# Nine tails is the entire brief, so nine tails is what the silhouette is: a
# white-and-gold fan twice the width of the fox itself. Two tricks make the fan
# read instead of clumping -- alternating tail LENGTHS so the tips never line
# up, and a pitch that flattens toward the outside so the fan opens rather than
# bunching into a bouquet.
#
# The animation slots are reused shamelessly: tail (3), arm.L/.R (2 each),
# fin.L/.R (1 each) = 9, so every tail moves on its own bone.
# ---------------------------------------------------------------------------

def _kit_tail(name, base, yaw, pitch, length, thickness, color, tip):
    """One flame-shaped tail, rotated into place around its own base."""
    obj = bk.tail(name, base, length=length, thickness=thickness, color=color,
                  style="taper", tip_color=tip, segments=3, curl=0.55)
    obj.rotation_euler = (pitch * bk.D2R, 0.0, yaw * bk.D2R)
    return obj


def build_kitsune():
    kit.reset_scene()
    root = kit.empty("root")

    pelt = "#fbf7f2"
    mask = LACQUER
    paw = LACQUER_DEEP
    flame = "#ffb75e"

    body_dims = (0.34, 0.52, 0.34)
    body_at = (0, -0.06, 0.54)
    body = [bk.block("body.core", body_dims, body_at, color=pelt)]
    body.append(bk.block("body.shoulder", (0.36, 0.2, 0.36), (0, 0.14, 0.56),
                         color=pelt))
    body += bk.belly("body.chest", body_at, body_dims, color=SNOW, inset=0.66)
    # Gold saddle band across the spine and a gold hip ring where the fan opens.
    body.append(bk.block("body.saddle", (0.36, 0.1, 0.36), (0, -0.02, 0.55),
                         color=GOLD))
    body.append(bk.block("body.hipring", (0.31, 0.08, 0.31), (0, -0.28, 0.56),
                         color=GOLD_BRIGHT))
    # Three floating foxfires orbiting the shoulders -- the divine tell.
    for i, (dx, dy, dz, s) in enumerate((
        (0.36, 0.22, 0.95, 0.09), (-0.34, -0.04, 1.06, 0.075),
        (0.28, -0.34, 1.0, 0.065),
    )):
        body.append(bk.glow_block("body.fire%d" % i, (s, s, s * 1.7),
                                  (dx, dy, dz), rot=(0, 0, 30 * i),
                                  color=flame, strength=3.6))

    head_dims = (0.3, 0.24, 0.28)
    head_at = (0, 0.38, 0.78)
    head = [bk.block("head.skull", head_dims, head_at, color=pelt)]
    face = bk.face_of(head_at, head_dims, "front")
    # The red mask marking: a broad band across the eyes with two tines rising
    # onto the brow. This, not the tails, is what identifies it up close.
    # Base layer, so kept shallow -- the glowing eyes must read THROUGH it.
    head.append(bk.face_plate("head.mask", face, (0.3, 0.115), face="front",
                              color=mask, depth=0.018, offset=(0, 0.055),
                              proud=bk.PROUD * 0.4))
    for side, sign in (("L", 1), ("R", -1)):
        tine = bk.face_plate("head.masktine.%s" % side, face, (0.05, 0.14),
                             face="front", color=mask, depth=0.022,
                             offset=(sign * 0.1, 0.15), proud=bk.PROUD * 2)
        tine.rotation_euler.y = sign * -14 * bk.D2R
        head.append(tine)
    head.append(bk.face_plate("head.maskdot", face, (0.055, 0.055), face="front",
                              color=GOLD_BRIGHT, depth=0.022, offset=(0, 0.055),
                              proud=bk.PROUD * 4))
    head += bk.eyes("head.eye", head_at, head_dims, spacing=0.56, height=0.05,
                    size=0.065, style="glow", iris=GOLD_BRIGHT)
    head += bk.snout("head.snout", head_at, head_dims, width=0.13, length=0.17,
                     height=0.11, color=SNOW, drop=-0.06, nose_color="#2a1e22")
    ear_l, ear_r = bk.ears_pointed("ear", head_at, head_dims, size=0.14,
                                   spacing=0.66, length=0.26, color=pelt,
                                   inner_color=mask, lean=10)

    # --- the fan of nine ------------------------------------------------
    # Every tail is rotated around one shared base at the rump. Yaw spreads it
    # sideways; pitch lifts it. Alternating lengths stagger the tips so nine
    # overlapping puffs still read as nine separate tails.
    # Yaw is capped at 62 degrees on purpose. Yawing a backward-pointing tail
    # past that swings it out to the SIDE of the fox with no backward component
    # left, and nine of those stop reading as tails and start reading as a
    # shaggy collar. Pitch does the rest of the spreading instead.
    base = (0, -0.4, 0.6)
    fan = []
    for i in range(9):
        a = (i - 4) / 4.0                     # -1 .. +1 across the fan
        yaw = a * 66.0
        lift = 10.0 + 24.0 * (1.0 - abs(a))   # centre most upright, ends low
        length = (0.76 if i % 2 == 0 else 0.6) - abs(a) * 0.06
        tip = GOLD_BRIGHT if i % 2 == 0 else PETAL_LIGHT
        fan.append(_kit_tail("tail%d" % i, base, yaw, -lift, length, 0.15,
                             pelt, tip))

    legs = bk.legs_quad("leg", front=(0.13, 0.16, 0.34), back=(0.14, -0.2, 0.34),
                        length=0.3, thickness=0.095, color=pelt, foot_color=paw)

    # Slot reuse: three tails on the tail bone, two per arm bone, one per fin
    # bone. Nothing else claims arm.L/.R or fin.L/.R on this pet, so all nine
    # tails end up on independent bones and the fan ripples instead of swinging
    # as one slab.
    groups = {
        "body": (body, (0, -0.1, 0.34)),
        "head": (head, (0, 0.26, 0.66)),
        "ear.L": ([ear_l], tuple(ear_l.location)),
        "ear.R": ([ear_r], tuple(ear_r.location)),
        "tail": ([fan[3], fan[4], fan[5]], base),
        "arm.L": ([fan[2], fan[1]], base),
        "arm.R": ([fan[6], fan[7]], base),
        "fin.L": ([fan[0]], base),
        "fin.R": ([fan[8]], base),
    }
    for key, obj in legs.items():
        groups[key] = ([obj], tuple(obj.location))
    bk.assemble(root, groups)
    return bk.finish(root)


# ---------------------------------------------------------------------------
# Oni Tiger -- Eternal, $600M/s. ORIGINAL.
# A demon-masked tiger. The mask is not painted on -- it is a bone panel
# standing proud of the skull and wider than it, with a lacquer brow, burning
# eye slits and gold fangs hanging below the jaw. Hiding the animal's own face
# is what turns a big cat into a temple guardian. Gold horns ride the ear
# slots so they toss with the walk cycle.
# ---------------------------------------------------------------------------

def build_oni_tiger():
    kit.reset_scene()
    root = kit.empty("root")

    hide = "#c0392f"
    hide_deep = "#8e1f1c"
    stripe = CHARCOAL
    bone = "#f2e6d2"
    ember = "#ffca4a"

    # Heavy front end, tapering rear -- a predator carrying its weight forward.
    body_dims = (0.46, 0.62, 0.44)
    body_at = (0, -0.08, 0.58)
    body = [bk.block("body.core", body_dims, body_at, color=hide)]
    body.append(bk.block("body.shoulders", (0.54, 0.26, 0.5), (0, 0.2, 0.62),
                         color=hide))
    body.append(bk.block("body.haunch", (0.42, 0.24, 0.4), (0, -0.34, 0.55),
                         color=hide))
    body += bk.belly("body.chest", body_at, body_dims, color="#e8c9a8", inset=0.56)
    body += bk.stripes("body.stripe", body_at, body_dims, count=5, width=0.055,
                       color=stripe, axis="y")
    body.append(bk.block("body.stripe.sh", (0.55, 0.055, 0.51), (0, 0.2, 0.62),
                         color=stripe))
    # Gold shoulder plates -- armour, and a place for the eye to land.
    for side, sign in (("L", 1), ("R", -1)):
        body.append(bk.block("body.pauldron.%s" % side, (0.11, 0.26, 0.22),
                             (sign * 0.27, 0.18, 0.76), rot=(0, sign * 16, 0),
                             color=GOLD))
        body.append(bk.block("body.rivet.%s" % side, (0.055, 0.055, 0.055),
                             (sign * 0.31, 0.18, 0.88), color=GOLD_BRIGHT))
    # Spine flames licking off the back.
    for i, y in enumerate((0.06, -0.12, -0.3)):
        body.append(bk.glow_block("body.spinefire%d" % i,
                                  (0.065, 0.065, 0.16 - i * 0.025),
                                  (0, y, 0.86 + i * 0.01), rot=(-8 + i * 6, 0, 0),
                                  color="#ff7a3c", strength=2.8))

    head_dims = (0.4, 0.3, 0.34)
    head_at = (0, 0.5, 0.88)
    head = [bk.block("head.skull", head_dims, head_at, color=hide)]
    # Charcoal mane tufts framing where the mask will sit.
    for i, (dx, dz) in enumerate(((0.23, 0.98), (-0.23, 0.98),
                                  (0.21, 0.78), (-0.21, 0.78))):
        head.append(bk.wedge("head.ruff%d" % i, (0.07, 0.1, 0.17),
                             (dx, 0.42, dz), rot=(0, math.copysign(56, dx), 0),
                             color=stripe, taper=0.6))
    # Small pinned-back tiger ears behind the mask.
    for side, sign in (("L", 1), ("R", -1)):
        head.append(bk.block("head.ear.%s" % side, (0.11, 0.065, 0.1),
                             (sign * 0.15, 0.4, 1.08), rot=(0, sign * 24, 0),
                             color=hide))
        head.append(bk.block("head.earin.%s" % side, (0.055, 0.045, 0.055),
                             (sign * 0.16, 0.42, 1.09), color=stripe))

    # --- the mask: a real panel, not a decal ----------------------------
    mask_dims = (0.46, 0.09, 0.4)
    mask_at = (0, head_at[1] + 0.2, head_at[2] + 0.01)
    head.append(bk.block("head.mask", mask_dims, mask_at, color=bone))
    mask_face = bk.face_of(mask_at, mask_dims, "front")
    # Flared lacquer horns-of-the-brow at the mask's top corners.
    for side, sign in (("L", 1), ("R", -1)):
        head.append(bk.block("head.mask.flare.%s" % side, (0.11, 0.08, 0.14),
                             (sign * 0.26, mask_at[1] - 0.01, mask_at[2] + 0.16),
                             rot=(0, sign * 26, 0), color=bone))
    head.append(bk.face_plate("head.mask.brow", mask_face, (0.46, 0.09),
                              face="front", color=hide_deep, depth=0.03,
                              offset=(0, 0.15), proud=bk.PROUD * 3))
    for side, sign in (("L", 1), ("R", -1)):
        # Angled eye slits, burning through the mask.
        slit = bk.face_plate("head.slit.%s" % side, mask_face, (0.13, 0.065),
                             face="front", color="#2b1a18", depth=0.03,
                             offset=(sign * 0.11, 0.04), proud=bk.PROUD * 4)
        slit.rotation_euler.y = sign * -18 * bk.D2R
        head.append(slit)
        head.append(bk.glow_block(
            "head.glow.%s" % side, (0.085, 0.03, 0.032),
            (sign * 0.11, mask_at[1] + 0.115, mask_at[2] + 0.04),
            rot=(0, sign * -18, 0), color=ember, strength=4.4))
        # Lacquer war-paint stripes on the mask's cheeks.
        head.append(bk.face_plate("head.paint.%s" % side, mask_face,
                                  (0.055, 0.14), face="front", color=LACQUER,
                                  depth=0.024, offset=(sign * 0.18, -0.04),
                                  proud=bk.PROUD * 3))
    # Snarl: a dark slot with bone teeth, low on the mask.
    head.append(bk.face_plate("head.snarl", mask_face, (0.28, 0.09),
                              face="front", color="#2b1a18", depth=0.03,
                              offset=(0, -0.13), proud=bk.PROUD * 3))
    for i, dx in enumerate((-0.09, -0.03, 0.03, 0.09)):
        head.append(bk.face_plate("head.tooth%d" % i, mask_face, (0.035, 0.07),
                                  face="front", color=bone, depth=0.026,
                                  offset=(dx, -0.13), proud=bk.PROUD * 6))
    # Gold tusks hanging below the mask's jaw.
    for side, sign in (("L", 1), ("R", -1)):
        head.append(bk.wedge("head.fang.%s" % side, (0.05, 0.05, 0.14),
                             (sign * 0.1, mask_at[1] - 0.01, mask_at[2] - 0.25),
                             rot=(186, 0, 0), color=GOLD_BRIGHT, taper=0.7))

    # Horns: a gold socket, a thick swept beam and a bright tip, grouped into
    # the ear slots so the runtime tosses them with the head.
    horns = []
    for side, sign in (("L", 1), ("R", -1)):
        base = (sign * 0.15, 0.44, 1.05)
        parts = [
            bk.block("ear.%s.socket" % side, (0.12, 0.12, 0.1),
                     (sign * 0.15, 0.44, 1.08), color=GOLD),
            bk.wedge("ear.%s.beam" % side, (0.11, 0.11, 0.34),
                     (sign * 0.25, 0.4, 1.26), rot=(-16, -sign * 28, 0),
                     color=GOLD, taper=0.5),
            bk.wedge("ear.%s.tip" % side, (0.07, 0.07, 0.18),
                     (sign * 0.33, 0.52, 1.45), rot=(-52, -sign * 30, 0),
                     color=GOLD_BRIGHT, taper=0.8),
        ]
        merged = kit.join(parts, "ear.%s" % side)
        kit.weld(merged)
        kit.set_origin_to(merged, base)
        horns.append(merged)

    legs = bk.legs_quad("leg", front=(0.19, 0.22, 0.36), back=(0.2, -0.28, 0.36),
                        length=0.32, thickness=0.155, color=hide,
                        foot_color=stripe)
    tail_base = (0, -0.44, 0.66)
    tail_obj = bk.tail("tail", tail_base, length=0.44, thickness=0.12,
                       color=hide, style="segmented", segments=4, curl=0.55)
    tail_extra = []
    for i in range(3):
        tail_extra.append(bk.block("tail.band%d" % i, (0.155, 0.055, 0.155),
                                   (0, -0.53 - i * 0.11, 0.69 + i * 0.055),
                                   color=stripe))
    tail_extra.append(bk.glow_block("tail.flame", (0.11, 0.13, 0.18),
                                    (0, -0.9, 0.88), color="#ff7a3c",
                                    strength=3.2))

    groups = {
        "body": (body, (0, -0.1, 0.36)),
        "head": (head, (0, 0.36, 0.74)),
        "ear.L": ([horns[0]], tuple(horns[0].location)),
        "ear.R": ([horns[1]], tuple(horns[1].location)),
        "tail": ([tail_obj] + tail_extra, tail_base),
    }
    for key, obj in legs.items():
        groups[key] = ([obj], tuple(obj.location))
    bk.assemble(root, groups)
    return bk.finish(root)


PETS = {
    "crane": build_crane,
    "salamander": build_salamander,
    "red-panda": build_red_panda,
    "snowy-owl": build_snowy_owl,
    "koi": build_koi,
    "stag": build_stag,
    "kitsune": build_kitsune,
    "oni-tiger": build_oni_tiger,
}
