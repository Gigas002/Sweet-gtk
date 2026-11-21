"""A window of GTK widgets, for comparing themes: gallery.py GTKVER STATE OUT.png

GTKVER is 3 or 4; STATE is normal, hover, active, disabled or backdrop, forced on every
widget. It takes a screenshot of the output with grim and exits, so it must run as the only
window of a compositor (tests/compare.py runs it in a private headless sway)."""
import subprocess
import sys

import gi

ver, state, out = sys.argv[1], sys.argv[2], sys.argv[3]
gi.require_version('Gtk', ver + '.0')
from gi.repository import Gtk, GLib
G4 = ver == '4'
if not G4: Gtk.init([])

def add(box, w):
    box.append(w) if G4 else box.pack_start(w, False, False, 0)

def hbox(*ws, cls=None, sp=6):
    b = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=sp)
    if cls: b.get_style_context().add_class(cls) if not G4 else b.add_css_class(cls)
    for w in ws: add(b, w)
    return b

def vbox(*ws, cls=None, sp=6):
    b = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=sp)
    if cls: b.get_style_context().add_class(cls) if not G4 else b.add_css_class(cls)
    for w in ws: add(b, w)
    return b

def css(w, *c):
    for x in c: w.add_css_class(x) if G4 else w.get_style_context().add_class(x)
    return w

def btn(label, *c): return css(Gtk.Button(label=label), *c)

def toggled(label, *c):
    t = css(Gtk.ToggleButton(label=label), *c); t.set_active(True); return t

def check(label, active, radio=False, group=None):
    if G4:
        w = Gtk.CheckButton(label=label)
        if group: w.set_group(group)
    elif radio:
        w = Gtk.RadioButton.new_with_label_from_widget(group, label)
    else:
        w = Gtk.CheckButton(label=label)
    w.set_active(active); return w

def entry(text, sel=True):
    e = Gtk.Entry(); e.set_text(text)
    if sel: GLib.idle_add(lambda: e.select_region(0, 5) or False)
    return e

def notebook():
    n = Gtk.Notebook(); n.set_scrollable(True); n.set_size_request(260, 60)
    for i in range(8):
        lab = Gtk.Label(label=f'page {i}')
        n.append_page(lab, Gtk.Label(label=f'Tab {i}'))
    return n

def listbox():
    l = Gtk.ListBox()
    for i in range(3):
        r = Gtk.Label(label=f'row {i}', xalign=0)
        l.append(r) if G4 else l.add(r)
    GLib.idle_add(lambda: l.select_row(l.get_row_at_index(1)) or False)
    return l

def treeview():
    st = Gtk.ListStore(str, str)
    for r in (('alpha', '1'), ('beta', '2'), ('gamma', '3')): st.append(r)
    t = Gtk.TreeView(model=st)
    for i, n in enumerate(('Name', 'Value')):
        t.append_column(Gtk.TreeViewColumn(n, Gtk.CellRendererText(), text=i))
    t.get_selection().select_path(1)
    return t

def textview():
    tv = Gtk.TextView(); b = tv.get_buffer(); b.set_text('selected text in a view\nsecond line')
    b.select_range(b.get_start_iter(), b.get_iter_at_offset(8)); tv.set_size_request(200, 40)
    return tv

def headerbar(selection=False):
    h = Gtk.HeaderBar()
    if not G4: h.set_show_close_button(True); h.set_title('Header')
    h.pack_start(btn('Back'))
    h.pack_start(hbox(btn('A'), btn('B'), btn('C'), cls='linked', sp=0))
    h.pack_end(btn('Done', 'suggested-action'))
    if selection: css(h, 'selection-mode')
    return h

if G4:
    combo = Gtk.DropDown.new_from_strings(['One', 'Two'])
    combo2 = Gtk.ComboBoxText(); combo2.append_text('Combo'); combo2.set_active(0)
