"""ArticleWriter — turns a completed run into a narrative, magazine-style article.

Runs after the Quality Judge as a best-effort post-synthesis stage (a failure
here never fails the run). Uses THINKING_MODEL: narrative quality is the whole
point of this stage. Output is structured JSON so the portal can render an
editorial layout (headline, deck, byline, drop-cap lede, pull quotes,
point/counterpoint) rather than reflowing markdown.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from protocols.config import THINKING_MODEL
from protocols.llm import agent_complete, parse_json_object

# Loaded lazily to avoid circular imports (mirrors judge.py)
_WRITER_AGENT: dict | None = None

MAX_AGENT_EXCERPT_CHARS = 3_000
MAX_TOTAL_INPUT_CHARS = 60_000


def _get_writer_agent() -> dict:
    global _WRITER_AGENT
    if _WRITER_AGENT is None:
        from protocols.agents import META_AGENTS

        _WRITER_AGENT = META_AGENTS["article_writer"]
    return _WRITER_AGENT


ARTICLE_PROMPT = """\
You are writing a feature article for a serious business magazine about a
multi-agent analysis that just concluded. Your readers are smart executives
who did not watch the analysis happen. Your job is to make them feel like
they were in the room — and leave them knowing exactly what was decided,
what was contested, and what happens next.

THE QUESTION UNDER ANALYSIS:
{question}

PROTOCOL USED: {protocol_name}
ANALYSTS (the "sources" for your reporting): {agent_names}

