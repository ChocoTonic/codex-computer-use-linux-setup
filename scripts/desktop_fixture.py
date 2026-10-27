import json
import os
from pathlib import Path

import gi

gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
from gi.repository import Gdk, GLib, Gtk

GLib.set_prgname('codex-cu-compatibility-test')
root = Path(os.environ['CU_TEST_STATE'])
state = {'pid': os.getpid(), 'text': '', 'clicks': 0, 'scroll': 0.0, 'drags': 0}


def save():
    temporary = root / 'fixture-state.tmp'
    temporary.write_text(json.dumps(state))
    temporary.replace(root / 'fixture-state.json')


window = Gtk.Window(title='Codex Computer Use Compatibility Test')
window.set_default_size(580, 460)
window.move(60, 60)
window.connect('destroy', Gtk.main_quit)
box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
box.set_border_width(16)
window.add(box)
box.pack_start(Gtk.Label(label='Disposable computer-use test; no real data'), False, False, 0)
entry = Gtk.Entry()
entry.get_accessible().set_name('Compatibility input')


def changed(widget):
    state['text'] = widget.get_text()
    save()


entry.connect('changed', changed)
box.pack_start(entry, False, False, 0)
button = Gtk.Button(label='Compatibility button')


def clicked(*_):
    state['clicks'] += 1
    save()


button.connect('clicked', clicked)
box.pack_start(button, False, False, 0)
scroller = Gtk.ScrolledWindow()
scroller.set_min_content_height(160)
view = Gtk.TextView()
view.set_editable(False)
view.get_accessible().set_name('Compatibility scroll area')
view.get_buffer().set_text('\n'.join('Disposable test line %d' % i for i in range(100)))
scroller.add(view)
box.pack_start(scroller, True, True, 0)


def scrolled(adjustment):
    state['scroll'] = adjustment.get_value()
    save()


scroller.get_vadjustment().connect('value-changed', scrolled)
area = Gtk.DrawingArea()
area.set_size_request(500, 60)
area.get_accessible().set_name('Compatibility drag area')
area.add_events(Gdk.EventMask.BUTTON_PRESS_MASK | Gdk.EventMask.BUTTON_RELEASE_MASK)
start = None


def press(_, event):
    global start
    start = (event.x, event.y)


def release(_, event):
    global start
    if start and abs(event.x - start[0]) > 20:
        state['drags'] += 1
        save()
    start = None


area.connect('button-press-event', press)
area.connect('button-release-event', release)
box.pack_start(area, False, False, 0)
window.show_all()
entry.grab_focus()
save()
Gtk.main()
