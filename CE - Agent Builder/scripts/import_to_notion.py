#!/usr/bin/env python3
"""
Import local markdown files into Notion Sprint Planner page bodies.
Uses the Notion API to convert markdown to blocks and append to existing pages.

Usage:
    pip install notion-client python-dotenv
    python scripts/import_to_notion.py
"""

import re
import time
from pathlib import Path

from notion_client import Client
from ce_shared.env import find_and_load_dotenv
import os

find_and_load_dotenv()

notion = Client(auth=os.environ["NOTION_API_KEY"])

# --- Markdown to Notion blocks converter ---

def md_to_rich_text(text: str) -> list[dict]:
    """Convert inline markdown (bold, italic, code, links) to Notion rich text."""
    parts = []
    pattern = r'(\*\*.*?\*\*|__.*?__|_.*?_|\*.*?\*|`[^`]+`|\[([^\]]+)\]\(([^)]+)\))'
    last_end = 0
    for m in re.finditer(pattern, text):
        if m.start() > last_end:
            plain = text[last_end:m.start()]
            if plain:
                parts.append({"type": "text", "text": {"content": plain}})
        token = m.group(0)
        if token.startswith("**") or token.startswith("__"):
            inner = token[2:-2]
            parts.append({"type": "text", "text": {"content": inner}, "annotations": {"bold": True}})
        elif token.startswith("`"):
            inner = token[1:-1]
            parts.append({"type": "text", "text": {"content": inner}, "annotations": {"code": True}})
        elif token.startswith("["):
            link_text = m.group(2)
            link_url = m.group(3)
            parts.append({"type": "text", "text": {"content": link_text, "link": {"url": link_url}}})
        elif token.startswith("_") or token.startswith("*"):
            inner = token[1:-1]
            parts.append({"type": "text", "text": {"content": inner}, "annotations": {"italic": True}})
        last_end = m.end()
    if last_end < len(text):
        remaining = text[last_end:]
        if remaining:
            parts.append({"type": "text", "text": {"content": remaining}})
    if not parts:
        parts.append({"type": "text", "text": {"content": text}})
    return parts


def md_to_blocks(md_content: str) -> list[dict]:
    """Convert markdown string to list of Notion block objects."""
    blocks = []
    lines = md_content.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i]

        if not line.strip():
            i += 1
            continue

        # Horizontal rule
        if re.match(r'^---+\s*$', line.strip()):
            blocks.append({"object": "block", "type": "divider", "divider": {}})
            i += 1
            continue

        # Code block
        if line.strip().startswith("```"):
            lang = line.strip()[3:].strip()
            code_lines = []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith("```"):
                code_lines.append(lines[i])
                i += 1
            i += 1
            code_text = "\n".join(code_lines)
            if len(code_text) > 2000:
                code_text = code_text[:1997] + "..."
            blocks.append({
                "object": "block", "type": "code",
                "code": {
                    "rich_text": [{"type": "text", "text": {"content": code_text}}],
                    "language": lang if lang else "plain text"
                }
            })
            continue

        # Headers
        if line.startswith("### "):
            blocks.append({
                "object": "block", "type": "heading_3",
                "heading_3": {"rich_text": md_to_rich_text(line[4:].strip())}
            })
            i += 1
            continue
        if line.startswith("## "):
            blocks.append({
                "object": "block", "type": "heading_2",
                "heading_2": {"rich_text": md_to_rich_text(line[3:].strip())}
            })
            i += 1
            continue
        if line.startswith("# "):
            blocks.append({
                "object": "block", "type": "heading_1",
                "heading_1": {"rich_text": md_to_rich_text(line[2:].strip())}
            })
            i += 1
            continue

        # Blockquote
        if line.strip().startswith("> "):
            blocks.append({
                "object": "block", "type": "quote",
                "quote": {"rich_text": md_to_rich_text(line.strip()[2:])}
            })
            i += 1
            continue

        # Checkbox
        if line.strip().startswith("- [ ] ") or line.strip().startswith("- [x] "):
            checked = line.strip().startswith("- [x]")
            text = line.strip()[6:]
            blocks.append({
                "object": "block", "type": "to_do",
                "to_do": {"rich_text": md_to_rich_text(text), "checked": checked}
            })
            i += 1
            continue

        # Bullet list
        if re.match(r'^[-*]\s', line.strip()):
            blocks.append({
                "object": "block", "type": "bulleted_list_item",
                "bulleted_list_item": {"rich_text": md_to_rich_text(line.strip()[2:])}
            })
            i += 1
            continue

        # Numbered list
        m = re.match(r'^(\d+)\.\s(.+)', line.strip())
        if m:
            blocks.append({
                "object": "block", "type": "numbered_list_item",
                "numbered_list_item": {"rich_text": md_to_rich_text(m.group(2))}
            })
            i += 1
            continue

        # Table
        if line.strip().startswith("|"):
            table_rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                row_text = lines[i].strip()
                if re.match(r'^\|[\s\-:|]+\|$', row_text):
                    i += 1
                    continue
                cells = [c.strip() for c in row_text.split("|")[1:-1]]
                table_rows.append(cells)
                i += 1
            if table_rows:
                col_count = max(len(r) for r in table_rows)
                for row in table_rows:
                    while len(row) < col_count:
                        row.append("")
                table_block = {
                    "object": "block", "type": "table",
                    "table": {
                        "table_width": col_count,
                        "has_column_header": True,
                        "has_row_header": False,
                        "children": []
                    }
                }
                for row in table_rows:
                    cells = []
                    for cell in row:
                        cell_text = cell[:2000] if len(cell) > 2000 else cell
                        cells.append(md_to_rich_text(cell_text))
                    table_block["table"]["children"].append({
                        "object": "block", "type": "table_row",
                        "table_row": {"cells": cells}
                    })
                blocks.append(table_block)
            continue

        # Default: paragraph
        text = line.strip()
        if text:
            if len(text) > 2000:
                text = text[:1997] + "..."
            blocks.append({
                "object": "block", "type": "paragraph",
                "paragraph": {"rich_text": md_to_rich_text(text)}
            })
        i += 1

    return blocks


