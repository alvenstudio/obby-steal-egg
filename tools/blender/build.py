"""
Model build, run inside Blender.

    blender --background --python tools/blender/build.py -- [options]

Options:
    --out DIR        output root (default: public/models)
    --only a,b,c     build only these pet ids
    --biome forest   build only this biome's pets
    --sheet PATH     also render a contact sheet of everything built
    --previews DIR   render one multi-angle preview png per pet
    --skip-export    build and preview without writing .glb (fast visual check)

Every pet is built in its own clean scene, exported, and reported with its
triangle count, so a model that quietly balloons to 40k tris is visible in the
build log rather than in the frame budget.
"""

from __future__ import annotations

import importlib
import json
import math
import os
import sys
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(HERE, "lib"))
sys.path.insert(0, os.path.join(HERE, "generators"))
sys.path.insert(0, HERE)

import bpy  # noqa: E402
from mathutils import Vector  # noqa: E402

import kit  # noqa: E402

# Every generator module the build knows about. A biome missing from here is
# simply not built; the game falls back to a magenta placeholder and says so.
GENERATOR_MODULES = [
    "pets_forest",
    "pets_lake",
    "pets_desert",
    "pets_jungle",
    "pets_snow",
    "pets_volcano",
    "pets_abyss",
    "pets_prehistoric",
    "pets_cosmic",
    "pets_blossom",
    "pets_titan",
    "pets_event_a",
    "pets_event_b",
    "pets_event_a",
]

PROP_MODULES = ["props_eggs", "props_world", "props_guardians"]


def parse_args():
    argv = sys.argv
    args = argv[argv.index("--") + 1:] if "--" in argv else []
    out = {
        "out": os.path.join(ROOT, "public", "models"),
        "only": None,
        "biome": None,
        "sheet": None,
        "previews": None,
        "skip_export": False,
        "props": True,
        "props_only": False,
    }
    i = 0
    while i < len(args):
        token = args[i]
        if token == "--out":
            out["out"] = args[i + 1]; i += 2
        elif token == "--only":
            out["only"] = set(args[i + 1].split(",")); i += 2
        elif token == "--biome":
            out["biome"] = args[i + 1]; i += 2
        elif token == "--sheet":
            out["sheet"] = args[i + 1]; i += 2
        elif token == "--previews":
            out["previews"] = args[i + 1]; i += 2
        elif token == "--skip-export":
            out["skip_export"] = True; i += 1
        elif token == "--no-props":
            out["props"] = False; i += 1
        elif token == "--props-only":
            out["props_only"] = True; i += 1
        else:
            i += 1
    return out


def load_manifest():
    path = os.path.join(HERE, "pet_manifest.json")
    if not os.path.exists(path):
        return []
    return json.load(open(path, encoding="utf-8"))


def load_builders():
    """Import every generator module that exists; report the ones that do not."""
    builders = {}
    missing = []
    for name in GENERATOR_MODULES:
        try:
            module = importlib.import_module(name)
            importlib.reload(module)
            builders.update(getattr(module, "PETS", {}))
        except ImportError:
            missing.append(name)
        except Exception as exc:  # a broken generator must not kill the build
            print("[build] ERROR importing %s: %s" % (name, exc), file=sys.stderr)
            traceback.print_exc()
            missing.append(name)
    return builders, missing


def load_prop_builders():
    props = {}
    for name in PROP_MODULES:
        try:
            module = importlib.import_module(name)
            importlib.reload(module)
            props.update(getattr(module, "PROPS", {}))
        except ImportError:
            continue
        except Exception as exc:
            print("[build] ERROR importing %s: %s" % (name, exc), file=sys.stderr)
            traceback.print_exc()
    return props


