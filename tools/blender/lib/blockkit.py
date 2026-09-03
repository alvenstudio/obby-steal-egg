"""
blockkit.py -- boxy creature anatomy, matching the reference game's look.

The game this clones builds its creatures the Roblox way: eight to twenty
stacked, axis-aligned boxes with flat painted faces, matte plastic materials,
no textures. That reads as deliberate rather than crude because of three
things, all of which this module enforces:

  1. **Consistent bevel.** Every box gets a small bevel keyed to its smallest
     dimension, so a tiny beak and a huge torso catch light the same way.
  2. **Proud face decals.** Eyes, nostrils, mouths and markings are thin plates
     pushed a hair out of the surface they sit on. Flush decals z-fight; sunken
     ones vanish. `face_plate` solves this once.
  3. **Snapped proportions.** Sizes come from a small unit grid, which is what
     makes a hundred separate creatures look like one toy line.

Facing convention is shared with petkit: creatures face +Y, which the glTF
exporter maps to -Z, the forward axis three.js expects.
"""

from __future__ import annotations

import math

from mathutils import Vector

import kit

D2R = math.pi / 180.0

# The unit the whole bestiary is proportioned on. Pets are normalised to 1.0
# tall at export, so these are ratios, not world units.
U = 0.125

# How much of a box's smallest dimension becomes its bevel. Small enough to
# keep corners crisp, large enough to catch a highlight.
BEVEL_RATIO = 0.14
BEVEL_MAX = 0.028


def snap(value, unit=U):
    """Quantise a dimension to the unit grid."""
    return round(value / unit) * unit


def block(name, dims, loc=(0, 0, 0), rot=(0, 0, 0), color=None, material=None,
          bevel=True, segments=2):
    """
    The workhorse. A beveled box given as full width/depth/height.

    `color` is a hex string; `material` overrides it with a shared material.
    """
    if material is None:
        material = kit.mat("blk." + (color or "#cccccc").strip("#"),
                           kit.hexcol(color or "#cccccc"))
    obj = kit.box(name, dims=dims, loc=loc, rot=rot, material=material)
    if bevel:
        width = min(abs(dims[0]), abs(dims[1]), abs(dims[2]))
        amount = min(width * BEVEL_RATIO, BEVEL_MAX)
        if amount > 0.0015:
            kit.bevel(obj, amount, segments)
    return obj


def slab(name, dims, loc=(0, 0, 0), rot=(0, 0, 0), color=None, material=None):
    """A thin plate; bevelled lightly so it still reads as a solid part."""
    return block(name, dims, loc, rot, color, material, bevel=True, segments=1)


def wedge(name, dims, loc=(0, 0, 0), rot=(0, 0, 0), color=None, material=None,
          taper=0.0):
    """A box tapered along +Z -- beaks, horns, fins, snouts."""
    obj = block(name, dims, loc, rot, color, material, bevel=True, segments=1)
    if taper > 0:
        kit.taper(obj, axis="Z", at_min=1.0, at_max=max(0.02, 1.0 - taper))
    return obj


def cylinder(name, r, h, loc=(0, 0, 0), rot=(0, 0, 0), color=None, material=None,
             verts=12):
    if material is None:
        material = kit.mat("blk." + (color or "#cccccc").strip("#"),
                           kit.hexcol(color or "#cccccc"))
    return kit.cyl(name, r=r, h=h, loc=loc, rot=rot, material=material, verts=verts)


def studs(name, top_center, dims, color=None, material=None, cols=2, rows=2,
          radius=None, height=None):
    """
    Roblox studs on a top face. Used sparingly -- on nests, crates and platform
    tops rather than on creatures, which is how the reference uses them.
    """
    if material is None:
        material = kit.mat("stud." + (color or "#cccccc").strip("#"),
                           kit.hexcol(color or "#cccccc"))
    radius = radius or min(dims[0] / cols, dims[1] / rows) * 0.26
    height = height or radius * 0.55
    parts = []
    for cx in range(cols):
        for cy in range(rows):
            x = top_center[0] + dims[0] * ((cx + 0.5) / cols - 0.5)
            y = top_center[1] + dims[1] * ((cy + 0.5) / rows - 0.5)
            parts.append(kit.cyl(
                "%s.%d_%d" % (name, cx, cy), r=radius, h=height,
                loc=(x, y, top_center[2] + height * 0.5),
                material=material, verts=10,
            ))
    return parts


