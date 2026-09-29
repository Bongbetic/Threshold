"""Desktop appearance inputs, with bounded reads and portable fallbacks.

External CSS is data only. Polling observes atomic replacement and directories
created after startup; two failed reads discard a partial or removed palette.
"""
import os
import re
from pathlib import Path

ROLES = {
    'window_bg_color', 'window_fg_color', 'card_bg_color', 'card_fg_color',
    'accent_bg_color', 'accent_fg_color', 'view_bg_color', 'view_fg_color',
}


def luminance(color):
    channels = [int(color[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    linear = [c / 12.92 if c <= .04045 else ((c + .055) / 1.055) ** 2.4 for c in channels]
    return sum(c * w for c, w in zip(linear, (.2126, .7152, .0722)))


def parse_palette(text):
    """Resolve only known roles and hex literals; require readable color pairs."""
    if len(text) > 65536:
        return {}
    text = re.sub(r'/\*.*?\*/', '', text, flags=re.S)
    definitions = dict(re.findall(r'@define-color\s+(\w+)\s+([^;]+);', text))

    def resolve(role, seen=()):
        if role not in ROLES or role in seen:
            raise ValueError('Unknown or cyclic color')
        value = definitions.get(role, '').strip()
        if value.startswith('@'):
            return resolve(value[1:], (*seen, role))
        if not re.fullmatch(r'#[0-9a-fA-F]{6}', value):
            raise ValueError('Unsupported color')
        return value.lower()

    try:
        bg, fg = resolve('window_bg_color'), resolve('window_fg_color')
        card = resolve('card_bg_color') if 'card_bg_color' in definitions else bg
        card_fg = resolve('card_fg_color') if 'card_fg_color' in definitions else fg
        accent, accent_fg = resolve('accent_bg_color'), resolve('accent_fg_color')
        pairs = ((bg, fg), (card, card_fg), (card, fg), (bg, card_fg),
                 (accent, accent_fg), (bg, accent), (card, accent))
        for a, b in pairs:
            lo, hi = sorted((luminance(a), luminance(b)))
            if (hi + .05) / (lo + .05) < 4.5:
                return {}
    except ValueError:
        return {}
    return {
        '--bg-page': bg, '--bg-surface': card, '--bg-surface-raised': card,
        '--bg-grid-gap': bg, '--bg-interactive-hover': bg, '--bg-interactive-active': card,
        '--text-primary': fg, '--text-secondary': card_fg, '--text-tertiary': card_fg,
        '--text-placeholder': card_fg, '--border-subtle': card_fg, '--border-strong': card_fg,
        '--scrollbar-track': bg, '--scrollbar-thumb': card_fg,
        '--accent-color': accent, '--accent-hover': accent,
        '--text-on-accent': accent_fg, '--focus-color': accent,
    }


class DesktopAppearance:
    def __init__(self, path=None):
        config_home = Path(os.environ.get('XDG_CONFIG_HOME', str(Path.home() / '.config')))
        self.path = path or config_home / 'gtk-4.0/dank-colors.css'
        self.palette = {}
        self.scheme = None
        self._failures = 0
        self._proxy = None
        self._cancel = None
        self._handlers = []
        self._revision = 0
        self.refresh()

    def refresh(self):
        try:
            with self.path.open() as stream:
                palette = parse_palette(stream.read(65537))
        except (OSError, UnicodeError):
            palette = {}
        if palette:
            self.palette, self._failures = palette, 0
        else:
            self._failures += 1
            if self._failures >= 2:
                self.palette = {}

    def snapshot(self, mode, fallback, accent):
        palette = self.palette if mode == 'system' else {}
        inferred = fallback
        if palette:
            inferred = 'dark' if luminance(palette['--bg-page']) < .179 else 'light'
        scheme = (self.scheme or inferred) if mode == 'system' else mode
        if palette and scheme != inferred:
            palette = {}
        return {'mode': mode, 'scheme': scheme, 'accent_color': accent, 'palette': palette}

    def start(self):
        """Asynchronously subscribe to the Settings portal, including restarts."""
        from gi.repository import Gio, GLib
        self._cancel = Gio.Cancellable()

        def read():
            self.scheme = None
            self._revision += 1
            revision = self._revision
            if not self._proxy.get_name_owner():
                return

            def done(proxy, result, _data):
                try:
                    values = proxy.call_finish(result).unpack()[0]
                    if revision == self._revision and not self._cancel.is_cancelled():
                        preference = values.get('org.freedesktop.appearance', {})
                        self.scheme = {1: 'dark', 2: 'light'}.get(preference.get('color-scheme'))
                except GLib.Error:
                    pass
            self._proxy.call('ReadAll', GLib.Variant('(as)', (['org.freedesktop.appearance'],)),
                             Gio.DBusCallFlags.NONE, 2000, self._cancel, done, None)

        def changed(_proxy, _sender, signal, parameters):
            if signal == 'SettingChanged':
                namespace, key, value = parameters.unpack()
                if namespace == 'org.freedesktop.appearance' and key == 'color-scheme':
                    self._revision += 1
                    self.scheme = {1: 'dark', 2: 'light'}.get(value)

        def ready(_source, result, _data):
            try:
                proxy = Gio.DBusProxy.new_for_bus_finish(result)
            except GLib.Error:
                return
            if self._cancel.is_cancelled():
                return
            self._proxy = proxy
            self._handlers = [
                proxy.connect('g-signal', changed),
                proxy.connect('notify::g-name-owner', lambda *_: read()),
            ]
            read()

        Gio.DBusProxy.new_for_bus(
            Gio.BusType.SESSION, Gio.DBusProxyFlags.DO_NOT_AUTO_START,
            None, 'org.freedesktop.portal.Desktop', '/org/freedesktop/portal/desktop',
            'org.freedesktop.portal.Settings', self._cancel, ready, None,
        )

    def stop(self):
        if self._cancel:
            self._cancel.cancel()
        if self._proxy:
            for handler in self._handlers:
                self._proxy.disconnect(handler)
        self._handlers = []
