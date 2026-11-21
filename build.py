#!/usr/bin/env python3
"""Builds the Sweet GTK and GNOME Shell theme from its SCSS and SVG.

    build.py [css]        compile every stylesheet below (needs dart-sass: `sass`)
    build.py assets       render the check and radio images from src/assets.svg
                          (needs inkscape; optipng, if installed, shrinks them)
    build.py check        fail if a committed .css differs from what its .scss compiles
                          to, or if an image a stylesheet names is missing or unnamed
    build.py watch        recompile whenever a .scss changes (Ctrl+C to stop)
    build.py install [DIR]
                          copy the theme to DIR/Sweet (default ~/.local/share/themes)

The .css and .png files are committed, so installing the theme needs nothing but a copy;
rebuild them after editing a .scss or src/assets.svg.

src/assets.svg draws each image in an Inkscape layer labelled "Baseplate", over a rect
whose area is exported, with a text labelled "icon-name" giving the file name. `assets`
renders those the stylesheets name, as assets/NAME.png (scale 1) and assets/NAME@2.png
(scale 2). The other images (window buttons, switches) are drawn by hand.

Stylesheets, each from the .scss of the same name:

    gtk-3.0/gtk.css, gtk-3.0/gtk-dark.css
    gtk-4.0/gtk.css, gtk-4.0/gtk-dark.css
    gnome-shell/gnome-shell.css

Only dart-sass compiles the SCSS as written: libsass (sassc) extends selectors differently
and adds about 1,700 wrong selectors to each GTK stylesheet. dart-sass 1.79 and later write
computed colors with fractional channels, as rgb(12.4%, 13.9%, 20.6%); they are rounded
back to the 8-bit hex and rgba() that older versions wrote, which GTK and St read alike.
"""

import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import xml.etree.ElementTree as ET

ROOT = os.path.dirname(os.path.abspath(__file__))
NAME = "Sweet"

STYLESHEETS = [
    "gtk-3.0/gtk",
    "gtk-3.0/gtk-dark",
    "gtk-4.0/gtk",
    "gtk-4.0/gtk-dark",
    "gnome-shell/gnome-shell",
]

ASSETS_SVG = "src/assets.svg"
# Folders of images the stylesheets use; `check` wants every file in them named by one.
IMAGE_DIRS = ["assets", "gnome-shell/assets"]

# What an installed theme is made of, relative to ROOT.
INSTALL = [
    "index.theme",
    "assets",
    "gtk-3.0/gtk.css",
    "gtk-3.0/gtk-dark.css",
    "gtk-4.0/gtk.css",
    "gtk-4.0/gtk-dark.css",
    "gnome-shell/gnome-shell.css",
    "gnome-shell/assets",
]

# Deprecations the SCSS is known to use (@import, global color functions, ...). They become
# errors in Dart Sass 3; until the SCSS moves to modules they are only noise. Anything else
# sass reports still shows.
KNOWN_DEPRECATIONS = [
    "import",
    "global-builtin",
    "color-functions",
    "if-function",
    "strict-unary",
    "slash-div",
]


def die(message):
    sys.exit(f"error: {message}")


def sass():
    exe = shutil.which("sass")
    if not exe:
        die("needs dart-sass (`sass`); on Arch Linux: pacman -S dart-sass")
    version = subprocess.run([exe, "--version"], capture_output=True, text=True).stdout
    if not re.match(r"1\.\d+", version):
        die(f"`sass` is not dart-sass 1.x (it says {version.strip()!r})")
    return exe


NUMBER = r"(-?\d+(?:\.\d+)?(?:e-?\d+)?)"
PERCENT_RGB = re.compile(
    rf"rgba?\(\s*{NUMBER}%\s*,\s*{NUMBER}%\s*,\s*{NUMBER}%\s*(?:,\s*{NUMBER}\s*)?\)"
)


def channel(percent):
    return max(0, min(255, int(float(percent) * 255 / 100 + 0.5)))


def round_color(match):
    r, g, b = (channel(match.group(i)) for i in (1, 2, 3))
    alpha = match.group(4)
    if alpha is None or float(alpha) == 1:
        return f"#{r:02x}{g:02x}{b:02x}"
    return f"rgba({r}, {g}, {b}, {alpha})"


def compile_one(exe, name):
    """The CSS for NAME.scss, as text."""
    command = [exe, "--no-source-map", "--style=expanded"]
    command += [f"--silence-deprecation={d}" for d in KNOWN_DEPRECATIONS]
    command.append(os.path.join(ROOT, name + ".scss"))
    result = subprocess.run(command, capture_output=True, text=True)
    if result.stderr:
        sys.stderr.write(result.stderr)
    if result.returncode:
        die(f"{name}.scss does not compile")
    css = PERCENT_RGB.sub(round_color, result.stdout)
    header = f"/* Generated from {os.path.basename(name)}.scss by build.py: edit that and rebuild. */\n"
    return header + css


def build(exe, names=STYLESHEETS):
    for name in names:
        css = compile_one(exe, name)
        path = os.path.join(ROOT, name + ".css")
        old = open(path).read() if os.path.exists(path) else None
        if css != old:
            with open(path, "w") as f:
                f.write(css)
            print(f"{name}.css")


def check(exe):
    stale = [n for n in STYLESHEETS if compile_one(exe, n) != open(os.path.join(ROOT, n + ".css")).read()]
    if stale:
        die("out of date, run build.py: " + ", ".join(n + ".css" for n in stale))
    check_images()
    print("all stylesheets are up to date, and every image they name is there")


