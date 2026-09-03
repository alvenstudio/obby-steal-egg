"""
Titan Temple -- the eight endgame pets.

Everything here is quarried out of the same four materials: weathered temple
stone, dark bronze plate, gold inlay and ember light. The biome's read is
WEIGHT -- these creatures are armoured, slab-shouldered and slow-looking, and
every one of them carries some piece of the temple on its back.

Conventions are the ones pets_forest.py establishes:

  * Build facing +Y, feet near z = 0, `bk.finish()` normalises the height.
  * Only the runtime's part names go into `assemble`: body, head, ear.L/.R,
    wing.L/.R, arm.L/.R, leg.FL/.FR/.BL/.BR, tail, fin.L/.R, fin.tail.
  * Pivot at the joint, never at the part's centre.

One local deviation, and it is deliberate. `kit.set_origin_to` writes a
world-space offset into local vertex coordinates, so any mesh that still
carries a non-unit object scale gets displaced when its origin is moved. Every
join in this module therefore goes through `_join`, which bakes transforms
first -- which in turn means the coordinates written below are the coordinates
that survive to the render, and the limbs are built here rather than borrowed
from blockkit's pre-joined helpers.
"""

import math

import bpy
from mathutils import Vector

import blockkit as bk
import kit


# ---------------------------------------------------------------------------
# Palette -- shared so eight very different silhouettes read as one temple.
# ---------------------------------------------------------------------------

STONE = "#8d8778"           # weathered granite
STONE_DK = "#5d574c"        # shadowed stone / mortar
STONE_PALE = "#b5ae9c"      # sun-bleached slab faces
BRONZE = "#8e5c2b"          # dark bronze plate
BRONZE_DK = "#5a3a19"       # oxidised bronze, joints and straps
GOLD = "#e8b93f"            # inlay
GOLD_DK = "#a8802a"
EMBER = "#ff7a1e"           # rune light
EMBER_PALE = "#ffc061"
BLOOD = "#9c211f"           # banners, gums, cloth
IRON = "#3b383e"            # blades, claws, hide
VOID = "#17141c"            # nightflame's scale
VIOLET = "#a259ff"          # nightflame's fire


# ---------------------------------------------------------------------------
# Local construction helpers
# ---------------------------------------------------------------------------


def _bake(parts):
    """Flatten rotation+scale into the mesh so origins can be moved exactly."""
    for obj in parts:
        if obj is not None and obj.type == "MESH":
            kit.apply_transforms(obj, rotation=True, scale=True)
    return parts


def _join(name, parts, pivot):
    """Weld a cluster into one animatable mesh whose origin sits at `pivot`."""
    parts = [p for p in parts if p is not None]
    _bake(parts)
    merged = kit.join(parts, name)
    kit.weld(merged)
    kit.set_origin_to(merged, pivot)
    return merged


def _mirror(obj, name):
    """The .R twin of a finished .L cluster."""
    right = kit.duplicate(obj, name, mirror=True)
    right.location = Vector((-obj.location.x, obj.location.y, obj.location.z))
    return right


def _discard(obj):
    """
    Delete a scratch mesh outright.

    Anything left in the scene but not handed to `assemble` is still a mesh:
    it is counted in the triangle budget, it drags the normalisation bounds
    around, and it renders. A mirror source that is not itself used has to go.
    """
    bpy.data.objects.remove(obj, do_unlink=True)


def _assemble(root, groups):
    for parts, _pivot in groups.values():
        _bake([p for p in parts if p is not None])
    return bk.assemble(root, groups)


def _strut(name, a, b, thick, color, taper=0.0, thick_y=None, glow=0.0):
    """A box spanning two points -- the limb segment this module is built from."""
    a, b = Vector(a), Vector(b)
    span = b - a
    length = max(span.length, 1e-4)
    rot = [math.degrees(v) for v in span.to_track_quat("Z", "Y").to_euler()]
    dims = (thick, thick_y if thick_y else thick, length)
    mid = tuple((a + b) * 0.5)
    if glow > 0:
        return bk.glow_block(name, dims, mid, rot, color=color, strength=glow)
    if taper > 0:
        return bk.wedge(name, dims, mid, rot, color=color, taper=taper)
    return bk.block(name, dims, mid, rot, color=color)


def _inlay(name, at, dims, color=GOLD, count=3, axis="x", width=0.02):
    """Thin gold lines cut across a stone face -- the biome's signature trim."""
    out = []
    for i in range(count):
        t = (i + 0.5) / count - 0.5
        if axis == "x":
            out.append(bk.slab("%s.%d" % (name, i),
                               (width, dims[1] * 0.94, dims[2] * 1.02),
                               (at[0] + t * dims[0] * 0.9, at[1], at[2]),
                               color=color))
        else:
            out.append(bk.slab("%s.%d" % (name, i),
                               (dims[0] * 1.02, width, dims[2] * 0.94),
                               (at[0], at[1] + t * dims[1] * 0.9, at[2]),
                               color=color))
    return out


# ===========================================================================
# Spideron -- Legendary, $95K/s.
# A temple-guardian spider: a bronze-plated abdomen slung low, a raised
# thorax, and eight long legs whose knees are higher than its back. The
# silhouette is all knees; the runes live in the joints.
# ===========================================================================

def build_spideron():
    kit.reset_scene()
    root = kit.empty("root")

    plate = BRONZE
    plate_dk = BRONZE_DK
    shell_c = "#4c463d"   # the dark stone the plates are bolted onto
    limb = "#585047"      # legs stay grey so the bronze body reads against them
    limb_dk = "#39342d"
    rune = EMBER

    # -- abdomen: low, wide and ribbed, hung behind the leg cluster ---------
    abd_dims = (0.52, 0.52, 0.42)
    abd_at = (0, -0.44, 0.60)
    body = [bk.block("body.abdomen", abd_dims, abd_at, color=shell_c)]
    for i, t in enumerate((-0.16, 0.0, 0.16)):
        body.append(bk.slab("body.rib%d" % i, (0.54, 0.08, 0.44),
                            (0, abd_at[1] + t, abd_at[2]), color=plate))
    body.append(bk.slab("body.crown", (0.34, 0.40, 0.05),
                        (0, abd_at[1], abd_at[2] + 0.22), color=STONE))
    body += _inlay("body.crown.inlay", (0, abd_at[1], abd_at[2] + 0.245),
                   (0.30, 0.36, 0.02), color=GOLD, count=2, axis="x",
                   width=0.026)
    body.append(bk.glow_block("body.rune.spine", (0.07, 0.36, 0.03),
                              (0, abd_at[1], abd_at[2] + 0.215),
                              color=rune, strength=2.4))
    for side, sign in (("L", 1), ("R", -1)):
        body.append(bk.glow_block("body.rune.flank.%s" % side,
                                  (0.03, 0.28, 0.12),
                                  (sign * 0.265, abd_at[1], abd_at[2]),
                                  color=rune, strength=2.0))
    body.append(bk.wedge("body.spinneret", (0.14, 0.14, 0.18),
                         (0, abd_at[1] - 0.27, abd_at[2] - 0.04),
                         rot=(96, 0, 0), color=plate_dk, taper=0.7))

    # -- thorax: the leg deck, a bronze carapace with a gold seam -----------
    thx_dims = (0.38, 0.34, 0.30)
    thx_at = (0, 0.02, 0.66)
    body.append(bk.block("body.thorax", thx_dims, thx_at, color=plate))
    body.append(bk.slab("body.carapace", (0.34, 0.30, 0.06),
                        (0, 0.0, thx_at[2] + 0.16), color=plate_dk))
    body += _inlay("body.seam", (0, 0.0, thx_at[2] + 0.185), (0.30, 0.28, 0.02),
                   color=GOLD, count=2, axis="x", width=0.024)

    # -- head: pushed well forward of the thorax, eight eyes ---------------
    head_dims = (0.28, 0.24, 0.22)
    head_at = (0, 0.34, 0.68)
    head = [bk.block("head.skull", head_dims, head_at, color=plate_dk)]
    head.append(bk.slab("head.brow", (0.28, 0.10, 0.05),
                        (0, head_at[1] - 0.02, head_at[2] + 0.11), color=plate))
    head += bk.eyes("head.eye.main", head_at, head_dims, spacing=0.5,
                    height=0.02, size=0.062, style="glow", iris=rune)
    head += bk.eyes("head.eye.side", head_at, head_dims, spacing=0.86,
                    height=0.045, size=0.036, style="glow", iris=EMBER_PALE)
    head += bk.eyes("head.eye.low", head_at, head_dims, spacing=0.62,
                    height=-0.055, size=0.03, style="glow", iris=EMBER_PALE)
    # Fangs: two down-swept wedges under the face.
    for side, sign in (("L", 1), ("R", -1)):
        head.append(bk.wedge("head.fang.%s" % side, (0.055, 0.055, 0.16),
                             (sign * 0.07, head_at[1] + 0.10, head_at[2] - 0.13),
                             rot=(-160, 0, 0), color=STONE_PALE, taper=0.85))
    head.append(bk.slab("head.collar", (0.24, 0.05, 0.16),
                        (0, head_at[1] - 0.12, head_at[2]), color=plate))

    # -- eight legs: femur up and out, tibia stabbing down to the floor ----
    # Front four go in leg.FL/.FR, rear four in leg.BL/.BR, so the animator
    # drives them as two alternating sets like any quadruped.
    # Knee heights step down front to back, so the back is a descending line
    # of joints instead of four legs of a table.
    # The femur reaches OUT far more than up, so the knees sit wide of the
    # body instead of stacking over it -- the difference between a spider and
    # a table. Knee heights step down front to back.
    spans = ((0.20, 0.36, 0.34, 0.90), (0.05, 0.40, 0.12, 0.85),
             (-0.13, 0.40, -0.14, 0.79), (-0.30, 0.34, -0.36, 0.73))
    front, back = [], []
    for i, (y, out, fwd, kz) in enumerate(spans):
        hip = (0.16, y, 0.58)
        knee = (0.16 + out, y + fwd * 0.35, kz)
        foot = (0.16 + out + 0.07, y + fwd, 0.015)
        bucket = front if i < 2 else back
        bucket.append(_strut("leg.L%d.femur" % i, hip, knee, 0.085, limb))
        bucket.append(_strut("leg.L%d.tibia" % i, knee, foot, 0.065, limb_dk,
                             taper=0.5))
        bucket.append(bk.glow_block("leg.L%d.rune" % i, (0.06, 0.06, 0.06),
                                    knee, color=rune, strength=2.8))

    leg_fl = _join("leg.FL", front, (0.16, 0.12, 0.58))
    leg_bl = _join("leg.BL", back, (0.16, -0.22, 0.58))
    leg_fr = _mirror(leg_fl, "leg.FR")
    leg_br = _mirror(leg_bl, "leg.BR")

    _assemble(root, {
        "body": (body, (0, -0.14, 0.44)),
        "head": (head, (0, 0.20, 0.64)),
        "leg.FL": ([leg_fl], tuple(leg_fl.location)),
        "leg.FR": ([leg_fr], tuple(leg_fr.location)),
        "leg.BL": ([leg_bl], tuple(leg_bl.location)),
        "leg.BR": ([leg_br], tuple(leg_br.location)),
    })
    return bk.finish(root)


