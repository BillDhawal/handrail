from __future__ import annotations

import re
from pathlib import Path

STATIC = Path(__file__).parents[3] / "src/handrail/serve/web/static"


def test_api_and_ws_go_through_the_configured_base() -> None:
    cfg = (STATIC / "config.js").read_text()
    app = (STATIC / "app.js").read_text()
    assert "export const API_BASE" in cfg and "export const WS_URL" in cfg
    assert "import { API_BASE, WS_URL } from './config.js'" in app
    assert "fetch(apiUrl(path)" in app and "${API_BASE}${path}" in app
    assert "new WebSocket(WS_URL)" in app
    assert "credentials: 'omit'" in app


def test_no_page_builds_an_api_address_by_hand() -> None:
    bad = []
    for f in sorted((STATIC / "pages").glob("*.js")):
        for n, line in enumerate(f.read_text().splitlines(), 1):
            if re.search(r"['\"`]/api/", line) and not re.search(r"\b(api|apiUrl)\(", line):
                bad.append(f"{f.name}:{n}")
    assert bad == []