def clear_page(page_id: str):
    """Remove all existing blocks from a page."""
    children = notion.blocks.children.list(block_id=page_id)
    for block in children["results"]:
        try:
            notion.blocks.delete(block_id=block["id"])
        except Exception:
            pass


def import_md_to_page(page_id: str, file_path: str) -> bool:
    """Read a markdown file and import its content into a Notion page."""
    path = Path(file_path)
    if not path.exists():
        print(f"  SKIP (file not found): {file_path}")
        return False

    md = path.read_text(encoding="utf-8")
    blocks = md_to_blocks(md)

    if not blocks:
        print(f"  SKIP (no blocks): {file_path}")
        return False

    clear_page(page_id)

    # Notion API allows max 100 blocks per append call
    for chunk_start in range(0, len(blocks), 100):
        chunk = blocks[chunk_start:chunk_start + 100]
        try:
            notion.blocks.children.append(block_id=page_id, children=chunk)
        except Exception as e:
            print(f"  ERROR appending blocks {chunk_start}-{chunk_start+len(chunk)}: {e}")
            for j, block in enumerate(chunk):
                try:
                    notion.blocks.children.append(block_id=page_id, children=[block])
                except Exception as e2:
                    print(f"    Block {chunk_start+j} failed: {e2}")

    return True


# --- Page ID to file path mapping ---

BASE = "/Users/scottewalt/Documents/CE - C-Suite/Strategy Meeting"

# Sprint 1 parent rows -> Sprint 1 exec plan files
SPRINT1_PAGES = {
    "30414917-f9e4-8151-b05f-c960f1beb953": f"{BASE}/02-Sprint-1-Strategy/CEO-Exec-Sprint1.md",
    "30414917-f9e4-81c2-8b7b-e677dcf52c0b": f"{BASE}/02-Sprint-1-Strategy/CFO-Agent-Economics.md",
    "30414917-f9e4-81d5-9d4c-daca700de9ae": f"{BASE}/02-Sprint-1-Strategy/CMO-Visual-Content-Plan.md",
    "30414917-f9e4-81f6-8a91-e76ee8a9177e": f"{BASE}/02-Sprint-1-Strategy/CTO-Bootstrap-Architecture.md",
    "30414917-f9e4-8163-9ef8-fffb97b632ae": f"{BASE}/02-Sprint-1-Strategy/COO-Agent-Native-Ops.md",
    "30414917-f9e4-8100-85c3-dc76397fda54": f"{BASE}/02-Sprint-1-Strategy/CPO-Operator-ICP-Sprint.md",
}