# ===========================================================================
# Crustacia -- Legendary, $130K/s.
# A crab the size of a gatehouse. The shell is a piece of temple floor --
# actual tiles, actual grout -- and the claws are two stone slabs that happen
# to open. Read from a distance: very wide, very low, two blocks up front.
# ===========================================================================

def build_crustacia():
    kit.reset_scene()
    root = kit.empty("root")

    shell_c = STONE
    tile = STONE_PALE
    grout = STONE_DK
    limb = BRONZE

    # -- shell: a slab of temple floor with the tiles still on it ----------
    shell_dims = (0.62, 0.46, 0.24)
    shell_at = (0, -0.06, 0.54)
    body = [bk.block("body.shell", shell_dims, shell_at, color=shell_c)]
    # A second, smaller course on top: the shell is a stepped ziggurat.
    body.append(bk.block("body.shell.upper", (0.46, 0.34, 0.11),
                         (0, -0.06, 0.71), color=shell_c))
    top = bk.face_of((0, -0.06, 0.71), (0.46, 0.34, 0.11), "top")
    for cx in range(3):
        for cy in range(2):
            u = (cx - 1) * 0.15
            v = (cy - 0.5) * 0.16
            body.append(bk.face_plate(
                "body.tile%d%d" % (cx, cy), top, (0.13, 0.14), face="top",
                color=(tile if (cx + cy) % 2 == 0 else shell_c),
                depth=0.035, offset=(u, v)))
    # Gold grout: two inlay lines running the length of the shell.
    for i, u in enumerate((-0.075, 0.075)):
        body.append(bk.slab("body.grout%d" % i, (0.022, 0.30, 0.02),
                            (u, shell_at[1], top[2] + 0.045), color=GOLD))
    # A gold rim around the lower course, so the shell reads as masonry.
    body.append(bk.slab("body.rim", (0.64, 0.48, 0.03),
                        (0, shell_at[1], shell_at[2] + 0.115), color=GOLD_DK))
    # Rear apron and a rim of shell teeth so the outline is not a plain slab.
    body.append(bk.block("body.apron", (0.50, 0.16, 0.18),
                         (0, shell_at[1] - 0.29, shell_at[2] - 0.04),
                         color=grout))
    for i, u in enumerate((-0.24, -0.08, 0.08, 0.24)):
        body.append(bk.wedge("body.tooth%d" % i, (0.08, 0.08, 0.10),
                             (u, shell_at[1] + 0.24, shell_at[2] - 0.03),
                             rot=(-90, 0, 0), color=grout, taper=0.6))
    body.append(bk.glow_block("body.vent", (0.30, 0.04, 0.035),
                              (0, shell_at[1] - 0.21, shell_at[2] + 0.12),
                              color=EMBER, strength=2.2))

    # -- head: a low brow between the shell edge and the claws -------------
    head_dims = (0.30, 0.16, 0.17)
    head_at = (0, 0.30, 0.50)
    head = [bk.block("head.brow", head_dims, head_at, color=grout)]
    head += bk.mouth("head.maw", head_at, head_dims, width=0.16, height=0.035,
                     drop=-0.045, color="#221c16", style="grin")
    # Eye stalks: two bronze posts with ember lamps, the only tall thing on it.
    for side, sign in (("L", 1), ("R", -1)):
        head.append(bk.block("head.stalk.%s" % side, (0.05, 0.05, 0.17),
                             (sign * 0.11, head_at[1] - 0.01, head_at[2] + 0.15),
                             rot=(0, -sign * 9, 0), color=limb))
        head.append(bk.glow_block("head.lamp.%s" % side, (0.075, 0.075, 0.075),
                                  (sign * 0.135, head_at[1] - 0.01, head_at[2] + 0.25),
                                  color=EMBER, strength=3.0))
    # Mandible plates.
    for side, sign in (("L", 1), ("R", -1)):
        head.append(bk.slab("head.mandible.%s" % side, (0.07, 0.10, 0.09),
                            (sign * 0.07, head_at[1] + 0.04, head_at[2] - 0.09),
                            rot=(0, 0, -sign * 14), color=limb))

    # -- claws: slab pincers on a short bronze arm -------------------------
    # Held high and forward so the claws, not the shell, own the outline.
    def claw(tag):
        shoulder = (0.26, 0.10, 0.52)
        elbow = (0.36, 0.30, 0.56)
        parts = [
            _strut("%s.upper" % tag, shoulder, elbow, 0.11, limb),
            bk.block("%s.knuckle" % tag, (0.13, 0.13, 0.13), elbow,
                     color=BRONZE_DK),
            # The claw body: a squared-off block of the same stone as the shell.
            bk.block("%s.palm" % tag, (0.22, 0.30, 0.26),
                     (0.40, 0.52, 0.58), rot=(0, 0, -12), color=shell_c),
            bk.slab("%s.inlay" % tag, (0.23, 0.06, 0.22),
                    (0.40, 0.52, 0.58), rot=(0, 0, -12), color=GOLD_DK),
            # Two slab pincers with a wide open gap between them -- the gap is
            # what makes a block read as a claw rather than a mitten.
            _strut("%s.jaw.low" % tag, (0.40, 0.62, 0.46), (0.46, 0.92, 0.40),
                   0.13, grout, taper=0.45, thick_y=0.12),
            _strut("%s.jaw.up" % tag, (0.40, 0.62, 0.70), (0.46, 0.90, 0.64),
                   0.13, tile, taper=0.45, thick_y=0.11),
            bk.glow_block("%s.socket" % tag, (0.11, 0.10, 0.07),
                          (0.40, 0.66, 0.57), color=EMBER, strength=1.8),
        ]
        return parts, shoulder

    left_parts, pivot = claw("arm.L")
    arm_l = _join("arm.L", left_parts, pivot)
    arm_r = _mirror(arm_l, "arm.R")

    # -- four walking legs, bent and short --------------------------------
    legs = {}
    for tag, y, fwd in (("F", 0.10, 0.14), ("B", -0.16, -0.16)):
        parts = [
            _strut("leg.%sL.femur" % tag, (0.28, y, 0.50),
                   (0.45, y + fwd * 0.4, 0.58), 0.14, limb, thick_y=0.16),
            _strut("leg.%sL.tibia" % tag, (0.45, y + fwd * 0.4, 0.58),
                   (0.49, y + fwd, 0.06), 0.115, BRONZE_DK, taper=0.45),
            bk.block("leg.%sL.foot" % tag, (0.12, 0.18, 0.06),
                     (0.49, y + fwd + 0.02, 0.03), color=grout),
        ]
        left = _join("leg.%sL" % tag, parts, (0.28, y, 0.50))
        legs["leg.%sL" % tag] = left
        legs["leg.%sR" % tag] = _mirror(left, "leg.%sR" % tag)

    groups = {
        "body": (body, (0, -0.10, 0.42)),
        "head": (head, (0, 0.22, 0.46)),
        "arm.L": ([arm_l], tuple(arm_l.location)),
        "arm.R": ([arm_r], tuple(arm_r.location)),
    }
    for key, obj in legs.items():
        groups[key] = ([obj], tuple(obj.location))
    _assemble(root, groups)
    return bk.finish(root)


