"""Seed all 55 Protocol nodes from the orchestration codebase.

Reads ``CE - Multi-Agent Orchestration/protocols/p*/`` directories and
upserts a Protocol node per protocol with code, name, category, and
methodology metadata.

Usage:
    python -m ce_graph.scripts.seed_protocols

Idempotent: safe to re-run.
"""

from __future__ import annotations

import asyncio
import re
import sys
from pathlib import Path

from ce_graph.falkor_client import FalkorClient
from ce_graph.tenancy import current_tenant, load_tenant

def _find_repo_root() -> Path:
    """Walk up from this file looking for the monorepo root sentinel."""
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "CE - Multi-Agent Orchestration").is_dir():
            return parent
    raise SystemExit(f"Could not find monorepo root from {here}")


REPO_ROOT = _find_repo_root()
PROTOCOLS_DIR = REPO_ROOT / "CE - Multi-Agent Orchestration" / "protocols"

# Manual category map -- the protocol dir names alone don't tell us category.
# Source: project CLAUDE.md taxonomy.
CATEGORY_MAP: dict[str, str] = {
    # Routing / triage
    "p0a": "routing", "p0b": "routing", "p0c": "routing", "p44": "routing",
    # Debate & synthesis
    "p03": "debate", "p04": "debate", "p14": "debate",
    # Adversarial
    "p16": "adversarial", "p17": "adversarial", "p38": "adversarial", "p39": "adversarial",
    # Decomposition
    "p06": "decomposition", "p22": "decomposition", "p36": "decomposition",
    "p33": "decomposition", "p34": "decomposition",
    # Sense-making / domain
    "p23": "sense_making", "p24": "sense_making", "p25": "sense_making",
    "p18": "sense_making", "p07": "sense_making",
    # Forecasting
    "p32": "forecasting",
    # Prioritization / weighting
    "p05": "prioritization", "p08": "prioritization", "p20": "prioritization",
    "p29": "prioritization", "p35": "prioritization", "p41": "prioritization",
    "p45": "prioritization",
    # Estimation / negotiation
    "p19": "estimation", "p21": "estimation",
    # Generation / divergent
    "p26": "generation", "p27": "generation", "p28": "generation",
    "p30": "generation", "p46": "generation",
    # Liberating Structures
    "p09": "liberating_structures", "p10": "liberating_structures",
    "p11": "liberating_structures", "p12": "liberating_structures",
    "p13": "liberating_structures", "p15": "liberating_structures",
    # Philosophical / meta
    "p31": "meta", "p37": "meta", "p42": "meta", "p43": "meta",
    "p47": "meta", "p48": "meta",
    # Walks
    "p49": "walk", "p50": "walk", "p51": "walk", "p52": "walk",
    # Boyd OODA
    "p40": "sense_making",
}


def _humanize(slug: str) -> str:
    """Turn 'p04_multi_round_debate' -> 'Multi-Round Debate'."""
    parts = slug.split("_")[1:]  # drop the pNN prefix
    return " ".join(p.capitalize() for p in parts).replace("Triz", "TRIZ").replace("Ach", "ACH").replace("Ooda", "OODA").replace("Pmi", "PMI")


def discover_protocols() -> list[dict[str, str]]:
    if not PROTOCOLS_DIR.exists():
        raise SystemExit(f"Protocols dir not found: {PROTOCOLS_DIR}")
    out: list[dict[str, str]] = []
    for d in sorted(PROTOCOLS_DIR.iterdir()):
        if not d.is_dir() or not re.match(r"^p[0-9a-z]+_", d.name):
            continue
        code = d.name.split("_", 1)[0].upper()
        out.append(
            {
                "code": code,
                "slug": d.name,
                "name": _humanize(d.name),
                "category": CATEGORY_MAP.get(code.lower(), "other"),
            }
        )
    return out


async def seed(tenant_slug: str | None = None) -> int:
    tenant = load_tenant(tenant_slug or current_tenant())
    client = FalkorClient(tenant=tenant)
    client.ensure_indexes()

    protocols = discover_protocols()
    print(f"[{tenant.slug}] Discovered {len(protocols)} protocols")

    for p in protocols:
        client.query(
            """
            MERGE (n:Protocol {code: $code})
            SET n.name = $name,
                n.category = $category,
                n.slug = $slug
            """,
            {
                "code": p["code"],
                "name": p["name"],
                "category": p["category"],
                "slug": p["slug"],
            },
        )

    result = client.query("MATCH (n:Protocol) RETURN count(n) AS n")
    count = int(result.result_set[0][0])
    print(f"[{tenant.slug}] OK -- {count} Protocol nodes in graph '{client.graph_name}'")
    return 0


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--tenant", help="Tenant slug (default: $CE_TENANT or cardinal-element)")
    args = ap.parse_args()
    sys.exit(asyncio.run(seed(tenant_slug=args.tenant)))
