"""Per-tenant presentation config.

Two institutions run the same PLUMBLINE product. Domain logic, routes, roles and
data are shared; only what things are called and how they are marked up differs.
That is exactly the variance a capability overlay has to absorb.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TenantConfig:
    slug: str
    institution: str
    template_dir: str
    frame_menu: str
    frame_work: str
    search_value_field: str
    search_submit_label: str
    member_header: str
    shares_table_class: str
    branches: list[str]


TENANTS: dict[str, TenantConfig] = {
    "quarrybrook": TenantConfig(
        slug="quarrybrook",
        institution="Quarrybrook Credit Union",
        template_dir="quarrybrook",
        frame_menu="menu",
        frame_work="work",
        search_value_field="sval",
        search_submit_label="F5=Search",
        member_header="MEMBER RECORD",
        shares_table_class="grid",
        branches=["QB-01", "QB-02", "QB-03"],
    ),
    "fernhollow": TenantConfig(
        slug="fernhollow",
        institution="Fernhollow Credit Union",
        template_dir="fernhollow",
        frame_menu="sidebar",
        frame_work="main",
        search_value_field="srchval",
        search_submit_label="PF5 Find",
        member_header="MEMBER MASTER",
        shares_table_class="lst",
        branches=["FH-01", "FH-02"],
    ),
}
