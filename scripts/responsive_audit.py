"""Check every signed-in screen for horizontal overflow at a narrow width.

Constitution rule XI says no screen scrolls horizontally at 375px. That is
easy to break and impossible to notice on a 1440px monitor, so this checks it
directly: it drives headless Chrome over the DevTools protocol, signs in the
way the app does, visits each route, and reports any element whose box crosses
the right edge of the viewport.

    .venv/Scripts/python scripts/responsive_audit.py            # 375px
    .venv/Scripts/python scripts/responsive_audit.py --width 320

Both servers must already be running. Exits non-zero if any route overflows,
so it can gate a change.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

CHROME = Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe")
FRONTEND = "http://localhost:5173"
BACKEND = "http://localhost:8000"
DEBUG_PORT = 9222

ROUTES = [
    ("/login", "Login"),
    ("/overview", "Command centre"),
    ("/data", "Data Studio"),
    ("/ask", "Ask DineAstra"),
    ("/banquets", "Events & banquets"),
    ("/proof", "Daily proof"),
    ("/brain", "Operating brain"),
    ("/connections", "Connections"),
]

# The one probe that runs in the page. Returns the elements sticking out past
# the right edge, ignoring anything deliberately scrollable -- a wide table in
# its own overflow-x container is allowed, the page itself is not.
PROBE = """
(() => {
  const de = document.documentElement;
  const limit = de.clientWidth + 1;
  // An ancestor that clips or scrolls its own overflow has already dealt with
  // the element: a wide table in an overflow-x container is fine, and so is a
  // decorative shape clipped by overflow:hidden. Only what escapes to the page
  // counts against the rule.
  const contained = (el) => {
    for (let node = el.parentElement; node && node !== document.body; node = node.parentElement) {
      const overflowX = getComputedStyle(node).overflowX;
      if (overflowX === 'auto' || overflowX === 'scroll' || overflowX === 'hidden') return true;
    }
    return false;
  };
  const offenders = [...document.querySelectorAll('body *')]
    .filter((el) => {
      const box = el.getBoundingClientRect();
      if (box.width === 0 || box.height === 0) return false;
      if (getComputedStyle(el).position === 'fixed') return false;
      return box.right > limit && !contained(el);
    })
    .map((el) => ({
      tag: el.tagName.toLowerCase(),
      cls: (el.getAttribute('class') || '').split(' ')[0],
      right: Math.round(el.getBoundingClientRect().right),
    }));
  const seen = new Set();
  const unique = offenders.filter((o) => {
    const id = o.tag + '.' + o.cls;
    if (seen.has(id)) return false;
    seen.add(id);
    return true;
  });
  // A route that never loaded has no wide elements and would otherwise
  // pass. Report whether React actually mounted, so an unreachable dev
  // server fails the audit instead of clearing it.
  const root = document.getElementById('root');
  return JSON.stringify({
    mounted: Boolean(root && root.firstElementChild),
    url: location.href,
    viewport: de.clientWidth,
    scrollWidth: de.scrollWidth,
    overflows: de.scrollWidth > de.clientWidth,
    offenders: unique.slice(0, 8),
  });
})()
"""


def _login_token() -> str:
    request = urllib.request.Request(
        f"{BACKEND}/api/auth/login",
        data=json.dumps({"email": "owner@dineastra.demo", "password": "dineastra"}).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=10) as response:
        payload = json.load(response)
    return json.dumps({"token": payload["token"], "user": payload["user"]})


def _start_chrome(width: int, height: int, profile: Path) -> subprocess.Popen:
    process = subprocess.Popen(
        [
            str(CHROME),
            "--headless=new",
            "--disable-gpu",
            f"--remote-debugging-port={DEBUG_PORT}",
            f"--window-size={width},{height}",
            f"--user-data-dir={profile}",
            "--no-first-run",
            "--no-default-browser-check",
            "about:blank",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    for _ in range(60):
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{DEBUG_PORT}/json/version", timeout=1):
                return process
        except (urllib.error.URLError, ConnectionError, OSError):
            time.sleep(0.5)
    process.terminate()
    raise SystemExit("headless Chrome did not start")


def _page_target() -> str:
    with urllib.request.urlopen(f"http://127.0.0.1:{DEBUG_PORT}/json", timeout=5) as response:
        targets = json.load(response)
    for target in targets:
        if target.get("type") == "page":
            return target["webSocketDebuggerUrl"]
    raise SystemExit("no page target in headless Chrome")


async def _audit(width: int, height: int) -> int:
    import websockets

    session = _login_token()
    # Chrome holds cache files briefly after terminate(), and Windows will
    # not delete a file still open, so cleanup errors are not failures here.
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as profile:
        chrome = _start_chrome(width, height, Path(profile))
        try:
            async with websockets.connect(_page_target(), max_size=None) as socket:
                counter = 0

                async def send(method: str, params: dict | None = None):
                    nonlocal counter
                    counter += 1
                    await socket.send(
                        json.dumps({"id": counter, "method": method, "params": params or {}})
                    )
                    while True:
                        message = json.loads(await socket.recv())
                        if message.get("id") == counter:
                            return message

                await send("Page.enable")
                await send(
                    "Emulation.setDeviceMetricsOverride",
                    {"width": width, "height": height, "deviceScaleFactor": 1, "mobile": True},
                )

                # Seed the session the way the app's own login does, so the
                # signed-in routes render instead of redirecting.
                await send("Page.navigate", {"url": f"{FRONTEND}/login"})
                await asyncio.sleep(2.0)
                stored = json.loads(session)
                await send(
                    "Runtime.evaluate",
                    {
                        "expression": (
                            "localStorage.setItem('dineastra.token', "
                            + json.dumps(stored["token"])
                            + "); localStorage.setItem('dineastra.user', "
                            + json.dumps(json.dumps(stored["user"]))
                            + "); 'ok'"
                        )
                    },
                )

                failures = 0
                print(f"Horizontal overflow audit at {width}px\n")
                for path, label in ROUTES:
                    await send("Page.navigate", {"url": FRONTEND + path})
                    await asyncio.sleep(2.2)
                    reply = await send(
                        "Runtime.evaluate", {"expression": PROBE, "returnByValue": True}
                    )
                    raw = reply["result"]["result"].get("value")
                    if raw is None:
                        print(f"  ????  {label:20} probe returned nothing")
                        failures += 1
                        continue
                    data = json.loads(raw)
                    if not data.get("mounted"):
                        failures += 1
                        print(
                            f"  FAIL  {label:20} app did not render at "
                            f"{data.get('url', FRONTEND + path)}"
                        )
                        continue
                    if data["overflows"] or data["offenders"]:
                        failures += 1
                        print(
                            f"  FAIL  {label:20} scrollWidth {data['scrollWidth']} "
                            f"> viewport {data['viewport']}"
                        )
                        for offender in data["offenders"]:
                            print(
                                f"           {offender['tag']}.{offender['cls']} "
                                f"reaches {offender['right']}px"
                            )
                    else:
                        print(f"  PASS  {label:20} fits {data['viewport']}px")

                print()
                print("No screen scrolls horizontally." if not failures
                      else f"{failures} route(s) failed at {width}px.")
                return 1 if failures else 0
        finally:
            chrome.terminate()
            try:
                chrome.wait(timeout=10)
            except subprocess.TimeoutExpired:
                chrome.kill()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--width", type=int, default=375)
    parser.add_argument("--height", type=int, default=900)
    args = parser.parse_args()
    if not CHROME.exists():
        raise SystemExit(f"Chrome not found at {CHROME}")
    sys.exit(asyncio.run(_audit(args.width, args.height)))


if __name__ == "__main__":
    main()
