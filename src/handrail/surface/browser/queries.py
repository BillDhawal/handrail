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

from playwright.async_api import Frame, Locator

from .locators import Query

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
    """The street, for `locators.surviving`: one frame of the live page."""

    def __init__(self, frame: Frame) -> None:
        self.frame = frame

    async def count(self, query: Query) -> int:
        return await to_locator(self.frame, query).count()

    async def is_same(self, query: Query, handle: Any) -> bool:
        js = "(el, sel) => el === document.querySelector(sel)"
        return bool(await to_locator(self.frame, query).first.evaluate(js, handle.selector))
