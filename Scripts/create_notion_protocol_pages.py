#!/usr/bin/env python3
"""Create individual Notion pages for all 48 protocols under the Protocol Registry.

Usage:
    pip install requests pyyaml
    export NOTION_API_KEY="your-notion-integration-token"
    python scripts/create_notion_protocol_pages.py

Parent page: Agent & Protocol Registry — Comprehensive Reference
"""

import os
import time
import yaml
import requests
from pathlib import Path

NOTION_API_KEY = os.environ.get("NOTION_API_KEY")
PARENT_PAGE_ID = "31314917-f9e4-81f3-84d0-c0a90a08b312"
PROTOCOLS_DIR = Path(__file__).parent.parent / "CE - Multi-Agent Orchestration" / "protocols"

NOTION_URL = "https://api.notion.com/v1/pages"
HEADERS = {
    "Authorization": f"Bearer {NOTION_API_KEY}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json",
}

# Origin/attribution data from the registry (not in capability.yaml)
ORIGINS = {
    "P0a": "Original", "P0b": "Original", "P0c": "Original",
    "P3": "Original", "P4": "Original", "P5": "Original",
    "P6": "Lipmanowicz & McCandless (CC BY)", "P7": "Lipmanowicz & McCandless (CC BY)",
    "P8": "Lipmanowicz & McCandless (CC BY)", "P9": "Lipmanowicz & McCandless (CC BY)",
    "P10": "Lipmanowicz & McCandless (CC BY)", "P11": "Lipmanowicz & McCandless (CC BY)",
    "P12": "Lipmanowicz & McCandless (CC BY)", "P13": "Lipmanowicz & McCandless (CC BY)",
    "P14": "Lipmanowicz & McCandless (CC BY)", "P15": "Lipmanowicz & McCandless (CC BY)",
    "P16": "CIA / Richards Heuer", "P17": "Military / Intelligence Community",
    "P18": "RAND Corporation (1950s)",
    "P19": "William Vickrey (Nobel 1996)", "P20": "Jean-Charles de Borda (1770)",
    "P21": "Fisher & Ury (Getting to Yes)",
    "P22": "Original", "P23": "Dave Snowden (Cynefin)",
    "P24": "Jay Forrester / System Dynamics", "P25": "Peter Senge (The Fifth Discipline)",
    "P26": "Google Ventures / Design Sprint", "P27": "Jiro Kawakita (KJ Method)",
    "P28": "Edward de Bono", "P29": "Edward de Bono",
    "P30": "Ramon Llull (13th century)", "P31": "Ludwig Wittgenstein",
    "P32": "Philip Tetlock", "P33": "Eliyahu Goldratt (TOC)",
    "P34": "Eliyahu Goldratt (TOC)", "P35": "Herbert Simon (Nobel 1978)",
    "P36": "Charles Sanders Peirce", "P37": "G.W.F. Hegel",
    "P38": "Gary Klein", "P39": "Karl Popper",
    "P40": "John Boyd", "P41": "Annie Duke",
    "P42": "Aristotle", "P43": "Gottfried Wilhelm Leibniz",
    "P44": "Immanuel Kant", "P45": "Alfred North Whitehead",
    "P46": "Cognitive Science", "P47": "George Polya (How to Solve It)",
}

# Map protocol directory names to their module paths
PROTOCOL_DIRS = sorted([
    d for d in PROTOCOLS_DIR.iterdir()
    if d.is_dir() and (d / "capability.yaml").exists()
], key=lambda d: d.name)


def load_capability(proto_dir: Path) -> dict:
    with open(proto_dir / "capability.yaml") as f:
        return yaml.safe_load(f)


def make_rich_text(text: str) -> list:
    return [{"type": "text", "text": {"content": text}}]


def make_heading(text: str, level: int = 2) -> dict:
    return {
        "object": "block",
        "type": f"heading_{level}",
        f"heading_{level}": {"rich_text": make_rich_text(text)},
    }


def make_paragraph(text: str) -> dict:
    return {
        "object": "block",
        "type": "paragraph",
        "paragraph": {"rich_text": make_rich_text(text)},
    }


