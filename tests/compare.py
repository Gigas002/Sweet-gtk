#!/usr/bin/env python3
"""Renders the theme at two revisions and compares the screenshots.

    tests/compare.py [--gtk | --shell] [--scale N] [--out DIR] OLD [NEW]

OLD and NEW are git revisions; NEW defaults to the working tree (as built: run build.py
first). Both are rendered in private headless sessions, so the desktop is never touched:

  --gtk    tests/gallery.py, a window of GTK 3 and GTK 4 widgets, in each of five states
           (normal, hover, active, disabled, backdrop), in headless sway
  --shell  GNOME Shell's main views (desktop with a notification, overview with two windows,
           search, app grid, an app menu, quick settings, calendar, a dialog with check boxes
           and an entry, the volume OSD, the window switcher, the screenshot UI, the lock screen
           and its password prompt), in
           headless GNOME Shell (as `gnome-shell --headless`, with a session mode that enables
           the screenshot extension in tests/shell-shot@sweet, which loads the theme on top of
           GNOME's own stylesheet as the User Themes extension does)

Without either, both run. It prints how many pixels differ in each screenshot and writes
OLD | NEW | difference images to DIR (default: a new temporary folder, printed at the end).
The panel clock differs between runs when a minute passes.

Needs: git, Python's PIL (python-pillow) and PyGObject, sway and grim for --gtk, GNOME Shell
for --shell. GTK runs with the cairo renderer, so no GPU is needed.
"""

import argparse
import os
import shlex
import shutil
import subprocess
import sys
import tempfile

from PIL import Image, ImageChops

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PARTS = ["index.theme", "assets", "gtk-3.0", "gtk-4.0", "gnome-shell"]
STATES = ["normal", "hover", "active", "disabled", "backdrop"]
SHELL_SHOTS = ["welcome", "desktop", "overview", "search", "apps", "app-menu", "quick-settings", "calendar",
               "dialog", "osd", "switcher", "screenshot-ui", "lock", "unlock-prompt"]


def theme_at(rev, dest):
    """Writes the theme at REV (None: the working tree) to DEST."""
    os.makedirs(dest)
    if rev is None:
        for p in PARTS:
            src = os.path.join(ROOT, p)
            (shutil.copytree if os.path.isdir(src) else shutil.copy2)(src, os.path.join(dest, p))
    else:
        archive = subprocess.run(["git", "-C", ROOT, "archive", rev, *PARTS], capture_output=True, check=True)
        subprocess.run(["tar", "-x", "-C", dest], input=archive.stdout, check=True)


def short_tempdir():
    # A Wayland socket path must fit in 108 bytes, so runtime dirs stay short.
    return tempfile.mkdtemp(prefix="sw-", dir="/tmp" if len(tempfile.gettempdir()) > 40 else None)


def clean_env(**extra):
    env = {k: v for k, v in os.environ.items()
           if k not in ("WAYLAND_DISPLAY", "DISPLAY", "SWAYSOCK", "HYPRLAND_INSTANCE_SIGNATURE",
                        "DBUS_SESSION_BUS_ADDRESS", "GTK_THEME")}
    env.update(extra)
    return env


def render_gtk(themes, out, scale):
    """themes: {label: theme dir}. Writes out/LABEL-gtkV-STATE.png."""
    data, config, runtime = tempfile.mkdtemp(), tempfile.mkdtemp(), short_tempdir()
    os.makedirs(os.path.join(data, "themes"))
    for label, path in themes.items():
        os.symlink(path, os.path.join(data, "themes", label))
    with open(os.path.join(config, "sway.conf"), "w") as f:
        f.write(f"output HEADLESS-1 resolution 1400x950 scale {scale} bg #000000 solid_color\n"
                "default_border none\nfor_window [title=\".*\"] fullscreen enable\nseat * hide_cursor 1\n")
    runs = []
    for label in themes:
        for v in (3, 4):
            for s in STATES:
                png = os.path.join(out, f"{label}-gtk{v}-{s}.png")
                runs.append(f"GTK_THEME={label} timeout 30 python3 {shlex.quote(os.path.join(HERE, 'gallery.py'))} "
                            f"{v} {s} {shlex.quote(png)} 2>/dev/null || echo 'gallery failed: {label} gtk{v} {s}'")
    script = (f"sway -c {shlex.quote(os.path.join(config, 'sway.conf'))} 2>/dev/null & SWAY=$!\n"
              "sleep 1.5\nexport WAYLAND_DISPLAY=wayland-1\n" + "\n".join(runs) + "\nkill $SWAY\n")
    env = clean_env(XDG_RUNTIME_DIR=runtime, XDG_DATA_HOME=data, XDG_CONFIG_HOME=config,
                    WLR_BACKENDS="headless", WLR_RENDERER="pixman", WLR_LIBINPUT_NO_DEVICES="1",
                    GSETTINGS_BACKEND="memory", GDK_BACKEND="wayland", GSK_RENDERER="cairo",
                    GDK_DEBUG="no-portals", GTK_A11Y="none", NO_AT_BRIDGE="1")
    subprocess.run(["dbus-run-session", "--", "sh", "-c", script], env=env, check=True, stderr=subprocess.DEVNULL)
    for d in (data, config, runtime):
        shutil.rmtree(d, ignore_errors=True)
    return [(f"gtk{v}-{s}", f"gtk{v}-{s}.png") for v in (3, 4) for s in STATES]


