export interface Agent {
  id?: number
  key: string
  name: string
  category: string
  model: string
  temperature: number
  system_prompt: string
  constraints: string[]
  context_scope: string[]
  is_builtin: boolean
  // Rich agent fields
  max_tokens: number
  tools: string[]
  mcp_servers: string[]
  kb_namespaces: string[]
  kb_write_enabled: boolean
  deliverable_template: string
  frameworks: Framework[]
  delegation: Delegation[]
  personality: string
  communication_style: string
}

export interface Framework {
  name: string
  description: string
  when_to_use: string
}

export interface Delegation {
  agent_key: string
  delegate_when: string
}

export interface ToolDefinition {
  name: string
  description: string
  domain: string
}

export interface McpServer {
  name: string
  description: string
  transport: string
}

export interface ToolRegistry {
  tools: Record<string, ToolDefinition>
  mcp_servers: Record<string, McpServer>
}

export interface Protocol {
  key: string
  protocol_id: string
  name: string
  category: string
  description: string
  problem_types: string[]
  cost_tier: string
  min_agents: number
  max_agents: number | null
  supports_rounds: boolean
  when_to_use: string
  when_not_to_use: string
  tools_enabled: boolean
}

export interface Team {
  id: number
  name: string
  description: string
  agent_keys: string[]
  created_at: string
  last_used_at: string | null
}

export interface Pipeline {
  id: number
  name: string
  description: string
  team_id: number | null
  steps: PipelineStep[]
  created_at: string
}

export interface PipelineStep {
  id?: number
  order: number
  protocol_key: string
  question_template: string
  agent_key_override: string[]
  rounds: number | null
  thinking_model: string
  orchestration_model: string
  output_passthrough: boolean
  no_tools: boolean
}

export interface ToolCallEvent {
  agent_name: string
  tool_name: string
  tool_input: string
  result_preview?: string
  elapsed_ms?: number
  status: 'running' | 'completed' | 'failed'
  iteration?: number
}

export interface Run {
  id: number
  type: 'protocol' | 'pipeline'
  protocol_key: string
  pipeline_id: number | null
  question: string
  team_id: number | null
  status: 'pending' | 'running' | 'completed' | 'failed'
  cost_usd: number
  started_at: string
  completed_at: string | null
}
