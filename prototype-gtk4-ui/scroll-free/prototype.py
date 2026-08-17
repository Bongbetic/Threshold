#!/usr/bin/env python3
"""Threshold — Industrial Grid UI Prototype.

Based on the Industrial Grid UI Design Specification.
Run: python3 prototype-gtk4-ui/scroll-free/prototype.py
"""
import gi
import os

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, Gdk


class ThresholdPrototype(Adw.Application):
    def __init__(self):
        super().__init__(application_id="com.bongbetic.threshold.prototype")
        self.connect("activate", self.on_activate)

    def on_activate(self, app):
        self.win = Adw.ApplicationWindow(application=app)
        self.win.set_title("Threshold")
        self.win.set_default_size(1100, 820)
        self.win.set_size_request(900, 680)

        self._setup_css()

        base = os.path.dirname(os.path.abspath(__file__))
        builder = Gtk.Builder()
        builder.add_from_file(os.path.join(base, "target.ui"))
        root = builder.get_object("root")
        self.win.set_content(root)

        self.win.present()

    def _setup_css(self):
        css_provider = Gtk.CssProvider()
        css_provider.load_from_string("""
            /* === Window & Background === */
            .threshold-window {
                background: #171717;
                color: #F4F4F4;
            }

            /* === Header === */
            .industrial-header {
                background: #202020;
                border-bottom: 1px solid #303030;
                min-height: 48px;
                padding-top: 4px;
                padding-bottom: 4px;
            }
            .header-menu-btn {
                background: #2B2B2B;
                border-radius: 9px;
                min-width: 46px;
                min-height: 46px;
            }
            .header-title {
                font-size: 20px;
                font-weight: 600;
                color: #F4F4F4;
            }
            .nav-item {
                font-size: 18px;
                font-weight: 400;
                color: #C3C3C3;
                background: transparent;
                border: none;
                border-bottom: 2px solid transparent;
                border-radius: 0;
                padding: 2px 0;
                margin: 0 18px;
            }
            .nav-item:hover {
                color: #FFFFFF;
            }
            .nav-item-active {
                color: #FFFFFF;
                border-bottom: 2px solid #FF7800;
            }

            /* === Panel / Card === */
            .panel {
                background: #222222;
                border: 1px solid #3A3A3A;
                border-radius: 8px;
                padding: 12px 14px;
            }
            .panel-title {
                font-size: 17px;
                font-weight: 600;
                color: #F3F3F3;
                margin-bottom: 8px;
            }

            /* === Instrument Values === */
            .instrument-value {
                font-size: 36px;
                font-weight: 400;
                color: #F4F4F4;
            }
            .instrument-value-accent {
                font-size: 36px;
                font-weight: 400;
                color: #FF7800;
            }
            .instrument-value-sm {
                font-size: 24px;
                font-weight: 400;
                color: #FF7800;
            }

            /* === Metadata === */
            .metadata-label {
                font-size: 14px;
                color: #8D8D8D;
            }
            .metadata-value {
                font-size: 16px;
                color: #EEEEEE;
            }
            .metadata-caption {
                font-size: 13px;
                color: #9C9C9C;
            }
            .metadata-caption-value {
                font-size: 14px;
                color: #EEEEEE;
            }

            /* === Charging Status === */
            .charging-icon {
                color: #B7B7B7;
            }
            .charging-label {
                font-size: 15px;
                color: #B7B7B7;
            }

            /* === Vertical Divider === */
            .v-divider {
                background: #414141;
                min-width: 1px;
            }

            /* === Threshold Mode Buttons === */
            .mode-btn {
                background: #303030;
                color: #BDBDBD;
                border: none;
                border-radius: 7px;
                min-height: 40px;
                font-size: 15px;
                font-weight: 500;
            }
            .mode-btn:hover {
                background: #383838;
            }
            .mode-btn-active {
                background: rgba(255, 120, 0, 0.22);
                color: #FF7800;
            }

            /* === Slider === */
            .threshold-slider {
                min-height: 22px;
            }
            .slider-label {
                font-size: 14px;
                color: #A6A6A6;
            }
            .recommendation-text {
                font-size: 14px;
                color: #A4A4A4;
            }

            /* === Preset Tiles === */
            .preset-tile {
                background: #272727;
                border: 1px solid #414141;
                border-radius: 7px;
                min-height: 48px;
                padding: 4px 8px;
                margin: 0;
            }
            .preset-tile:hover {
                background: #303030;
            }
            .preset-tile-selected {
                background: rgba(255, 120, 0, 0.12);
                border: 1px solid #FF7800;
            }
            .preset-value {
                font-size: 17px;
                font-weight: 600;
                color: #F4F4F4;
            }
            .preset-value-selected {
                color: #FF7800;
            }
            .preset-subtitle {
                font-size: 14px;
                color: #9C9C9C;
            }
            .preset-subtitle-selected {
                color: #FF7800;
            }
            .preset-check {
                color: #FF7800;
                font-size: 16px;
            }

            /* === Action Buttons === */
            .primary-action {
                background: #FF7800;
                color: #FFFFFF;
                border: none;
                border-radius: 7px;
                min-height: 38px;
                font-size: 15px;
                font-weight: 600;
            }
            .primary-action:hover {
                background: #FF8B1A;
            }
            .primary-action:active {
                background: #E96D00;
            }
            .secondary-action {
                background: #353535;
                color: #F1F1F1;
                border: none;
                border-radius: 7px;
                min-height: 38px;
                font-size: 15px;
            }
            .secondary-action:hover {
                background: #3D3D3D;
            }

            /* === Settings Rows === */
            .settings-row {
                padding: 3px 0;
                border-bottom: 1px solid #3A3A3A;
            }
            .settings-row:last-child {
                border-bottom: none;
            }
            .settings-row-title {
                font-size: 15px;
                color: #F1F1F1;
            }
            .settings-row-desc {
                font-size: 13px;
                color: #8F8F8F;
            }
            .nested-setting {
                background: #292929;
                border: 1px solid #3E3E3E;
                border-radius: 6px;
                padding: 6px 10px;
            }

            /* === Accent Color Swatches === */
            .accent-swatch {
                border-radius: 9999px;
                min-width: 24px;
                min-height: 24px;
                padding: 0;
                margin: 0 3px;
                border: 2px solid transparent;
                background: none;
                background-clip: padding-box;
                box-shadow: none;
                outline: none;
            }
            .accent-swatch:checked {
                border: 2px solid #FF7800;
                background-clip: padding-box;
            }
            .accent-swatch:hover {
                border: 2px solid rgba(255, 255, 255, 0.5);
                background-clip: padding-box;
            }
            .swatch-orange { background: #FF7800; min-width: 24px; min-height: 24px; }
            .swatch-blue   { background: #4A91F2; min-width: 24px; min-height: 24px; }
            .swatch-green  { background: #32D74B; min-width: 24px; min-height: 24px; }
            .swatch-purple { background: #A44BF4; min-width: 24px; min-height: 24px; }
            .swatch-red    { background: #F04444; min-width: 24px; min-height: 24px; }

            /* Container for swatches — tight horizontal layout */
            .accent-swatch-row {
                padding: 0;
            }

            /* === Footer === */
            .footer-bar {
                background: #1B1B1B;
                border-top: 1px solid #323232;
                min-height: 44px;
                padding-top: 4px;
                padding-bottom: 4px;
            }
            .footer-label {
                font-size: 14px;
                color: #C6C6C6;
            }
            .footer-value {
                font-size: 14px;
                color: #EEEEEE;
            }
            .profile-dropdown {
                background: #303030;
                border: 1px solid #3A3A3A;
                border-radius: 7px;
                min-height: 38px;
            }
            .save-btn {
                background: #303030;
                border: 1px solid #3A3A3A;
                border-radius: 7px;
                min-width: 44px;
                min-height: 38px;
            }
            .save-btn:hover {
                background: #383838;
            }

            /* === Switch overrides === */
            .switch-orange {
                background: rgba(255, 120, 0, 0.18);
                border: 1px solid #FF7800;
            }

            /* === Separator === */
            .grid-separator {
                background: #383838;
                min-height: 1px;
            }
        """)
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(),
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )


if __name__ == "__main__":
    app = ThresholdPrototype()
    app.run()