FULL SYNTHESIS (the analysis's conclusions):
{synthesis}

QUALITY VERDICT (independent review of the analysis):
{judge_summary}

ANALYST CONTRIBUTIONS (quote from these — attribute accurately):
{agent_excerpts}

WRITE THE ARTICLE:
- Report, don't summarize. Findings appear as reporting ("The CFO's model
  put the payback window at…"), disagreements as live tension between named
  analysts, and the conclusion as the earned destination of the narrative.
- Quote analysts verbatim where their words are vivid; attribute every quote
  to its analyst by name. Never invent quotes or facts beyond the material
  above.
- Voice: confident, concrete, zero corporate filler. Vary sentence length.
  No bullet points in the lede. Markdown allowed in section bodies (bold,
  short lists where they genuinely help).

Respond with ONLY a JSON object, exactly this shape:
{{
  "headline": "≤12 words, active voice, no colons unless earned",
  "deck": "1-2 sentence standfirst under the headline",
  "lede": "2-4 paragraph narrative opening (markdown, no headings)",
  "sections": [
    {{
      "heading": "short section heading",
      "body_markdown": "3-6 paragraphs of reporting",
      "pull_quote": {{"text": "verbatim quote", "attribution": "Analyst Name"}}
    }}
  ],
  "tensions": [
    {{"framing": "what the disagreement is about", "sides": ["Analyst A's position", "Analyst B's position"]}}
  ],
  "what_next": "1-2 paragraph forward-looking close (markdown)"
}}

3-6 sections. pull_quote may be null when no line is worth pulling.
tensions may be an empty list when the analysts genuinely agreed."""


@dataclass
class Article:
    headline: str = ""
    deck: str = ""
    byline: dict = field(default_factory=dict)
    lede: str = ""
    sections: list[dict] = field(default_factory=list)
    tensions: list[dict] = field(default_factory=list)
    what_next: str = ""

    def as_dict(self) -> dict:
        return {
            "headline": self.headline,
            "deck": self.deck,
            "byline": self.byline,
            "lede": self.lede,
            "sections": self.sections,
            "tensions": self.tensions,
            "what_next": self.what_next,
        }

    @property
    def is_empty(self) -> bool:
        return not (self.headline and (self.lede or self.sections))


def _clip(text: str, limit: int) -> str:
    """Keep the opening and closing of long text — that's where theses live."""
    if len(text) <= limit:
        return text
    head = text[: int(limit * 0.7)]
    tail = text[-int(limit * 0.25) :]
    return f"{head}\n\n[…]\n\n{tail}"


def _format_excerpts(agent_outputs: list[dict]) -> str:
    """agent_outputs: [{"name": str, "text": str}, ...] → attributed excerpts."""
    blocks = []
    budget = MAX_TOTAL_INPUT_CHARS
    for out in agent_outputs:
        name = out.get("name") or out.get("agent_key") or "Analyst"
        text = (out.get("text") or "").strip()
        if not text:
            continue
        excerpt = _clip(text, min(MAX_AGENT_EXCERPT_CHARS, max(budget, 500)))
        budget -= len(excerpt)
        blocks.append(f"=== {name} ===\n{excerpt}")
        if budget <= 0:
            break
    return "\n\n".join(blocks) if blocks else "(no individual contributions recorded)"


def _validate_article(
    data: dict, *, protocol_key: str, agent_names: list[str]
) -> Article:
    sections = []
    for s in (data.get("sections") or [])[:8]:
        if not isinstance(s, dict):
            continue
        body = str(s.get("body_markdown", "")).strip()
        if not body:
            continue
        pull = s.get("pull_quote")
        if isinstance(pull, dict) and pull.get("text"):
            pull = {
                "text": str(pull.get("text", "")).strip(),
                "attribution": str(pull.get("attribution", "")).strip(),
            }
        else:
            pull = None
        sections.append(
            {
                "heading": str(s.get("heading", "")).strip(),
                "body_markdown": body,
                "pull_quote": pull,
            }
        )

    tensions = []
    for t in (data.get("tensions") or [])[:5]:
        if isinstance(t, dict) and t.get("framing"):
            tensions.append(
                {
                    "framing": str(t.get("framing", "")).strip(),
                    "sides": [str(x).strip() for x in (t.get("sides") or [])][:4],
                }
            )

    return Article(
        headline=str(data.get("headline", "")).strip(),
        deck=str(data.get("deck", "")).strip(),
        byline={
            "protocol": protocol_key,
            "agents": agent_names,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        },
        lede=str(data.get("lede", "")).strip(),
        sections=sections,
        tensions=tensions,
        what_next=str(data.get("what_next", "")).strip(),
    )


class ArticleWriter:
    """Writes the narrative article for a completed run.

    Args:
        client: Anthropic AsyncAnthropic client.
        model: Defaults to THINKING_MODEL — narrative quality is the product.
    """

    def __init__(self, client, model: str = THINKING_MODEL):
        self.client = client
        self.model = model

    async def write(
        self,
        *,
        question: str,
        synthesis: str,
        protocol_key: str,
        protocol_name: str | None = None,
        agent_outputs: list[dict] | None = None,
        judge_verdict: dict | None = None,
    ) -> Article:
        """Produce an Article from run material. Raises on LLM failure —
        the runner wraps this stage in try/except so a failure never fails
        the run."""
        agent_names = [
            (o.get("name") or o.get("agent_key") or "Analyst")
            for o in (agent_outputs or [])
        ]
        judge_summary = "(no independent review available)"
        if judge_verdict:
            judge_summary = (
                f"overall {judge_verdict.get('overall', '?')}/5, "
                f"completeness {judge_verdict.get('completeness', '?')}/5, "
                f"recommendation: {judge_verdict.get('recommendation', 'n/a')}; "
                f"flags: {', '.join(judge_verdict.get('flags', [])) or 'none'}"
            )

        prompt = ARTICLE_PROMPT.format(
            question=question,
            protocol_name=protocol_name or protocol_key,
            agent_names=", ".join(agent_names) or "unattributed analysts",
            synthesis=_clip(synthesis or "", 30_000),
            judge_summary=judge_summary,
            agent_excerpts=_format_excerpts(agent_outputs or []),
        )

        # no_tools: the writer reports on material it already has in full —
        # tool use would invite new research beyond the run's actual record.
        raw = await agent_complete(
            agent=_get_writer_agent(),
            fallback_model=self.model,
            messages=[{"role": "user", "content": prompt}],
            thinking_budget=0,
            max_tokens=8192,
            anthropic_client=self.client,
            no_tools=True,
        )

        return _validate_article(
            parse_json_object(raw),
            protocol_key=protocol_key,
            agent_names=agent_names,
        )
