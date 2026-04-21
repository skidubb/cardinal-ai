"""``cegraph`` CLI -- tenant management + provisioning.

Usage:
    cegraph list                                    # list all tenants
    cegraph status [--tenant SLUG]                  # show graph stats
    cegraph create SLUG --display "Name" [--vertical V]
    cegraph init [--tenant SLUG | --all]            # provision graph + seed protocols
    cegraph drop --tenant SLUG --yes                # delete a tenant's graph (destructive)
    cegraph connectors                              # list registered connectors
"""

from __future__ import annotations

import argparse
import asyncio
import sys

from ce_graph.connectors import REGISTRY
from ce_graph.connectors import hubspot as _hubspot, mcp_marker as _mcp
from ce_graph.falkor_client import FalkorClient
from ce_graph.queries import GraphQueries
from ce_graph.tenancy import TENANTS_DIR, list_tenants, load_tenant

# Register built-in connectors
_hubspot.register(REGISTRY)
_mcp.register(REGISTRY)


def cmd_list(_: argparse.Namespace) -> int:
    tenants = list_tenants()
    if not tenants:
        print("No tenants configured. Add YAML files to", TENANTS_DIR)
        return 0
    print(f"{'SLUG':<28} {'GRAPH':<28} {'VERTICAL':<40} CONNECTORS")
    print("-" * 120)
    for t in tenants:
        cons = ", ".join(t.enabled_connectors()) or "(none enabled)"
        print(f"{t.slug:<28} {t.graph_name:<28} {(t.vertical or '-'):<40} {cons}")
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    targets = [load_tenant(args.tenant)] if args.tenant else list_tenants()
    for t in targets:
        client = FalkorClient(tenant=t)
        try:
            stats = GraphQueries(client).graph_stats()
            populated = {k: v for k, v in stats.items() if v}
            print(f"\n{t.display_name} ({t.slug}) -> graph='{t.graph_name}'")
            if not populated:
                print("  (empty)")
            else:
                for label, count in populated.items():
                    print(f"  {label:<14} {count}")
        except Exception as e:
            print(f"\n{t.display_name} ({t.slug}) -> ERROR: {e}")
    return 0


def cmd_create(args: argparse.Namespace) -> int:
    slug = args.slug
    path = TENANTS_DIR / f"{slug}.yaml"
    if path.exists():
        print(f"Tenant already exists: {path}", file=sys.stderr)
        return 1
    TENANTS_DIR.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"slug: {slug}\n"
        f"display_name: {args.display or slug}\n"
        f"vertical: {args.vertical or 'TBD'}\n"
        f"description: New tenant -- knowledge graph TBD.\n"
        f"primary_contact: TBD\n"
        f"seeded_protocols: true\n"
        f"connectors:\n"
        f"  notion: {{enabled: false, auth: mcp}}\n"
        f"  granola: {{enabled: false, auth: mcp}}\n"
        f"  hubspot: {{enabled: false}}\n"
        f"notes: |\n"
        f"  Onboarding playbook:\n"
        f"  1. Identify their data sources\n"
        f"  2. Provision credentials per connector\n"
        f"  3. Backfill: cegraph backfill --tenant {slug}\n"
    )
    print(f"Created tenant config: {path}")
    print("Next: cegraph init --tenant", slug)
    return 0


async def _init_one(slug: str, seed_protocols: bool) -> None:
    from ce_graph.scripts.seed_protocols import seed as run_seed
    tenant = load_tenant(slug)
    client = FalkorClient(tenant=tenant)
    client.ensure_indexes()
    print(f"  [{slug}] indexes ensured on graph='{tenant.graph_name}'")
    if seed_protocols and tenant.seeded_protocols:
        await run_seed(tenant_slug=slug)


def cmd_init(args: argparse.Namespace) -> int:
    if args.all:
        targets = [t.slug for t in list_tenants()]
    elif args.tenant:
        targets = [args.tenant]
    else:
        print("Specify --tenant SLUG or --all", file=sys.stderr)
        return 1
    for slug in targets:
        print(f"Initialising tenant: {slug}")
        asyncio.run(_init_one(slug, seed_protocols=not args.skip_protocols))
    return 0


CANONICAL_TENANT = "cardinal-element"


def cmd_drop(args: argparse.Namespace) -> int:
    if not args.yes:
        print("Refusing without --yes (this is destructive)", file=sys.stderr)
        return 1
    if args.tenant == CANONICAL_TENANT and not args.i_mean_it:
        print(
            f"Refusing to drop the canonical reference graph '{CANONICAL_TENANT}'.\n"
            f"This graph is shown to every sales prospect. If you really mean it, "
            f"re-run with --i-mean-it.",
            file=sys.stderr,
        )
        return 1
    tenant = load_tenant(args.tenant)
    client = FalkorClient(tenant=tenant)
    client.drop_graph()
    print(f"Dropped graph '{tenant.graph_name}' for tenant {tenant.slug}")
    return 0


def cmd_connectors(_: argparse.Namespace) -> int:
    print("Registered connectors:")
    for name in REGISTRY.list_names():
        cls = REGISTRY.get(name)
        flavour = "MCP-driven (run via ce-graph-backfill agent)" if getattr(cls, "requires_mcp", False) else "Direct API (Python)"
        print(f"  {name:<16} -- {flavour}")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(prog="cegraph", description="ce-graph tenant manager")
    sub = p.add_subparsers(dest="cmd")

    sub.add_parser("list", help="List all tenants").set_defaults(func=cmd_list)

    s_status = sub.add_parser("status", help="Show graph stats per tenant")
    s_status.add_argument("--tenant", help="Specific tenant slug; default: all")
    s_status.set_defaults(func=cmd_status)

    s_create = sub.add_parser("create", help="Create a new tenant config")
    s_create.add_argument("slug")
    s_create.add_argument("--display", help="Display name")
    s_create.add_argument("--vertical", help="Industry vertical")
    s_create.set_defaults(func=cmd_create)

    s_init = sub.add_parser("init", help="Provision a tenant graph (indexes + protocols)")
    s_init.add_argument("--tenant", help="Tenant slug")
    s_init.add_argument("--all", action="store_true", help="Init every tenant")
    s_init.add_argument("--skip-protocols", action="store_true")
    s_init.set_defaults(func=cmd_init)

    s_drop = sub.add_parser("drop", help="Delete a tenant's graph (destructive)")
    s_drop.add_argument("--tenant", required=True)
    s_drop.add_argument("--yes", action="store_true", help="Confirm destruction")
    s_drop.add_argument(
        "--i-mean-it",
        action="store_true",
        help="Required additional flag to drop the canonical cardinal-element reference graph.",
    )
    s_drop.set_defaults(func=cmd_drop)

    sub.add_parser("connectors", help="List registered connectors").set_defaults(func=cmd_connectors)

    args = p.parse_args()
    if not getattr(args, "func", None):
        p.print_help()
        return 1
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
