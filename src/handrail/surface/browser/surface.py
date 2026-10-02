"""The browser waiter: Playwright behind the six verbs, and nothing else.

A waiter in a real restaurant does the same six things the pretend one did in
``null_surface.py``: walk to a table, report what is on it, find one item,
act on it, answer a yes/no question without going anywhere, take a photo. The
difference is that this one walks into a real room: a Chromium page, with
frames, forms and whatever the application decided to do today.

The engine never sees Playwright. It gets an ``Observation``, a ``Resolution``
whose handle it never opens, and typed refusals. ``evaluate`` never waits, by
contract: the engine does the polling, so the surface answers what is true at
this instant. ``resolve`` is allowed to wait, because a control that is still
loading is not yet missing.

Secrets never pass through here except as the value typed into a field, and
nothing here logs. Masking is the recorder's job; the surface just does not
write anything down.

The allowlist is enforced twice: ``open`` refuses an entry outside it, and a
route handler drops every request to any other host, so a page that tries to
wander off cannot.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any, cast
from urllib.parse import urlparse

from playwright.async_api import (
    Browser,
    Frame,
    Locator,
    Page,
    Playwright,
    async_playwright,
)
from playwright.async_api import TimeoutError as PlaywrightTimeoutError

from ...schema.errors import ErrorCode, HandrailError
from ...schema.target import ScopeStep, Target, Verb
from ..base import ActResult, EvidenceBundle, Observation, Resolution
from .fingerprint import same_control
from .locators import query_for
from .operations import build_table
from .queries import Root, to_locator
from .walk import DESCRIBE_JS, WALK_JS, control_from, signature_of

POLL_S = 0.2
#: How long a click gets to start a navigation before we decide it did not.
NAVIGATION_GRACE_MS = 1500


class BrowserSurface:
    kind = "browser"

    def __init__(self, allowed_hosts: list[str], headless: bool = True) -> None:
        self.allowed_hosts = set(allowed_hosts)
        self.headless = headless
        self._pw: Playwright | None = None
        self._browser: Browser | None = None
        self._page: Page | None = None
        self.dialogs: list[str] = []

    @property
    def page(self) -> Page:
        if self._page is None:
            raise HandrailError("the browser is not open", ErrorCode.APPLICATION_ERROR)
        return self._page

    # -- the six verbs ----------------------------------------------------------

    async def open(self, entry: str) -> None:
        host = urlparse(entry).netloc
        if host not in self.allowed_hosts:
            raise HandrailError(f"{host!r} is not an allowed host", ErrorCode.POLICY_VIOLATION)
        if self._page is None:
            self._pw = await async_playwright().start()
            self._browser = await self._pw.chromium.launch(headless=self.headless)
            context = await self._browser.new_context()
            await context.route("**/*", self._gate)
            self._page = await context.new_page()
            self._page.on("dialog", self._on_dialog)
        await self.page.goto(entry, wait_until="load")

    async def observe(self) -> Observation:
        controls, frames, texts = [], [], []
        for frame in self.page.frames:
            seen = await self._walk(frame)
            controls += [control_from(frame.name, raw) for raw in seen["controls"]]
            frames.append((frame.name, list(seen["structure"])))
            texts.append(await self._text_of(frame))
        return Observation(
            text="\n".join(t for t in texts if t),
            operations=build_table(controls),
            structure=(signature_of(frames),),
        )

    async def resolve(self, target: Target, timeout_ms: int) -> Resolution:
        name = (target.name.eq or target.name.matches or "") if target.name else ""
        regex = bool(target.name and target.name.matches)
        deadline = time.monotonic() + timeout_ms / 1000
        while True:
            for rung in target.ladder:  # cheapest first, by the schema
                try:
                    query = query_for(rung, target.role, name, regex)
                except ValueError:
                    continue  # a rung meant for another surface
                for frame, root in self._roots(target.scope):
                    locator = to_locator(root, query)
                    count = await locator.count()
                    if count > 1:
                        raise HandrailError(
                            f"{rung.rung} finds {count} controls for {target.role} {name!r}",
                            ErrorCode.AMBIGUOUS_CONTROL,
                        )
                    if count == 1:
                        await self._check_fingerprint(target, frame, locator)
                        return Resolution(handle=locator, rung=rung.rung, rung_cost=rung.cost)
            if time.monotonic() >= deadline:
                raise HandrailError(
                    f"no rung finds {target.role} {name!r}", ErrorCode.MISSING_CONTROL
                )
            await asyncio.sleep(POLL_S)

    async def act(self, resolution: Resolution | None, verb: Verb, value: str | None) -> ActResult:
        locator = cast(Locator | None, resolution.handle if resolution else None)
        if verb == "press_key":
            await self.page.keyboard.press(value or "Enter")
        elif verb == "wait":
            await asyncio.sleep(int(value or "0") / 1000)
        elif verb == "scroll":
            await self.page.mouse.wheel(0, int(value or "400"))
        elif locator is None:
            raise HandrailError(f"{verb} needs a control", ErrorCode.MISSING_CONTROL)
        elif verb == "invoke" or verb == "toggle":
            await self._click_and_settle(locator)
        elif verb == "set_value":
            await locator.fill(value or "")
        elif verb == "select":
            await locator.select_option(label=value)
        elif verb == "read":
            return ActResult(ok=True, value=(await locator.inner_text()).strip())
        return ActResult(ok=True)

    async def evaluate(self, condition: str) -> bool:
        kind, _, arg = condition.partition(":")
        if kind == "screen_is":
            return await self._signature() == arg
        if kind == "target_present":
            for frame in self.page.frames:
                by_text = frame.get_by_text(arg, exact=True)
                by_attr = frame.locator(f'[value="{arg}"], [name="{arg}"]')
                if await by_text.count() or await by_attr.count():
                    return True
            return False
        return kind == "keyboard_unlocked"

    async def evidence(self) -> EvidenceBundle:
        texts = [await self._text_of(f) for f in self.page.frames]
        png = await self.page.screenshot(full_page=True)
        return EvidenceBundle(text="\n".join(t for t in texts if t), screenshot_png=png)

    async def close(self) -> None:
        if self._browser is not None:
            await self._browser.close()
        if self._pw is not None:
            await self._pw.stop()
        self._pw = self._browser = self._page = None

    # -- helpers ------------------------------------------------------------------

    async def _click_and_settle(self, locator: Locator) -> None:
        """Click, and if that navigated any frame, let the new document load first.

        A click on a submit button in a frameset navigates one child frame, and
        the old document stays visible until the new one commits. Asking "which
        screen is this" in that gap gets the old answer. So: click, give any
        frame a moment to start navigating, and wait for it to finish. A click
        that navigates nothing (a checkbox, a script button) just pays the wait.
        """
        try:
            async with self.page.expect_event("framenavigated", timeout=NAVIGATION_GRACE_MS) as ev:
                await locator.click()
            frame = await ev.value
            await frame.wait_for_load_state("load")
            await self.page.wait_for_load_state("load")
        except PlaywrightTimeoutError:
            pass  # no navigation followed the click; nothing to wait for

    def _roots(self, scope: list[ScopeStep]) -> list[tuple[Frame, Root]]:
        """Where to look: the named frame, narrowed to any container the scope names."""
        frames = [s.name for s in scope if s.role == "frame" and s.name]
        chosen = [f for f in self.page.frames if not frames or f.name == frames[-1]]
        roots: list[tuple[Frame, Root]] = []
        for frame in chosen:
            root: Root = frame
            for step in scope:
                if step.role != "frame":
                    inner = root.get_by_role(cast(Any, step.role))
                    root = inner.filter(has_text=step.name) if step.name else inner
            roots.append((frame, root))
        return roots

    async def _check_fingerprint(self, target: Target, frame: Frame, locator: Locator) -> None:
        if target.fingerprint is None:
            return
        control = control_from(frame.name, await locator.evaluate(DESCRIBE_JS))
        if not same_control(target.fingerprint, control):
            raise HandrailError(
                f"the control found for {target.role} is not the one that was recorded",
                ErrorCode.TARGET_MISMATCH,
            )

    async def _walk(self, frame: Frame) -> dict[str, Any]:
        try:
            return cast(dict[str, Any], await frame.evaluate(WALK_JS))
        except Exception:  # noqa: BLE001 - a frame mid-navigation has no document to walk yet
            return {"controls": [], "structure": []}

    async def _signature(self) -> str:
        frames = []
        for frame in self.page.frames:
            frames.append((frame.name, list((await self._walk(frame))["structure"])))
        return signature_of(frames)

    async def _text_of(self, frame: Frame) -> str:
        js = "() => document.body && document.body.innerText ? document.body.innerText : ''"
        try:
            text = str(await frame.evaluate(js))
        except Exception:  # noqa: BLE001 - same: not there yet is not a failure
            return ""
        return f"[frame {frame.name or 'top'}]\n{text}" if text.strip() else ""

    async def _gate(self, route: Any, request: Any) -> None:
        if urlparse(request.url).netloc in self.allowed_hosts:
            await route.continue_()
        else:
            await route.abort()

    def _on_dialog(self, dialog: Any) -> None:
        self.dialogs.append(str(dialog.message))
        asyncio.ensure_future(dialog.dismiss())
