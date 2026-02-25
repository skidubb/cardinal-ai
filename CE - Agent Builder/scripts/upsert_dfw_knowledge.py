#!/usr/bin/env python3
"""Upsert DFW Master Package data to Pinecone ce-gtm-knowledge index, airport-5g namespace.

Usage:
    python scripts/upsert_dfw_knowledge.py

Requires PINECONE_API_KEY and PINECONE_INDEX_HOST in .env
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv

load_dotenv()

NAMESPACE = "airport-5g"

# DFW Master Package content — chunked by topic with metadata
DFW_CHUNKS = [
    # Campus facts
    {
        "_id": "dfw-campus-overview",
        "text": (
            "DFW International Airport is a 27-square-mile campus serving 87 million "
            "passengers annually. It is the 3rd busiest airport in the world by aircraft "
            "movements and 2nd busiest in the US by passenger traffic. The campus includes "
            "5 terminals (A, B, C, D, E), 168+ gates, and extensive cargo facilities. "
            "DFW Forward is a $12 billion capital improvement plan that includes Terminal F "
            "($4B, 31 new gates, opening 2027+), Terminal C rebuild ($3B through 2028), "
            "and new cargo warehouse construction."
        ),
        "source_file": "dfw-master-package",
        "source_folder": "airport-5g",
        "scope": "strategic",
        "constituency": "all",
    },
    # AT&T CWP
    {
        "_id": "dfw-att-cwp-specs",
        "text": (
            "AT&T Connected Workplace Partnership (CWP) at DFW: $10M invested in private "
            "5G infrastructure. 1000 access points (800 upgraded + 200 new) providing "
            "outdoor campus CBRS coverage on 3.5-3.7 GHz spectrum. Integrated with "
            "Federated Wireless SAS (Spectrum Access System) managing 340K+ APs globally. "
            "CBRS 2.0 improvements have reduced DoD interference suspensions by 85%. "
            "Currently serving 800-900 iPad users for ramp operations. Jason Inskeep is "
            "AT&T's primary engagement lead for the DFW partnership."
        ),
        "source_file": "dfw-master-package",
        "source_folder": "airport-5g",
        "scope": "technical",
        "constituency": "cio",
    },
    # Spectrum architecture
    {
        "_id": "dfw-cbrs-spectrum",
        "text": (
            "CBRS (Citizens Broadband Radio Service) operates in the 3.5-3.7 GHz band "
            "with three-tier sharing: Tier 1 (Incumbent/DoD — priority), Tier 2 (PAL — "
            "licensed via auction), Tier 3 (GAA — General Authorized Access, shared). "
            "DFW operates on GAA spectrum managed through Federated Wireless SAS. CBRS 2.0 "
            "protocol improvements have dramatically reduced DoD Dynamic Protection Area "
            "suspensions (85% reduction), making GAA spectrum much more reliable for "
            "mission-critical airport operations. FCC Part 96 compliance is mandatory."
        ),
        "source_file": "dfw-master-package",
        "source_folder": "airport-5g",
        "scope": "technical",
        "constituency": "all",
    },
    # Infrastructure costs
    {
        "_id": "dfw-infrastructure-costs",
        "text": (
            "DFW private 5G infrastructure cost estimates: $5M-$21M total investment for "
            "1550-2500 access points to achieve comprehensive campus coverage (indoor + "
            "outdoor). Per-AP costs range from $2,000-$5,000 depending on indoor vs outdoor "
            "and density requirements. Warehouse/cargo facilities require highest density "
            "(sub-100ms latency for automation). Terminal indoor coverage requires medium "
            "density. Outdoor campus coverage (existing) requires lowest density. Retrofit "
            "costs are 3-5x higher than design-in for new construction."
        ),
        "source_file": "dfw-master-package",
        "source_folder": "airport-5g",
        "scope": "financial",
        "constituency": "cio",
    },
    # Revenue model
    {
        "_id": "dfw-revenue-model",
        "text": (
            "DFW Private 5G 3-Stream Revenue Model — $80M+ 5-year net value projection:\n"
            "Stream 1 — Operational Savings (Year 1): $2.5-11M from network consolidation, "
            "reduced Wi-Fi costs, automated operations\n"
            "Stream 2 — Tenant Monetization (Year 2+): $3.5-14M from connectivity-as-a-service "
            "to airlines, concessions, cargo operators. Tiered pricing (basic/premium/enterprise)\n"
            "Stream 3 — Data & Experience (Year 3+): $4.5-16M from location analytics, "
            "advertising ($30-100 CPM on 87M captive audience), premium passenger services, "
            "IoT data marketplace"
        ),
        "source_file": "dfw-master-package",
        "source_folder": "airport-5g",
        "scope": "financial",
        "constituency": "cro",
    },
    # Airline operations
    {
        "_id": "dfw-airline-operations",
        "text": (
            "Anchor airline controls 80%+ of DFW departures (700+ daily). Operates "
            "Terminals A, B, C exclusively with 168+ gates. Terminal F will add 31 gates "
            "($4B investment, opening 2027+). Terminal C undergoing $3B rebuild through "
            "2028. Currently 800-900 iPad users on CBRS outdoor coverage for ramp "
            "operations including baggage tracking, crew communications, and flight "
            "operations analytics. Mission-critical requirement: 99.99% uptime SLA "
            "(4.3 minutes downtime/month max). Every minute of delayed pushback costs "
            "$74+ in direct operating costs. Airline demands dedicated network slice "
            "for operations — not shared with passenger/tenant traffic."
        ),
        "source_file": "dfw-master-package",
        "source_folder": "airport-5g",
        "scope": "operational",
        "constituency": "airline",
    },
    # Cargo operations
    {
        "_id": "dfw-cargo-operations",
        "text": (
            "DFW is the 3rd-largest cargo hub in the US with $20B+ annual economic "
            "impact to North Texas. 2M+ sq ft dedicated cargo facilities operated by "
            "Menzies Aviation, dnata, FedEx, UPS, American Cargo, and 10+ carriers. "
            "NEW WAREHOUSES UNDER CONSTRUCTION: Menzies and dnata building the most "
            "technologically advanced cargo warehouses in North America — designed for "
            "AGV navigation, robotic sorting, RFID/IoT tracking, environmental monitoring. "
            "CRITICAL TIMING: 5G must be designed-in before concrete is poured. Missing "
            "this window = 20-year lockout from embedded wireless infrastructure. "
            "Cold chain monitoring requires sub-100ms latency for pharmaceutical/perishable "
            "cargo compliance."
        ),
        "source_file": "dfw-master-package",
        "source_folder": "airport-5g",
        "scope": "operational",
        "constituency": "cargo",
    },
    # Concessions
    {
        "_id": "dfw-concessions-overview",
        "text": (
            "DFW concession program: 200+ locations, 60 operators, $4.2B gross concession "
            "product in 2024. Major operators: HMSHost/Avolta AG (anchor, most locations), "
            "Paradies Lagardere, Star Concessions (Dallas-based, 24+ locations). 34+ new "
            "locations approved/in RFP through 2028 across Terminal F and Terminal C rebuild. "
            "ACDBE Small Business Enterprise program ensures opportunities for disadvantaged "
            "businesses — these operators have minimal IT capability. Amazon JWO cashierless "
            "technology already deployed at Terminal D. POS systems in use: Aloha, Toast, "
            "Square, proprietary. Operators need turnkey managed connectivity — cannot manage "
            "another vendor. Per-location monthly pricing model (opex, not capex)."
        ),
        "source_file": "dfw-master-package",
        "source_folder": "airport-5g",
        "scope": "market",
        "constituency": "concessions",
    },
    # Competitive landscape
    {
        "_id": "dfw-competitive-landscape",
        "text": (
            "Private 5G competitive landscape at DFW:\n"
            "- AT&T: $10M CWP investment, 1000 APs, incumbent carrier partner\n"
            "- Betacom: Trial nodes already deployed at DFW, competing for expansion\n"
            "- Celona: MicroSlicing technology for network segmentation\n"
            "- Boingo/DigitalBridge: $854M exit sets airport wireless valuation benchmark\n"
            "- Ericsson: Enterprise 5G infrastructure provider\n"
            "- Federated Wireless: SAS provider managing 340K+ APs globally, spectrum arbitration\n"
            "Key competitive dynamic: AT&T vs airport sovereignty. AT&T wants to remain "
            "carrier-layer operator; airport may choose to own infrastructure and treat "
            "carriers as tenants. Hybrid models are emerging as the likely middle ground."
        ),
        "source_file": "dfw-master-package",
        "source_folder": "airport-5g",
        "scope": "strategic",
        "constituency": "att",
    },
    # Terminal projects
    {
        "_id": "dfw-terminal-projects",
        "text": (
            "DFW Forward capital projects relevant to 5G deployment:\n"
            "Terminal F: $4B greenfield construction, 31 new gates, opening 2027+. "
            "Greenfield = optimal for 5G design-in from day one. Anchor airline will "
            "operate all 31 gates.\n"
            "Terminal C: $3B rebuild through 2028. Must maintain operations during "
            "construction — network migration challenge. Anchor airline's exclusive terminal.\n"
            "New cargo warehouses: Menzies and dnata facilities under construction NOW. "
            "Must embed 5G before concrete is poured.\n"
            "New concession locations: 34+ approved/in RFP through 2028, spread across "
            "Terminal F and Terminal C rebuild."
        ),
        "source_file": "dfw-master-package",
        "source_folder": "airport-5g",
        "scope": "operational",
        "constituency": "all",
    },
    # Carrier offload economics
    {
        "_id": "dfw-carrier-offload-economics",
        "text": (
            "AT&T carrier offload economics at DFW: $500K-$2M/year in CBRS capacity "
            "that can be sold to third-party carriers (T-Mobile, Verizon) for traffic "
            "offload. 87M passengers annually with smartphones = massive data demand. "
            "Neutral-host model allows airport to sell connectivity to multiple carriers "
            "simultaneously. Revenue share models: 70/30 (airport/carrier), 60/40, or "
            "flat-fee per-carrier arrangements. AT&T's position: retain carrier-layer "
            "operations and earn revenue share on any CBRS capacity sold to competitors. "
            "AT&T brand presence requirement in tenant-facing connectivity products."
        ),
        "source_file": "dfw-master-package",
        "source_folder": "airport-5g",
        "scope": "financial",
        "constituency": "att",
    },
    # Use case inventory
    {
        "_id": "dfw-5g-use-cases",
        "text": (
            "DFW Private 5G Use Case Inventory:\n"
            "AIRLINE OPS: Ramp IoT (baggage tracking, crew comms, flight analytics), "
            "real-time aircraft turnaround monitoring, automated ground equipment tracking\n"
            "CARGO: Warehouse automation (AGV navigation, robotic sorting), cold chain "
            "monitoring (sub-100ms latency), RFID/IoT asset tracking, customs automation\n"
            "CONCESSIONS: POS connectivity (99.9% uptime), mobile ordering, cashierless "
            "checkout (Amazon JWO expansion), dynamic pricing, digital signage\n"
            "PASSENGER: High-speed connectivity, wayfinding, location-based services, "
            "premium Wi-Fi tiers, AR/VR experiences\n"
            "AIRPORT OPS: Security camera analytics, environmental monitoring, energy "
            "management, predictive maintenance, autonomous vehicles (landside transport)"
        ),
        "source_file": "dfw-master-package",
        "source_folder": "airport-5g",
        "scope": "operational",
        "constituency": "all",
    },
    # Deployment hypotheses
    {
        "_id": "dfw-deployment-hypotheses",
        "text": (
            "Four competing deployment architectures for DFW private 5G:\n"
            "H1: AT&T-Led Expansion — Extend existing CWP to cover all use cases. "
            "AT&T owns/operates entire network. Airport pays subscription. Pro: simplicity, "
            "proven carrier. Con: airport has no ownership, limited customization.\n"
            "H2: Airport-Sovereign Network — DFW builds and owns entire 5G infrastructure. "
            "AT&T becomes one tenant among many. Pro: full control, maximum revenue. "
            "Con: operational complexity, AT&T resistance, requires building expertise.\n"
            "H3: Hybrid Co-Investment — DFW owns infrastructure, AT&T operates carrier "
            "layer, revenue share on tenant access. Pro: balanced control/expertise. "
            "Con: complex governance, revenue split negotiations.\n"
            "H4: Phased Sovereignty — Start AT&T-led (existing terminals), transition to "
            "airport-owned for new builds (Terminal F, cargo). Pro: low risk, learns as it "
            "goes. Con: two parallel architectures, migration complexity."
        ),
        "source_file": "dfw-master-package",
        "source_folder": "airport-5g",
        "scope": "strategic",
        "constituency": "all",
    },
]


def upsert_to_pinecone() -> None:
    """Upsert DFW knowledge chunks to Pinecone."""
    api_key = os.environ.get("PINECONE_API_KEY")
    index_host = os.environ.get("PINECONE_INDEX_HOST")

    if not api_key or not index_host:
        print("ERROR: PINECONE_API_KEY and PINECONE_INDEX_HOST must be set in .env")
        sys.exit(1)

    from pinecone import Pinecone

    pc = Pinecone(api_key=api_key)
    index = pc.Index(host=index_host)

    print(f"Upserting {len(DFW_CHUNKS)} chunks to namespace '{NAMESPACE}'...")

    for i, chunk in enumerate(DFW_CHUNKS):
        record = {
            "_id": chunk["_id"],
            "text": chunk["text"],
            "source_file": chunk["source_file"],
            "source_folder": chunk["source_folder"],
            "scope": chunk["scope"],
            "constituency": chunk["constituency"],
        }

        try:
            index.upsert_records(namespace=NAMESPACE, records=[record])
            print(f"  [{i+1}/{len(DFW_CHUNKS)}] {chunk['_id']} ✓")
        except Exception as e:
            print(f"  [{i+1}/{len(DFW_CHUNKS)}] {chunk['_id']} ✗ — {e}")

        # Brief pause to avoid rate limits
        if (i + 1) % 5 == 0:
            time.sleep(0.5)

    print(f"\nDone. {len(DFW_CHUNKS)} records upserted to '{NAMESPACE}' namespace.")


def verify_upsert() -> None:
    """Verify the upsert by querying the namespace."""
    api_key = os.environ.get("PINECONE_API_KEY")
    index_host = os.environ.get("PINECONE_INDEX_HOST")

    if not api_key or not index_host:
        return

    from pinecone import Pinecone

    pc = Pinecone(api_key=api_key)
    index = pc.Index(host=index_host)

    print("\nVerification — querying 'airport-5g' namespace...")
    try:
        response = index.search(
            namespace=NAMESPACE,
            query={"top_k": 3, "inputs": {"text": "DFW private 5G deployment cost"}},
        )
        hits = response.get("result", {}).get("hits", [])
        print(f"  Found {len(hits)} results:")
        for hit in hits:
            rid = hit.get("_id", "?")
            score = hit.get("_score", 0)
            text_preview = hit.get("fields", {}).get("text", "")[:100]
            print(f"    {rid} (score: {score:.3f}): {text_preview}...")
    except Exception as e:
        print(f"  Verification query failed: {e}")


if __name__ == "__main__":
    upsert_to_pinecone()
    verify_upsert()
