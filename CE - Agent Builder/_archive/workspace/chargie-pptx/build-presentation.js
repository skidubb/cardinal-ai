const PptxGenJS = require('pptxgenjs');

// Create presentation
const pptx = new PptxGenJS();
pptx.layout = 'LAYOUT_16x9';
pptx.author = 'Cardinal Element C-Suite AI Advisory Team';
pptx.title = 'Growth Strategy Audit: Chargie';
pptx.subject = 'Strategic Analysis for Property Electrification Leadership';

// Chargie Brand Colors
const C = {
  dark: '1C1C1E',       // Main dark background
  white: 'FFFFFF',       // White text
  gray: '86868B',        // Gray accent text
  lightBg: 'F5F5F7',     // Light background/callouts
  coral: 'FF4D6D',       // Primary accent (start of gradient)
  coral2: 'FE5469',
  coral3: 'FD5B65',
  coral4: 'FC6160',
  orange1: 'FA685C',
  orange2: 'F96F58',
  orange3: 'F87654',
  orange4: 'F77C4F',
  orange5: 'F6834B',
  orange6: 'F58A47',     // End of gradient
  // Semantic colors
  warning: 'FF4D6D',     // Same as coral for warnings
  success: '4CAF50',     // Green for positive
  danger: 'E74C3C'       // Red for critical warnings
};

// Helper functions
function addSlide(opts = {}) {
  const slide = pptx.addSlide();
  slide.background = { color: opts.bg === 'light' ? C.lightBg : opts.bg === 'white' ? C.white : C.dark };
  return slide;
}

// Add gradient bar (Chargie brand element)
function addGradientBar(slide, y, barWidth = 0.22, count = 10) {
  const colors = [C.coral, C.coral2, C.coral3, C.coral4, C.orange1, C.orange2, C.orange3, C.orange4, C.orange5, C.orange6];
  for (let i = 0; i < count; i++) {
    slide.addShape('rect', { x: 0.5 + (i * barWidth * 1.1), y, w: barWidth, h: 0.06, fill: { color: colors[i % colors.length] } });
  }
}

function addTitleBar(slide, title, subtitle = null, opts = {}) {
  slide.addShape('rect', { x: 0, y: 0, w: '100%', h: 1.0, fill: { color: C.dark } });
  slide.addText(title, { x: 0.5, y: 0.25, w: 8.5, h: 0.5, fontSize: 24, bold: true, color: C.white, fontFace: 'Arial' });
  if (subtitle) {
    slide.addText(subtitle, { x: 0.5, y: 0.65, w: 8.5, h: 0.3, fontSize: 12, color: C.coral, fontFace: 'Arial' });
  }
}

function addSectionDivider(slide, sectionTitle, sectionSubtitle = '') {
  addGradientBar(slide, 0.85);
  slide.addText(sectionTitle, { x: 0.5, y: 2.0, w: 9, h: 0.8, fontSize: 36, bold: true, color: C.white, fontFace: 'Arial' });
  if (sectionSubtitle) {
    slide.addText(sectionSubtitle, { x: 0.5, y: 2.8, w: 9, h: 0.5, fontSize: 18, italic: true, color: C.gray, fontFace: 'Arial' });
  }
}

function addTable(slide, headers, rows, opts = {}) {
  const x = opts.x || 0.5;
  const y = opts.y || 1.2;
  const tableData = [
    headers.map(h => ({ text: h, options: { bold: true, fill: { color: C.dark }, color: C.white, fontSize: 10, fontFace: 'Arial' } })),
    ...rows.map((row, i) => row.map(cell => ({
      text: cell,
      options: {
        fill: { color: i % 2 === 0 ? C.white : C.lightBg },
        fontSize: 9,
        fontFace: 'Arial',
        color: C.dark
      }
    })))
  ];
  slide.addTable(tableData, { x, y, w: opts.w || 9, colW: opts.colW, border: { pt: 0.5, color: C.lightBg } });
}

// ============================================
// SECTION 1: TITLE & EXECUTIVE SUMMARY
// ============================================

// Slide 1: Title Slide
let slide = addSlide();
addGradientBar(slide, 3.6);
slide.addText('Growth Strategy Audit', { x: 0.5, y: 1.5, w: 9, h: 0.7, fontSize: 42, bold: true, color: C.white, fontFace: 'Arial' });
slide.addText('Chargie', { x: 0.5, y: 2.2, w: 9, h: 0.8, fontSize: 52, bold: true, color: C.coral, fontFace: 'Arial' });
slide.addText('"Clean energy, no fuss, just go."', { x: 0.5, y: 3.8, w: 9, h: 0.4, fontSize: 16, italic: true, color: C.gray, fontFace: 'Arial' });
slide.addText('Strategic Analysis for Property Electrification Leadership', { x: 0.5, y: 4.35, w: 9, h: 0.3, fontSize: 14, color: C.white, fontFace: 'Arial' });
slide.addText('February 9, 2026  |  Cardinal Element C-Suite AI Advisory Team', { x: 0.5, y: 4.8, w: 9, h: 0.3, fontSize: 11, color: C.gray, fontFace: 'Arial' });

// Slide 2: Audit Overview
slide = addSlide({ bg: 'white' });
addTitleBar(slide, 'Audit Overview');
slide.addText('SCOPE', { x: 0.5, y: 1.2, w: 1.5, h: 0.3, fontSize: 11, bold: true, color: C.coral, fontFace: 'Arial' });
slide.addText('Comprehensive CFO & CMO perspectives + strategic synthesis', { x: 2.0, y: 1.2, w: 7.2, h: 0.3, fontSize: 12, color: C.dark, fontFace: 'Arial' });
slide.addText('METHODOLOGY', { x: 0.5, y: 1.7, w: 1.5, h: 0.3, fontSize: 11, bold: true, color: C.coral, fontFace: 'Arial' });
slide.addText('Financial modeling, competitive analysis, positioning strategy', { x: 2.0, y: 1.7, w: 7.2, h: 0.3, fontSize: 12, color: C.dark, fontFace: 'Arial' });
slide.addText('FOCUS AREAS', { x: 0.5, y: 2.2, w: 1.5, h: 0.3, fontSize: 11, bold: true, color: C.coral, fontFace: 'Arial' });
const focuses = ['Unit economics & pricing optimization', 'Competitive positioning & market analysis', 'Go-to-market strategy & channel assessment', 'Cash flow stress testing & risk analysis'];
focuses.forEach((f, i) => {
  slide.addText('•', { x: 2.0, y: 2.2 + (i * 0.4), w: 0.3, h: 0.35, fontSize: 12, color: C.coral, fontFace: 'Arial' });
  slide.addText(f, { x: 2.3, y: 2.2 + (i * 0.4), w: 6.9, h: 0.35, fontSize: 12, color: C.dark, fontFace: 'Arial' });
});