# --------------------------------------------------------------------------
# face decals
# --------------------------------------------------------------------------

# How far a decal is pushed out of the face it sits on. Large enough to beat
# depth precision at any camera distance, small enough to be invisible.
PROUD = 0.006


def face_plate(name, center, size, face="front", depth=0.018, color="#20191a",
               material=None, offset=(0, 0), proud=PROUD):
    """
    A flat plate sitting proud of one face of a box.

    `center` is the CENTRE OF THE HOST FACE, not the host box's centre --
    passing the face directly is what stops every caller from re-deriving the
    same half-extent arithmetic and getting it wrong.

    `size` is (width, height) in the face's own plane.
    `offset` shifts the plate within that plane.
    """
    if material is None:
        material = kit.mat("dec." + color.strip("#"), kit.hexcol(color), rough=0.45)

    w, h = size
    push = depth * 0.5 + proud
    if face == "front":     # +Y
        dims = (w, depth, h)
        loc = (center[0] + offset[0], center[1] + push, center[2] + offset[1])
        rot = (0, 0, 0)
    elif face == "back":    # -Y
        dims = (w, depth, h)
        loc = (center[0] + offset[0], center[1] - push, center[2] + offset[1])
        rot = (0, 0, 0)
    elif face == "left":    # +X
        dims = (depth, w, h)
        loc = (center[0] + push, center[1] + offset[0], center[2] + offset[1])
        rot = (0, 0, 0)
    elif face == "right":   # -X
        dims = (depth, w, h)
        loc = (center[0] - push, center[1] + offset[0], center[2] + offset[1])
        rot = (0, 0, 0)
    elif face == "top":     # +Z
        dims = (w, h, depth)
        loc = (center[0] + offset[0], center[1] + offset[1], center[2] + push)
        rot = (0, 0, 0)
    else:                   # bottom, -Z
        dims = (w, h, depth)
        loc = (center[0] + offset[0], center[1] + offset[1], center[2] - push)
        rot = (0, 0, 0)

    return block(name, dims, loc, rot, material=material, bevel=True, segments=1)


def face_of(center, dims, face):
    """Centre point of one face of a box, given the box's centre and full size."""
    half = (dims[0] * 0.5, dims[1] * 0.5, dims[2] * 0.5)
    return {
        "front": (center[0], center[1] + half[1], center[2]),
        "back": (center[0], center[1] - half[1], center[2]),
        "left": (center[0] + half[0], center[1], center[2]),
        "right": (center[0] - half[0], center[1], center[2]),
        "top": (center[0], center[1], center[2] + half[2]),
        "bottom": (center[0], center[1], center[2] - half[2]),
    }[face]


def eyes(name, head_center, head_dims, spacing=0.5, height=0.12, size=0.13,
         style="dot", iris="#1a1620", sclera="#ffffff", pupil_scale=0.5,
         face="front", glint=True):
    """
    A mirrored pair of painted eyes on a box face.

    styles:
        dot    -- a single dark square. The reference's default.
        white  -- sclera plate with a smaller dark pupil on top.
        angry  -- sclera plus a slanted brow bar.
        glow   -- emissive iris, for cosmic and undead pets.
        sleepy -- a wide flat bar, half-closed.
    """
    plane = face_of(head_center, head_dims, face)
    span = head_dims[0] if face in ("front", "back") else head_dims[1]
    dx = span * 0.5 * spacing
    parts = []

    for side, sign in (("L", 1), ("R", -1)):
        offset = (sign * dx, height)
        tag = "%s.%s" % (name, side)

        if style == "dot":
            parts.append(face_plate(tag, plane, (size, size), face=face,
                                    color=iris, depth=0.02, offset=offset))
        elif style == "sleepy":
            parts.append(face_plate(tag, plane, (size * 1.35, size * 0.34),
                                    face=face, color=iris, depth=0.02, offset=offset))
        elif style == "glow":
            material = kit.mat("eyeglow." + iris.strip("#"), kit.hexcol(iris),
                               rough=0.2, emission=kit.hexcol(iris),
                               emission_strength=3.2)
            parts.append(face_plate(tag, plane, (size, size * 1.1), face=face,
                                    material=material, depth=0.022, offset=offset))
        else:  # white / angry
            parts.append(face_plate(tag + ".sclera", plane, (size, size * 1.15),
                                    face=face, color=sclera, depth=0.02, offset=offset))
            parts.append(face_plate(
                tag + ".iris", plane, (size * pupil_scale, size * pupil_scale * 1.15),
                face=face, color=iris, depth=0.02, offset=offset, proud=PROUD * 3.2,
            ))
            if style == "angry":
                brow = face_plate(
                    tag + ".brow", plane, (size * 1.25, size * 0.3), face=face,
                    color=iris, depth=0.022,
                    offset=(offset[0], offset[1] + size * 0.78),
                    proud=PROUD * 2,
                )
                brow.rotation_euler.y = sign * -16 * D2R
                parts.append(brow)
            if glint:
                parts.append(face_plate(
                    tag + ".glint", plane, (size * 0.2, size * 0.2), face=face,
                    color="#ffffff", depth=0.016,
                    offset=(offset[0] + size * 0.2, offset[1] + size * 0.24),
                    proud=PROUD * 5,
                ))
    return parts


