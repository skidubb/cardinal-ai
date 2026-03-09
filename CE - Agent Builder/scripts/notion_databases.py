#!/usr/bin/env python3
"""
Notion database operations for COO sprint tracking.

Creates and manages two databases:
- Sprint Deliverable Registry (COO-D1)
- Calibration Log (COO-D5)

Usage:
    python scripts/notion_databases.py create-registry --parent-page-id <ID>
    python scripts/notion_databases.py create-calibration-log --parent-page-id <ID>
    python scripts/notion_databases.py import-registry
    python scripts/notion_databases.py upsert-deliverable --id CEO-D1 --status "In Progress"
    python scripts/notion_databases.py upsert-calibration --edit-id EDIT-001 --source-deliverable CEO-D1 ...

Requires notion-client >= 2.7.0 which uses Notion API v2:
- Properties are added via data_sources.update (not databases.create)
- Queries use data_sources.query (not databases.query)
- Title property is always "Name" internally
"""

import json
import time
from pathlib import Path

import click
from ce_shared.env import find_and_load_dotenv
from notion_client import Client
import os

find_and_load_dotenv()

notion = Client(auth=os.environ["NOTION_API_KEY"])

DB_IDS_FILE = Path(__file__).parent / ".notion_db_ids.json"

RATE_LIMIT_DELAY = 0.35


def _load_db_ids() -> dict:
    if DB_IDS_FILE.exists():
        return json.loads(DB_IDS_FILE.read_text())
    return {}


def _save_db_ids(ids: dict):
    DB_IDS_FILE.write_text(json.dumps(ids, indent=2))


def _get_ids(key: str) -> tuple[str, str]:
    """Return (database_id, data_source_id) for a stored database."""
    ids = _load_db_ids()
    if key not in ids:
        raise click.ClickException(
            f"Database '{key}' not found. Run create-registry or create-calibration-log first."
        )
    entry = ids[key]
    if isinstance(entry, str):
        raise click.ClickException(
            f"Database '{key}' was created with old format. Please re-run create command."
        )
    return entry["db_id"], entry["ds_id"]


def _upsert_page(db_id: str, ds_id: str, title_value: str, properties: dict) -> str:
    """Query by Name (title), update if exists, create if not. Returns page ID."""
    time.sleep(RATE_LIMIT_DELAY)
    results = notion.data_sources.query(
        data_source_id=ds_id,
        filter={"property": "Name", "title": {"equals": title_value}},
    )

    props = {"Name": {"title": [{"text": {"content": title_value}}]}}
    props.update(properties)

    if results["results"]:
        page_id = results["results"][0]["id"]
        time.sleep(RATE_LIMIT_DELAY)
        notion.pages.update(page_id=page_id, properties=props)
        return page_id
    else:
        time.sleep(RATE_LIMIT_DELAY)
        page = notion.pages.create(parent={"database_id": db_id}, properties=props)
        return page["id"]


def _create_db_with_properties(
    parent_page_id: str, title: str, properties: dict
) -> tuple[str, str]:
    """Create a database, then add properties via data_sources.update.

    Returns (database_id, data_source_id).
    """
    time.sleep(RATE_LIMIT_DELAY)
    db = notion.databases.create(
        parent={"type": "page_id", "page_id": parent_page_id},
        title=[{"type": "text", "text": {"content": title}}],
    )
    db_id = db["id"]
    ds_id = db["data_sources"][0]["id"]

    # Add all non-title properties via data_sources.update
    # (title "Name" is created automatically)
    time.sleep(RATE_LIMIT_DELAY)
    notion.data_sources.update(data_source_id=ds_id, properties=properties)

    return db_id, ds_id


# --- Registry schema (non-title properties only; "Name" is auto-created) ---

