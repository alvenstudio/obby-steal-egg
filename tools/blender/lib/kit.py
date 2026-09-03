"""
kit.py -- a small, opinionated low-poly modelling toolkit for Blender 4.x/5.x.

Everything in the game is built from this kit so that the whole asset library
shares one silhouette language: chunky rounded primitives, beveled hard edges,
flat matte materials, no textures. Models are exported as .glb with a stable,
documented node hierarchy so the runtime can animate parts by name.

Node naming contract (the runtime's PetAnimator looks these up):
    root                 -- top level empty, origin at the model's feet
    body                 -- main torso
    head                 -- head group (bobs, tilts, looks at things)
    ear.L / ear.R        -- flop on movement
    wing.L / wing.R      -- flap
    arm.L / arm.R        -- swing
    leg.FL/.FR/.BL/.BR   -- step cycle
    tail                 -- wags
    fin.L / fin.R        -- undulate
    accessory.*          -- static decoration, never animated
Anything not on this list is welded into its parent group.
"""

from __future__ import annotations

import math
import os
import sys

import bpy
import bmesh
from mathutils import Vector, Euler

TAU = math.tau
D2R = math.pi / 180.0

# --------------------------------------------------------------------------
# scene lifecycle
# --------------------------------------------------------------------------


KEEP_COLLECTION = "__keep__"


def keep_collection(create=True):
    """
    The one collection `reset_scene` will not clear.

    The contact-sheet build needs to accumulate a hundred models in one scene
    while each generator still starts from a clean slate, so parking finished
    work here is what lets both be true at once.
    """
    existing = bpy.data.collections.get(KEEP_COLLECTION)
    if existing is None and create:
        existing = bpy.data.collections.new(KEEP_COLLECTION)
        bpy.context.scene.collection.children.link(existing)
    return existing


def protect(root):
    """Move a finished hierarchy into the keep collection."""
    collection = keep_collection()

    def move(obj):
        for parent in list(obj.users_collection):
            parent.objects.unlink(obj)
        collection.objects.link(obj)
        for child in obj.children:
            move(child)

    move(root)
    return root


def reset_scene() -> None:
    """Wipe the file back to an empty scene, including orphaned datablocks."""
    protected = set()
    keep = bpy.data.collections.get(KEEP_COLLECTION)
    if keep is not None:
        protected = {obj.name for obj in keep.objects}

    deselect_all()
    for obj in bpy.context.scene.objects:
        if obj.name not in protected:
            obj.select_set(True)
    bpy.ops.object.delete(use_global=False)
    for collection in (
        bpy.data.meshes,
        bpy.data.materials,
        bpy.data.armatures,
        bpy.data.objects,
        bpy.data.curves,
    ):
        for block in list(collection):
            if block.users == 0:
                collection.remove(block)
    _MATERIAL_CACHE.clear()


def deselect_all() -> None:
    for obj in bpy.context.scene.objects:
        obj.select_set(False)
    bpy.context.view_layer.objects.active = None


def activate(obj):
    """Make `obj` the sole selected + active object; most operators need both."""
    deselect_all()
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    return obj


# --------------------------------------------------------------------------
# materials
# --------------------------------------------------------------------------

_MATERIAL_CACHE = {}


def mat(
    name,
    color,
    rough=0.72,
    metal=0.0,
    emission=None,
    emission_strength=1.6,
    alpha=1.0,
):
    """Fetch-or-create a flat matte material. Colors are linear 0-1 triples."""
    if name in _MATERIAL_CACHE:
        return _MATERIAL_CACHE[name]

    material = bpy.data.materials.new(name)
    material.use_nodes = True
    bsdf = material.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (color[0], color[1], color[2], 1.0)
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Metallic"].default_value = metal
    if "Specular IOR Level" in bsdf.inputs:
        bsdf.inputs["Specular IOR Level"].default_value = 0.28
    elif "Specular" in bsdf.inputs:
        bsdf.inputs["Specular"].default_value = 0.28
    if emission is not None:
        bsdf.inputs["Emission Color"].default_value = (
            emission[0], emission[1], emission[2], 1.0,
        )
        bsdf.inputs["Emission Strength"].default_value = emission_strength
    if alpha < 1.0:
        bsdf.inputs["Alpha"].default_value = alpha
        material.blend_method = "BLEND"
    _MATERIAL_CACHE[name] = material
    return material