def mouth(name, head_center, head_dims, width=0.3, height=0.06, drop=-0.16,
          color="#2a1f24", face="front", style="line", teeth=0, teeth_color="#ffffff"):
    """styles: line | open | grin | beakless"""
    plane = face_of(head_center, head_dims, face)
    parts = []
    if style == "open":
        parts.append(face_plate(name, plane, (width, height * 3.2), face=face,
                                color=color, depth=0.02, offset=(0, drop)))
        for i in range(teeth):
            t = (i + 0.5) / max(1, teeth)
            parts.append(face_plate(
                "%s.tooth%d" % (name, i),
                plane, (width / max(1, teeth) * 0.55, height * 1.1), face=face,
                color=teeth_color, depth=0.02,
                offset=(width * (t - 0.5), drop + height * 1.35),
                proud=PROUD * 3.2,
            ))
    elif style == "grin":
        segments = 5
        for i in range(segments):
            t = (i / (segments - 1)) * 2 - 1
            parts.append(face_plate(
                "%s.%d" % (name, i), plane, (width / segments * 1.3, height),
                face=face, color=color, depth=0.02,
                offset=(t * width * 0.5, drop - abs(t) * height * 0.9),
            ))
    elif style != "beakless":
        parts.append(face_plate(name, plane, (width, height), face=face,
                                color=color, depth=0.02, offset=(0, drop)))
    return parts


def cheeks(name, head_center, head_dims, spacing=0.78, height=-0.1, size=0.13,
           color="#ff8fa3", face="front"):
    plane = face_of(head_center, head_dims, face)
    span = head_dims[0] if face in ("front", "back") else head_dims[1]
    parts = []
    for side, sign in (("L", 1), ("R", -1)):
        parts.append(face_plate(
            "%s.%s" % (name, side), plane, (size, size * 0.62), face=face,
            color=color, depth=0.016, offset=(sign * span * 0.5 * spacing, height),
        ))
    return parts


def nostrils(name, snout_center, snout_dims, spacing=0.42, height=0.05,
             size=0.05, color="#20191a", face="front"):
    plane = face_of(snout_center, snout_dims, face)
    parts = []
    for side, sign in (("L", 1), ("R", -1)):
        parts.append(face_plate(
            "%s.%s" % (name, side), plane, (size, size), face=face, color=color,
            depth=0.014, offset=(sign * snout_dims[0] * 0.5 * spacing, height),
        ))
    return parts


# --------------------------------------------------------------------------
# limbs and appendages
# --------------------------------------------------------------------------


def leg(name, at, length=0.3, thickness=0.11, color="#c98a5a", foot=True,
        foot_color=None, foot_length=None, material=None):
    """One boxy leg with an optional foot. `at` is the hip joint."""
    parts = [block(
        name + ".shaft", (thickness, thickness, length),
        (at[0], at[1], at[2] - length * 0.5), color=color, material=material,
    )]
    if foot:
        fl = foot_length or thickness * 1.9
        parts.append(block(
            name + ".foot", (thickness * 1.15, fl, thickness * 0.55),
            (at[0], at[1] + fl * 0.22, at[2] - length - thickness * 0.22),
            color=foot_color or color,
        ))
    merged = kit.join(parts, name)
    kit.weld(merged)
    kit.set_origin_to(merged, at)
    return merged