// Slide 3: Key Metrics
slide = addSlide();
addTitleBar(slide, 'Key Metrics at a Glance');
const metrics = [
  { value: '1,200+', label: 'Properties\nDeployed', color: C.coral },
  { value: '18,000+', label: 'Charging\nStations', color: C.orange2 },
  { value: '~$100M', label: 'Rebate Savings\nFacilitated', color: C.orange4 },
  { value: '$30-80M', label: 'Est. Annual\nRevenue', color: C.orange6 }
];
metrics.forEach((m, i) => {
  const x = 0.5 + (i * 2.35);
  slide.addShape('rect', { x, y: 1.5, w: 2.15, h: 2.3, fill: { color: m.color } });
  slide.addText(m.value, { x, y: 1.7, w: 2.15, h: 0.8, fontSize: 28, bold: true, color: C.white, align: 'center', fontFace: 'Arial' });
  slide.addText(m.label, { x, y: 2.6, w: 2.15, h: 1, fontSize: 12, color: C.white, align: 'center', fontFace: 'Arial' });
});

// Slide 4: Executive Summary - 3 Critical Findings
slide = addSlide({ bg: 'white' });
addTitleBar(slide, 'Executive Summary: 3 Critical Findings');
const findings = [
  { num: '1', title: 'Rebate Facilitation Under-Monetized', desc: 'The $100M rebate facilitation capability is massively under-monetized — potential $2-5M annual revenue at 80%+ margin' },
  { num: '2', title: 'Dangerous Margin Compression', desc: 'Hardware-heavy revenue mix (40-55%) creates dangerous margin compression — blended gross margin only 28-38%' },
  { num: '3', title: 'Underleveraged Recurring Asset', desc: '18,000 installed stations are an underleveraged recurring revenue asset — should generate $3-8M+ in SaaS revenue' }
];
const gradColors = [C.coral, C.orange3, C.orange6];
findings.forEach((f, i) => {
  const y = 1.2 + (i * 1.1);
  slide.addShape('rect', { x: 0.5, y, w: 0.5, h: 0.9, fill: { color: gradColors[i] } });
  slide.addText(f.num, { x: 0.5, y: y + 0.2, w: 0.5, h: 0.5, fontSize: 22, bold: true, color: C.white, align: 'center', fontFace: 'Arial' });
  slide.addText(f.title, { x: 1.2, y, w: 8, h: 0.35, fontSize: 14, bold: true, color: C.dark, fontFace: 'Arial' });
  slide.addText(f.desc, { x: 1.2, y: y + 0.4, w: 8, h: 0.5, fontSize: 11, color: C.dark, fontFace: 'Arial' });
});

// ============================================
// SECTION 2: CFO FINANCIAL ANALYSIS
// ============================================

// Slide 5: CFO Section Divider
slide = addSlide();
addSectionDivider(slide, 'CFO Perspective', 'Financial Analysis');

// Slide 6: Unit Economics Overview
slide = addSlide({ bg: 'white' });
addTitleBar(slide, 'Unit Economics Overview');
addTable(slide, ['Metric', 'Estimated Range', 'Context'], [
  ['Est. Headcount', '80-150 FTEs', 'Based on scale indicators'],
  ['Est. Annual Revenue', '$30-80M', 'Derived from station count'],
  ['Revenue/Employee', '$300-600K', 'Hardware-inclusive'],
  ['Net Rev/Employee (ex-HW)', '$120-250K', 'More meaningful metric']
], { y: 1.15, colW: [3, 2.5, 3.5] });
slide.addShape('rect', { x: 0.5, y: 3.3, w: 9, h: 0.9, fill: { color: C.dark } });
slide.addText('⚠️ KEY INSIGHT', { x: 0.7, y: 3.4, w: 2, h: 0.3, fontSize: 11, bold: true, color: C.coral, fontFace: 'Arial' });
slide.addText('Net revenue per employee is below the $250K+ threshold for tech-enabled services companies',
  { x: 0.7, y: 3.7, w: 8.6, h: 0.4, fontSize: 12, color: C.white, fontFace: 'Arial' });

// Slide 7: Gross Margin Analysis
slide = addSlide({ bg: 'white' });
addTitleBar(slide, 'Gross Margin Analysis');
addTable(slide, ['Revenue Stream', 'Est. Mix', 'Gross Margin', 'Contribution'], [
  ['Hardware sales', '40-55%', '15-25%', 'Low'],
  ['Installation services', '20-30%', '25-40%', 'Moderate'],
  ['Software (SaaS)', '10-20%', '75-85%', 'High'],
  ['Rebate facilitation', '3-8%', '60-80%', 'High'],
  ['Maintenance/support', '5-10%', '50-65%', 'Moderate-High'],
  ['BLENDED TOTAL', '100%', '28-38%', '—']
], { y: 1.15, colW: [3, 1.8, 2.2, 2] });

// Slide 8: Gross Margin Deep Dive
slide = addSlide({ bg: 'white' });
addTitleBar(slide, 'Why Hardware is Dangerous', 'Gross Margin Deep Dive');
const warnings = [
  { icon: '📉', title: 'Hardware is a commodity race', desc: 'Chinese manufacturers driving L2 charger costs down 10-15% annually. Margins will compress further.' },
  { icon: '🌍', title: 'Installation margins are geography-dependent', desc: 'Can vary 2-3x across markets (Austin 40% vs San Francisco 20%). Subcontractor management is the hidden margin killer.' },
  { icon: '💎', title: 'Software is the margin engine', desc: "But at only 10-20% of revenue, it's not yet carrying the P&L. This is the single biggest financial lever in the business." }
];
warnings.forEach((w, i) => {
  const y = 1.15 + (i * 1.1);
  slide.addText(w.icon, { x: 0.5, y, w: 0.5, h: 0.5, fontSize: 20, fontFace: 'Arial' });
  slide.addText(w.title, { x: 1.1, y, w: 8, h: 0.35, fontSize: 13, bold: true, color: C.dark, fontFace: 'Arial' });
  slide.addText(w.desc, { x: 1.1, y: y + 0.4, w: 8, h: 0.55, fontSize: 11, color: C.dark, fontFace: 'Arial' });
});

// Slide 9: CAC by Segment
slide = addSlide({ bg: 'white' });
addTitleBar(slide, 'Customer Acquisition Cost by Segment');
addTable(slide, ['Segment', 'Est. CAC', 'Sales Cycle', 'CAC Payback'], [
  ['Multifamily', '$3-8K', '3-6 mo', '6-18 mo'],
  ['Commercial/Office', '$5-15K', '4-9 mo', '8-24 mo'],
  ['Hospitality', '$4-12K', '3-8 mo', '6-18 mo'],
  ['Government', '$8-25K', '6-18 mo', '12-36 mo'],
  ['Fleet', '$10-30K', '6-12 mo', '12-24 mo']
], { y: 1.15, colW: [2.5, 2, 2.25, 2.25] });
slide.addShape('rect', { x: 0.5, y: 3.45, w: 9, h: 0.65, fill: { color: C.success } });
slide.addText('💡 Rebate facilitation is a "CAC weapon" — customers perceive net-zero or net-negative cost',
  { x: 0.7, y: 3.5, w: 8.6, h: 0.5, fontSize: 12, bold: true, color: C.white, fontFace: 'Arial' });