# ===========================================================================
# Bladehide -- Mythic, $750K/s.
# A quadruped whose hide is armoury surplus: rows of overlapping blade-scales
# down the spine and flanks, pauldron blades at the shoulders, and a tail that
# is literally four swords fanned out behind it.
# ===========================================================================

def build_bladehide():
    kit.reset_scene()
    root = kit.empty("root")

    hide = IRON
    steel = "#b9bcc4"
    steel_dk = "#7c818c"
    trim = BRONZE

    # -- torso: shoulders high, hips low; the back is a blade ramp ---------
    body_dims = (0.38, 0.62, 0.34)
    body_at = (0, -0.04, 0.52)
    body = [bk.block("body.core", body_dims, body_at, color=hide)]
    body.append(bk.block("body.shoulders", (0.44, 0.24, 0.30),
                         (0, 0.20, 0.60), color=hide))
    body += bk.belly("body.chest", body_at, body_dims, color="#4a464c", inset=0.66)
    body.append(bk.slab("body.girth", (0.42, 0.07, 0.36),
                        (0, -0.02, body_at[2]), color=trim))

    # Blade-scales: three ranks along the spine, each rank a shallower and
    # shorter blade than the one in front, so the back reads as a saw.
    for rank, (y, length, lean) in enumerate((
            (0.22, 0.20, -38), (0.06, 0.22, -34), (-0.10, 0.19, -30),
            (-0.26, 0.15, -26))):
        for i, u in enumerate((-0.10, 0.0, 0.10)):
            scale = 1.0 - abs(i - 1) * 0.28
            body.append(bk.wedge(
                "body.blade%d%d" % (rank, i),
                (0.055, 0.03, length * scale),
                (u, y, 0.70 + 0.02 * scale),
                rot=(lean, 0, 0), color=steel if i == 1 else steel_dk, taper=0.7))
    # Flank blades, angled down and back.
    for side, sign in (("L", 1), ("R", -1)):
        for i, y in enumerate((0.12, -0.04, -0.20)):
            body.append(bk.wedge(
                "body.flank.%s%d" % (side, i), (0.03, 0.05, 0.17),
                (sign * 0.20, y, 0.48), rot=(0, sign * 108, 0),
                color=steel_dk, taper=0.7))
        # Pauldron: one big blade standing off the shoulder.
        body.append(bk.wedge(
            "body.pauldron.%s" % side, (0.05, 0.10, 0.30),
            (sign * 0.22, 0.20, 0.76), rot=(-24, sign * 34, 0),
            color=steel, taper=0.6))
        body.append(bk.glow_block("body.pauldron.rune.%s" % side,
                                  (0.05, 0.06, 0.03),
                                  (sign * 0.20, 0.21, 0.66),
                                  color=BLOOD, strength=2.4))

    # -- head: a wedge with a blade running down the nose ------------------
    head_dims = (0.28, 0.30, 0.24)
    head_at = (0, 0.44, 0.66)
    head = [bk.block("head.skull", head_dims, head_at, color=hide)]
    head.append(bk.block("head.jaw", (0.24, 0.24, 0.10),
                         (0, head_at[1] + 0.06, head_at[2] - 0.15), color="#2c2a2f"))
    head += bk.mouth("head.maw", head_at, head_dims, width=0.19, height=0.035,
                     drop=-0.11, color=BLOOD, style="open", teeth=5,
                     teeth_color=steel)
    head += bk.eyes("head.eye", head_at, head_dims, spacing=0.56, height=0.05,
                    size=0.055, style="glow", iris=BLOOD)
    head.append(bk.slab("head.brow", (0.30, 0.16, 0.05),
                        (0, head_at[1] - 0.01, head_at[2] + 0.12), color=trim))
    # Nose blade + two cheek blades.
    head.append(bk.wedge("head.noseblade", (0.045, 0.16, 0.22),
                         (0, head_at[1] + 0.06, head_at[2] + 0.22),
                         rot=(-14, 0, 0), color=steel, taper=0.72))
    for side, sign in (("L", 1), ("R", -1)):
        head.append(bk.wedge("head.cheek.%s" % side, (0.035, 0.05, 0.17),
                             (sign * 0.14, head_at[1] - 0.04, head_at[2] + 0.02),
                             rot=(0, sign * 118, 0), color=steel_dk, taper=0.7))

    # -- legs: short, thick, greaved --------------------------------------
    legs = {}
    for tag, y, hipz in (("F", 0.20, 0.44), ("B", -0.22, 0.42)):
        parts = [
            _strut("leg.%sL.thigh" % tag, (0.15, y, hipz), (0.17, y - 0.02, 0.22),
                   0.12, hide),
            _strut("leg.%sL.shin" % tag, (0.17, y - 0.02, 0.22), (0.17, y, 0.05),
                   0.10, "#2c2a2f"),
            bk.block("leg.%sL.hoof" % tag, (0.14, 0.17, 0.06),
                     (0.17, y + 0.02, 0.03), color=trim),
            bk.wedge("leg.%sL.greave" % tag, (0.04, 0.05, 0.14),
                     (0.24, y - 0.01, 0.26), rot=(0, 122, 0), color=steel_dk,
                     taper=0.7),
        ]
        left = _join("leg.%sL" % tag, parts, (0.15, y, hipz))
        legs["leg.%sL" % tag] = left
        legs["leg.%sR" % tag] = _mirror(left, "leg.%sR" % tag)

    # -- tail of swords ----------------------------------------------------
    tail_parts = [
        _strut("tail.stump", (0, -0.34, 0.54), (0, -0.48, 0.60), 0.13, hide),
        bk.block("tail.boss", (0.14, 0.10, 0.14), (0, -0.50, 0.62), color=trim),
    ]
    for i, (spread, lift, length) in enumerate((
            (-0.17, 0.05, 0.36), (-0.06, 0.15, 0.44),
            (0.06, 0.15, 0.44), (0.17, 0.05, 0.36))):
        tip = (spread * 1.5, -0.50 - length * 0.60, 0.62 + lift * 3.2)
        base = (spread * 0.4, -0.50, 0.62)
        tail_parts.append(_strut("tail.sword%d" % i, base, tip, 0.035, steel,
                                 taper=0.6, thick_y=0.09))
        # Cross-guard, so each blade reads as a sword rather than a spike.
        mid = tuple(Vector(base) * 0.72 + Vector(tip) * 0.28)
        tail_parts.append(bk.slab("tail.guard%d" % i, (0.12, 0.045, 0.03),
                                  mid, color=GOLD_DK))
    tail = _join("tail", tail_parts, (0, -0.34, 0.54))

    groups = {
        "body": (body, (0, -0.1, 0.34)),
        "head": (head, (0, 0.30, 0.58)),
        "tail": ([tail], tuple(tail.location)),
    }
    for key, obj in legs.items():
        groups[key] = ([obj], tuple(obj.location))
    _assemble(root, groups)
    return bk.finish(root)


# ===========================================================================
# Mantaris -- Cosmic, $11M/s.
# A slab of carved temple ceiling that decided to fly. Enormous flat wing
# span, cephalic horns at the front, glyph channels burning along the wings,
# and a whip tail. Nothing touches the ground: it hovers.
# ===========================================================================