def legs_quad(prefix, front, back, length=0.3, thickness=0.11, color="#c98a5a",
              foot_color=None, foot=True):
    """Four legs from two hip positions (left side given; right is mirrored)."""
    out = {}
    for tag, at in (("F", front), ("B", back)):
        left = leg("%s.%sL" % (prefix, tag), at, length, thickness, color,
                   foot, foot_color)
        right = kit.duplicate(left, "%s.%sR" % (prefix, tag), mirror=True)
        right.location = Vector((-left.location.x, left.location.y, left.location.z))
        out["%s.%sL" % (prefix, tag)] = left
        out["%s.%sR" % (prefix, tag)] = right
    return out


def legs_pair(prefix, at, length=0.3, thickness=0.11, color="#c98a5a",
              foot_color=None, foot=True, foot_length=None):
    """Two legs, named leg.FL / leg.FR so the animator drives them as a pair."""
    left = leg("%s.FL" % prefix, at, length, thickness, color, foot, foot_color,
               foot_length)
    right = kit.duplicate(left, "%s.FR" % prefix, mirror=True)
    right.location = Vector((-left.location.x, left.location.y, left.location.z))
    return {"%s.FL" % prefix: left, "%s.FR" % prefix: right}


def bird_feet(prefix, at, shin=0.14, thickness=0.05, toe=0.16, color="#ff9c2e"):
    """Stick shin plus three splayed toes."""
    out = {}
    parts = [block("%s.FL.shin" % prefix, (thickness, thickness, shin),
                   (at[0], at[1], at[2] - shin * 0.5), color=color)]
    for i, spread in enumerate((-24.0, 0.0, 24.0)):
        parts.append(block(
            "%s.FL.toe%d" % (prefix, i), (thickness * 0.62, toe, thickness * 0.62),
            (at[0], at[1] + toe * 0.3, at[2] - shin - thickness * 0.3),
            rot=(0, 0, spread), color=color,
        ))
    left = kit.join(parts, "%s.FL" % prefix)
    kit.weld(left)
    kit.set_origin_to(left, at)
    right = kit.duplicate(left, "%s.FR" % prefix, mirror=True)
    right.location = Vector((-left.location.x, left.location.y, left.location.z))
    out["%s.FL" % prefix] = left
    out["%s.FR" % prefix] = right
    return out


def arms(name, at, length=0.24, thickness=0.09, color="#c98a5a", hand=True,
         hand_color=None, angle=14.0):
    """A mirrored pair of arms; returns (left, right)."""
    dz = math.cos(angle * D2R) * length
    dx = math.sin(angle * D2R) * length
    parts = [block(name + ".shaft", (thickness, thickness, length),
                   (at[0] + dx * 0.5, at[1], at[2] - dz * 0.5),
                   rot=(0, angle, 0), color=color)]
    if hand:
        parts.append(block(
            name + ".hand", (thickness * 1.2, thickness * 1.2, thickness * 0.9),
            (at[0] + dx, at[1], at[2] - dz), color=hand_color or color,
        ))
    left = kit.join(parts, name + ".L")
    kit.weld(left)
    kit.set_origin_to(left, at)
    right = kit.duplicate(left, name + ".R", mirror=True)
    right.location = Vector((-left.location.x, left.location.y, left.location.z))
    return left, right


def wings_flat(name, at, span=0.4, height=0.26, thickness=0.05, color="#f2f2f6",
               tip_color=None, layers=2, tilt=8.0):
    """
    Stepped slab wings. Two or three overlapping plates of decreasing size read
    as feathers at this scale far better than actual feather geometry.
    """
    parts = []
    for i in range(layers):
        t = i / max(1, layers - 1) if layers > 1 else 0
        parts.append(block(
            "%s.f%d" % (name, i),
            (span * (1 - 0.18 * t), thickness, height * (1 - 0.22 * t)),
            (at[0] + span * 0.5, at[1] - height * 0.22 * t, at[2] - height * 0.3 * t),
            rot=(0, -tilt - 8 * t, 0),
            color=(tip_color if (tip_color and i == layers - 1) else color),
        ))
    left = kit.join(parts, name + ".L")
    kit.weld(left)
    kit.set_origin_to(left, at)
    right = kit.duplicate(left, name + ".R", mirror=True)
    right.location = Vector((-left.location.x, left.location.y, left.location.z))
    return left, right