// Slide 10: LTV Analysis
slide = addSlide({ bg: 'white' });
addTitleBar(slide, 'Lifetime Value Analysis');
addTable(slide, ['Component', 'Year 1', 'Years 2-5 (annual)', '5-Year LTV'], [
  ['Hardware + install', '$15-60K', '$0', '$15-60K'],
  ['Software fees', '$1.8-5.4K', '$1.8-5.4K', '$9-27K'],
  ['Maintenance', '$1.2-3.6K', '$1.2-3.6K', '$6-18K'],
  ['Expansion', '—', '$5-20K (yr 2-3)', '$10-40K'],
  ['Total LTV/property', '—', '—', '$40-145K'],
  ['Gross Profit LTV', '—', '—', '$15-55K']
], { y: 1.15, colW: [2.5, 2, 2.5, 2] });
slide.addText('LTV:CAC Ratio: 3:1 to 7:1 — Healthy but heavily front-loaded with one-time hardware revenue',
  { x: 0.5, y: 3.9, w: 9, h: 0.3, fontSize: 11, italic: true, color: C.gray, fontFace: 'Arial' });

// Slide 11: Pricing Model Assessment
slide = addSlide({ bg: 'white' });
addTitleBar(slide, 'Current Pricing Model Assessment');
addTable(slide, ['Component', 'Current Model', 'Assessment'], [
  ['Hardware', 'Cost-plus (20-35%)', '⚠️ Commodity trap'],
  ['Installation', 'Project-based', '⚠️ Margin risk'],
  ['Software', '$10-30/station/mo', '⚠️ Under-priced'],
  ['Rebate facilitation', 'Bundled (FREE)', '🔴 MASSIVE value leak'],
  ['Maintenance', 'Optional add-on', '⚠️ Under-attached']
], { y: 1.15, colW: [2.5, 3, 3.5] });

// Slide 12: Pricing Opportunity #1
slide = addSlide({ bg: 'white' });
addTitleBar(slide, 'Pricing Opportunity #1: Monetize Rebate Facilitation');
slide.addShape('rect', { x: 0.5, y: 1.15, w: 2.5, h: 1.3, fill: { color: C.coral } });
slide.addText('$2-5M', { x: 0.5, y: 1.25, w: 2.5, h: 0.7, fontSize: 32, bold: true, color: C.white, align: 'center', fontFace: 'Arial' });
slide.addText('Annual Revenue\n80%+ Margin', { x: 0.5, y: 1.95, w: 2.5, h: 0.45, fontSize: 11, color: C.white, align: 'center', fontFace: 'Arial' });
const opp1Points = [
  'Market rate: 5-15% of rebate value or $2-10K flat fee',
  'Recommendation: 8-12% success-based fee',
  'Framing: "We only get paid when you save money"',
  'On $20-40M annual rebates = $1.6-4.8M near-pure-margin revenue'
];
opp1Points.forEach((p, i) => {
  slide.addText('•', { x: 3.2, y: 1.2 + (i * 0.4), w: 0.3, h: 0.35, fontSize: 12, color: C.coral, fontFace: 'Arial' });
  slide.addText(p, { x: 3.5, y: 1.2 + (i * 0.4), w: 5.7, h: 0.35, fontSize: 11, color: C.dark, fontFace: 'Arial' });
});
slide.addShape('rect', { x: 0.5, y: 3.2, w: 9, h: 0.65, fill: { color: C.dark } });
slide.addText('HIGHEST-IMPACT, LOWEST-RISK REVENUE LEVER AVAILABLE',
  { x: 0.7, y: 3.3, w: 8.6, h: 0.45, fontSize: 13, bold: true, color: C.coral, align: 'center', fontFace: 'Arial' });

// Slide 13: Pricing Opportunity #2
slide = addSlide({ bg: 'white' });
addTitleBar(slide, 'Pricing Opportunity #2: Tiered SaaS Pricing');
slide.addShape('rect', { x: 0.5, y: 1.15, w: 2.5, h: 1.0, fill: { color: C.orange3 } });
slide.addText('+40-80%', { x: 0.5, y: 1.25, w: 2.5, h: 0.5, fontSize: 26, bold: true, color: C.white, align: 'center', fontFace: 'Arial' });
slide.addText('SaaS Revenue', { x: 0.5, y: 1.75, w: 2.5, h: 0.35, fontSize: 11, color: C.white, align: 'center', fontFace: 'Arial' });
addTable(slide, ['Tier', 'Features', 'Price', 'Target'], [
  ['Essential', 'Basic monitoring, usage', '$8-12/sta/mo', 'Small MF'],
  ['Professional', '+ Revenue mgmt, billing', '$20-30/sta/mo', 'Large MF, Commercial'],
  ['Enterprise', '+ Fleet mgmt, API, SLA', '$35-50/sta/mo', 'Fleet, Gov, Hospitality']
], { x: 3.2, y: 1.15, w: 6, colW: [1.4, 1.9, 1.4, 1.3] });
slide.addText('Key unlock: Revenue-share layer (5-10%) on charging revenue could be highly accretive',
  { x: 0.5, y: 3.4, w: 9, h: 0.3, fontSize: 11, italic: true, color: C.orange3, fontFace: 'Arial' });

// Slide 14: Pricing Opportunity #3
slide = addSlide({ bg: 'white' });
addTitleBar(slide, 'Pricing Opportunity #3: Charging-as-a-Service (CaaS)');
slide.addShape('rect', { x: 0.5, y: 1.15, w: 2.3, h: 1.0, fill: { color: C.orange6 } });
slide.addText('2-3x', { x: 0.5, y: 1.25, w: 2.3, h: 0.5, fontSize: 30, bold: true, color: C.white, align: 'center', fontFace: 'Arial' });
slide.addText('Revenue/Property', { x: 0.5, y: 1.75, w: 2.3, h: 0.35, fontSize: 10, color: C.white, align: 'center', fontFace: 'Arial' });
const caasPoints = [
  'Model: $150-500/station/month all-inclusive subscription',
  '3-5 year contract terms, zero upfront for property owner',
  'Payback period: 15-30 months → remaining term = pure margin',
  'Transforms valuation: 1-2x revenue (project) → 4-8x (recurring)'
];
caasPoints.forEach((p, i) => {
  slide.addText('•', { x: 3.0, y: 1.15 + (i * 0.4), w: 0.3, h: 0.35, fontSize: 12, color: C.orange6, fontFace: 'Arial' });
  slide.addText(p, { x: 3.3, y: 1.15 + (i * 0.4), w: 6, h: 0.35, fontSize: 11, color: C.dark, fontFace: 'Arial' });
});
slide.addShape('rect', { x: 0.5, y: 3.0, w: 9, h: 0.85, fill: { color: C.danger } });
slide.addText('⚠️ CATCH: Requires $15-24M annual capital deployment', { x: 0.7, y: 3.1, w: 8.6, h: 0.35, fontSize: 12, bold: true, color: C.white, fontFace: 'Arial' });
slide.addText('Do NOT launch without committed equipment financing.', { x: 0.7, y: 3.45, w: 8.6, h: 0.3, fontSize: 11, color: C.white, fontFace: 'Arial' });

