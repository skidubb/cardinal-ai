"""Model catalog — single source of truth for every model the platform can run.

Each entry declares how a model is reached (``route``): ``anthropic`` models go
direct through the Anthropic SDK (keeps prompt caching and the native tool
loop); ``gateway`` models go through the Vercel AI Gateway via LiteLLM and are
billed on the existing Vercel account.

Consumers:
- protocols/llm.py         — routes llm_complete() calls by ``resolve_route``
- protocols/server_agent.py — gateway agents use plain completions (no tools)
- protocols/agent_provider.py — validates per-agent model overrides
- api/routers/models.py    — GET /api/models for the UIs
- ce-shared pricing stays authoritative for billing math; prices here are
  display values (a test asserts the two agree).

Anthropic model IDs verified against the live /v1/models endpoint 2026-07-04.
Gateway model IDs use LiteLLM's ``vercel_ai_gateway/`` prefix; entries marked
"verify" in ``notes`` must be confirmed in the Vercel AI Gateway model browser
once VERCEL_AI_GATEWAY_API_KEY is provisioned.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel


class ModelRoute(str, Enum):
    ANTHROPIC = "anthropic"
    GATEWAY = "gateway"


class ModelInfo(BaseModel):
    model_config = {"frozen": True}

    id: str  # canonical id used in DB rows, API payloads, env overrides
    display_name: str
    provider: str
    route: ModelRoute
    litellm_id: str  # gateway: "vercel_ai_gateway/<provider>/<model>"; anthropic: == id
    tier: str  # L1 cheap/mechanical … L4 frontier reasoning (matches config.COGNITIVE_TIERS)
    input_price: float  # $ per MTok, display only — ce_shared.pricing is billing truth
    output_price: float
    supports_anthropic_tool_loop: bool
    context_window: int
    notes: str = ""


_ANTHROPIC_MODELS = [
    ModelInfo(
        id="claude-fable-5",
        display_name="Claude Fable 5",
        provider="anthropic",
        route=ModelRoute.ANTHROPIC,
        litellm_id="claude-fable-5",
        tier="L4",
        input_price=10.0,
        output_price=50.0,
        supports_anthropic_tool_loop=True,
        context_window=1_000_000,
        notes="Mythos-class. New tokenizer ≈ +30% tokens vs pre-4.7 models.",
    ),
    ModelInfo(
        id="claude-opus-4-8",
        display_name="Claude Opus 4.8",
        provider="anthropic",
        route=ModelRoute.ANTHROPIC,
        litellm_id="claude-opus-4-8",
        tier="L4",
        input_price=5.0,
        output_price=25.0,
        supports_anthropic_tool_loop=True,
        context_window=1_000_000,
        notes="Current flagship Opus.",
    ),
    ModelInfo(
        id="claude-opus-4-7",
        display_name="Claude Opus 4.7",
        provider="anthropic",
        route=ModelRoute.ANTHROPIC,
        litellm_id="claude-opus-4-7",
        tier="L4",
        input_price=5.0,
        output_price=25.0,
        supports_anthropic_tool_loop=True,
        context_window=1_000_000,
    ),
    ModelInfo(
        id="claude-sonnet-5",
        display_name="Claude Sonnet 5",
        provider="anthropic",
        route=ModelRoute.ANTHROPIC,
        litellm_id="claude-sonnet-5",
        tier="L3",
        input_price=2.0,
        output_price=10.0,
        supports_anthropic_tool_loop=True,
        context_window=1_000_000,
        notes="Intro pricing $2/$10 until 2026-08-31, then $3/$15.",
    ),
    ModelInfo(
        id="claude-sonnet-4-6",
        display_name="Claude Sonnet 4.6",
        provider="anthropic",
        route=ModelRoute.ANTHROPIC,
        litellm_id="claude-sonnet-4-6",
        tier="L3",
        input_price=3.0,
        output_price=15.0,
        supports_anthropic_tool_loop=True,
        context_window=1_000_000,
    ),
    ModelInfo(
        id="claude-haiku-4-5-20251001",
        display_name="Claude Haiku 4.5",
        provider="anthropic",
        route=ModelRoute.ANTHROPIC,
        litellm_id="claude-haiku-4-5-20251001",
        tier="L1",
        input_price=1.0,
        output_price=5.0,
        supports_anthropic_tool_loop=True,
        context_window=200_000,
    ),
]

_GATEWAY_MODELS = [
    ModelInfo(
        id="deepseek-v4-pro",
        display_name="DeepSeek V4 Pro",
        provider="deepseek",
        route=ModelRoute.GATEWAY,
        litellm_id="vercel_ai_gateway/deepseek/deepseek-v4-pro",
        tier="L4",
        input_price=2.0,
        output_price=4.0,
        supports_anthropic_tool_loop=False,
        context_window=1_000_000,
        notes="Top open agentic/coding model.",
    ),
    ModelInfo(
        id="deepseek-v4-flash",
        display_name="DeepSeek V4 Flash",
        provider="deepseek",
        route=ModelRoute.GATEWAY,
        litellm_id="vercel_ai_gateway/deepseek/deepseek-v4-flash",
        tier="L1",
        input_price=0.14,
        output_price=0.28,
        supports_anthropic_tool_loop=False,
        context_window=1_000_000,
        notes="Cheapest strong option for mechanical stages.",
    ),
    ModelInfo(
        id="qwen-3.6-plus",
        display_name="Qwen 3.6 Plus",
        provider="qwen",
        route=ModelRoute.GATEWAY,
        litellm_id="vercel_ai_gateway/alibaba/qwen-3.6-plus",
        tier="L3",
        input_price=0.5,
        output_price=3.0,
        supports_anthropic_tool_loop=False,
        context_window=1_000_000,
        notes="Verify availability in Vercel AI Gateway model browser.",
    ),
    ModelInfo(
        id="kimi-k2.6",
        display_name="Kimi K2.6",
        provider="moonshot",
        route=ModelRoute.GATEWAY,
        litellm_id="vercel_ai_gateway/moonshotai/kimi-k2.6",
        tier="L4",
        input_price=1.2,
        output_price=4.5,
        supports_anthropic_tool_loop=False,
        context_window=256_000,
        notes="Verify availability in Vercel AI Gateway model browser.",
    ),
    ModelInfo(
        id="glm-5.2",
        display_name="GLM 5.2",
        provider="zhipu",
        route=ModelRoute.GATEWAY,
        litellm_id="vercel_ai_gateway/zai/glm-5.2",
        tier="L4",
        input_price=1.4,
        output_price=4.4,
        supports_anthropic_tool_loop=False,
        context_window=1_000_000,
        notes="Verify availability in Vercel AI Gateway model browser.",
    ),
    ModelInfo(
        id="minimax-m2.7",
        display_name="MiniMax M2.7",
        provider="minimax",
        route=ModelRoute.GATEWAY,
        litellm_id="vercel_ai_gateway/minimax/minimax-m2.7",
        tier="L1",
        input_price=0.3,
        output_price=1.2,
        supports_anthropic_tool_loop=False,
        context_window=200_000,
        notes="Verify availability in Vercel AI Gateway model browser.",
    ),
]

CATALOG: dict[str, ModelInfo] = {m.id: m for m in _ANTHROPIC_MODELS + _GATEWAY_MODELS}

TIERS = ["L1", "L2", "L3", "L4"]


def get_model(model_id: str) -> ModelInfo | None:
    """Look up a catalog entry by canonical id (or litellm id)."""
    info = CATALOG.get(model_id)
    if info is not None:
        return info
    for m in CATALOG.values():
        if m.litellm_id == model_id:
            return m
    return None


def resolve_route(model_str: str) -> ModelRoute:
    """Route for any model string, catalog-listed or not.

    Unknown strings fall back to the same heuristic llm.py uses so env
    overrides pointing at un-cataloged models never crash: anything that
    looks like Claude goes direct, everything else goes to the gateway.
    """
    info = get_model(model_str)
    if info is not None:
        return info.route
    if model_str.startswith("anthropic/") or "claude" in model_str.lower():
        return ModelRoute.ANTHROPIC
    return ModelRoute.GATEWAY


def litellm_id_for(model_str: str) -> str:
    """LiteLLM model string for a gateway call.

    Catalog models return their declared litellm_id. Unknown non-Anthropic
    strings are prefixed for the Vercel AI Gateway unless the caller already
    supplied a provider-prefixed LiteLLM string.
    """
    info = get_model(model_str)
    if info is not None:
        return info.litellm_id
    if "/" in model_str:
        return model_str
    return f"vercel_ai_gateway/{model_str}"


def supports_tools(model_str: str) -> bool:
    """Whether the model can run the native Anthropic tool loop."""
    info = get_model(model_str)
    if info is not None:
        return info.supports_anthropic_tool_loop
    return resolve_route(model_str) == ModelRoute.ANTHROPIC


def models_for_tier(tier: str) -> list[ModelInfo]:
    return [m for m in CATALOG.values() if m.tier == tier]


def catalog_dump() -> list[dict]:
    """JSON-safe dump for GET /api/models."""
    return [m.model_dump(mode="json") for m in CATALOG.values()]