def wings_membrane(name, at, span=0.46, height=0.4, thickness=0.045,
                   color="#6b3f8f", bone_color=None, fingers=3, tilt=14.0):
    """Bat/dragon wing: one webbed slab plus finger struts."""
    parts = [block(name + ".web", (span, thickness, height),
                   (at[0] + span * 0.5, at[1] - height * 0.1, at[2] + height * 0.08),
                   rot=(0, -tilt, 0), color=color)]
    bone = bone_color or color
    for i in range(fingers):
        t = (i + 1) / (fingers + 1)
        parts.append(block(
            "%s.bone%d" % (name, i),
            (thickness * 1.1, thickness * 1.35, height * (1.02 - 0.2 * t)),
            (at[0] + span * t, at[1] - height * 0.1, at[2] + height * 0.08),
            rot=(0, -tilt, 0), color=bone,
        ))
    parts.append(block(
        name + ".spar", (span, thickness * 1.4, thickness * 1.4),
        (at[0] + span * 0.5, at[1] - height * 0.1, at[2] + height * 0.5),
        rot=(0, -tilt, 0), color=bone,
    ))
    left = kit.join(parts, name + ".L")
    kit.weld(left)
    kit.set_origin_to(left, at)
    right = kit.duplicate(left, name + ".R", mirror=True)
    right.location = Vector((-left.location.x, left.location.y, left.location.z))
    return left, right


def fins(name, at, size=0.22, thickness=0.045, color="#4fa8d8", tilt=22.0):
    left = block(name + ".L", (size, thickness, size * 0.7),
                 (at[0] + size * 0.5, at[1], at[2]),
                 rot=(0, -tilt, 14), color=color)
    kit.set_origin_to(left, at)
    right = kit.duplicate(left, name + ".R", mirror=True)
    right.location = Vector((-left.location.x, left.location.y, left.location.z))
    return left, right


def fin_tail(name, at, size=0.3, thickness=0.05, color="#4fa8d8", lobes=2):
    parts = []
    for i in range(lobes):
        up = 1 if i == 0 else -1
        parts.append(block(
            "%s.%d" % (name, i), (thickness, size * 0.8, size * 0.62),
            (at[0], at[1] - size * 0.34, at[2] + up * size * 0.3),
            rot=(up * 26, 0, 0), color=color,
        ))
    merged = kit.join(parts, name)
    kit.weld(merged)
    kit.set_origin_to(merged, at)
    return merged


def tail(name, at, length=0.36, thickness=0.1, color="#c98a5a", style="taper",
         tip_color=None, segments=4, curl=0.28):
    """
    Boxy tails. styles: taper | puff | segmented | whip | flat | spike | coil
    Grows backward along -Y from `at`, curling up.
    """
    parts = []
    for i in range(segments):
        t = (i + 0.5) / segments
        y = at[1] - length * t
        z = at[2] + length * curl * t * t

        if style == "puff":
            s = thickness * (1.5 + 1.5 * math.sin(math.pi * min(1.0, t * 0.9)))
        elif style == "segmented":
            s = thickness * (1.05 - 0.5 * t)
        elif style == "whip":
            s = thickness * (0.8 - 0.55 * t)
        elif style == "flat":
            s = thickness
        elif style == "spike":
            s = thickness * (1.0 - 0.62 * t)
        else:  # taper
            s = thickness * (1.0 - 0.6 * t)

        dims = (s, length / segments * 1.15, s)
        if style == "flat":
            dims = (thickness * 2.6, length / segments * 1.15, thickness * 0.55)
        parts.append(block(
            "%s.%d" % (name, i), dims, (at[0], y, z),
            color=(tip_color if (tip_color and i == segments - 1) else color),
        ))

    if style in ("whip", "puff") and tip_color:
        parts.append(block(
            name + ".tip", (thickness * 1.7, thickness * 2.0, thickness * 1.7),
            (at[0], at[1] - length - thickness * 0.4, at[2] + length * curl),
            color=tip_color,
        ))
    if style == "spike":
        parts.append(wedge(
            name + ".spike", (thickness * 1.4, thickness * 1.4, thickness * 2.4),
            (at[0], at[1] - length - thickness * 0.6, at[2] + length * curl),
            rot=(-96, 0, 0), color=tip_color or color, taper=0.85,
        ))

    merged = kit.join(parts, name)
    kit.weld(merged)
    kit.set_origin_to(merged, at)
    return merged


# --------------------------------------------------------------------------
# head furniture
# --------------------------------------------------------------------------


