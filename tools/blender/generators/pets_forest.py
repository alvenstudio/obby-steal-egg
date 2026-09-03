"""
Whisperpine Forest -- the eight starter pets.

This module is the reference implementation every other biome follows. The
conventions that matter:

  * Build facing +Y. Feet near z = 0; `finish()` normalises the height.
  * Group parts under the runtime's animation names: body, head, ear.L/.R,
    wing.L/.R, arm.L/.R, leg.FL/.FR/.BL/.BR, tail, fin.L/.R, fin.tail.
  * Pivots matter more than geometry. A head that pivots at the neck reads as
    alive; one that pivots at its own centre reads as a bobbing box.
  * Silhouette first. These are seen at 1-2 metres in first person and as
    24px icons in the index, so the shape has to survive both.
"""

import blockkit as bk
import kit


# ---------------------------------------------------------------------------
# Chicken -- Common, $1/s. The very first pet, and the Forest guardian's kin.
# ---------------------------------------------------------------------------

def build_chicken():
    kit.reset_scene()
    root = kit.empty("root")

    feather = "#f4f1e8"
    comb = "#e0453c"
    beak = "#ffb02e"

    body_dims = (0.44, 0.5, 0.42)
    body_at = (0, -0.02, 0.36)
    body = [bk.block("body.core", body_dims, body_at, color=feather)]
    body += bk.belly("body.breast", body_at, body_dims, color="#ffffff", inset=0.7)
    # A stubby wing plate on each flank so the silhouette is not a plain box.
    wing_l, wing_r = bk.wings_flat("wing", (0.2, -0.02, 0.4), span=0.16,
                                   height=0.26, thickness=0.08, color=feather,
                                   tip_color="#ddd6c6", layers=2, tilt=4)

    head_dims = (0.3, 0.28, 0.28)
    head_at = (0, 0.16, 0.72)
    head = [bk.block("head.skull", head_dims, head_at, color=feather)]
    head += bk.eyes("head.eye", head_at, head_dims, spacing=0.62, height=0.05,
                    size=0.075, style="dot")
    head += bk.beak("head.beak", head_at, head_dims, width=0.1, length=0.13,
                    height=0.07, color=beak, drop=-0.04)
    # Comb: three rising blocks, the reference's exact idiom for a crest.
    for i, (dx, h) in enumerate(((-0.06, 0.06), (0.0, 0.09), (0.06, 0.065))):
        head.append(bk.block("head.comb%d" % i, (0.05, 0.09, h),
                             (dx, head_at[1] - 0.02, head_at[2] + 0.14 + h * 0.5),
                             color=comb))
    head.append(bk.block("head.wattle", (0.06, 0.05, 0.08),
                         (0, head_at[1] + 0.13, head_at[2] - 0.16), color=comb))

    tail = bk.tail("tail", (0, -0.26, 0.5), length=0.24, thickness=0.13,
                   color=feather, style="puff", tip_color="#ddd6c6", segments=2,
                   curl=0.55)

    legs = bk.bird_feet("leg", (0.09, 0.0, 0.16), shin=0.14, thickness=0.05,
                        toe=0.14, color=beak)

    groups = {
        "body": (body, (0, 0, 0.2)),
        "head": (head, (0, 0.06, 0.56)),
        "wing.L": ([wing_l], tuple(wing_l.location)),
        "wing.R": ([wing_r], tuple(wing_r.location)),
        "tail": ([tail], (0, -0.26, 0.5)),
    }
    for key, obj in legs.items():
        groups[key] = ([obj], tuple(obj.location))
    bk.assemble(root, groups)
    return bk.finish(root)


# ---------------------------------------------------------------------------
# Dog -- Common, $2/s.
# ---------------------------------------------------------------------------