# Sprint 2 parent rows -> Sprint 2 plan files
SPRINT2_PAGES = {
    "30414917-f9e4-81e0-8cb1-d46ae8ff71c5": f"{BASE}/06-Sprint-2/Plans/CEO-Sprint-2-Plan.md",
    "30414917-f9e4-81b6-9c33-c754a91c4028": f"{BASE}/06-Sprint-2/Plans/CFO-Sprint-2-Plan.md",
    "30414917-f9e4-81f1-8cff-dbdbe2c50b84": f"{BASE}/06-Sprint-2/Plans/CMO-Sprint-2-Plan.md",
    "30414917-f9e4-81e7-ae83-c797a4c4683e": f"{BASE}/06-Sprint-2/Plans/CTO-Sprint-2-Plan.md",
    "30414917-f9e4-817a-82ba-f34eb98c0b5d": f"{BASE}/06-Sprint-2/Plans/COO-Sprint-2-Plan.md",
    "30414917-f9e4-8197-867a-ee39ca87942a": f"{BASE}/06-Sprint-2/Plans/CPO-Sprint-2-Plan.md",
}

# Context rows
CONTEXT_PAGES = {
    "30414917-f9e4-81d5-8037-c7824fadae7a": f"{BASE}/01-Chairman-Directives/Chairman-Directives-v1.md",
    "30414917-f9e4-8134-a53b-febd21b728bf": f"{BASE}/06-Sprint-2/Pre-Mortems/Risk-Register-Sprint-2.md",
}