def ears_box(name, head_center, head_dims, size=0.15, height=0.9, spacing=0.62,
             depth=0.06, color="#e0a86a", inner_color=None, lean=0.0):
    """Flat slab ears standing on top of the skull."""
    top = head_center[2] + head_dims[2] * 0.5
    dx = head_dims[0] * 0.5 * spacing
    parts_l = [block(name + ".outer", (size, depth, size * 1.25),
                     (dx, head_center[1], top + size * 0.5), rot=(0, lean, 0),
                     color=color)]
    if inner_color:
        parts_l.append(block(
            name + ".inner", (size * 0.5, depth * 0.7, size * 0.7),
            (dx, head_center[1] + depth * 0.3, top + size * 0.52),
            rot=(0, lean, 0), color=inner_color,
        ))
    left = kit.join(parts_l, name + ".L")
    kit.weld(left)
    kit.set_origin_to(left, (dx, head_center[1], top))
    right = kit.duplicate(left, name + ".R", mirror=True)
    right.location = Vector((-left.location.x, left.location.y, left.location.z))
    _ = height
    return left, right


def ears_pointed(name, head_center, head_dims, size=0.14, spacing=0.6,
                 length=0.24, color="#e0a86a", inner_color=None, lean=10.0):
    """Tapered spire ears -- cats, foxes, wolves."""
    top = head_center[2] + head_dims[2] * 0.5
    dx = head_dims[0] * 0.5 * spacing
    parts = [wedge(name + ".outer", (size, size * 0.55, length),
                   (dx, head_center[1], top + length * 0.45),
                   rot=(0, -lean, 0), color=color, taper=0.86)]
    if inner_color:
        parts.append(wedge(
            name + ".inner", (size * 0.5, size * 0.34, length * 0.7),
            (dx, head_center[1] + size * 0.18, top + length * 0.42),
            rot=(0, -lean, 0), color=inner_color, taper=0.86,
        ))
    left = kit.join(parts, name + ".L")
    kit.weld(left)
    kit.set_origin_to(left, (dx, head_center[1], top))
    right = kit.duplicate(left, name + ".R", mirror=True)
    right.location = Vector((-left.location.x, left.location.y, left.location.z))
    return left, right


def ears_long(name, head_center, head_dims, size=0.12, spacing=0.42,
              length=0.44, color="#e6dccc", inner_color="#ffc9d4", lean=8.0):
    """Rabbit ears."""
    top = head_center[2] + head_dims[2] * 0.5
    dx = head_dims[0] * 0.5 * spacing
    parts = [block(name + ".outer", (size, size * 0.42, length),
                   (dx, head_center[1], top + length * 0.45),
                   rot=(0, -lean, 0), color=color)]
    if inner_color:
        parts.append(block(
            name + ".inner", (size * 0.48, size * 0.3, length * 0.74),
            (dx, head_center[1] + size * 0.14, top + length * 0.45),
            rot=(0, -lean, 0), color=inner_color,
        ))
    left = kit.join(parts, name + ".L")
    kit.weld(left)
    kit.set_origin_to(left, (dx, head_center[1], top))
    right = kit.duplicate(left, name + ".R", mirror=True)
    right.location = Vector((-left.location.x, left.location.y, left.location.z))
    return left, right


def ears_floppy(name, head_center, head_dims, size=0.14, spacing=1.0,
                length=0.3, color="#c98a5a", droop=34.0):
    dx = head_dims[0] * 0.5 * spacing
    anchor = (dx, head_center[1], head_center[2] + head_dims[2] * 0.22)
    flap = block(name + ".L", (size * 0.42, size, length),
                 (anchor[0] + size * 0.16, anchor[1], anchor[2] - length * 0.42),
                 color=color)
    kit.set_origin_to(flap, anchor)
    flap.rotation_euler = (0, -droop * D2R, 0)
    right = kit.duplicate(flap, name + ".R", mirror=True)
    right.location = Vector((-flap.location.x, flap.location.y, flap.location.z))
    right.rotation_euler = (0, droop * D2R, 0)
    return flap, right