REGISTRY_PROPERTIES = {
    "Deliverable Name": {"rich_text": {}},
    "Executive": {
        "select": {
            "options": [
                {"name": "CEO", "color": "red"},
                {"name": "CFO", "color": "green"},
                {"name": "CMO", "color": "purple"},
                {"name": "CTO", "color": "blue"},
                {"name": "COO", "color": "orange"},
                {"name": "CPO", "color": "yellow"},
            ]
        }
    },
    "Chairman Action Line": {"rich_text": {}},
    "Action Date": {"date": {}},
    "Chairman Time": {"rich_text": {}},
    "Priority": {
        "select": {
            "options": [
                {"name": "P0", "color": "red"},
                {"name": "P1", "color": "orange"},
                {"name": "P2", "color": "yellow"},
                {"name": "P3", "color": "green"},
                {"name": "P4", "color": "blue"},
                {"name": "P5", "color": "gray"},
            ]
        }
    },
    "D16 A/B": {"checkbox": {}},
    "Reviewer 1": {"rich_text": {}},
    "Reviewer 2": {"rich_text": {}},
    "Friction Reports Filed": {"number": {}},
    "Dissent Log Status": {
        "select": {
            "options": [
                {"name": "Empty", "color": "gray"},
                {"name": "Pending", "color": "yellow"},
                {"name": "Filed", "color": "green"},
                {"name": "Responded", "color": "blue"},
            ]
        }
    },
    "Status": {
        "select": {
            "options": [
                {"name": "Not Started", "color": "gray"},
                {"name": "In Progress", "color": "blue"},
                {"name": "In Review", "color": "yellow"},
                {"name": "Complete", "color": "green"},
                {"name": "Blocked", "color": "red"},
                {"name": "Backlog", "color": "default"},
            ]
        }
    },
}

# --- Calibration Log schema (non-title properties; relation added at create time) ---

CALIBRATION_PROPERTIES = {
    "Producing Executive": {
        "select": {
            "options": [
                {"name": "CEO", "color": "red"},
                {"name": "CFO", "color": "green"},
                {"name": "CMO", "color": "purple"},
                {"name": "CTO", "color": "blue"},
                {"name": "COO", "color": "orange"},
                {"name": "CPO", "color": "yellow"},
            ]
        }
    },
    "Change Summary": {"rich_text": {}},
    "Category": {
        "select": {
            "options": [
                {"name": "Tone", "color": "purple"},
                {"name": "Precision", "color": "blue"},
                {"name": "Strategic Reframe", "color": "red"},
                {"name": "Structural", "color": "orange"},
                {"name": "Factual", "color": "yellow"},
                {"name": "Scope Change", "color": "green"},
            ]
        }
    },
    "Inferred Lesson": {"rich_text": {}},
    "Applicable Scope": {
        "select": {
            "options": [
                {"name": "This Deliverable", "color": "gray"},
                {"name": "This Executive", "color": "blue"},
                {"name": "All Executives", "color": "green"},
                {"name": "Permanent Standard", "color": "red"},
            ]
        }
    },
    "Date": {"date": {}},
    "Impact Estimate": {
        "select": {
            "options": [
                {"name": "Minor", "color": "gray"},
                {"name": "Moderate", "color": "yellow"},
                {"name": "Major", "color": "red"},
            ]
        }
    },
    "Status": {
        "select": {
            "options": [
                {"name": "Logged", "color": "gray"},
                {"name": "Notified", "color": "blue"},
                {"name": "Acknowledged", "color": "yellow"},
                {"name": "Archived", "color": "green"},
            ]
        }
    },
}


@click.group()
def cli():
    """Notion database operations for COO sprint tracking."""
    pass


@cli.command()
@click.option("--parent-page-id", required=True, help="Notion page ID to create DB under")
def create_registry(parent_page_id: str):
    """Create the Sprint Deliverable Registry database."""
    click.echo("Creating Sprint Deliverable Registry...")

    db_id, ds_id = _create_db_with_properties(
        parent_page_id, "Sprint Deliverable Registry", REGISTRY_PROPERTIES
    )

    ids = _load_db_ids()
    ids["registry"] = {"db_id": db_id, "ds_id": ds_id}
    _save_db_ids(ids)

    click.echo(f"Created registry DB: {db_id}")
    click.echo(f"Data source: {ds_id}")
    click.echo(f"Saved to {DB_IDS_FILE}")


