import { useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useRunStore } from '../stores/runStore'
import { ProtocolReport } from '../components/ProtocolReport'
import type { ProtocolReportData } from '../components/ProtocolReport'
import { getApiKey } from '../api'

export default function RunDetail() {
  const { id } = useParams<{ id: string }>()
  const { currentRun, loading, fetchById } = useRunStore()

  useEffect(() => {
    if (id) fetchById(Number(id))
  }, [id, fetchById])

  if (loading) {
    return (
      <div className="max-w-5xl">
        <div className="flex items-center gap-3 py-12 justify-center">
          <span className="w-5 h-5 border-2 border-primary border-t-transparent rounded-full animate-spin" />
          <span className="text-sm text-text-muted">Loading run...</span>
        </div>
      </div>
    )
  }

  if (!currentRun) {
    return (
      <div className="max-w-5xl">
        <p className="text-sm text-text-muted py-12 text-center">Run not found.</p>
        <div className="text-center">
          <Link to="/runs" className="text-sm text-primary hover:underline">Back to Run History</Link>
        </div>
      </div>
    )
  }

  const run = currentRun
  const report = (run as any).protocol_report as ProtocolReportData | null | undefined
  const judgeVerdict = run as any
  let verdict: any = null
  try {
    const raw = (run as any).judge_verdict_json
    if (raw && raw !== '{}') verdict = typeof raw === 'string' ? JSON.parse(raw) : raw
  } catch { /* ignore */ }

  const statusColor: Record<string, string> = {
    completed: 'bg-green-100 text-green-700 border-green-200',
    failed: 'bg-red-100 text-red-700 border-red-200',
    running: 'bg-blue-100 text-blue-700 border-blue-200',
    pending: 'bg-gray-100 text-gray-700 border-gray-200',
    cancelled: 'bg-amber-100 text-amber-700 border-amber-200',
  }

  return (
    <div className="max-w-5xl">
      {/* Breadcrumb */}
      <div className="flex items-center gap-2 mb-6">
        <Link to="/runs" className="text-xs text-text-muted hover:text-primary transition">
          Run History
        </Link>
        <span className="text-xs text-text-muted">/</span>
        <span className="text-xs text-text font-medium">Run #{run.id}</span>
      </div>

      {/* Header */}
      <div className="bg-card border border-border rounded-xl p-6 mb-6">
        <div className="flex items-start justify-between mb-4">
          <div>
            <h1 className="text-xl font-semibold text-text mb-1">
              {run.protocol_key}
            </h1>
            <p className="text-sm text-text-muted">{(run as any).question}</p>
          </div>
          <span className={`px-2.5 py-1 rounded-full text-xs font-semibold border ${statusColor[run.status] || statusColor.pending}`}>
            {run.status}
          </span>
        </div>

        <div className="flex items-center gap-6 text-xs text-text-muted">
          {run.started_at && (
            <span>Started: {new Date(run.started_at).toLocaleString()}</span>
          )}
          {(run as any).completed_at && (
            <span>Completed: {new Date((run as any).completed_at).toLocaleString()}</span>
          )}
          {run.cost_usd > 0 && (
            <span>Cost: <strong className="text-text">${run.cost_usd.toFixed(4)}</strong></span>
          )}
          {(run as any).trace_id && (
            <span>Trace: <code className="text-[10px]">{(run as any).trace_id}</code></span>
          )}
        </div>
      </div>

      {/* Judge Verdict */}
      {verdict && (
        <div className="bg-card border border-border rounded-xl p-5 mb-6">
          <div className="flex items-center justify-between mb-3">
            <span className="text-xs font-bold tracking-wider uppercase text-text-muted">Quality Judge</span>
            <span className={`px-2.5 py-1 rounded-full text-xs font-semibold border ${
              verdict.recommendation === 'accept'
                ? 'bg-green-100 text-green-700 border-green-200'
                : 'bg-amber-100 text-amber-700 border-amber-200'
            }`}>
              {verdict.recommendation === 'accept' ? 'Accepted' : 'Revise'}
            </span>
          </div>
          <div className="flex gap-3 mb-3">
            {(['completeness', 'consistency', 'actionability', 'overall'] as const).map(dim => {
              const score = verdict[dim] ?? 0
              const color = score >= 4 ? 'bg-green-100 text-green-700 border-green-200'
                : score >= 3 ? 'bg-yellow-100 text-yellow-700 border-yellow-200'
                : 'bg-red-100 text-red-700 border-red-200'
              return (
                <div key={dim} className="flex flex-col items-center gap-1">
                  <span className={`w-10 h-10 rounded-lg border flex items-center justify-center text-sm font-bold ${color}`}>
                    {score}
                  </span>
                  <span className="text-[10px] text-text-muted capitalize">{dim}</span>
                </div>
              )
            })}
          </div>
          {verdict.flags?.length > 0 && (
            <div className="space-y-1">
              {verdict.flags.map((flag: string, i: number) => (
                <div key={i} className="flex items-start gap-1.5 text-xs text-amber-700">
                  <span className="mt-0.5 flex-shrink-0">&#9888;</span>
                  <span>{flag}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Protocol Report */}
      {report && (
        <div className="mb-6">
          <div className="flex items-center justify-between mb-3">
            <p className="text-xs font-bold tracking-wider uppercase text-text-muted">Protocol Report</p>
            <div className="flex items-center gap-3">
              <a
                href={`/share/${run.id}`}
                target="_blank"
                rel="noopener noreferrer"
                className="text-xs text-primary hover:underline"
              >
                Share Report
              </a>
              <button
                onClick={async () => {
                  const apiKey = getApiKey()
                  const res = await fetch(`/api/reports/${run.id}/pdf`, {
                    headers: apiKey ? { 'X-API-Key': apiKey } : {},
                  })
                  if (!res.ok) {
                    alert(`PDF generation failed: ${res.status} ${res.statusText}`)
                    return
                  }
                  const blob = await res.blob()
                  const url = URL.createObjectURL(blob)
                  const a = document.createElement('a')
                  a.href = url
                  a.download = `run-${run.protocol_key}-${run.id}.pdf`
                  a.click()
                  URL.revokeObjectURL(url)
                }}
                className="text-xs text-primary hover:underline"
              >
                Download PDF
              </button>
            </div>
          </div>
          <ProtocolReport report={report} />
        </div>
      )}

      {/* Agent Outputs (raw, if no structured report) */}
      {!report && run.outputs && run.outputs.length > 0 && (
        <div className="space-y-4 mb-6">
          <p className="text-xs font-bold tracking-wider uppercase text-text-muted">Agent Outputs</p>
          {run.outputs.map((out: any) => (
            <div key={out.id} className="bg-card border border-border rounded-xl p-4">
              <div className="flex items-center gap-2 mb-2">
                <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-elevated text-text-muted">
                  {out.agent_key}
                </span>
                {out.model && (
                  <span className="text-[10px] text-text-muted font-mono">{out.model}</span>
                )}
                {out.cost_usd > 0 && (
                  <span className="text-[10px] text-text-muted">${out.cost_usd.toFixed(4)}</span>
                )}
              </div>
              <div className="text-sm text-text whitespace-pre-wrap font-mono leading-relaxed max-h-96 overflow-y-auto">
                {out.output_text}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Error */}
      {run.status === 'failed' && (run as any).error_message && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-4 mb-6">
          <p className="text-sm font-medium text-red-700 mb-1">Error</p>
          <p className="text-xs text-red-600 font-mono whitespace-pre-wrap">
            {(run as any).error_message}
          </p>
        </div>
      )}
    </div>
  )
}
