import { useState, useCallback, useRef } from 'react'
import type { ToolCallEvent } from '../types'

export interface AgentOutputEvent {
  agent_key: string
  agent_name: string
  text: string
  round?: number
  step?: number
}

export interface RunStreamState {
  runId: number | null
  status: 'idle' | 'starting' | 'running' | 'completed' | 'failed'
  agents: { key: string; name: string }[]
  outputs: AgentOutputEvent[]
  toolCalls: ToolCallEvent[]
  synthesis: string
  error: string | null
  elapsedSeconds: number | null
  currentStep: number | null
}

const initial: RunStreamState = {
  runId: null,
  status: 'idle',
  agents: [],
  outputs: [],
  toolCalls: [],
  synthesis: '',
  error: null,
  elapsedSeconds: null,
  currentStep: null,
}

export function useRunStream() {
  const [state, setState] = useState<RunStreamState>(initial)
  const abortRef = useRef<AbortController | null>(null)

  const startProtocolRun = useCallback(async (payload: {
    protocol_key: string
    question: string
    agent_keys: string[]
    thinking_model?: string
    orchestration_model?: string
    rounds?: number | null
    no_tools?: boolean
  }) => {
    abortRef.current?.abort()
    const controller = new AbortController()
    abortRef.current = controller

    setState({ ...initial, status: 'starting' })

    try {
      const res = await fetch('/api/runs/protocol', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
        signal: controller.signal,
      })

      if (!res.ok) {
        const err = await res.text()
        setState(s => ({ ...s, status: 'failed', error: `HTTP ${res.status}: ${err}` }))
        return
      }

      const reader = res.body?.getReader()
      if (!reader) return

      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        let eventType = ''
        for (const line of lines) {
          if (line.startsWith('event: ')) {
            eventType = line.slice(7).trim()
          } else if (line.startsWith('data: ') && eventType) {
            try {
              const data = JSON.parse(line.slice(6))
              handleEvent(eventType, data, setState)
            } catch { /* skip malformed */ }
            eventType = ''
          }
        }
      }
    } catch (e: any) {
      if (e.name !== 'AbortError') {
        setState(s => ({ ...s, status: 'failed', error: e.message }))
      }
    }
  }, [])

  const startPipelineRun = useCallback(async (payload: {
    question: string
    agent_keys: string[]
    steps: {
      protocol_key: string
      question_template: string
      thinking_model?: string
      orchestration_model?: string
      rounds?: number | null
      output_passthrough?: boolean
      no_tools?: boolean
    }[]
  }) => {
    abortRef.current?.abort()
    const controller = new AbortController()
    abortRef.current = controller

    setState({ ...initial, status: 'starting' })

    try {
      const res = await fetch('/api/runs/pipeline', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
        signal: controller.signal,
      })

      if (!res.ok) {
        const err = await res.text()
        setState(s => ({ ...s, status: 'failed', error: `HTTP ${res.status}: ${err}` }))
        return
      }

      const reader = res.body?.getReader()
      if (!reader) return

      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        let eventType = ''
        for (const line of lines) {
          if (line.startsWith('event: ')) {
            eventType = line.slice(7).trim()
          } else if (line.startsWith('data: ') && eventType) {
            try {
              const data = JSON.parse(line.slice(6))
              handleEvent(eventType, data, setState)
            } catch { /* skip malformed */ }
            eventType = ''
          }
        }
      }
    } catch (e: any) {
      if (e.name !== 'AbortError') {
        setState(s => ({ ...s, status: 'failed', error: e.message }))
      }
    }
  }, [])

  const abort = useCallback(() => {
    abortRef.current?.abort()
    setState(s => ({ ...s, status: 'failed', error: 'Aborted by user' }))
  }, [])

  return { ...state, startProtocolRun, startPipelineRun, abort }
}

function handleEvent(
  event: string,
  data: any,
  setState: React.Dispatch<React.SetStateAction<RunStreamState>>
) {
  switch (event) {
    case 'run_start':
      setState(s => ({ ...s, runId: data.run_id, status: 'running' }))
      break
    case 'agent_roster':
      setState(s => ({ ...s, agents: data.agents }))
      break
    case 'stage':
      // info event, could display as status message
      break
    case 'step_start':
      setState(s => ({ ...s, currentStep: data.step }))
      break
    case 'step_complete':
      break
    case 'tool_call':
      setState(s => ({
        ...s,
        toolCalls: [...s.toolCalls, {
          agent_name: data.agent_name,
          tool_name: data.tool_name,
          tool_input: data.tool_input,
          iteration: data.iteration,
          status: 'running' as const,
        }],
      }))
      break
    case 'tool_result':
      setState(s => {
        const updated = [...s.toolCalls]
        // Find last matching running tool_call for this agent+tool
        for (let i = updated.length - 1; i >= 0; i--) {
          if (updated[i].tool_name === data.tool_name && updated[i].agent_name === data.agent_name && updated[i].status === 'running') {
            updated[i] = { ...updated[i], result_preview: data.result_preview, elapsed_ms: data.elapsed_ms, status: 'completed' }
            break
          }
        }
        return { ...s, toolCalls: updated }
      })
      break
    case 'agent_output':
      setState(s => ({ ...s, outputs: [...s.outputs, data as AgentOutputEvent] }))
      break
    case 'synthesis':
      setState(s => ({ ...s, synthesis: data.text }))
      break
    case 'error':
      setState(s => ({ ...s, error: data.message }))
      break
    case 'run_complete':
      setState(s => ({
        ...s,
        status: data.status === 'completed' ? 'completed' : 'failed',
        elapsedSeconds: data.elapsed_seconds ?? null,
      }))
      break
  }
}