def build_dog():
    kit.reset_scene()
    root = kit.empty("root")

    coat = "#c98a4e"
    cream = "#f0dcb8"
    dark = "#7a4f28"

    body_dims = (0.36, 0.56, 0.34)
    body_at = (0, -0.04, 0.44)
    body = [bk.block("body.core", body_dims, body_at, color=coat)]
    body += bk.belly("body.chest", body_at, body_dims, color=cream, inset=0.72)

    head_dims = (0.3, 0.26, 0.28)
    head_at = (0, 0.34, 0.62)
    head = [bk.block("head.skull", head_dims, head_at, color=coat)]
    head += bk.snout("head.snout", head_at, head_dims, width=0.17, length=0.16,
                     height=0.13, color=cream, drop=-0.05, nose_color="#2e2226")
    head += bk.eyes("head.eye", head_at, head_dims, spacing=0.56, height=0.07,
                    size=0.07, style="white", pupil_scale=0.58)
    ear_l, ear_r = bk.ears_floppy("ear", head_at, head_dims, size=0.11,
                                  spacing=1.0, length=0.2, color=dark, droop=28)

    legs = bk.legs_quad("leg", front=(0.12, 0.16, 0.28), back=(0.13, -0.2, 0.28),
                        length=0.26, thickness=0.1, color=coat, foot_color=cream)
    tail_obj = bk.tail("tail", (0, -0.3, 0.54), length=0.24, thickness=0.09,
                       color=coat, style="taper", tip_color=cream, segments=3,
                       curl=0.85)

    groups = {
        "body": (body, (0, 0, 0.28)),
        "head": (head, (0, 0.22, 0.5)),
        "ear.L": ([ear_l], tuple(ear_l.location)),
        "ear.R": ([ear_r], tuple(ear_r.location)),
        "tail": ([tail_obj], (0, -0.3, 0.54)),
    }
    for key, obj in legs.items():
        groups[key] = ([obj], tuple(obj.location))
    bk.assemble(root, groups)
    return bk.finish(root)


# ---------------------------------------------------------------------------
# Bird -- Uncommon, $8/s. A little blue songbird.
# ---------------------------------------------------------------------------

def build_bird():
    kit.reset_scene()
    root = kit.empty("root")

    plume = "#4a90e2"
    light = "#a8d4f5"
    beak = "#ffc93c"

    body_dims = (0.3, 0.34, 0.32)
    body_at = (0, 0, 0.34)
    body = [bk.block("body.core", body_dims, body_at, color=plume)]
    body += bk.belly("body.breast", body_at, body_dims, color=light, inset=0.72)

    head_dims = (0.24, 0.22, 0.22)
    head_at = (0, 0.08, 0.6)
    head = [bk.block("head.skull", head_dims, head_at, color=plume)]
    head += bk.eyes("head.eye", head_at, head_dims, spacing=0.6, height=0.03,
                    size=0.062, style="dot")
    head += bk.beak("head.beak", head_at, head_dims, width=0.075, length=0.11,
                    height=0.055, color=beak, drop=-0.03)
    head.append(bk.wedge("head.crest", (0.05, 0.08, 0.1),
                         (0, head_at[1] - 0.04, head_at[2] + 0.15),
                         rot=(-22, 0, 0), color="#2d6bb5", taper=0.7))

    wing_l, wing_r = bk.wings_flat("wing", (0.14, 0.0, 0.4), span=0.2,
                                   height=0.24, thickness=0.055, color=plume,
                                   tip_color="#2d6bb5", layers=2, tilt=10)
    tail = bk.tail("tail", (0, -0.18, 0.34), length=0.2, thickness=0.1,
                   color="#2d6bb5", style="flat", segments=2, curl=0.3)
    legs = bk.bird_feet("leg", (0.07, 0.0, 0.18), shin=0.1, thickness=0.038,
                        toe=0.1, color=beak)

    groups = {
        "body": (body, (0, 0, 0.18)),
        "head": (head, (0, 0.02, 0.48)),
        "wing.L": ([wing_l], tuple(wing_l.location)),
        "wing.R": ([wing_r], tuple(wing_r.location)),
        "tail": ([tail], (0, -0.18, 0.34)),
    }
    for key, obj in legs.items():
        groups[key] = ([obj], tuple(obj.location))
    bk.assemble(root, groups)
    return bk.finish(root)


# ---------------------------------------------------------------------------
# Burrowing Owl -- Rare, $35/s. Long legs, enormous eyes.
# ---------------------------------------------------------------------------

