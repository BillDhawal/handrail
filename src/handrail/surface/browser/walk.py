"""The waiter's notebook: one walk through the dining room, everything written down.

Before the waiter can hand the kitchen a menu, somebody has to walk every
table and note what is there: a form field here, a button there, a greyed-out
switch that should not be offered. This module is that walk. It is one piece
of JavaScript that runs inside a page frame and comes back with a plain list,
one record per control, plus the attribute paths that make up the screen's
structure.

Two things it does that Playwright's own accessibility snapshot does not.
First, a field with no accessible name gets the caption from the cell to its
left, because that is how legacy forms are laid out and that is how the
``label`` rung in ``locators.py`` will find it again. Second, it returns the
structural paths the screen signature is built from: tag, classes and ``name``
attribute for every element on the way down, never text and never a value, so
"HOLD POSTED" and "SHARE ALREADY UNDER HOLD" can still be told apart by the
one class that differs while a different confirmation number cannot.

The signature here is the milestone 2 version: a hash over the set of paths.
Milestone 5 replaces it with the tiered, Stoat-style match the design calls
for; the walk stays the same.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any

from .operations import Control

_HELPERS = r"""
  const FIELD = {text:'textbox', password:'textbox', search:'searchbox', number:'spinbutton',
    email:'textbox', tel:'textbox', url:'textbox', checkbox:'checkbox', radio:'radio',
    submit:'button', button:'button', reset:'button', image:'button'};
  const BLOCK = {table:'table', tr:'row', td:'cell', th:'columnheader', form:'form', ul:'list',
    ol:'list', li:'listitem', dialog:'dialog', nav:'navigation', main:'main', fieldset:'group'};
  const clean = s => (s || '').replace(/\s+/g, ' ').trim();
  const roleOf = el => {
    const explicit = el.getAttribute('role'); if (explicit) return explicit;
    const tag = el.tagName.toLowerCase();
    if (tag === 'input') { const t = (el.getAttribute('type') || 'text').toLowerCase();
      return t === 'hidden' ? null : (FIELD[t] || 'textbox'); }
    if (tag === 'select') return 'combobox';
    if (tag === 'textarea') return 'textbox';
    if (tag === 'button') return 'button';
    if (tag === 'a') return el.hasAttribute('href') ? 'link' : null;
    if (/^h[1-6]$/.test(tag)) return 'heading';
    return null;
  };
  const nameOf = (el, role) => {
    const aria = el.getAttribute('aria-label'); if (aria) return clean(aria);
    if (el.id) { const l = document.querySelector('label[for="' + CSS.escape(el.id) + '"]');
      if (l) return clean(l.textContent); }
    const wrap = el.closest('label'); if (wrap) return clean(wrap.textContent);
    const tag = el.tagName.toLowerCase();
    if (tag === 'input' && role === 'button') return clean(el.value) || 'Submit';
    if (tag === 'button' || tag === 'a' || role === 'heading') return clean(el.textContent);
    return clean(el.getAttribute('title') || el.getAttribute('placeholder') || '');
  };
  const captionOf = el => {
    const cell = el.closest('td,th'); const prev = cell && cell.previousElementSibling;
    return prev ? clean(prev.textContent) : '';
  };
  const pathOf = el => { const parts = [];
    for (let n = el; n && n !== document.body; n = n.parentElement) {
      let p = n.tagName.toLowerCase();
      if (n.classList.length) p += '.' + [...n.classList].sort().join('.');
      if (typeof n.name === 'string' && n.name) p += '[' + n.name + ']';
      parts.unshift(p); }
    return parts.join('/'); };
  const selectorOf = el => { const parts = [];
    for (let n = el; n && n.nodeType === 1 && n !== document.documentElement; n = n.parentElement) {
      let i = 1; for (let s = n.previousElementSibling; s; s = s.previousElementSibling) i++;
      parts.unshift(n.tagName.toLowerCase() + ':nth-child(' + i + ')'); }
    return parts.join(' > '); };
  const ancestorsOf = el => { const r = [];
    for (let n = el.parentElement; n && n !== document.body; n = n.parentElement) {
      const x = roleOf(n) || BLOCK[n.tagName.toLowerCase()]; if (x) r.unshift(x); }
    return r; };
  const visible = el => { const r = el.getBoundingClientRect(); const cs = getComputedStyle(el);
    return r.width > 0 && r.height > 0 && cs.visibility !== 'hidden' && cs.display !== 'none'; };
  const describe = (el, role) => ({ role, name: nameOf(el, role),
    label: ['button', 'link', 'heading'].includes(role) ? '' : captionOf(el),
    attr_name: el.getAttribute('name') || '', test_id: el.getAttribute('data-testid') || '',
    ancestors: ancestorsOf(el), disabled: !!el.disabled, readonly: !!el.readOnly,
    visible: visible(el), selector: selectorOf(el) });
"""

#: Runs in a frame: every control, and every structural path.
WALK_JS = (
    "() => {"
    + _HELPERS
    + """
  const controls = [], structure = [];
  if (!document.body) return { controls, structure };
  for (const el of document.body.querySelectorAll('*')) {
    const role = roleOf(el);
    if (role || el.classList.length) structure.push(pathOf(el));
    if (role) controls.push(describe(el, role));
  }
  return { controls, structure: [...new Set(structure)].sort() };
}"""
)

#: Runs on one element: the same record the walk would have written for it.
DESCRIBE_JS = "(el) => {" + _HELPERS + " return describe(el, roleOf(el) || 'generic'); }"


@dataclass(frozen=True)
class Handle:
    """Where a control was seen: which frame, and a CSS path valid until the page changes."""

    frame: str
    selector: str


def control_from(frame: str, raw: dict[str, Any]) -> Control:
    """One JavaScript record into the surface-neutral shape the menu is built from."""
    return Control(
        role=str(raw["role"]),
        name=str(raw["name"]),
        label=str(raw["label"]),
        attr_name=str(raw["attr_name"]),
        test_id=str(raw["test_id"]),
        scope=(frame,) if frame else (),
        ancestors=tuple(str(a) for a in raw["ancestors"]),
        disabled=bool(raw["disabled"]),
        readonly=bool(raw["readonly"]),
        visible=bool(raw["visible"]),
        handle=Handle(frame, str(raw["selector"])),
    )


def signature_of(frames: list[tuple[str, list[str]]]) -> str:
    """The screen's structural hash: every frame's paths, as a set, order-free."""
    lines = sorted({f"{name}:{path}" for name, paths in frames for path in paths})
    digest = hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest()
    return "sha256:" + digest[:16]
