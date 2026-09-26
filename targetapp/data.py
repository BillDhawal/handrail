"""PLUMBLINE domain model and in-memory store.

State lives in memory and is rebuilt by ``reset()``. A real core cannot be reset;
this exists so evidence runs are repeatable, and the write-up says so.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from datetime import UTC, datetime

# Screen text. These exact strings are what the outcome catalogue detects on, so
# they are defined once here and rendered by the templates.
MSG_SIGNON_REJECTED = "SIGN ON REJECTED - OPERATOR ID OR PASSWORD NOT RECOGNIZED"
MSG_NO_MATCH = "NO MEMBER RECORD MATCHES THAT VALUE"
MSG_NOT_AUTHORIZED = "AUTHORIZATION FAILURE - OPERATOR NOT AUTHORIZED FOR FUNCTION HLD"
MSG_ALREADY_HELD = "SHARE ALREADY UNDER HOLD - NO ACTION TAKEN"
MSG_HOLD_POSTED = "HOLD POSTED"
# Shown to every operator on the review screen, including supervisors who then
# succeed. It must not be mistaken for MSG_NOT_AUTHORIZED.
MSG_RESTRICTED_BANNER = "RESTRICTED FUNCTION - SUPERVISOR AUTHORIZATION REQUIRED"
MSG_SESSION_EXPIRED = "SESSION HAS EXPIRED - SIGN ON REQUIRED"
MSG_MAINTENANCE = "SYSTEM UNAVAILABLE - SCHEDULED MAINTENANCE"
MSG_APP_ERROR = "APPLICATION ERROR - TRANSACTION CODE 0087"
MSG_DIALOG = "NOTICE - ACKNOWLEDGE TO CONTINUE"

REASONS = ["LEGAL", "FRAUD_REVIEW", "MEMBER_REQUEST"]


@dataclass
class Member:
    member_number: str
    last_name: str
    first_name: str
    branch: str

    @property
    def display_name(self) -> str:
        return f"{self.last_name}, {self.first_name}"


@dataclass
class Share:
    share_id: str
    member_number: str
    share_type: str
    balance_cents: int
    status: str

    @property
    def balance_display(self) -> str:
        return f"${self.balance_cents / 100:,.2f}"


@dataclass
class Operator:
    operator_id: str
    password: str
    role: str
    branch: str


@dataclass
class Hold:
    share_id: str
    reason: str
    notes: str
    placed_by: str
    placed_at: str
    confirmation_code: str


def _seed_members() -> list[Member]:
    return [
        Member("400118", "Alvarez", "Marisol", "QB-01"),
        Member("400226", "Okonkwo", "Daniel", "QB-01"),
        Member("400337", "Petrov", "Irina", "QB-02"),
        Member("400445", "Nakamura", "Kenji", "QB-02"),
    ]


def _seed_shares() -> list[Share]:
    return [
        Share("400118-S0001", "400118", "REGULAR", 4_210_050, "ACTIVE"),
        Share("400118-S0005", "400118", "DRAFT", 88_025, "ACTIVE"),
        Share("400226-S0001", "400226", "REGULAR", 1_500_000, "ACTIVE"),
        Share("400226-S0002", "400226", "VACATION", 250_000, "HOLD"),
        Share("400337-S0001", "400337", "REGULAR", 75_000, "ACTIVE"),
        Share("400445-S0001", "400445", "REGULAR", 320_000, "ACTIVE"),
    ]


def _seed_operators() -> list[Operator]:
    return [
        Operator("mrivas", "plumbline-demo", "TELLER", "QB-01"),
        Operator("dcolewell", "plumbline-demo", "SUPERVISOR", "QB-01"),
    ]


@dataclass
class Store:
    members: list[Member] = field(default_factory=list)
    shares: list[Share] = field(default_factory=list)
    operators: list[Operator] = field(default_factory=list)
    holds: list[Hold] = field(default_factory=list)

    def reset(self) -> None:
        self.members = _seed_members()
        self.shares = _seed_shares()
        self.operators = _seed_operators()
        self.holds = []

    def authenticate(self, operator_id: str, password: str) -> Operator | None:
        for op in self.operators:
            if op.operator_id == operator_id and op.password == password:
                return op
        return None

    def find_members(self, search_by: str, value: str) -> list[Member]:
        needle = (value or "").strip().lower()
        if not needle:
            return []
        if search_by == "MBRNO":
            return [m for m in self.members if m.member_number == needle]
        return [m for m in self.members if m.last_name.lower() == needle]

    def get_member(self, member_number: str) -> Member | None:
        return next((m for m in self.members if m.member_number == member_number), None)

    def shares_for(self, member_number: str) -> list[Share]:
        return [s for s in self.shares if s.member_number == member_number]

    def get_share(self, share_id: str) -> Share | None:
        return next((s for s in self.shares if s.share_id == share_id), None)

    def place_hold(
        self, share_id: str, reason: str, notes: str, operator: Operator
    ) -> tuple[str, str]:
        """Attempt to place a hold.

        Role is checked before state deliberately: a teller must be refused for
        authorization, not told the share is already held.
        """
        if operator.role != "SUPERVISOR":
            return "not_authorized", ""
        share = self.get_share(share_id)
        if share is None:
            return "not_authorized", ""
        if share.status == "HOLD":
            return "already_held", ""
        code = f"HX-{random.randint(0, 999_999):06d}"
        share.status = "HOLD"
        self.holds.append(
            Hold(
                share_id=share_id,
                reason=reason,
                notes=notes,
                placed_by=operator.operator_id,
                placed_at=datetime.now(UTC).isoformat(),
                confirmation_code=code,
            )
        )
        return "posted", code