def referenced_images():
    """Every local file a stylesheet's url() names, relative to ROOT."""
    images = set()
    for name in STYLESHEETS:
        path = os.path.join(ROOT, name + ".css")
        for url in re.findall(r"url\(\s*[\"']?([^\"')]+)[\"']?\s*\)", open(path).read()):
            if ":" not in url:  # resource:// and the like are the shell's own
                images.add(os.path.normpath(os.path.join(os.path.dirname(name), url)))
    return images


def check_images():
    named = referenced_images()
    missing = sorted(p for p in named if not os.path.exists(os.path.join(ROOT, p)))
    unnamed = sorted(
        os.path.join(d, f)
        for d in IMAGE_DIRS
        for f in os.listdir(os.path.join(ROOT, d))
        if os.path.join(d, f) not in named
    )
    if missing:
        die("named by a stylesheet but missing: " + ", ".join(missing))
    if unnamed:
        die("in the theme but named by no stylesheet: " + ", ".join(unnamed))


INKSCAPE = "{http://www.inkscape.org/namespaces/inkscape}"
SVG = "{http://www.w3.org/2000/svg}"


def baseplates():
    """{image name: id of the rect to export} from ASSETS_SVG."""
    plates = {}
    root = ET.parse(os.path.join(ROOT, ASSETS_SVG)).getroot()
    for layer in root.iter(SVG + "g"):
        if layer.get(INKSCAPE + "groupmode") != "layer":
            continue
        if not (layer.get(INKSCAPE + "label") or "").startswith("Baseplate"):
            continue
        names = ["".join(t.itertext()).strip() for t in layer.iter(SVG + "text") if t.get(INKSCAPE + "label") == "icon-name"]
        rects = [r.get("id") for r in layer.iter(SVG + "rect")]
        if len(names) != 1 or len(rects) != 1:
            die(f"{ASSETS_SVG}: a baseplate needs one icon-name text and one rect, has {names} and {rects}")
        if names[0] in plates:
            die(f"{ASSETS_SVG}: two baseplates are named {names[0]}")
        plates[names[0]] = rects[0]
    return plates


def render_assets():
    inkscape = shutil.which("inkscape")
    if not inkscape:
        die("needs inkscape")
    plates = baseplates()
    wanted = set()
    for p in referenced_images():
        m = re.fullmatch(r"assets/(.+?)(@2)?\.png", p)
        if m and m.group(1) in plates:
            wanted.add(m.group(1))
    with tempfile.TemporaryDirectory() as tmp:
        actions = []
        for name in sorted(wanted):
            for suffix, dpi in (("", 96), ("@2", 192)):
                out = os.path.join(tmp, f"{name}{suffix}.png")
                actions.append(f"export-id:{plates[name]};export-dpi:{dpi};export-filename:{out};export-do")
        result = subprocess.run(
            [inkscape, "--actions=" + ";".join(actions), os.path.join(ROOT, ASSETS_SVG)],
            capture_output=True, text=True,
        )
        made = sorted(os.listdir(tmp))
        if result.returncode or len(made) != 2 * len(wanted):
            sys.stderr.write(result.stderr)
            die(f"inkscape made {len(made)} of {2 * len(wanted)} images")
        optipng = shutil.which("optipng")
        if optipng:
            subprocess.run([optipng, "-quiet", "-o7", "-strip", "all"] + [os.path.join(tmp, f) for f in made], check=True)
        for f in made:
            shutil.move(os.path.join(tmp, f), os.path.join(ROOT, "assets", f))
    print(f"rendered {len(made)} images to assets/")


def scss_mtimes():
    times = {}
    for top in ("gtk-3.0", "gtk-4.0", "gnome-shell"):
        for dirpath, _, files in os.walk(os.path.join(ROOT, top)):
            for f in files:
                if f.endswith(".scss"):
                    path = os.path.join(dirpath, f)
                    times[path] = os.stat(path).st_mtime
    return times


def watch(exe):
    # gtk-4.0 imports gtk-3.0's colors, so any change rebuilds everything (half a second).
    print("watching the .scss files, Ctrl+C to stop", flush=True)
    seen = None
    try:
        while True:
            now = scss_mtimes()
            if now == seen:
                time.sleep(0.5)
            else:
                seen = now
                try:
                    build(exe)
                    print(time.strftime("%H:%M:%S rebuilt"), flush=True)
                except SystemExit as e:
                    print(e, file=sys.stderr, flush=True)
    except KeyboardInterrupt:
        pass


def install(dest):
    target = os.path.join(dest, NAME)
    missing = [p for p in INSTALL if not os.path.exists(os.path.join(ROOT, p))]
    if missing:
        die("missing, run build.py first: " + ", ".join(missing))
    # Build the copy beside the target, then swap it in, so a failed copy leaves the old theme.
    os.makedirs(dest, exist_ok=True)
    staging = tempfile.mkdtemp(prefix=f".{NAME}-", dir=dest)
    for p in INSTALL:
        src, dst = os.path.join(ROOT, p), os.path.join(staging, p)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        if os.path.isdir(src):
            shutil.copytree(src, dst)
        else:
            shutil.copy2(src, dst)
    os.chmod(staging, 0o755)
    if os.path.exists(target):
        shutil.rmtree(target)
    os.rename(staging, target)
    print(f"installed to {target}")


def main(argv):
    command = argv[0] if argv else "css"
    if command == "css" and len(argv) <= 1:
        build(sass())
    elif command == "assets" and len(argv) == 1:
        render_assets()
    elif command == "check" and len(argv) == 1:
        check(sass())
    elif command == "watch" and len(argv) == 1:
        watch(sass())
    elif command == "install" and len(argv) <= 2:
        default = os.path.join(os.environ.get("XDG_DATA_HOME") or os.path.expanduser("~/.local/share"), "themes")
        install(argv[1] if len(argv) == 2 else default)
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
