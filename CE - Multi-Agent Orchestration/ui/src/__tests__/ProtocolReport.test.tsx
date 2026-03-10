import { describe, it, expect } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import '@testing-library/jest-dom'
import { ProtocolReport } from '../components/ProtocolReport'
import type { ProtocolReportData } from '../components/ProtocolReport'

// ── Mock react-markdown to avoid transform issues in jsdom ──────────────────
vi.mock('react-markdown', () => ({
  default: ({ children }: { children: string }) => <div>{children}</div>,
}))
vi.mock('remark-gfm', () => ({ default: () => {} }))

// ── Fixtures ──────────────────────────────────────────────────────────────────

const baseReport: ProtocolReportData = {
  participants: ['ceo', 'cfo', 'cto'],
  executive_summary: 'The team recommends expanding into Europe with careful resource planning.',
  key_findings: [
    'Market opportunity is significant in DACH region',
    'Regulatory complexity requires local counsel',
    'Break-even projected at 18 months',
  ],
  disagreements: [
    'However, the CFO raised concerns about burn rate timing',
    'In contrast, the CTO believes infrastructure costs are underestimated',
  ],
  confidence_score: 4,
  confidence_label: 'High',
  synthesis: 'Full synthesis text here.\n\nSecond paragraph of synthesis.',
  agent_contributions: [
    {
      agent_key: 'ceo',
      agent_name: 'CEO',
      text: 'CEO analysis: We should expand into Germany first.',
      cost_usd: 0.0125,
      model: 'claude-opus-4-6',
      tool_calls: [],
    },
    {
      agent_key: 'cfo',
      agent_name: 'CFO',
      text: 'CFO analysis: Cash runway needs review before committing.',
      cost_usd: 0.0089,
      model: 'claude-opus-4-6',
      tool_calls: [],
    },
  ],
  cost_summary: {
    total_usd: 0.0214,
    calls: 5,
  },
  metadata: {
    protocol_key: 'p03_parallel_synthesis',
    run_id: 42,
    question: 'Should we expand into Europe?',
    trace_id: 'abc-123',
    started_at: '2026-03-10T20:00:00Z',
    completed_at: '2026-03-10T20:05:00Z',
  },
}

const emptyDisagreementsReport: ProtocolReportData = {
  ...baseReport,
  disagreements: [],
}

const lowConfidenceReport: ProtocolReportData = {
  ...baseReport,
  confidence_score: 2,
  confidence_label: 'Low',
}

const mediumConfidenceReport: ProtocolReportData = {
  ...baseReport,
  confidence_score: 3,
  confidence_label: 'Medium',
}

const unscoredReport: ProtocolReportData = {
  ...baseReport,
  confidence_score: 0,
  confidence_label: 'Unscored',
}

// ── Tests ─────────────────────────────────────────────────────────────────────