@cli.command()
@click.option("--parent-page-id", required=True, help="Notion page ID to create DB under")
def create_calibration_log(parent_page_id: str):
    """Create the Calibration Log database with relation to Registry."""
    _, registry_ds_id = _get_ids("registry")

    # Add relation property to calibration schema
    props = dict(CALIBRATION_PROPERTIES)
    props["Source Deliverable"] = {
        "relation": {"data_source_id": registry_ds_id, "single_property": {}},
    }

    click.echo("Creating Calibration Log...")

    db_id, ds_id = _create_db_with_properties(
        parent_page_id, "Calibration Log", props
    )

    ids = _load_db_ids()
    ids["calibration_log"] = {"db_id": db_id, "ds_id": ds_id}
    _save_db_ids(ids)

    click.echo(f"Created calibration log DB: {db_id}")
    click.echo(f"Data source: {ds_id}")
    click.echo(f"Saved to {DB_IDS_FILE}")
    click.echo()
    click.echo("MANUAL STEP: Create these views in the Notion UI:")
    click.echo("  1. All Edits (default table view)")
    click.echo("  2. By Executive (grouped by Producing Executive)")
    click.echo("  3. By Category (grouped by Category)")
    click.echo("  4. Recent (sorted by Date descending)")
    click.echo("  5. Unacknowledged (filtered: Status != Archived, Status != Acknowledged)")


@cli.command()
@click.option("--id", "deliverable_id", required=True, help="Deliverable ID (e.g. CEO-D1)")
@click.option("--name", default=None, help="Deliverable Name")
@click.option("--executive", default=None, help="Executive (CEO/CFO/CMO/CTO/COO/CPO)")
@click.option("--action-line", default=None, help="Chairman Action Line")
@click.option("--action-date", default=None, help="Action Date (YYYY-MM-DD)")
@click.option("--chairman-time", default=None, help="Chairman Time")
@click.option("--priority", default=None, help="Priority (P0-P5)")
@click.option("--d16-ab", default=None, type=bool, help="D16 A/B required")
@click.option("--reviewer-1", default=None, help="Reviewer 1")
@click.option("--reviewer-2", default=None, help="Reviewer 2")
@click.option("--friction-count", default=None, type=int, help="Friction Reports Filed count")
@click.option("--dissent-status", default=None, help="Dissent Log Status")
@click.option("--status", default=None, help="Status")
def upsert_deliverable(deliverable_id, **kwargs):
    """Create or update a row in the Sprint Deliverable Registry."""
    db_id, ds_id = _get_ids("registry")

    props = {}
    if kwargs["name"]:
        props["Deliverable Name"] = {"rich_text": [{"text": {"content": kwargs["name"]}}]}
    if kwargs["executive"]:
        props["Executive"] = {"select": {"name": kwargs["executive"]}}
    if kwargs["action_line"]:
        props["Chairman Action Line"] = {
            "rich_text": [{"text": {"content": kwargs["action_line"]}}]
        }
    if kwargs["action_date"]:
        props["Action Date"] = {"date": {"start": kwargs["action_date"]}}
    if kwargs["chairman_time"]:
        props["Chairman Time"] = {"rich_text": [{"text": {"content": kwargs["chairman_time"]}}]}
    if kwargs["priority"]:
        props["Priority"] = {"select": {"name": kwargs["priority"]}}
    if kwargs["d16_ab"] is not None:
        props["D16 A/B"] = {"checkbox": kwargs["d16_ab"]}
    if kwargs["reviewer_1"]:
        props["Reviewer 1"] = {"rich_text": [{"text": {"content": kwargs["reviewer_1"]}}]}
    if kwargs["reviewer_2"]:
        props["Reviewer 2"] = {"rich_text": [{"text": {"content": kwargs["reviewer_2"]}}]}
    if kwargs["friction_count"] is not None:
        props["Friction Reports Filed"] = {"number": kwargs["friction_count"]}
    if kwargs["dissent_status"]:
        props["Dissent Log Status"] = {"select": {"name": kwargs["dissent_status"]}}
    if kwargs["status"]:
        props["Status"] = {"select": {"name": kwargs["status"]}}

    page_id = _upsert_page(db_id, ds_id, deliverable_id, props)
    click.echo(f"Upserted {deliverable_id}: {page_id}")


