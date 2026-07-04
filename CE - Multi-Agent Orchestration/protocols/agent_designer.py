"""Agent designer — LLM-suggested agents and teams for questions the bench doesn't cover.

Given a question, ranks the best-fit existing agents and, when there is a
genuine capability gap, designs net-new agents: production-grade system
prompt, tool selection from the runtime tool catalog, model from the model
catalog, and a proposed team composition.

Suggested specs are field-compatible with ``POST /api/agents`` so the API
layer can persist them without translation. All LLM output is validated
here — unknown tools are dropped, unknown models coerced, key collisions
suffixed — so callers can trust the shapes.
"""

from __future__ import annotations

import logging
import re

import anthropic

from protocols.config import THINKING_MODEL
from protocols.llm import llm_complete, parse_json_object
from protocols.model_catalog import CATALOG, supports_tools

logger = logging.getLogger(__name__)

MAX_NEW_AGENTS = 3
_KEY_RE = re.compile(r"[^a-z0-9_]+")


# ── Catalog blocks for the prompt ─────────────────────────────────────────────


def _bench_entries() -> dict[str, dict]:
    """Merged agent bench: builtin registry + custom DB agents (best-effort)."""
    from protocols.agents import BUILTIN_AGENTS

    entries: dict[str, dict] = {
        key: {"name": a.get("name", key), "category": a.get("category", "")}
        for key, a in BUILTIN_AGENTS.items()
    }
    try:
        from sqlmodel import Session, select

        from api.database import engine
        from api.models import Agent as AgentModel

        with Session(engine) as session:
            for row in session.execute(select(AgentModel)).scalars():
                entries.setdefault(
                    row.key,
                    {"name": row.name or row.key, "category": row.category or "custom"},
                )
    except Exception as exc:
        logger.debug("bench DB merge skipped: %s", exc)
    return entries


def _bench_catalog_block(entries: dict[str, dict]) -> str:
    lines = [
        f"- {key} — {e['name']}" + (f" [{e['category']}]" if e["category"] else "")
        for key, e in sorted(entries.items())
    ]
    return "\n".join(lines)


def _tool_catalog_block() -> tuple[str, set[str]]:
    """One line per runtime tool; returns (block, valid tool names)."""
    try:
        from csuite.tools.schemas import ALL_TOOL_SCHEMAS
    except ImportError:
        logger.warning(
            "csuite tool schemas unavailable — designer will propose no tools"
        )
        return (
            "(tool catalog unavailable — propose agents with an empty tools list)",
            set(),
        )

    lines = []
    for name, schema in ALL_TOOL_SCHEMAS.items():
        desc = (schema.get("description") or "").split(". ")[0][:110]
        lines.append(f"- {name}: {desc}")
    return "\n".join(lines), set(ALL_TOOL_SCHEMAS.keys())


def _model_guidance_block() -> str:
    lines = []
    for m in CATALOG.values():
        tools = (
            "tools enabled"
            if m.supports_anthropic_tool_loop
            else "NO TOOLS (gateway model)"
        )
        lines.append(
            f"- {m.id} — {m.display_name}, tier {m.tier}, "
            f"${m.input_price}/{m.output_price} per MTok, {tools}"
        )
    return "\n".join(lines)


# ── Prompts ───────────────────────────────────────────────────────────────────

DESIGNER_SYSTEM = """You are the staffing director for an elite multi-agent \
analysis firm. Given a strategic question, you decide which existing analysts \
(agents) to assign, and — only when the current bench genuinely cannot cover a \
critical dimension of the question — you design new specialist agents from \
scratch.

You design agents the way a great manager writes a role charter: a sharply \
scoped identity, explicit expertise, named analytical methods, a clear point \
of view on quality, and instructions on how to engage with other agents' \
arguments. Generic agents are worthless; a good agent could only have been \
designed for this question."""


