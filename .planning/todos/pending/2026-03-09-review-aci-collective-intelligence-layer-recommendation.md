---
created: 2026-03-09T23:32:55.505Z
title: Review ACI collective intelligence layer recommendation
area: planning
files:
  - RECOMMENDATION-collective-intelligence-layer.md
---

## Problem

A comprehensive recommendation document proposes elevating Artificial Collective Intelligence (ACI) to a first-class architectural concept in CE-AGENTS. The doc reframes the system from "protocol library" to "collective cognition system with multiple protocol modes" and presents three implementation options (A: spec/eval only, B: add telemetry, C: full adaptive learning loop).

Six decisions are requested: adopt the reframe, choose starting option, classify protocols by collective function (Exploration/Adjudication/Coordination/Learning), mandate ACI spec sections, extend CE-Evals with collective performance metrics, and determine scope (product-only vs including operational agents).

The recommended path is Option A now, instrument toward B during monorepo integration, design toward C as north star.

## Solution

1. CPO/CTO review the recommendation document
2. Decide on the 6 questions posed in "Decisions Requested" section
3. If adopting: add ACI Contribution section to protocol spec template, extend eval rubrics, classify existing 48 protocols by collective function
4. Plan telemetry schema design as part of monorepo integration work