@cli.command()
@click.option("--edit-id", required=True, help="Edit ID (e.g. EDIT-001)")
@click.option("--source-deliverable", default=None, help="Source Deliverable ID (e.g. CEO-D1)")
@click.option("--executive", default=None, help="Producing Executive")
@click.option("--summary", default=None, help="Change Summary")
@click.option("--category", default=None, help="Category")
@click.option("--lesson", default=None, help="Inferred Lesson")
@click.option("--scope", default=None, help="Applicable Scope")
@click.option("--date", default=None, help="Date (YYYY-MM-DD)")
@click.option("--impact", default=None, help="Impact Estimate")
@click.option("--status", default=None, help="Status")
def upsert_calibration(edit_id, **kwargs):
    """Create or update a row in the Calibration Log."""
    cal_db_id, cal_ds_id = _get_ids("calibration_log")

    props = {}
    if kwargs["executive"]:
        props["Producing Executive"] = {"select": {"name": kwargs["executive"]}}
    if kwargs["summary"]:
        props["Change Summary"] = {"rich_text": [{"text": {"content": kwargs["summary"]}}]}
    if kwargs["category"]:
        props["Category"] = {"select": {"name": kwargs["category"]}}
    if kwargs["lesson"]:
        props["Inferred Lesson"] = {"rich_text": [{"text": {"content": kwargs["lesson"]}}]}
    if kwargs["scope"]:
        props["Applicable Scope"] = {"select": {"name": kwargs["scope"]}}
    if kwargs["date"]:
        props["Date"] = {"date": {"start": kwargs["date"]}}
    if kwargs["impact"]:
        props["Impact Estimate"] = {"select": {"name": kwargs["impact"]}}
    if kwargs["status"]:
        props["Status"] = {"select": {"name": kwargs["status"]}}

    # Resolve source deliverable relation by querying registry
    if kwargs["source_deliverable"]:
        reg_db_id, reg_ds_id = _get_ids("registry")
        time.sleep(RATE_LIMIT_DELAY)
        results = notion.data_sources.query(
            data_source_id=reg_ds_id,
            filter={"property": "Name", "title": {"equals": kwargs["source_deliverable"]}},
        )
        if results["results"]:
            props["Source Deliverable"] = {"relation": [{"id": results["results"][0]["id"]}]}
        else:
            click.echo(f"Warning: source deliverable '{kwargs['source_deliverable']}' not found")

    page_id = _upsert_page(cal_db_id, cal_ds_id, edit_id, props)
    click.echo(f"Upserted {edit_id}: {page_id}")


# --- Bulk import data (all 30 Sprint 2 deliverables from COO-D1) ---