def build_one(pet_id, builder, out_dir, skip_export, previews):
    root = builder()
    meshes = kit.scene_meshes()
    tris = kit.tri_count(meshes)
    lo, hi = kit.bounds(meshes)
    size = hi - lo

    path = os.path.join(out_dir, pet_id + ".glb")
    if not skip_export:
        kit.export_glb(path, root)
    if previews:
        kit.render_multiview(os.path.join(previews, pet_id + ".png"), size=320)

    parts = sorted(child.name for child in root.children)
    return {
        "id": pet_id,
        "tris": tris,
        "parts": parts,
        "size": [round(size.x, 3), round(size.y, 3), round(size.z, 3)],
        "path": path if not skip_export else None,
    }


# ---------------------------------------------------------------------------
# contact sheet
# ---------------------------------------------------------------------------


def render_sheet(entries, builders, path, columns=0, cell=300):
    """
    Build every pet into one scene on a grid and render it as a single image.

    Reviewing a hundred creatures one PNG at a time is impractical; one sheet
    makes an outlier -- wrong scale, missing head, black material -- obvious at
    a glance.

    `columns` defaults to whatever keeps the sheet roughly square. A fixed six
    columns turns the full 107-pet roster into a 1:3 ribbon that every image
    viewer downscales into uselessness, which defeats the entire point.

    Note that a full-roster sheet re-runs every generator and then renders a
    very large image; it is minutes of work, not seconds. Per-biome sheets are
    the ones to use while iterating.
    """
    kit.reset_scene()
    if columns <= 0:
        columns = max(4, int(math.ceil(math.sqrt(len(entries) * 1.6))))
    rows = (len(entries) + columns - 1) // columns
    spacing = 1.75
    spacing_y = 1.6

    for index, entry in enumerate(entries):
        builder = builders.get(entry["id"])
        if builder is None:
            continue
        # Each builder resets the scene, so build into a temp scene and copy the
        # resulting objects across with an offset.
        objects_before = set(bpy.context.scene.objects)
        try:
            root = builder()
        except Exception:
            traceback.print_exc()
            continue
        _ = objects_before
        col = index % columns
        row = index // columns
        root.location.x += (col - (columns - 1) / 2.0) * spacing
        # Rows stack along Z, not Y. The camera looks down -Y, so a Y offset
        # only pushes a row further away and it lands on top of the one in
        # front of it; Z is the only axis that separates rows on screen.
        root.location.z += ((rows - 1) / 2.0 - row) * spacing_y
        # Three-quarter view: dead-on front hides how long a quadruped is, and
        # length is most of what distinguishes these silhouettes.
        root.rotation_euler.z += math.radians(32)
        root.name = "sheet_%s" % entry["id"]
        bpy.context.view_layer.update()
        kit.protect(root)

    # Cap the long edge: past ~2600px the sheet gets downscaled for viewing
    # anyway, so extra pixels cost render time and buy nothing.
    scale = min(1.0, 2600.0 / max(cell * columns, cell * rows))
    width = int(cell * columns * scale)
    height = int(cell * rows * scale)
    _render_ortho_grid(path, columns, rows, spacing, spacing_y, rows, width, height)