def build_burrowing_owl():
    kit.reset_scene()
    root = kit.empty("root")

    feather = "#a8814e"
    cream = "#efe0c4"
    beak = "#3b3128"

    body_dims = (0.34, 0.32, 0.4)
    body_at = (0, 0, 0.46)
    body = [bk.block("body.core", body_dims, body_at, color=feather)]
    body += bk.belly("body.breast", body_at, body_dims, color=cream, inset=0.76)
    body += bk.spots("body.speck", body_at, body_dims, count=6, size=0.05,
                     color="#6d5433", seed=11, faces=("front", "left", "right"))

    head_dims = (0.32, 0.26, 0.26)
    head_at = (0, 0.04, 0.78)
    head = [bk.block("head.skull", head_dims, head_at, color=feather)]
    # The owl's whole read is the facial disc: a pale plate with huge eyes.
    head += [bk.face_plate("head.disc", bk.face_of(head_at, head_dims, "front"),
                           (0.26, 0.2), face="front", color=cream, depth=0.03)]
    head += bk.eyes("head.eye", head_at, head_dims, spacing=0.52, height=0.02,
                    size=0.105, style="white", iris="#2a2118", pupil_scale=0.62)
    head += bk.beak("head.beak", head_at, head_dims, width=0.06, length=0.08,
                    height=0.06, color=beak, drop=-0.08)
    for side, sign in (("L", 1), ("R", -1)):
        head.append(bk.wedge("head.tuft.%s" % side, (0.06, 0.06, 0.11),
                             (sign * 0.1, head_at[1] - 0.03, head_at[2] + 0.17),
                             rot=(0, -sign * 14, 0), color="#6d5433", taper=0.75))

    wing_l, wing_r = bk.wings_flat("wing", (0.16, -0.02, 0.5), span=0.16,
                                   height=0.3, thickness=0.07, color=feather,
                                   tip_color="#6d5433", layers=2, tilt=4)
    legs = bk.bird_feet("leg", (0.09, 0.0, 0.26), shin=0.22, thickness=0.05,
                        toe=0.12, color="#d8b878")

    groups = {
        "body": (body, (0, 0, 0.26)),
        "head": (head, (0, 0, 0.65)),
        "wing.L": ([wing_l], tuple(wing_l.location)),
        "wing.R": ([wing_r], tuple(wing_r.location)),
    }
    for key, obj in legs.items():
        groups[key] = ([obj], tuple(obj.location))
    bk.assemble(root, groups)
    return bk.finish(root)


# ---------------------------------------------------------------------------
# Raccoon -- Rare, $45/s. Mask and ringed tail do all the work.
# ---------------------------------------------------------------------------

def build_raccoon():
    kit.reset_scene()
    root = kit.empty("root")

    fur = "#8a8f9a"
    dark = "#3a3d46"
    pale = "#d8dce2"

    body_dims = (0.36, 0.5, 0.34)
    body_at = (0, -0.04, 0.42)
    body = [bk.block("body.core", body_dims, body_at, color=fur)]
    body += bk.belly("body.chest", body_at, body_dims, color=pale, inset=0.7)

    head_dims = (0.3, 0.26, 0.26)
    head_at = (0, 0.3, 0.6)
    head = [bk.block("head.skull", head_dims, head_at, color=fur)]
    face = bk.face_of(head_at, head_dims, "front")
    # The bandit mask: one dark bar with the pale muzzle punched under it.
    head.append(bk.face_plate("head.mask", face, (0.27, 0.1), face="front",
                              color=dark, depth=0.022, offset=(0, 0.04)))
    head += bk.snout("head.snout", head_at, head_dims, width=0.13, length=0.13,
                     height=0.1, color=pale, drop=-0.07, nose_color="#241d22")
    head += bk.eyes("head.eye", head_at, head_dims, spacing=0.54, height=0.05,
                    size=0.055, style="white", iris="#141118", pupil_scale=0.6)
    ear_l, ear_r = bk.ears_box("ear", head_at, head_dims, size=0.1,
                               spacing=0.66, depth=0.05, color=fur,
                               inner_color="#c8a6a0")

    legs = bk.legs_quad("leg", front=(0.12, 0.14, 0.26), back=(0.13, -0.2, 0.26),
                        length=0.24, thickness=0.1, color=dark, foot_color=dark)
    tail_obj = bk.tail("tail", (0, -0.28, 0.5), length=0.34, thickness=0.13,
                       color=fur, style="segmented", segments=5, curl=0.55)
    # Alternating rings, painted as bands over the finished tail.
    rings = []
    for i in range(3):
        rings.append(bk.block("tail.ring%d" % i, (0.15, 0.05, 0.15),
                              (0, -0.34 - i * 0.09, 0.53 + i * 0.035),
                              color=dark))

    groups = {
        "body": (body, (0, 0, 0.26)),
        "head": (head, (0, 0.2, 0.48)),
        "ear.L": ([ear_l], tuple(ear_l.location)),
        "ear.R": ([ear_r], tuple(ear_r.location)),
        "tail": ([tail_obj] + rings, (0, -0.28, 0.5)),
    }
    for key, obj in legs.items():
        groups[key] = ([obj], tuple(obj.location))
    bk.assemble(root, groups)
    return bk.finish(root)


# ---------------------------------------------------------------------------
# Fox -- Epic, $180/s.
# ---------------------------------------------------------------------------

