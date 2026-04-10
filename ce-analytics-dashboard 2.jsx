import { useState } from "react";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
  PieChart, Pie, Cell, RadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis,
  Treemap, LineChart, Line
} from "recharts";

const COLORS = {
  primary: "#1e3a5f",
  secondary: "#2d6a4f",
  accent: "#e76f51",
  warm: "#f4a261",
  cool: "#264653",
  light: "#a8dadc",
  highlight: "#e9c46a",
  muted: "#6b7280",
  bg: "#f8fafc",
  card: "#ffffff",
  text: "#1e293b",
  subtext: "#64748b",
};

const PIE_COLORS = ["#264653", "#2a9d8f", "#e9c46a", "#f4a261", "#e76f51", "#1e3a5f", "#457b9d", "#a8dadc", "#d4a373"];

// ─── DATA ───────────────────────────────────────────────────────────
const projectScale = [
  { name: "Agent Builder", files: 111, loc: 25387, tests: 23, deps: 16 },
  { name: "Orchestration", files: 241, loc: 28660, tests: 4, deps: 5 },
  { name: "Evals", files: 23, loc: 1911, tests: 6, deps: 6 },
];

const protocolCategories = [
  { name: "Wave 2 Research", value: 20, desc: "Philosophy & cognitive science" },
  { name: "Liberating Structures", value: 10, desc: "Facilitation frameworks" },
  { name: "Meta-Protocols", value: 3, desc: "Routing & escalation" },
  { name: "Baselines", value: 3, desc: "Synthesis, debate, negotiation" },
  { name: "Intel Analysis", value: 3, desc: "ACH, Red/Blue, Delphi" },
  { name: "Game Theory", value: 3, desc: "Vickrey, Borda, negotiation" },
  { name: "Org Theory", value: 2, desc: "Pipeline, Cynefin" },
  { name: "Systems Thinking", value: 2, desc: "Causal loops, archetypes" },
  { name: "Design Thinking", value: 2, desc: "Crazy 8s, affinity mapping" },
];

const agentCategories = [
  { name: "Executive", count: 7 },
  { name: "CMO Team", count: 6 },
  { name: "GTM Leadership", count: 6 },
  { name: "GTM Sales", count: 5 },
  { name: "GTM Marketing", count: 5 },
  { name: "GTM Partners", count: 4 },
  { name: "CEO Team", count: 3 },
  { name: "CFO Team", count: 3 },
  { name: "COO Team", count: 3 },
  { name: "CPO Team", count: 3 },
  { name: "CTO Team", count: 3 },
  { name: "GTM Success", count: 3 },
  { name: "External", count: 3 },
  { name: "GTM Ops", count: 2 },
];

const intellectualTraditions = [
  { tradition: "Facilitation", protocols: 10, depth: 8, novelty: 6 },
  { tradition: "Intelligence", protocols: 3, depth: 9, novelty: 7 },
  { tradition: "Game Theory", protocols: 3, depth: 7, novelty: 8 },
  { tradition: "Systems", protocols: 2, depth: 9, novelty: 7 },
  { tradition: "Design", protocols: 2, depth: 6, novelty: 6 },
  { tradition: "Philosophy", protocols: 10, depth: 10, novelty: 10 },
  { tradition: "Cognitive Sci", protocols: 10, depth: 9, novelty: 9 },
];

const evalDimensions = [
  { dimension: "Answer Quality", rubric1: 9, rubric2: 0 },
  { dimension: "Reasoning Depth", rubric1: 8, rubric2: 8 },
  { dimension: "Tension Surfacing", rubric1: 7, rubric2: 7 },
  { dimension: "Actionability", rubric1: 9, rubric2: 9 },
  { dimension: "Novelty", rubric1: 6, rubric2: 0 },
  { dimension: "Coherence", rubric1: 8, rubric2: 0 },
  { dimension: "Specificity", rubric1: 0, rubric2: 8 },
  { dimension: "Consistency", rubric1: 0, rubric2: 7 },
  { dimension: "Constraints", rubric1: 0, rubric2: 8 },
  { dimension: "Completeness", rubric1: 0, rubric2: 7 },
];

