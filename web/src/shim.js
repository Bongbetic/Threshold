/**
 * Document-start UserScript shim - injected before any page script.
 *
 * Exposes window.threshold.request() and window.threshold.on()
 * and hides direct webkit.messageHandlers access.
 */
(function() {
  'use strict';

  var _nextId = 0;
  var _pending = {};
  var _listeners = {};

  window.threshold = {
    /**
     * Send a request to Python and return a Promise for the response.
     */
    request: function(cmd, args) {
      return new Promise(function(resolve, reject) {
        var id = 'req-' + Date.now() + '-' + (_nextId++);
        _pending[id] = { resolve: resolve, reject: reject };

        var msg = JSON.stringify({ id: id, cmd: cmd, args: args });
        window.webkit.messageHandlers.threshold.postMessage(msg);
      });
    },

    /**
     * Register an event listener for push events from Python.
     * Returns an unsubscribe function.
     */
    on: function(event, callback) {
      if (!_listeners[event]) {
        _listeners[event] = [];
      }
      _listeners[event].push(callback);
      return function() {
        _listeners[event] = _listeners[event].filter(function(cb) {
          return cb !== callback;
        });
      };
    }
  };

  /**
   * Handle incoming messages from Python (called by Python evaluate_javascript).
   * This function is called from the native side via evaluate_javascript.
   */
  window.threshold._handleMessage = function(raw) {
    var msg;
    try {
      msg = JSON.parse(raw);
    } catch (e) {
      console.error('Threshold shim: malformed message', raw);
      return;
    }

    // Response to a pending request
    if (msg.id && typeof msg.ok === 'boolean') {
      var pending = _pending[msg.id];
      if (pending) {
        delete _pending[msg.id];
        if (msg.ok) {
          pending.resolve(msg.data);
        } else {
          pending.reject(new Error(msg.error || 'Unknown error'));
        }
      }
      return;
    }

    // Push event
    if (msg.event && _listeners[msg.event]) {
      _listeners[msg.event].forEach(function(cb) {
        try {
          cb(msg.data);
        } catch (err) {
          console.error('Threshold shim: error in listener for ' + msg.event, err);
        }
      });
    }
  };
})();
