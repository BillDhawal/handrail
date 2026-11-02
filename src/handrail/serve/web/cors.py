"""The guest list at the door.

When the page is served from one building and the API lives in another, the browser
asks the API "do you accept visitors from that address?" before it lets the page talk.
This module writes the guest list: only the origins named with --cors, no cookies.
"""

from __future__ import annotations

import argparse

from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware


def cors_middleware(origins: list[str]) -> Middleware:
    return Middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["content-type"],
        allow_credentials=False,
    )


def cors_origins(args: argparse.Namespace) -> list[str]:
    return [o.rstrip("/") for o in (getattr(args, "cors", None) or [])]
