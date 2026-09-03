"""
Hollowfrost Shelf -- the eight snow pets.

Palette discipline for the whole biome: bone white, pale ice blue, slate grey,
deep navy shadow, and a single cyan that only the charged pets are allowed to
emit. The two mythics deliberately break toward cold brown so the shelf does
not read as eight white boxes in a row -- a mammoth next to a polar bear has to
be tellable apart at icon size, and hue is the cheapest way to do that.

Conventions inherited from pets_forest:
  * Build facing +Y, feet near z = 0, `bk.finish()` normalises the height.
  * Only the runtime's part names appear in `bk.assemble`.
  * The head pivots at the neck, ears at the skull, tails at their base.
  * Silhouette first. Every creature here owns one shape you could pick out
    of a lineup as a black cut-out: the penguin's upright teardrop, the
    walrus's hanging tusks, the sabertooth's shoulder hump, the mammoth's
    trunk-and-tusk arc, the yeti's knuckle-dragging arms, the dragon's wings.
"""

import math

import blockkit as bk
import kit


# ---------------------------------------------------------------------------
# shared helper
# ---------------------------------------------------------------------------

def _curved_horn(name, base, length, thickness, color, start=180.0, sweep=90.0,
                 segments=4, splay=0.0, taper_to=0.5, material=None):
    """
    A tusk, fang or horn swept as a chain of shrinking blocks.

    Four of the eight pets here hang something curved off the face, and doing
    it by hand four times is how the numbers drift apart. Each segment is
    rotated a little further around X than the last and placed at the end of
    the previous one, so the chain arcs.

    `start` is the heading in degrees (0 = straight up, 180 = straight down,
    270 = straight forward); `sweep` is how far it turns over its length;
    `splay` drifts the chain sideways in X as it grows. Blocks stay axis
    aligned in X on purpose -- at this scale a stack of boxes reads as a curve
    and a properly banked chain just costs geometry.
    """
    parts = []
    cx, cy, cz = base
    seg = length / float(segments)
    step = splay / float(segments)
    for i in range(segments):
        t = i / float(max(1, segments - 1))
        angle = math.radians(start + sweep * t)
        dy, dz = -math.sin(angle), math.cos(angle)
        size = thickness * (1.0 - (1.0 - taper_to) * (i / float(segments)))
        parts.append(bk.block(
            "%s.%d" % (name, i), (size, size, seg * 1.2),
            (cx + step * 0.5, cy + dy * seg * 0.5, cz + dz * seg * 0.5),
            rot=(math.degrees(angle), 0, 0), color=color, material=material,
        ))
        cx += step
        cy += dy * seg
        cz += dz * seg
    return parts


# ---------------------------------------------------------------------------
# Penguin -- Rare, $140/s. The shelf's starter: an upright navy teardrop.
# ---------------------------------------------------------------------------

def build_penguin():
    kit.reset_scene()
    root = kit.empty("root")

    coat = "#2b3346"        # deep navy shadow
    belly_c = "#f6fafd"
    bill = "#f2a03c"        # the one warm accent in the biome, and it earns it
    plume = "#a9dcf0"

    # Tall and narrow: the penguin is the only upright bird here, so the
    # silhouette has to be a standing column, not the forest bird's ball.
    body_dims = (0.34, 0.30, 0.50)
    body_at = (0, -0.01, 0.42)
    body = [bk.block("body.core", body_dims, body_at, color=coat)]
    body += bk.belly("body.front", body_at, body_dims, color=belly_c, inset=0.94)
    # A narrower shoulder block lifts the head clear of the barrel instead of
    # letting the two merge into one lump.
    body.append(bk.block("body.shoulders", (0.22, 0.22, 0.11),
                         (0, 0.02, 0.70), color=coat))

    head_dims = (0.26, 0.24, 0.24)
    head_at = (0, 0.06, 0.86)
    head = [bk.block("head.skull", head_dims, head_at, color=coat)]
    face = bk.face_of(head_at, head_dims, "front")
    # White face mask: the single marking that says "penguin" at icon size.
    head.append(bk.face_plate("head.mask", face, (0.2, 0.15), face="front",
                              color=belly_c, depth=0.014, offset=(0, -0.03)))
    head += bk.eyes("head.eye", head_at, head_dims, spacing=0.54, height=0.045,
                    size=0.055, style="white", iris="#151b28", pupil_scale=0.6)
    head += bk.beak("head.beak", head_at, head_dims, width=0.08, length=0.15,
                    height=0.07, color=bill, drop=-0.05)
    # Rockhopper-style crest plumes, swept back in pale ice. Cheap, and it
    # stops the head being a plain cube from every angle.
    for side, sign in (("L", 1), ("R", -1)):
        head.append(bk.wedge(
            "head.plume.%s" % side, (0.04, 0.04, 0.17),
            (sign * 0.11, head_at[1] - 0.07, head_at[2] + 0.13),
            rot=(48, sign * 22, 0), color=plume, taper=0.85,
        ))

    # Flippers, not wings: a narrow span and a tall drop.
    wing_l, wing_r = bk.wings_flat("wing", (0.17, 0.0, 0.52), span=0.09,
                                   height=0.36, thickness=0.06, color=coat,
                                   tip_color=plume, layers=2, tilt=6)
    tail_obj = bk.tail("tail", (0, -0.15, 0.23), length=0.16, thickness=0.09,
                       color=coat, style="flat", segments=2, curl=0.25)
    legs = bk.bird_feet("leg", (0.08, 0.02, 0.17), shin=0.13, thickness=0.055,
                        toe=0.18, color=bill)

    groups = {
        "body": (body, (0, 0, 0.2)),
        "head": (head, (0, 0.0, 0.74)),
        "wing.L": ([wing_l], tuple(wing_l.location)),
        "wing.R": ([wing_r], tuple(wing_r.location)),
        "tail": ([tail_obj], (0, -0.15, 0.23)),
    }
    for key, obj in legs.items():
        groups[key] = ([obj], tuple(obj.location))
    bk.assemble(root, groups)
    return bk.finish(root)


