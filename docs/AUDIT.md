# Audit

A whole-repository audit of the Sweet GTK theme (2026-11-20 and 21) in five
parts:

- §2 scope: what the theme is for, and what was removed;
- §3 build;
- §4 GTK correctness and assets;
- §5 the GNOME Shell theme;
- §6 hygiene, tests and docs.

§7 lists what was left open, and §8 is the checklist to re-run the audit.

The fixes are the commits on `master` from fb33d1e on, on top of 75a5441
(`git log --reverse --stat 75a5441..master`). Each finding is one commit.

The repository went from 1,471 tracked files to 233, and its archive from
15.6 MB to 1.7 MB. Node, npm and Gulp are gone. The build is one Python
script that calls dart-sass and Inkscape.

Each finding says what was found, how serious it is, and what was done:

- **fixed**, with the commit;
- **removed**, for scope;
- **accepted**, with the reason;
- **OK**: checked, nothing to do.

Severity:

- **high**: wrong or missing drawing in normal use, or a build that can't run;
- **medium**: wrong in a reachable case;
- **low**: polish, or dead weight.

## 1. Method

The theme was rendered before and after every change, and the screenshots
were compared pixel by pixel. That check is now `tests/compare.py` (§8).

- **GTK 3 and GTK 4.** `tests/gallery.py` is a window of the common widgets:
  - buttons in every class, and linked groups;
  - entries, combos and spin buttons;
  - checks, radios and switches;
  - scales, progress and level bars;
  - a notebook and an info bar;
  - list, tree and text views;
  - a calendar and an expander;
  - headerbars, including one in selection mode;
  - a content view.

  It forces each of five states (normal, hover, active, disabled, backdrop) on
  every widget. It runs in a private headless sway 1.12 with the pixman
  renderer and GTK's cairo renderer, at scale 1, and at scale 2 for the images.
- **GNOME Shell 51.1.** It runs as `gnome-shell --headless` in its own D-Bus
  session. A small extension loads the theme the way the User Themes extension
  does, on top of GNOME's own stylesheet, and screenshots 14 views:
  - the desktop with a notification, the overview with two windows, search, the
    app grid and an app's menu;
  - quick settings and the calendar;
  - a dialog with check boxes, an entry and a default button;
  - the volume OSD, Alt+Tab and the screenshot UI;
  - the lock screen and its prompt. The shell builds these only when GDM runs,
    so the extension builds them itself.
- **Stylesheets.**
  - Every stylesheet went through GTK's own CSS parser (`Gtk.CssProvider`,
    GTK 3.24 and 4.24) and counted errors: 0 for both.
  - An effective-style diff compared old and new: per selector, the declarations
    that win, with colors equal within 1/255.
- **GNOME Shell versions.** Every class name in the shell stylesheet was looked
  up in the sources of GNOME Shell 46.0, 46.10, 47.10, 48.8, 49.10 and 50.6 (git
  tags), and in the strings of the installed 51.1 (JS is embedded in
  `libshell-51.so`).
- **Images.** Every `url()` in the built CSS was checked against the files, and
  every image file against the URLs. Renders of the SVG sources were compared
  with the committed PNGs, premultiplied, so that invisible transparent pixels
  don't count.

Tools: dart-sass 1.108.2, Inkscape 1.4, optipng, Python 3 with PIL and
PyGObject.

## 2. Scope

The theme is for GTK 3, GTK 4 and GNOME Shell 46 and later. Elementary apps
keep Pantheon's styles, and Geary and Rnote keep theirs.

| Area | Finding | Status |
| ---- | ------- | ------ |
| KDE | Plasma themes, Aurorae, Kvantum, color schemes, Konsole, SDDM and cursors (537 files). They live in Sweet-kde, Sweet-kvantum and Sweet-cursors now. | Removed (fb33d1e) |
| Firefox, wallpapers | Not part of a GTK theme. | Removed (3563749) |
| GTK 2, Cinnamon, Metacity, Xfwm4 | 499 files. | Removed (75e7205) |
| GNOME Shell before 46 | The per-version shell themes, and the Pop!_OS COSMIC dock styles that only they imported. | Removed (2ada55f) |
| Other desktops in the GTK CSS | Budgie, Unity, MATE, Xfce, LightDM, Nemo and Caja: 4,600 lines of SCSS and about 620 selectors per GTK version. Every remaining selector kept the same declarations. One was not scoped to its desktop: the Xfce file gave every GTK 4 `scrolledwindow.sidebar treeview.view` Thunar's sidebar background. | Removed (78c8a4d) |
| Cinnamon thumbnails | `gtk-3.0/thumbnail.png` and `gtk-4.0/thumbnail.png` were Cinnamon's theme-picker previews. | Removed (e2f1d1d) |