// Slide 15: Cash Flow Stress Test
slide = addSlide({ bg: 'white' });
addTitleBar(slide, 'Cash Flow Stress Test: Incentive Policy Risk', 'SEVERITY: HIGH');
addTable(slide, ['Scenario', 'Revenue Impact', 'EBITDA Impact', '12-mo Cash'], [
  ['Base case (current)', '$0', '$0', '$0'],
  ['25% incentive cut', '-10 to -15%', '-20 to -30%', '-$2-6M'],
  ['50% incentive cut', '-25 to -35%', '-50 to -70%', '-$5-15M'],
  ['Full elimination', '-40 to -60%', 'Breakeven/neg', '-$10-25M']
], { y: 1.15, colW: [2.5, 2.3, 2.2, 2] });
slide.addShape('rect', { x: 0.5, y: 3.2, w: 9, h: 0.75, fill: { color: C.danger } });
slide.addText('🚨 EXISTENTIAL RISK', { x: 0.7, y: 3.25, w: 3, h: 0.3, fontSize: 12, bold: true, color: C.white, fontFace: 'Arial' });
slide.addText('Every dollar shifted from project-based to recurring revenue reduces incentive policy exposure',
  { x: 0.7, y: 3.55, w: 8.6, h: 0.3, fontSize: 11, color: C.white, fontFace: 'Arial' });

// Slide 16: Working Capital Optimization
slide = addSlide({ bg: 'white' });
addTitleBar(slide, 'Working Capital Optimization');
slide.addText('Cash Conversion Cycle: 120-300 days net', { x: 0.5, y: 1.0, w: 9, h: 0.25, fontSize: 11, italic: true, color: C.coral, fontFace: 'Arial' });
addTable(slide, ['Lever', 'Current', 'Target', 'Cash Impact'], [
  ['Customer deposits', '25-30%', '40-50%', '+$2-5M'],
  ['Milestone billing', 'At completion', '3-stage', '+$3-8M'],
  ['Vendor terms', 'Net 30', 'Net 60 + consign', '+$1-3M'],
  ['Gov AR management', '60-90 DSO', 'Factoring', '+$1-4M'],
  ['TOTAL IMPROVEMENT', '—', '—', '+$7-20M']
], { y: 1.35, colW: [2.5, 2, 2.25, 2.25] });

// ============================================
// SECTION 3: CMO COMPETITIVE POSITIONING
// ============================================

// Slide 17: CMO Section Divider
slide = addSlide();
addSectionDivider(slide, 'CMO Perspective', 'Competitive Positioning');

// Slide 18: Market Position Assessment
slide = addSlide({ bg: 'white' });
addTitleBar(slide, 'Market Position Assessment');
slide.addText('Current: "Full-stack EV charging solutions provider" — same as 15-20 competitors',
  { x: 0.5, y: 1.0, w: 9, h: 0.25, fontSize: 11, italic: true, color: C.danger, fontFace: 'Arial' });
addTable(slide, ['Dimension', 'Position', 'Assessment'], [
  ['Scale', '18K+ stations', 'Top-tier property-focused'],
  ['Vertical Focus', '6+ segments', 'Broad but "jack of all trades" risk'],
  ['Value Chain', 'Full-stack', 'Genuine differentiator'],
  ['Geographic', 'National (US)', 'Advantage vs regional'],
  ['Business Model', 'Project + recurring', 'Healthy but recurring story weak']
], { y: 1.35, colW: [2.5, 2.5, 4] });

// Slide 19: Genuine Differentiators
slide = addSlide({ bg: 'white' });
addTitleBar(slide, 'Genuine Differentiators (Defensible)');
const diffs = [
  '~$100M in facilitated rebate savings — quantifiable, almost no competitor can match',
  '1,200+ property track record — operational credibility across diverse types',
  'Full-stack ownership — hardware-agnostic, software, install, support = reduced buyer risk',
  'Multi-vertical expertise — cross-pollination of best practices'
];
diffs.forEach((d, i) => {
  slide.addShape('rect', { x: 0.5, y: 1.15 + (i * 0.6), w: 0.35, h: 0.45, fill: { color: gradColors[i % 3] } });
  slide.addText((i + 1).toString(), { x: 0.5, y: 1.2 + (i * 0.6), w: 0.35, h: 0.35, fontSize: 12, bold: true, color: C.white, align: 'center', fontFace: 'Arial' });
  slide.addText(d, { x: 1.0, y: 1.15 + (i * 0.6), w: 8.2, h: 0.55, fontSize: 11, color: C.dark, fontFace: 'Arial' });
});
slide.addShape('rect', { x: 0.5, y: 3.6, w: 9, h: 0.55, fill: { color: C.lightBg } });
slide.addText('COMMODITIZED (Everyone claims these): "Turnkey solutions", "Expert installation", "Reliable hardware"',
  { x: 0.7, y: 3.65, w: 8.6, h: 0.45, fontSize: 10, italic: true, color: C.gray, fontFace: 'Arial' });

// Slide 20: Competitive Landscape
slide = addSlide({ bg: 'white' });
addTitleBar(slide, 'Competitive Landscape: 4 Threat Categories');
const cats = [
  { cat: 'National Networked', players: 'ChargePoint, Blink, EVgo', threat: 'High brand, network effects', edge: 'Low property expertise' },
  { cat: 'Hardware Manufacturers', players: 'ABB, Siemens, Wallbox', threat: 'Industrial trust', edge: 'Low full-stack capability' },
  { cat: 'Regional Installers', players: 'Qmerit, local electricians', threat: 'Price competition', edge: 'Low scale & software' },
  { cat: 'CaaS Providers', players: 'EverCharge, Xeal', threat: 'Business model innovation', edge: 'Low proven scale' }
];
cats.forEach((c, i) => {
  const y = 1.15 + (i * 0.75);
  slide.addShape('rect', { x: 0.5, y, w: 0.12, h: 0.6, fill: { color: gradColors[i % 3] } });
  slide.addText(c.cat, { x: 0.75, y, w: 2.1, h: 0.3, fontSize: 11, bold: true, color: C.dark, fontFace: 'Arial' });
  slide.addText(c.players, { x: 0.75, y: y + 0.3, w: 2.1, h: 0.25, fontSize: 9, color: C.gray, fontFace: 'Arial' });
  slide.addText(c.threat, { x: 3.0, y: y + 0.1, w: 2.7, h: 0.4, fontSize: 10, color: C.danger, fontFace: 'Arial' });
  slide.addText(c.edge, { x: 5.9, y: y + 0.1, w: 3.3, h: 0.4, fontSize: 10, color: C.success, fontFace: 'Arial' });
});