# ---------------------------------------------------------------------------
# Walrus -- Epic, $600/s. Blubber, whiskers, and two tusks doing the talking.
# ---------------------------------------------------------------------------

def build_walrus():
    kit.reset_scene()
    root = kit.empty("root")

    hide = "#77808f"        # slate back
    pale = "#9fabba"        # the underside, two steps lighter
    muzzle_c = "#c3ccd7"
    ivory = "#f3ecd9"
    dark = "#232c3d"

    # A blob that is mostly front. The walrus's whole read is a huge face
    # with tusks, so the torso is kept short and the head is the biggest
    # single mass on the model -- earlier passes gave it a long body and a
    # small cube head, and it came out looking like freight with a snout.
    body = []
    for i, (dims, loc) in enumerate((
        ((0.52, 0.34, 0.46), (0, -0.02, 0.34)),
        ((0.44, 0.28, 0.36), (0, -0.32, 0.28)),
        ((0.3, 0.24, 0.26), (0, -0.56, 0.24)),
    )):
        body.append(bk.block("body.seg%d" % i, dims, loc, color=hide))
    # Pale underside hung BELOW the segments rather than tucked inside them.
    # Flush with the hull it was invisible and the animal was one flat grey.
    body.append(bk.block("body.underside", (0.5, 0.86, 0.13),
                         (0, -0.24, 0.1), color=pale))
    # Blubber creases gathered at the shoulders.
    for i, dy in enumerate((0.11, 0.0)):
        body.append(bk.block("body.fold%d" % i, (0.53, 0.05, 0.44),
                             (0, dy, 0.35), color=pale))

    head_dims = (0.42, 0.28, 0.34)
    head_at = (0, 0.34, 0.6)
    head = [bk.block("head.skull", head_dims, head_at, color=hide)]
    # The muzzle pad is WIDER than the skull. That overhang is the feature
    # that says walrus before the tusks are even read.
    muzzle_dims = (0.46, 0.24, 0.24)
    muzzle_at = (0, 0.52, 0.5)
    head.append(bk.block("head.muzzle", muzzle_dims, muzzle_at, color=muzzle_c))
    head += bk.nostrils("head.nostril", muzzle_at, muzzle_dims, spacing=0.24,
                        height=0.06, size=0.04, color=dark)
    # Whisker studs painted on the pad. Whiskers modelled as bars sticking out
    # of the sides of the muzzle read as antennae, so they went back to dots.
    pad = bk.face_of(muzzle_at, muzzle_dims, "front")
    for side, sign in (("L", 1), ("R", -1)):
        for i, (du, dv) in enumerate(((0.055, -0.02), (0.11, -0.005),
                                      (0.075, -0.06))):
            head.append(bk.face_plate(
                "head.whisker.%s%d" % (side, i), pad, (0.028, 0.028),
                face="front", color=dark, depth=0.012,
                offset=(sign * du, dv),
            ))
    head += bk.eyes("head.eye", head_at, head_dims, spacing=0.6, height=0.1,
                    size=0.05, style="white", iris="#141a26", pupil_scale=0.62)
    # A lip block under the pad, so the tusks visibly grow out of a jaw. Hung
    # off nothing, in a wide-set pair, they read as a second set of legs.
    head.append(bk.block("head.lip", (0.34, 0.2, 0.1), (0, 0.5, 0.36),
                         color=muzzle_c))
    for side, sign in (("L", 1), ("R", -1)):
        head += _curved_horn("head.tusk.%s" % side,
                             (sign * 0.105, 0.53, 0.36), length=0.32,
                             thickness=0.085, color=ivory, start=186, sweep=-22,
                             segments=3, splay=sign * 0.035, taper_to=0.2)

    # Front flippers: stubby paddles propping the chest up off the ice, set
    # well forward so the front view has something under the chin besides
    # tusks. Thin plates on the ribs looked like panels; these have thickness.
    paddle = bk.slab("fin", (0.26, 0.32, 0.11), (0.29, 0.12, 0.11),
                     rot=(0, -28, -12), color=hide)
    kit.set_origin_to(paddle, (0.23, 0.16, 0.26))
    fin_l, fin_r = kit.mirrored_pair(paddle, "fin")
    fin_tail_obj = bk.fin_tail("fin.tail", (0, -0.7, 0.19), size=0.34,
                               thickness=0.08, color=pale, lobes=2)

    groups = {
        "body": (body, (0, -0.1, 0.1)),
        "head": (head, (0, 0.22, 0.46)),
        "fin.L": ([fin_l], tuple(fin_l.location)),
        "fin.R": ([fin_r], tuple(fin_r.location)),
        "fin.tail": ([fin_tail_obj], (0, -0.7, 0.19)),
    }
    bk.assemble(root, groups)
    return bk.finish(root)


# ---------------------------------------------------------------------------
# Polar Bear -- Legendary, $7K/s. Bulk plus the first frost crystals.
# ---------------------------------------------------------------------------

