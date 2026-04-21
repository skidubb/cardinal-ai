import { inferLiveStage } from "../src/components/run/liveStageInference";

const p04 = [
  { key: "opening", name: "Opening Statements", stage_type: "agent" as const },
  { key: "rebuttals", name: "Rebuttals", stage_type: "agent" as const },
  { key: "closing", name: "Closing", stage_type: "agent" as const },
  { key: "synthesis", name: "Synthesis", stage_type: "synthesis" as const },
];

const p06 = [
  { key: "invert", name: "Invert", stage_type: "mechanical" as const },
  { key: "failure_modes", name: "Failure Modes", stage_type: "agent" as const },
  { key: "dedupe", name: "Dedupe", stage_type: "mechanical" as const },
  { key: "solutions", name: "Solutions", stage_type: "agent" as const },
  { key: "synthesis", name: "Synthesis", stage_type: "synthesis" as const },
];

const cases = [
  { name: "p04 empty", stages: p04, events: [] },
  { name: "p04 run_start only", stages: p04, events: [{ event: "run_start", data: {} }] },
  { name: "p04 mid-opening (round=0)", stages: p04, events: [
    { event: "run_start", data: {} },
    { event: "agent_output", data: { round: 0, agent_key: "ceo" } },
    { event: "agent_output", data: { round: 0, agent_key: "cfo" } },
  ]},
  { name: "p04 mid-rebuttals (round=1)", stages: p04, events: [
    { event: "run_start", data: {} },
    { event: "agent_output", data: { round: 0 } },
    { event: "agent_output", data: { round: 0 } },
    { event: "agent_output", data: { round: 1 } },
  ]},
  { name: "p04 rounds=2 synthesis (no closing)", stages: p04, events: [
    { event: "run_start", data: {} },
    { event: "agent_output", data: { round: 0 } },
    { event: "agent_output", data: { round: 1 } },
    { event: "synthesis", data: {} },
  ]},
  { name: "p04 run_complete rounds=2", stages: p04, events: [
    { event: "run_start", data: {} },
    { event: "agent_output", data: { round: 0 } },
    { event: "agent_output", data: { round: 1 } },
    { event: "synthesis", data: {} },
    { event: "run_complete", data: {} },
  ]},
  { name: "p06 mid-failure-modes (no round)", stages: p06, events: [
    { event: "run_start", data: {} },
    { event: "agent_output", data: { agent_key: "ceo" } },
  ]},
  { name: "p06 run_complete", stages: p06, events: [
    { event: "run_start", data: {} },
    { event: "agent_output", data: {} },
    { event: "agent_output", data: {} },
    { event: "synthesis", data: {} },
    { event: "run_complete", data: {} },
  ]},
];

for (const c of cases) {
  const r = inferLiveStage(c.stages, c.events);
  console.log(`${c.name}:`);
  console.log(`  active = ${r.activeStageKey}`);
  console.log(`  completed = [${r.completedStageKeys.join(", ")}]`);
}