// Slide 21: Competitor Threat Matrix
slide = addSlide({ bg: 'white' });
addTitleBar(slide, 'Competitor Threat Matrix');
addTable(slide, ['Category', 'Brand', 'Hardware', 'Software', 'Property', 'Incentive'], [
  ['National Network', '🔴 High', '🟡 Med', '🔴 High', '🟢 Low', '🟢 Low'],
  ['HW Manufacturers', '🔴 High', '🔴 High', '🟡 Med', '🟢 Low', '🟢 Low'],
  ['Regional Install', '🟢 Low', '🟡 Med', '🟢 Low', '🟡 Med', '🟢 Low'],
  ['CaaS Providers', '🟢 Low', '🟡 Med', '🟡 Med', '🟡 Med', '🟢 Low']
], { y: 1.15, colW: [2.2, 1.3, 1.3, 1.3, 1.3, 1.6] });
slide.addText("Chargie's edge: Financial expertise + Operational scale + Full-stack ownership",
  { x: 0.5, y: 3.4, w: 9, h: 0.35, fontSize: 12, bold: true, color: C.coral, fontFace: 'Arial' });

// Slide 22: The Competitive Moat
slide = addSlide();
addTitleBar(slide, 'The Competitive Moat: 3 Interlocking Elements');
const moatItems = [
  { title: 'FINANCIAL EXPERTISE', desc: '$100M rebate savings, incentive navigation, ROI modeling', color: C.coral },
  { title: 'OPERATIONAL SCALE', desc: '1,200+ properties, 18K+ stations, multi-vertical patterns', color: C.orange3 },
  { title: 'FULL-STACK OWNERSHIP', desc: 'Single partner, HW+SW+Install+Support, reduced finger-pointing', color: C.orange6 }
];
moatItems.forEach((m, i) => {
  const y = 1.2 + (i * 1.1);
  slide.addShape('rect', { x: 1.2, y, w: 7.5, h: 0.9, fill: { color: m.color } });
  slide.addText(m.title, { x: 1.4, y: y + 0.1, w: 7.1, h: 0.35, fontSize: 14, bold: true, color: C.white, fontFace: 'Arial' });
  slide.addText(m.desc, { x: 1.4, y: y + 0.45, w: 7.1, h: 0.35, fontSize: 11, color: C.white, fontFace: 'Arial' });
  if (i < 2) {
    slide.addShape('rect', { x: 4.7, y: y + 0.9, w: 0.5, h: 0.2, fill: { color: C.white } });
  }
});

// Slide 23: Go-to-Market Optimization
slide = addSlide({ bg: 'white' });
addTitleBar(slide, 'Go-to-Market Optimization');
slide.addText('HIGH POTENTIAL (Invest More)', { x: 0.5, y: 1.1, w: 4, h: 0.3, fontSize: 11, bold: true, color: C.success, fontFace: 'Arial' });
const highPot = ['Referral/Client Advocacy — systematize case studies', 'Industry Events — shift booth → speaking', 'Strategic Partnerships — utilities, prop mgmt', 'SEO/Content — own "fund EV charging" searches'];
highPot.forEach((p, i) => {
  slide.addText('•', { x: 0.5, y: 1.4 + (i * 0.38), w: 0.3, h: 0.32, fontSize: 10, color: C.success, fontFace: 'Arial' });
  slide.addText(p, { x: 0.8, y: 1.4 + (i * 0.38), w: 4, h: 0.32, fontSize: 10, color: C.dark, fontFace: 'Arial' });
});
slide.addText('LOWER PRIORITY (Deprioritize)', { x: 5.0, y: 1.1, w: 4.2, h: 0.3, fontSize: 11, bold: true, color: C.danger, fontFace: 'Arial' });
const lowPot = ['Broad digital ads — high cost, low intent', 'Social media (broad) — LinkedIn only', 'General PR — vertical trade pubs only'];
lowPot.forEach((p, i) => {
  slide.addText('•', { x: 5.0, y: 1.4 + (i * 0.38), w: 0.3, h: 0.32, fontSize: 10, color: C.danger, fontFace: 'Arial' });
  slide.addText(p, { x: 5.3, y: 1.4 + (i * 0.38), w: 4, h: 0.32, fontSize: 10, color: C.dark, fontFace: 'Arial' });
});

// Slide 24: Recommended Positioning
slide = addSlide({ bg: 'white' });
addTitleBar(slide, 'Recommended Positioning: "The Risk Remover"');
slide.addShape('rect', { x: 0.5, y: 1.1, w: 9, h: 1.2, fill: { color: C.coral } });
slide.addText('"Chargie is the EV charging infrastructure partner that eliminates the financial, technical, and operational risk of electrifying your property — proven across 1,200+ properties and ~$100M in secured savings."',
  { x: 0.7, y: 1.2, w: 8.6, h: 1.0, fontSize: 13, italic: true, color: C.white, fontFace: 'Arial' });
slide.addText('Why This Wins:', { x: 0.5, y: 2.5, w: 4, h: 0.3, fontSize: 12, bold: true, color: C.dark, fontFace: 'Arial' });
const whyWins = ["Addresses buyer's #1 concern (risk, not features)", 'Leverages strongest proof point ($100M savings)', 'Differentiates from ALL 4 competitor categories', 'Creates category of one: "risk removal partner"'];
whyWins.forEach((w, i) => {
  slide.addText('✓', { x: 0.5, y: 2.85 + (i * 0.38), w: 0.3, h: 0.32, fontSize: 12, bold: true, color: C.coral, fontFace: 'Arial' });
  slide.addText(w, { x: 0.85, y: 2.85 + (i * 0.38), w: 8.3, h: 0.32, fontSize: 11, color: C.dark, fontFace: 'Arial' });
});