def build_polar_bear():
    kit.reset_scene()
    root = kit.empty("root")

    fur = "#f4f8fb"
    shade = "#d6e5f0"
    nose_c = "#232c3d"
    frost = "#a8dcf0"
    glow = "#7fe6ff"

    body_dims = (0.54, 0.66, 0.46)
    body_at = (0, -0.05, 0.52)
    body = [bk.block("body.core", body_dims, body_at, color=fur)]
    body += bk.belly("body.chest", body_at, body_dims, color=shade, inset=0.6)
    # Low neck carried forward -- a polar bear's head hangs off the front of
    # the shoulders rather than sitting on top of them.
    body.append(bk.block("body.neck", (0.3, 0.2, 0.28),
                         (0, 0.34, 0.66), color=fur))
    body.append(bk.block("body.haunch", (0.5, 0.22, 0.4), (0, -0.32, 0.5),
                         color=fur))
    body += bk.spots("body.rime", body_at, body_dims, count=5, size=0.07,
                     color=shade, seed=17, faces=("top", "left", "right"))
    # Legendary signature: three ice shards frozen along the spine. Big enough
    # to break the back line -- at half this size they vanished into the fur.
    for i, (dy, h) in enumerate(((0.12, 0.2), (-0.06, 0.26), (-0.24, 0.18))):
        body.append(bk.wedge("body.shard%d" % i, (0.08, 0.1, h),
                             (0, dy, 0.75 + h * 0.42), rot=(-8, 0, 0),
                             color=frost, taper=0.78))
    body += bk.gem("body.core_gem.L", (0.22, 0.14, 0.74), size=0.09,
                   color=glow, strength=2.4)
    body += bk.gem("body.core_gem.R", (-0.22, 0.14, 0.74), size=0.09,
                   color=glow, strength=2.4)

    head_dims = (0.34, 0.3, 0.28)
    head_at = (0, 0.5, 0.72)
    head = [bk.block("head.skull", head_dims, head_at, color=fur)]
    head += bk.snout("head.snout", head_at, head_dims, width=0.2, length=0.19,
                     height=0.15, color=shade, drop=-0.06, nose_color=nose_c)
    head += bk.eyes("head.eye", head_at, head_dims, spacing=0.5, height=0.08,
                    size=0.06, style="white", iris="#141a26", pupil_scale=0.58)
    ear_l, ear_r = bk.ears_box("ear", head_at, head_dims, size=0.11,
                               spacing=0.68, depth=0.07, color=fur,
                               inner_color=shade)

    legs = bk.legs_quad("leg", front=(0.19, 0.19, 0.34), back=(0.2, -0.24, 0.34),
                        length=0.32, thickness=0.16, color=fur, foot_color=shade)
    tail_obj = bk.tail("tail", (0, -0.38, 0.56), length=0.1, thickness=0.11,
                       color=fur, style="puff", segments=1, curl=0.2)

    groups = {
        "body": (body, (0, 0, 0.3)),
        "head": (head, (0, 0.36, 0.6)),
        "ear.L": ([ear_l], tuple(ear_l.location)),
        "ear.R": ([ear_r], tuple(ear_r.location)),
        "tail": ([tail_obj], (0, -0.38, 0.56)),
    }
    for key, obj in legs.items():
        groups[key] = ([obj], tuple(obj.location))
    bk.assemble(root, groups)
    return bk.finish(root)


# ---------------------------------------------------------------------------
# Sabertooth Tiger -- Mythic, $35K/s.
# Two enormous downward fangs, a prowling shoulder hump, and a head carried
# LOW. Everything else on the shelf stands tall; this one stalks.
# ---------------------------------------------------------------------------

