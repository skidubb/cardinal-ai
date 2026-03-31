/**
 * Curated example questions from benchmark-questions.json.
 * Shown as clickable chips to help users get started quickly.
 */
export const EXAMPLE_QUESTIONS = [
  {
    label: 'Competitive Threat',
    question:
      "McKinsey just published a free 40-page AI transformation playbook that covers 60% of what we deliver in our $25K audit. Three prospects have sent it to us asking 'how is yours different?'",
  },
  {
    label: 'Diagnostic',
    question:
      "Revenue per client dropped 22% over the last two quarters despite adding 3 new clients. Client count is up 37%, total revenue is up 6%. NPS hasn't changed. What's happening?",
  },
  {
    label: 'Explore Opportunities',
    question:
      'We have 400 hours of recorded client discovery calls, 50 completed audit reports, and 3 years of engagement data. What could we build with these assets that we haven\'t considered?',
  },
  {
    label: 'Prioritize Initiatives',
    question:
      'Rank these initiatives for a bootstrapped AI consultancy with $150K budget and 18 months runway: (a) hire senior consultant $120K, (b) build self-serve PLG tool $40K, (c) launch podcast/content series $15K, (d) attend 4 industry conferences $50K, (e) develop proprietary training curriculum $25K, (f) build partner channel program $10K, (g) invest in AI automation tools $35K, (h) open second geographic market $20K.',
  },
  {
    label: 'Scaling Paradox',
    question:
      "How do we scale without hiring when our value proposition is human expertise applied through AI? Every scaling mechanism (PLG, automation, templates) dilutes the 'bespoke' positioning that commands premium pricing.",
  },
  {
    label: 'Pre-Mortem',
    question:
      "We've decided to take the $500K enterprise engagement outside our ICP (2,000-person company vs. our usual 50-200). We've signed the SOW. What kills us?",
  },
  {
    label: 'Client Concentration',
    question:
      'Our 40% revenue client demands a 25% discount or they walk. We have 14 months of runway but losing them cuts revenue by nearly half overnight. What do we do?',
  },
  {
    label: 'Build vs Buy',
    question:
      'We can either build a proprietary data pipeline for client reporting ($40K, 3 months) or use a white-labeled SaaS tool ($800/mo, live in 2 weeks). We have 6 active clients expecting dashboards by Q2.',
  },
] as const
