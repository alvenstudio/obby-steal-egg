"""
Smoke test for the modelling kit. Builds one small pet plus one egg and writes
them to the scratch output dir, so pipeline breakage surfaces in seconds rather
than after a hundred models.

    blender --background --python tools/blender/smoke_test.py -- <outdir>
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "lib"))

import kit  # noqa: E402


def out_dir():
    argv = sys.argv
    if "--" in argv:
        tail = argv[argv.index("--") + 1:]
        if tail:
            return tail[0]
    return os.path.join(os.getcwd(), "public", "models", "_smoke")


def build_chick():
    kit.reset_scene()

    yellow = kit.mat("chick.body", kit.hexcol("#ffd94a"))
    beak = kit.mat("chick.beak", kit.hexcol("#ff9c2e"))
    dark = kit.mat("eye.dark", kit.hexcol("#241c14"), rough=0.35)
    white = kit.mat("eye.white", kit.hexcol("#ffffff"), rough=0.3)

    root = kit.empty("root")

    body = kit.sphere("body", r=0.5, scale=(1.0, 0.92, 0.86), material=yellow)
    kit.smooth(body)

    skull = kit.sphere("head.skull", r=0.36, loc=(0, 0.06, 0.55),
                       scale=(1.0, 0.96, 0.94), material=yellow)
    kit.smooth(skull)
    bill = kit.cone("head.bill", r1=0.13, r2=0.0, h=0.22, loc=(0, 0.36, 0.5),
                    rot=(-90, 0, 0), material=beak)
    kit.flat(bill)
    tuft = kit.sphere("head.tuft", r=0.09, loc=(0, -0.02, 0.9),
                      scale=(0.8, 0.8, 1.5), material=yellow)
    kit.smooth(tuft)

    eye_white_l = kit.sphere("head.eyew", r=0.1, loc=(0.16, 0.28, 0.6),
                             scale=(1, 0.6, 1), material=white)
    eye_dark_l = kit.sphere("head.eyed", r=0.055, loc=(0.175, 0.335, 0.6),
                            material=dark)
    kit.smooth(eye_white_l)
    kit.smooth(eye_dark_l)
    eye_l = kit.join([eye_white_l, eye_dark_l], "head.eye.L")
    eye_r = kit.duplicate(eye_l, "head.eye.R", mirror=True)
    eye_r.location = eye_l.location.copy()

    head = kit.group("head", [skull, bill, tuft, eye_l, eye_r], pivot=(0, 0, 0.38))
    kit.parent_to(head, root)

    wing = kit.sphere("wing", r=0.2, loc=(0.44, 0.0, 0.1),
                      scale=(0.34, 1.0, 0.9), material=yellow)
    kit.smooth(wing)
    wing_l, wing_r = kit.mirrored_pair(wing, "wing")
    kit.set_origin_to(wing_l, (0.36, 0.0, 0.2))
    kit.set_origin_to(wing_r, (-0.36, 0.0, 0.2))
    kit.parent_to(wing_l, root)
    kit.parent_to(wing_r, root)

    foot = kit.box("foot", dims=(0.14, 0.26, 0.06), loc=(0.17, 0.06, -0.46),
                   material=beak)
    kit.bevel(foot, 0.02, 2)
    foot_l, foot_r = kit.mirrored_pair(foot, "leg.F")
    kit.parent_to(foot_l, root)
    kit.parent_to(foot_r, root)

    kit.parent_to(body, root)

    kit.normalize_height(root, 1.0)
    return root


def build_egg():
    kit.reset_scene()
    shell = kit.mat("egg.shell", kit.hexcol("#fff3d6"))
    spot = kit.mat("egg.spot", kit.hexcol("#8fd67a"))

    root = kit.empty("root")
    body = kit.teardrop("body", r=0.42, stretch=1.5, tip=0.62, material=shell)
    kit.smooth(body)

    speckles = []
    positions = [
        (0.24, 0.18, 0.16), (-0.2, 0.26, 0.34), (0.1, -0.3, 0.02),
        (-0.3, -0.1, -0.1), (0.05, 0.3, -0.18),
    ]
    for i, pos in enumerate(positions):
        dot = kit.sphere("egg.spot.%d" % i, r=0.09, loc=pos,
                         scale=(1, 1, 0.5), material=spot, segments=10, rings=6)
        kit.smooth(dot)
        speckles.append(dot)

    egg = kit.join([body] + speckles, "body")
    kit.parent_to(egg, root)
    kit.normalize_height(root, 1.0)
    return root


def main():
    target = out_dir()
    failures = []

    for name, builder in (("chick", build_chick), ("egg", build_egg)):
        try:
            root = builder()
            path = os.path.join(target, name + ".glb")
            kit.export_glb(path, root)
            kit.report(name, path)
        except Exception as exc:  # noqa: BLE001 - we want the whole list
            import traceback
            traceback.print_exc()
            failures.append("%s: %s" % (name, exc))

    if failures:
        print("SMOKE FAILED: " + "; ".join(failures), file=sys.stderr)
        sys.exit(1)
    print("SMOKE OK", file=sys.stderr)


if __name__ == "__main__":
    main()