def build_sabertooth_tiger():
    kit.reset_scene()
    root = kit.empty("root")

    coat = "#cfe0ec"
    ruff = "#f4fafd"
    stripe = "#3d4b61"      # dark enough to carry across a pale coat
    ivory = "#f7f8f4"       # bone, not tan: tan fangs read as a second pair of legs
    glow = "#7fe6ff"
    paw = "#39465a"

    body_dims = (0.4, 0.62, 0.36)
    body_at = (0, -0.08, 0.5)
    body = [bk.block("body.core", body_dims, body_at, color=coat)]
    # Stripes as narrow bands. The first pass used full-width wraps and the
    # torso read as an exposed ribcage rather than a striped cat.
    body += bk.stripes("body.stripe", body_at, body_dims, count=4, width=0.042,
                       color=stripe, axis="y")
    body += bk.belly("body.chest", body_at, body_dims, color=ruff, inset=0.55)
    # The hump, and behind it a back line that slopes away to a low rump. The
    # sabertooth is the only quadruped here whose spine is not level.
    body.append(bk.block("body.hump", (0.44, 0.3, 0.22),
                         (0, 0.13, 0.72), color=coat))
    body.append(bk.block("body.rump", (0.38, 0.2, 0.32),
                         (0, -0.34, 0.46), color=coat))
    body.append(bk.block("body.neck", (0.28, 0.2, 0.24),
                         (0, 0.32, 0.6), color=coat))
    # Frost shards riding the hump -- the mythic charge.
    for i, dx in enumerate((-0.12, 0.0, 0.12)):
        body.append(bk.wedge("body.shard%d" % i, (0.06, 0.07, 0.18 - abs(dx)),
                             (dx, 0.12, 0.86), rot=(-14, 0, 0),
                             color="#bfe4f2", taper=0.82))

    head_dims = (0.32, 0.26, 0.27)
    head_at = (0, 0.46, 0.58)
    head = [bk.block("head.skull", head_dims, head_at, color=coat)]
    head += bk.snout("head.snout", head_at, head_dims, width=0.19, length=0.13,
                     height=0.13, color=ruff, drop=-0.05, nose_color="#2a3446")
    head += bk.eyes("head.eye", head_at, head_dims, spacing=0.54, height=0.07,
                    size=0.06, style="glow", iris=glow)
    # A slate brow bar over the glow, so the eyes read as a scowl not a lamp.
    head.append(bk.face_plate("head.brow", bk.face_of(head_at, head_dims, "front"),
                              (0.28, 0.045), face="front", color=stripe,
                              depth=0.02, offset=(0, 0.115)))
    head.append(bk.block("head.chin", (0.15, 0.14, 0.09), (0, 0.6, 0.46),
                         color=ruff))
    # Cheek ruff: two swept fur wedges. A full mane ring turned into a spiky
    # collar that swallowed the head.
    for side, sign in (("L", 1), ("R", -1)):
        head.append(bk.wedge("head.ruff.%s" % side, (0.1, 0.16, 0.22),
                             (sign * 0.19, head_at[1] - 0.02, head_at[2] - 0.03),
                             rot=(0, sign * 52, 0), color=ruff, taper=0.55))
    ear_l, ear_r = bk.ears_pointed("ear", head_at, head_dims, size=0.11,
                                   spacing=0.64, length=0.17, color=coat,
                                   inner_color=stripe, lean=10)
    # The fangs. Long enough to pass the jawline by half a head, curving back
    # under the chin -- if they were short this would just be a snow leopard.
    for side, sign in (("L", 1), ("R", -1)):
        head += _curved_horn("head.fang.%s" % side, (sign * 0.088, 0.585, 0.5),
                             length=0.27, thickness=0.09, color=ivory,
                             start=178, sweep=-30, segments=3,
                             splay=sign * 0.035, taper_to=0.18)

    legs = bk.legs_quad("leg", front=(0.15, 0.19, 0.34), back=(0.16, -0.24, 0.34),
                        length=0.32, thickness=0.115, color=coat, foot_color=paw)
    tail_obj = bk.tail("tail", (0, -0.36, 0.54), length=0.36, thickness=0.1,
                       color=coat, style="taper", tip_color=stripe, segments=4,
                       curl=0.6)

    groups = {
        "body": (body, (0, 0, 0.3)),
        "head": (head, (0, 0.34, 0.5)),
        "ear.L": ([ear_l], tuple(ear_l.location)),
        "ear.R": ([ear_r], tuple(ear_r.location)),
        "tail": ([tail_obj], (0, -0.36, 0.54)),
    }
    for key, obj in legs.items():
        groups[key] = ([obj], tuple(obj.location))
    bk.assemble(root, groups)
    return bk.finish(root)


# ---------------------------------------------------------------------------
# Mammoth -- Mythic, $42K/s.
# Cold brown on purpose: at icon size a white mammoth and a white polar bear
# are the same blob. Trunk, curved tusks and a shaggy skirt do the rest.
# ---------------------------------------------------------------------------

def build_mammoth():
    kit.reset_scene()
    root = kit.empty("root")

    wool = "#6f5b4c"
    wool_dark = "#54443a"
    frost = "#cfe3ee"
    ivory = "#efe6cf"
    hide = "#4a3c34"

    body_dims = (0.56, 0.64, 0.5)
    body_at = (0, -0.08, 0.56)
    body = [bk.block("body.core", body_dims, body_at, color=wool)]
    # High shoulder hump into a sloping back -- the mammoth profile.
    body.append(bk.block("body.hump", (0.48, 0.3, 0.2), (0, 0.1, 0.86),
                         color=wool))
    body.append(bk.block("body.rump", (0.46, 0.16, 0.34), (0, -0.36, 0.52),
                         color=wool_dark))
    # Shaggy skirt: hanging fur slats along both flanks. This is the shape that
    # makes the silhouette woolly rather than merely large.
    for i, dy in enumerate((0.12, -0.04, -0.22)):
        for side, sign in (("L", 1), ("R", -1)):
            body.append(bk.block(
                "body.shag.%s%d" % (side, i), (0.07, 0.16, 0.24),
                (sign * 0.28, dy, 0.34), color=wool_dark,
            ))
    body += bk.spots("body.frost", body_at, body_dims, count=5, size=0.07,
                     color=frost, seed=23, faces=("top", "left", "right"))

    head_dims = (0.38, 0.28, 0.32)
    head_at = (0, 0.44, 0.84)
    head = [bk.block("head.skull", head_dims, head_at, color=wool)]
    # Domed crown: elephants and mammoths are read from that twin dome.
    head.append(bk.block("head.crown", (0.3, 0.24, 0.15), (0, 0.42, 1.05),
                         color=wool))
    head += bk.eyes("head.eye", head_at, head_dims, spacing=0.62, height=0.06,
                    size=0.05, style="white", iris="#1c1510", pupil_scale=0.6)
    # Trunk: five shrinking blocks dropping off the face and curling forward.
    trunk = (
        ((0.18, 0.18, 0.16), (0, 0.58, 0.7), (0, 0, 0)),
        ((0.16, 0.16, 0.15), (0, 0.6, 0.55), (-8, 0, 0)),
        ((0.14, 0.15, 0.14), (0, 0.62, 0.42), (-16, 0, 0)),
        ((0.12, 0.15, 0.13), (0, 0.66, 0.3), (-40, 0, 0)),
        ((0.1, 0.13, 0.11), (0, 0.74, 0.24), (-72, 0, 0)),
    )
    for i, (dims, loc, rot) in enumerate(trunk):
        head.append(bk.block("head.trunk%d" % i, dims, loc, rot=rot,
                             color=wool if i < 3 else hide))
    for side, sign in (("L", 1), ("R", -1)):
        head += _curved_horn("head.tusk.%s" % side, (sign * 0.16, 0.52, 0.62),
                             length=0.46, thickness=0.1, color=ivory,
                             start=175, sweep=115, segments=4,
                             splay=sign * 0.07, taper_to=0.42)
    ear_l, ear_r = bk.ears_floppy("ear", head_at, head_dims, size=0.13,
                                  spacing=1.02, length=0.18, color=hide,
                                  droop=26)

    legs = bk.legs_quad("leg", front=(0.2, 0.18, 0.36), back=(0.21, -0.26, 0.36),
                        length=0.34, thickness=0.17, color=wool_dark,
                        foot_color=hide)
    tail_obj = bk.tail("tail", (0, -0.42, 0.6), length=0.2, thickness=0.07,
                       color=wool_dark, style="whip", tip_color=hide,
                       segments=2, curl=0.2)

    groups = {
        "body": (body, (0, 0, 0.32)),
        "head": (head, (0, 0.32, 0.7)),
        "ear.L": ([ear_l], tuple(ear_l.location)),
        "ear.R": ([ear_r], tuple(ear_r.location)),
        "tail": ([tail_obj], (0, -0.42, 0.6)),
    }
    for key, obj in legs.items():
        groups[key] = ([obj], tuple(obj.location))
    bk.assemble(root, groups)
    return bk.finish(root)