DELIVERABLES = [
    # CEO
    {"id": "CEO-D1", "name": "ODSC AI East 2026 Submission — Final Review Package", "exec": "CEO", "action_line": "Scott will use this deliverable to record the required Loom video and submit the ODSC speaker proposal by February 14.", "date": "2026-02-14", "time": "1 hour", "priority": "P0", "d16": True, "r1": "CFO (Economics)", "r2": "CPO (ICP Fit)", "status": "Not Started"},
    {"id": "CEO-D2", "name": "Pain-First Outbound Messaging Rewrite (10 Prospects)", "exec": "CEO", "action_line": "Scott will use this deliverable to send the first 3 personalized outbound emails to top-priority prospects by February 14.", "date": "2026-02-14", "time": "1 hour", "priority": "P1", "d16": True, "r1": "CFO (Economics)", "r2": "CPO (ICP Fit)", "status": "Not Started"},
    {"id": "CEO-D3", "name": "Weekly Action Calendar — Week of Feb 10-16", "exec": "CEO", "action_line": "Scott will use this deliverable to plan his execution week and allocate his 20 hours across all C-Suite deliverables by February 11.", "date": "2026-02-11", "time": "15 min", "priority": "P1", "d16": False, "r1": "CFO (Economics)", "r2": "CPO (ICP Fit)", "status": "Not Started"},
    {"id": "CEO-D4", "name": "Discovery Call Prep Kit — Pain-First Edition", "exec": "CEO", "action_line": "Scott will use this deliverable to run his first discovery call with a prepared pain-first framework by February 21.", "date": "2026-02-21", "time": "30 min", "priority": "P3", "d16": False, "r1": "CFO (Economics)", "r2": "CPO (ICP Fit)", "status": "Not Started"},
    {"id": "CEO-D5", "name": "Podcast Pitch Rewrite — Operator-Outcome Framing", "exec": "CEO", "action_line": "Scott will use this deliverable to send 3 revised podcast pitch emails by February 21.", "date": "2026-02-21", "time": "30 min", "priority": "P4", "d16": False, "r1": "CFO (Economics)", "r2": "CPO (ICP Fit)", "status": "Not Started"},
    # CFO
    {"id": "CFO-D1", "name": "Pricing Discovery Conversation Guide", "exec": "CFO", "action_line": "Scott will use this deliverable to test specific price anchors in the first 2-3 discovery calls and log buyer reactions in a structured format by February 21.", "date": "2026-02-21", "time": "15 min", "priority": "P3", "d16": False, "r1": "CTO (Feasibility)", "r2": "COO (Operations)", "status": "Not Started"},
    {"id": "CFO-D2", "name": "Prospect-Ready Engagement Economics One-Pager", "exec": "CFO", "action_line": "Scott will use this deliverable to answer 'what does this cost and what do I get?' in discovery conversations with confidence by February 14.", "date": "2026-02-14", "time": "15 min", "priority": "P1", "d16": False, "r1": "CTO (Feasibility)", "r2": "COO (Operations)", "status": "Not Started"},
    {"id": "CFO-D3", "name": "Sprint 2 Cash Position and Burn Rate Tracker", "exec": "CFO", "action_line": "Scott will use this deliverable to confirm exact cash runway and set a hard deadline for when the first paid engagement must close by February 12.", "date": "2026-02-12", "time": "30 min", "priority": "P5", "d16": False, "r1": "CTO (Feasibility)", "r2": "COO (Operations)", "status": "Not Started"},
    {"id": "CFO-D4", "name": "Pricing Validation Dashboard (Lightweight)", "exec": "CFO", "action_line": "Scott will use this deliverable to review pricing data from the first 3 prospect conversations and decide whether to adjust tiers by February 28.", "date": "2026-02-28", "time": "15 min", "priority": "P5", "d16": False, "r1": "CTO (Feasibility)", "r2": "COO (Operations)", "status": "Not Started"},
    # CMO
    {"id": "CMO-D1", "name": "Post 1 — \"The Million-Dollar Spreadsheet\" Carousel", "exec": "CMO", "action_line": "Scott will use this deliverable to design and publish his first LinkedIn carousel in Figma by Friday, February 13.", "date": "2026-02-13", "time": "2 hours", "priority": "P2", "d16": True, "r1": "CTO (Technical Claims)", "r2": "CEO (Market Positioning)", "status": "Not Started"},
    {"id": "CMO-D2", "name": "Post 2 — \"Why Did You Lose That Account?\" Carousel", "exec": "CMO", "action_line": "Scott will use this deliverable to design and publish the second LinkedIn carousel in Figma by Wednesday, February 19.", "date": "2026-02-19", "time": "2 hours", "priority": "P2", "d16": True, "r1": "CTO (Technical Claims)", "r2": "CEO (Market Positioning)", "status": "Not Started"},
    {"id": "CMO-D3", "name": "Post 3 — \"Your Competitor Has a C-Suite. You Have a Gut Feeling.\"", "exec": "CMO", "action_line": "Scott will use this deliverable to design and publish the third LinkedIn carousel in Figma by Monday, February 24.", "date": "2026-02-24", "time": "2 hours", "priority": "P2", "d16": True, "r1": "CTO (Technical Claims)", "r2": "CEO (Market Positioning)", "status": "Not Started"},
    {"id": "CMO-D4", "name": "Operator Language Guide and Banned-Words Protocol", "exec": "CMO", "action_line": "Scott will use this deliverable to review and approve the content language standard for all Sprint 2 and future LinkedIn content by Wednesday, February 12.", "date": "2026-02-12", "time": "15 min", "priority": "P2", "d16": False, "r1": "CTO (Technical Claims)", "r2": "CEO (Market Positioning)", "status": "Not Started"},
    {"id": "CMO-D5", "name": "ICP Engagement Audit Template (Leading Indicator Tracker for R3)", "exec": "CMO", "action_line": "Scott will use this deliverable to audit the LinkedIn engagement on Post 1 within 48 hours of publishing, by Sunday, February 15.", "date": "2026-02-15", "time": "15 min", "priority": "P2", "d16": False, "r1": "CTO (Technical Claims)", "r2": "CEO (Market Positioning)", "status": "Not Started"},
    # CTO
    {"id": "CTO-D1", "name": "Streamlit Demo App — Public URL Deployment", "exec": "CTO", "action_line": "Scott will use this deliverable to show prospects a live, working AI-powered prospect research brief during discovery calls, starting February 17.", "date": "2026-02-17", "time": "30 min", "priority": "P1", "d16": False, "r1": "CFO (Cost Reality)", "r2": "CMO (Messaging Clarity)", "status": "Not Started"},
    {"id": "CTO-D2", "name": "Integration Tests + GitHub Actions CI Pipeline", "exec": "CTO", "action_line": "Scott will use this deliverable to trust that the demo URL works reliably when he shares it with prospects, starting February 18.", "date": "2026-02-18", "time": "15 min", "priority": "P1", "d16": False, "r1": "CFO (Cost Reality)", "r2": "CMO (Messaging Clarity)", "status": "Not Started"},
    {"id": "CTO-D3", "name": "Prospect Report Export (PDF/Markdown)", "exec": "CTO", "action_line": "Scott will use this deliverable to email a prospect-ready research brief as a PDF attachment after discovery calls, starting February 19.", "date": "2026-02-19", "time": "15 min", "priority": "P3", "d16": False, "r1": "CFO (Cost Reality)", "r2": "CMO (Messaging Clarity)", "status": "Not Started"},
    {"id": "CTO-D4", "name": "API Rate Limit and Error Resilience Hardening", "exec": "CTO", "action_line": "Scott will use this deliverable to run live demos during ODSC or prospect calls without fear of API failures mid-presentation, starting February 20.", "date": "2026-02-20", "time": "0 min", "priority": "P0", "d16": False, "r1": "CFO (Cost Reality)", "r2": "CMO (Messaging Clarity)", "status": "Not Started"},
    {"id": "CTO-D5", "name": "ODSC Demo Environment (Technical Support for P0)", "exec": "CTO", "action_line": "Scott will use this deliverable to include a live demo link and technical architecture slide in the ODSC AI East 2026 submission, by February 14.", "date": "2026-02-14", "time": "30 min", "priority": "P0", "d16": False, "r1": "CFO (Cost Reality)", "r2": "CMO (Messaging Clarity)", "status": "Not Started"},
    # COO
    {"id": "COO-D1", "name": "Sprint Deliverable Registry (Notion)", "exec": "COO", "action_line": "Scott will use this deliverable to track every C-Suite output in one view, instantly see which deliverables have Chairman Action Lines vs. backlog status, and prioritize his 20-hour weekly budget by February 12.", "date": "2026-02-12", "time": "15 min", "priority": "P1", "d16": False, "r1": "CEO (Client Impact)", "r2": "CFO (Cost Efficiency)", "status": "In Progress"},
    {"id": "COO-D2", "name": "Engagement Dry Run 1 — Full Lifecycle Simulation", "exec": "COO", "action_line": "Scott will use this deliverable to execute a complete engagement simulation so he knows exactly where the delivery system breaks before any real client is involved, by February 14.", "date": "2026-02-14", "time": "2 hours", "priority": "P1", "d16": False, "r1": "CEO (Client Impact)", "r2": "CFO (Cost Efficiency)", "status": "Not Started"},
    {"id": "COO-D3", "name": "Engagement Dry Run 2 — Validation and Cycle Time Improvement", "exec": "COO", "action_line": "Scott will use this deliverable to validate that Dry Run 1 fixes actually hold, test a different engagement type, and establish baseline cycle time, by February 19.", "date": "2026-02-19", "time": "2 hours", "priority": "P1", "d16": False, "r1": "CEO (Client Impact)", "r2": "CFO (Cost Efficiency)", "status": "Not Started"},
    {"id": "COO-D4", "name": "Mid-Sprint Status Pulse (D18)", "exec": "COO", "action_line": "Scott will use this deliverable to see, on one page, whether any Pre-Mortem risks are triggering, how many Action Lines have been executed, how much budget consumed, and any escalations, by February 24.", "date": "2026-02-24", "time": "15 min", "priority": "P3", "d16": False, "r1": "CEO (Client Impact)", "r2": "CFO (Cost Efficiency)", "status": "Not Started"},
    {"id": "COO-D5", "name": "Calibration Log Framework + Edit Analysis Protocol (D19)", "exec": "COO", "action_line": "Scott will use this deliverable to have a structured system in Notion where every edit he makes is captured, categorized, and converted into a lesson, by February 17.", "date": "2026-02-17", "time": "30 min", "priority": "P5", "d16": False, "r1": "CEO (Client Impact)", "r2": "CFO (Cost Efficiency)", "status": "Not Started"},
    # CPO
    {"id": "CPO-D1", "name": "Service-Market Fit Memo", "exec": "CPO", "action_line": "Scott will use this deliverable to decide whether to proceed with the current audit offering or restructure the entry point before sending any proposal, by February 22.", "date": "2026-02-22", "time": "30 min", "priority": "P1", "d16": False, "r1": "CMO (Market Demand)", "r2": "CTO (Buildability)", "status": "Not Started"},
    {"id": "CPO-D2", "name": "Validation Interview Guide and Scoring Rubric", "exec": "CPO", "action_line": "Scott will use this deliverable to conduct the first 2 problem-validation interviews with operators by February 14.", "date": "2026-02-14", "time": "15 min", "priority": "P1", "d16": False, "r1": "CMO (Market Demand)", "r2": "CTO (Buildability)", "status": "Not Started"},
    {"id": "CPO-D3", "name": "Revised Audit Scope Document (Conditional on Validation Findings)", "exec": "CPO", "action_line": "Scott will use this deliverable to describe the audit offering in his next discovery call with confidence that the scope matches what operators actually want, by February 24.", "date": "2026-02-24", "time": "1 hour", "priority": "P3", "d16": True, "r1": "CMO (Market Demand)", "r2": "CTO (Buildability)", "status": "Not Started"},
    {"id": "CPO-D4", "name": "Discovery Call Offering Script", "exec": "CPO", "action_line": "Scott will use this deliverable to articulate the Cardinal Element offering in 90 seconds during his first discovery call, by February 17.", "date": "2026-02-17", "time": "30 min", "priority": "P3", "d16": True, "r1": "CMO (Market Demand)", "r2": "CTO (Buildability)", "status": "Not Started"},
    {"id": "CPO-D5", "name": "Sprint 1 Deliverable Retrofit Memo", "exec": "CPO", "action_line": "Scott will use this deliverable to decide which Sprint 1 CPO deliverables to update, archive, or discard based on validation findings, by February 25.", "date": "2026-02-25", "time": "15 min", "priority": "P5", "d16": False, "r1": "CMO (Market Demand)", "r2": "CTO (Buildability)", "status": "Not Started"},
]