# Sprint 2 sub-items -> deliverable files
SUBITEM_PAGES = {
    "30414917-f9e4-8165-8aff-ced597b7421c": f"{BASE}/06-Sprint-2/Deliverables/CEO-D1-ODSC-Package.md",
    "30414917-f9e4-8120-9ab0-eb5efb05d558": f"{BASE}/06-Sprint-2/Deliverables/CEO-D2-Outbound-Messages.md",
    "30414917-f9e4-81f0-b6e6-d8d5d2f7f6fc": f"{BASE}/06-Sprint-2/Plans/Weekly-Action-Calendar.md",
    "30414917-f9e4-8134-9a69-d585538b0d2e": f"{BASE}/06-Sprint-2/Deliverables/CEO-D4-Discovery-Call-Prep-Kit.md",
    "30414917-f9e4-81fe-81aa-db35e0424dd6": f"{BASE}/06-Sprint-2/Deliverables/CEO-D5-Podcast-Pitch-Rewrite.md",
    "30414917-f9e4-81f5-86da-c5dfa87c0eaf": f"{BASE}/06-Sprint-2/Deliverables/CFO-D1-Pricing-Discovery-Guide.md",
    "30414917-f9e4-8150-8b36-fd9708fee01b": f"{BASE}/06-Sprint-2/Deliverables/CFO-D2-Engagement-Economics.md",
    "30414917-f9e4-8184-91bc-f86d766dd507": f"{BASE}/06-Sprint-2/Deliverables/CFO-D3-Cash-Position-Tracker.md",
    "30414917-f9e4-81b9-944f-ddf1f28f3afc": f"{BASE}/06-Sprint-2/Deliverables/CFO-D4-Pricing-Validation-Dashboard.md",
    "30414917-f9e4-8103-8151-fbfda7ab8d44": f"{BASE}/06-Sprint-2/Deliverables/CMO-D1-LinkedIn-Post-1.md",
    "30414917-f9e4-8146-9092-cdc22e4e541b": f"{BASE}/06-Sprint-2/Deliverables/CMO-D2-LinkedIn-Post-2.md",
    "30414917-f9e4-813a-b3f3-ec36c7176264": f"{BASE}/06-Sprint-2/Deliverables/CMO-D3-LinkedIn-Post-3.md",
    "30414917-f9e4-8131-b276-fd3be31e19f5": f"{BASE}/06-Sprint-2/Deliverables/CMO-D4-Operator-Language-Guide.md",
    "30414917-f9e4-8193-b1a9-f26eb760f0e1": f"{BASE}/06-Sprint-2/Deliverables/CMO-D5-ICP-Engagement-Audit.md",
    "30414917-f9e4-8128-94a9-cc4dc1edf0c3": f"{BASE}/06-Sprint-2/Deliverables/CTO-D1-Streamlit-Demo-Deployment.md",
    "30414917-f9e4-8160-840f-eee2bf749e8e": f"{BASE}/06-Sprint-2/Deliverables/CTO-D2-CI-Pipeline.md",
    "30414917-f9e4-8152-ade6-e6ed2937ac63": f"{BASE}/06-Sprint-2/Deliverables/CTO-D3-PDF-Report-Export.md",
    "30414917-f9e4-8176-a853-c3f70d2d4b98": f"{BASE}/06-Sprint-2/Deliverables/CTO-D4-API-Resilience.md",
    "30414917-f9e4-81c4-a0c1-dc5afa92eaa1": f"{BASE}/06-Sprint-2/Deliverables/CTO-D5-ODSC-Demo-Environment.md",
    "30414917-f9e4-81bd-84ab-c5fd4ebc5bf9": f"{BASE}/06-Sprint-2/Deliverables/COO-D1-Sprint-Deliverable-Registry.md",
    "30414917-f9e4-81f7-826b-c15d7b8a9e0e": f"{BASE}/06-Sprint-2/Deliverables/COO-D2-Dry-Run-1.md",
    "30414917-f9e4-8111-a394-f9105c56b1c8": f"{BASE}/06-Sprint-2/Deliverables/COO-D3-Dry-Run-2.md",
    "30414917-f9e4-811c-8fb0-ecf9ddc24e6d": f"{BASE}/06-Sprint-2/Deliverables/COO-D4-Mid-Sprint-Status-Pulse.md",
    "30414917-f9e4-8114-84f1-e87a7b24efcc": f"{BASE}/06-Sprint-2/Deliverables/COO-D5-Calibration-Log-Framework.md",
    "30414917-f9e4-81a8-8dbd-da00129c145f": f"{BASE}/06-Sprint-2/Deliverables/CPO-D1-Service-Market-Fit-Memo.md",
    "30414917-f9e4-8172-bdf5-c835525a550a": f"{BASE}/06-Sprint-2/Deliverables/CPO-D1-Interview-Guide.md",
    "30414917-f9e4-813b-9713-f13e56f5132c": f"{BASE}/06-Sprint-2/Deliverables/CPO-D3-Revised-Audit-Scope.md",
    "30414917-f9e4-813b-80ee-ebd72a71c765": f"{BASE}/06-Sprint-2/Deliverables/CPO-D4-Discovery-Call-Script.md",
    "30414917-f9e4-8151-92a5-d3352ffa8ae6": f"{BASE}/06-Sprint-2/Deliverables/CPO-D5-Sprint1-Retrofit-Memo.md",
}


def main():
    all_pages = {}
    all_pages.update(SPRINT1_PAGES)
    all_pages.update(SPRINT2_PAGES)
    all_pages.update(CONTEXT_PAGES)
    all_pages.update(SUBITEM_PAGES)

    total = len(all_pages)
    success = 0
    skip = 0
    fail = 0

    print(f"\nImporting {total} markdown files into Notion pages...\n")

    for idx, (page_id, file_path) in enumerate(all_pages.items(), 1):
        fname = Path(file_path).name
        print(f"[{idx}/{total}] {fname} -> {page_id[:8]}...")

        try:
            result = import_md_to_page(page_id, file_path)
            if result:
                success += 1
                print(f"  OK")
            else:
                skip += 1
        except Exception as e:
            fail += 1
            print(f"  FAIL: {e}")

        # Rate limit: Notion API allows 3 req/sec
        time.sleep(0.5)

    print(f"\nDone! {success} imported, {skip} skipped, {fail} failed out of {total} total.")


if __name__ == "__main__":
    main()