const systemArchitecture = [
  { name: "Agents", value: 56, category: "core" },
  { name: "Protocols", value: 48, category: "core" },
  { name: "Eval Reports", value: 7, category: "output" },
  { name: "Benchmark Qs", value: 34, category: "eval" },
  { name: "Judge Models", value: 3, category: "eval" },
  { name: "Rubric Dims", value: 13, category: "eval" },
  { name: "Tool Integrations", value: 6, category: "infra" },
  { name: "n8n Workflows", value: 5, category: "infra" },
];

const wave2Protocols = [
  { name: "Six Hats", origin: "de Bono", type: "Thinking" },
  { name: "PMI", origin: "de Bono", type: "Thinking" },
  { name: "Combinatorial", origin: "Llull", type: "Philosophy" },
  { name: "Language Game", origin: "Wittgenstein", type: "Philosophy" },
  { name: "Forecast", origin: "Tetlock", type: "Cognitive" },
  { name: "Evaporation Cloud", origin: "Goldratt (TOC)", type: "Systems" },
  { name: "Reality Tree", origin: "Goldratt (TOC)", type: "Systems" },
  { name: "Satisficing", origin: "Simon", type: "Cognitive" },
  { name: "Abduction", origin: "Peirce", type: "Philosophy" },
  { name: "Sublation", origin: "Hegel", type: "Philosophy" },
  { name: "Premortem", origin: "Klein", type: "Cognitive" },
  { name: "Falsification", origin: "Popper", type: "Philosophy" },
  { name: "OODA Loop", origin: "Boyd", type: "Military" },
  { name: "Decision Quality", origin: "Annie Duke", type: "Cognitive" },
  { name: "Square of Opp.", origin: "Aristotle", type: "Philosophy" },
  { name: "Audit", origin: "Leibniz", type: "Philosophy" },
  { name: "Pre-Router", origin: "Kant", type: "Philosophy" },
  { name: "Weights", origin: "Whitehead", type: "Philosophy" },
  { name: "Incubation", origin: "Wallas", type: "Cognitive" },
  { name: "Lookback", origin: "Pólya", type: "Math/Logic" },
];

// ─── COMPONENTS ─────────────────────────────────────────────────────

const StatCard = ({ label, value, sub, color = COLORS.primary }) => (
  <div className="bg-white rounded-xl border border-gray-200 p-5 flex flex-col items-center justify-center shadow-sm">
    <div className="text-3xl font-bold" style={{ color }}>{value}</div>
    <div className="text-sm font-semibold text-gray-700 mt-1">{label}</div>
    {sub && <div className="text-xs text-gray-400 mt-0.5">{sub}</div>}
  </div>
);

const SectionTitle = ({ children, sub }) => (
  <div className="mb-4 mt-8">
    <h2 className="text-xl font-bold text-gray-800">{children}</h2>
    {sub && <p className="text-sm text-gray-500 mt-1">{sub}</p>}
  </div>
);

const ChartCard = ({ children, title, className = "" }) => (
  <div className={`bg-white rounded-xl border border-gray-200 p-5 shadow-sm ${className}`}>
    {title && <h3 className="text-sm font-semibold text-gray-600 mb-3">{title}</h3>}
    {children}
  </div>
);

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-white border border-gray-200 rounded-lg p-3 shadow-lg text-sm">
      <p className="font-semibold text-gray-800 mb-1">{label}</p>
      {payload.map((p, i) => (
        <p key={i} style={{ color: p.color }} className="text-xs">
          {p.name}: <span className="font-bold">{p.value.toLocaleString()}</span>
        </p>
      ))}
    </div>
  );
};