describe('ProtocolReport', () => {
  describe('executive summary', () => {
    it('renders executive summary text', () => {
      render(<ProtocolReport report={baseReport} />)
      expect(screen.getByTestId('executive-summary')).toBeInTheDocument()
      expect(screen.getByText(/recommends expanding into Europe/i)).toBeInTheDocument()
    })

    it('executive-summary testid is present', () => {
      render(<ProtocolReport report={baseReport} />)
      const el = screen.getByTestId('executive-summary')
      expect(el).toBeInTheDocument()
    })
  })

  describe('confidence indicator', () => {
    it('renders confidence indicator with testid', () => {
      render(<ProtocolReport report={baseReport} />)
      expect(screen.getByTestId('confidence-indicator')).toBeInTheDocument()
    })

    it('shows confidence label text (not just raw number)', () => {
      render(<ProtocolReport report={baseReport} />)
      const indicator = screen.getByTestId('confidence-indicator')
      expect(indicator).toHaveTextContent('High')
    })

    it('does not render the score as a bare standalone number', () => {
      render(<ProtocolReport report={baseReport} />)
      // The score 4 should only appear as "(4/5)" not as a bare "4"
      const indicator = screen.getByTestId('confidence-indicator')
      // The label should be "High" not the raw integer
      expect(indicator.textContent).toContain('High')
      // Ensure raw "4" only appears as part of the "(4/5)" format
      expect(indicator.textContent).not.toMatch(/^4$/)
    })

    it('renders 5 dot elements for any score', () => {
      render(<ProtocolReport report={baseReport} />)
      const indicator = screen.getByTestId('confidence-indicator')
      // 5 dots as span[aria-hidden="true"]
      const dots = indicator.querySelectorAll('span[aria-hidden="true"]')
      expect(dots).toHaveLength(5)
    })

    it('shows yellow dots for score 3', () => {
      render(<ProtocolReport report={mediumConfidenceReport} />)
      const indicator = screen.getByTestId('confidence-indicator')
      const yellowDots = indicator.querySelectorAll('.bg-yellow-500')
      expect(yellowDots.length).toBe(3)
    })

    it('shows red dots for low confidence score', () => {
      render(<ProtocolReport report={lowConfidenceReport} />)
      const indicator = screen.getByTestId('confidence-indicator')
      const redDots = indicator.querySelectorAll('.bg-red-500')
      expect(redDots.length).toBe(2)
    })

    it('shows green dots for high confidence score', () => {
      render(<ProtocolReport report={baseReport} />)
      const indicator = screen.getByTestId('confidence-indicator')
      const greenDots = indicator.querySelectorAll('.bg-green-500')
      expect(greenDots.length).toBe(4)
    })

    it('shows gray dots for unscored', () => {
      render(<ProtocolReport report={unscoredReport} />)
      const indicator = screen.getByTestId('confidence-indicator')
      const grayDots = indicator.querySelectorAll('.bg-gray-300')
      expect(grayDots.length).toBe(5)
    })
  })

  describe('key findings', () => {
    it('renders all key findings', () => {
      render(<ProtocolReport report={baseReport} />)
      const findings = screen.getByTestId('key-findings')
      expect(findings).toBeInTheDocument()
      expect(screen.getByText(/Market opportunity is significant/i)).toBeInTheDocument()
      expect(screen.getByText(/Regulatory complexity/i)).toBeInTheDocument()
      expect(screen.getByText(/Break-even projected/i)).toBeInTheDocument()
    })

    it('key-findings testid is present', () => {
      render(<ProtocolReport report={baseReport} />)
      expect(screen.getByTestId('key-findings')).toBeInTheDocument()
    })
  })

  describe('disagreements', () => {
    it('renders disagreements with amber border styling when present', () => {
      render(<ProtocolReport report={baseReport} />)
      const disagreements = screen.getByTestId('disagreements')
      expect(disagreements).toBeInTheDocument()
      expect(disagreements.className).toContain('border-amber-500')
    })

    it('renders disagreements heading', () => {
      render(<ProtocolReport report={baseReport} />)
      expect(screen.getByText(/Areas of Disagreement/i)).toBeInTheDocument()
    })

    it('renders each disagreement item', () => {
      render(<ProtocolReport report={baseReport} />)
      expect(screen.getByText(/CFO raised concerns/i)).toBeInTheDocument()
      expect(screen.getByText(/CTO believes infrastructure/i)).toBeInTheDocument()
    })

    it('hides disagreements section when empty', () => {
      render(<ProtocolReport report={emptyDisagreementsReport} />)
      expect(screen.queryByTestId('disagreements')).not.toBeInTheDocument()
    })

    it('disagreements background has amber styling', () => {
      render(<ProtocolReport report={baseReport} />)
      const el = screen.getByTestId('disagreements')
      expect(el.className).toContain('bg-amber-50')
    })
  })

  describe('agent contributions', () => {
    it('renders agent contribution section', () => {
      render(<ProtocolReport report={baseReport} />)
      expect(screen.getByTestId('agent-contributions')).toBeInTheDocument()
    })

    it('shows agent names in collapsed state', () => {
      render(<ProtocolReport report={baseReport} />)
      expect(screen.getByText('CEO')).toBeInTheDocument()
      expect(screen.getByText('CFO')).toBeInTheDocument()
    })

    it('cards are collapsed by default', () => {
      render(<ProtocolReport report={baseReport} />)
      // Content should not be visible initially
      expect(screen.queryByText(/CEO analysis: We should expand/)).not.toBeInTheDocument()
    })

    it('expands card on click', () => {
      render(<ProtocolReport report={baseReport} />)
      const ceoButton = screen.getByRole('button', { name: /CEO/ })
      fireEvent.click(ceoButton)
      expect(screen.getByText(/CEO analysis: We should expand/)).toBeInTheDocument()
    })

    it('collapses card on second click', () => {
      render(<ProtocolReport report={baseReport} />)
      const ceoButton = screen.getByRole('button', { name: /CEO/ })
      fireEvent.click(ceoButton)
      fireEvent.click(ceoButton)
      expect(screen.queryByText(/CEO analysis: We should expand/)).not.toBeInTheDocument()
    })
  })

  describe('cost summary', () => {
    it('renders cost summary section', () => {
      render(<ProtocolReport report={baseReport} />)
      expect(screen.getByTestId('cost-summary')).toBeInTheDocument()
    })

    it('shows formatted total cost', () => {
      render(<ProtocolReport report={baseReport} />)
      const costSection = screen.getByTestId('cost-summary')
      expect(costSection.textContent).toContain('$0.0214')
    })

    it('shows call count when available', () => {
      render(<ProtocolReport report={baseReport} />)
      expect(screen.getByText(/5 API calls/i)).toBeInTheDocument()
    })
  })
})