# ---------------------------------------------------------------------------
# King Mammoth -- Cosmic, $400K/s.
# The mammoth again, but night-blue, plated in ice crystal, wearing a frozen
# crown and trailing a glowing ring. Cosmic has to look like money.
# ---------------------------------------------------------------------------

def build_king_mammoth():
    kit.reset_scene()
    root = kit.empty("root")

    # Night-blue rather than black: the first pass used a near-navy coat and
    # the whole model sank into the background, which is a bad look for the
    # second most expensive pet on the shelf.
    wool = "#4d5d80"
    wool_dark = "#36425c"
    armour = "#d2eefb"
    armour_deep = "#89c3e2"
    ivory = "#f4f8fc"
    glow = "#74e9ff"

    body_dims = (0.6, 0.68, 0.52)
    body_at = (0, -0.08, 0.6)
    body = [bk.block("body.core", body_dims, body_at, color=wool)]
    body.append(bk.block("body.hump", (0.52, 0.32, 0.22), (0, 0.1, 0.92),
                         color=wool))
    body.append(bk.block("body.rump", (0.5, 0.16, 0.36), (0, -0.38, 0.56),
                         color=wool_dark))
    for i, dy in enumerate((0.1, -0.08, -0.26)):
        for side, sign in (("L", 1), ("R", -1)):
            body.append(bk.block(
                "body.shag.%s%d" % (side, i), (0.08, 0.16, 0.26),
                (sign * 0.3, dy, 0.36), color=wool_dark,
            ))
    # Armour: a saddle plate over the hump, a pauldron each side, and a row of
    # crystal spikes down the spine.
    body.append(bk.slab("body.saddle", (0.5, 0.34, 0.07), (0, 0.08, 1.06),
                        color=armour))
    for side, sign in (("L", 1), ("R", -1)):
        body.append(bk.block("body.pauldron.%s" % side, (0.12, 0.3, 0.26),
                             (sign * 0.31, 0.1, 0.86), rot=(0, sign * 14, 0),
                             color=armour_deep))
    for i, dy in enumerate((-0.06, -0.22, -0.38)):
        body.append(bk.wedge("body.spike%d" % i, (0.08, 0.1, 0.24 - 0.04 * i),
                             (0, dy, 1.0 - 0.06 * i), rot=(-10, 0, 0),
                             color=armour, taper=0.84))
    body += bk.gem("body.heart", (0, 0.28, 0.72), size=0.13, color=glow,
                   strength=3.2)

    head_dims = (0.4, 0.3, 0.34)
    head_at = (0, 0.46, 0.9)
    head = [bk.block("head.skull", head_dims, head_at, color=wool)]
    head.append(bk.block("head.crown_dome", (0.32, 0.26, 0.16), (0, 0.44, 1.12),
                         color=wool))
    # The frozen crown: a band around the dome carrying five ice teeth. The
    # band matters -- five loose spikes read as bed-head, a band reads as a
    # crown.
    head.append(bk.block("head.crownband", (0.34, 0.28, 0.06),
                         (0, 0.46, 1.22), color=armour_deep))
    for i, (dx, dy, h) in enumerate((
        (-0.15, 0.45, 0.15), (-0.08, 0.53, 0.22), (0.0, 0.57, 0.3),
        (0.08, 0.53, 0.22), (0.15, 0.45, 0.15),
    )):
        head.append(bk.glow_block("head.crown%d" % i, (0.085, 0.085, h),
                                  (dx, dy, 1.25 + h * 0.45), color="#a9e8fb",
                                  strength=1.5))
    head += bk.eyes("head.eye", head_at, head_dims, spacing=0.6, height=0.06,
                    size=0.055, style="glow", iris=glow)
    trunk = (
        ((0.18, 0.18, 0.16), (0, 0.61, 0.74), (0, 0, 0)),
        ((0.16, 0.16, 0.16), (0, 0.63, 0.59), (-8, 0, 0)),
        ((0.14, 0.15, 0.15), (0, 0.65, 0.45), (-16, 0, 0)),
        ((0.12, 0.15, 0.13), (0, 0.69, 0.33), (-40, 0, 0)),
        ((0.1, 0.13, 0.11), (0, 0.77, 0.28), (-70, 0, 0)),
    )
    for i, (dims, loc, rot) in enumerate(trunk):
        head.append(bk.block("head.trunk%d" % i, dims, loc, rot=rot,
                             color=wool if i < 3 else wool_dark))
    # A band of ice locked around the trunk.
    head.append(bk.block("head.trunkband", (0.18, 0.06, 0.06),
                         (0, 0.63, 0.58), color=armour_deep))
    for side, sign in (("L", 1), ("R", -1)):
        head += _curved_horn("head.tusk.%s" % side, (sign * 0.17, 0.54, 0.66),
                             length=0.54, thickness=0.115, color=ivory,
                             start=175, sweep=120, segments=4,
                             splay=sign * 0.08, taper_to=0.4)
        # Glowing fracture lines cut into each tusk.
        head.append(bk.glow_block("head.tuskglow.%s" % side, (0.05, 0.05, 0.05),
                                  (sign * 0.19, 0.66, 0.4), color=glow,
                                  strength=2.6))
    ear_l, ear_r = bk.ears_floppy("ear", head_at, head_dims, size=0.14,
                                  spacing=1.02, length=0.2, color=wool_dark,
                                  droop=26)

    legs = bk.legs_quad("leg", front=(0.22, 0.18, 0.38), back=(0.23, -0.28, 0.38),
                        length=0.38, thickness=0.18, color=wool_dark,
                        foot_color=armour_deep)
    tail_obj = bk.tail("tail", (0, -0.44, 0.64), length=0.22, thickness=0.08,
                       color=wool_dark, style="whip", tip_color=armour,
                       segments=2, curl=0.2)
    # A frost halo hanging flat above the crown. Tilted on edge it just looked
    # like a hoop someone had thrown; flat and horizontal it reads as regalia.
    halo = bk.ring("head.halo", (0, 0.46, 1.62), radius=0.28, thickness=0.022,
                   tilt=0, color=glow, strength=2.4)

    groups = {
        "body": (body, (0, 0, 0.34)),
        "head": (head + halo, (0, 0.32, 0.74)),
        "ear.L": ([ear_l], tuple(ear_l.location)),
        "ear.R": ([ear_r], tuple(ear_r.location)),
        "tail": ([tail_obj], (0, -0.44, 0.64)),
    }
    for key, obj in legs.items():
        groups[key] = ([obj], tuple(obj.location))
    bk.assemble(root, groups)
    return bk.finish(root)