def build_fox():
    kit.reset_scene()
    root = kit.empty("root")

    coat = "#e2703a"
    cream = "#fdf0dd"
    paw = "#3a2b30"

    body_dims = (0.34, 0.56, 0.32)
    body_at = (0, -0.04, 0.42)
    body = [bk.block("body.core", body_dims, body_at, color=coat)]
    body += bk.belly("body.chest", body_at, body_dims, color=cream, inset=0.74)

    head_dims = (0.3, 0.24, 0.26)
    head_at = (0, 0.34, 0.6)
    head = [bk.block("head.skull", head_dims, head_at, color=coat)]
    head += bk.snout("head.snout", head_at, head_dims, width=0.14, length=0.18,
                     height=0.11, color=cream, drop=-0.05, nose_color="#241d22")
    head += bk.eyes("head.eye", head_at, head_dims, spacing=0.56, height=0.06,
                    size=0.065, style="white", iris="#20180f", pupil_scale=0.55)
    ear_l, ear_r = bk.ears_pointed("ear", head_at, head_dims, size=0.12,
                                   spacing=0.62, length=0.2, color=coat,
                                   inner_color="#2a2026", lean=8)

    legs = bk.legs_quad("leg", front=(0.12, 0.16, 0.26), back=(0.13, -0.2, 0.26),
                        length=0.25, thickness=0.095, color=coat, foot_color=paw)
    tail_obj = bk.tail("tail", (0, -0.3, 0.5), length=0.4, thickness=0.14,
                       color=coat, style="puff", tip_color=cream, segments=3,
                       curl=0.5)

    groups = {
        "body": (body, (0, 0, 0.26)),
        "head": (head, (0, 0.22, 0.5)),
        "ear.L": ([ear_l], tuple(ear_l.location)),
        "ear.R": ([ear_r], tuple(ear_r.location)),
        "tail": ([tail_obj], (0, -0.3, 0.5)),
    }
    for key, obj in legs.items():
        groups[key] = ([obj], tuple(obj.location))
    bk.assemble(root, groups)
    return bk.finish(root)


# ---------------------------------------------------------------------------
# Bear -- Epic, $240/s. Bulk is the whole read; keep the limbs short.
# ---------------------------------------------------------------------------

def build_bear():
    kit.reset_scene()
    root = kit.empty("root")

    fur = "#7a5236"
    muzzle = "#c4a077"
    claw = "#2b2018"

    body_dims = (0.52, 0.62, 0.5)
    body_at = (0, -0.02, 0.46)
    body = [bk.block("body.core", body_dims, body_at, color=fur)]
    body += bk.belly("body.chest", body_at, body_dims, color="#9a7150", inset=0.66)

    head_dims = (0.38, 0.3, 0.32)
    head_at = (0, 0.34, 0.76)
    head = [bk.block("head.skull", head_dims, head_at, color=fur)]
    head += bk.snout("head.snout", head_at, head_dims, width=0.2, length=0.13,
                     height=0.15, color=muzzle, drop=-0.06, nose_color="#241d22")
    head += bk.eyes("head.eye", head_at, head_dims, spacing=0.52, height=0.08,
                    size=0.06, style="white", iris="#1b1410", pupil_scale=0.6)
    ear_l, ear_r = bk.ears_box("ear", head_at, head_dims, size=0.12,
                               spacing=0.66, depth=0.07, color=fur,
                               inner_color="#4d3423")

    legs = bk.legs_quad("leg", front=(0.18, 0.2, 0.26), back=(0.19, -0.22, 0.26),
                        length=0.24, thickness=0.15, color=fur, foot_color=claw)
    tail_obj = bk.tail("tail", (0, -0.34, 0.5), length=0.1, thickness=0.11,
                       color=fur, style="puff", segments=1, curl=0.2)

    groups = {
        "body": (body, (0, 0, 0.26)),
        "head": (head, (0, 0.22, 0.62)),
        "ear.L": ([ear_l], tuple(ear_l.location)),
        "ear.R": ([ear_r], tuple(ear_r.location)),
        "tail": ([tail_obj], (0, -0.34, 0.5)),
    }
    for key, obj in legs.items():
        groups[key] = ([obj], tuple(obj.location))
    bk.assemble(root, groups)
    return bk.finish(root)


# ---------------------------------------------------------------------------
# Branchwalker -- Legendary, $1.8K/s.
# An original creature: a walking piece of forest. Bark torso, moss shoulders,
# antler branches, and stilt legs, so its silhouette reads as "tree" long
# before you can see any detail.
# ---------------------------------------------------------------------------

