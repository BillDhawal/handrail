"""Asking the page a question in Playwright's own words.

``locators.py`` writes a ``Query``: "by role button named F5=Sign On", "by this
CSS". It deliberately knows nothing about Playwright, so its tests run without
a browser. This module is the translator: one function turns a ``Query`` into
a Playwright locator, and one small class lets ``locators.surviving`` walk a
real frame. Both the probe at authoring time and the resolve at replay time
come through here, so they ask the page the identical question.
"""

from __future__ import annotations

import re
from typing import Any, cast

from playwright.async_api import Frame, Locator, Page

from ...schema.errors import ErrorCode, HandrailError
from .locators import Query
from .operations import Control
from .walk import DESCRIBE_JS, Handle, control_from

#: Where a question may be asked: a whole frame, or a container inside one.
Root = Frame | Locator


def to_locator(frame: Root, query: Query) -> Locator:
    """A `Query` into Playwright's own question. The one place this translation lives."""
    if query.how == "test_id":
        return frame.get_by_test_id(query.value)
    if query.how == "role":
        name: str | re.Pattern[str] = re.compile(query.name) if query.regex else query.name
        return frame.get_by_role(cast(Any, query.role), name=name, exact=not query.regex)
    if query.how == "text":
        return frame.get_by_text(query.value, exact=True)
    return frame.locator(query.value)


class FrameProbe:
    """The street, for `locators.surviving`: one frame, or one row inside it."""

    def __init__(self, frame: Root) -> None:
        self.frame = frame

    async def count(self, query: Query) -> int:
        return await to_locator(self.frame, query).count()

    async def is_same(self, query: Query, handle: Any) -> bool:
        js = "(el, sel) => el === document.querySelector(sel)"
        return bool(await to_locator(self.frame, query).first.evaluate(js, handle.selector))


class BrowserAuthoring:
    """For authoring only: a menu row back into something the ladder can probe."""

    def __init__(self, page: Page) -> None:
        self.page = page

    async def describe(self, handle: Handle) -> Control:
        """The control behind a menu row, as `walk.py` would have written it."""
        frame = self._frame_named(handle.frame)
        return control_from(frame.name, await frame.locator(handle.selector).evaluate(DESCRIBE_JS))

    def probe(self, handle: Handle, control: Control) -> FrameProbe:
        """The street the control lives on: its frame, narrowed to its table row if it has one.

        This mirrors how replay will look: a target scoped to the row named by the
        control's first cell. Probing inside the row is what lets "Hold" survive on a
        page with one Hold link per share.
        """
        frame = self._frame_named(handle.frame)
        root: Root = frame
        if control.row:
            root = frame.get_by_role("row").filter(has_text=control.row)
        return FrameProbe(root)

    def _frame_named(self, name: str) -> Frame:
        for frame in self.page.frames:
            if frame.name == name:
                return frame
        raise HandrailError(f"no frame named {name!r} is open", ErrorCode.MISSING_CONTROL)