def build_mantaris():
    kit.reset_scene()
    root = kit.empty("root")

    slabc = STONE
    slab_dk = STONE_DK
    glyph = EMBER

    hover = 0.56  # centreline height; the wings arch above, the tail hangs

    # -- central body: a thick keel with a tiled back ----------------------
    body_dims = (0.32, 0.54, 0.19)
    body_at = (0, -0.02, hover)
    body = [bk.block("body.keel", body_dims, body_at, color=slabc)]
    body.append(bk.slab("body.spine", (0.13, 0.52, 0.06),
                        (0, -0.02, hover + 0.10), color=slab_dk))
    body += _inlay("body.rib", (0, -0.02, hover + 0.09), (0.26, 0.48, 0.05),
                   color=GOLD_DK, count=3, axis="y", width=0.025)
    body.append(bk.block("body.gill", (0.34, 0.10, 0.10),
                         (0, 0.16, hover - 0.04), color=slab_dk))
    for i, u in enumerate((-0.13, -0.05, 0.05, 0.13)):
        body.append(bk.glow_block("body.gillrune%d" % i, (0.025, 0.05, 0.07),
                                  (u, 0.21, hover - 0.04), color=glyph,
                                  strength=2.2))
    # Underside keel-stone so the belly is not a flat card.
    body.append(bk.block("body.ballast", (0.20, 0.34, 0.09),
                         (0, -0.04, hover - 0.11), color=slab_dk))

    # -- head: mouth slot between two forward-reaching cephalic horns ------
    head_dims = (0.26, 0.16, 0.13)
    head_at = (0, 0.34, hover - 0.01)
    head = [bk.block("head.plate", head_dims, head_at, color=slabc)]
    head.append(bk.glow_block("head.maw", (0.20, 0.035, 0.045),
                              (0, head_at[1] + 0.08, head_at[2] - 0.03),
                              color="#ffd08a", strength=1.8))
    head.append(bk.slab("head.crown", (0.24, 0.13, 0.04),
                        (0, head_at[1] - 0.01, head_at[2] + 0.08), color=slab_dk))
    head.append(bk.glow_block("head.crown.rune", (0.05, 0.09, 0.02),
                              (0, head_at[1] - 0.01, head_at[2] + 0.105),
                              color=glyph, strength=2.6))
    for side, sign in (("L", 1), ("R", -1)):
        head.append(bk.wedge("head.horn.%s" % side, (0.06, 0.06, 0.24),
                             (sign * 0.11, head_at[1] + 0.11, head_at[2] - 0.01),
                             rot=(-96, 0, -sign * 8), color=slab_dk, taper=0.6))
        # Eyes on the outboard corners, where a manta's actually are.
        head.append(bk.glow_block("head.eye.%s" % side, (0.05, 0.055, 0.05),
                                  (sign * 0.14, head_at[1] - 0.02, head_at[2]),
                                  color=glyph, strength=3.2))

    # -- wings: three stepped slabs per side, sweeping back and dropping ---
    # Each step is shorter, thinner and HIGHER than the last, so the wing
    # arches into a hovering vault instead of lying flat like a table top.
    def wing(tag):
        parts = []
        steps = ((0.14, 0.48, 0.11, -0.01, 0.00, -8),
                 (0.32, 0.42, 0.09, -0.05, 0.11, -18),
                 (0.48, 0.30, 0.07, -0.12, 0.26, -30))
        for i, (x, depth, thick, y, z, lean) in enumerate(steps):
            parts.append(bk.block(
                "%s.slab%d" % (tag, i), (0.22, depth, thick),
                (x, y, hover + z), rot=(0, lean, 0),
                color=slabc if i == 0 else STONE_PALE))
            # A glyph channel burning along the leading edge of each step.
            parts.append(bk.glow_block(
                "%s.glyph%d" % (tag, i), (0.15, 0.05, thick * 0.45),
                (x, y + depth * 0.30, hover + z + thick * 0.45),
                rot=(0, lean, 0), color=glyph, strength=2.6))
            parts.append(bk.slab(
                "%s.trim%d" % (tag, i), (0.19, 0.035, thick * 0.9),
                (x, y - depth * 0.34, hover + z), rot=(0, lean, 0),
                color=GOLD_DK))
        # Wing tip: a long tapered stone fin, swept up and back.
        parts.append(_strut("%s.tip" % tag, (0.58, -0.16, hover + 0.32),
                            (0.74, -0.34, hover + 0.46), 0.15, slab_dk,
                            taper=0.75, thick_y=0.05))
        return parts

    wing_l = _join("wing.L", wing("wing.L"), (0.13, 0.0, hover))
    wing_r = _mirror(wing_l, "wing.R")

    # -- tail: a whip of shrinking stone beads, hanging down and back ------
    tail_parts = []
    for i in range(5):
        t = i / 4.0
        size = 0.13 * (1.0 - 0.62 * t)
        tail_parts.append(bk.block(
            "tail.bead%d" % i, (size, 0.14, size),
            (0, -0.32 - i * 0.13, hover - 0.07 - t * 0.36),
            color=slabc if i % 2 == 0 else slab_dk))
    tail_parts.append(bk.glow_block("tail.barb", (0.035, 0.19, 0.035),
                                    (0, -0.92, hover - 0.52),
                                    rot=(30, 0, 0), color=glyph, strength=3.2))
    tail = _join("tail", tail_parts, (0, -0.28, hover - 0.04))

    _assemble(root, {
        "body": (body, (0, -0.02, hover)),
        "head": (head, (0, 0.24, hover)),
        "wing.L": ([wing_l], tuple(wing_l.location)),
        "wing.R": ([wing_r], tuple(wing_r.location)),
        "tail": ([tail], tuple(tail.location)),
    })
    return bk.finish(root)


# ===========================================================================
# Rhinotaur -- Cosmic, $17.5M/s.
# Minotaur build, rhino head. Everything above the waist is twice as wide as
# everything below it, so the outline is a wedge standing on hooves. Bronze
# bracers, a gold-inlaid chest plate, and one enormous nose horn.
# ===========================================================================

