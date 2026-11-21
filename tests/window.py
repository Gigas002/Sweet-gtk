"""An empty GTK 4 window titled TITLE, for the shell tests: window.py TITLE. Runs until killed."""
import sys

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import GLib, Gtk

window = Gtk.Window(title=sys.argv[1])
window.set_default_size(640, 400)
window.set_child(Gtk.Label(label=sys.argv[1]))
window.present()
GLib.MainLoop().run()
