# Sweet

![](Art/Sweet-theme.png)

Fork of the [Sweet theme](https://github.com/EliverLara/Sweet): a dark, colorful theme for GTK 3, GTK 4 and GNOME Shell 46 and later.

- `gtk-3.0/`, `gtk-4.0/`: the GTK themes, with styles for libadwaita-less GNOME apps, Pantheon (granite), Geary and Rnote
- `gnome-shell/`: the GNOME Shell theme (needs the User Themes extension)
- `assets/`: the images both GTK themes use

## Install

On Arch Linux, the AUR package `sweet-gtk-theme-git` installs it.

Otherwise, the built theme is committed, so installing is a copy:

```sh
python3 build.py install              # to ~/.local/share/themes/Sweet
python3 build.py install /usr/share/themes   # system-wide (as root)
```

Then select it:

```sh
gsettings set org.gnome.desktop.interface gtk-theme Sweet
gsettings set org.gnome.shell.extensions.user-theme name Sweet   # with User Themes enabled
```

GTK 4 apps read `gtk-theme` only if they don't use libadwaita; for the others, copy `gtk-4.0/` to `~/.config/gtk-4.0/` or run them with `GTK_THEME=Sweet`.

## Build

Needs Python 3 and [dart-sass](https://sass-lang.com/dart-sass) 1.97.1 or later (`sass`; on Arch Linux, `dart-sass`), plus Inkscape to render images. libsass and `sassc` won't do: they compile this SCSS into different CSS.

```sh
python3 build.py          # compile the SCSS into the .css files
python3 build.py assets   # render the check and radio images from src/assets.svg
python3 build.py watch    # recompile on every .scss change
python3 build.py check    # fail if a .css is out of date, or an image is missing or unused
```

## Editing

The `.css` files are generated: edit the `.scss` and rebuild.

- `gtk-3.0/_colors.scss`: the palette. `gtk-4.0/_colors.scss` forwards it.
- `gtk-3.0/_drawing.scss`, `gtk-4.0/_drawing.scss`: the mixins and functions that draw buttons, entries and so on, and the shared transitions.
- `gtk-3.0/_common.scss`, `gtk-4.0/_common.scss`: defaults for every widget; one file per widget in `widgets/`, app styles in `apps/`.
- `gnome-shell/_common.scss`: the shell; `extensions/` styles the OpenWeather extension.

The SCSS uses Sass modules (`@use`), not `@import`. A file that writes CSS keeps its rules in a mixin called `styles`, and `gtk.scss` (or `gnome-shell.scss`) includes them all in order. That way an `@extend` in one file still reaches selectors in every other file, which plain `@use` wouldn't allow. A new widget file starts with the `@use` lines it needs (`'../colors' as *`, `'../drawing' as *`, `'sass:color'`), wraps its rules in `@mixin styles { ... }`, and is added to `_widgets.scss`.
- `src/assets.svg`: the check and radio images. Each is drawn in a layer labelled `Baseplate`, over a rect whose area is exported, with a text labelled `icon-name` giving the file name; `build.py assets` renders those a stylesheet names, at scale 1 and 2. The window buttons and switches in `assets/` are drawn by hand.

`tests/compare.py OLD [NEW]` renders two revisions (default NEW: the working tree) in private headless sway and GNOME Shell sessions and reports which pixels changed; see its header. [docs/AUDIT.md](docs/AUDIT.md) describes the 2026 clean-up.