@cli.command()
def import_registry():
    """Bulk-import all 30 deliverables from COO-D1 into the Registry database."""
    db_id, ds_id = _get_ids("registry")

    total = len(DELIVERABLES)
    click.echo(f"Importing {total} deliverables into Registry...")

    for i, d in enumerate(DELIVERABLES, 1):
        click.echo(f"[{i}/{total}] {d['id']} — {d['name'][:50]}...")

        props = {
            "Deliverable Name": {"rich_text": [{"text": {"content": d["name"]}}]},
            "Executive": {"select": {"name": d["exec"]}},
            "Chairman Action Line": {"rich_text": [{"text": {"content": d["action_line"]}}]},
            "Action Date": {"date": {"start": d["date"]}},
            "Chairman Time": {"rich_text": [{"text": {"content": d["time"]}}]},
            "Priority": {"select": {"name": d["priority"]}},
            "D16 A/B": {"checkbox": d["d16"]},
            "Reviewer 1": {"rich_text": [{"text": {"content": d["r1"]}}]},
            "Reviewer 2": {"rich_text": [{"text": {"content": d["r2"]}}]},
            "Friction Reports Filed": {"number": 0},
            "Dissent Log Status": {"select": {"name": "Empty"}},
            "Status": {"select": {"name": d["status"]}},
        }

        page_id = _upsert_page(db_id, ds_id, d["id"], props)
        click.echo(f"  -> {page_id}")

    click.echo(f"\nDone! Imported {total} deliverables.")


if __name__ == "__main__":
    cli()