// Slide 25: Messaging Framework
slide = addSlide();
addTitleBar(slide, 'Messaging Framework: 3 Pillars');
slide.addText('Master Narrative: "EV charging without the risk"', { x: 0.5, y: 1.0, w: 9, h: 0.25, fontSize: 12, bold: true, color: C.white, fontFace: 'Arial' });
addGradientBar(slide, 1.3, 0.15, 10);
const pillars = [
  { title: 'FINANCIAL CERTAINTY', msg: '"$100M in savings. We\'ll find every dollar."', proof: 'Incentive database, ROI case studies', color: C.coral },
  { title: 'OPERATIONAL CONFIDENCE', msg: '"1,200+ properties. We\'ve solved every scenario."', proof: 'Deployment volume, testimonials', color: C.orange3 },
  { title: 'SINGLE-PARTNER SIMPLICITY', msg: '"One partner, one plan, one call."', proof: 'Client retention, support metrics', color: C.orange6 }
];
pillars.forEach((p, i) => {
  const x = 0.5 + (i * 3.1);
  slide.addShape('rect', { x, y: 1.55, w: 2.9, h: 2.5, fill: { color: p.color } });
  slide.addText(p.title, { x, y: 1.65, w: 2.9, h: 0.4, fontSize: 10, bold: true, color: C.white, align: 'center', fontFace: 'Arial' });
  slide.addText(p.msg, { x: x + 0.1, y: 2.1, w: 2.7, h: 0.7, fontSize: 10, italic: true, color: C.white, fontFace: 'Arial' });
  slide.addText('Proof:', { x: x + 0.1, y: 2.85, w: 2.7, h: 0.25, fontSize: 9, bold: true, color: C.lightBg, fontFace: 'Arial' });
  slide.addText(p.proof, { x: x + 0.1, y: 3.1, w: 2.7, h: 0.8, fontSize: 9, color: C.lightBg, fontFace: 'Arial' });
});

// Slide 26: Priority Marketing Investments
slide = addSlide({ bg: 'white' });
addTitleBar(slide, 'Priority Marketing Investments');
addTable(slide, ['#', 'Initiative', 'Investment', 'Impact'], [
  ['1', 'Incentive Intelligence Platform', 'Medium', 'High'],
  ['2', 'Vertical Case Study Engine (12-18)', 'Medium', 'High'],
  ['3', 'Speaking Program (8-12 events/yr)', 'Medium', 'Med-High'],
  ['4', 'LinkedIn Authority (2-3 leaders)', 'Low-Med', 'Medium'],
  ['5', 'Utility Co-Marketing (5-10 partners)', 'Medium', 'High']
], { y: 1.15, colW: [0.5, 4.5, 2, 2] });

// ============================================
// SECTION 4: STRATEGIC SYNTHESIS
// ============================================

// Slide 27: Synthesis Section Divider
slide = addSlide();
addSectionDivider(slide, 'Strategic Synthesis', 'Unified Recommendations');

// Slide 28: Aligned Perspectives
slide = addSlide({ bg: 'white' });
addTitleBar(slide, 'Where CFO & CMO Converge');
const themes = [
  '$100M rebate story is most powerful AND most under-leveraged asset',
  'Hardware is commodity trap; software/services are margin engine',
  '18K station installed base is underleveraged recurring asset',
  'Vertical depth must balance breadth — maintain coverage, invest in packaging',
  'Transition to recurring revenue is strategically essential'
];
themes.forEach((t, i) => {
  const y = 1.15 + (i * 0.55);
  slide.addShape('rect', { x: 0.5, y, w: 0.4, h: 0.4, fill: { color: gradColors[i % 3] } });
  slide.addText((i + 1).toString(), { x: 0.5, y: y + 0.02, w: 0.4, h: 0.35, fontSize: 13, bold: true, color: C.white, align: 'center', fontFace: 'Arial' });
  slide.addText(t, { x: 1.05, y, w: 8.15, h: 0.5, fontSize: 11, color: C.dark, fontFace: 'Arial' });
});

// Slide 29: Strategic North Star
slide = addSlide();
addTitleBar(slide, 'Strategic North Star');
slide.addShape('rect', { x: 0.5, y: 1.3, w: 9, h: 2.2, fill: { color: C.coral } });
slide.addText('"Chargie becomes the category-defining \'property electrification risk partner\' — the company that property operators trust to navigate financial, technical, and operational complexity of EV charging, with a business model that increasingly generates recurring revenue from the growing installed base."',
  { x: 0.7, y: 1.5, w: 8.6, h: 1.8, fontSize: 16, italic: true, color: C.white, fontFace: 'Arial', valign: 'middle' });

// Slide 30: Three Strategic Pillars
slide = addSlide();
addTitleBar(slide, 'Three Strategic Pillars');
const stratPillars = [
  { num: '1', title: 'MONETIZE\nTHE MOAT', time: 'Months 1-6', color: C.coral },
  { num: '2', title: 'REPOSITION\n& AMPLIFY', time: 'Months 1-9', color: C.orange3 },
  { num: '3', title: 'TRANSFORM\nBUSINESS MODEL', time: 'Months 6-18', color: C.orange6 }
];
stratPillars.forEach((p, i) => {
  const x = 0.5 + (i * 3.1);
  slide.addShape('rect', { x, y: 1.3, w: 2.9, h: 2.3, fill: { color: p.color } });
  slide.addText(p.num, { x, y: 1.45, w: 2.9, h: 0.7, fontSize: 36, bold: true, color: C.white, align: 'center', fontFace: 'Arial' });
  slide.addText(p.title, { x, y: 2.15, w: 2.9, h: 0.8, fontSize: 13, bold: true, color: C.white, align: 'center', fontFace: 'Arial' });
  slide.addText(p.time, { x, y: 3.0, w: 2.9, h: 0.4, fontSize: 11, color: C.lightBg, align: 'center', fontFace: 'Arial' });
});

// Slide 31: Pillar 1 - Monetize the Moat
slide = addSlide({ bg: 'white' });
addTitleBar(slide, 'Pillar 1: Monetize the Moat', 'Months 1-6');
addTable(slide, ['Initiative', 'Revenue', 'Margin', 'Owner'], [
  ['Rebate facilitation fee (8-12%)', '+$2-5M/yr', '~80%', 'CFO + Sales'],
  ['Tiered SaaS pricing', '+$1-3M/yr', '~75%', 'Product + CFO'],
  ['Revenue-share on charging', '+$0.5-2M/yr', '~90%', 'Product'],
  ['Maintenance attach rate', '+$0.5-1.5M/yr', '~55%', 'Ops + Sales'],
  ['COMBINED', '+$4-11.5M', '65-80%', '—']
], { y: 1.15, colW: [3.5, 2, 1.5, 2] });
slide.addShape('rect', { x: 0.5, y: 3.4, w: 9, h: 0.5, fill: { color: C.coral } });
slide.addText('Highest-ROI, lowest-risk growth lever available',
  { x: 0.7, y: 3.45, w: 8.6, h: 0.4, fontSize: 12, bold: true, color: C.white, align: 'center', fontFace: 'Arial' });