def _render_ortho_grid(path, columns, rows, spacing, spacing_y, row_count, width, height):
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)

    scene = bpy.context.scene
    kit._pick_eevee()
    scene.render.resolution_x = width
    scene.render.resolution_y = height
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = path

    world = bpy.data.worlds.get("PreviewWorld") or bpy.data.worlds.new("PreviewWorld")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs[0].default_value = (0.09, 0.10, 0.13, 1)
    world.node_tree.nodes["Background"].inputs[1].default_value = 0.32
    scene.world = world

    span_x = columns * spacing
    span_y = row_count * spacing_y
    center = Vector((0, 0, 0.45))
    _ = spacing

    cam_data = bpy.data.cameras.new("SheetCam")
    cam_data.type = "ORTHO"
    # ortho_scale maps to the larger image axis, so the smaller axis has to be
    # converted through the aspect ratio or trailing rows fall out of frame.
    aspect = width / float(height)
    needed = max(span_x, span_y * aspect)
    cam_data.ortho_scale = needed * 1.04
    cam = bpy.data.objects.new("SheetCam", cam_data)
    pitch = math.radians(9)
    cam.location = Vector((center.x, center.y + 60 * math.cos(pitch),
                           center.z + 60 * math.sin(pitch)))
    cam.rotation_euler = (
        Vector((0, -math.cos(pitch), -math.sin(pitch)))
        .to_track_quat("-Z", "Y").to_euler()
    )
    bpy.context.scene.collection.objects.link(cam)
    scene.camera = cam

    for name in ("Standard", "Filmic"):
        try:
            scene.view_settings.view_transform = name
            break
        except TypeError:
            continue

    kit._sun_rig("Sheet_", center, kit._PREVIEW_SUNS)
    bpy.ops.render.render(write_still=True)


def main():
    options = parse_args()
    manifest = load_manifest()
    builders, missing_modules = load_builders()

    wanted = [] if options["props_only"] else manifest
    if options["biome"]:
        wanted = [p for p in wanted if p["biome"] == options["biome"]]
    if options["only"]:
        wanted = [p for p in wanted if p["id"] in options["only"]]

    pets_out = os.path.join(options["out"], "pets")
    os.makedirs(pets_out, exist_ok=True)
    previews = options["previews"]
    if previews:
        os.makedirs(previews, exist_ok=True)

    built, skipped, failed = [], [], []
    for entry in wanted:
        builder = builders.get(entry["id"])
        if builder is None:
            skipped.append(entry["id"])
            continue
        try:
            info = build_one(entry["id"], builder, pets_out,
                             options["skip_export"], previews)
            built.append(info)
            print("[build] %-26s tris=%-6d parts=%d" %
                  (info["id"], info["tris"], len(info["parts"])), file=sys.stderr)
        except Exception as exc:
            failed.append((entry["id"], str(exc)))
            traceback.print_exc()

    if options["props"] and (options["props_only"] or (not options["only"] and not options["biome"])):
        for prop_id, builder in load_prop_builders().items():
            try:
                root = builder()
                sub = os.path.join(options["out"], prop_id.split("/")[0]) \
                    if "/" in prop_id else options["out"]
                name = prop_id.split("/")[-1]
                os.makedirs(sub, exist_ok=True)
                if not options["skip_export"]:
                    kit.export_glb(os.path.join(sub, name + ".glb"), root)
                print("[build] prop %-22s tris=%d" %
                      (prop_id, kit.tri_count(kit.scene_meshes())), file=sys.stderr)
            except Exception:
                failed.append((prop_id, "prop build failed"))
                traceback.print_exc()

    if options["sheet"] and built:
        try:
            render_sheet(built, builders, options["sheet"])
        except Exception:
            traceback.print_exc()

    total_tris = sum(info["tris"] for info in built)
    print("", file=sys.stderr)
    print("[build] built=%d skipped=%d failed=%d total_tris=%d" %
          (len(built), len(skipped), len(failed), total_tris), file=sys.stderr)
    if missing_modules:
        print("[build] generator modules not present: %s" %
              ", ".join(missing_modules), file=sys.stderr)
    if skipped:
        print("[build] no builder for: %s" % ", ".join(sorted(skipped)[:40]),
              file=sys.stderr)
    if failed:
        print("[build] FAILURES:", file=sys.stderr)
        for pet_id, message in failed:
            print("   %s: %s" % (pet_id, message), file=sys.stderr)

    report_path = os.path.join(options["out"], "build-report.json")
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    json.dump(
        {
            "built": built,
            "skipped": sorted(skipped),
            "failed": [{"id": i, "error": e} for i, e in failed],
            "totalTris": total_tris,
        },
        open(report_path, "w", encoding="utf-8"),
        indent=1,
    )
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