# ---------------------------------------------------------------------------
# Yeti -- Secret, $5M/s.
# The only biped on the shelf. Huge shoulders, knuckle-dragging arms, tiny
# legs, blue skin showing through the fur, and eyes that light the snow.
# ---------------------------------------------------------------------------

def build_yeti():
    kit.reset_scene()
    root = kit.empty("root")

    fur = "#eef5fa"
    fur_shade = "#c9dcea"
    skin = "#5f9cc0"
    skin_dark = "#3f7597"
    glow = "#9ff4ff"
    maw = "#16202e"

    # Triangle of mass: a broad shoulder yoke over an enormous chest, a
    # narrow waist, and short legs. Every edge gets a fur tuft hung off it,
    # because clean rectangles on a white body read as a machine.
    chest_dims = (0.66, 0.42, 0.44)
    chest_at = (0, 0.0, 0.9)
    body = [bk.block("body.chest", chest_dims, chest_at, color=fur)]
    body.append(bk.block("body.yoke", (0.8, 0.36, 0.16), (0, -0.01, 1.14),
                         color=fur))
    body.append(bk.block("body.waist", (0.42, 0.34, 0.24), (0, -0.01, 0.57),
                         color=fur))

    # Bare blue hide across the chest, with fur creeping over its edges.
    chest_face = bk.face_of(chest_at, chest_dims, "front")
    body.append(bk.face_plate("body.hide", chest_face, (0.26, 0.34), face="front",
                              color=skin, depth=0.02, offset=(0, -0.02)))
    body.append(bk.face_plate("body.hide.dark", chest_face, (0.2, 0.1),
                              face="front", color=skin_dark, depth=0.016,
                              offset=(0.02, -0.14), proud=bk.PROUD * 3))
    for i, (dx, w, h) in enumerate(((-0.24, 0.14, 0.3), (0.24, 0.14, 0.3),
                                    (0.0, 0.16, 0.16))):
        body.append(bk.block("body.bib%d" % i, (w, 0.1, h),
                             (dx, chest_face[1] - 0.03, 1.02), color=fur))
    # Shaggy tufts around the whole shoulder line and hips.
    for i, (dx, dy, dz, s) in enumerate((
        (-0.36, 0.02, 1.18, 0.18), (-0.16, -0.1, 1.24, 0.15),
        (0.16, -0.1, 1.24, 0.15), (0.36, 0.02, 1.18, 0.18),
        (-0.3, 0.12, 1.02, 0.14), (0.3, 0.12, 1.02, 0.14),
    )):
        body.append(bk.wedge("body.tuft%d" % i, (s, s, s),
                             (dx, dy, dz), rot=(0, dx * 70, 0),
                             color=fur, taper=0.6))
    for side, sign in (("L", 1), ("R", -1)):
        body.append(bk.block("body.flank.%s" % side, (0.07, 0.28, 0.3),
                             (sign * 0.35, -0.02, 0.88), color=fur_shade))
        body.append(bk.block("body.hipfur.%s" % side, (0.1, 0.2, 0.16),
                             (sign * 0.22, -0.02, 0.6), color=fur_shade))
        # A fur cap over each shoulder socket, so the arm grows out of the
        # coat instead of being bolted to a flat side.
        body.append(bk.block("body.cap.%s" % side, (0.26, 0.28, 0.18),
                             (sign * 0.39, 0.0, 1.07), color=fur))
        # Ice spurs frozen into the shoulders -- the secret-tier charge.
        body.append(bk.glow_block("body.spur.%s" % side, (0.08, 0.1, 0.3),
                                  (sign * 0.36, -0.02, 1.34),
                                  rot=(0, sign * 26, 0), color="#bfe4f2",
                                  strength=1.6))

    head_dims = (0.44, 0.34, 0.3)
    head_at = (0, 0.1, 1.36)
    head = [bk.block("head.skull", head_dims, head_at, color=fur)]
    face = bk.face_of(head_at, head_dims, "front")
    # Bare blue face inside a fur frame. The plate is deliberately LESS proud
    # than the eyes that sit on it, or it buries them.
    head.append(bk.face_plate("head.face", face, (0.34, 0.24), face="front",
                              color=skin, depth=0.016, offset=(0, -0.02)))
    head += bk.eyes("head.eye", head_at, head_dims, spacing=0.5, height=0.03,
                    size=0.085, style="glow", iris=glow)
    # Brow ridge sits ABOVE the eyes and juts forward; a shelf, not a visor.
    head.append(bk.block("head.brow", (0.42, 0.12, 0.09),
                         (0, head_at[1] + 0.14, head_at[2] + 0.13), color=fur))
    # Heavy underbite jaw slung forward in bare blue skin.
    jaw_dims = (0.3, 0.22, 0.15)
    jaw_at = (0, head_at[1] + 0.13, head_at[2] - 0.2)
    head.append(bk.block("head.jaw", jaw_dims, jaw_at, color=skin))
    head += bk.mouth("head.mouth", jaw_at, jaw_dims, width=0.2, height=0.035,
                     drop=0.005, color=maw, style="open", teeth=4,
                     teeth_color="#f6fbff")
    for side, sign in (("L", 1), ("R", -1)):
        head.append(bk.wedge("head.fang.%s" % side, (0.04, 0.04, 0.09),
                             (sign * 0.075, jaw_at[1] + 0.08, jaw_at[2] + 0.09),
                             color="#f6fbff", taper=0.75))
        # Cheek fur swept out sideways -- the beard that frames the face.
        head.append(bk.wedge("head.cheek.%s" % side, (0.14, 0.2, 0.2),
                             (sign * 0.24, head_at[1] - 0.02, head_at[2] - 0.1),
                             rot=(0, sign * 54, 0), color=fur, taper=0.5))
    for i, dx in enumerate((-0.13, 0.0, 0.13)):
        head.append(bk.wedge("head.crown%d" % i, (0.12, 0.15, 0.16 - abs(dx)),
                             (dx, head_at[1] - 0.04, head_at[2] + 0.2),
                             rot=(-16, dx * 60, 0), color=fur, taper=0.55))

    # Knuckle-draggers: the arms have to reach past the knees or the whole
    # ape silhouette collapses into a snowman.
    arm_l, arm_r = bk.arms("arm", (0.4, 0.0, 1.04), length=0.8, thickness=0.2,
                           color=fur, hand_color=skin_dark, angle=11)
    legs = bk.legs_pair("leg", (0.18, 0.0, 0.44), length=0.4, thickness=0.21,
                        color=fur, foot_color=skin_dark, foot_length=0.32)

    groups = {
        "body": (body, (0, 0, 0.44)),
        "head": (head, (0, 0.0, 1.2)),
        "arm.L": ([arm_l], tuple(arm_l.location)),
        "arm.R": ([arm_r], tuple(arm_r.location)),
    }
    for key, obj in legs.items():
        groups[key] = ([obj], tuple(obj.location))
    bk.assemble(root, groups)
    return bk.finish(root)


