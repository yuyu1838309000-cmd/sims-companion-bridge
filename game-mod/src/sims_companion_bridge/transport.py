"""Bounded stdlib-only loopback delivery for read-only game events."""
from __future__ import absolute_import

import json
import queue
import threading
import time
import urllib.error
import urllib.parse
import urllib.request


MAX_EVENT_BYTES = 16 * 1024
LOOPBACK_HOSTS = ("127.0.0.1", "localhost", "::1")
_STOP = object()


class LoopbackTransport(object):
    """Synchronous HTTP primitive; simulation callbacks must use EventWorker."""

    def __init__(self, base_url="http://127.0.0.1:8765", timeout=3.0):
        parsed = urllib.parse.urlsplit(base_url)
        try:
            port = parsed.port
        except ValueError:
            raise ValueError("base_url has an invalid port")
        if (parsed.scheme != "http" or parsed.hostname not in LOOPBACK_HOSTS or
                parsed.username is not None or parsed.password is not None or
                parsed.query or parsed.fragment or parsed.path not in ("", "/") or
                port is None):
            raise ValueError("base_url must be an explicit loopback HTTP origin")
        self.base_url = base_url.rstrip("/")
        self.timeout = max(0.1, min(float(timeout), 10.0))
        self._opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

    def post_event(self, event):
        try:
            body = json.dumps(event, sort_keys=True, separators=(",", ":"),
                              ensure_ascii=False, allow_nan=False).encode("utf-8")
        except (TypeError, ValueError, UnicodeEncodeError, RecursionError):
            return False, {"error": "invalid_event_json"}
        if not body or len(body) > MAX_EVENT_BYTES:
            return False, {"error": "event_size_limit"}
        request = urllib.request.Request(
            self.base_url + "/api/v0.1/game/events", data=body, method="POST"
        )
        request.add_header("Content-Type", "application/json")
        try:
            with self._opener.open(request, timeout=self.timeout) as response:
                raw = response.read().decode("utf-8")
                return True, json.loads(raw) if raw else {}
        except urllib.error.HTTPError as exc:
            try:
                raw = exc.read().decode("utf-8")
                result = json.loads(raw) if raw else {"error": "http_%s" % exc.code}
            except Exception:
                result = {"error": "http_%s" % exc.code}
            finally:
                _close_quietly(exc)
            return False, result
        except Exception as exc:
            return False, {"error": "unreachable", "reason": str(exc)[:160]}


def _close_quietly(value):
    try:
        value.close()
    except Exception:
        pass


class EventWorker(object):
    """Daemon worker that keeps network I/O off the simulation callback thread."""

    def __init__(self, transport, max_queue=100, max_retries=0, retry_delay=0.25):
        self.transport = transport
        self.max_retries = max(0, min(int(max_retries), 1))
        self.retry_delay = max(0.0, min(float(retry_delay), 2.0))
        self._queue = queue.Queue(maxsize=max(1, min(int(max_queue), 100)))
        self._thread = None
        self._stopping = threading.Event()
        self.last_result = None

    def start(self):
        if self._thread is not None and self._thread.is_alive():
            return
        self._stopping.clear()
        self._thread = threading.Thread(target=self._run, name="scb-event-worker")
        self._thread.daemon = True
        self._thread.start()

    def submit(self, event):
        if self._thread is None or not self._thread.is_alive() or self._stopping.is_set():
            return False
        try:
            self._queue.put_nowait(event)
            return True
        except queue.Full:
            return False

    def stop(self, timeout=3.0):
        thread = self._thread
        if thread is None:
            return True
        self._stopping.set()
        try:
            self._queue.put(_STOP, timeout=max(0.0, min(float(timeout), 3.0)))
        except queue.Full:
            return False
        thread.join(max(0.0, min(float(timeout), 10.0)))
        return not thread.is_alive()

    def _run(self):
        while True:
            item = self._queue.get()
            try:
                if item is _STOP:
                    return
                result = self.transport.post_event(item)
                for _attempt in range(self.max_retries):
                    if result[0] or self._stopping.is_set():
                        break
                    time.sleep(self.retry_delay)
                    result = self.transport.post_event(item)
                self.last_result = result
            finally:
                self._queue.task_done()