## 3. Build

| Area | Finding | Status |
| ---- | ------- | ------ |
| Compiler | The CSS was compiled by libsass 3.5 (node-sass 4 through Gulp), which nothing ships any more. dart-sass refused the GTK SCSS: it extended 17 compound selectors per GTK version (`%linked:last-child`, `%button.flat.suggested-action`, ...). libsass 3.6 (`sassc`) compiles it but adds about 1,700 wrong selectors per GTK stylesheet (`progressbar:backdrop progress.action-bar`) and drops 180. Each compound is now a placeholder at the rule it names. Four selectors that dart-sass would drop from extended lists won the cascade, and are kept explicitly; without that, link buttons would lose their hover colors and Shell's quick-settings buttons their hover icons. GTK renders are pixel-identical apart from the accepted row below; Shell has the same selectors and values. | Fixed, high (c96bc91) |
| Gulp and npm | 170 KB of lockfile ran one command (sass). The Gulp tasks also switched the desktop to the theme with `gsettings` after every build, and `npm run build` pushed to git. They are replaced by `build.py`: `css`, `assets`, `check`, `watch` and `install`. It rounds the fractional `rgb(%)` colors dart-sass 1.79+ prints back to the hex that GTK and St read, and silences only the known deprecations. A full build takes 0.5 s. | Fixed, high (c37366d) |
| Image pipeline | `src/` had three SVGs and two render scripts. Of the 100 images the CSS used, only 14 matched what the SVGs render: the committed "light" images had dark check marks where `gtk3-assets.svg` draws white ones. The AUR package re-renders at build time, so it shipped a different theme from the repo: 118 images differ. The scale-2 script exported at 180 dpi (images 30 px instead of 32, so checks were drawn 15 px wide), and neither script waited for Inkscape before running optipng. `gtk3-assets-dark.svg` draws every used image exactly as committed, and is now `src/assets.svg`. `build.py assets` renders exactly the images the stylesheets name, at 96 and 192 dpi, in one Inkscape run (under 1 s, deterministic). At scale 1, all 53 states are pixel-identical. At scale 2 the look is the same, now 16 px and sharper. | Fixed, high (18ce0cc) |
| `build.py check` | Fails if a committed CSS differs from its SCSS, if a stylesheet names a missing image, or if an image is named by no stylesheet. | Fixed (c37366d, 18ce0cc) |
| Deprecations | dart-sass warns about `@import`, global color functions, `if()`, unary minus and `/` division. These become errors in Dart Sass 3. | Accepted (§7) |

## 4. GTK correctness and assets

