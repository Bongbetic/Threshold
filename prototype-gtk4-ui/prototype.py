#!/usr/bin/env python3
import gi
import os

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, Gdk, GObject


class BatteryGuardApp(Adw.Application):
    variant_names = {
        0: "Variant A — Settings",
        1: "Variant B — Dashboard",
        2: "Variant C — Navigation",
    }

    def __init__(self):
        super().__init__(application_id="com.example.BatteryGuardPrototype")
        self.connect("activate", self.on_activate)

    def on_activate(self, app):
        self.win = Adw.ApplicationWindow(application=app)
        self.win.set_title("BatteryGuard GTK4 — UI Prototype")
        self.win.set_default_size(500, 600)

        overlay = Gtk.Overlay()
        self.win.set_content(overlay)

        self.stack = Gtk.Stack()
        overlay.set_child(self.stack)
        self._load_variants()

        self.stack.set_visible_child_name("variant_a")
        self._current_variant = 0

        switcher_bar = self._build_switcher_bar()
        overlay.add_overlay(switcher_bar)

        self._setup_css()
        self._setup_keyboard_shortcuts()

        self.win.present()

    def _load_variants(self):
        base = os.path.dirname(os.path.abspath(__file__))

        builder = Gtk.Builder()
        builder.add_from_file(os.path.join(base, "variant_a.ui"))
        root_a = builder.get_object("root")
        self.stack.add_named(root_a, "variant_a")

        builder = Gtk.Builder()
        builder.add_from_file(os.path.join(base, "variant_b.ui"))
        root_b = builder.get_object("root")
        self.stack.add_named(root_b, "variant_b")

        builder = Gtk.Builder()
        builder.add_from_file(os.path.join(base, "variant_c.ui"))
        root_c = builder.get_object("root")
        self.stack.add_named(root_c, "variant_c")

        self.stack.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT_RIGHT)

        sidebar = root_c.get_first_child()
        content_stack = None
        if sidebar:
            next_sib = sidebar.get_next_sibling()
            if next_sib and isinstance(next_sib, Gtk.Stack):
                content_stack = next_sib
        if sidebar and isinstance(sidebar, Gtk.ListBox) and content_stack:
            sidebar.connect("row-activated", self._on_nav_row_activated, content_stack)

    def _on_nav_row_activated(self, listbox, row, content_stack):
        index = row.get_index()
        pages = content_stack.get_pages()
        if 0 <= index < pages.get_n_items():
            content_stack.set_visible_child(pages.get_item(index).get_child())

    def _build_switcher_bar(self):
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        box.set_css_classes(["switcher-bar"])

        self._btn_prev = Gtk.Button(label="←")
        self._btn_prev.connect("clicked", self._on_prev)
        box.append(self._btn_prev)

        self._label_variant = Gtk.Label(label=self.variant_names[0])
        box.append(self._label_variant)

        self._btn_next = Gtk.Button(label="→")
        self._btn_next.connect("clicked", self._on_next)
        box.append(self._btn_next)

        box.set_halign(Gtk.Align.CENTER)
        box.set_valign(Gtk.Align.END)
        box.set_margin_bottom(16)
        return box

    def _setup_css(self):
        css_provider = Gtk.CssProvider()
        css_provider.load_from_string(
            """
            .switcher-bar {
                background: rgba(0,0,0,0.75);
                border-radius: 24px;
                padding: 6px 16px;
            }
            .switcher-bar button {
                background: transparent;
                color: white;
                border: none;
                font-size: 18px;
                padding: 0 8px;
            }
            .switcher-bar label {
                color: white;
                font-size: 13px;
                padding: 0 12px;
            }
            .card {
                background: @card_bg_color;
                border-radius: 12px;
                padding: 16px;
                margin: 8px;
            }
            .accent {
                color: @accent_color;
            }
            #threshold_value {
                color: @accent_color;
            }
            .navigation-sidebar {
                background: @sidebar_bg_color;
                border-right: 1px solid @borders;
            }
            """
        )
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(),
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )

    def _setup_keyboard_shortcuts(self):
        controller = Gtk.EventControllerKey.new()
        self.win.add_controller(controller)
        controller.connect("key-pressed", self._on_key_pressed)

    def _on_key_pressed(self, controller, keyval, keycode, state):
        focused = self.win.get_focus()
        if focused and (isinstance(focused, Gtk.Text) or isinstance(focused, Gtk.Editable)):
            return False
        if keyval == Gdk.KEY_Left:
            self._goto_prev()
            return True
        elif keyval == Gdk.KEY_Right:
            self._goto_next()
            return True
        return False

    def _on_prev(self, button):
        self._goto_prev()

    def _on_next(self, button):
        self._goto_next()

    def _goto_prev(self):
        self._current_variant = (self._current_variant - 1) % 3
        name = ["variant_a", "variant_b", "variant_c"][self._current_variant]
        self.stack.set_visible_child_name(name)
        self._label_variant.set_label(self.variant_names[self._current_variant])

    def _goto_next(self):
        self._current_variant = (self._current_variant + 1) % 3
        name = ["variant_a", "variant_b", "variant_c"][self._current_variant]
        self.stack.set_visible_child_name(name)
        self._label_variant.set_label(self.variant_names[self._current_variant])


if __name__ == "__main__":
    app = BatteryGuardApp()
    app.run()