def hexcol(code):
    """'#ff8844' -> linear RGB triple (Blender wants linear, CSS gives sRGB)."""
    code = code.lstrip("#")
    return tuple(
        _srgb_to_linear(int(code[i:i + 2], 16) / 255.0) for i in (0, 2, 4)
    )


def _srgb_to_linear(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def apply_mat(obj, material):
    obj.data.materials.clear()
    obj.data.materials.append(material)
    return obj


# --------------------------------------------------------------------------
# primitives
# --------------------------------------------------------------------------


def _finish(obj, name, loc, rot, scale, material):
    obj.name = name
    obj.data.name = name
    obj.location = Vector(loc)
    obj.rotation_euler = Euler([a * D2R for a in rot])
    obj.scale = Vector(scale)
    if material is not None:
        apply_mat(obj, material)
    return obj


def cube(name, size=1.0, loc=(0, 0, 0), rot=(0, 0, 0), scale=(1, 1, 1), material=None):
    bpy.ops.mesh.primitive_cube_add(size=size, location=(0, 0, 0))
    return _finish(bpy.context.object, name, loc, rot, scale, material)


def box(name, dims=(1, 1, 1), loc=(0, 0, 0), rot=(0, 0, 0), material=None):
    """Cube expressed as full width/depth/height rather than half-extents."""
    return cube(name, 1.0, loc, rot, (dims[0], dims[1], dims[2]), material)


def sphere(name, r=0.5, loc=(0, 0, 0), rot=(0, 0, 0), scale=(1, 1, 1),
           material=None, segments=16, rings=10):
    bpy.ops.mesh.primitive_uv_sphere_add(
        radius=r, segments=segments, ring_count=rings, location=(0, 0, 0)
    )
    return _finish(bpy.context.object, name, loc, rot, scale, material)


def ico(name, r=0.5, subdiv=2, loc=(0, 0, 0), rot=(0, 0, 0), scale=(1, 1, 1), material=None):
    bpy.ops.mesh.primitive_ico_sphere_add(radius=r, subdivisions=subdiv, location=(0, 0, 0))
    return _finish(bpy.context.object, name, loc, rot, scale, material)


def cyl(name, r=0.5, h=1.0, loc=(0, 0, 0), rot=(0, 0, 0), scale=(1, 1, 1),
        material=None, verts=14):
    bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=h, vertices=verts, location=(0, 0, 0))
    return _finish(bpy.context.object, name, loc, rot, scale, material)


def cone(name, r1=0.5, r2=0.0, h=1.0, loc=(0, 0, 0), rot=(0, 0, 0), scale=(1, 1, 1),
         material=None, verts=12):
    bpy.ops.mesh.primitive_cone_add(
        radius1=r1, radius2=r2, depth=h, vertices=verts, location=(0, 0, 0)
    )
    return _finish(bpy.context.object, name, loc, rot, scale, material)


def torus(name, major=0.5, minor=0.12, loc=(0, 0, 0), rot=(0, 0, 0), scale=(1, 1, 1),
          material=None, major_seg=16, minor_seg=8):
    bpy.ops.mesh.primitive_torus_add(
        major_radius=major, minor_radius=minor,
        major_segments=major_seg, minor_segments=minor_seg, location=(0, 0, 0),
    )
    return _finish(bpy.context.object, name, loc, rot, scale, material)


def plane(name, size=1.0, loc=(0, 0, 0), rot=(0, 0, 0), scale=(1, 1, 1), material=None):
    bpy.ops.mesh.primitive_plane_add(size=size, location=(0, 0, 0))
    return _finish(bpy.context.object, name, loc, rot, scale, material)