| Area | Finding | Status |
| ---- | ------- | ------ |
| Invisible checks | 17 image URLs led nowhere, so GTK drew nothing. In a selection-mode content view (Photos, Boxes, ...), unchecked checks and radios asked for `selection-mode-*.png`, which were never added. At scale 1 they were invisible in every state; the render shows nothing before the fix and the theme's box and circle after. Disabled-in-backdrop images were named `*-backdrop-insensitive@2.png`, but the files are `*-insensitive-backdrop@2.png`. A disabled checked GTK 3 switch at scale 2 asked for `switch-slider-on-insensitive@@.png`. Pantheon's "auto" color radio asked for an elementary image that was never shipped, so its rule is gone. | Fixed, high (7426850) |
| Unused images | 166 files were named by no stylesheet: light, selection-mode, calendar, menu-item, pane, scale and grid images, Metacity button SVGs (they don't match the GTK buttons) and 5 GNOME Shell images. | Removed, low (18ce0cc) |
| `gtk-dark.css` | A copy of `gtk.css`, 200 KB per GTK version. It is now `@import url("gtk.css")`. It can't go away: GTK 3 falls back to `gtk.css`, but GTK 4 leaves an app that asks for the dark variant unstyled. With `GTK_THEME=Sweet:dark`, renders are identical to the plain theme. | Fixed, low (5f1a112) |
| Disabled tree view | The text of a selected row in a disabled tree view mixes 50 % instead of 40 % of the accent. dart-sass drops a selector that libsass kept, and the difference is barely visible. | Accepted |
| Backdrop headerbar | A disabled suggested-action button in an unfocused GTK 3 headerbar loses its gradient, for the same reason. | Accepted |
| Parse errors | GTK 3 and GTK 4 report 0 errors on their stylesheets. | OK |

## 5. GNOME Shell

| Area | Finding | Status |
| ---- | ------- | ------ |
| Dead selectors | 126 class and id names appear in no GNOME Shell from 46.0 to 51.1, and none is built from a template string. They cover the old end-session, mount, network and run dialogs, the screen shield, the workspace-switcher popup, panel corners, app-well icons, chat bubbles and the aggregate menu (GNOME 3.x to 45). The 207 selectors that name them are gone, along with the two arrow images only they used. No remaining selector changed. Classes that exist in some supported versions only stay. | Removed, low (c4bfe42) |
| Regressions | The shell renders identically to 2ada55f in all 14 views, apart from the clock's minute. | OK |
| GNOME 51 | All 14 views render correctly. A first version of the test loaded the theme as GNOME's only stylesheet, which no session does. That made the theme look broken: 215 of the 436 classes GNOME's theme styles are left to GNOME's stylesheet, and without it they fell back to St's bare defaults. A rebuild of the shell theme from GNOME 51's own was made on that basis, then dropped once the test loaded the theme as User Themes does. | OK (5e77911) |

## 6. Hygiene, tests and docs

| Area | Finding | Status |
| ---- | ------- | ------ |
| `index.theme` | It named the theme Sweet-Dark and pointed GtkTheme and MetacityTheme at a Sweet-Dark folder that no install makes. It also set an icon theme that isn't a dependency (Boston), a button layout, and the obsolete Encoding key, and the file was executable. | Fixed, medium (e2f1d1d) |
| File modes | 48 data files were executable (images, every GTK `.scss` and `.css`, the asset SVG), and the package installed them so. Only `build.py` and `tests/compare.py` are now. | Fixed, low (a611356) |
| Tests | There were none. `tests/compare.py` renders two revisions in private sessions and reports the pixels that differ (§8). | Fixed (f79c20c) |
| README | It said to extract a zip and set a Metacity theme. It now covers install, the build and its needs (dart-sass, not libsass), and where to edit what. | Fixed (c1a5771) |

## 7. Left open

- **GNOME Shell 46–50** weren't run (nothing here can run them). Only 51.1 was
  checked live; for 46–50, only that the removed selectors name nothing they have.
- **The lock screen's password entry** doesn't appear without GDM (the prompt
  stops at "Authentication error"), so it wasn't seen.
- **AUR package.** `sweet-gtk-theme-git` (in `awesome-sweet/PKGBUILDs` and
  `software-and-services/PKGBUILDs`) built upstream's `nova` branch: it rendered
  images with the deleted scripts and installed GTK 2, Cinnamon, Metacity and
  Xfwm4. Its font options did nothing (the shell CSS names no font) or broke
  the theme (one size for all 17 `font-size` declarations). It is rewritten
  to build this fork's `master` and run `build.py install`, and was
  test-built from the local clone with makepkg: 120 files, all 644. The rewrite
  isn't committed in those repos yet, and needs this branch pushed.
- **Dart Sass 3.** The SCSS uses `@import` and global color functions, and
  `build.py` silences their warnings. Moving to `@use` and `color.adjust()`
  is needed before Dart Sass 3.
- **GTK 4 SCSS** still styles some GTK 3-only nodes. They are harmless, since
  GTK ignores selectors that match nothing.
- **OpenWeather styles** (`gnome-shell/extensions/`) weren't checked against
  the current extension.
- **Untested:** the libadwaita path (`~/.config/gtk-4.0`), Pantheon apps, Geary
  and Rnote live. The galleries cover the generic widgets those apps use.

## 8. Re-running the audit

```sh
python3 build.py check       # CSS up to date, every image there and used
python3 build.py && python3 build.py assets && git status --short   # nothing changes

# GTK's own parser: prints the error count
for v in 3 4; do python3 - $v gtk-$v.0/gtk.css <<'EOF'
import sys, gi
gi.require_version("Gtk", sys.argv[1] + ".0")
from gi.repository import Gtk
errors = []
p = Gtk.CssProvider()
p.connect("parsing-error", lambda *a: errors.append(a[-1].message))
p.load_from_path(sys.argv[2])
print(sys.argv[2], len(errors), "errors")
EOF
done

# Before/after renders: GTK 3/4 in 5 states, and GNOME Shell's main views,
# in private headless sessions. Compare against the audit's base:
tests/compare.py 2ada55f            # both; about 70 s
tests/compare.py --gtk --scale 2 HEAD
```