else:
    combo = Gtk.ComboBoxText(); combo.append_text('Combo'); combo.set_active(0)
    combo2 = Gtk.ComboBoxText.new_with_entry(); combo2.append_text('Entry combo'); combo2.set_active(0)

r1 = check('Radio on', True, radio=True)
scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 100, 1); scale.set_value(40); scale.set_size_request(160, -1)
prog = Gtk.ProgressBar(); prog.set_fraction(0.6); prog.set_size_request(160, -1)
lvl = Gtk.LevelBar(); lvl.set_value(0.5); lvl.set_size_request(160, -1)
sw1 = Gtk.Switch(); sw1.set_active(True)
spin = Gtk.SpinButton.new_with_range(0, 100, 1); spin.set_value(42)
link = Gtk.LinkButton.new_with_label('https://example.org', 'A link')
info = Gtk.InfoBar(); info.set_message_type(Gtk.MessageType.WARNING)
ilab = Gtk.Label(label='Info bar warning')
info.add_child(ilab) if G4 else info.get_content_area().add(ilab)
cal = Gtk.Calendar()
exp = Gtk.Expander(label='Expander'); exp.set_expanded(True)
expl = Gtk.Label(label='inside'); exp.set_child(expl) if G4 else exp.add(expl)

col1 = vbox(
    hbox(btn('Normal'), btn('Flat', 'flat'), toggled('Toggled'), btn('Suggested', 'suggested-action'), btn('Destructive', 'destructive-action')),
    hbox(btn('Flat sugg', 'flat', 'suggested-action'), btn('Flat destr', 'flat', 'destructive-action'), btn('Circular', 'circular'), link),
    hbox(hbox(btn('First'), btn('Middle'), toggled('Last'), cls='linked', sp=0),
         vbox(btn('Top'), btn('Bottom'), cls='linked', sp=0),
         hbox(entry('linked entry', False), btn('Go'), cls='linked', sp=0)),
    hbox(combo, combo2, spin),
    hbox(entry('Entry with selection'), css(entry('error entry', False), 'error')),
    hbox(check('Check on', True), check('Check off', False), r1, check('Radio off', False, True, r1), sw1, Gtk.Switch()),
    hbox(scale, prog, lvl),
    notebook(), info,
)
rsel = check('sel radio', False, radio=True)
contentview = css(hbox(check('sel check', False), rsel, check('sel radio 2', False, True, rsel)), 'view', 'content-view')
col2 = vbox(listbox(), treeview(), textview(), exp, cal, contentview)
body = hbox(col1, col2, sp=18)
win = Gtk.Window(); win.set_default_size(1200, 760)
root = vbox(headerbar(True), body, sp=12)
if G4: win.set_titlebar(headerbar()); win.set_child(root)
else: win.set_titlebar(headerbar()); win.add(root)

FLAGS = {'hover': Gtk.StateFlags.PRELIGHT, 'active': Gtk.StateFlags.ACTIVE, 'backdrop': Gtk.StateFlags.BACKDROP}

def walk(w):
    yield w
    if G4:
        c = w.get_first_child()
        while c: yield from walk(c); c = c.get_next_sibling()
    elif isinstance(w, Gtk.Container):
        for c in w.get_children(): yield from walk(c)

def apply():
    if state == 'disabled':
        for w in (body, ):
            w.set_sensitive(False)
    elif state in FLAGS:
        targets = [win] if state == 'backdrop' else list(walk(body))
        for w in targets: w.set_state_flags(FLAGS[state], False)
    return False

def shoot():
    subprocess.run(['grim', out], check=True)
    (win.destroy() if G4 else Gtk.main_quit())
    if G4: loop.quit()
    return False

GLib.timeout_add(600, apply)
GLib.timeout_add(1500, shoot)
if G4:
    win.present(); loop = GLib.MainLoop(); loop.run()
else:
    win.show_all(); Gtk.main()
