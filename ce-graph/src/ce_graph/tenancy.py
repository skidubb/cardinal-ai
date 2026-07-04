"""Tenant model for multi-tenant knowledge graphs.

Each Cardinal Element customer (and CE itself) is a tenant. Each tenant
gets its own FalkorDB graph for strong isolation -- no cross-tenant
queries possible, no risk of data leakage.

Tenant configuration lives at ``ce-graph/tenants/<slug>.yaml``.
"""

from __future__ import annotations

import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


def _find_repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "ce-graph").is_dir():
            return parent
    raise SystemExit(f"Cannot find monorepo root from {here}")


REPO_ROOT = _find_repo_root()
TENANTS_DIR = REPO_ROOT / "ce-graph" / "tenants"

SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]{1,48}[a-z0-9]$")


@dataclass(frozen=True)
class TenantConfig:
    """Configuration for a single tenant.

    The ``slug`` is the canonical identifier -- lowercase, kebab-case.
    The ``graph_name`` is the FalkorDB graph (slug with hyphens swapped
    for underscores).
    """

    slug: str
    display_name: str
    vertical: str | None = None
    description: str | None = None
    primary_contact: str | None = None
    connectors: dict[str, dict[str, Any]] = field(default_factory=dict)
    seeded_protocols: bool = True
    notes: str | None = None

    @property
    def graph_name(self) -> str:
        return self.slug.replace("-", "_")

    @property
    def config_path(self) -> Path:
        return TENANTS_DIR / f"{self.slug}.yaml"

    def enabled_connectors(self) -> list[str]:
        return [
            name
            for name, cfg in self.connectors.items()
            if cfg.get("enabled", True)
        ]


def _parse_yaml(path: Path) -> dict[str, Any]:
    """Parse a tenant config YAML.

    PyYAML is a hard dependency (see pyproject.toml). We don't ship a fallback
    parser because tenant configs mix block and flow styles and a custom parser
    is a footgun.
    """
    import yaml
    return yaml.safe_load(path.read_text()) or {}


def load_tenant(slug: str) -> TenantConfig:
    """Load a tenant config by slug. Raises if not found."""
    if not SLUG_RE.match(slug):
        raise ValueError(f"Invalid tenant slug '{slug}' -- must be lowercase kebab-case")
    path = TENANTS_DIR / f"{slug}.yaml"
    if not path.exists():
        raise FileNotFoundError(
            f"Tenant config not found: {path}\n"
            f"Available: {', '.join(sorted(t.slug for t in list_tenants()))}"
        )
    data = _parse_yaml(path)
    return TenantConfig(
        slug=data.get("slug", slug),
        display_name=data.get("display_name", slug),
        vertical=data.get("vertical"),
        description=data.get("description"),
        primary_contact=data.get("primary_contact"),
        connectors=data.get("connectors", {}) or {},
        seeded_protocols=bool(data.get("seeded_protocols", True)),
        notes=data.get("notes"),
    )


def list_tenants() -> list[TenantConfig]:
    if not TENANTS_DIR.exists():
        return []
    out: list[TenantConfig] = []
    for path in sorted(TENANTS_DIR.glob("*.yaml")):
        try:
            out.append(load_tenant(path.stem))
        except Exception as e:
            print(f"WARN: skipping {path.name}: {e}", file=sys.stderr)
    return out


def current_tenant() -> str:
    """Resolve the active tenant from env var CE_TENANT (default: cardinal-element)."""
    return os.environ.get("CE_TENANT", "cardinal-element")


__all__ = [
    "TenantConfig",
    "TENANTS_DIR",
    "load_tenant",
    "list_tenants",
    "current_tenant",
]