def build_branchwalker():
    kit.reset_scene()
    root = kit.empty("root")

    bark = "#6b4f34"
    barkdark = "#4e3826"
    moss = "#5b8f3e"
    glow = "#ffe27a"

    body_dims = (0.36, 0.34, 0.62)
    body_at = (0, 0, 0.62)
    body = [bk.block("body.trunk", body_dims, body_at, color=bark)]
    # Vertical bark ridges give the trunk grain without a texture.
    for i, dx in enumerate((-0.12, 0.0, 0.12)):
        body.append(bk.block("body.grain%d" % i, (0.05, 0.03, 0.5),
                             (dx, body_at[1] + 0.18, body_at[2]), color=barkdark))
    body += [bk.block("body.moss", (0.4, 0.36, 0.1), (0, 0, 0.9), color=moss)]
    body += bk.spots("body.lichen", body_at, body_dims, count=5, size=0.06,
                     color="#7fae52", seed=5, faces=("left", "right", "back"))

    head_dims = (0.3, 0.28, 0.26)
    head_at = (0, 0.04, 1.06)
    head = [bk.block("head.skull", head_dims, head_at, color=bark)]
    face = bk.face_of(head_at, head_dims, "front")
    # Hollow-knot eyes: dark sockets with a warm ember inside.
    head += bk.eyes("head.socket", head_at, head_dims, spacing=0.52, height=0.02,
                    size=0.085, style="dot", iris="#241a12")
    for side, sign in (("L", 1), ("R", -1)):
        head.append(bk.face_plate(
            "head.ember.%s" % side, face, (0.04, 0.04), face="front",
            material=kit.mat("bw.ember", kit.hexcol(glow), rough=0.2,
                             emission=kit.hexcol(glow), emission_strength=3.4),
            depth=0.02, offset=(sign * head_dims[0] * 0.26, 0.02),
            proud=bk.PROUD * 4,
        ))
    head.append(bk.block("head.brow", (0.3, 0.06, 0.06),
                         (0, head_at[1] + 0.1, head_at[2] + 0.11), color=barkdark))
    head += bk.mouth("head.mouth", head_at, head_dims, width=0.14, height=0.03,
                     drop=-0.09, color="#241a12")

    # Antlers: two forked branch clusters, built as ears so they sway.
    antlers = []
    for side, sign in (("L", 1), ("R", -1)):
        parts = [
            bk.block("ear.%s.beam" % side, (0.05, 0.05, 0.24),
                     (sign * 0.11, 0.0, 1.28), rot=(0, -sign * 16, 0), color=barkdark),
            bk.block("ear.%s.fork1" % side, (0.04, 0.04, 0.14),
                     (sign * 0.2, 0.03, 1.38), rot=(12, -sign * 46, 0), color=barkdark),
            bk.block("ear.%s.fork2" % side, (0.04, 0.04, 0.11),
                     (sign * 0.16, -0.06, 1.44), rot=(-20, -sign * 28, 0), color=barkdark),
            bk.block("ear.%s.leaf" % side, (0.09, 0.09, 0.04),
                     (sign * 0.24, 0.05, 1.45), color=moss),
        ]
        merged = kit.join(parts, "ear.%s" % side)
        kit.weld(merged)
        kit.set_origin_to(merged, (sign * 0.1, 0, 1.18))
        antlers.append(merged)

    arm_l, arm_r = bk.arms("arm", (0.2, 0, 0.82), length=0.3, thickness=0.08,
                           color=barkdark, hand_color=moss, angle=18)
    legs = bk.legs_pair("leg", (0.11, 0, 0.32), length=0.3, thickness=0.1,
                        color=barkdark, foot_color=bark, foot_length=0.24)

    groups = {
        "body": (body, (0, 0, 0.3)),
        "head": (head, (0, 0, 0.92)),
        "ear.L": ([antlers[0]], tuple(antlers[0].location)),
        "ear.R": ([antlers[1]], tuple(antlers[1].location)),
        "arm.L": ([arm_l], tuple(arm_l.location)),
        "arm.R": ([arm_r], tuple(arm_r.location)),
    }
    for key, obj in legs.items():
        groups[key] = ([obj], tuple(obj.location))
    bk.assemble(root, groups)
    return bk.finish(root)


PETS = {
    "chicken": build_chicken,
    "dog": build_dog,
    "bird": build_bird,
    "burrowing-owl": build_burrowing_owl,
    "raccoon": build_raccoon,
    "fox": build_fox,
    "bear": build_bear,
    "branchwalker": build_branchwalker,
}
