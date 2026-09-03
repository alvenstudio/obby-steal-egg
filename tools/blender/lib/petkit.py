"""
petkit.py -- anatomy helpers layered on top of kit.py.

kit.py knows about primitives. petkit.py knows about *creatures*: eyes that sit
on a skull's surface instead of sinking into it, ears that pivot where an ear
would actually pivot, tails that taper, paws that splay.

Every pet in the game is assembled from these, which is what keeps ~100
different animals looking like they came out of the same studio.

Two conventions do most of the work here:

*Facing.* Creatures face +Y. The glTF exporter maps Blender +Y to glTF -Z,
which is the forward axis three.js expects, so a pet authored facing +Y walks
the right way at runtime with no fixup.

*Protrusion.* Blender primitives are centred on their origin, so naively
placing a horn "at the surface" buries half of it. Every helper here instead
takes how far the feature should stick OUT of the body and solves for the
centre, which is why nothing sinks.
"""

from __future__ import annotations

import math

from mathutils import Vector

import kit

D2R = math.pi / 180.0


# --------------------------------------------------------------------------
# surface placement
# --------------------------------------------------------------------------


def on_sphere(center, radius, yaw=0.0, pitch=0.0, inset=0.0):
    """
    A point on a sphere's surface. `yaw` swings around Z from straight-ahead
    (+Y); positive yaw goes to the creature's left (+X). `pitch` lifts toward
    +Z. `inset` pulls the point inward along the normal.
    """
    r = radius - inset
    y = yaw * D2R
    p = pitch * D2R
    return (
        center[0] + r * math.cos(p) * math.sin(y),
        center[1] + r * math.cos(p) * math.cos(y),
        center[2] + r * math.sin(p),
    )


def normal_at(yaw=0.0, pitch=0.0):
    """Outward unit normal for a (yaw, pitch) pair."""
    y = yaw * D2R
    p = pitch * D2R
    return Vector((
        math.cos(p) * math.sin(y),
        math.cos(p) * math.cos(y),
        math.sin(p),
    ))


def stick_out(center, radius, yaw, pitch, extent, out):
    """
    Centre for a primitive of length `extent` along the surface normal whose
    tip should end up `out` beyond the surface. This is the single fix for
    "my horns disappeared into the skull".
    """
    return on_sphere(center, radius + out - extent * 0.5, yaw=yaw, pitch=pitch)


def aim_from(center, point):
    """Euler (degrees) that points a +Z-aligned primitive outward from `center`."""
    direction = Vector(point) - Vector(center)
    if direction.length < 1e-6:
        return (0.0, 0.0, 0.0)
    euler = direction.to_track_quat("Z", "Y").to_euler()
    return (euler.x / D2R, euler.y / D2R, euler.z / D2R)


def aim_along(yaw=0.0, pitch=0.0):
    """Euler (degrees) aligning a +Z primitive with the (yaw, pitch) normal."""
    euler = normal_at(yaw, pitch).to_track_quat("Z", "Y").to_euler()
    return (euler.x / D2R, euler.y / D2R, euler.z / D2R)


def _mirror(obj, base_name):
    """Make `obj` the .L half and return (.L, .R)."""
    obj.name = base_name + ".L"
    obj.data.name = obj.name
    right = kit.duplicate(obj, base_name + ".R", mirror=True)
    right.location = Vector((-obj.location.x, obj.location.y, obj.location.z))
    right.scale = obj.scale.copy()
    right.rotation_euler = obj.rotation_euler.copy()
    right.rotation_euler.y = -right.rotation_euler.y
    right.rotation_euler.z = -right.rotation_euler.z
    return obj, right


# --------------------------------------------------------------------------
# eyes
# --------------------------------------------------------------------------


def eye_materials(iris="#20191a", sclera="#ffffff", glint="#ffffff"):
    return (
        kit.mat("eye.sclera." + sclera.strip("#"), kit.hexcol(sclera), rough=0.24),
        kit.mat("eye.iris." + iris.strip("#"), kit.hexcol(iris), rough=0.18),
        kit.mat("eye.glint." + glint.strip("#"), kit.hexcol(glint), rough=0.05,
                emission=kit.hexcol(glint), emission_strength=0.5),
    )


def eyes(
    name,
    center,
    radius,
    yaw=30.0,
    pitch=8.0,
    size=0.12,
    style="round",
    iris="#20191a",
    sclera="#ffffff",
    squash=1.0,
    bulge=0.5,
    glint=True,
):
    """
    A mirrored pair of cartoon eyes sitting ON the skull.

    `size` is the eye's full width. `bulge` is how much of the eyeball's radius
    pokes out past the skull (0 = flush decal, 1 = full googly ball).

    style:
        round  -- sclera + iris + glint, the default
        bead   -- solid dark bead, no sclera (birds, bugs, fish)
        pie    -- oversized anime iris filling most of the sclera
        sleepy -- wide half-lidded lens
    """
    sclera_mat, iris_mat, glint_mat = eye_materials(iris, sclera)
    r = size * 0.5
    parts = []

    # the eyeball's centre sits so that `bulge * r` of it clears the skull
    ball_center = on_sphere(center, radius + r * bulge - r, yaw=yaw, pitch=pitch)
    surface = radius + r * bulge

    if style == "bead":
        ball = kit.sphere(name + ".ball", r=r, loc=ball_center,
                          scale=(1, 1, squash), material=iris_mat,
                          segments=12, rings=8)
        kit.smooth(ball)
        parts.append(ball)
    else:
        white_scale = {
            "round": (1.0, 1.0, squash * 1.06),
            "pie": (1.0, 1.0, squash * 1.16),
            "sleepy": (1.2, 1.0, squash * 0.52),
        }[style]
        white = kit.sphere(name + ".sclera", r=r, loc=ball_center,
                           scale=white_scale, material=sclera_mat,
                           segments=14, rings=9)
        kit.smooth(white)
        parts.append(white)

        iris_r = {"round": 0.56, "pie": 0.8, "sleepy": 0.5}[style] * r
        # the iris rides on the outer face of the sclera
        iris_center = on_sphere(center, surface - iris_r * 0.45, yaw=yaw, pitch=pitch)
        pupil = kit.sphere(name + ".iris", r=iris_r, loc=iris_center,
                           scale=(1, 1, 1), material=iris_mat,
                           segments=12, rings=8)
        kit.smooth(pupil)
        parts.append(pupil)

    if glint:
        glint_r = r * 0.22
        gpos = on_sphere(center, surface - glint_r * 0.3,
                         yaw=yaw + size * 26.0, pitch=pitch + size * 34.0)
        dot = kit.sphere(name + ".glint", r=glint_r, loc=gpos,
                         material=glint_mat, segments=8, rings=5)
        kit.smooth(dot)
        parts.append(dot)

    merged = kit.join(parts, name + ".L")
    left, right = _mirror(merged, name)
    return [left, right]


