# WebKitGTK ↔ Python Bridge: Script Message Handlers vs Injected JS vs Local Sidecar

**Research ticket**: [#37](https://github.com/Bongbetic/Threshold/issues/37) (map: #34)

**Sources**: [WebKitGTK stable API reference](https://webkitgtk.org/reference/webkitgtk/stable/) (register_script_message_handler, script-message-received, evaluate_javascript, UserScript), [pywebview source](https://github.com/r0x0r/pywebview/tree/master/webview/platforms) (real GTK bridge), Threshold's own backend (`src/threshold/battery.py`, `src/threshold/config.py`, `src/threshold/window.py`).

---

## Question

Which bridging mechanism should the Carbon web UI use to talk to the Python
backend — WebKitGTK **script message handlers**, an **injected JS API**, or a
**local socket/HTTP sidecar**? Evaluated against Threshold's real flows:
apply threshold (needs ack), control-mode state, battery status polling,
GSettings persistence.

## TL;DR

**Use WebKitGTK script message handlers as the transport** (JS → Python
requests), with **`evaluate_javascript` for Python → JS pushes** (events and
acks), and a **small injected `UserScript` shim** that wraps both into a
promise-based `window.threshold` API. Do **not** run a local sidecar: it adds
a process, a port, an auth surface, and a serialization layer the in-process
bridge already provides.

"Injected JS API" is not a competing transport — you cannot inject Python into
a page. Injection is the *ergonomics layer* on top of message handlers.

---

## Options evaluated

### Option A — Script message handlers (native WebKitGTK bridge)

Python registers a named handler on the WebView's `UserContentManager`; JS
calls `window.webkit.messageHandlers.<name>.postMessage(value)`; Python
receives the value via the `script-message-received::<name>` signal
([docs](https://webkitgtk.org/reference/webkitgtk/stable/method.UserContentManager.register_script_message_handler.html)).

- One-way JS → Python, structured values (arrives as a `JSC.Value`).
- Async, delivered on the GTK main thread — same loop as GLib timeouts,
  GSettings signals, and GTK signal handlers. No IPC, no sockets.
- Available since WebKitGTK 2.8; the `world_name` parameter since 2.40.

For Python → JS, the same WebView exposes
[`evaluate_javascript`](https://webkitgtk.org/reference/webkitgtk/stable/method.WebView.evaluate_javascript.html)
(2.40+; replaces deprecated `run_javascript`): runs a script string in the
page asynchronously. Marshalling data = `json.dumps` + `JSON.parse`.

### Option B — Injected JS API (UserScript shim)

`UserContentManager.add_script(WebKit.UserScript(...))` injects JS at document
creation, before page scripts run ([docs](https://webkitgtk.org/reference/webkitgtk/stable/class.UserContentManager.html)).
An injected shim can define `window.threshold.request(cmd, args) → Promise`
and an event emitter, implemented on top of `postMessage` (A) and a global
push callback driven by `evaluate_javascript` (A).

- Pure ergonomics: keeps Carbon components free of WebKit-specific globals;
  gives request/response correlation and typed events.
- Cannot move data Python → JS or back by itself. Always needs A underneath.

### Option C — Local socket / HTTP sidecar

Python runs a localhost HTTP/WebSocket server; the WebView fetches it.

- Pros: transport-agnostic (curl-testable, could serve a future CLI/remote UI).
- Cons for Threshold:
  - New always-on process or thread + a port to own (collision, firewall
    prompts in some desktops, sandbox/Flatpak wrangling).
  - Auth surface: a localhost server is reachable by *any* local process and
    by the browser (CSRF / DNS-rebinding) — writing sysfs thresholds behind an
    unauthenticated `POST /threshold` needs token minting at minimum.
  - Push requires WebSockets or polling-on-top-of-polling.
  - Packaging: an HTTP framework dependency for zero added capability.
  - Battery polling would move from one GLib timeout to HTTP chatter.
- Threshold is a single-window, single-process desktop app whose backend
  already lives in the same process as the WebView. A sidecar solves a
  problem Threshold does not have (multi-client serving), at real cost.

### Comparison against Threshold's flows

| Flow | A: message handlers (+eval push) | B: injected shim | C: sidecar |
|---|---|---|---|
| Apply threshold with ack | Request id → threaded sysfs write → ack pushed via `evaluate_javascript` | Promise API over A; same ack | HTTP req/res works; pkexec dialog still needs main loop care |
| Control-mode state | Push on load + on change (rare event) — trivial | `threshold.on('mode')` sugar | Needs WS/poll for push |
| Battery polling (5 s) | Existing `GLib.timeout_add_seconds(5)` stays; push JSON each tick | Event sugar | Timer in server + WS push, or JS fetch loop |
| GSettings | `changed::*` signals → push; writes via bridge (runs as user, no auth issue) | Same | Same, plus token auth for writes |
| Offline bundling | Zero network; page from gresource/local files | Same | Loopback only, but still a server |
| Security surface | None beyond WebKit sandbox | Same | localhost port = real attack surface |
| Packaging | `gir1.2-webkit-6.0` only | Same | + HTTP/WS deps |
| Moving parts | None extra | One static JS string | Process/port/token lifecycle |

## Recommendation

**A + B combined; C rejected.** Concretely:

1. One registered handler name (e.g. `threshold`) carrying JSON-stringified
   request messages `{id, cmd, args}` from JS.
2. Python answers and pushes via `evaluate_javascript` calling
   `window.threshold._receive(payload)` with `{id, ok, result}` for acks and
   `{event, data}` for state pushes.
3. A ~40-line injected UserScript turns that into:
   `await window.threshold.request('applyThreshold', {value: 80})` and
   `window.threshold.on('battery', handler)`.
4. Backend work (sysfs write, pkexec) runs on a worker thread; only the push
   back to the WebView happens on the GLib main loop.

### Why it fits Threshold's four flows

- **Apply threshold (needs ack)** — `write_threshold()` (`battery.py`) returns
  `(success, method_or_error)` and may block up to 30 s on the pkexec auth
  dialog (`subprocess.run(..., timeout=30)`). `script-message-received` fires
  on the main thread; the handler must return fast, so the write goes to a
  `GLib.Thread` worker and the ack is pushed back via `GLib.idle_add` +
  `evaluate_javascript`. Request-id correlation gives exactly the ack
  semantics the flow needs (including delivering the pkexec-failure string).
- **Control-mode state** — `detect_control_mode()` output is small, static
  state; include it in one `state` snapshot pushed at page load and re-push
  on the rare change. No polling needed.
- **Battery polling** — today's pattern is `GLib.timeout_add_seconds(5)` in
  `window.py` (`_poll_tick`). Keep that ownership in Python (single source of
  truth, timer survives WebView reloads, no double timers) and push
  `{event: 'battery', data: {...}}` each tick. The web UI stays stateless
  about acquisition.
- **GSettings** — `Config` (`config.py`) already wraps `Gio.Settings` and
  exposes `connect('changed::key', cb)`. Every `changed::` signal fans out to
  the page as an event; JS settings writes are bridge commands calling the
  same `Config` setters. dconf change-notification for free, including
  changes made by external tools like `dconf-editor`.

## Example patterns

### Python side (PyGObject, GTK4 → WebKit 6.0 API)

```python
import json
import gi

gi.require_version("WebKit", "6.0")
gi.require_version("JavaScriptCore", "6.0")

from gi.repository import WebKit, GLib

class Bridge:
    def __init__(self, webview: WebKit.WebView, backend):
        self.webview = webview
        self.backend = backend          # battery/config services
        self._pending = {}              # request id -> callback (if needed)
        ucm = webview.get_user_content_manager()

        # Inject the shim before any page load (Option B).
        ucm.add_script(WebKit.UserScript(
            BRIDGE_SHIM_JS,
            WebKit.UserContentInjectedFrames.ALL_FRAMES,
            WebKit.UserScriptInjectionTime.DOCUMENT_END,
            None, None,
        ))

        # Connect BEFORE registering — the docs call this out to avoid races.
        ucm.connect("script-message-received::threshold", self._on_message)
        ucm.register_script_message_handler("threshold", None)  # default world

    # JS -> Python: arrives on the main thread. Return fast!
    def _on_message(self, ucm, jsc_value):
        msg = json.loads(jsc_value.to_string())   # shim always sends JSON text
        cmd, args, rid = msg["cmd"], msg.get("args", {}), msg["id"]

        if cmd == "applyThreshold":
            # write_threshold may block ~30 s on the pkexec dialog -> worker.
            GLib.Thread.spawn(None, self._apply_worker, rid, args["value"])
        elif cmd == "getState":
            self.push({"id": rid, "ok": True,
                       "result": self.backend.snapshot()})
        elif cmd == "setSetting":
            self.backend.config.set(args["key"], args["value"])  # GSettings
            self.push({"id": rid, "ok": True, "result": None})   # changed:: event follows

    def _apply_worker(self, rid, value):
        ok, detail = self.backend.write_threshold(value)   # battery.py logic
        # Marshal back to the main loop, then into the page.
        GLib.idle_add(self.push, {"id": rid, "ok": ok, "result": detail})

    # Python -> JS (acks + events)
    def push(self, payload: dict):
        script = f"window.threshold._receive({json.dumps(payload)});"
        self.webview.evaluate_javascript(script, -1, None, None, None, None, None)

    # Event fan-out used by poller / GSettings / mode changes
    def emit(self, event: str, data):
        self.push({"event": event, "data": data})
```

Wiring the existing flows:

```python
GLib.timeout_add_seconds(5, self._poll_tick)     # unchanged pattern from window.py
def _poll_tick(self):
    self.bridge.emit("battery", self.backend.read_battery())
    return GLib.SOURCE_CONTINUE

self.backend.config.connect("changed::dark-mode",
    lambda s, k: self.bridge.emit("settings", {"key": k,
                                               "value": s.get_boolean(k)}))
```

### Injected shim (Option B, ~40 lines of JS)

```js
(() => {
  let seq = 0;
  const waiting = new Map();
  const listeners = new Map();

  window.threshold = {
    request(cmd, args = {}) {
      return new Promise((resolve, reject) => {
        const id = ++seq;
        waiting.set(id, { resolve, reject });
        window.webkit.messageHandlers.threshold
          .postMessage(JSON.stringify({ id, cmd, args }));
      });
    },
    on(event, cb) {
      (listeners.get(event) ?? listeners.set(event, []).get(event)).push(cb);
    },
    // Called from Python via evaluate_javascript.
    _receive(payload) {
      if (payload.event) {
        for (const cb of listeners.get(payload.event) ?? []) cb(payload.data);
      } else if (waiting.has(payload.id)) {
        const p = waiting.get(payload.id); waiting.delete(payload.id);
        payload.ok ? p.resolve(payload.result) : p.reject(payload.result);
      }
    },
  };
})();
```

Carbon UI usage:

```js
const state = await window.threshold.request('getState');
window.threshold.on('battery', (b) => gauge.value = b.percent);
try {
  await window.threshold.request('applyThreshold', { value: 80 });
  notification.open({ kind: 'success', ... });
} catch (e) {   // e is pkexec error string from write_threshold
  notification.open({ kind: 'error', ... });
}
```

## Version & security notes

- **API/dependency**: GTK4 shell → `webkitgtk-6.0` (`gir1.2-webkit-6.0`,
  `WebKit-6.0` namespace; `JavaScriptCore-6.0` for `JSC.Value`).
  `evaluate_javascript` and the `world_name` parameter require WebKitGTK
  **2.40 (March 2023)**; current Debian (≥ 12) and Ubuntu (≥ 22.04) releases
  ship at or above this. Repo floors (`gtk4 >= 4.14`, `libadwaita-1 >= 1.5`,
  Debian 13 targets per `docs/research/debian13-package-versions.md`) already
  imply a newer base than 2.40.
- **Registration order**: connect `script-message-received::<name>` *before*
  `register_script_message_handler` — the API reference explicitly warns
  about the race.
- **Keep JSON as strings**: the shim `postMessage`-es `JSON.stringify(...)`
  and Python `to_string()`-es it. This sidesteps `JSC.Value` structural
  access and gir mapping differences between 4.1/6.0.
- **Threading**: `script-message-received` and `evaluate_javascript` run on
  the main loop. `write_threshold`'s pkexec fallback blocks → worker thread
  mandatory, ack marshalled via `GLib.idle_add`.
- **Sandbox**: no remote content — serve the Carbon bundle from local files or
  gresource; if a custom URI scheme is used, register it as local via
  `WebKit.SecurityManager`. The bridge then never leaves the WebKit
  sandbox/process model; there is no listening socket to attack.
- **Reject option C** unless a second client (CLI daemon, remote UI) ever
  becomes a real requirement — and if it does, it belongs in a separate
  decision, since it reopens packaging and auth.

## Real-world precedent

- **pywebview** (portable Python webview toolkit): its GTK backend implements
  the `js_api` bridge exactly this way — a `UserContentManager` script message
  handler receives calls from an injected JS shim, and Python returns values
  by executing JS in the page
  ([webview/platforms/gtk.py](https://github.com/r0x0r/pywebview/blob/master/webview/platforms/gtk.py)).
  Same architecture as recommended here: handlers + shim + host-side eval.
- **WebKitGTK's own API reference** uses this pair (register handler +
  `script-message-received`, `evaluate_javascript`) as the canonical
  script-communication examples — see sources above.
- **Same-family API elsewhere**: `window.webkit.messageHandlers` is the
  identical surface Apple's WKWebView exposes (`WKScriptMessageHandler`), so
  the pattern is the standard, battle-tested WebKit bridge, not a GTK-only
  idiosyncrasy.

## References

- Register script message handler:
  https://webkitgtk.org/reference/webkitgtk/stable/method.UserContentManager.register_script_message_handler.html
- script-message-received signal:
  https://webkitgtk.org/reference/webkitgtk/stable/signal.UserContentManager.script-message-received.html
- evaluate_javascript:
  https://webkitgtk.org/reference/webkitgtk/stable/method.WebView.evaluate_javascript.html
- UserContentManager (UserScript injection):
  https://webkitgtk.org/reference/webkitgtk/stable/class.UserContentManager.html
- pywebview GTK platform (real bridge implementation):
  https://github.com/r0x0r/pywebview/blob/master/webview/platforms/gtk.py
- Threshold backend under discussion: `src/threshold/battery.py`
  (`write_threshold`, `detect_control_mode`), `src/threshold/config.py`
  (GSettings wrapper), `src/threshold/window.py` (5 s poll loop).
