import { useEffect, useRef, useState } from 'react'
import mermaid from 'mermaid'
import type { ProtocolStages } from '../types'
import { api } from '../api'

mermaid.initialize({
  startOnLoad: false,
  theme: 'base',
  themeVariables: {
    primaryColor: '#3b82f6',
    primaryTextColor: '#1e293b',
    lineColor: '#94a3b8',
    fontSize: '14px',
  },
  flowchart: { curve: 'basis' },
})

let renderCounter = 0

interface Props {
  protocolKey: string
}

export default function ProtocolDiagram({ protocolKey }: Props) {
  const containerRef = useRef<HTMLDivElement>(null)
  const [data, setData] = useState<ProtocolStages | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    setLoading(true)
    setError(null)
    api.protocols.stages(protocolKey)
      .then(setData)
      .catch((e) => setError((e as Error).message))
      .finally(() => setLoading(false))
  }, [protocolKey])

  useEffect(() => {
    if (!data || !containerRef.current) return

    const stages = data.stages
    const lines: string[] = ['flowchart TD']

    const nodeId = (name: string) => name.replace(/[^a-zA-Z0-9]/g, '_')

    stages.forEach((stage) => {
      const id = nodeId(stage.name)
      const label = stage.agents_filter ? `${stage.name}<br/><small>${stage.agents_filter}</small>` : stage.name

      if (stage.stage_type === 'agent') {
        lines.push(`    ${id}([${JSON.stringify(label)}])`)
      } else if (stage.stage_type === 'synthesis') {
        lines.push(`    ${id}{{${JSON.stringify(label)}}}`)
      } else {
        lines.push(`    ${id}[${JSON.stringify(label)}]`)
      }
    })

    stages.forEach((stage) => {
      const targetId = nodeId(stage.name)
      stage.depends_on.forEach((dep) => {
        const sourceId = nodeId(dep)
        lines.push(`    ${sourceId} --> ${targetId}`)
      })
    })

    stages.forEach((stage) => {
      const id = nodeId(stage.name)
      if (stage.stage_type === 'agent') {
        lines.push(`    style ${id} fill:#dbeafe,stroke:#3b82f6,color:#1e40af`)
      } else if (stage.stage_type === 'synthesis') {
        lines.push(`    style ${id} fill:#ede9fe,stroke:#8b5cf6,color:#6d28d9`)
      } else {
        lines.push(`    style ${id} fill:#fef3c7,stroke:#f59e0b,color:#92400e`)
      }
    })

    const definition = lines.join('\n')

    // Mermaid.render produces SVG from our own deterministic DSL input (stage definitions),
    // not from untrusted external content, so innerHTML assignment is safe here.
    mermaid.render(`mermaid_${++renderCounter}`, definition).then(({ svg }) => {
      if (containerRef.current) {
        containerRef.current.innerHTML = svg
      }
    }).catch((err) => {
      setError(`Diagram render error: ${err.message}`)
    })
  }, [data, protocolKey])

  if (loading) return <p className="text-sm text-text-muted py-4">Loading diagram...</p>
  if (error) return <p className="text-sm text-red-500 py-4">Error: {error}</p>
  if (!data) return null

  return (
    <div className="mt-4">
      <div ref={containerRef} className="bg-white border border-border rounded-lg p-4 overflow-x-auto" />
      <div className="flex items-center gap-4 mt-3 text-xs text-text-muted">
        <span className="flex items-center gap-1.5">
          <span className="w-3 h-3 rounded-full bg-blue-200 border border-blue-400" />
          Agent Stage
        </span>
        <span className="flex items-center gap-1.5">
          <span className="w-3 h-3 rounded bg-amber-200 border border-amber-400" />
          Mechanical
        </span>
        <span className="flex items-center gap-1.5">
          <span className="w-3 h-3 rounded bg-violet-200 border border-violet-400" style={{ clipPath: 'polygon(50% 0%, 100% 25%, 100% 75%, 50% 100%, 0% 75%, 0% 25%)' }} />
          Synthesis
        </span>
      </div>
    </div>
  )
}