def build_rhinotaur():
    kit.reset_scene()
    root = kit.empty("root")

    hide = "#77716a"
    hide_dk = "#4d4842"
    horn_c = STONE_PALE

    # -- torso: a slab-sided barrel with a bronze chest plate --------------
    body_dims = (0.54, 0.38, 0.46)
    body_at = (0, -0.01, 0.78)
    body = [bk.block("body.torso", body_dims, body_at, color=hide)]
    body.append(bk.block("body.gut", (0.44, 0.34, 0.22),
                         (0, 0.0, 0.56), color=hide_dk))
    chest = bk.face_of(body_at, body_dims, "front")
    body.append(bk.face_plate("body.plate", chest, (0.42, 0.34), face="front",
                              color=BRONZE, depth=0.05, offset=(0, 0.03)))
    body.append(bk.face_plate("body.plate.inlay", chest, (0.10, 0.26),
                              face="front", color=GOLD, depth=0.04,
                              offset=(0, 0.03), proud=bk.PROUD * 9))
    body.append(bk.glow_block("body.plate.core", (0.09, 0.05, 0.09),
                              (0, chest[1] + 0.09, body_at[2] + 0.06),
                              color=EMBER, strength=2.6))
    # Shoulder yokes: bronze pauldrons that make the wedge silhouette.
    for side, sign in (("L", 1), ("R", -1)):
        body.append(bk.block("body.pauldron.%s" % side, (0.20, 0.30, 0.14),
                             (sign * 0.32, 0.0, 0.94), rot=(0, -sign * 16, 0),
                             color=BRONZE))
        body.append(bk.slab("body.pauldron.trim.%s" % side, (0.21, 0.31, 0.035),
                            (sign * 0.33, 0.0, 1.00), rot=(0, -sign * 16, 0),
                            color=GOLD_DK))
    # Blood-red waist cloth hanging at the back.
    body.append(bk.slab("body.cloth", (0.40, 0.06, 0.34),
                        (0, -0.20, 0.50), rot=(6, 0, 0), color=BLOOD))
    body.append(bk.slab("body.belt", (0.50, 0.36, 0.07),
                        (0, 0.0, 0.58), color=BRONZE_DK))

    # -- head: low, forward, and mostly horn -------------------------------
    head_dims = (0.32, 0.30, 0.28)
    head_at = (0, 0.38, 1.18)
    head = [bk.block("head.skull", head_dims, head_at, color=hide)]
    head.append(bk.block("head.snout", (0.24, 0.22, 0.18),
                         (0, head_at[1] + 0.22, head_at[2] - 0.08), color=hide_dk))
    snout_at = (0, head_at[1] + 0.22, head_at[2] - 0.08)
    head += bk.nostrils("head.nostril", snout_at, (0.24, 0.22, 0.18),
                        spacing=0.42, height=-0.02, size=0.045, color="#221e1b")
    head += bk.eyes("head.eye", head_at, head_dims, spacing=0.72, height=0.04,
                    size=0.06, style="angry", iris=EMBER, sclera="#ffe0b2")
    head.append(bk.slab("head.brow", (0.34, 0.14, 0.06),
                        (0, head_at[1] + 0.06, head_at[2] + 0.13), color=BRONZE))
    # THE horn: a long stone spike off the snout, plus a small second horn.
    head.append(bk.wedge("head.horn.main", (0.16, 0.16, 0.54),
                         (0, head_at[1] + 0.32, head_at[2] + 0.16),
                         rot=(-40, 0, 0), color=horn_c, taper=0.9))
    head.append(bk.slab("head.horn.band", (0.155, 0.11, 0.05),
                        (0, head_at[1] + 0.255, head_at[2] + 0.015),
                        rot=(-40, 0, 0), color=GOLD))
    head.append(bk.wedge("head.horn.second", (0.09, 0.09, 0.17),
                         (0, head_at[1] + 0.13, head_at[2] + 0.21),
                         rot=(-30, 0, 0), color=horn_c, taper=0.8))
    head.append(bk.block("head.ring", (0.09, 0.03, 0.09),
                         (0, head_at[1] + 0.30, head_at[2] - 0.16), color=GOLD))

    # Bull horns sweep out of the temples -- animated as ears so they toss.
    ears = []
    for side, sign in (("L", 1), ("R", -1)):
        base = (sign * 0.16, head_at[1] - 0.03, head_at[2] + 0.10)
        parts = [
            _strut("ear.%s.a" % side, base,
                   (sign * 0.33, head_at[1] - 0.05, head_at[2] + 0.20),
                   0.085, horn_c),
            _strut("ear.%s.b" % side,
                   (sign * 0.33, head_at[1] - 0.05, head_at[2] + 0.20),
                   (sign * 0.40, head_at[1] + 0.06, head_at[2] + 0.34),
                   0.065, horn_c, taper=0.7),
            bk.slab("ear.%s.band" % side, (0.09, 0.09, 0.035),
                    (sign * 0.26, head_at[1] - 0.04, head_at[2] + 0.155),
                    rot=(0, sign * 60, 0), color=GOLD_DK),
        ]
        left = _join("ear.%s" % side, parts, base)
        ears.append(left)

    # -- arms: heavy, with bronze bracers and fists ------------------------
    arm_parts = []
    shoulder = (0.32, 0.0, 0.92)
    elbow = (0.40, 0.04, 0.62)
    fist = (0.42, 0.10, 0.38)
    arm_parts.append(_strut("arm.L.upper", shoulder, elbow, 0.15, hide))
    arm_parts.append(_strut("arm.L.fore", elbow, fist, 0.14, hide))
    arm_parts.append(bk.block("arm.L.bracer", (0.17, 0.17, 0.14),
                              (0.41, 0.07, 0.50), color=BRONZE))
    arm_parts.append(bk.slab("arm.L.bracer.trim", (0.18, 0.18, 0.03),
                             (0.41, 0.07, 0.555), color=GOLD))
    arm_parts.append(bk.block("arm.L.fist", (0.17, 0.19, 0.16),
                              (0.42, 0.11, 0.32), color=hide_dk))
    arm_l = _join("arm.L", arm_parts, shoulder)
    arm_r = _mirror(arm_l, "arm.R")

    # -- legs: short, thick, hooved ---------------------------------------
    legs = {}
    parts = [
        _strut("leg.FL.thigh", (0.17, 0.0, 0.56), (0.19, -0.03, 0.30), 0.17, hide),
        _strut("leg.FL.shin", (0.19, -0.03, 0.30), (0.19, 0.02, 0.10), 0.14, hide_dk),
        bk.block("leg.FL.hoof", (0.19, 0.24, 0.09), (0.19, 0.05, 0.05),
                 color=STONE_DK),
        bk.slab("leg.FL.anklet", (0.16, 0.16, 0.04), (0.19, 0.01, 0.14),
                color=BRONZE),
    ]
    leg_l = _join("leg.FL", parts, (0.17, 0.0, 0.56))
    legs["leg.FL"] = leg_l
    legs["leg.FR"] = _mirror(leg_l, "leg.FR")

    tail = _join("tail", [
        _strut("tail.a", (0, -0.20, 0.72), (0, -0.30, 0.52), 0.075, hide),
        bk.block("tail.tuft", (0.09, 0.09, 0.13), (0, -0.31, 0.44), color=hide_dk),
    ], (0, -0.20, 0.72))

    groups = {
        "body": (body, (0, 0, 0.56)),
        "head": (head, (0, 0.18, 1.02)),
        "ear.L": ([ears[0]], tuple(ears[0].location)),
        "ear.R": ([ears[1]], tuple(ears[1].location)),
        "arm.L": ([arm_l], tuple(arm_l.location)),
        "arm.R": ([arm_r], tuple(arm_r.location)),
        "tail": ([tail], tuple(tail.location)),
    }
    for key, obj in legs.items():
        groups[key] = ([obj], tuple(obj.location))
    _assemble(root, groups)
    return bk.finish(root)


# ===========================================================================
# Mutant Shark -- Secret, $215M/s.
# The temple got into it. The main jaw is too big, there are two more jaws
# growing out of the neck, the fins are torn into steps, and lit tumours push
# out between the plates.
# ===========================================================================

def build_mutant_shark():
    kit.reset_scene()
    root = kit.empty("root")

    skin = "#787d72"
    skin_dk = "#4d534c"
    belly_c = "#cfc9b6"
    gum = BLOOD
    tooth = "#efe9d8"
    tumour = EMBER

    # It swims at a hard nose-up angle. A shark is a long horizontal thing;
    # pitching the whole spine 30 degrees is what stops it normalising into a
    # flat plank, and it reads as a lunge rather than a log. Centreline
    # stations (y, z), tail to snout: (-0.70, 0.30) (-0.26, 0.50)
    # (0.36, 0.86) (0.46, 0.92) (0.76, 1.04).

    # -- body: a torpedo built along the rising spine ----------------------
    body = [
        _strut("body.core", (0, -0.26, 0.50), (0, 0.36, 0.86), 0.38, skin,
               thick_y=0.42),
        _strut("body.rear", (0, -0.58, 0.36), (0, -0.20, 0.52), 0.28, skin,
               thick_y=0.32),
        _strut("body.belly", (0, -0.18, 0.32), (0, 0.40, 0.66), 0.28, belly_c,
               thick_y=0.07),
    ]
    # Gill slashes, raked back along the shoulder.
    for i in range(4):
        body.append(bk.slab("body.gill%d" % i, (0.40, 0.03, 0.21),
                            (0, 0.20 - i * 0.06, 0.80 - i * 0.035),
                            rot=(30, 0, 0), color=skin_dk))
    # Lit tumours pushing out between the plates.
    for i, (u, y, z, s) in enumerate((
            (0.13, 0.14, 0.88, 0.09), (-0.16, 0.00, 0.78, 0.07),
            (0.07, -0.22, 0.62, 0.08), (-0.09, -0.44, 0.46, 0.06),
            (0.18, -0.10, 0.60, 0.07))):
        body.append(bk.glow_block("body.tumour%d" % i, (s, s, s),
                                  (u, y, z), color=tumour, strength=3.0))
    # Ragged dorsal: one tall crooked blade with two torn stubs behind it.
    body.append(_strut("body.dorsal", (0, 0.06, 0.82), (0, -0.20, 1.30),
                       0.065, skin_dk, taper=0.45, thick_y=0.32))
    body.append(_strut("body.dorsal.vein", (0, 0.02, 0.90), (0, -0.16, 1.22),
                       0.04, tumour, thick_y=0.055, glow=2.2))
    body.append(_strut("body.dorsal.rip1", (0, -0.30, 0.62), (0, -0.42, 0.88),
                       0.05, skin_dk, taper=0.5, thick_y=0.16))

    # -- head: an oversized maw plus two parasitic side jaws ---------------
    head_dims = (0.34, 0.30, 0.32)
    head_at = (0, 0.46, 0.92)
    head = [bk.block("head.skull", head_dims, head_at, rot=(30, 0, 0),
                     color=skin)]
    # The snout is a long point that overhangs the mouth -- that overhang is
    # the single feature that says "shark" from any angle.
    head.append(_strut("head.snout", (0, 0.48, 0.96), (0, 0.86, 1.10), 0.30,
                       skin, taper=0.74, thick_y=0.20))
    # Open maw: red gums slung under the snout, two rows of teeth.
    head.append(bk.block("head.gum", (0.28, 0.26, 0.18), (0, 0.64, 0.80),
                         rot=(30, 0, 0), color=gum))
    # Teeth stand at the FRONT lip of the mouth; anywhere further back and the
    # snout hides them from every angle that matters.
    for i in range(5):
        u = (i - 2) * 0.06
        head.append(bk.wedge("head.tooth.up%d" % i, (0.05, 0.05, 0.12),
                             (u, 0.80, 0.83), rot=(150, 0, 0), color=tooth,
                             taper=0.85))
        head.append(bk.wedge("head.tooth.low%d" % i, (0.05, 0.05, 0.10),
                             (u, 0.76, 0.66), rot=(28, 0, 0), color=tooth,
                             taper=0.85))
    head.append(bk.block("head.jaw", (0.27, 0.26, 0.12), (0, 0.63, 0.63),
                         rot=(30, 0, 0), color=skin_dk))
    for side, sign in (("L", 1), ("R", -1)):
        head.append(bk.glow_block("head.eye.%s" % side, (0.06, 0.065, 0.065),
                                  (sign * 0.16, 0.56, 0.99), color="#ffe9a8",
                                  strength=3.2))
    # The extra jaws: warped little mouths bursting out of each cheek.
    for side, sign in (("L", 1), ("R", -1)):
        base = (sign * 0.23, 0.34, 0.87)
        head.append(bk.block("head.jaw2.%s" % side, (0.17, 0.22, 0.19), base,
                             rot=(18, sign * 34, 0), color=skin_dk))
        head.append(bk.glow_block("head.jaw2.gum.%s" % side, (0.07, 0.16, 0.11),
                                  (sign * 0.32, 0.39, 0.86),
                                  rot=(18, sign * 34, 0), color=gum,
                                  strength=1.6))
        for i in range(3):
            head.append(bk.wedge(
                "head.jaw2.tooth.%s%d" % (side, i), (0.035, 0.035, 0.085),
                (sign * 0.37, 0.42, 0.95 - i * 0.07),
                rot=(0, sign * 102, 0), color=tooth, taper=0.8))

    # -- fins: torn pectorals and a lopsided caudal ------------------------
    def pectoral(tag):
        return [
            _strut("%s.main" % tag, (0.16, 0.16, 0.62), (0.54, 0.00, 0.38),
                   0.28, skin_dk, thick_y=0.06),
            _strut("%s.rip" % tag, (0.46, -0.04, 0.44), (0.66, -0.22, 0.26),
                   0.15, skin_dk, thick_y=0.055),
            _strut("%s.vein" % tag, (0.19, 0.16, 0.64), (0.48, 0.02, 0.43),
                   0.05, tumour, thick_y=0.035, glow=2.0),
        ]

    fin_l = _join("fin.L", pectoral("fin.L"), (0.16, 0.16, 0.62))
    fin_r = _mirror(fin_l, "fin.R")

    tail = _join("tail", [
        _strut("tail.peduncle", (0, -0.70, 0.30), (0, -0.48, 0.39), 0.17, skin,
               thick_y=0.20),
        _strut("tail.keel", (0, -0.66, 0.32), (0, -0.52, 0.37), 0.26, skin_dk,
               thick_y=0.045),
    ], (0, -0.48, 0.39))

    # Caudal fin: a tall crooked upper lobe over a short lower one.
    caudal = _join("fin.tail", [
        _strut("fin.tail.up", (0, -0.70, 0.31), (0, -0.90, 0.82), 0.055,
               skin_dk, taper=0.5, thick_y=0.28),
        _strut("fin.tail.down", (0, -0.70, 0.31), (0, -0.86, 0.05), 0.055,
               skin_dk, taper=0.5, thick_y=0.22),
        _strut("fin.tail.edge", (0, -0.75, 0.36), (0, -0.92, 0.76), 0.035,
               tumour, thick_y=0.05, glow=2.2),
    ], (0, -0.70, 0.31))

    _assemble(root, {
        "body": (body, (0, -0.10, 0.60)),
        "head": (head, (0, 0.30, 0.84)),
        "fin.L": ([fin_l], tuple(fin_l.location)),
        "fin.R": ([fin_r], tuple(fin_r.location)),
        "tail": ([tail], tuple(tail.location)),
        "fin.tail": ([caudal], tuple(caudal.location)),
    })
    return bk.finish(root)


