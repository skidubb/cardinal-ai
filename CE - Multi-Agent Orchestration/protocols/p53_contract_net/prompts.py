"""Prompts for P53: Contract Net Protocol.

All agent calls ask for structured JSON actions. The orchestrator never synthesizes.
"""

TASK_SPLIT_PROMPT = """You are a task decomposition helper. Split the following strategic question into 2-5 distinct sub-tasks that different specialists could own independently.

Respond with JSON only:
{"tasks": [{"id": "t1", "title": "short title", "scope": "one sentence of what this covers"}, ...]}

QUESTION:
{question}
"""


BID_PROMPT = """You are {agent_name}.

{system_prompt}

A coordination protocol is distributing work. Below is the task board. Bid on the tasks where you are the best owner. You may bid on more than one; the mechanical award step will ensure each task goes to exactly one agent.

TASK BOARD:
{task_board}

OTHER AGENTS IN POOL: {other_agents}

For each task you want to bid on, emit ONE JSON object on its own line (no prose, no code fences). Use this exact schema:

{{"action":"bid","task_id":"<task id>","fit_score":<0.0-1.0>,"confidence":<0.0-1.0>,"cost_estimate":<integer 1-10>,"approach":"<one-sentence approach>"}}

- fit_score: your honest assessment of how well the task matches your specialty. 1.0 = perfect fit, 0.0 = wrong agent.
- confidence: how sure you are of a good outcome. Separate from fit.
- cost_estimate: relative effort, 1 = trivial, 10 = major undertaking.
- approach: one concrete sentence of how you would handle it.

If no task fits you, emit nothing.

Output only the JSON lines, one per task, nothing else."""


EXECUTE_PROMPT = """You are {agent_name}.

{system_prompt}

You were awarded this task by the coordination protocol:

TASK ID: {task_id}
TASK TITLE: {task_title}
TASK SCOPE: {task_scope}

CONTEXT (the overall question being decomposed):
{question}

YOUR STATED APPROACH (from your bid):
{approach}

Deliver your section of the answer. Be direct, specific, and scoped to this task only. Do not attempt to cover tasks awarded to other agents — they will write those. Do not summarize across the overall question; your deliverable is one component of a mechanically-assembled final report.

Respond with clean prose. No JSON, no wrapper, no preamble. Markdown headings/lists are fine."""