DESIGNER_USER_TEMPLATE = """QUESTION:
{question}
{context_block}
EXISTING AGENT BENCH (key — name [category]):
{bench_catalog}

AVAILABLE TOOLS (new agents may ONLY use tools from this list):
{tool_catalog}

AVAILABLE MODELS (choose per agent; note which support tools):
{model_guidance}

YOUR TASK:
1. Rank the 3-6 best-fit EXISTING agents for this question (score 0.0-1.0).
2. Decide whether the bench has a genuine capability gap for this question —
   a dimension no existing agent can credibly analyze. Most questions need
   ZERO new agents. Propose at most {max_new} new agents, and only for real gaps.
3. For each new agent, write a complete production-grade system prompt
   (300-800 words) with these sections: role identity and mandate; domain
   expertise (specific frameworks, methods, named bodies of knowledge);
   analytical approach for exactly this kind of question; how to use the
   assigned tools; output standards (structure, evidence bar, what a great
   answer looks like); and stance in multi-agent debate (what it should
   challenge, what it should concede).
4. Propose ONE team for the question mixing existing + new agent keys
   (3-6 members) with complementary, non-overlapping mandates.

RULES:
- new agent keys: snake_case, descriptive, no collision with bench keys.
- tools: only names from the AVAILABLE TOOLS list; 2-6 tools that the agent
  concretely needs. Models marked "NO TOOLS" must get an empty tools list.
- model: pick from AVAILABLE MODELS by fit — frontier tier for reasoning-heavy
  mandates, cheaper tiers for narrower ones.
- team.agent_keys may reference existing bench keys and your new agent keys.

OUTPUT — exactly this JSON shape, no prose:
{{
  "existing_agents": [
    {{"key": "cfo", "score": 0.85, "rationale": "8-15 word reason"}}
  ],
  "new_agents": [
    {{
      "key": "spectrum_policy_analyst",
      "name": "Spectrum Policy Analyst",
      "category": "custom",
      "model": "claude-opus-4-8",
      "temperature": 1.0,
      "system_prompt": "...(300-800 words, sections as specified)...",
      "tools": ["web_search", "web_fetch"],
      "kb_namespaces": [],
      "rationale": "one sentence: the gap this agent fills"
    }}
  ],
  "team": {{
    "name": "3-5 word team name",
    "description": "one sentence",
    "agent_keys": ["cfo", "spectrum_policy_analyst"]
  }}
}}
"""


BATCH_SUFFIX = """
You are given {n} QUESTIONS, numbered. Produce the same JSON shape PER
QUESTION, wrapped as: {{"suggestions": [{{"question_index": 0, ...same shape...}}]}}.
Design new agents sparingly across the whole batch — reuse a proposed new
agent across questions by referencing its key instead of duplicating it
(define it fully the first time it appears).
"""


# ── Validation ────────────────────────────────────────────────────────────────


def _slugify_key(raw: str, taken: set[str]) -> str:
    key = _KEY_RE.sub("_", (raw or "agent").strip().lower()).strip("_") or "agent"
    if key not in taken:
        return key
    i = 2
    while f"{key}_{i}" in taken:
        i += 1
    return f"{key}_{i}"


def _validate_suggestion(
    raw: dict,
    bench_keys: set[str],
    valid_tools: set[str],
) -> dict:
    """Coerce one raw LLM suggestion into a trustworthy shape."""
    existing = []
    for e in raw.get("existing_agents", []) or []:
        key = str(e.get("key", "")).strip().lower()
        if key not in bench_keys:
            continue
        try:
            score = max(0.0, min(1.0, float(e.get("score", 0.0))))
        except (TypeError, ValueError):
            score = 0.0
        existing.append(
            {
                "key": key,
                "score": score,
                "rationale": str(e.get("rationale", "")).strip(),
            }
        )
    existing.sort(key=lambda e: -e["score"])

    taken = set(bench_keys)
    new_agents = []
    for spec in (raw.get("new_agents", []) or [])[:MAX_NEW_AGENTS]:
        prompt = str(spec.get("system_prompt", "")).strip()
        if len(prompt) < 200:
            logger.info(
                "designer: dropped new agent with thin prompt (%d chars)", len(prompt)
            )
            continue
        key = _slugify_key(str(spec.get("key", "")), taken)
        taken.add(key)

        model = str(spec.get("model", "")).strip()
        if model not in CATALOG:
            logger.info(
                "designer: unknown model %r coerced to %s", model, THINKING_MODEL
            )
            model = THINKING_MODEL

        tools = [t for t in (spec.get("tools") or []) if t in valid_tools]
        dropped = [t for t in (spec.get("tools") or []) if t not in valid_tools]
        if dropped:
            logger.info("designer: dropped invalid tools %s for %s", dropped, key)
        if not supports_tools(model):
            tools = []

        new_agents.append(
            {
                "key": key,
                "name": str(spec.get("name", key.replace("_", " ").title())).strip(),
                "category": str(spec.get("category", "custom")).strip() or "custom",
                "model": model,
                "temperature": spec.get("temperature", 1.0),
                "system_prompt": prompt,
                "tools": tools,
                "kb_namespaces": [
                    str(ns)
                    for ns in (spec.get("kb_namespaces") or [])
                    if isinstance(ns, str)
                ],
                "rationale": str(spec.get("rationale", "")).strip(),
            }
        )

    team = None
    raw_team = raw.get("team")
    if isinstance(raw_team, dict):
        allowed = bench_keys | {a["key"] for a in new_agents}
        keys = [
            str(k).strip().lower()
            for k in (raw_team.get("agent_keys") or [])
            if str(k).strip().lower() in allowed
        ]
        if keys:
            team = {
                "name": str(raw_team.get("name", "Suggested Team")).strip(),
                "description": str(raw_team.get("description", "")).strip(),
                "agent_keys": keys,
            }

    return {"existing_agents": existing, "new_agents": new_agents, "team": team}