# ===========================================================================
# Gorilla King -- Eternal, $880M/s.
# The temple's owner. Enormous shoulders, short legs, a gold crown, gold
# pauldrons, and a stone pillar carried in one fist like a club. The pillar
# is grouped under arm.L so it swings with him.
# ===========================================================================

def build_gorilla_king():
    kit.reset_scene()
    root = kit.empty("root")

    fur = "#2f2b2e"
    fur_dk = "#201d20"
    back = "#585260"      # silverback saddle
    face_c = "#5c4c40"

    # -- torso: barrel chest, sloped silverback ----------------------------
    body_dims = (0.70, 0.46, 0.50)
    body_at = (0, -0.02, 0.88)
    body = [bk.block("body.torso", body_dims, body_at, color=fur)]
    body.append(bk.block("body.hips", (0.46, 0.38, 0.26),
                         (0, -0.06, 0.56), color=fur_dk))
    body.append(bk.slab("body.saddle", (0.58, 0.42, 0.11),
                        (0, -0.12, 1.09), color=back))
    chest = bk.face_of(body_at, body_dims, "front")
    body.append(bk.face_plate("body.chest", chest, (0.40, 0.36), face="front",
                              color=fur_dk, depth=0.03))
    # Gold harness across the chest.
    for i, (u, lean) in enumerate(((-0.13, 22), (0.13, -22))):
        body.append(bk.slab("body.strap%d" % i, (0.07, 0.05, 0.46),
                            (u, chest[1] + 0.02, body_at[2]), rot=(0, lean, 0),
                            color=GOLD_DK))
    body.append(bk.glow_block("body.medal", (0.13, 0.06, 0.13),
                              (0, chest[1] + 0.03, body_at[2] - 0.02),
                              color=EMBER, strength=2.4))
    # Pauldrons: three stepped gold plates per shoulder.
    for side, sign in (("L", 1), ("R", -1)):
        for i, (dx, dz, w) in enumerate(((0.34, 0.18, 0.26),
                                         (0.41, 0.07, 0.21),
                                         (0.45, -0.05, 0.16))):
            body.append(bk.slab("body.pauldron.%s%d" % (side, i),
                                (w, 0.38 - i * 0.05, 0.10),
                                (sign * dx, -0.02, 1.04 + dz - 0.16),
                                rot=(0, -sign * (18 + i * 8), 0),
                                color=GOLD if i == 0 else GOLD_DK))

    # -- head: jutting forward out of the shoulders, not sunk between ------
    head_dims = (0.40, 0.36, 0.32)
    head_at = (0, 0.36, 1.20)
    head = [bk.block("head.skull", head_dims, head_at, color=fur)]
    head.append(bk.block("head.muzzle", (0.30, 0.20, 0.18),
                         (0, head_at[1] + 0.20, head_at[2] - 0.10), color=face_c))
    head.append(bk.slab("head.brow", (0.36, 0.16, 0.08),
                        (0, head_at[1] + 0.10, head_at[2] + 0.09), color=fur_dk))
    muzzle_at = (0, head_at[1] + 0.20, head_at[2] - 0.10)
    head += bk.nostrils("head.nostril", muzzle_at, (0.30, 0.20, 0.18),
                        spacing=0.34, height=0.03, size=0.04, color="#191416")
    head += bk.mouth("head.mouth", muzzle_at, (0.30, 0.20, 0.18), width=0.18,
                     height=0.04, drop=-0.05, color="#191416", style="line")
    head += bk.eyes("head.eye", head_at, head_dims, spacing=0.46, height=0.04,
                    size=0.058, style="glow", iris=EMBER_PALE)
    # Crown: a gold band with five temple spikes.
    head.append(bk.block("head.crown.band", (0.40, 0.36, 0.07),
                         (0, head_at[1] - 0.01, head_at[2] + 0.17), color=GOLD))
    head.append(bk.slab("head.crown.trim", (0.41, 0.37, 0.02),
                        (0, head_at[1] - 0.01, head_at[2] + 0.20), color=GOLD_DK))
    for i, (u, y, h) in enumerate((
            (0.0, 0.16, 0.19), (-0.15, 0.10, 0.14), (0.15, 0.10, 0.14),
            (-0.18, -0.06, 0.11), (0.18, -0.06, 0.11))):
        head.append(bk.wedge("head.crown.spike%d" % i, (0.06, 0.06, h),
                             (u, head_at[1] + y, head_at[2] + 0.21 + h * 0.45),
                             color=GOLD, taper=0.75))
    head.append(bk.gem("head.crown.gem", (0, head_at[1] + 0.19,
                                          head_at[2] + 0.22), size=0.09,
                       color=EMBER, strength=3.4)[0])

    # -- arms: long enough to knuckle the floor ----------------------------
    # Arms are the whole read: they reach past the knees to the floor.
    def build_arm(tag, hand_z, forward):
        shoulder = (0.40, -0.02, 1.04)
        elbow = (0.56, 0.04 + forward * 0.4, 0.58)
        hand = (0.56, 0.14 + forward, hand_z)
        return [
            _strut("%s.upper" % tag, shoulder, elbow, 0.21, fur),
            _strut("%s.fore" % tag, elbow, hand, 0.19, fur),
            bk.slab("%s.cuff" % tag, (0.22, 0.22, 0.055),
                    (0.56, 0.09 + forward * 0.7, hand_z + 0.17), color=GOLD_DK),
            bk.block("%s.fist" % tag, (0.22, 0.27, 0.19),
                     (0.56, 0.16 + forward, hand_z - 0.03), color=fur_dk),
        ], shoulder

    # Right arm knuckles the ground.
    right_parts, shoulder = build_arm("arm.R", 0.14, 0.06)
    arm_r_src = _join("arm.R.src", right_parts, shoulder)
    arm_r = _mirror(arm_r_src, "arm.R")
    _discard(arm_r_src)

    # Left arm is raised, gripping a temple pillar through the fist.
    left_parts, shoulder = build_arm("arm.L", 0.52, 0.16)
    # Stood outboard of the fist so the column reads as its own object rather
    # than merging into the arm behind it.
    pillar_x, pillar_y = 0.76, 0.40
    left_parts += [
        bk.block("arm.L.pillar", (0.21, 0.21, 0.86),
                 (pillar_x, pillar_y, 0.58), color=STONE_PALE),
        bk.block("arm.L.pillar.cap", (0.28, 0.28, 0.10),
                 (pillar_x, pillar_y, 1.05), color=STONE_DK),
        bk.block("arm.L.pillar.base", (0.28, 0.28, 0.10),
                 (pillar_x, pillar_y, 0.11), color=STONE_DK),
        bk.slab("arm.L.pillar.inlay1", (0.225, 0.225, 0.035),
                (pillar_x, pillar_y, 0.88), color=GOLD),
        bk.slab("arm.L.pillar.inlay2", (0.225, 0.225, 0.035),
                (pillar_x, pillar_y, 0.30), color=GOLD),
        bk.glow_block("arm.L.pillar.rune", (0.05, 0.22, 0.26),
                      (pillar_x, pillar_y, 0.59), color=EMBER, strength=2.2),
    ]
    arm_l = _join("arm.L", left_parts, shoulder)

    # -- legs: short, crouched, wide feet ---------------------------------
    parts = [
        _strut("leg.FL.thigh", (0.20, 0.0, 0.58), (0.26, -0.02, 0.30), 0.23, fur),
        _strut("leg.FL.shin", (0.26, -0.02, 0.30), (0.25, 0.04, 0.11), 0.19,
               fur_dk),
        bk.block("leg.FL.foot", (0.23, 0.32, 0.12), (0.25, 0.12, 0.06),
                 color=fur_dk),
        bk.slab("leg.FL.anklet", (0.21, 0.21, 0.05), (0.255, 0.02, 0.17),
                color=GOLD_DK),
    ]
    leg_l = _join("leg.FL", parts, (0.20, 0.0, 0.58))
    leg_r = _mirror(leg_l, "leg.FR")

    _assemble(root, {
        "body": (body, (0, 0, 0.60)),
        "head": (head, (0, 0.22, 1.06)),
        "arm.L": ([arm_l], tuple(arm_l.location)),
        "arm.R": ([arm_r], tuple(arm_r.location)),
        "leg.FL": ([leg_l], tuple(leg_l.location)),
        "leg.FR": ([leg_r], tuple(leg_r.location)),
    })
    return bk.finish(root)


