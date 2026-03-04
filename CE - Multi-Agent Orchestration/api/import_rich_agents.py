"""Import rich agent configurations from CE Agent Builder into the orchestrator DB."""

import json
from pathlib import Path

from sqlmodel import Session, select

from api.database import engine
from api.models import Agent
from api.tool_registry import ROLE_KB_NAMESPACES, ROLE_MCP_MAP, ROLE_TOOL_MAP
from protocols.agents import AGENT_CATEGORIES, BUILTIN_AGENTS

# Path to CE Agent Builder prompts
_AGENT_BUILDER_ROOT = Path(__file__).resolve().parent.parent.parent / "CE - Agent Builder"
_PROMPTS_DIR = _AGENT_BUILDER_ROOT / "src" / "csuite" / "prompts"

# Executive role → prompt module mapping
_EXECUTIVE_PROMPTS = {
    "ceo": "ceo_prompt",
    "cfo": "cfo_prompt",
    "cto": "cto_prompt",
    "cmo": "cmo_prompt",
    "coo": "coo_prompt",
    "cpo": "cpo_prompt",
    "cro": "cro_prompt",
}

# Temperature per role (from CE Agent Builder config.py)
_ROLE_TEMPERATURES = {
    "ceo": 0.6, "cfo": 0.5, "cto": 0.6, "cmo": 0.8, "coo": 0.6, "cpo": 0.6, "cro": 0.6,
}


def _load_kb_instructions() -> str:
    """Load KB_INSTRUCTIONS from the Agent Builder."""
    kb_file = _PROMPTS_DIR / "kb_instructions.py"
    if not kb_file.exists():
        return ""
    text = kb_file.read_text()
    ns: dict = {}
    try:
        exec(compile(text, str(kb_file), "exec"), ns)  # noqa: S307
    except Exception:
        return ""
    return ns.get("KB_INSTRUCTIONS", "")


def _ensure_csuite_prompts_module():
    """Register a fake csuite.prompts.kb_instructions module so exec() can resolve the import."""
    import sys
    import types

    kb_text = _load_kb_instructions()

    for mod_name in ("csuite", "csuite.prompts", "csuite.prompts.kb_instructions"):
        if mod_name not in sys.modules:
            sys.modules[mod_name] = types.ModuleType(mod_name)

    sys.modules["csuite.prompts.kb_instructions"].KB_INSTRUCTIONS = kb_text  # type: ignore[attr-defined]


def _load_prompt(role: str) -> str:
    """Load the full system prompt for an executive role."""
    module_name = _EXECUTIVE_PROMPTS.get(role)
    if not module_name:
        return ""
    prompt_file = _PROMPTS_DIR / f"{module_name}.py"
    if not prompt_file.exists():
        return ""

    _ensure_csuite_prompts_module()

    text = prompt_file.read_text()
    namespace: dict = {}
    try:
        compiled = compile(text, str(prompt_file), "exec")
        exec(compiled, namespace)  # noqa: S307
    except Exception:
        return ""

    for key, val in namespace.items():
        if key.endswith("_SYSTEM_PROMPT") and isinstance(val, str):
            return val
    return ""


def _get_category(key: str) -> str:
    """Find the category for an agent key."""
    for cat, keys in AGENT_CATEGORIES.items():
        if key in keys:
            return cat
    return ""


def _get_parent_executive(category: str) -> str:
    """Map a sub-agent category to its parent executive role."""
    mapping = {
        "executive": "",
        "ceo-team": "ceo",
        "cfo-team": "cfo",
        "cmo-team": "cmo",
        "coo-team": "coo",
        "cpo-team": "cpo",
        "cto-team": "cto",
        "gtm-leadership": "cro",
        "gtm-sales": "cro",
        "gtm-marketing": "cmo",
        "gtm-partners": "cro",
        "gtm-success": "cro",
        "gtm-ops": "cro",
        "external": "",
    }
    return mapping.get(category, "")


def import_rich_agents() -> dict:
    """Import rich agent configs from CE Agent Builder into the DB.

    Returns summary of what was imported.
    """
    stats = {"executives_updated": 0, "sub_agents_updated": 0, "skipped": 0}

    with Session(engine) as session:
        for key, agent_data in BUILTIN_AGENTS.items():
            category = _get_category(key)

            existing = session.exec(select(Agent).where(Agent.key == key)).first()

            if not existing:
                existing = Agent(key=key, name=agent_data["name"], is_builtin=True)
                session.add(existing)

            existing.name = agent_data["name"]
            existing.category = category
            existing.is_builtin = True

            # Determine the executive role for this agent
            executive_role = ""
            if category == "executive":
                executive_role = key
            else:
                executive_role = _get_parent_executive(category)

            # Load rich prompt for executives
            if category == "executive" and key in _EXECUTIVE_PROMPTS:
                rich_prompt = _load_prompt(key)
                if rich_prompt:
                    existing.system_prompt = rich_prompt
                    stats["executives_updated"] += 1
                else:
                    existing.system_prompt = agent_data.get("system_prompt", "")
                    stats["skipped"] += 1
            else:
                existing.system_prompt = agent_data.get("system_prompt", "")
                stats["sub_agents_updated"] += 1

            # Assign tools from parent executive role
            if executive_role and executive_role in ROLE_TOOL_MAP:
                existing.tools_json = json.dumps(ROLE_TOOL_MAP[executive_role])

            # Assign MCP servers
            if executive_role and executive_role in ROLE_MCP_MAP:
                existing.mcp_servers_json = json.dumps(ROLE_MCP_MAP[executive_role])

            # Assign KB namespaces
            if executive_role and executive_role in ROLE_KB_NAMESPACES:
                existing.kb_namespaces_json = json.dumps(ROLE_KB_NAMESPACES[executive_role])

            # Set temperature for executives
            if key in _ROLE_TEMPERATURES:
                existing.temperature = _ROLE_TEMPERATURES[key]

            # External agents with their own model
            if "model" in agent_data:
                existing.model = agent_data["model"]

            session.add(existing)

        session.commit()

    return stats