def capsule(name, r=0.3, h=1.0, loc=(0, 0, 0), rot=(0, 0, 0), scale=(1, 1, 1),
            material=None, verts=14):
    """Cylinder capped by two hemispheres -- the workhorse limb/torso shape."""
    body = cyl(name + ".mid", r=r, h=h, verts=verts)
    top = sphere(name + ".top", r=r, loc=(0, 0, h / 2), segments=verts, rings=max(4, verts // 2))
    bot = sphere(name + ".bot", r=r, loc=(0, 0, -h / 2), segments=verts, rings=max(4, verts // 2))
    merged = join([body, top, bot], name)
    weld(merged, 0.0008)
    return _finish(merged, name, loc, rot, scale, material)


def teardrop(name, r=0.5, stretch=1.45, tip=0.55, loc=(0, 0, 0), rot=(0, 0, 0),
             scale=(1, 1, 1), material=None):
    """An egg/teardrop: a sphere with its top half pinched inward and pulled up."""
    obj = sphere(name + ".src", r=r, segments=20, rings=14)
    for vert in obj.data.vertices:
        t = max(0.0, vert.co.z / r)          # 0 at equator, 1 at pole
        pinch = 1.0 - (1.0 - tip) * (t ** 1.6)
        vert.co.x *= pinch
        vert.co.y *= pinch
        vert.co.z *= 1.0 + (stretch - 1.0) * (t ** 0.85)
    return _finish(obj, name, loc, rot, scale, material)


# --------------------------------------------------------------------------
# mesh operations
# --------------------------------------------------------------------------


def join(objs, name):
    """Join a list of meshes into the first one and rename the result."""
    objs = [o for o in objs if o is not None]
    if not objs:
        raise ValueError("join() got no objects")
    if len(objs) == 1:
        objs[0].name = name
        objs[0].data.name = name
        return objs[0]
    deselect_all()
    for obj in objs:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.join()
    result = bpy.context.object
    result.name = name
    result.data.name = name
    return result


def weld(obj, distance=0.0012):
    """Merge coincident verts -- keeps joined primitives from z-fighting."""
    mesh = bmesh.new()
    mesh.from_mesh(obj.data)
    bmesh.ops.remove_doubles(mesh, verts=mesh.verts, dist=distance)
    mesh.to_mesh(obj.data)
    mesh.free()
    obj.data.update()
    return obj


def bevel(obj, width=0.02, segments=2, angle=42.0):
    activate(obj)
    modifier = obj.modifiers.new("bevel", "BEVEL")
    modifier.width = width
    modifier.segments = segments
    modifier.limit_method = "ANGLE"
    modifier.angle_limit = angle * D2R
    modifier.harden_normals = False
    bpy.ops.object.modifier_apply(modifier=modifier.name)
    return obj


def subsurf(obj, levels=1):
    activate(obj)
    modifier = obj.modifiers.new("subsurf", "SUBSURF")
    modifier.levels = levels
    modifier.render_levels = levels
    bpy.ops.object.modifier_apply(modifier=modifier.name)
    return obj


def mirror_x(obj, use_bisect=False):
    activate(obj)
    modifier = obj.modifiers.new("mirror", "MIRROR")
    modifier.use_axis = (True, False, False)
    modifier.use_bisect_axis = (use_bisect, False, False)
    bpy.ops.object.modifier_apply(modifier=modifier.name)
    return obj


def solidify(obj, thickness=0.04):
    activate(obj)
    modifier = obj.modifiers.new("solidify", "SOLIDIFY")
    modifier.thickness = thickness
    modifier.offset = 0.0
    bpy.ops.object.modifier_apply(modifier=modifier.name)
    return obj


def boolean(target, cutter, operation="DIFFERENCE"):
    activate(target)
    modifier = target.modifiers.new("bool", "BOOLEAN")
    modifier.operation = operation
    modifier.object = cutter
    modifier.solver = "EXACT"
    bpy.ops.object.modifier_apply(modifier=modifier.name)
    bpy.data.objects.remove(cutter, do_unlink=True)
    return target


def smooth(obj, angle=48.0):
    """Shade smooth with an angle threshold; keeps beveled edges crisp."""
    activate(obj)
    bpy.ops.object.shade_smooth()
    try:
        bpy.ops.object.shade_smooth_by_angle(angle=angle * D2R)
    except (AttributeError, RuntimeError):
        if hasattr(obj.data, "use_auto_smooth"):     # Blender < 4.1
            obj.data.use_auto_smooth = True
            obj.data.auto_smooth_angle = angle * D2R
    return obj


def flat(obj):
    activate(obj)
    bpy.ops.object.shade_flat()
    return obj


def apply_transforms(obj, location=False, rotation=True, scale=True):
    activate(obj)
    bpy.ops.object.transform_apply(location=location, rotation=rotation, scale=scale)
    return obj


def set_origin_to(obj, point):
    """Move the object's origin to a world-space point without moving geometry."""
    offset = obj.matrix_world.translation - Vector(point)
    for vert in obj.data.vertices:
        vert.co += offset
    obj.location = Vector(point)
    return obj


def taper(obj, axis="Z", at_min=1.0, at_max=0.4):
    """Scale cross-section linearly along `axis`, from at_min to at_max."""
    idx = "XYZ".index(axis)
    coords = [v.co[idx] for v in obj.data.vertices]
    lo, hi = min(coords), max(coords)
    span = max(hi - lo, 1e-6)
    others = [i for i in range(3) if i != idx]
    for vert in obj.data.vertices:
        t = (vert.co[idx] - lo) / span
        factor = at_min + (at_max - at_min) * t
        for o in others:
            vert.co[o] *= factor
    return obj


def bend_z(obj, amount=0.4, axis="Y"):
    """Curve a shape along Z -- for tails, horns, banana bodies."""
    idx = "XYZ".index(axis)
    coords = [v.co.z for v in obj.data.vertices]
    lo, hi = min(coords), max(coords)
    span = max(hi - lo, 1e-6)
    for vert in obj.data.vertices:
        t = (vert.co.z - lo) / span
        vert.co[idx] += amount * (t ** 2)
    return obj


def jitter(obj, amount=0.02, seed=1):
    """Deterministic vertex noise -- rocks, coral, clouds, fur clumps."""
    state = seed * 1103515245 + 12345
    for vert in obj.data.vertices:
        for i in range(3):
            state = (state * 1103515245 + 12345) & 0x7FFFFFFF
            vert.co[i] += ((state / 0x7FFFFFFF) - 0.5) * 2.0 * amount
    return obj


# --------------------------------------------------------------------------
# grouping / hierarchy
# --------------------------------------------------------------------------


def empty(name, loc=(0, 0, 0)):
    obj = bpy.data.objects.new(name, None)
    obj.empty_display_size = 0.1
    obj.empty_display_type = "PLAIN_AXES"
    obj.location = Vector(loc)
    bpy.context.scene.collection.objects.link(obj)
    return obj


def parent_to(child, parent, keep_transform=True):
    if keep_transform:
        child.parent = parent
        child.matrix_parent_inverse = parent.matrix_world.inverted()
    else:
        child.parent = parent
    return child


def group(name, parts, pivot=(0, 0, 0)):
    """
    Weld `parts` into one mesh named `name` with its origin at `pivot`.
    This is how animatable parts (head, ear.L, tail...) are produced: one mesh,
    one sensible pivot, so the runtime can rotate it directly.
    """
    merged = join(parts, name)
    weld(merged)
    set_origin_to(merged, pivot)
    return merged


def duplicate(obj, name, loc=None, rot=None, scale=None, mirror=False):
    copy = obj.copy()
    copy.data = obj.data.copy()
    copy.name = name
    copy.data.name = name
    bpy.context.scene.collection.objects.link(copy)
    if loc is not None:
        copy.location = Vector(loc)
    if rot is not None:
        copy.rotation_euler = Euler([a * D2R for a in rot])
    if scale is not None:
        copy.scale = Vector(scale)
    if mirror:
        for vert in copy.data.vertices:
            vert.co.x *= -1
        for poly in copy.data.polygons:
            poly.flip()
        copy.data.update()
    return copy


def mirrored_pair(obj, base_name):
    """
    Build the .L part sitting at its left-side position, then produce the .R
    twin by mirroring geometry across X. Returns (left, right).
    """
    obj.name = base_name + ".L"
    obj.data.name = obj.name
    right = duplicate(obj, base_name + ".R", mirror=True)
    right.location = obj.location.copy()
    right.location.x = -obj.location.x
    right.rotation_euler = obj.rotation_euler.copy()
    right.rotation_euler.y = -right.rotation_euler.y
    right.rotation_euler.z = -right.rotation_euler.z
    right.scale = obj.scale.copy()
    return obj, right


# --------------------------------------------------------------------------
# analysis + export
# --------------------------------------------------------------------------


def bounds(objs):
    lo = Vector((1e9, 1e9, 1e9))
    hi = Vector((-1e9, -1e9, -1e9))
    found = False
    for obj in objs:
        if obj.type != "MESH":
            continue
        found = True
        for corner in obj.bound_box:
            world = obj.matrix_world @ Vector(corner)
            for i in range(3):
                lo[i] = min(lo[i], world[i])
                hi[i] = max(hi[i], world[i])
    if not found:
        return Vector((0, 0, 0)), Vector((0, 0, 0))
    return lo, hi


def tri_count(objs):
    total = 0
    for obj in objs:
        if obj.type != "MESH":
            continue
        for poly in obj.data.polygons:
            total += max(1, len(poly.vertices) - 2)
    return total


def scene_meshes(include_protected=False):
    keep = bpy.data.collections.get(KEEP_COLLECTION)
    protected = {obj.name for obj in keep.objects} if keep is not None else set()
    return [
        o for o in bpy.context.scene.objects
        if o.type == "MESH" and (include_protected or o.name not in protected)
    ]


def normalize_height(root, target_height, floor_at_zero=True):
    """
    Uniformly scale the whole hierarchy so its bounding box is `target_height`
    tall, then drop it so its lowest point sits on Z=0. Every pet in the game
    is normalized this way, so gameplay scale is a single number per pet.
    """
    bpy.context.view_layer.update()
    lo, hi = bounds(scene_meshes())
    height = max(hi.z - lo.z, 1e-6)
    factor = target_height / height
    root.scale = Vector((factor, factor, factor))
    bpy.context.view_layer.update()
    if floor_at_zero:
        lo2, _ = bounds(scene_meshes())
        root.location.z -= lo2.z
    bpy.context.view_layer.update()
    return root


def export_glb(path, root=None):
    """Export the whole scene (or `root`'s hierarchy) to a .glb."""
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    deselect_all()
    if root is not None:
        def mark(obj):
            obj.select_set(True)
            for child in obj.children:
                mark(child)
        mark(root)
        bpy.context.view_layer.objects.active = root
    kwargs = dict(
        filepath=path,
        export_format="GLB",
        use_selection=root is not None,
        export_apply=True,
        export_yup=True,
        export_normals=True,
        export_texcoords=False,
        export_materials="EXPORT",
        export_cameras=False,
        export_lights=False,
    )
    try:
        bpy.ops.export_scene.gltf(**kwargs)
    except TypeError:
        bpy.ops.export_scene.gltf(
            filepath=path, export_format="GLB",
            use_selection=root is not None, export_apply=True,
        )
    return path


def report(name, path):
    meshes = scene_meshes()
    lo, hi = bounds(meshes)
    size = hi - lo
    print(
        "[kit] {0}: tris={1} parts={2} size=({3:.2f}, {4:.2f}, {5:.2f}) -> {6}".format(
            name, tri_count(meshes), len(meshes), size.x, size.y, size.z,
            os.path.basename(path),
        ),
        file=sys.stderr,
    )


# --------------------------------------------------------------------------
# preview rendering (visual QA for the asset library)
# --------------------------------------------------------------------------


def _pick_eevee():
    """Engine id moved around between 4.x and 5.x; pick whatever exists."""
    scene = bpy.context.scene
    for engine in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE", "BLENDER_WORKBENCH"):
        try:
            scene.render.engine = engine
            break
        except TypeError:
            continue
    # Blender 4.x+ defaults to AgX, which desaturates so hard that a preview
    # stops being a usable check on the albedo the runtime will actually use.
    for transform in ("Standard", "Filmic", "sRGB"):
        try:
            scene.view_settings.view_transform = transform
            break
        except TypeError:
            continue
    scene.view_settings.look = "None"
    scene.view_settings.exposure = 0.0
    scene.view_settings.gamma = 1.0
    return scene.render.engine


def _sun_rig(prefix, center, directions):
    """
    Three suns instead of area lights. Sun strength is irradiance in W/m^2, so
    a facing surface lands at roughly strength/pi times its albedo -- which
    makes exposure predictable and independent of how big the model is. Area
    lights scale with distance and blew every preview out to white.
    """
    lights = []
    for name, direction, strength, color in directions:
        data = bpy.data.lights.new(prefix + name, type="SUN")
        data.energy = strength
        data.angle = 0.35
        data.color = color
        light = bpy.data.objects.new(prefix + name, data)
        light.location = center + Vector(direction) * 10.0
        light.rotation_euler = (-Vector(direction)).to_track_quat("-Z", "Y").to_euler()
        bpy.context.scene.collection.objects.link(light)
        lights.append(light)
    return lights


_PREVIEW_SUNS = (
    ("key", (0.42, 0.62, 0.66), 2.7, (1.0, 0.97, 0.92)),
    ("fill", (-0.68, 0.42, 0.2), 1.05, (0.74, 0.83, 1.0)),
    ("rim", (-0.2, -0.78, 0.58), 1.35, (1.0, 0.88, 0.74)),
)


def render_preview(path, size=384, angle=38.0, elevation=26.0, bg=(0.09, 0.10, 0.13)):
    """
    Render a 3/4 hero shot of whatever is currently in the scene. Used to build
    contact sheets so a hundred pets can be eyeballed at once.
    """
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)

    meshes = scene_meshes()
    if not meshes:
        return None
    lo, hi = bounds(meshes)
    center = (lo + hi) * 0.5
    radius = max((hi - lo).length * 0.5, 0.35)

    scene = bpy.context.scene
    _pick_eevee()
    scene.render.resolution_x = size
    scene.render.resolution_y = size
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = False
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = path

    world = bpy.data.worlds.get("PreviewWorld") or bpy.data.worlds.new("PreviewWorld")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs[0].default_value = (bg[0], bg[1], bg[2], 1.0)
    world.node_tree.nodes["Background"].inputs[1].default_value = 0.32
    scene.world = world

    # Models are authored facing +Y (which the glTF exporter maps to -Z, the
    # forward axis three.js expects), so the hero camera orbits the +Y side.
    dist = radius * 3.4
    yaw = angle * D2R
    pitch = elevation * D2R
    cam_loc = Vector((
        center.x + dist * math.cos(pitch) * math.sin(yaw),
        center.y + dist * math.cos(pitch) * math.cos(yaw),
        center.z + dist * math.sin(pitch),
    ))
    cam_data = bpy.data.cameras.new("PreviewCam")
    cam_data.lens = 62
    cam = bpy.data.objects.new("PreviewCam", cam_data)
    cam.location = cam_loc
    direction = center - cam_loc
    cam.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
    bpy.context.scene.collection.objects.link(cam)
    scene.camera = cam

    lights = _sun_rig("Pv_", center, _PREVIEW_SUNS)

    bpy.ops.render.render(write_still=True)

    for obj in [cam] + lights:
        bpy.data.objects.remove(obj, do_unlink=True)
    return path


def render_multiview(path, size=420, angles=(8.0, 52.0, 96.0), elevation=22.0,
                     bg=(0.09, 0.10, 0.13)):
    """
    Render several yaw angles of the current scene side by side in one image.
    Catching a feature that sank into the body needs more than one viewpoint,
    and one wide render is far cheaper than N separate ones.
    """
    meshes = scene_meshes()
    if not meshes:
        return None
    lo, hi = bounds(meshes)
    center = (lo + hi) * 0.5
    radius = max((hi - lo).length * 0.5, 0.35)

    holder = empty("MV_holder")
    originals = [o for o in bpy.context.scene.objects if o.parent is None and o is not holder]
    spacing = radius * 2.45
    clones = []

    for i, yaw in enumerate(angles):
        offset = Vector(((i - (len(angles) - 1) / 2.0) * spacing, 0, 0))
        pivot = empty("MV_pivot_%d" % i, loc=center + offset)
        pivot.rotation_euler = (0, 0, yaw * D2R)
        clones.append(pivot)
        for src in originals:
            copy = src.copy()
            if src.data is not None:
                copy.data = src.data
            copy.name = "MV_%d_%s" % (i, src.name)
            bpy.context.scene.collection.objects.link(copy)
            copy.parent = pivot
            copy.matrix_parent_inverse = (
                bpy.data.objects[pivot.name].matrix_world.inverted()
            )
            copy.location = src.location - center
            clones.append(copy)
            for child in src.children_recursive:
                cc = child.copy()
                if child.data is not None:
                    cc.data = child.data
                cc.name = "MV_%d_%s" % (i, child.name)
                bpy.context.scene.collection.objects.link(cc)
                cc.parent = pivot
                cc.matrix_world = child.matrix_world.copy()
                cc.location = child.matrix_world.translation - center
                clones.append(cc)

    for src in originals:
        src.hide_render = True
        for child in src.children_recursive:
            child.hide_render = True

    width = int(size * len(angles) * 0.92)
    result = _render_span(path, center, radius, spacing, len(angles), width, size,
                          elevation, bg)

    for src in originals:
        src.hide_render = False
        for child in src.children_recursive:
            child.hide_render = False
    for obj in clones + [holder]:
        try:
            bpy.data.objects.remove(obj, do_unlink=True)
        except (ReferenceError, RuntimeError):
            pass
    return result


def _render_span(path, center, radius, spacing, count, width, height, elevation, bg):
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    scene = bpy.context.scene
    _pick_eevee()
    scene.render.resolution_x = width
    scene.render.resolution_y = height
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = False
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = path

    world = bpy.data.worlds.get("PreviewWorld") or bpy.data.worlds.new("PreviewWorld")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs[0].default_value = (bg[0], bg[1], bg[2], 1.0)
    world.node_tree.nodes["Background"].inputs[1].default_value = 0.32
    scene.world = world

    total_width = spacing * count
    cam_data = bpy.data.cameras.new("MVCam")
    cam_data.type = "ORTHO"
    cam_data.ortho_scale = total_width * 1.02
    cam = bpy.data.objects.new("MVCam", cam_data)
    pitch = elevation * D2R
    dist = radius * 8.0
    cam.location = Vector((center.x, center.y + dist * math.cos(pitch),
                           center.z + dist * math.sin(pitch)))
    cam.rotation_euler = (Vector((0, -math.cos(pitch), -math.sin(pitch)))
                          .to_track_quat("-Z", "Y").to_euler())
    bpy.context.scene.collection.objects.link(cam)
    scene.camera = cam

    lights = _sun_rig("MV_", center, _PREVIEW_SUNS)

    bpy.ops.render.render(write_still=True)
    for obj in [cam] + lights:
        bpy.data.objects.remove(obj, do_unlink=True)
    return path