def horns(name, head_center, head_dims, size=0.09, spacing=0.55, length=0.2,
          color="#f0e2c4", lean=22.0, tilt=0.0, segments=1):
    """Tapered horn pair. `segments` > 1 stacks shrinking blocks for a ridged look."""
    top = head_center[2] + head_dims[2] * 0.5
    dx = head_dims[0] * 0.5 * spacing
    parts = []
    if segments <= 1:
        parts.append(wedge(name + ".h", (size, size, length),
                           (dx, head_center[1], top + length * 0.45),
                           rot=(tilt, -lean, 0), color=color, taper=0.9))
    else:
        for i in range(segments):
            t = i / segments
            s = size * (1 - t * 0.6)
            parts.append(block(
                "%s.h%d" % (name, i), (s, s, length / segments * 1.1),
                (dx + math.sin(lean * D2R) * length * t,
                 head_center[1] - math.sin(tilt * D2R) * length * t,
                 top + length * (t + 0.5 / segments)),
                color=color,
            ))
    left = kit.join(parts, name + ".L")
    kit.weld(left)
    kit.set_origin_to(left, (dx, head_center[1], top))
    right = kit.duplicate(left, name + ".R", mirror=True)
    right.location = Vector((-left.location.x, left.location.y, left.location.z))
    return [left, right]


def horn_single(name, head_center, head_dims, size=0.08, length=0.26,
                color="#f0e2c4", tilt=-16.0, forward=0.3):
    top = head_center[2] + head_dims[2] * 0.5
    return [wedge(
        name, (size, size, length),
        (head_center[0], head_center[1] + head_dims[1] * 0.5 * forward,
         top + length * 0.45),
        rot=(tilt, 0, 0), color=color, taper=0.92,
    )]


def beak(name, head_center, head_dims, width=0.14, length=0.16, height=0.08,
         color="#ff9c2e", drop=-0.02, taper=0.7):
    front = head_center[1] + head_dims[1] * 0.5
    return [wedge(
        name, (width, height, length),
        (head_center[0], front + length * 0.42, head_center[2] + drop),
        rot=(-90, 0, 0), color=color, taper=taper,
    )]


def snout(name, head_center, head_dims, width=0.2, length=0.16, height=0.14,
          color="#e8c9a0", drop=-0.08, nose_color="#2e2226", nose=True):
    front = head_center[1] + head_dims[1] * 0.5
    center = (head_center[0], front + length * 0.42, head_center[2] + drop)
    dims = (width, length, height)
    parts = [block(name, dims, center, color=color)]
    if nose:
        parts.append(face_plate(
            name + ".nose", face_of(center, dims, "front"),
            (width * 0.42, height * 0.34), face="front", color=nose_color,
            depth=0.02, offset=(0, height * 0.16),
        ))
    return parts


def crest(name, head_center, head_dims, count=4, height=0.13, width=0.05,
          color="#ff5a4d", back=0.0, spacing=None):
    """A row of fins along the top centreline."""
    top = head_center[2] + head_dims[2] * 0.5
    spacing = spacing if spacing is not None else head_dims[1] / max(1, count) * 0.85
    parts = []
    for i in range(count):
        t = (i - (count - 1) / 2.0)
        s = 0.6 + 0.4 * math.sin(math.pi * ((i + 0.5) / count))
        parts.append(wedge(
            "%s.%d" % (name, i), (width, width * 1.6, height * s),
            (head_center[0], head_center[1] + back - t * spacing, top + height * s * 0.45),
            color=color, taper=0.8,
        ))
    return parts


def mane(name, head_center, head_dims, ring=0.14, thickness=0.09, count=10,
         color="#c8531f"):
    """A ring of blocks around the neck -- lions, dragons, ruffs."""
    parts = []
    rx = head_dims[0] * 0.5 + ring * 0.5
    rz = head_dims[2] * 0.5 + ring * 0.5
    for i in range(count):
        angle = (i / count) * 2 * math.pi
        parts.append(block(
            "%s.%d" % (name, i), (thickness, thickness * 0.9, thickness * 1.5),
            (head_center[0] + math.sin(angle) * rx,
             head_center[1] - head_dims[1] * 0.24,
             head_center[2] + math.cos(angle) * rz),
            rot=(0, math.degrees(angle), 0), color=color,
        ))
    return parts


def shell(name, at, dims=(0.5, 0.6, 0.28), color="#7a5a3a", rim_color="#a8834f",
          plates=5):
    parts = [block(name + ".dome", dims, at, color=color)]
    for i in range(plates):
        t = (i + 0.5) / plates
        parts.append(block(
            "%s.plate%d" % (name, i),
            (dims[0] * 0.24, dims[1] * 0.9, dims[2] * 0.16),
            (at[0] + dims[0] * (t - 0.5) * 0.86, at[1], at[2] + dims[2] * 0.5),
            color=rim_color,
        ))
    return parts