// Slide 32: Pillar 2 - Reposition & Amplify
slide = addSlide({ bg: 'white' });
addTitleBar(slide, 'Pillar 2: Reposition & Amplify', 'Months 1-9');
slide.addText('Shift perception: "charger installer" → "risk removal partner"',
  { x: 0.5, y: 1.0, w: 9, h: 0.25, fontSize: 11, italic: true, color: C.orange3, fontFace: 'Arial' });
const inits = [
  ['Adopt "Risk Remover" positioning', 'Low', 'Messaging + training'],
  ['Launch Incentive Intelligence Platform', 'Medium', 'Web dev + data'],
  ['Vertical case studies (12-18)', 'Medium', 'Content production'],
  ['Speaking program (8-12/year)', 'Medium', 'Travel + prep'],
  ['LinkedIn authority (2-3 leaders)', 'Low', 'Ghostwriting'],
  ['Utility co-marketing (5-10)', 'Medium', 'Relationship dev']
];
inits.forEach((item, i) => {
  slide.addText('•', { x: 0.5, y: 1.35 + (i * 0.4), w: 0.3, h: 0.35, fontSize: 10, color: C.orange3, fontFace: 'Arial' });
  slide.addText(item[0], { x: 0.8, y: 1.35 + (i * 0.4), w: 4.5, h: 0.35, fontSize: 10, color: C.dark, fontFace: 'Arial' });
  slide.addText(item[1], { x: 5.5, y: 1.35 + (i * 0.4), w: 1.2, h: 0.35, fontSize: 10, bold: true, color: C.orange3, fontFace: 'Arial' });
  slide.addText(item[2], { x: 6.8, y: 1.35 + (i * 0.4), w: 2.5, h: 0.35, fontSize: 10, color: C.gray, fontFace: 'Arial' });
});

// Slide 33: Pillar 3 - Transform Business Model
slide = addSlide({ bg: 'white' });
addTitleBar(slide, 'Pillar 3: Transform Business Model', 'Months 6-18');
addTable(slide, ['Initiative', 'Prerequisite', 'Timeline'], [
  ['Secure equipment financing', 'CFO-led, $10-20M', 'Mo 6-9'],
  ['Pilot CaaS in multifamily', 'Financing + pricing', 'Mo 9-12'],
  ['Build expansion revenue engine', 'NRR tracking', 'Mo 6-12'],
  ['Scale CaaS on pilot economics', 'Unit econ confirmed', 'Mo 12-18'],
  ['Target: 30% recurring', 'All above', 'Month 24']
], { y: 1.15, colW: [3.5, 3, 2.5] });

// Slide 34: Key Trade-offs
slide = addSlide({ bg: 'white' });
addTitleBar(slide, 'Key Trade-offs: Critical Decisions');
const tradeoffs = [
  { title: 'CaaS Speed vs Cash Flow', desc: 'Pilot don\'t launch at scale; secure financing first' },
  { title: 'Rebate Monetization vs Sales Velocity', desc: 'Bundle free assessment, charge for procurement' },
  { title: 'Brand Investment vs Cash Priorities', desc: 'CFO cash-freeing (mo 1-3) funds CMO brand-building (mo 2-6)' },
  { title: 'Vertical Specialization vs Simplicity', desc: 'Specialize front-end (marketing), standardize back-end (delivery)' }
];
tradeoffs.forEach((t, i) => {
  const y = 1.15 + (i * 0.75);
  slide.addShape('rect', { x: 0.5, y, w: 0.4, h: 0.6, fill: { color: gradColors[i % 3] } });
  slide.addText((i + 1).toString(), { x: 0.5, y: y + 0.12, w: 0.4, h: 0.35, fontSize: 14, bold: true, color: C.white, align: 'center', fontFace: 'Arial' });
  slide.addText(t.title, { x: 1.05, y, w: 8.15, h: 0.3, fontSize: 12, bold: true, color: C.dark, fontFace: 'Arial' });
  slide.addText(t.desc, { x: 1.05, y: y + 0.32, w: 8.15, h: 0.3, fontSize: 10, color: C.dark, fontFace: 'Arial' });
});

// ============================================
// SECTION 5: ACTION PLAN & CLOSE
// ============================================

// Slide 35: 90-Day Priority Actions
slide = addSlide({ bg: 'white' });
addTitleBar(slide, '90-Day Priority Actions');
addTable(slide, ['#', 'Action', 'Owner', 'Impact', 'Timeline'], [
  ['1', 'Implement rebate facilitation fee', 'CFO + Sales', '$2-5M/yr at 80%+', 'Wk 1-8'],
  ['2', 'Restructure billing + credit facility', 'CFO', 'Free $7-20M WC', 'Wk 1-12'],
  ['3', 'Launch Risk Remover positioning', 'CMO', 'Differentiation', 'Mo 1-4'],
  ['4', 'Tiered SaaS pricing + NRR tracking', 'Product + CFO', '+40-80% SaaS', 'Mo 3-6'],
  ['5', 'Pilot CaaS in multifamily', 'CEO + CFO', 'Model transform', 'Mo 6-12']
], { y: 1.15, colW: [0.5, 3.2, 1.8, 2, 1.5] });

// Slide 36: Action Timeline
slide = addSlide();
addTitleBar(slide, 'Action Timeline: Visual Roadmap');
const phases = [
  { phase: 'MONTH 1-3', subtitle: 'Foundation', items: ['Rebate fee (wk 1-8)', 'Billing restructure', 'Positioning launch'], color: C.coral },
  { phase: 'MONTH 3-6', subtitle: 'Amplification', items: ['Incentive platform live', 'Tiered SaaS + NRR'], color: C.orange3 },
  { phase: 'MONTH 6-12', subtitle: 'Transformation', items: ['Equipment financing', 'CaaS pilot (50-100)'], color: C.orange6 }
];
phases.forEach((p, i) => {
  const x = 0.5 + (i * 3.1);
  slide.addShape('rect', { x, y: 1.2, w: 2.9, h: 0.6, fill: { color: p.color } });
  slide.addText(p.phase, { x, y: 1.25, w: 2.9, h: 0.3, fontSize: 11, bold: true, color: C.white, align: 'center', fontFace: 'Arial' });
  slide.addText(p.subtitle, { x, y: 1.5, w: 2.9, h: 0.25, fontSize: 10, color: C.lightBg, align: 'center', fontFace: 'Arial' });
  p.items.forEach((item, j) => {
    slide.addText('• ' + item, { x: x + 0.1, y: 1.95 + (j * 0.4), w: 2.7, h: 0.35, fontSize: 10, color: C.white, fontFace: 'Arial' });
  });
});

