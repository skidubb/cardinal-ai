import { describe, it, expect, vi, beforeEach } from 'vitest'
import { useProtocolStore } from '../stores/protocolStore'
import type { Protocol } from '../types'

const mockProtocols: Protocol[] = [
  {
    key: 'p03_parallel_synthesis', protocol_id: 'P3', name: 'Parallel Synthesis',
    category: 'Baselines', description: 'All agents answer independently',
    problem_types: ['General Analysis'], cost_tier: 'low',
    min_agents: 2, max_agents: null, supports_rounds: false,
    when_to_use: '', when_not_to_use: '', tools_enabled: true,
  },
  {
    key: 'p16_ach', protocol_id: 'P16', name: 'ACH',
    category: 'Intelligence Analysis', description: 'Analysis of competing hypotheses',
    problem_types: ['Diagnostic', 'Adversarial'], cost_tier: 'medium',
    min_agents: 3, max_agents: null, supports_rounds: false,
    when_to_use: '', when_not_to_use: '', tools_enabled: true,
  },
  {
    key: 'p0a_reasoning_router', protocol_id: 'P0a', name: 'Reasoning Router',
    category: 'Meta-Protocols', description: 'Route to optimal protocol',
    problem_types: ['General Analysis'], cost_tier: 'low',
    min_agents: 0, max_agents: 0, supports_rounds: false,
    when_to_use: '', when_not_to_use: '', tools_enabled: false,
  },
]

// Mock the API
vi.mock('../api', () => ({
  api: {
    protocols: {
      list: vi.fn(() => Promise.resolve(mockProtocols)),
    },
  },
}))

beforeEach(() => {
  useProtocolStore.setState({
    protocols: mockProtocols,
    selectedProblemType: null,
    searchQuery: '',
  })
})

describe('protocolStore', () => {
  describe('problemTypes()', () => {
    it('returns deduplicated sorted problem types', () => {
      const pts = useProtocolStore.getState().problemTypes()
      expect(pts).toEqual(['Adversarial', 'Diagnostic', 'General Analysis'])
    })
  })

  describe('filtered() with problem type', () => {
    it('returns all protocols when no filter selected', () => {
      const result = useProtocolStore.getState().filtered()
      expect(result).toHaveLength(3)
    })

    it('filters by problem type', () => {
      useProtocolStore.setState({ selectedProblemType: 'Diagnostic' })
      const result = useProtocolStore.getState().filtered()
      expect(result).toHaveLength(1)
      expect(result[0].key).toBe('p16_ach')
    })

    it('shows protocol under each matching problem type', () => {
      // P16 has both Diagnostic and Adversarial
      useProtocolStore.setState({ selectedProblemType: 'Adversarial' })
      const adversarial = useProtocolStore.getState().filtered()
      expect(adversarial).toHaveLength(1)
      expect(adversarial[0].key).toBe('p16_ach')

      useProtocolStore.setState({ selectedProblemType: 'Diagnostic' })
      const diagnostic = useProtocolStore.getState().filtered()
      expect(diagnostic).toHaveLength(1)
      expect(diagnostic[0].key).toBe('p16_ach')
    })

    it('filters by General Analysis includes multiple protocols', () => {
      useProtocolStore.setState({ selectedProblemType: 'General Analysis' })
      const result = useProtocolStore.getState().filtered()
      expect(result).toHaveLength(2)
      const keys = result.map(p => p.key)
      expect(keys).toContain('p03_parallel_synthesis')
      expect(keys).toContain('p0a_reasoning_router')
    })
  })

  describe('filtered() with search', () => {
    it('filters by search query', () => {
      useProtocolStore.setState({ searchQuery: 'ACH' })
      const result = useProtocolStore.getState().filtered()
      expect(result).toHaveLength(1)
      expect(result[0].key).toBe('p16_ach')
    })

    it('combines search and problem type filter', () => {
      useProtocolStore.setState({ selectedProblemType: 'General Analysis', searchQuery: 'router' })
      const result = useProtocolStore.getState().filtered()
      expect(result).toHaveLength(1)
      expect(result[0].key).toBe('p0a_reasoning_router')
    })
  })

  describe('setProblemType', () => {
    it('sets and clears problem type', () => {
      useProtocolStore.getState().setProblemType('Diagnostic')
      expect(useProtocolStore.getState().selectedProblemType).toBe('Diagnostic')

      useProtocolStore.getState().setProblemType(null)
      expect(useProtocolStore.getState().selectedProblemType).toBeNull()
    })
  })
})