def spots(name, at, dims, count=6, size=0.09, color="#ffffff", seed=3,
          faces=("top", "left", "right")):
    """Deterministic surface patches on a box's faces."""
    parts = []
    state = seed * 7919 + 13
    for i in range(count):
        state = (state * 1103515245 + 12345) & 0x7FFFFFFF
        face = faces[state % len(faces)]
        state = (state * 1103515245 + 12345) & 0x7FFFFFFF
        u = ((state / 0x7FFFFFFF) - 0.5) * 0.62
        state = (state * 1103515245 + 12345) & 0x7FFFFFFF
        v = ((state / 0x7FFFFFFF) - 0.5) * 0.62
        state = (state * 1103515245 + 12345) & 0x7FFFFFFF
        s = size * (0.65 + (state / 0x7FFFFFFF) * 0.7)
        plane = face_of(at, dims, face)
        span_u = dims[0] if face in ("front", "back", "top") else dims[1]
        span_v = dims[2] if face != "top" else dims[1]
        parts.append(face_plate(
            "%s.%d" % (name, i), plane, (s, s), face=face, color=color,
            depth=0.016, offset=(u * span_u, v * span_v),
        ))
    return parts


def stripes(name, at, dims, count=4, width=0.06, color="#2b2b33", axis="y"):
    """Bands wrapped around a body block."""
    parts = []
    for i in range(count):
        t = (i + 0.5) / count - 0.5
        if axis == "y":
            parts.append(block(
                "%s.%d" % (name, i),
                (dims[0] * 1.02, width, dims[2] * 1.02),
                (at[0], at[1] + t * dims[1] * 0.86, at[2]), color=color,
            ))
        else:
            parts.append(block(
                "%s.%d" % (name, i),
                (width, dims[1] * 1.02, dims[2] * 1.02),
                (at[0] + t * dims[0] * 0.86, at[1], at[2]), color=color,
            ))
    return parts


def belly(name, at, dims, color="#fff2dc", inset=0.86, depth=0.02):
    """A lighter plate on the chest/underside."""
    return [face_plate(
        name, face_of(at, dims, "front"),
        (dims[0] * inset * 0.8, dims[2] * inset * 0.72), face="front",
        color=color, depth=depth, offset=(0, -dims[2] * 0.06),
    )]


def glow_block(name, dims, loc=(0, 0, 0), rot=(0, 0, 0), color="#5ce1ff",
               strength=2.6):
    """Neon part -- lava veins, cosmic cores, mecha optics."""
    material = kit.mat("neon." + color.strip("#"), kit.hexcol(color), rough=0.2,
                       emission=kit.hexcol(color), emission_strength=strength)
    return block(name, dims, loc, rot, material=material, segments=1)


def gem(name, loc, size=0.1, color="#5ce1ff", strength=3.0):
    material = kit.mat("gem." + color.strip("#"), kit.hexcol(color), rough=0.12,
                       emission=kit.hexcol(color), emission_strength=strength)
    obj = kit.ico(name, r=size * 0.5, subdiv=1, loc=loc, scale=(1, 1, 1.4),
                  material=material)
    kit.flat(obj)
    return [obj]


def ring(name, loc, radius=0.4, thickness=0.035, tilt=22.0, color="#c9a6ff",
         strength=1.6):
    material = kit.mat("ring." + color.strip("#"), kit.hexcol(color), rough=0.28,
                       emission=kit.hexcol(color), emission_strength=strength)
    obj = kit.torus(name, major=radius, minor=thickness, loc=loc,
                    rot=(tilt, 0, 12), material=material,
                    major_seg=22, minor_seg=6)
    kit.smooth(obj)
    return [obj]


# --------------------------------------------------------------------------
# assembly
# --------------------------------------------------------------------------


def assemble(root, groups):
    """
    `groups` maps a runtime part name to (parts, pivot); each becomes one welded
    mesh parented to `root` with its origin at pivot. Same contract as
    petkit.assemble, so a pet can mix boxy and rounded parts freely.
    """
    built = {}
    for part_name, spec in groups.items():
        parts, pivot = spec
        parts = [p for p in parts if p is not None]
        if not parts:
            continue
        merged = kit.group(part_name, parts, pivot=pivot)
        kit.parent_to(merged, root)
        built[part_name] = merged
    return built


def finish(root, height=1.0):
    """Normalise to `height` with feet on the floor. Call at the end of every pet."""
    kit.normalize_height(root, height)
    return root