def make_bold_paragraph(label: str, value: str) -> dict:
    return {
        "object": "block",
        "type": "paragraph",
        "paragraph": {
            "rich_text": [
                {"type": "text", "text": {"content": label}, "annotations": {"bold": True}},
                {"type": "text", "text": {"content": f" {value}"}},
            ]
        },
    }


def make_bulleted(text: str) -> dict:
    return {
        "object": "block",
        "type": "bulleted_list_item",
        "bulleted_list_item": {"rich_text": make_rich_text(text)},
    }


def make_code(text: str) -> dict:
    return {
        "object": "block",
        "type": "code",
        "code": {"rich_text": make_rich_text(text), "language": "bash"},
    }


def make_divider() -> dict:
    return {"object": "block", "type": "divider", "divider": {}}


def build_page_blocks(cap: dict, module_name: str) -> list:
    pid = cap["protocol_id"]
    origin = ORIGINS.get(pid, "Unknown")
    agents_str = "0" if cap.get("min_agents", 0) == 0 else f"{cap['min_agents']}+"
    if cap.get("max_agents") and cap["max_agents"] != cap.get("min_agents"):
        agents_str = f"{cap['min_agents']}-{cap['max_agents']}"
    elif cap.get("max_agents") and cap["max_agents"] == cap.get("min_agents"):
        agents_str = f"{cap['min_agents']} (fixed)"

    blocks = [
        # Metadata bar
        make_paragraph(
            f"Protocol ID: {pid}  |  Category: {cap['category']}  |  Origin: {origin}\n"
            f"Cost Tier: {cap['cost_tier'].title()}  |  Agents: {agents_str}  |  "
            f"Multi-Round: {'Yes' if cap.get('supports_rounds') else 'No'}  |  "
            f"Tools: {'Yes' if cap.get('tools_enabled') else 'No'}"
        ),
        make_divider(),
        # Description
        make_heading("Description"),
        make_paragraph(cap.get("description", "")),
        # When to Use
        make_heading("When to Use"),
        make_paragraph(cap.get("when_to_use", "")),
        # When NOT to Use
        make_heading("When NOT to Use"),
        make_paragraph(cap.get("when_not_to_use", "")),
        # Problem Types
        make_heading("Problem Types"),
    ]

    for pt in cap.get("problem_types", []):
        blocks.append(make_bulleted(pt))

    # CLI Usage
    blocks.append(make_heading("CLI Usage"))
    cli_cmd = f'python -m protocols.{module_name}.run -q "Your question here" -a ceo cfo cto'
    if cap.get("supports_rounds"):
        cli_cmd += " --rounds 3"
    blocks.append(make_code(cli_cmd))

    return blocks


def create_page(cap: dict, module_name: str) -> dict | None:
    pid = cap["protocol_id"]
    name = cap["name"]
    title = f"{pid} — {name}"

    blocks = build_page_blocks(cap, module_name)

    payload = {
        "parent": {"page_id": PARENT_PAGE_ID},
        "properties": {
            "title": [{"text": {"content": title}}]
        },
        "children": blocks,
    }

    resp = requests.post(NOTION_URL, headers=HEADERS, json=payload)
    if resp.status_code == 200:
        url = resp.json().get("url", "")
        print(f"  ✓ Created: {title} → {url}")
        return resp.json()
    else:
        print(f"  ✗ FAILED: {title} — {resp.status_code}: {resp.text[:200]}")
        return None


def main():
    if not NOTION_API_KEY:
        print("ERROR: Set NOTION_API_KEY environment variable")
        print("  Get an integration token from https://www.notion.so/my-integrations")
        print("  Then share the parent page with your integration")
        return

    print(f"Creating 48 protocol pages under: {PARENT_PAGE_ID}")
    print(f"Reading capability.yaml files from: {PROTOCOLS_DIR}\n")

    created = 0
    failed = 0

    for proto_dir in PROTOCOL_DIRS:
        module_name = proto_dir.name
        cap = load_capability(proto_dir)
        result = create_page(cap, module_name)
        if result:
            created += 1
        else:
            failed += 1
        # Rate limit: Notion API allows 3 req/sec
        time.sleep(0.4)

    print(f"\nDone! Created: {created}, Failed: {failed}")


if __name__ == "__main__":
    main()
