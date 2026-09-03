"""
Exercises petkit's anatomy helpers on three very different body plans so a
regression in any one helper shows up as a broken silhouette in the contact
sheet rather than in the middle of a hundred-model build.

    blender --background --python tools/blender/petkit_test.py -- <outdir>
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "lib"))

import kit      # noqa: E402
import petkit   # noqa: E402


def out_dir():
    argv = sys.argv
    if "--" in argv:
        tail = argv[argv.index("--") + 1:]
        if tail:
            return tail[0]
    return os.path.join(os.getcwd(), "public", "models", "_smoke")


def bird():
    """Chick -- tests eyes-on-surface, beak, feather wings, blush."""
    kit.reset_scene()
    root = kit.empty("root")
    down = kit.mat("chick.down", kit.hexcol("#ffd447"))
    foot_mat = kit.mat("chick.foot", kit.hexcol("#ff9c2e"))

    body = kit.sphere("body.core", r=0.5, scale=(1.0, 0.9, 0.84), material=down)
    kit.smooth(body)
    body_parts = [body] + petkit.belly("body.belly", (0, 0, -0.04), 0.42,
                                       color="#fff0c0", scale=(0.8, 0.5, 0.8))

    head_c = (0, 0.04, 0.62)
    skull = kit.sphere("head.skull", r=0.37, loc=head_c, scale=(1, 0.97, 0.95),
                       material=down)
    kit.smooth(skull)
    head_parts = [skull]
    head_parts += petkit.eyes("head.eye", head_c, 0.36, yaw=30, pitch=6,
                              size=0.115, style="round", bulge=0.62)
    head_parts += petkit.beak("head.beak", head_c, 0.36, length=0.24, width=0.115,
                              pitch=-6, color="#ff9c2e")
    head_parts += petkit.blush("head.blush", head_c, 0.36, yaw=54, pitch=-12,
                               size=0.1)
    tuft = kit.sphere("head.tuft", r=0.085, loc=(0, -0.04, 1.0),
                      scale=(0.85, 0.85, 1.6), material=down)
    kit.smooth(tuft)
    head_parts.append(tuft)

    wing_l, wing_r = petkit.wing_feather("wing", (0.42, 0.0, 0.14), span=0.34,
                                         height=0.34, color="#ffe57a", layers=3)

    legs = {}
    for side, sx in (("L", 1), ("R", -1)):
        shin = kit.cyl("leg.%s.shin" % side, r=0.035, h=0.16,
                       loc=(sx * 0.16, 0.02, -0.46), material=foot_mat, verts=6)
        toes = kit.box("leg.%s.foot" % side, dims=(0.15, 0.24, 0.055),
                       loc=(sx * 0.16, 0.08, -0.55), material=foot_mat)
        kit.bevel(toes, 0.018, 2)
        legs["leg.F%s" % side] = (
            [shin, toes], (sx * 0.16, 0.02, -0.42),
        )

    groups = {
        "body": (body_parts, (0, 0, 0)),
        "head": (head_parts, (0, 0, 0.4)),
        "wing.L": ([wing_l], tuple(wing_l.location)),
        "wing.R": ([wing_r], tuple(wing_r.location)),
    }
    groups.update(legs)
    petkit.assemble(root, groups)
    kit.normalize_height(root, 1.0)
    return root


def quadruped():
    """Fox -- tests pointed ears, snout, quad legs, puff tail, whiskers."""
    kit.reset_scene()
    root = kit.empty("root")
    fur = kit.mat("fox.fur", kit.hexcol("#e2703a"))
    cream = kit.mat("fox.cream", kit.hexcol("#fdf0dd"))

    body = kit.sphere("body.core", r=0.42, loc=(0, -0.02, 0.0),
                      scale=(0.92, 1.25, 0.9), material=fur)
    kit.smooth(body)
    body_parts = [body] + petkit.belly("body.belly", (0, -0.02, -0.1), 0.36,
                                       color="#fdf0dd", scale=(0.82, 1.1, 0.6),
                                       forward=0.0)

    head_c = (0, 0.42, 0.34)
    skull = kit.sphere("head.skull", r=0.33, loc=head_c, scale=(1, 1.02, 0.96),
                       material=fur)
    kit.smooth(skull)
    head_parts = [skull]
    head_parts += petkit.snout("head.snout", head_c, 0.32, length=0.3, width=0.19,
                               height=0.17, pitch=-12, color="#fdf0dd",
                               nose_color="#2e2226")
    head_parts += petkit.eyes("head.eye", head_c, 0.32, yaw=32, pitch=12,
                              size=0.095, style="round", bulge=0.5)
    head_parts += petkit.whiskers("head.whisker", head_c, 0.33, yaw=40, pitch=-8,
                                  count=3, length=0.2)
    ear_l, ear_r = petkit.ear_pointed("ear", head_c, 0.32, yaw=34, pitch=62,
                                      length=0.34, width=0.14,
                                      color="#e2703a", inner_color="#ffd0b8")

    legs = petkit.legs_quad("leg", front=(0.2, 0.28, -0.22), back=(0.22, -0.3, -0.22),
                            length=0.3, thickness=0.075, color="#c95a28",
                            paw_color="#3a2b30")
    brush = petkit.tail("tail", (0, -0.5, 0.06), length=0.5, thickness=0.09,
                        color="#e2703a", style="puff", tip_color="#fdf0dd",
                        segments=4, curl=0.5)

    groups = {
        "body": (body_parts, (0, 0, 0)),
        "head": (head_parts, (0, 0.24, 0.24)),
        "ear.L": ([ear_l], tuple(ear_l.location)),
        "ear.R": ([ear_r], tuple(ear_r.location)),
        "tail": ([brush], (0, -0.5, 0.06)),
    }
    for key, obj in legs.items():
        groups[key] = ([obj], tuple(obj.location))
    petkit.assemble(root, groups)
    _ = cream
    kit.normalize_height(root, 1.0)
    return root


def dragon():
    """Tests horns, membrane wings, crest, fangs, gems, segmented tail."""
    kit.reset_scene()
    root = kit.empty("root")
    scale_mat = kit.mat("drg.scale", kit.hexcol("#4bd07a"))

    body = kit.sphere("body.core", r=0.44, scale=(0.95, 1.1, 0.95),
                      material=scale_mat)
    kit.smooth(body)
    body_parts = [body]
    body_parts += petkit.belly("body.belly", (0, 0, -0.05), 0.38,
                               color="#ffe9a8", scale=(0.78, 0.95, 0.7))

    head_c = (0, 0.34, 0.52)
    skull = kit.sphere("head.skull", r=0.34, loc=head_c, scale=(1, 1.08, 0.94),
                       material=scale_mat)
    kit.smooth(skull)
    head_parts = [skull]
    head_parts += petkit.snout("head.snout", head_c, 0.33, length=0.26, width=0.22,
                               height=0.18, pitch=-14, color="#4bd07a",
                               nose_color="#2c6b42")
    head_parts += petkit.eyes("head.eye", head_c, 0.33, yaw=34, pitch=14,
                              size=0.1, style="pie", iris="#ffd23f", bulge=0.55)
    head_parts += petkit.fangs("head.fang", head_c, 0.33, count=2, size=0.045,
                               pitch=-24, spread=13)
    head_parts += petkit.horn("head.horn", head_c, 0.33, yaw=26, pitch=58,
                              length=0.26, width=0.07, color="#f5e6c0", curve=0.06)
    head_parts += petkit.crest("head.crest", head_c, 0.33, count=4, height=0.1,
                               width=0.05, pitch_from=52, pitch_to=90,
                               color="#ffb03a")

    wing_l, wing_r = petkit.wing_membrane("wing", (0.34, -0.06, 0.28), span=0.52,
                                          height=0.46, color="#2f9c5c",
                                          bone_color="#1d6b3d", fingers=3)
    spine = petkit.crest("body.spine", (0, -0.1, 0.0), 0.44, count=4, height=0.09,
                         width=0.045, pitch_from=40, pitch_to=86, color="#ffb03a")
    body_parts += spine
    body_parts += petkit.gem("body.gem", (0, 0.4, 0.06), size=0.075, color="#ffd23f")

    legs = petkit.legs_quad("leg", front=(0.22, 0.2, -0.26), back=(0.24, -0.24, -0.26),
                            length=0.26, thickness=0.085, color="#3fb56a",
                            paw_color="#f5e6c0")
    tail_obj = petkit.tail("tail", (0, -0.46, 0.0), length=0.5, thickness=0.085,
                           color="#4bd07a", style="segmented", segments=5,
                           tip_color="#ffb03a", curl=0.35)

    groups = {
        "body": (body_parts, (0, 0, 0)),
        "head": (head_parts, (0, 0.2, 0.36)),
        "wing.L": ([wing_l], tuple(wing_l.location)),
        "wing.R": ([wing_r], tuple(wing_r.location)),
        "tail": ([tail_obj], (0, -0.46, 0.0)),
    }
    for key, obj in legs.items():
        groups[key] = ([obj], tuple(obj.location))
    petkit.assemble(root, groups)
    kit.normalize_height(root, 1.0)
    return root


def main():
    target = out_dir()
    builders = (("pk_bird", bird), ("pk_quad", quadruped), ("pk_dragon", dragon))
    failed = []
    for name, builder in builders:
        try:
            root = builder()
            kit.export_glb(os.path.join(target, name + ".glb"), root)
            kit.report(name, name + ".glb")
            kit.render_multiview(os.path.join(target, name + ".png"), size=400)
        except Exception as exc:  # noqa: BLE001
            import traceback
            traceback.print_exc()
            failed.append("%s: %s" % (name, exc))
    if failed:
        print("PETKIT FAILED: " + " | ".join(failed), file=sys.stderr)
        sys.exit(1)
    print("PETKIT OK", file=sys.stderr)


if __name__ == "__main__":
    main()