// Slide 37: Open Questions
slide = addSlide({ bg: 'white' });
addTitleBar(slide, 'Open Questions: What We Need to Validate');
const questions = [
  'What is the actual revenue breakdown by stream? (hardware vs software vs services)',
  'What is real customer concentration? (any segment >30%?)',
  'What is current NRR rate? (below 100% = churn problem)',
  'Incentive policy risk preparedness? (can you survive at 50% incentives?)',
  'Hardware model? (manufacture, white-label, or resell?)',
  'Competitive win/loss data? (who are you losing to?)'
];
questions.forEach((q, i) => {
  slide.addText((i + 1).toString() + '.', { x: 0.5, y: 1.15 + (i * 0.5), w: 0.35, h: 0.4, fontSize: 12, bold: true, color: C.coral, fontFace: 'Arial' });
  slide.addText(q, { x: 0.9, y: 1.15 + (i * 0.5), w: 8.3, h: 0.45, fontSize: 11, color: C.dark, fontFace: 'Arial' });
});

// Slide 38: Critical Risk Warning
slide = addSlide();
slide.background = { color: C.danger };
slide.addText('⚠️ CRITICAL RISK WARNING', { x: 0.5, y: 0.7, w: 9, h: 0.6, fontSize: 28, bold: true, color: C.white, fontFace: 'Arial' });
slide.addText('INCENTIVE POLICY DEPENDENCY', { x: 0.5, y: 1.4, w: 9, h: 0.45, fontSize: 18, bold: true, color: C.lightBg, fontFace: 'Arial' });
slide.addShape('rect', { x: 0.5, y: 2.0, w: 9, h: 2.0, fill: { color: C.dark } });
slide.addText('This is the existential risk.', { x: 0.7, y: 2.15, w: 8.6, h: 0.3, fontSize: 13, bold: true, color: C.white, fontFace: 'Arial' });
slide.addText('With shifting political dynamics around IRA provisions and state incentives:', { x: 0.7, y: 2.5, w: 8.6, h: 0.3, fontSize: 11, color: C.lightBg, fontFace: 'Arial' });
const riskPoints = [
  'Current model is ~70% dependent on incentive value proposition',
  'Every strategic action should be pressure-tested: "Does this make us more or less resilient if incentives are cut in half?"',
  'The recommended strategy (monetizing expertise, building recurring, positioning around risk removal) systematically reduces this dependency'
];
riskPoints.forEach((r, i) => {
  slide.addText('•', { x: 0.7, y: 2.9 + (i * 0.35), w: 0.3, h: 0.3, fontSize: 10, color: C.coral, fontFace: 'Arial' });
  slide.addText(r, { x: 1.0, y: 2.9 + (i * 0.35), w: 8.3, h: 0.3, fontSize: 10, color: C.white, fontFace: 'Arial' });
});

// Slide 39: The Bottom Line
slide = addSlide({ bg: 'white' });
addTitleBar(slide, 'The Bottom Line');
slide.addShape('rect', { x: 0.5, y: 1.15, w: 9, h: 1.0, fill: { color: C.dark } });
slide.addText('"Chargie has built the hard thing — operational scale and domain expertise — but hasn\'t yet captured the value of what it\'s built."',
  { x: 0.7, y: 1.25, w: 8.6, h: 0.8, fontSize: 14, italic: true, color: C.white, fontFace: 'Arial' });
slide.addText('The strategic imperative is NOT to build new capabilities. It\'s to:',
  { x: 0.5, y: 2.35, w: 9, h: 0.35, fontSize: 12, bold: true, color: C.dark, fontFace: 'Arial' });
const imperatives = [
  { check: '✓', text: 'Monetize existing ones ($4-11M opportunity)', color: C.coral },
  { check: '✓', text: 'Make them visible to the market (Risk Remover positioning)', color: C.orange3 },
  { check: '✓', text: 'Restructure the business model (recurring revenue)', color: C.orange6 }
];
imperatives.forEach((imp, i) => {
  slide.addText(imp.check, { x: 0.7, y: 2.75 + (i * 0.4), w: 0.35, h: 0.35, fontSize: 14, bold: true, color: imp.color, fontFace: 'Arial' });
  slide.addText(imp.text, { x: 1.1, y: 2.75 + (i * 0.4), w: 8.1, h: 0.35, fontSize: 11, color: C.dark, fontFace: 'Arial' });
});
slide.addText('The $100M rebate story, 18K stations, and 1,200-property track record are assets competitors would need years and tens of millions to replicate.',
  { x: 0.5, y: 4.0, w: 9, h: 0.4, fontSize: 10, italic: true, color: C.gray, fontFace: 'Arial' });

// Slide 40: Next Steps / Discussion
slide = addSlide({ bg: 'white' });
addTitleBar(slide, 'Next Steps & Discussion');
slide.addText('Immediate Decisions Needed:', { x: 0.5, y: 1.1, w: 4.3, h: 0.3, fontSize: 12, bold: true, color: C.coral, fontFace: 'Arial' });
const decisions = ['Rebate pricing: 8-12% success fee or flat $3-5K?', 'Billing: Can you implement 40/30/30 milestone?', 'Credit facility: Ready to pursue $5-15M revolver?', 'CaaS: Which multifamily properties for pilot?'];
decisions.forEach((d, i) => {
  slide.addText('•', { x: 0.5, y: 1.45 + (i * 0.38), w: 0.3, h: 0.32, fontSize: 10, color: C.coral, fontFace: 'Arial' });
  slide.addText(d, { x: 0.8, y: 1.45 + (i * 0.38), w: 4, h: 0.32, fontSize: 10, color: C.dark, fontFace: 'Arial' });
});
slide.addText('Questions for Chargie Leadership:', { x: 5.0, y: 1.1, w: 4.2, h: 0.3, fontSize: 12, bold: true, color: C.orange3, fontFace: 'Arial' });
const leaderQs = ['Confirm revenue mix & margin by stream', 'Review customer concentration data', 'Validate NRR and churn metrics', 'Discuss incentive contingency planning'];
leaderQs.forEach((q, i) => {
  slide.addText('•', { x: 5.0, y: 1.45 + (i * 0.38), w: 0.3, h: 0.32, fontSize: 10, color: C.orange3, fontFace: 'Arial' });
  slide.addText(q, { x: 5.3, y: 1.45 + (i * 0.38), w: 4, h: 0.32, fontSize: 10, color: C.dark, fontFace: 'Arial' });
});
addGradientBar(slide, 3.5);
slide.addText('Prepared by Cardinal Element C-Suite AI Advisory Team | February 2026',
  { x: 0.5, y: 3.75, w: 9, h: 0.3, fontSize: 11, color: C.gray, align: 'center', fontFace: 'Arial' });

// Save the presentation
pptx.writeFile({ fileName: '/Users/scottewalt/Documents/CE - C-Suite/chargie-audit-presentation.pptx' })
  .then(() => console.log('Presentation saved successfully!'))
  .catch(err => console.error('Error:', err));