# ===========================================================================
# Nightflame -- Divine, $3B/s. The last pet in the game.
# Black scale, gold temple armour, six horns, and wings that are not membrane
# but sheets of violet-black fire. Everything about it is one tier louder than
# anything else in the biome: more gold, more emissive, a halo, and a chest
# furnace you can see burning through the plate.
# ===========================================================================

def build_nightflame():
    kit.reset_scene()
    root = kit.empty("root")

    scale_c = VOID
    scale_dk = "#332b40"
    plate = GOLD
    plate_dk = GOLD_DK
    fire = VIOLET
    fire_pale = "#c98bff"

    # -- torso: chest up, hips back, gold cuirass over black scale ---------
    body_dims = (0.44, 0.46, 0.50)
    body_at = (0, 0.02, 1.00)
    body = [bk.block("body.chest", body_dims, body_at, color=scale_c)]
    body.append(bk.block("body.hips", (0.40, 0.42, 0.36),
                         (0, -0.32, 0.84), color=scale_dk))
    chest = bk.face_of(body_at, body_dims, "front")
    body.append(bk.face_plate("body.cuirass", chest, (0.36, 0.40), face="front",
                              color=plate, depth=0.05, offset=(0, 0.0)))
    body.append(bk.face_plate("body.cuirass.trim", chest, (0.40, 0.06),
                              face="front", color=plate_dk, depth=0.04,
                              offset=(0, -0.20), proud=bk.PROUD * 9))
    # The furnace: violet fire burning through the middle of the breastplate.
    body.append(bk.glow_block("body.furnace", (0.15, 0.08, 0.18),
                              (0, chest[1] + 0.07, body_at[2] + 0.02),
                              color=fire, strength=4.2))
    body.append(bk.glow_block("body.furnace.core", (0.065, 0.06, 0.075),
                              (0, chest[1] + 0.10, body_at[2] + 0.02),
                              color=fire_pale, strength=5.0))
    # Gold shoulder plates.
    for side, sign in (("L", 1), ("R", -1)):
        body.append(bk.block("body.pauldron.%s" % side, (0.17, 0.30, 0.14),
                             (sign * 0.28, 0.06, 1.18), rot=(0, -sign * 20, 0),
                             color=plate))
        body.append(bk.slab("body.pauldron.spike.%s" % side, (0.06, 0.11, 0.20),
                            (sign * 0.33, 0.08, 1.29), rot=(0, -sign * 34, 0),
                            color=plate_dk))
    # Spine crest: violet flame tongues running down the back.
    for i, (y, h) in enumerate(((0.12, 0.15), (-0.06, 0.18), (-0.24, 0.15),
                                (-0.40, 0.12))):
        body.append(bk.wedge("body.crest%d" % i, (0.055, 0.08, h),
                             (0, y, 1.26 - i * 0.06 + h * 0.4),
                             rot=(-16, 0, 0), color=scale_dk, taper=0.6))
        body.append(bk.glow_block("body.crest.fire%d" % i,
                                  (0.03, 0.045, h * 0.7),
                                  (0, y - 0.012, 1.29 - i * 0.06 + h * 0.4),
                                  rot=(-16, 0, 0), color=fire, strength=3.0))

    # -- neck: three rising blocks with gold collars -----------------------
    neck = []
    for i, (y, z, s) in enumerate(((0.18, 1.22, 0.24), (0.28, 1.38, 0.22),
                                   (0.36, 1.52, 0.20))):
        neck.append(bk.block("head.neck%d" % i, (s, 0.22, 0.20),
                             (0, y, z), rot=(26, 0, 0), color=scale_c))
        neck.append(bk.slab("head.collar%d" % i, (s + 0.025, 0.05, 0.21),
                            (0, y - 0.055, z), rot=(26, 0, 0), color=plate_dk))

    # -- head: long snout, gold mask, violet eyes --------------------------
    head_dims = (0.30, 0.34, 0.28)
    head_at = (0, 0.48, 1.68)
    head = list(neck)
    head.append(bk.block("head.skull", head_dims, head_at, color=scale_c))
    head.append(bk.wedge("head.snout", (0.22, 0.30, 0.30),
                         (0, head_at[1] + 0.24, head_at[2] - 0.04),
                         rot=(-96, 0, 0), color=scale_c, taper=0.4))
    head.append(bk.block("head.jaw", (0.19, 0.26, 0.08),
                         (0, head_at[1] + 0.22, head_at[2] - 0.13),
                         rot=(-8, 0, 0), color=scale_dk))
    head.append(bk.slab("head.mask", (0.30, 0.22, 0.10),
                        (0, head_at[1] + 0.04, head_at[2] + 0.08), color=plate))
    head += bk.eyes("head.eye", head_at, head_dims, spacing=0.60, height=0.01,
                    size=0.085, style="glow", iris=fire_pale)
    head.append(bk.glow_block("head.maw", (0.15, 0.16, 0.035),
                              (0, head_at[1] + 0.26, head_at[2] - 0.10),
                              rot=(-8, 0, 0), color=fire, strength=3.2))
    # Gold ridge running the length of the snout.
    head.append(bk.slab("head.ridge", (0.075, 0.26, 0.05),
                        (0, head_at[1] + 0.22, head_at[2] + 0.08),
                        rot=(-6, 0, 0), color=plate))
    for side, sign in (("L", 1), ("R", -1)):
        head.append(bk.wedge("head.fang.%s" % side, (0.03, 0.03, 0.07),
                             (sign * 0.055, head_at[1] + 0.26,
                              head_at[2] - 0.075),
                             rot=(-170, 0, 0), color="#f2ead6", taper=0.8))
    # Cheek horns (the lower pair of the six).
    for side, sign in (("L", 1), ("R", -1)):
        head.append(bk.wedge("head.cheekhorn.%s" % side, (0.045, 0.045, 0.16),
                             (sign * 0.14, head_at[1] - 0.02, head_at[2] - 0.05),
                             rot=(0, sign * 128, 0), color=plate_dk, taper=0.7))

    # -- six horns: the upper four are ear.L/ear.R clusters so they sway ---
    horns = []
    for side, sign in (("L", 1), ("R", -1)):
        base = (sign * 0.10, head_at[1] - 0.09, head_at[2] + 0.11)
        parts = [
            # Great swept horn -- the tallest thing on the model.
            _strut("ear.%s.great" % side, base,
                   (sign * 0.28, head_at[1] - 0.42, head_at[2] + 0.50),
                   0.085, "#4a4058"),
            _strut("ear.%s.great.tip" % side,
                   (sign * 0.28, head_at[1] - 0.42, head_at[2] + 0.50),
                   (sign * 0.38, head_at[1] - 0.72, head_at[2] + 0.40),
                   0.06, "#4a4058", taper=0.7),
            bk.slab("ear.%s.great.band" % side, (0.085, 0.085, 0.035),
                    (sign * 0.18, head_at[1] - 0.23, head_at[2] + 0.28),
                    rot=(48, sign * 24, 0), color=plate),
            # Second, shorter horn just outboard of it.
            _strut("ear.%s.minor" % side,
                   (sign * 0.16, head_at[1] - 0.04, head_at[2] + 0.10),
                   (sign * 0.30, head_at[1] - 0.16, head_at[2] + 0.30),
                   0.05, "#4a4058", taper=0.65),
            bk.glow_block("ear.%s.ember" % side, (0.04, 0.04, 0.04),
                          (sign * 0.31, head_at[1] - 0.17, head_at[2] + 0.32),
                          color=fire, strength=3.0),
        ]
        horns.append(_join("ear.%s" % side, parts, base))

    # -- wings of dark flame ----------------------------------------------
    # Not membrane: sheets of violet-black fire hung off a black spar, with
    # burning tongues along the trailing edge.
    # A leading-edge spar that sweeps out and well ABOVE the horns, with the
    # membrane hung off it as a fan of tapering flame blades. Blocks big
    # enough to be a wing are just boxes; a fan of blades is a wing.
    def wing(tag):
        root_at = (0.16, -0.04, 1.16)
        elbow = (0.60, -0.10, 1.88)
        tip = (1.00, -0.28, 1.82)
        parts = [
            _strut("%s.spar1" % tag, root_at, elbow, 0.09, scale_dk,
                   thick_y=0.10),
            _strut("%s.spar2" % tag, elbow, tip, 0.07, scale_dk, taper=0.5,
                   thick_y=0.08),
            _strut("%s.spar.fire" % tag, (0.22, -0.05, 1.24), (0.58, -0.10, 1.84),
                   0.035, fire, thick_y=0.035, glow=2.8),
            bk.block("%s.claw" % tag, (0.06, 0.06, 0.15),
                     (0.64, -0.06, 1.98), rot=(-14, -24, 0), color=plate_dk),
        ]
        # The membrane: five blades of violet-black fire fanning down and back.
        blades = ((0.28, -0.06, 1.34, 0.32, -0.46, 0.82, 0.20),
                  (0.44, -0.08, 1.60, 0.52, -0.52, 0.94, 0.19),
                  (0.62, -0.10, 1.84, 0.74, -0.56, 1.10, 0.18),
                  (0.80, -0.18, 1.86, 0.92, -0.58, 1.28, 0.16),
                  (0.96, -0.26, 1.82, 1.06, -0.54, 1.46, 0.14))
        for i, (ax, ay, az, bx, by, bz, w) in enumerate(blades):
            parts.append(_strut(
                "%s.blade%d" % (tag, i), (ax, ay, az), (bx, by, bz), w,
                "#2f2043" if i % 2 == 0 else "#20163a", taper=0.42,
                thick_y=0.05))
        # Fire burning along the blade roots, and tongues at the trailing tips.
        for i, (ax, ay, az, bx, by, bz, w) in enumerate(blades):
            parts.append(_strut(
                "%s.fire%d" % (tag, i), (ax, ay - 0.03, az),
                (ax * 0.5 + bx * 0.5, ay * 0.5 + by * 0.5 - 0.03,
                 az * 0.5 + bz * 0.5), w * 0.42, fire, thick_y=0.03, glow=2.8))
            parts.append(bk.wedge(
                "%s.tongue%d" % (tag, i), (w * 0.42, 0.06, 0.17),
                (bx, by - 0.02, bz - 0.09), rot=(196, 0, 0), color=fire_pale,
                taper=0.75))
        return parts, root_at

    wing_parts, wing_root = wing("wing.L")
    wing_l = _join("wing.L", wing_parts, wing_root)
    wing_r = _mirror(wing_l, "wing.R")

    # -- legs: heavy digitigrade with gold greaves -------------------------
    leg_parts = [
        _strut("leg.FL.thigh", (0.20, -0.12, 0.86), (0.26, -0.26, 0.52),
               0.20, scale_c),
        _strut("leg.FL.shin", (0.26, -0.26, 0.52), (0.25, 0.02, 0.26),
               0.15, scale_dk),
        _strut("leg.FL.ankle", (0.25, 0.02, 0.26), (0.25, 0.08, 0.07),
               0.13, scale_dk),
        bk.block("leg.FL.foot", (0.18, 0.26, 0.09), (0.25, 0.17, 0.05),
                 color=scale_dk),
        bk.slab("leg.FL.greave", (0.21, 0.17, 0.10), (0.255, -0.08, 0.40),
                rot=(-24, 0, 0), color=plate),
        bk.glow_block("leg.FL.rune", (0.05, 0.05, 0.05),
                      (0.255, -0.04, 0.35), color=fire, strength=2.6),
    ]
    for i, u in enumerate((-0.055, 0.0, 0.055)):
        leg_parts.append(bk.wedge("leg.FL.claw%d" % i, (0.038, 0.038, 0.085),
                                  (0.25 + u, 0.30, 0.045), rot=(-96, 0, 0),
                                  color="#f2ead6", taper=0.75))
    leg_l = _join("leg.FL", leg_parts, (0.20, -0.12, 0.86))
    leg_r = _mirror(leg_l, "leg.FR")

    # -- small forelimbs ---------------------------------------------------
    arm_parts = [
        _strut("arm.L.upper", (0.23, 0.16, 1.06), (0.32, 0.32, 0.86), 0.095,
               scale_c),
        _strut("arm.L.fore", (0.32, 0.32, 0.86), (0.31, 0.44, 0.70), 0.08,
               scale_dk),
        bk.slab("arm.L.bracer", (0.12, 0.12, 0.05), (0.32, 0.35, 0.82),
                color=plate),
    ]
    for i, u in enumerate((-0.045, 0.0, 0.045)):
        arm_parts.append(bk.wedge("arm.L.claw%d" % i, (0.03, 0.03, 0.075),
                                  (0.31 + u, 0.48, 0.66), rot=(-118, 0, 0),
                                  color="#f2ead6", taper=0.8))
    arm_l = _join("arm.L", arm_parts, (0.23, 0.16, 1.06))
    arm_r = _mirror(arm_l, "arm.R")

    # -- tail: long, banded, ending in a flame blade -----------------------
    tail_parts = []
    pts = ((0, -0.48, 0.88), (0, -0.74, 0.74), (0, -1.00, 0.66),
           (0, -1.24, 0.70), (0, -1.42, 0.86))
    for i in range(len(pts) - 1):
        tail_parts.append(_strut("tail.seg%d" % i, pts[i], pts[i + 1],
                                 0.18 - i * 0.03, scale_c))
        tail_parts.append(bk.slab("tail.band%d" % i, (0.17 - i * 0.03, 0.035,
                                                      0.17 - i * 0.03),
                                  pts[i + 1], color=plate_dk))
    tail_parts.append(bk.wedge("tail.blade", (0.055, 0.17, 0.28),
                               (0, -1.48, 1.02), rot=(-18, 0, 0),
                               color=scale_dk, taper=0.55))
    tail_parts.append(bk.glow_block("tail.flame", (0.035, 0.09, 0.20),
                                    (0, -1.50, 1.08), rot=(-18, 0, 0),
                                    color=fire, strength=3.4))
    tail = _join("tail", tail_parts, (0, -0.44, 0.90))

    # -- halo: a burning ring behind the head, the divine tell -------------
    halo = bk.ring("body.halo", (0, -0.26, 1.96), radius=0.30, thickness=0.03,
                   tilt=82.0, color=fire, strength=2.8)
    body += halo

    _assemble(root, {
        "body": (body, (0, 0, 0.70)),
        "head": (head, (0, 0.12, 1.16)),
        "ear.L": ([horns[0]], tuple(horns[0].location)),
        "ear.R": ([horns[1]], tuple(horns[1].location)),
        "wing.L": ([wing_l], tuple(wing_l.location)),
        "wing.R": ([wing_r], tuple(wing_r.location)),
        "arm.L": ([arm_l], tuple(arm_l.location)),
        "arm.R": ([arm_r], tuple(arm_r.location)),
        "leg.FL": ([leg_l], tuple(leg_l.location)),
        "leg.FR": ([leg_r], tuple(leg_r.location)),
        "tail": ([tail], tuple(tail.location)),
    })
    return bk.finish(root)


PETS = {
    "spideron": build_spideron,
    "crustacia": build_crustacia,
    "bladehide": build_bladehide,
    "mantaris": build_mantaris,
    "rhinotaur": build_rhinotaur,
    "mutant-shark": build_mutant_shark,
    "gorilla-king": build_gorilla_king,
    "nightflame": build_nightflame,
}