def eye_single(name, center, radius, pitch=8.0, size=0.2, iris="#20191a",
               sclera="#ffffff", bulge=0.55):
    """One big cyclops eye, dead centre."""
    sclera_mat, iris_mat, glint_mat = eye_materials(iris, sclera)
    r = size * 0.5
    ball_center = on_sphere(center, radius + r * bulge - r, yaw=0, pitch=pitch)
    surface = radius + r * bulge
    white = kit.sphere(name + ".sclera", r=r, loc=ball_center, material=sclera_mat,
                       segments=16, rings=10)
    kit.smooth(white)
    pupil = kit.sphere(name + ".iris", r=r * 0.6,
                       loc=on_sphere(center, surface - r * 0.27, yaw=0, pitch=pitch),
                       material=iris_mat, segments=14, rings=9)
    kit.smooth(pupil)
    dot = kit.sphere(name + ".glint", r=r * 0.2,
                     loc=on_sphere(center, surface - r * 0.06, yaw=13, pitch=pitch + 16),
                     material=glint_mat, segments=8, rings=5)
    kit.smooth(dot)
    return [white, pupil, dot]


def brows(name, center, radius, yaw=30.0, pitch=26.0, size=0.11,
          tilt=-16.0, color="#20191a"):
    """Eyebrow slabs. Negative tilt reads angry, positive reads worried."""
    material = kit.mat("brow." + color.strip("#"), kit.hexcol(color))
    thickness = size * 0.3
    pos = stick_out(center, radius, yaw, pitch, thickness, out=thickness * 0.45)
    rot = aim_along(yaw, pitch)
    brow = kit.box(name + ".L", dims=(size * 1.6, size * 0.42, thickness),
                   loc=pos, rot=(rot[0], rot[1] + tilt, rot[2]), material=material)
    kit.bevel(brow, thickness * 0.2, 1)
    return list(_mirror(brow, name))


def blush(name, center, radius, yaw=48.0, pitch=-10.0, size=0.12, color="#ff8fa3"):
    material = kit.mat("blush." + color.strip("#"), kit.hexcol(color), rough=0.9)
    depth = size * 0.3
    pos = stick_out(center, radius, yaw, pitch, depth, out=depth * 0.28)
    rot = aim_along(yaw, pitch)
    patch = kit.sphere(name + ".L", r=0.5, loc=pos, rot=rot,
                       scale=(size, size * 0.72, depth),
                       material=material, segments=12, rings=7)
    kit.smooth(patch)
    return list(_mirror(patch, name))


# --------------------------------------------------------------------------
# faces
# --------------------------------------------------------------------------


def beak(name, center, radius, length=0.24, width=0.14, pitch=-4.0,
         color="#ff9c2e", open_gap=0.0):
    """Cone beak seated on the skull, pointing forward along the normal."""
    material = kit.mat("beak." + color.strip("#"), kit.hexcol(color), rough=0.55)
    rot = aim_along(0.0, pitch)
    parts = []
    if open_gap <= 0.0:
        pos = stick_out(center, radius, 0.0, pitch, length, out=length * 0.78)
        cone = kit.cone(name, r1=width * 0.5, r2=0.0, h=length, loc=pos,
                        rot=rot, material=material, verts=10)
        kit.flat(cone)
        parts.append(cone)
    else:
        up = stick_out(center, radius, 0.0, pitch + 6, length, out=length * 0.78)
        lo = stick_out(center, radius, 0.0, pitch - 6, length * 0.82, out=length * 0.62)
        upper = kit.cone(name + ".upper", r1=width * 0.5, r2=0.0, h=length,
                         loc=(up[0], up[1], up[2] + open_gap * 0.4),
                         rot=aim_along(0.0, pitch + 10), material=material, verts=10)
        lower = kit.cone(name + ".lower", r1=width * 0.44, r2=0.0, h=length * 0.82,
                         loc=(lo[0], lo[1], lo[2] - open_gap * 0.5),
                         rot=aim_along(0.0, pitch - 16), material=material, verts=10)
        kit.flat(upper)
        kit.flat(lower)
        parts += [upper, lower]
    return parts


def beak_duck(name, center, radius, length=0.3, width=0.22, pitch=-8.0,
              color="#ffb42e"):
    """Flat rounded bill."""
    material = kit.mat("beak." + color.strip("#"), kit.hexcol(color), rough=0.55)
    pos = stick_out(center, radius, 0.0, pitch, length, out=length * 0.62)
    bill = kit.sphere(name, r=0.5, loc=pos, rot=aim_along(0.0, pitch),
                      scale=(width, width * 0.36, length),
                      material=material, segments=14, rings=9)
    kit.smooth(bill)
    return [bill]


def snout(name, center, radius, length=0.28, width=0.2, height=0.17, pitch=-12.0,
          color="#e8c9a0", nose_color="#3a2b24", nose=True, out=None):
    """
    Rounded muzzle. `length` is the full forward extent of the muzzle; `out` is
    how far it clears the skull (defaults to 40% of its length).
    """
    material = kit.mat("snout." + color.strip("#"), kit.hexcol(color))
    if out is None:
        out = length * 0.42
    pos = stick_out(center, radius, 0.0, pitch, length, out=out)
    rot = aim_along(0.0, pitch)
    muzzle = kit.sphere(name, r=0.5, loc=pos, rot=rot,
                        scale=(width, height, length), material=material,
                        segments=14, rings=9)
    kit.smooth(muzzle)
    parts = [muzzle]
    if nose:
        nose_mat = kit.mat("nose." + nose_color.strip("#"),
                           kit.hexcol(nose_color), rough=0.3)
        # the nose button rides on the muzzle's front face, not out in space:
        # `out` already measures to the muzzle tip, so bed the button just
        # inside it rather than adding the muzzle's length a second time.
        nose_r = width * 0.3
        tip = kit.sphere(
            name + ".nose", r=nose_r * 0.5,
            loc=stick_out(center, radius, 0.0, pitch + 5,
                          nose_r, out=out + nose_r * 0.34),
            rot=rot, scale=(2.4, 1.7, 1.8), material=nose_mat,
            segments=12, rings=7,
        )
        kit.smooth(tip)
        parts.append(tip)
    return parts


def mouth_line(name, center, radius, width=0.18, pitch=-26.0, color="#4a3128",
               thickness=0.026, curve=0.0):
    """A simple mouth. `curve` > 0 arcs it into a smile."""
    material = kit.mat("mouth." + color.strip("#"), kit.hexcol(color))
    parts = []
    steps = 3 if curve else 1
    for i in range(steps):
        t = 0.0 if steps == 1 else (i / (steps - 1)) * 2.0 - 1.0
        yaw = t * (width * 42.0)
        drop = -abs(t) * curve * 12.0
        pos = stick_out(center, radius, yaw, pitch + drop, thickness,
                        out=thickness * 0.4)
        seg = kit.box(name + ".%d" % i,
                      dims=(width / steps * 1.5, thickness * 1.3, thickness),
                      loc=pos, rot=aim_along(yaw, pitch + drop), material=material)
        parts.append(seg)
    return parts