def render_shell(themes, out):
    """themes: {label: theme dir}. Writes out/LABEL-shell-SHOT.png."""
    for label, path in themes.items():
        data, home, runtime, shots = tempfile.mkdtemp(), tempfile.mkdtemp(), short_tempdir(), tempfile.mkdtemp()
        shell = os.path.join(data, "gnome-shell")
        os.makedirs(os.path.join(shell, "modes"))
        os.makedirs(os.path.join(shell, "extensions"))
        # A session mode that enables the screenshot extension; it loads the theme.
        with open(os.path.join(shell, "modes", "sweet-test.json"), "w") as f:
            f.write('{"parentMode": "user", "enabledExtensions": ["shell-shot@sweet"]}\n')
        shutil.copytree(os.path.join(HERE, "shell-shot@sweet"), os.path.join(shell, "extensions", "shell-shot@sweet"))
        env = clean_env(XDG_RUNTIME_DIR=runtime, HOME=home, XDG_CONFIG_HOME=os.path.join(home, ".config"),
                        XDG_DATA_HOME=os.path.join(home, ".local/share"), XDG_CACHE_HOME=os.path.join(home, ".cache"),
                        XDG_DATA_DIRS=data + ":" + os.environ.get("XDG_DATA_DIRS", "/usr/local/share:/usr/share"),
                        SWEET_SHOT_DIR=shots, SWEET_TESTS_DIR=HERE,
                        SWEET_THEME_CSS=os.path.join(path, "gnome-shell", "gnome-shell.css"), GSK_RENDERER="cairo")
        log = subprocess.run(["dbus-run-session", "--", "timeout", "90", "gnome-shell", "--headless", "--wayland",
                              "--no-x11", "--virtual-monitor", "1280x800", "--mode=sweet-test"],
                             env=env, capture_output=True, text=True)
        for line in log.stderr.splitlines():
            if "shell-shot" in line or "Stylesheet" in line or "stylesheet" in line:
                print(f"{label}: {line}", file=sys.stderr)
        for name in SHELL_SHOTS:
            if os.path.exists(os.path.join(shots, name + ".png")):
                shutil.move(os.path.join(shots, name + ".png"), os.path.join(out, f"{label}-shell-{name}.png"))
            else:
                print(f"{label}: no {name} screenshot", file=sys.stderr)
        for d in (data, home, runtime, shots):
            shutil.rmtree(d, ignore_errors=True)
    return [(f"shell-{n}", f"shell-{n}.png") for n in SHELL_SHOTS]


def compare(out, pairs):
    for name, suffix in pairs:
        a_path, b_path = os.path.join(out, "old-" + suffix), os.path.join(out, "new-" + suffix)
        if not (os.path.exists(a_path) and os.path.exists(b_path)):
            print(f"{name:20} missing")
            continue
        a, b = Image.open(a_path).convert("RGB"), Image.open(b_path).convert("RGB")
        if a.size != b.size:
            print(f"{name:20} sizes differ: {a.size} {b.size}")
            continue
        mask = ImageChops.difference(a, b).convert("L").point(lambda v: 255 if v > 3 else 0)
        count = mask.histogram()[255]
        print(f"{name:20} {count:8} px differ" + (f"  in {mask.getbbox()}" if count else ""))
        if count:
            marked = a.copy()
            marked.paste((255, 0, 0), mask=mask)
            sheet = Image.new("RGB", (a.width * 3 + 20, a.height), (255, 0, 0))
            for i, im in enumerate((a, b, marked)):
                sheet.paste(im, (i * (a.width + 10), 0))
            sheet.save(os.path.join(out, f"diff-{name}.png"))


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("old")
    p.add_argument("new", nargs="?")
    p.add_argument("--gtk", action="store_true")
    p.add_argument("--shell", action="store_true")
    p.add_argument("--scale", type=int, default=1, help="output scale for --gtk (2 shows the @2 images)")
    p.add_argument("--out")
    args = p.parse_args()
    if not (args.gtk or args.shell):
        args.gtk = args.shell = True
    out = os.path.abspath(args.out or tempfile.mkdtemp(prefix="sweet-compare-"))
    os.makedirs(out, exist_ok=True)
    work = tempfile.mkdtemp()
    themes = {"old": os.path.join(work, "old"), "new": os.path.join(work, "new")}
    theme_at(args.old, themes["old"])
    theme_at(args.new, themes["new"])
    pairs = []
    if args.gtk:
        pairs += render_gtk(themes, out, args.scale)
    if args.shell:
        pairs += render_shell(themes, out)
    shutil.rmtree(work, ignore_errors=True)
    compare(out, pairs)
    print(f"screenshots in {out}")


if __name__ == "__main__":
    main()
