"""Curated pipeline preset definitions.

These preset chains are returned alongside DB-stored pipelines by GET /api/pipelines.
Each preset has is_preset=True so clients can distinguish them from user-created pipelines.

Protocol key values are verified against the actual protocols/ directory names.
"""

from __future__ import annotations

PIPELINE_PRESETS: list[dict] = [
    {
        "id": "preset-strategy-deep-dive",
        "name": "Strategy Deep Dive",
        "description": (
            "Four-stage strategic analysis: classify complexity via Cynefin, "
            "generate solutions via TRIZ, stress-test via Red/Blue/White Team, "
            "then uncover failure modes via Klein Premortem."
        ),
        "is_preset": True,
        "steps": [
            {
                "protocol_key": "p23_cynefin_probe",
                "question_template": "{question}",
            },
            {
                "protocol_key": "p06_triz",
                "question_template": (
                    "{question}\n\nContext from Cynefin analysis:\n{prev_output}"
                ),
            },
            {
                "protocol_key": "p17_red_blue_white",
                "question_template": (
                    "{question}\n\nProposed approach:\n{prev_output}"
                ),
            },
            {
                "protocol_key": "p38_klein_premortem",
                "question_template": (
                    "We are about to implement the following strategy. Identify failure modes.\n"
                    "Strategy:\n{prev_output}"
                ),
            },
        ],
    },
    {
        "id": "preset-risk-assessment",
        "name": "Risk Assessment",
        "description": (
            "Three-stage risk pipeline: forecast probabilities via Tetlock, "
            "surface failure modes via Klein Premortem, then evaluate competing "
            "hypotheses via ACH."
        ),
        "is_preset": True,
        "steps": [
            {
                "protocol_key": "p32_tetlock_forecast",
                "question_template": "{question}",
            },
            {
                "protocol_key": "p38_klein_premortem",
                "question_template": (
                    "Given these forecasts, identify potential failure modes:\n{prev_output}"
                ),
            },
            {
                "protocol_key": "p16_ach",
                "question_template": (
                    "Evaluate the competing hypotheses for this question: {question}\n\n"
                    "Risk context:\n{prev_output}"
                ),
            },
        ],
    },
    {
        "id": "preset-innovation-sprint",
        "name": "Innovation Sprint",
        "description": (
            "Three-stage creative pipeline: generate ideas via Crazy Eights, "
            "cluster and theme them via Affinity Mapping, then negotiate "
            "constraints for the best candidate via Constraint Negotiation."
        ),
        "is_preset": True,
        "steps": [
            {
                "protocol_key": "p26_crazy_eights",
                "question_template": "{question}",
            },
            {
                "protocol_key": "p27_affinity_mapping",
                "question_template": (
                    "Cluster and theme the following ideas:\n{prev_output}"
                ),
            },
            {
                "protocol_key": "p05_constraint_negotiation",
                "question_template": (
                    "Identify and negotiate constraints for implementing this approach:\n"
                    "{prev_output}"
                ),
            },
        ],
    },
    {
        "id": "preset-decision-quality",
        "name": "Decision Quality",
        "description": (
            "Three-stage decision pipeline: explore perspectives via Six Hats, "
            "enumerate pros/minus/interesting via PMI, then rank options via "
            "Borda Count voting."
        ),
        "is_preset": True,
        "steps": [
            {
                "protocol_key": "p28_six_hats",
                "question_template": "{question}",
            },
            {
                "protocol_key": "p29_pmi_enumeration",
                "question_template": (
                    "Enumerate the Plus/Minus/Interesting dimensions of the options "
                    "surfaced here:\n{prev_output}"
                ),
            },
            {
                "protocol_key": "p20_borda_count",
                "question_template": (
                    "Rank the following options using Borda Count voting:\n{prev_output}"
                ),
            },
        ],
    },
    {
        "id": "preset-systems-analysis",
        "name": "Systems Analysis",
        "description": (
            "Three-stage systems pipeline: map causal loops, detect system "
            "archetypes, then classify complexity via Cynefin to determine "
            "appropriate intervention strategies."
        ),
        "is_preset": True,
        "steps": [
            {
                "protocol_key": "p24_causal_loop_mapping",
                "question_template": "{question}",
            },
            {
                "protocol_key": "p25_system_archetype_detection",
                "question_template": (
                    "Detect system archetypes in this causal structure:\n{prev_output}"
                ),
            },
            {
                "protocol_key": "p23_cynefin_probe",
                "question_template": (
                    "Classify the complexity domain for this system: {question}\n\n"
                    "Systems analysis:\n{prev_output}"
                ),
            },
        ],
    },
    {
        "id": "preset-competitive-strategy",
        "name": "Competitive Strategy",
        "description": (
            "Four-stage competitive pipeline: generate inventive solutions via TRIZ, "
            "surface tensions via Wicked Questions, stress-test via Red/Blue/White Team, "
            "then build an OODA decision loop via Boyd OODA."
        ),
        "is_preset": True,
        "steps": [
            {
                "protocol_key": "p06_triz",
                "question_template": "{question}",
            },
            {
                "protocol_key": "p07_wicked_questions",
                "question_template": (
                    "Surface the wicked questions and tensions in this approach:\n{prev_output}"
                ),
            },
            {
                "protocol_key": "p17_red_blue_white",
                "question_template": (
                    "Stress-test this competitive strategy:\n{prev_output}"
                ),
            },
            {
                "protocol_key": "p40_boyd_ooda",
                "question_template": (
                    "Build an OODA decision loop for executing this strategy:\n{prev_output}"
                ),
            },
        ],
    },
]