def fangs(name, center, radius, count=2, size=0.06, pitch=-22.0, spread=13.0,
          color="#fffaf0", down=True):
    """Little teeth poking out of the mouth line."""
    material = kit.mat("fang." + color.strip("#"), kit.hexcol(color), rough=0.3)
    parts = []
    length = size * 2.2
    for i in range(count):
        side = -1 if i % 2 else 1
        yaw = side * spread * (1 + i // 2)
        pos = stick_out(center, radius, yaw, pitch, length, out=length * 0.34)
        rot = aim_along(yaw, pitch)
        tooth = kit.cone(name + ".%d" % i, r1=size * 0.5, r2=0.0, h=length,
                         loc=pos, rot=rot, material=material, verts=6)
        if down:
            tooth.rotation_euler.x += 150 * D2R
        kit.flat(tooth)
        parts.append(tooth)
    return parts


def tusks(name, center, radius, size=0.07, pitch=-16.0, spread=22.0, length=0.3,
          color="#f7efdc", curve=0.1):
    material = kit.mat("tusk." + color.strip("#"), kit.hexcol(color), rough=0.35)
    parts = []
    for side in (1, -1):
        yaw = side * spread
        pos = stick_out(center, radius, yaw, pitch, length, out=length * 0.66)
        tusk = kit.cone(name + (".L" if side > 0 else ".R"),
                        r1=size * 0.5, r2=size * 0.06, h=length, loc=pos,
                        rot=aim_along(yaw, pitch + 26), material=material, verts=7)
        kit.bend_z(tusk, curve * side)
        kit.flat(tusk)
        parts.append(tusk)
    return parts


def tongue(name, center, radius, length=0.18, width=0.1, pitch=-28.0,
           color="#ff7a94"):
    material = kit.mat("tongue." + color.strip("#"), kit.hexcol(color), rough=0.4)
    pos = stick_out(center, radius, 0.0, pitch, length, out=length * 0.6)
    lick = kit.sphere(name, r=0.5, loc=pos, rot=aim_along(0.0, pitch - 22),
                      scale=(width, width * 0.4, length), material=material,
                      segments=10, rings=6)
    kit.smooth(lick)
    return [lick]


def whiskers(name, center, radius, yaw=52.0, pitch=-6.0, count=3, length=0.28,
             color="#f4ece0", thickness=0.012, fan=13.0):
    """
    Straight bristles sweeping outward and forward from the muzzle. Built as
    thin boxes aligned to X so they read as lines from any angle instead of
    collapsing into blobs.
    """
    material = kit.mat("whisker." + color.strip("#"), kit.hexcol(color))
    parts = []
    for i in range(count):
        drop = (i - (count - 1) / 2.0) * fan
        base = on_sphere(center, radius * 0.92, yaw=yaw, pitch=pitch + drop)
        hair = kit.box(
            name + ".%d" % i,
            dims=(length, thickness, thickness),
            loc=(base[0] + length * 0.5, base[1], base[2]),
            rot=(0, -drop * 0.55, -18.0), material=material,
        )
        parts.append(hair)
    merged = kit.join(parts, name + ".L")
    return list(_mirror(merged, name))


# --------------------------------------------------------------------------
# ears, horns, antennae
# --------------------------------------------------------------------------


def ear_round(name, center, radius, yaw=54.0, pitch=48.0, size=0.26,
              color="#e0a86a", inner_color="#ffc9d4", thickness=0.35):
    """Mouse/bear disc ear. Returns (left, right) as separately pivoted meshes."""
    outer_mat = kit.mat("ear." + color.strip("#"), kit.hexcol(color))
    inner_mat = kit.mat("earin." + inner_color.strip("#"), kit.hexcol(inner_color))
    depth = size * thickness
    pos = stick_out(center, radius, yaw, pitch, depth, out=depth * 0.3)
    rot = aim_along(yaw, pitch)

    disc = kit.sphere(name + ".outer", r=0.5, loc=pos, rot=rot,
                      scale=(size, size, depth), material=outer_mat,
                      segments=16, rings=10)
    kit.smooth(disc)
    inner = kit.sphere(
        name + ".inner", r=0.5,
        loc=stick_out(center, radius, yaw, pitch, depth, out=depth * 0.62),
        rot=rot, scale=(size * 0.6, size * 0.6, depth * 0.75),
        material=inner_mat, segments=14, rings=9,
    )
    kit.smooth(inner)

    left = kit.join([disc, inner], name + ".L")
    kit.weld(left)
    kit.set_origin_to(left, on_sphere(center, radius * 0.86, yaw=yaw, pitch=pitch))
    right = kit.duplicate(left, name + ".R", mirror=True)
    right.location = Vector((-left.location.x, left.location.y, left.location.z))
    return left, right


def ear_pointed(name, center, radius, yaw=36.0, pitch=62.0, length=0.4,
                width=0.17, color="#e0a86a", inner_color="#ffc9d4", lean=0.0):
    """Cat/fox/rabbit spire ear standing proud of the skull."""
    outer_mat = kit.mat("ear." + color.strip("#"), kit.hexcol(color))
    inner_mat = kit.mat("earin." + inner_color.strip("#"), kit.hexcol(inner_color))
    rot = aim_along(yaw, pitch)
    rot = (rot[0], rot[1] + lean, rot[2])

    pos = stick_out(center, radius, yaw, pitch, length, out=length * 0.82)
    shell = kit.cone(name + ".outer", r1=width * 0.5, r2=width * 0.04, h=length,
                     loc=pos, rot=rot, material=outer_mat, verts=9)
    kit.flat(shell)
    inner = kit.cone(
        name + ".inner", r1=width * 0.28, r2=0.0, h=length * 0.68,
        loc=stick_out(center, radius + length * 0.06, yaw, pitch,
                      length * 0.68, out=length * 0.6),
        rot=rot, material=inner_mat, verts=8,
    )
    kit.flat(inner)

    left = kit.join([shell, inner], name + ".L")
    kit.weld(left)
    kit.set_origin_to(left, on_sphere(center, radius * 0.88, yaw=yaw, pitch=pitch))
    right = kit.duplicate(left, name + ".R", mirror=True)
    right.location = Vector((-left.location.x, left.location.y, left.location.z))
    return left, right


def ear_long(name, center, radius, yaw=22.0, pitch=72.0, length=0.62,
             width=0.15, color="#e6dccc", inner_color="#ffc9d4", lean=8.0):
    """Rabbit ear: a tall rounded blade rather than a cone."""
    outer_mat = kit.mat("ear." + color.strip("#"), kit.hexcol(color))
    inner_mat = kit.mat("earin." + inner_color.strip("#"), kit.hexcol(inner_color))
    rot = aim_along(yaw, pitch)
    rot = (rot[0], rot[1] + lean, rot[2])
    pos = stick_out(center, radius, yaw, pitch, length, out=length * 0.86)
    blade = kit.sphere(name + ".outer", r=0.5, loc=pos, rot=rot,
                       scale=(width, width * 0.45, length),
                       material=outer_mat, segments=12, rings=10)
    kit.smooth(blade)
    inner = kit.sphere(
        name + ".inner", r=0.5,
        loc=stick_out(center, radius, yaw, pitch, length * 0.82,
                      out=length * 0.8),
        rot=rot, scale=(width * 0.52, width * 0.36, length * 0.78),
        material=inner_mat, segments=10, rings=8,
    )
    kit.smooth(inner)
    left = kit.join([blade, inner], name + ".L")
    kit.weld(left)
    kit.set_origin_to(left, on_sphere(center, radius * 0.9, yaw=yaw, pitch=pitch))
    right = kit.duplicate(left, name + ".R", mirror=True)
    right.location = Vector((-left.location.x, left.location.y, left.location.z))
    return left, right


def ear_floppy(name, center, radius, yaw=66.0, pitch=18.0, length=0.44,
               width=0.18, color="#c98a5a", droop=42.0):
    """Long hanging ear -- dogs, elephants, resting bunnies."""
    material = kit.mat("ear." + color.strip("#"), kit.hexcol(color))
    anchor = on_sphere(center, radius * 0.94, yaw=yaw, pitch=pitch)
    flap = kit.sphere(name + ".L", r=0.5,
                      loc=(anchor[0] + width * 0.2, anchor[1], anchor[2] - length * 0.42),
                      scale=(width, width * 0.5, length),
                      material=material, segments=12, rings=9)
    kit.smooth(flap)
    kit.set_origin_to(flap, anchor)
    flap.rotation_euler = (0.0, -droop * D2R, 0.0)
    right = kit.duplicate(flap, name + ".R", mirror=True)
    right.location = Vector((-flap.location.x, flap.location.y, flap.location.z))
    right.rotation_euler = (0.0, droop * D2R, 0.0)
    return flap, right


def horn(name, center, radius, yaw=28.0, pitch=62.0, length=0.32, width=0.1,
         color="#f0e2c4", curve=0.0, ridged=False):
    material = kit.mat("horn." + color.strip("#"), kit.hexcol(color), rough=0.45)
    parts = []
    pos = stick_out(center, radius, yaw, pitch, length, out=length * 0.8)
    rot = aim_along(yaw, pitch)
    spike = kit.cone(name + ".L", r1=width * 0.5, r2=width * 0.04, h=length,
                     loc=pos, rot=rot, material=material, verts=8)
    if curve:
        kit.bend_z(spike, curve)
    kit.flat(spike)
    if ridged:
        rings = []
        for i in range(3):
            t = (i + 1) / 4.0
            ring = kit.torus(
                name + ".ring%d" % i, major=width * 0.5 * (1.0 - t * 0.55),
                minor=width * 0.11,
                loc=stick_out(center, radius, yaw, pitch, length, out=length * (0.8 - t * 0.6)),
                rot=rot, material=material, major_seg=8, minor_seg=5,
            )
            rings.append(ring)
        spike = kit.join([spike] + rings, name + ".L")
        kit.weld(spike)
    parts.append(spike)
    right = kit.duplicate(spike, name + ".R", mirror=True)
    right.location = Vector((-spike.location.x, spike.location.y, spike.location.z))
    parts.append(right)
    return parts


def horn_single(name, center, radius, pitch=64.0, length=0.36, width=0.1,
                color="#f0e2c4", ridged=True):
    """Unicorn/narwhal spire on the centreline."""
    material = kit.mat("horn." + color.strip("#"), kit.hexcol(color), rough=0.4)
    pos = stick_out(center, radius, 0.0, pitch, length, out=length * 0.82)
    rot = aim_along(0.0, pitch)
    spike = kit.cone(name, r1=width * 0.5, r2=0.0, h=length, loc=pos, rot=rot,
                     material=material, verts=8)
    kit.flat(spike)
    parts = [spike]
    if ridged:
        for i in range(4):
            t = (i + 1) / 5.0
            ring = kit.torus(
                name + ".ring%d" % i, major=width * 0.5 * (1.0 - t * 0.7),
                minor=width * 0.1,
                loc=stick_out(center, radius, 0.0, pitch, length,
                              out=length * (0.82 - t * 0.62)),
                rot=rot, material=material, major_seg=8, minor_seg=5,
            )
            parts.append(ring)
    return parts


def antler(name, center, radius, yaw=28.0, pitch=58.0, length=0.34, width=0.055,
           color="#9a6f42", prongs=2):
    material = kit.mat("antler." + color.strip("#"), kit.hexcol(color), rough=0.6)
    rot = aim_along(yaw, pitch)
    pos = stick_out(center, radius, yaw, pitch, length, out=length * 0.82)
    beam = kit.cone(name + ".beam", r1=width * 0.5, r2=width * 0.22, h=length,
                    loc=pos, rot=rot, material=material, verts=6)
    kit.flat(beam)
    parts = [beam]
    for i in range(prongs):
        t = 0.35 + 0.4 * (i / max(1, prongs - 1) if prongs > 1 else 0)
        tine_len = length * (0.5 - 0.12 * i)
        tine = kit.cone(
            name + ".tine%d" % i, r1=width * 0.34, r2=0.0, h=tine_len,
            loc=stick_out(center, radius, yaw + 12 + i * 8, pitch + 6,
                          tine_len, out=length * t + tine_len * 0.3),
            rot=aim_along(yaw + 34 + i * 12, pitch + 16),
            material=material, verts=5,
        )
        kit.flat(tine)
        parts.append(tine)
    left = kit.join(parts, name + ".L")
    kit.weld(left)
    kit.set_origin_to(left, on_sphere(center, radius * 0.9, yaw=yaw, pitch=pitch))
    right = kit.duplicate(left, name + ".R", mirror=True)
    right.location = Vector((-left.location.x, left.location.y, left.location.z))
    return [left, right]


def antenna(name, center, radius, yaw=16.0, pitch=76.0, length=0.36,
            stalk=0.03, bulb=0.08, color="#3d3348", bulb_color="#ffe36b",
            glow=False):
    stalk_mat = kit.mat("ant." + color.strip("#"), kit.hexcol(color))
    bulb_mat = kit.mat(
        "antbulb." + bulb_color.strip("#"), kit.hexcol(bulb_color),
        emission=kit.hexcol(bulb_color) if glow else None,
        emission_strength=2.6,
    )
    rot = aim_along(yaw, pitch)
    rod = kit.cyl(name + ".rod", r=stalk * 0.5, h=length,
                  loc=stick_out(center, radius, yaw, pitch, length, out=length * 0.86),
                  rot=rot, material=stalk_mat, verts=6)
    knob = kit.sphere(name + ".bulb", r=bulb * 0.5,
                      loc=on_sphere(center, radius + length * 0.86 + bulb * 0.35,
                                    yaw=yaw, pitch=pitch),
                      material=bulb_mat, segments=10, rings=7)
    kit.smooth(knob)
    left = kit.join([rod, knob], name + ".L")
    kit.weld(left)
    kit.set_origin_to(left, on_sphere(center, radius * 0.9, yaw=yaw, pitch=pitch))
    right = kit.duplicate(left, name + ".R", mirror=True)
    right.location = Vector((-left.location.x, left.location.y, left.location.z))
    return [left, right]


def crest(name, center, radius, count=5, height=0.2, width=0.08,
          pitch_from=34.0, pitch_to=88.0, color="#ff5a4d", yaw=0.0, taper=True):
    """A row of spines along the skull ridge or spine."""
    material = kit.mat("crest." + color.strip("#"), kit.hexcol(color))
    parts = []
    for i in range(count):
        t = i / max(1, count - 1)
        pitch = pitch_from + (pitch_to - pitch_from) * t
        scale = (0.55 + 0.45 * math.sin(math.pi * t)) if taper else 1.0
        h = height * scale
        fin = kit.cone(name + ".%d" % i, r1=width * scale * 0.5, r2=0.0, h=h,
                       loc=stick_out(center, radius, yaw, pitch, h, out=h * 0.78),
                       rot=aim_along(yaw, pitch), material=material, verts=6)
        kit.flat(fin)
        parts.append(fin)
    return parts


def plume(name, center, radius, pitch=84.0, count=3, height=0.28, width=0.07,
          color="#ff5a4d", spread=16.0):
    """A little feather/leaf tuft on top of the head."""
    material = kit.mat("plume." + color.strip("#"), kit.hexcol(color))
    parts = []
    for i in range(count):
        offset = (i - (count - 1) / 2.0) * spread
        h = height * (1.0 - abs(i - (count - 1) / 2.0) * 0.18)
        blade = kit.sphere(
            name + ".%d" % i, r=0.5,
            loc=stick_out(center, radius, offset, pitch, h, out=h * 0.78),
            rot=aim_along(offset, pitch),
            scale=(width, width * 0.4, h), material=material,
            segments=10, rings=7,
        )
        kit.smooth(blade)
        parts.append(blade)
    return parts


# --------------------------------------------------------------------------
# limbs
# --------------------------------------------------------------------------


def leg(name, at, length=0.34, thickness=0.1, color="#c98a5a",
        paw=True, paw_color=None, splay=0.0):
    """One leg with an optional paw. `at` is the hip joint in world space."""
    material = kit.mat("limb." + color.strip("#"), kit.hexcol(color))
    shaft = kit.capsule(name + ".shaft", r=thickness * 0.5, h=length,
                        loc=(at[0], at[1], at[2] - length * 0.5),
                        rot=(0, splay, 0), material=material, verts=10)
    parts = [shaft]
    if paw:
        pmat = kit.mat("paw." + (paw_color or color).strip("#"),
                       kit.hexcol(paw_color or color))
        foot = kit.sphere(name + ".paw", r=0.5,
                          loc=(at[0], at[1] + thickness * 0.24,
                               at[2] - length - thickness * 0.12),
                          scale=(thickness * 1.25, thickness * 1.75, thickness * 0.8),
                          material=pmat, segments=12, rings=8)
        kit.smooth(foot)
        parts.append(foot)
    merged = kit.join(parts, name)
    kit.weld(merged)
    kit.set_origin_to(merged, at)
    return merged


def legs_quad(name_prefix, front, back, length=0.34, thickness=0.1,
              color="#c98a5a", paw_color=None, paw=True):
    """
    Four legs from two hip positions given as (x, y, z), where x is the left
    side. Returns a dict keyed by the runtime's step-cycle names.
    """
    out = {}
    for tag, at in (("F", front), ("B", back)):
        left = leg("%s.%sL" % (name_prefix, tag), at, length, thickness,
                   color, paw, paw_color)
        right = kit.duplicate(left, "%s.%sR" % (name_prefix, tag), mirror=True)
        right.location = Vector((-left.location.x, left.location.y, left.location.z))
        out["%s.%sL" % (name_prefix, tag)] = left
        out["%s.%sR" % (name_prefix, tag)] = right
    return out


def legs_bird(name_prefix, at, shin=0.16, thickness=0.05, toe_len=0.22,
              toe_width=0.15, color="#ff9c2e"):
    """Stick shin plus a flat three-toe foot; returns leg.FL / leg.FR."""
    material = kit.mat("limb." + color.strip("#"), kit.hexcol(color))
    out = {}
    shaft = kit.cyl(name_prefix + ".FL.shin", r=thickness * 0.5, h=shin,
                    loc=(at[0], at[1], at[2] - shin * 0.5),
                    material=material, verts=8)
    parts = [shaft]
    for i, spread in enumerate((-22.0, 0.0, 22.0)):
        toe = kit.box(name_prefix + ".FL.toe%d" % i,
                      dims=(toe_width * 0.3, toe_len, thickness * 0.75),
                      loc=(at[0], at[1] + toe_len * 0.34, at[2] - shin - thickness * 0.3),
                      rot=(0, 0, spread), material=material)
        kit.bevel(toe, thickness * 0.16, 1)
        parts.append(toe)
    left = kit.join(parts, name_prefix + ".FL")
    kit.weld(left)
    kit.set_origin_to(left, at)
    right = kit.duplicate(left, name_prefix + ".FR", mirror=True)
    right.location = Vector((-left.location.x, left.location.y, left.location.z))
    out[name_prefix + ".FL"] = left
    out[name_prefix + ".FR"] = right
    return out


def arm(name, at, length=0.3, thickness=0.085, color="#c98a5a",
        hand=True, hand_color=None, angle=18.0):
    material = kit.mat("limb." + color.strip("#"), kit.hexcol(color))
    dx = math.sin(angle * D2R)
    dz = math.cos(angle * D2R)
    shaft = kit.capsule(name + ".shaft", r=thickness * 0.5, h=length,
                        loc=(at[0] + dx * length * 0.5, at[1], at[2] - dz * length * 0.5),
                        rot=(0, angle, 0), material=material, verts=9)
    parts = [shaft]
    if hand:
        hmat = kit.mat("paw." + (hand_color or color).strip("#"),
                       kit.hexcol(hand_color or color))
        mitt = kit.sphere(name + ".hand", r=thickness * 0.72,
                          loc=(at[0] + dx * length, at[1], at[2] - dz * length),
                          material=hmat, segments=10, rings=7)
        kit.smooth(mitt)
        parts.append(mitt)
    merged = kit.join(parts, name + ".L")
    kit.weld(merged)
    kit.set_origin_to(merged, at)
    right = kit.duplicate(merged, name + ".R", mirror=True)
    right.location = Vector((-merged.location.x, merged.location.y, merged.location.z))
    return merged, right


def wing_feather(name, at, span=0.5, height=0.38, color="#f2f2f6",
                 tilt=14.0, layers=3, tip_color=None, sweep=0.3):
    """
    Layered bird wing built OUTWARD from the shoulder point `at`, so it always
    clears the torso. `span` is how far the wing reaches sideways.
    """
    material = kit.mat("wing." + color.strip("#"), kit.hexcol(color))
    tip_mat = kit.mat("wingtip." + (tip_color or color).strip("#"),
                      kit.hexcol(tip_color or color))
    parts = []
    for i in range(layers):
        t = i / max(1, layers - 1)
        seg_span = span * (1.0 - 0.16 * t)
        blade = kit.sphere(
            name + ".f%d" % i, r=0.5,
            loc=(at[0] + span * 0.5,
                 at[1] - height * sweep * t,
                 at[2] - height * 0.3 * t),
            rot=(0, -tilt - 14 * t, 0),
            scale=(seg_span, height * 0.3, height * (1.0 - 0.18 * t)),
            material=tip_mat if (tip_color and i == layers - 1) else material,
            segments=12, rings=8,
        )
        kit.smooth(blade)
        parts.append(blade)
    left = kit.join(parts, name + ".L")
    kit.weld(left)
    kit.set_origin_to(left, at)
    right = kit.duplicate(left, name + ".R", mirror=True)
    right.location = Vector((-left.location.x, left.location.y, left.location.z))
    return left, right


def wing_membrane(name, at, span=0.6, height=0.52, color="#6b3f8f",
                  fingers=3, tilt=18.0, bone_color=None, thickness=0.05):
    """Bat/dragon wing: a webbed sheet with finger struts, built outward."""
    web = kit.mat("web." + color.strip("#"), kit.hexcol(color), rough=0.6)
    bone = kit.mat("wbone." + (bone_color or color).strip("#"),
                   kit.hexcol(bone_color or color))
    parts = []
    sheet = kit.sphere(name + ".web", r=0.5,
                       loc=(at[0] + span * 0.5, at[1] - height * 0.12, at[2] + height * 0.08),
                       rot=(0, -tilt, 0),
                       scale=(span, thickness, height),
                       material=web, segments=14, rings=10)
    kit.smooth(sheet)
    parts.append(sheet)
    for i in range(fingers):
        t = (i + 1) / (fingers + 1)
        bone_len = height * (1.0 - 0.22 * t)
        strut = kit.cyl(
            name + ".bone%d" % i, r=span * 0.022, h=bone_len,
            loc=(at[0] + span * t, at[1] - height * 0.12, at[2] + height * 0.08),
            rot=(0, -tilt, 0), material=bone, verts=6,
        )
        parts.append(strut)
    spar = kit.cyl(name + ".spar", r=span * 0.03, h=span,
                   loc=(at[0] + span * 0.5, at[1] - height * 0.12, at[2] + height * 0.44),
                   rot=(0, 90, 0), material=bone, verts=6)
    parts.append(spar)
    left = kit.join(parts, name + ".L")
    kit.weld(left)
    kit.set_origin_to(left, at)
    right = kit.duplicate(left, name + ".R", mirror=True)
    right.location = Vector((-left.location.x, left.location.y, left.location.z))
    return left, right


def wing_insect(name, at, span=0.5, height=0.42, color="#a8e8ff", pairs=2,
                alpha=0.62, tilt=22.0):
    """Translucent bug/fairy wings -- two overlapping pairs."""
    material = kit.mat("iwing." + color.strip("#"), kit.hexcol(color),
                       rough=0.15, alpha=alpha,
                       emission=kit.hexcol(color), emission_strength=0.35)
    parts = []
    for i in range(pairs):
        t = i / max(1, pairs - 1) if pairs > 1 else 0.0
        blade = kit.sphere(
            name + ".p%d" % i, r=0.5,
            loc=(at[0] + span * 0.48, at[1] - height * 0.34 * t, at[2] + height * 0.16 * (1 - t)),
            rot=(0, -tilt + 12 * t, 26 - 18 * t),
            scale=(span * (1.0 - 0.22 * t), span * 0.045, height * (1.0 - 0.26 * t)),
            material=material, segments=12, rings=8,
        )
        kit.smooth(blade)
        parts.append(blade)
    left = kit.join(parts, name + ".L")
    kit.weld(left)
    kit.set_origin_to(left, at)
    right = kit.duplicate(left, name + ".R", mirror=True)
    right.location = Vector((-left.location.x, left.location.y, left.location.z))
    return left, right


def fin(name, at, size=0.28, color="#4fa8d8", tilt=26.0, thickness=0.05):
    """Side fins/flippers, built outward from the body."""
    material = kit.mat("fin." + color.strip("#"), kit.hexcol(color), rough=0.4)
    blade = kit.sphere(name + ".L", r=0.5,
                       loc=(at[0] + size * 0.5, at[1] - size * 0.1, at[2] - size * 0.1),
                       rot=(0, -tilt, 18.0),
                       scale=(size, thickness, size * 0.75),
                       material=material, segments=12, rings=8)
    kit.smooth(blade)
    kit.set_origin_to(blade, at)
    right = kit.duplicate(blade, name + ".R", mirror=True)
    right.location = Vector((-blade.location.x, blade.location.y, blade.location.z))
    return blade, right


def fin_dorsal(name, at, size=0.3, color="#4fa8d8", thickness=0.05, sweep=22.0):
    material = kit.mat("fin." + color.strip("#"), kit.hexcol(color), rough=0.4)
    blade = kit.cone(name, r1=size * 0.5, r2=0.0, h=size * 1.5,
                     loc=(at[0], at[1], at[2] + size * 0.6),
                     rot=(sweep, 0, 0), scale=(thickness / max(size, 1e-5) * 3.0, 1, 1),
                     material=material, verts=7)
    kit.flat(blade)
    return [blade]


def fin_tail(name, at, size=0.36, color="#4fa8d8", thickness=0.05, lobes=2):
    """A fish's caudal fin: two swept lobes."""
    material = kit.mat("fin." + color.strip("#"), kit.hexcol(color), rough=0.4)
    parts = []
    for i in range(lobes):
        up = 1 if i == 0 else -1
        lobe = kit.cone(
            name + ".%d" % i, r1=size * 0.4, r2=0.0, h=size,
            loc=(at[0], at[1] - size * 0.4, at[2] + up * size * 0.34),
            rot=(90 - up * 42, 0, 0),
            scale=(thickness / max(size, 1e-5) * 3.4, 1, 1),
            material=material, verts=7,
        )
        kit.flat(lobe)
        parts.append(lobe)
    merged = kit.join(parts, name)
    kit.weld(merged)
    kit.set_origin_to(merged, at)
    return merged


def tentacles(name, at, count=6, length=0.4, thickness=0.07, radius=0.22,
              color="#c86ba8", curl=0.3):
    """A ring of dangling arms -- jellyfish, squid, eldritch things."""
    material = kit.mat("tent." + color.strip("#"), kit.hexcol(color))
    parts = []
    for i in range(count):
        angle = (i / count) * 2 * math.pi
        x = at[0] + math.sin(angle) * radius
        y = at[1] + math.cos(angle) * radius
        arm_obj = kit.cone(
            name + ".%d" % i, r1=thickness * 0.5, r2=thickness * 0.12, h=length,
            loc=(x, y, at[2] - length * 0.5), rot=(0, 0, 0),
            material=material, verts=6,
        )
        kit.bend_z(arm_obj, length * curl * (1 if i % 2 else -1), axis="X")
        kit.flat(arm_obj)
        parts.append(arm_obj)
    merged = kit.join(parts, name)
    kit.weld(merged)
    kit.set_origin_to(merged, at)
    return merged


# --------------------------------------------------------------------------
# tails
# --------------------------------------------------------------------------


def tail(name, at, length=0.44, thickness=0.09, color="#c98a5a", style="taper",
         tip_color=None, segments=4, curl=0.3):
    """
    Tail styles: taper | puff | segmented | whip | flat | coil | spade
    `at` is the base joint; the tail grows backward along -Y and curls up.
    """
    material = kit.mat("tail." + color.strip("#"), kit.hexcol(color))
    tip_mat = kit.mat("tailtip." + (tip_color or color).strip("#"),
                      kit.hexcol(tip_color or color))
    parts = []

    if style == "puff":
        for i in range(segments):
            t = (i + 0.5) / segments
            r = thickness * (1.1 + 1.5 * math.sin(math.pi * t * 0.85))
            blob = kit.sphere(
                name + ".p%d" % i, r=r,
                loc=(at[0], at[1] - length * t * 0.9,
                     at[2] + length * curl * t * t),
                material=tip_mat if i == segments - 1 else material,
                segments=12, rings=8,
            )
            kit.smooth(blob)
            parts.append(blob)
    elif style == "segmented":
        for i in range(segments):
            t = (i + 0.5) / segments
            bead = kit.sphere(
                name + ".s%d" % i, r=thickness * (0.85 - 0.42 * t),
                loc=(at[0], at[1] - length * t, at[2] + length * curl * t * t),
                material=tip_mat if i == segments - 1 else material,
                segments=10, rings=7,
            )
            kit.smooth(bead)
            parts.append(bead)
    elif style == "whip":
        rod = kit.cone(name + ".rod", r1=thickness * 0.5, r2=thickness * 0.1, h=length,
                       loc=(at[0], at[1] - length * 0.5, at[2] + length * curl * 0.3),
                       rot=(90, 0, 0), material=material, verts=8)
        kit.flat(rod)
        parts.append(rod)
        tuft = kit.sphere(name + ".tuft", r=thickness * 1.15,
                          loc=(at[0], at[1] - length, at[2] + length * curl),
                          scale=(0.75, 1.4, 1.0), material=tip_mat,
                          segments=10, rings=7)
        kit.smooth(tuft)
        parts.append(tuft)
    elif style == "spade":
        rod = kit.cone(name + ".rod", r1=thickness * 0.5, r2=thickness * 0.16, h=length,
                       loc=(at[0], at[1] - length * 0.5, at[2] + length * curl * 0.3),
                       rot=(90, 0, 0), material=material, verts=8)
        kit.flat(rod)
        parts.append(rod)
        spade = kit.cone(name + ".spade", r1=thickness * 1.5, r2=0.0, h=thickness * 2.6,
                         loc=(at[0], at[1] - length - thickness * 0.6,
                              at[2] + length * curl),
                         rot=(-90, 0, 0),
                         scale=(1, 0.34, 1), material=tip_mat, verts=6)
        kit.flat(spade)
        parts.append(spade)
    elif style == "flat":
        paddle = kit.sphere(name + ".paddle", r=0.5,
                            loc=(at[0], at[1] - length * 0.5, at[2] + length * curl * 0.35),
                            scale=(thickness * 3.4, length, thickness * 1.1),
                            material=material, segments=12, rings=8)
        kit.smooth(paddle)
        parts.append(paddle)
    elif style == "coil":
        turns = max(2, segments)
        for i in range(turns * 3):
            t = i / (turns * 3.0)
            angle = t * turns * 2 * math.pi
            r = length * 0.28 * (1.0 - t * 0.55)
            bead = kit.sphere(
                name + ".c%d" % i, r=thickness * (0.6 - 0.28 * t),
                loc=(at[0] + math.sin(angle) * r * 0.4,
                     at[1] - length * 0.3 - math.cos(angle) * r,
                     at[2] + r * 0.5 + length * 0.2 * t),
                material=tip_mat if i >= turns * 3 - 2 else material,
                segments=8, rings=6,
            )
            kit.smooth(bead)
            parts.append(bead)
    else:  # taper
        rod = kit.cone(name + ".rod", r1=thickness * 0.7, r2=thickness * 0.08, h=length,
                       loc=(at[0], at[1] - length * 0.5, at[2] + length * curl * 0.4),
                       rot=(96, 0, 0), material=material, verts=9)
        kit.bend_z(rod, -length * curl, axis="Y")
        kit.flat(rod)
        parts.append(rod)

    merged = kit.join(parts, name)
    kit.weld(merged)
    kit.set_origin_to(merged, at)
    return merged


# --------------------------------------------------------------------------
# body shells and surface detail
# --------------------------------------------------------------------------


def shell(name, at, radius=0.44, color="#7a5a3a", rim_color="#a8834f",
          plates=6, dome=1.0):
    """Turtle/beetle carapace: a squashed dome with radial plate seams."""
    body_mat = kit.mat("shell." + color.strip("#"), kit.hexcol(color), rough=0.55)
    rim_mat = kit.mat("shellrim." + rim_color.strip("#"), kit.hexcol(rim_color))
    dome_obj = kit.sphere(name + ".dome", r=radius, loc=at,
                          scale=(1.0, 1.12, dome * 0.7), material=body_mat,
                          segments=18, rings=11)
    kit.smooth(dome_obj)
    parts = [dome_obj]
    for i in range(plates):
        angle = (i / plates) * 180.0
        seam = kit.box(
            name + ".seam%d" % i,
            dims=(radius * 0.055, radius * 1.95, radius * 0.055),
            loc=(at[0], at[1], at[2] + radius * dome * 0.44),
            rot=(0, 0, angle), material=rim_mat,
        )
        parts.append(seam)
    ring = kit.torus(name + ".rim", major=radius * 0.98, minor=radius * 0.1,
                     loc=(at[0], at[1], at[2] - radius * 0.03),
                     scale=(1, 1.12, 1), material=rim_mat,
                     major_seg=18, minor_seg=6)
    kit.smooth(ring)
    parts.append(ring)
    return parts


def spots(name, at, radius, count=7, size=0.1, color="#ffffff", seed=3,
          squash=0.35, band=(-40.0, 55.0)):
    """Deterministic surface freckles/patches spread over a sphere."""
    material = kit.mat("spot." + color.strip("#"), kit.hexcol(color))
    parts = []
    state = seed * 7919 + 13
    for i in range(count):
        state = (state * 1103515245 + 12345) & 0x7FFFFFFF
        yaw = (state / 0x7FFFFFFF) * 360.0
        state = (state * 1103515245 + 12345) & 0x7FFFFFFF
        pitch = band[0] + (state / 0x7FFFFFFF) * (band[1] - band[0])
        state = (state * 1103515245 + 12345) & 0x7FFFFFFF
        scale = 0.6 + (state / 0x7FFFFFFF) * 0.7
        s = size * scale
        depth = s * squash
        dot = kit.sphere(name + ".%d" % i, r=0.5,
                         loc=stick_out(at, radius, yaw, pitch, depth, out=depth * 0.3),
                         rot=aim_along(yaw, pitch),
                         scale=(s, s, depth), material=material,
                         segments=10, rings=6)
        kit.smooth(dot)
        parts.append(dot)
    return parts


def stripes(name, at, radius, count=4, width=0.08, color="#2b2b33",
            from_pitch=-30.0, to_pitch=45.0, squash=0.55):
    """Tiger/zebra bands wrapped around a body sphere."""
    material = kit.mat("stripe." + color.strip("#"), kit.hexcol(color))
    parts = []
    for i in range(count):
        t = (i + 0.5) / count
        pitch = from_pitch + (to_pitch - from_pitch) * t
        r = radius * math.cos(pitch * D2R)
        band = kit.torus(name + ".%d" % i, major=r, minor=width * 0.5,
                         loc=(at[0], at[1], at[2] + radius * math.sin(pitch * D2R)),
                         scale=(1, 1, squash), material=material,
                         major_seg=18, minor_seg=6)
        kit.smooth(band)
        parts.append(band)
    return parts


def belly(name, at, radius, color="#fff2dc", scale=(0.78, 0.5, 0.85), forward=0.36):
    """A lighter patch on the chest -- reads instantly as 'animal'."""
    material = kit.mat("belly." + color.strip("#"), kit.hexcol(color))
    patch = kit.sphere(name, r=radius, loc=(at[0], at[1] + radius * forward, at[2]),
                       scale=scale, material=material, segments=16, rings=10)
    kit.smooth(patch)
    return [patch]


def mane(name, at, radius, count=12, length=0.24, color="#c8531f", spread=1.0):
    """Lion/dragon ruff: spikes fanned around a neck point."""
    material = kit.mat("mane." + color.strip("#"), kit.hexcol(color))
    parts = []
    for i in range(count):
        angle = (i / count) * 360.0
        pitch = (math.sin(i * 2.1) * 26.0) * spread
        tuft = kit.cone(name + ".%d" % i, r1=length * 0.36, r2=0.0, h=length * 1.4,
                        loc=stick_out(at, radius, angle, pitch, length * 1.4,
                                      out=length * 0.9),
                        rot=aim_along(angle, pitch), material=material, verts=6)
        kit.flat(tuft)
        parts.append(tuft)
    return parts


def scales(name, at, radius, rows=3, per_row=7, size=0.09, color="#2f9c5c",
           from_pitch=-20.0, to_pitch=40.0):
    """Overlapping plates across the back."""
    material = kit.mat("scale." + color.strip("#"), kit.hexcol(color))
    parts = []
    for r in range(rows):
        tr = r / max(1, rows - 1)
        pitch = from_pitch + (to_pitch - from_pitch) * tr
        for c in range(per_row):
            yaw = -70 + (140.0 * c / max(1, per_row - 1)) + (18 if r % 2 else 0)
            depth = size * 0.32
            plate = kit.sphere(
                name + ".%d_%d" % (r, c), r=0.5,
                loc=stick_out(at, radius, yaw, pitch, depth, out=depth * 0.34),
                rot=aim_along(yaw, pitch),
                scale=(size, size * 0.9, depth), material=material,
                segments=8, rings=5,
            )
            kit.smooth(plate)
            parts.append(plate)
    return parts


def halo(name, at, radius=0.32, thickness=0.04, color="#ffe066"):
    material = kit.mat("halo." + color.strip("#"), kit.hexcol(color),
                       emission=kit.hexcol(color), emission_strength=3.0, rough=0.25)
    ring = kit.torus(name, major=radius, minor=thickness, loc=at,
                     material=material, major_seg=20, minor_seg=7)
    kit.smooth(ring)
    return [ring]


def gem(name, at, size=0.13, color="#5ce1ff", glow=2.8, stretch=1.5):
    material = kit.mat("gem." + color.strip("#"), kit.hexcol(color),
                       rough=0.12, emission=kit.hexcol(color), emission_strength=glow)
    crystal = kit.ico(name, r=size * 0.5, subdiv=1, loc=at,
                      scale=(1, 1, stretch), material=material)
    kit.flat(crystal)
    return [crystal]


def crystal_cluster(name, at, count=4, size=0.14, color="#8affd6", glow=2.4,
                    radius=0.14):
    material = kit.mat("gem." + color.strip("#"), kit.hexcol(color),
                       rough=0.12, emission=kit.hexcol(color), emission_strength=glow)
    parts = []
    for i in range(count):
        angle = (i / count) * 2 * math.pi
        s = size * (0.6 + 0.5 * ((i * 7) % 5) / 5.0)
        shard = kit.cone(
            name + ".%d" % i, r1=s * 0.32, r2=0.0, h=s * 2.0,
            loc=(at[0] + math.sin(angle) * radius, at[1] + math.cos(angle) * radius,
                 at[2] + s * 0.8),
            rot=(math.sin(angle) * 22, math.cos(angle) * 22, 0),
            material=material, verts=5,
        )
        kit.flat(shard)
        parts.append(shard)
    return parts


def orbit_ring(name, at, radius=0.55, thickness=0.035, tilt=24.0, color="#c9a6ff"):
    material = kit.mat("ring." + color.strip("#"), kit.hexcol(color),
                       rough=0.3, emission=kit.hexcol(color), emission_strength=1.4)
    ring = kit.torus(name, major=radius, minor=thickness, loc=at,
                     rot=(tilt, 0, 12), material=material,
                     major_seg=24, minor_seg=6)
    kit.smooth(ring)
    return [ring]


def flame_tuft(name, at, count=5, size=0.18, color="#ff8a1f",
               inner_color="#ffe14d", spread=0.14):
    """A lick of stylised fire -- manes, tails, volcano pets."""
    outer = kit.mat("flame." + color.strip("#"), kit.hexcol(color),
                    emission=kit.hexcol(color), emission_strength=2.2, rough=0.3)
    inner = kit.mat("flamein." + inner_color.strip("#"), kit.hexcol(inner_color),
                    emission=kit.hexcol(inner_color), emission_strength=3.4, rough=0.2)
    parts = []
    for i in range(count):
        angle = (i / count) * 2 * math.pi
        s = size * (0.55 + 0.6 * abs(math.sin(i * 1.7)))
        tongue_obj = kit.cone(
            name + ".%d" % i, r1=s * 0.34, r2=0.0, h=s * 1.9,
            loc=(at[0] + math.sin(angle) * spread, at[1] + math.cos(angle) * spread,
                 at[2] + s * 0.8),
            rot=(math.sin(angle) * 26, math.cos(angle) * 26, 0),
            material=inner if i % 2 else outer, verts=5,
        )
        kit.flat(tongue_obj)
        parts.append(tongue_obj)
    return parts


# --------------------------------------------------------------------------
# assembly
# --------------------------------------------------------------------------


def assemble(root, groups):
    """
    `groups` maps a runtime part name to (parts, pivot). Each becomes one
    welded mesh parented to `root` with its origin at pivot, which is what lets
    the runtime rotate "head" or "wing.L" without touching anything else.
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
