import { useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

// ── Types ─────────────────────────────────────────────────────────────────────

export interface AgentContribution {
  agent_key: string
  agent_name: string
  text: string
  cost_usd: number
  model: string
  tool_calls: unknown[]
}

export interface ProtocolReportData {
  participants: string[]
  executive_summary: string
  key_findings: string[]
  disagreements: string[]
  confidence_score: number
  confidence_label: string
  synthesis: string
  agent_contributions: AgentContribution[]
  cost_summary: Record<string, unknown>
  metadata: Record<string, unknown>
}

// ── Confidence Indicator ──────────────────────────────────────────────────────

function ConfidenceIndicator({ score, label }: { score: number; label: string }) {
  const dotColor = (idx: number): string => {
    if (score === 0) return 'bg-gray-300'
    const filled = idx < score
    if (!filled) return 'bg-gray-200 border border-gray-300'
    if (score >= 4) return 'bg-green-500'
    if (score === 3) return 'bg-yellow-500'
    return 'bg-red-500'
  }

  return (
    <div className="flex items-center gap-3" data-testid="confidence-indicator">
      <div className="flex items-center gap-1.5">
        {Array.from({ length: 5 }, (_, i) => (
          <span
            key={i}
            className={`inline-block w-3.5 h-3.5 rounded-full ${dotColor(i)}`}
            aria-hidden="true"
          />
        ))}
      </div>
      <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
        {label}
      </span>
      <span className="text-xs text-gray-400">({score}/5)</span>
    </div>
  )
}

// ── Agent Contribution Card ───────────────────────────────────────────────────

function AgentCard({ contribution }: { contribution: AgentContribution }) {
  const [expanded, setExpanded] = useState(false)
  const displayName = contribution.agent_name || contribution.agent_key

  return (
    <div className="border border-gray-200 dark:border-gray-700 rounded-xl overflow-hidden">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between px-4 py-3 bg-gray-50 dark:bg-gray-800/60 hover:bg-gray-100 dark:hover:bg-gray-800 transition text-left"
      >
        <div className="flex items-center gap-3">
          <span className="font-medium text-sm text-gray-800 dark:text-gray-200">{displayName}</span>
          {contribution.model && (
            <span className="px-2 py-0.5 rounded-full text-[10px] font-medium bg-violet-100 dark:bg-violet-900/30 text-violet-700 dark:text-violet-300 border border-violet-200 dark:border-violet-700">
              {contribution.model.length > 28 ? contribution.model.slice(0, 28) + '…' : contribution.model}
            </span>
          )}
          {contribution.cost_usd > 0 && (
            <span className="px-2 py-0.5 rounded-full text-[10px] font-medium bg-emerald-100 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-700">
              ${contribution.cost_usd.toFixed(4)}
            </span>
          )}
        </div>
        <span className="text-xs text-gray-400">{expanded ? '▲' : '▼'}</span>
      </button>
      {expanded && (
        <div className="px-4 py-3 text-sm text-gray-700 dark:text-gray-300">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{contribution.text}</ReactMarkdown>
        </div>
      )}
    </div>
  )
}

// ── Main Component ────────────────────────────────────────────────────────────

export function ProtocolReport({ report }: { report: ProtocolReportData }) {
  const totalCost = typeof report.cost_summary?.total_usd === 'number'
    ? (report.cost_summary.total_usd as number)
    : 0
  const callCount = typeof report.cost_summary?.calls === 'number'
    ? (report.cost_summary.calls as number)
    : 0

  return (
    <div className="space-y-6">

      {/* Executive Summary */}
      <div
        className="bg-blue-50 dark:bg-blue-950/20 border border-blue-200 dark:border-blue-800 rounded-xl p-5"
        data-testid="executive-summary"
      >
        <p className="text-xs font-bold tracking-wider uppercase text-blue-600 dark:text-blue-400 mb-2">
          Executive Summary
        </p>
        <p className="text-sm text-gray-800 dark:text-gray-200 leading-relaxed">
          {report.executive_summary}
        </p>
      </div>

      {/* Confidence Indicator */}
      <ConfidenceIndicator score={report.confidence_score} label={report.confidence_label} />

      {/* Key Findings */}
      {report.key_findings.length > 0 && (
        <div data-testid="key-findings">
          <p className="text-xs font-bold tracking-wider uppercase text-gray-500 dark:text-gray-400 mb-3">
            Key Findings
          </p>
          <ul className="space-y-2">
            {report.key_findings.map((finding, i) => (
              <li key={i} className="flex items-start gap-2 text-sm text-gray-700 dark:text-gray-300">
                <span className="mt-1 text-blue-500 flex-shrink-0">▸</span>
                <span>{finding}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Disagreements — amber/warning styling, visually distinct */}
      {report.disagreements.length > 0 && (
        <div
          className="border-l-4 border-amber-500 bg-amber-50 dark:bg-amber-950/20 rounded-r-xl p-4"
          data-testid="disagreements"
        >
          <p className="text-xs font-bold tracking-wider uppercase text-amber-700 dark:text-amber-400 mb-3">
            Areas of Disagreement
          </p>
          <div className="space-y-2">
            {report.disagreements.map((d, i) => (
              <p key={i} className="text-sm text-amber-900 dark:text-amber-200 leading-relaxed">
                {d}
              </p>
            ))}
          </div>
        </div>
      )}

      {/* Agent Contributions */}
      {report.agent_contributions.length > 0 && (
        <div data-testid="agent-contributions">
          <p className="text-xs font-bold tracking-wider uppercase text-gray-500 dark:text-gray-400 mb-3">
            Agent Contributions
          </p>
          <div className="space-y-3">
            {report.agent_contributions.map((c) => (
              <AgentCard key={c.agent_key} contribution={c} />
            ))}
          </div>
        </div>
      )}

      {/* Cost Summary */}
      <div
        className="bg-gray-50 dark:bg-gray-800/40 border border-gray-200 dark:border-gray-700 rounded-xl p-4"
        data-testid="cost-summary"
      >
        <p className="text-xs font-bold tracking-wider uppercase text-gray-500 dark:text-gray-400 mb-3">
          Cost Summary
        </p>
        <div className="flex items-baseline gap-2">
          <span className="text-xl font-semibold text-gray-800 dark:text-gray-200">
            ${totalCost.toFixed(4)}
          </span>
          {callCount > 0 && (
            <span className="text-xs text-gray-500">{callCount} API calls</span>
          )}
        </div>
      </div>

    </div>
  )
}