const RADIAN = Math.PI / 180;
const renderCustomizedLabel = ({ cx, cy, midAngle, innerRadius, outerRadius, percent, name }) => {
  if (percent < 0.05) return null;
  const radius = innerRadius + (outerRadius - innerRadius) * 0.5;
  const x = cx + radius * Math.cos(-midAngle * RADIAN);
  const y = cy + radius * Math.sin(-midAngle * RADIAN);
  return (
    <text x={x} y={y} fill="white" textAnchor="middle" dominantBaseline="central" fontSize={11} fontWeight="bold">
      {`${(percent * 100).toFixed(0)}%`}
    </text>
  );
};

// ─── TAB NAV ────────────────────────────────────────────────────────
const tabs = [
  { id: "overview", label: "Overview" },
  { id: "protocols", label: "Protocols" },
  { id: "agents", label: "Agents" },
  { id: "evals", label: "Evaluation" },
  { id: "wave2", label: "Wave 2 Deep Dive" },
];

// ─── MAIN ───────────────────────────────────────────────────────────
export default function Dashboard() {
  const [activeTab, setActiveTab] = useState("overview");

  return (
    <div className="min-h-screen" style={{ background: COLORS.bg }}>
      {/* Header */}
      <div className="border-b border-gray-200 bg-white">
        <div className="max-w-6xl mx-auto px-6 py-6">
          <div className="flex items-center gap-3 mb-1">
            <div className="w-8 h-8 rounded-lg flex items-center justify-center text-white font-bold text-sm" style={{ background: COLORS.primary }}>CE</div>
            <h1 className="text-2xl font-bold text-gray-900">Cardinal Element — Repository Analytics</h1>
          </div>
          <p className="text-sm text-gray-500 ml-11">Multi-agent AI platform for strategic advisory — monorepo analysis as of Feb 27, 2026</p>
        </div>
        {/* Tabs */}
        <div className="max-w-6xl mx-auto px-6 flex gap-1">
          {tabs.map(t => (
            <button
              key={t.id}
              onClick={() => setActiveTab(t.id)}
              className={`px-4 py-2.5 text-sm font-medium rounded-t-lg transition-colors ${
                activeTab === t.id
                  ? "bg-gray-100 text-gray-900 border-b-2"
                  : "text-gray-500 hover:text-gray-700 hover:bg-gray-50"
              }`}
              style={activeTab === t.id ? { borderBottomColor: COLORS.accent } : {}}
            >
              {t.label}
            </button>
          ))}
        </div>
      </div>

      <div className="max-w-6xl mx-auto px-6 pb-12">
        {/* ═══════════ OVERVIEW ═══════════ */}
        {activeTab === "overview" && (
          <>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-6">
              <StatCard label="Total Protocols" value="48" sub="9 categories" color={COLORS.primary} />
              <StatCard label="AI Agents" value="56" sub="14 categories" color={COLORS.secondary} />
              <StatCard label="Python Files" value="375" sub="Excl. venvs" color={COLORS.accent} />
              <StatCard label="Lines of Code" value="55.9K" sub="Source only" color={COLORS.cool} />
            </div>

            <SectionTitle sub="Lines of code, file count, tests, and dependencies by project">Project Scale Comparison</SectionTitle>
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <ChartCard title="Lines of Code by Project">
                <ResponsiveContainer width="100%" height={280}>
                  <BarChart data={projectScale} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                    <XAxis dataKey="name" tick={{ fontSize: 12 }} />
                    <YAxis tick={{ fontSize: 11 }} tickFormatter={v => `${(v/1000).toFixed(0)}K`} />
                    <Tooltip content={<CustomTooltip />} />
                    <Bar dataKey="loc" name="Lines of Code" fill={COLORS.primary} radius={[6, 6, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </ChartCard>

              <ChartCard title="Files, Tests & Dependencies">
                <ResponsiveContainer width="100%" height={280}>
                  <BarChart data={projectScale} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                    <XAxis dataKey="name" tick={{ fontSize: 12 }} />
                    <YAxis tick={{ fontSize: 11 }} />
                    <Tooltip content={<CustomTooltip />} />
                    <Legend iconType="circle" wrapperStyle={{ fontSize: 11 }} />
                    <Bar dataKey="files" name="Python Files" fill={COLORS.secondary} radius={[4, 4, 0, 0]} />
                    <Bar dataKey="tests" name="Test Files" fill={COLORS.warm} radius={[4, 4, 0, 0]} />
                    <Bar dataKey="deps" name="Dependencies" fill={COLORS.light} radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </ChartCard>
            </div>

            <SectionTitle sub="What the platform includes at a glance">System Inventory</SectionTitle>
            <ChartCard>
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={systemArchitecture} layout="vertical" margin={{ top: 5, right: 30, left: 90, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                  <XAxis type="number" tick={{ fontSize: 11 }} />
                  <YAxis type="category" dataKey="name" tick={{ fontSize: 12 }} width={85} />
                  <Tooltip content={<CustomTooltip />} />
                  <Bar dataKey="value" name="Count" fill={COLORS.cool} radius={[0, 6, 6, 0]}>
                    {systemArchitecture.map((entry, index) => (
                      <Cell key={index} fill={
                        entry.category === "core" ? COLORS.primary :
                        entry.category === "eval" ? COLORS.secondary :
                        COLORS.warm
                      } />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </ChartCard>
          </>
        )}

        {/* ═══════════ PROTOCOLS ═══════════ */}
        {activeTab === "protocols" && (
          <>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-6">
              <StatCard label="Total Protocols" value="48" color={COLORS.primary} />
              <StatCard label="Categories" value="9" color={COLORS.secondary} />
              <StatCard label="Wave 1" value="28" sub="Established methods" color={COLORS.cool} />
              <StatCard label="Wave 2" value="20" sub="Philosophy & CogSci" color={COLORS.accent} />
            </div>

            <SectionTitle sub="Distribution of 48 protocols across intellectual traditions">Protocol Categories</SectionTitle>
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <ChartCard title="Protocol Distribution">
                <ResponsiveContainer width="100%" height={340}>
                  <PieChart>
                    <Pie
                      data={protocolCategories}
                      cx="50%" cy="50%"
                      outerRadius={130}
                      innerRadius={55}
                      dataKey="value"
                      labelLine={false}
                      label={renderCustomizedLabel}
                    >
                      {protocolCategories.map((_, i) => (
                        <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip formatter={(value, name) => [`${value} protocols`, name]} />
                  </PieChart>
                </ResponsiveContainer>
                <div className="flex flex-wrap gap-2 mt-2 justify-center">
                  {protocolCategories.map((c, i) => (
                    <span key={i} className="flex items-center gap-1.5 text-xs text-gray-600">
                      <span className="w-2.5 h-2.5 rounded-full" style={{ background: PIE_COLORS[i] }}></span>
                      {c.name}
                    </span>
                  ))}
                </div>
              </ChartCard>

              <ChartCard title="Intellectual Depth vs. Novelty">
                <ResponsiveContainer width="100%" height={340}>
                  <RadarChart data={intellectualTraditions}>
                    <PolarGrid stroke="#e5e7eb" />
                    <PolarAngleAxis dataKey="tradition" tick={{ fontSize: 11 }} />
                    <PolarRadiusAxis angle={30} domain={[0, 10]} tick={{ fontSize: 9 }} />
                    <Radar name="Protocols" dataKey="protocols" stroke={COLORS.primary} fill={COLORS.primary} fillOpacity={0.15} />
                    <Radar name="Depth" dataKey="depth" stroke={COLORS.secondary} fill={COLORS.secondary} fillOpacity={0.15} />
                    <Radar name="Novelty" dataKey="novelty" stroke={COLORS.accent} fill={COLORS.accent} fillOpacity={0.15} />
                    <Legend iconType="circle" wrapperStyle={{ fontSize: 11 }} />
                    <Tooltip />
                  </RadarChart>
                </ResponsiveContainer>
              </ChartCard>
            </div>

            <SectionTitle sub="Detailed breakdown by category with descriptions">Protocol Inventory</SectionTitle>
            <ChartCard>
              <ResponsiveContainer width="100%" height={320}>
                <BarChart data={protocolCategories} layout="vertical" margin={{ top: 5, right: 30, left: 120, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                  <XAxis type="number" tick={{ fontSize: 11 }} />
                  <YAxis type="category" dataKey="name" tick={{ fontSize: 11 }} width={115} />
                  <Tooltip content={({ active, payload }) => {
                    if (!active || !payload?.length) return null;
                    const d = payload[0].payload;
                    return (
                      <div className="bg-white border border-gray-200 rounded-lg p-3 shadow-lg text-sm">
                        <p className="font-semibold">{d.name}</p>
                        <p className="text-xs text-gray-500">{d.desc}</p>
                        <p className="text-xs font-bold mt-1">{d.value} protocols</p>
                      </div>
                    );
                  }} />
                  <Bar dataKey="value" name="Protocols" fill={COLORS.secondary} radius={[0, 6, 6, 0]}>
                    {protocolCategories.map((_, i) => (
                      <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </ChartCard>
          </>
        )}

        {/* ═══════════ AGENTS ═══════════ */}
        {activeTab === "agents" && (
          <>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-6">
              <StatCard label="Total Agents" value="56" color={COLORS.primary} />
              <StatCard label="Categories" value="14" color={COLORS.secondary} />
              <StatCard label="Executive" value="7" sub="C-Suite core" color={COLORS.accent} />
              <StatCard label="GTM Agents" value="22" sub="Go-to-market" color={COLORS.cool} />
            </div>

            <SectionTitle sub="56 specialized agents across 14 organizational categories">Agent Registry Distribution</SectionTitle>
            <ChartCard>
              <ResponsiveContainer width="100%" height={460}>
                <BarChart data={agentCategories} layout="vertical" margin={{ top: 5, right: 30, left: 100, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                  <XAxis type="number" tick={{ fontSize: 11 }} domain={[0, 8]} />
                  <YAxis type="category" dataKey="name" tick={{ fontSize: 11 }} width={95} />
                  <Tooltip content={<CustomTooltip />} />
                  <Bar dataKey="count" name="Agents" fill={COLORS.primary} radius={[0, 6, 6, 0]}>
                    {agentCategories.map((entry, i) => (
                      <Cell key={i} fill={
                        entry.name === "Executive" ? COLORS.accent :
                        entry.name.startsWith("GTM") ? COLORS.secondary :
                        entry.name.includes("Team") ? COLORS.primary :
                        COLORS.warm
                      } />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </ChartCard>

            <SectionTitle sub="Breakdown by organizational function">Agent Coverage by Function</SectionTitle>
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <ChartCard title="Agent Type Breakdown">
                <ResponsiveContainer width="100%" height={300}>
                  <PieChart>
                    <Pie
                      data={[
                        { name: "Executive C-Suite", value: 7 },
                        { name: "C-Suite Teams", value: 18 },
                        { name: "GTM Org", value: 22 },
                        { name: "GTM Ops", value: 2 },
                        { name: "External / Advisory", value: 3 },
                      ]}
                      cx="50%" cy="50%"
                      outerRadius={110}
                      innerRadius={45}
                      dataKey="value"
                      labelLine={false}
                      label={renderCustomizedLabel}
                    >
                      {[COLORS.accent, COLORS.primary, COLORS.secondary, COLORS.cool, COLORS.warm].map((c, i) => (
                        <Cell key={i} fill={c} />
                      ))}
                    </Pie>
                    <Tooltip formatter={(value, name) => [`${value} agents`, name]} />
                    <Legend iconType="circle" wrapperStyle={{ fontSize: 11 }} />
                  </PieChart>
                </ResponsiveContainer>
              </ChartCard>

              <ChartCard title="Agent Depth per Executive">
                <div className="space-y-3 mt-2">
                  {[
                    { exec: "CEO", team: 3, color: COLORS.accent },
                    { exec: "CFO", team: 3, color: COLORS.primary },
                    { exec: "CTO", team: 3, color: COLORS.secondary },
                    { exec: "CMO", team: 6, color: COLORS.warm },
                    { exec: "COO", team: 3, color: COLORS.cool },
                    { exec: "CPO", team: 3, color: COLORS.light },
                    { exec: "CRO", team: 22, color: "#457b9d" },
                  ].map((e, i) => (
                    <div key={i} className="flex items-center gap-3">
                      <span className="text-xs font-bold w-8 text-right text-gray-600">{e.exec}</span>
                      <div className="flex-1 bg-gray-100 rounded-full h-5 overflow-hidden">
                        <div
                          className="h-full rounded-full flex items-center justify-end pr-2"
                          style={{ width: `${Math.min((e.team / 22) * 100, 100)}%`, background: e.color }}
                        >
                          <span className="text-xs text-white font-bold">{e.team === 22 ? "22 (GTM org)" : `+${e.team} sub-agents`}</span>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
                <p className="text-xs text-gray-400 mt-3">CRO oversees the full 22-agent GTM organization spanning sales, marketing, partners, success, and ops.</p>
              </ChartCard>
            </div>
          </>
        )}

        {/* ═══════════ EVALUATION ═══════════ */}
        {activeTab === "evals" && (
          <>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-6">
              <StatCard label="Eval Reports" value="7" sub="Completed runs" color={COLORS.primary} />
              <StatCard label="Judge Models" value="3" sub="Claude, GPT, Gemini" color={COLORS.secondary} />
              <StatCard label="Rubric Dimensions" value="13" sub="Across 2 rubrics" color={COLORS.accent} />
              <StatCard label="Benchmark Qs" value="34" sub="8 problem types" color={COLORS.cool} />
            </div>

            <SectionTitle sub="13 evaluation dimensions across two rubrics measuring protocol output quality">Evaluation Rubric Coverage</SectionTitle>
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <ChartCard title="Rubric Dimensions Comparison">
                <ResponsiveContainer width="100%" height={360}>
                  <BarChart data={evalDimensions} layout="vertical" margin={{ top: 5, right: 20, left: 110, bottom: 5 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                    <XAxis type="number" domain={[0, 10]} tick={{ fontSize: 11 }} />
                    <YAxis type="category" dataKey="dimension" tick={{ fontSize: 11 }} width={105} />
                    <Tooltip content={<CustomTooltip />} />
                    <Legend iconType="circle" wrapperStyle={{ fontSize: 11 }} />
                    <Bar dataKey="rubric1" name="Protocol Quality" fill={COLORS.primary} radius={[0, 4, 4, 0]} />
                    <Bar dataKey="rubric2" name="Strategic Advisory" fill={COLORS.accent} radius={[0, 4, 4, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </ChartCard>

              <ChartCard title="Multi-Model Judge Architecture">
                <div className="space-y-4 mt-2">
                  {[
                    { model: "Claude Opus 4.6", provider: "Anthropic", cost: "$15 / $75 per M tokens", color: COLORS.accent },
                    { model: "GPT-5.2", provider: "OpenAI", cost: "$2.50 / $10 per M tokens", color: COLORS.secondary },
                    { model: "Gemini 3.1 Pro", provider: "Google", cost: "$1.25 / $5 per M tokens", color: COLORS.primary },
                  ].map((j, i) => (
                    <div key={i} className="border border-gray-200 rounded-lg p-4">
                      <div className="flex items-center gap-2">
                        <div className="w-3 h-3 rounded-full" style={{ background: j.color }}></div>
                        <span className="font-semibold text-sm text-gray-800">{j.model}</span>
                      </div>
                      <div className="mt-1 flex justify-between text-xs text-gray-500">
                        <span>{j.provider}</span>
                        <span>{j.cost}</span>
                      </div>
                    </div>
                  ))}
                  <div className="bg-gray-50 rounded-lg p-3 text-xs text-gray-600 border border-gray-100">
                    <p className="font-semibold mb-1">Bias Mitigations</p>
                    <div className="grid grid-cols-2 gap-1">
                      <span>Response anonymization</span>
                      <span>Metadata stripping</span>
                      <span>Random ordering</span>
                      <span>Forced ranking</span>
                      <span>Inter-rater agreement</span>
                      <span>Borda count aggregation</span>
                    </div>
                  </div>
                </div>
              </ChartCard>
            </div>

            <SectionTitle sub="7 completed evaluation runs with progressive complexity">Evaluation Run History</SectionTitle>
            <ChartCard>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-gray-200">
                      <th className="text-left py-2 text-xs font-semibold text-gray-500">Run</th>
                      <th className="text-left py-2 text-xs font-semibold text-gray-500">Type</th>
                      <th className="text-center py-2 text-xs font-semibold text-gray-500">Scale</th>
                      <th className="text-left py-2 text-xs font-semibold text-gray-500">Date</th>
                    </tr>
                  </thead>
                  <tbody>
                    {[
                      { name: "Q2.1 Initial", type: "Single question", scale: "1×1", date: "Feb 22" },
                      { name: "Q2.1 Retry 1", type: "Single question", scale: "1×1", date: "Feb 22" },
                      { name: "Q2.1 Retry 2", type: "Single question", scale: "1×1", date: "Feb 22" },
                      { name: "Smoke Test", type: "Integration", scale: "2×2", date: "Feb 22" },
                      { name: "Multi-Model v1", type: "Full eval", scale: "5×5", date: "Feb 22" },
                      { name: "Multi-Model v2", type: "Full eval", scale: "5×5", date: "Feb 22" },
                      { name: "Multi-Model v3", type: "Full eval", scale: "5×5", date: "Feb 22" },
                    ].map((r, i) => (
                      <tr key={i} className="border-b border-gray-100">
                        <td className="py-2 font-medium text-gray-800">{r.name}</td>
                        <td className="py-2 text-gray-600">{r.type}</td>
                        <td className="py-2 text-center">
                          <span className="bg-gray-100 text-gray-600 text-xs px-2 py-0.5 rounded-full font-mono">{r.scale}</span>
                        </td>
                        <td className="py-2 text-gray-500">{r.date}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </ChartCard>
          </>
        )}

        {/* ═══════════ WAVE 2 ═══════════ */}
        {activeTab === "wave2" && (
          <>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-6">
              <StatCard label="Wave 2 Protocols" value="20" color={COLORS.primary} />
              <StatCard label="Unique Thinkers" value="16" sub="Referenced" color={COLORS.secondary} />
              <StatCard label="Traditions" value="6" sub="Philosophy to military" color={COLORS.accent} />
              <StatCard label="Oldest Source" value="Aristotle" sub="384 BC" color={COLORS.cool} />
            </div>

            <SectionTitle sub="20 protocols drawing from 2,400 years of structured reasoning traditions">Wave 2 Research Protocols</SectionTitle>
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <ChartCard title="Protocols by Intellectual Origin">
                <ResponsiveContainer width="100%" height={320}>
                  <PieChart>
                    <Pie
                      data={[
                        { name: "Philosophy", value: 9 },
                        { name: "Cognitive Science", value: 5 },
                        { name: "Systems / TOC", value: 2 },
                        { name: "Thinking Methods", value: 2 },
                        { name: "Military Strategy", value: 1 },
                        { name: "Mathematics", value: 1 },
                      ]}
                      cx="50%" cy="50%"
                      outerRadius={115}
                      innerRadius={50}
                      dataKey="value"
                      labelLine={false}
                      label={renderCustomizedLabel}
                    >
                      {PIE_COLORS.map((c, i) => <Cell key={i} fill={c} />)}
                    </Pie>
                    <Tooltip formatter={(value, name) => [`${value} protocols`, name]} />
                    <Legend iconType="circle" wrapperStyle={{ fontSize: 11 }} />
                  </PieChart>
                </ResponsiveContainer>
              </ChartCard>

              <ChartCard title="Full Wave 2 Protocol Map">
                <div className="grid grid-cols-2 gap-2 max-h-80 overflow-y-auto pr-2">
                  {wave2Protocols.map((p, i) => (
                    <div key={i} className="flex items-start gap-2 border border-gray-100 rounded-lg p-2.5">
                      <span className="text-xs font-mono text-gray-400 mt-0.5">P{28 + i}</span>
                      <div>
                        <p className="text-xs font-semibold text-gray-800">{p.name}</p>
                        <p className="text-xs text-gray-500">{p.origin}</p>
                        <span
                          className="text-xs px-1.5 py-0.5 rounded-full mt-0.5 inline-block"
                          style={{
                            background:
                              p.type === "Philosophy" ? "#264653" :
                              p.type === "Cognitive" ? "#2a9d8f" :
                              p.type === "Systems" ? "#e9c46a" :
                              p.type === "Thinking" ? "#f4a261" :
                              p.type === "Military" ? "#e76f51" :
                              "#457b9d",
                            color: "#fff",
                            fontSize: 10,
                          }}
                        >
                          {p.type}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </ChartCard>
            </div>

            <SectionTitle sub="Historical span of intellectual traditions being encoded as AI coordination protocols">Timeline of Referenced Thinkers</SectionTitle>
            <ChartCard>
              <div className="relative mt-2 mb-4">
                <div className="h-1 bg-gray-200 rounded-full absolute top-3 left-8 right-8"></div>
                <div className="flex justify-between items-start px-4 relative">
                  {[
                    { name: "Aristotle", year: "384 BC", y: 0 },
                    { name: "Llull", year: "1232", y: 30 },
                    { name: "Leibniz", year: "1646", y: 0 },
                    { name: "Kant", year: "1724", y: 30 },
                    { name: "Hegel", year: "1770", y: 0 },
                    { name: "Peirce", year: "1839", y: 30 },
                    { name: "Whitehead", year: "1861", y: 0 },
                    { name: "Wittgenstein", year: "1889", y: 30 },
                    { name: "Pólya", year: "1945", y: 0 },
                    { name: "Simon", year: "1956", y: 30 },
                    { name: "de Bono", year: "1967", y: 0 },
                    { name: "Boyd", year: "1976", y: 30 },
                    { name: "Goldratt", year: "1984", y: 0 },
                    { name: "Klein", year: "1998", y: 30 },
                    { name: "Tetlock", year: "2005", y: 0 },
                    { name: "Duke", year: "2018", y: 30 },
                  ].map((t, i) => (
                    <div key={i} className="flex flex-col items-center" style={{ marginTop: t.y }}>
                      <div className="w-2.5 h-2.5 rounded-full bg-white border-2 z-10" style={{ borderColor: PIE_COLORS[i % PIE_COLORS.length] }}></div>
                      <span className="text-xs font-semibold text-gray-700 mt-1 whitespace-nowrap" style={{ fontSize: 9 }}>{t.name}</span>
                      <span className="text-xs text-gray-400" style={{ fontSize: 8 }}>{t.year}</span>
                    </div>
                  ))}
                </div>
              </div>
              <p className="text-xs text-gray-500 text-center mt-8">
                2,400 years of structured reasoning — from Aristotle's Square of Opposition to Annie Duke's decision quality frameworks — encoded as multi-agent coordination protocols.
              </p>
            </ChartCard>
          </>
        )}

        {/* Footer */}
        <div className="mt-12 pt-6 border-t border-gray-200 text-center">
          <p className="text-xs text-gray-400">Cardinal Element — AI-Native Growth Architecture | Repository analytics generated Feb 27, 2026</p>
        </div>
      </div>
    </div>
  );
}