# ---------------------------------------------------------------------------
# Ice Dragon -- Eternal, $65M/s.
# The showpiece. Crystalline plating, a long neck, pale membrane wings, a
# spined tail, and frost vents that glow along the throat.
# ---------------------------------------------------------------------------

def build_ice_dragon():
    kit.reset_scene()
    root = kit.empty("root")

    scale_c = "#a9d9ef"
    scale_deep = "#4f8cb6"
    membrane = "#dbf1fc"
    crystal = "#eaf9ff"
    glow = "#7ff0ff"
    maw = "#1d3550"

    body_dims = (0.42, 0.58, 0.38)
    body_at = (0, -0.1, 0.64)
    body = [bk.block("body.core", body_dims, body_at, color=scale_c)]
    body.append(bk.block("body.chest", (0.44, 0.26, 0.38), (0, 0.2, 0.68),
                         color=scale_c))
    body += bk.belly("body.plates", (0, 0.06, 0.62), (0.42, 0.5, 0.36),
                     color=membrane, inset=0.66)
    # Neck: three shrinking blocks climbing forward, so the head ends up well
    # clear of the shoulders instead of bolted to them.
    for i, (dims, loc) in enumerate((
        ((0.26, 0.24, 0.24), (0, 0.36, 0.86)),
        ((0.23, 0.22, 0.22), (0, 0.46, 1.02)),
        ((0.2, 0.2, 0.2), (0, 0.54, 1.16)),
    )):
        body.append(bk.block("body.neck%d" % i, dims, loc, color=scale_c))
    # Frost vents: glowing slits down the throat and across the chest. These
    # are the "breath" the brief asks for -- lit from inside, not a plume.
    for i, (dy, dz, w) in enumerate(((0.42, 0.96, 0.11), (0.34, 0.82, 0.13),
                                     (0.26, 0.7, 0.14))):
        body.append(bk.glow_block("body.vent%d" % i, (w, 0.05, 0.035),
                                  (0, dy + 0.1, dz), color=glow, strength=3.0))
    body += bk.crest("body.spine", body_at, body_dims, count=5, height=0.17,
                     width=0.055, color=crystal, back=0.02)
    for side, sign in (("L", 1), ("R", -1)):
        body.append(bk.wedge("body.shoulderspur.%s" % side, (0.07, 0.1, 0.2),
                             (sign * 0.2, 0.14, 0.9), rot=(-16, sign * 26, 0),
                             color=crystal, taper=0.8))
    body += bk.gem("body.heart", (0, 0.32, 0.72), size=0.12, color=glow,
                   strength=3.4)

    head_dims = (0.24, 0.28, 0.22)
    head_at = (0, 0.68, 1.26)
    head = [bk.block("head.skull", head_dims, head_at, color=scale_c)]
    snout_dims = (0.17, 0.24, 0.14)
    snout_at = (0, 0.9, 1.21)
    head.append(bk.block("head.snout", snout_dims, snout_at, color=scale_deep))
    head.append(bk.slab("head.jaw", (0.15, 0.22, 0.05), (0, 0.9, 1.12),
                        color=maw))
    for i, dx in enumerate((-0.045, 0.0, 0.045)):
        head.append(bk.wedge("head.tooth%d" % i, (0.03, 0.03, 0.06),
                             (dx, 0.94, 1.09), rot=(180, 0, 0),
                             color="#f6fbff", taper=0.8))
    head += bk.nostrils("head.nostril", snout_at, snout_dims, spacing=0.4,
                        height=0.04, size=0.035, color=maw)
    head += bk.eyes("head.eye", head_at, head_dims, spacing=0.7, height=0.04,
                    size=0.06, style="glow", iris=glow, face="front")
    # Cheek fins and a pair of backswept crystal horns.
    for side, sign in (("L", 1), ("R", -1)):
        head.append(bk.wedge("head.cheekfin.%s" % side, (0.05, 0.1, 0.15),
                             (sign * 0.13, 0.62, 1.24), rot=(58, sign * 30, 0),
                             color=crystal, taper=0.8))
        head += _curved_horn("head.horn.%s" % side, (sign * 0.085, 0.6, 1.36),
                             length=0.3, thickness=0.065, color=crystal,
                             start=26, sweep=46, segments=3,
                             splay=sign * 0.05, taper_to=0.35)
    head.append(bk.block("head.brow", (0.26, 0.06, 0.05), (0, 0.78, 1.36),
                         color=scale_deep))

    # Wings big enough to be the first thing you see. An eternal pet whose
    # wings tuck inside its own outline is just a lizard.
    wing_l, wing_r = bk.wings_membrane("wing", (0.19, -0.06, 0.9), span=0.78,
                                       height=0.62, thickness=0.05,
                                       color=membrane, bone_color=scale_deep,
                                       fingers=3, tilt=18)
    # Sweep them back around the shoulder pivot. Straight out sideways they
    # looked like solar panels bolted to a lizard.
    for obj, sign in ((wing_l, 1), (wing_r, -1)):
        obj.rotation_euler = (math.radians(-6), math.radians(-sign * 10),
                              math.radians(-sign * 30))

    tail_obj = bk.tail("tail", (0, -0.38, 0.62), length=0.66, thickness=0.17,
                       color=scale_c, style="taper", tip_color=scale_deep,
                       segments=5, curl=0.42)
    # Crystal fins riding the tail, growing toward a blade at the tip.
    tail_fins = []
    for i, (dy, dz, h) in enumerate(((-0.52, 0.68, 0.13), (-0.72, 0.74, 0.16),
                                     (-0.92, 0.82, 0.2))):
        tail_fins.append(bk.wedge("tail.fin%d" % i, (0.05, 0.08, h),
                                  (0, dy, dz + h * 0.4), rot=(-26, 0, 0),
                                  color=crystal, taper=0.8))

    legs = bk.legs_quad("leg", front=(0.17, 0.2, 0.46), back=(0.19, -0.24, 0.46),
                        length=0.44, thickness=0.13, color=scale_deep,
                        foot_color=crystal)

    groups = {
        "body": (body, (0, 0, 0.4)),
        "head": (head, (0, 0.56, 1.16)),
        "wing.L": ([wing_l], tuple(wing_l.location)),
        "wing.R": ([wing_r], tuple(wing_r.location)),
        "tail": ([tail_obj] + tail_fins, (0, -0.4, 0.6)),
    }
    for key, obj in legs.items():
        groups[key] = ([obj], tuple(obj.location))
    bk.assemble(root, groups)
    return bk.finish(root)


PETS = {
    "penguin": build_penguin,
    "walrus": build_walrus,
    "polar-bear": build_polar_bear,
    "sabertooth-tiger": build_sabertooth_tiger,
    "mammoth": build_mammoth,
    "king-mammoth": build_king_mammoth,
    "yeti": build_yeti,
    "ice-dragon": build_ice_dragon,
}