_EMPTY_SUGGESTION: dict = {"existing_agents": [], "new_agents": [], "team": None}


# ── Public API ────────────────────────────────────────────────────────────────


async def suggest_agents(
    question: str,
    context: str | None = None,
    *,
    protocol_key: str | None = None,
    client: anthropic.AsyncAnthropic | None = None,
) -> dict:
    """Suggest existing agents, new agent specs, and a team for one question."""
    results = await suggest_agents_batch(
        [question], context=context, protocol_key=protocol_key, client=client
    )
    return results[0] if results else dict(_EMPTY_SUGGESTION)


async def suggest_agents_batch(
    questions: list[str],
    context: str | None = None,
    *,
    protocol_key: str | None = None,
    client: anthropic.AsyncAnthropic | None = None,
) -> list[dict]:
    """Batched designer call — one LLM round-trip for N questions.

    Returns a list aligned to ``questions``; entries the model skipped come
    back as empty suggestions, never raising, so callers can zip safely.
    """
    if not questions:
        return []
    client = client or anthropic.AsyncAnthropic()

    entries = _bench_entries()
    bench_keys = set(entries.keys())
    tool_block, valid_tools = _tool_catalog_block()

    context_parts = []
    if context:
        context_parts.append(f"\nCONTEXT:\n{context[:20_000]}\n")
    if protocol_key:
        context_parts.append(
            f"\nThe question will run through protocol '{protocol_key}'.\n"
        )
    context_block = "".join(context_parts) or "\n"

    if len(questions) == 1:
        question_text = questions[0]
        suffix = ""
    else:
        question_text = "\n".join(f"{i}. {q}" for i, q in enumerate(questions))
        suffix = BATCH_SUFFIX.format(n=len(questions))

    prompt = (
        DESIGNER_USER_TEMPLATE.format(
            question=question_text,
            context_block=context_block,
            bench_catalog=_bench_catalog_block(entries),
            tool_catalog=tool_block,
            model_guidance=_model_guidance_block(),
            max_new=MAX_NEW_AGENTS,
        )
        + suffix
    )

    try:
        text = await llm_complete(
            client,
            agent_name="agent_designer",
            model=THINKING_MODEL,
            max_tokens=8192,
            system=DESIGNER_SYSTEM,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = parse_json_object(text)
    except Exception as exc:
        logger.warning("agent designer LLM call failed: %s", exc)
        return [dict(_EMPTY_SUGGESTION) for _ in questions]

    if len(questions) == 1:
        return [_validate_suggestion(raw, bench_keys, valid_tools)]

    by_index: dict[int, dict] = {}
    defined_new: dict[str, dict] = {}
    for item in raw.get("suggestions", []) or []:
        try:
            idx = int(item.get("question_index", -1))
        except (TypeError, ValueError):
            continue
        if not (0 <= idx < len(questions)):
            continue
        validated = _validate_suggestion(item, bench_keys, valid_tools)
        # Batch dedupe: a new agent fully defined earlier may be referenced by
        # key only later; re-attach the earlier definition so every entry is
        # self-contained for the UI.
        for spec in validated["new_agents"]:
            defined_new.setdefault(spec["key"], spec)
        if validated["team"]:
            for key in validated["team"]["agent_keys"]:
                if key in defined_new and all(
                    a["key"] != key for a in validated["new_agents"]
                ):
                    validated["new_agents"].append(defined_new[key])
        by_index[idx] = validated

    return [by_index.get(i, dict(_EMPTY_SUGGESTION)) for i in range(len(questions))]
