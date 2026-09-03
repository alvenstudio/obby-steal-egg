"""
Model build launcher.

Finds Blender and runs tools/blender/build.py inside it. Kept separate from the
build script itself so `npm run models` works without anyone having to know
where Blender lives or how to pass `--background --python`.

    python tools/build_models.py                      # everything
    python tools/build_models.py --biome volcano      # one biome
    python tools/build_models.py --only fox,bear      # specific pets
    python tools/build_models.py --sheet              # + a contact sheet
    python tools/build_models.py --previews           # + one preview per pet
    python tools/build_models.py --clean              # wipe outputs first

Set BLENDER to override the executable that gets used.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILD_SCRIPT = os.path.join(ROOT, "tools", "blender", "build.py")

# Ordered by how likely each is to be the one the user actually has.
CANDIDATES = [
    os.environ.get("BLENDER"),
    "blender",
    r"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe",
    r"C:\Program Files\Blender Foundation\Blender 4.5\blender.exe",
    r"C:\Program Files\Blender Foundation\Blender 4.2\blender.exe",
    r"D:\blender.exe",
    "/Applications/Blender.app/Contents/MacOS/Blender",
    "/usr/bin/blender",
    "/usr/local/bin/blender",
    "/snap/bin/blender",
]


def find_blender() -> str | None:
    for candidate in CANDIDATES:
        if not candidate:
            continue
        if os.path.isfile(candidate):
            return candidate
        found = shutil.which(candidate)
        if found:
            return found
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the game's .glb models.")
    parser.add_argument("--biome", help="build only this biome's pets")
    parser.add_argument("--only", help="comma-separated pet ids")
    parser.add_argument("--sheet", action="store_true",
                        help="render a contact sheet of everything built")
    parser.add_argument("--previews", action="store_true",
                        help="render a multi-angle preview per model")
    parser.add_argument("--props-only", action="store_true",
                        help="build eggs and props, skip the pets")
    parser.add_argument("--skip-export", action="store_true",
                        help="build and preview without writing .glb files")
    parser.add_argument("--clean", action="store_true",
                        help="delete generated models before building")
    parser.add_argument("--out", default=os.path.join(ROOT, "public", "models"))
    args = parser.parse_args()

    blender = find_blender()
    if not blender:
        print(
            "Could not find Blender.\n"
            "Install Blender 4.x or 5.x, then either put it on your PATH or set\n"
            "  BLENDER=/path/to/blender\n"
            "The game itself does not need Blender -- the committed .glb files\n"
            "are enough to play. This is only needed to regenerate the art.",
            file=sys.stderr,
        )
        return 1

    if args.clean and os.path.isdir(args.out):
        print("cleaning %s" % args.out)
        shutil.rmtree(args.out)

    passthrough: list[str] = ["--out", args.out]
    if args.biome:
        passthrough += ["--biome", args.biome]
    if args.only:
        passthrough += ["--only", args.only]
    if args.props_only:
        passthrough.append("--props-only")
    if args.skip_export:
        passthrough.append("--skip-export")
    if args.sheet:
        label = args.biome or ("selection" if args.only else "all")
        passthrough += ["--sheet", os.path.join(ROOT, "build", "sheet-%s.png" % label)]
    if args.previews:
        passthrough += ["--previews", os.path.join(ROOT, "build", "previews")]

    command = [blender, "--background", "--python", BUILD_SCRIPT, "--"] + passthrough
    print("using %s" % blender)

    # Blender is extremely chatty on stdout; the build's own reporting goes to
    # stderr, so surface that and drop the rest unless something fails.
    process = subprocess.run(
        command, cwd=ROOT, stdout=subprocess.PIPE, stderr=None, text=True,
    )
    if process.returncode != 0:
        sys.stdout.write(process.stdout or "")
        print("\nmodel build FAILED (exit %d)" % process.returncode, file=sys.stderr)
    return process.returncode


if __name__ == "__main__":
    raise SystemExit(main())
