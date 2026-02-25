import {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  HeadingLevel, AlignmentType, BorderStyle, WidthType, ShadingType,
  PageBreak, Header, Footer, TableOfContents, TabStopPosition, TabStopType,
  convertInchesToTwip, PageNumber, NumberFormat, ImageRun,
} from "docx";
import { execSync } from "child_process";
import * as fs from "fs";

// Imagine Wireless brand
const BRAND = {
  dark: "1A1A2E",      // Deep navy-black
  accent: "00B4D8",    // Cyan/teal accent
  accentDark: "0077B6", // Deeper blue
  white: "FFFFFF",
  lightGray: "F0F4F8",
  medGray: "ABB8C3",
  textDark: "2D3436",
  textLight: "636E72",
};

const OUT_DIR = "/Users/scottewalt/Documents/CE - AGENTS/CE - Multi-Agent Orchesration/output/airport_5g_test";
const md = fs.readFileSync(`${OUT_DIR}/20260224_113027_board_report.md`, "utf-8");

// Pre-load diagram images
const diagramImages = {};
for (let d = 0; d < 5; d++) {
  const p = `${OUT_DIR}/diagram_${d}.png`;
  if (fs.existsSync(p)) {
    diagramImages[d] = fs.readFileSync(p);
    // Get dimensions
    const buf = diagramImages[d];
    // Read PNG width/height from IHDR chunk (bytes 16-23)
    const w = buf.readUInt32BE(16);
    const h = buf.readUInt32BE(18);
    diagramImages[`${d}_w`] = w;
    diagramImages[`${d}_h`] = h;
  }
}
let diagramCounter = 0;

// Parse markdown into structured sections
const lines = md.split("\n");
const sections = [];
let current = null;

for (const line of lines) {
  if (line.startsWith("# ")) {
    current = { level: 1, title: line.replace(/^# /, ""), content: [] };
    sections.push(current);
  } else if (line.startsWith("## ")) {
    current = { level: 2, title: line.replace(/^## /, ""), content: [] };
    sections.push(current);
  } else if (line.startsWith("### ")) {
    current = { level: 3, title: line.replace(/^### /, ""), content: [] };
    sections.push(current);
  } else if (current) {
    current.content.push(line);
  } else {
    // Pre-header content
    if (!sections.length) {
      current = { level: 0, title: "", content: [line] };
      sections.push(current);
    }
  }
}

// Helper: parse inline bold/italic
function parseInline(text) {
  const runs = [];
  // Split on **bold** patterns
  const parts = text.split(/(\*\*.*?\*\*)/g);
  for (const part of parts) {
    if (part.startsWith("**") && part.endsWith("**")) {
      runs.push(new TextRun({ text: part.slice(2, -2), bold: true, font: "Calibri", size: 22, color: BRAND.textDark }));
    } else if (part.length > 0) {
      runs.push(new TextRun({ text: part, font: "Calibri", size: 22, color: BRAND.textDark }));
    }
  }
  return runs;
}

// Helper: create a styled table from markdown table lines
function parseTable(tableLines) {
  const rows = tableLines
    .filter(l => l.includes("|") && !l.match(/^\|[\s-:|]+\|$/))
    .map(l => l.split("|").filter((_, i, a) => i > 0 && i < a.length - 1).map(c => c.trim()));

  if (rows.length < 1) return null;

  const header = rows[0];
  const dataRows = rows.slice(1);
  const colCount = header.length;

  const headerRow = new TableRow({
    tableHeader: true,
    children: header.map(cell =>
      new TableCell({
        shading: { type: ShadingType.SOLID, color: BRAND.dark },
        children: [new Paragraph({
          children: [new TextRun({ text: cell, bold: true, font: "Calibri", size: 18, color: BRAND.white })],
          spacing: { before: 40, after: 40 },
        })],
        margins: { top: 40, bottom: 40, left: 80, right: 80 },
      })
    ),
  });

  const bodyRows = dataRows.map((row, idx) =>
    new TableRow({
      children: Array.from({ length: colCount }, (_, i) =>
        new TableCell({
          shading: idx % 2 === 0
            ? { type: ShadingType.SOLID, color: BRAND.white }
            : { type: ShadingType.SOLID, color: BRAND.lightGray },
          children: [new Paragraph({
            children: [new TextRun({ text: (row[i] || ""), font: "Calibri", size: 18, color: BRAND.textDark })],
            spacing: { before: 30, after: 30 },
          })],
          margins: { top: 30, bottom: 30, left: 80, right: 80 },
        })
      ),
    })
  );

  return new Table({
    width: { size: 100, type: WidthType.PERCENTAGE },
    rows: [headerRow, ...bodyRows],
    borders: {
      top: { style: BorderStyle.SINGLE, size: 1, color: BRAND.medGray },
      bottom: { style: BorderStyle.SINGLE, size: 1, color: BRAND.medGray },
      left: { style: BorderStyle.SINGLE, size: 1, color: BRAND.medGray },
      right: { style: BorderStyle.SINGLE, size: 1, color: BRAND.medGray },
      insideHorizontal: { style: BorderStyle.SINGLE, size: 1, color: BRAND.medGray },
      insideVertical: { style: BorderStyle.SINGLE, size: 1, color: BRAND.medGray },
    },
  });
}

// Build document children
const children = [];

// --- COVER PAGE ---
children.push(new Paragraph({ spacing: { before: 4000 } }));
children.push(new Paragraph({
  alignment: AlignmentType.CENTER,
  children: [new TextRun({ text: "IMAGINE WIRELESS", font: "Calibri Light", size: 28, color: BRAND.accent, bold: true, characterSpacing: 300 })],
}));
children.push(new Paragraph({ spacing: { before: 200 } }));
children.push(new Paragraph({
  alignment: AlignmentType.CENTER,
  spacing: { before: 600 },
  children: [new TextRun({ text: "DFW Airport", font: "Calibri Light", size: 72, color: BRAND.dark, bold: true })],
}));
children.push(new Paragraph({
  alignment: AlignmentType.CENTER,
  children: [new TextRun({ text: "Private 5G Deployment", font: "Calibri Light", size: 72, color: BRAND.dark, bold: true })],
}));
children.push(new Paragraph({
  alignment: AlignmentType.CENTER,
  spacing: { before: 200 },
  children: [new TextRun({ text: "Decision-Maker Simulation Report", font: "Calibri Light", size: 36, color: BRAND.accentDark })],
}));

// Accent line
children.push(new Paragraph({ spacing: { before: 400 } }));
children.push(new Paragraph({
  alignment: AlignmentType.CENTER,
  border: { bottom: { style: BorderStyle.SINGLE, size: 6, color: BRAND.accent, space: 1 } },
  children: [new TextRun({ text: "  ", size: 8 })],
}));

children.push(new Paragraph({ spacing: { before: 600 } }));
children.push(new Paragraph({
  alignment: AlignmentType.CENTER,
  children: [new TextRun({ text: "Strategic Question", font: "Calibri", size: 22, color: BRAND.textLight, italics: true })],
}));
children.push(new Paragraph({
  alignment: AlignmentType.CENTER,
  spacing: { before: 100 },
  children: [new TextRun({ text: "How should DFW structure its private 5G deployment", font: "Calibri", size: 26, color: BRAND.textDark })],
}));
children.push(new Paragraph({
  alignment: AlignmentType.CENTER,
  children: [new TextRun({ text: "to maximize value for all stakeholders?", font: "Calibri", size: 26, color: BRAND.textDark })],
}));

children.push(new Paragraph({ spacing: { before: 800 } }));

const metaItems = [
  ["Date", "February 2026"],
  ["Constituencies Modeled", "6 (Airport CIO, Airport CRO, Anchor Airline VP, Cargo Director, Concessions Tech Lead, AT&T Carrier Rep)"],
  ["Protocol Pipeline", "Discover \u2192 Diagnose \u2192 Negotiate \u2192 Stress-Test"],
  ["Prepared by", "Scott Ewalt for Imagine Wireless"],
];
for (const [label, value] of metaItems) {
  children.push(new Paragraph({
    alignment: AlignmentType.CENTER,
    spacing: { before: 60, after: 60 },
    children: [
      new TextRun({ text: `${label}: `, font: "Calibri", size: 20, color: BRAND.textLight, bold: true }),
      new TextRun({ text: value, font: "Calibri", size: 20, color: BRAND.textDark }),
    ],
  }));
}

// Simulation context box
children.push(new Paragraph({ spacing: { before: 600 } }));
children.push(new Paragraph({
  shading: { type: ShadingType.SOLID, color: BRAND.lightGray },
  border: { left: { style: BorderStyle.SINGLE, size: 12, color: BRAND.accent } },
  spacing: { before: 100, after: 100 },
  indent: { left: convertInchesToTwip(0.5), right: convertInchesToTwip(0.5) },
  children: [
    new TextRun({ text: "Simulation Context: ", font: "Calibri", size: 18, bold: true, color: BRAND.accentDark }),
    new TextRun({
      text: "This report was generated by a multi-agent AI simulation modeling the decision dynamics of DFW Airport's private 5G deployment. The simulation uses a mid-2025 scenario baseline \u2014 the point at which key decisions were being actively negotiated. Timeline references throughout reflect that decision window. The analytical framework and stakeholder dynamics remain current and applicable.",
      font: "Calibri", size: 18, color: BRAND.textDark,
    }),
  ],
}));

children.push(new Paragraph({ children: [new PageBreak()] }));

// --- EXECUTIVE SUMMARY ---
children.push(new Paragraph({
  heading: HeadingLevel.HEADING_1,
  spacing: { before: 200, after: 200 },
  border: { bottom: { style: BorderStyle.SINGLE, size: 4, color: BRAND.accent, space: 8 } },
  children: [new TextRun({ text: "Executive Summary", font: "Calibri Light", size: 36, color: BRAND.dark, bold: true })],
}));

// Recommendation box
children.push(new Paragraph({
  shading: { type: ShadingType.SOLID, color: BRAND.dark },
  spacing: { before: 200, after: 100 },
  indent: { left: 0, right: 0 },
  children: [
    new TextRun({ text: "  RECOMMENDATION:  ", font: "Calibri", size: 24, color: BRAND.accent, bold: true }),
    new TextRun({ text: "Conditional Go  |  Plan Strength: 7/10", font: "Calibri", size: 24, color: BRAND.white, bold: true }),
  ],
}));

children.push(new Paragraph({
  spacing: { before: 200, after: 100 },
  children: [new TextRun({
    text: "Six AI agents representing DFW Airport's key constituencies were run through a four-stage analytical pipeline to stress-test how the airport should structure its private 5G deployment. The simulation produced a negotiated consensus, identified vulnerabilities, and delivered a board-ready recommendation.",
    font: "Calibri", size: 22, color: BRAND.textDark,
  })],
}));

// Winning architecture
children.push(new Paragraph({
  spacing: { before: 200, after: 80 },
  children: [new TextRun({ text: "Winning Architecture: Hybrid Co-Investment", font: "Calibri", size: 24, color: BRAND.accentDark, bold: true })],
}));
children.push(new Paragraph({
  spacing: { after: 80 },
  children: [new TextRun({
    text: "DFW owns all physical and logical infrastructure. AT&T operates the carrier layer (spectrum management, SAS coordination, radio resources) under a performance-based services contract. Revenue is generated through multi-tenant access fees, carrier offload, and DFW-exclusive data monetization. This was the only architecture with zero inconsistencies across all six constituency groups.",
    font: "Calibri", size: 22, color: BRAND.textDark,
  })],
}));

// Key numbers
children.push(new Paragraph({
  spacing: { before: 200, after: 80 },
  children: [new TextRun({ text: "Key Financials", font: "Calibri", size: 24, color: BRAND.accentDark, bold: true })],
}));
const keyNumbers = [
  ["$80M+", "5-year cumulative net value across three revenue streams"],
  ["$15M", "Cargo consortium prepaid infrastructure commitment (binding)"],
  ["$6M/year", "Committed cargo tenant revenue on 5-year contracts"],
  ["$6\u201313M/year", "Data monetization opportunity (passenger flow, location advertising)"],
  ["$175\u2013200/mo", "Per-location concession connectivity (200+ locations, turnkey)"],
  ["99.99%", "Design-target uptime with zone-specific SLAs measured at point of consumption"],
];
for (const [num, desc] of keyNumbers) {
  children.push(new Paragraph({
    spacing: { before: 40, after: 40 },
    indent: { left: convertInchesToTwip(0.25) },
    children: [
      new TextRun({ text: `${num}  `, font: "Calibri", size: 24, color: BRAND.accent, bold: true }),
      new TextRun({ text: `\u2014 ${desc}`, font: "Calibri", size: 20, color: BRAND.textDark }),
    ],
  }));
}

// What the pipeline found
children.push(new Paragraph({
  spacing: { before: 250, after: 80 },
  children: [new TextRun({ text: "What the 4-Stage Pipeline Produced", font: "Calibri", size: 24, color: BRAND.accentDark, bold: true })],
}));

const pipelineFindings = [
  ["Stage 1 \u2014 Discover", "7 universal requirements and 18 priority-ranked specifications across technical, financial, operational, data, and timeline clusters. All six constituencies independently demanded \u226599.95% uptime, phased deployment with rollback, and vendor-portable architecture."],
  ["Stage 2 \u2014 Diagnose", "Four competing architectures evaluated against all constituency requirements. Hybrid Co-Investment (H3) emerged with zero inconsistencies vs. two for the runner-up. Key differentiators: federal security accountability (DFW must own), data monetization rights (requires infrastructure ownership), and vendor portability (contractual breakout provisions)."],
  ["Stage 3 \u2014 Negotiate", "Three rounds of constraint negotiation across 44 hard constraints. All 44 were satisfied in the final consensus. Produced detailed pricing (cargo: $0.25/sq ft/mo; concessions: $175\u2013200/mo; AT&T: $1.2\u20131.5M/yr operations fee), priority hierarchy (5 tiers from safety-critical to best-effort), and phased deployment plan with independent cargo zone timeline."],
  ["Stage 4 \u2014 Stress-Test", "10 attack vectors from Red Team (AT&T + Airline VP). 2 fully resolved, 8 require targeted plan modifications before contract execution. Most critical gaps: DPA Emergency Capacity Protocol, licensed-spectrum failover ($4\u20135M CapEx), and airline pricing specificity."],
];
for (const [stage, desc] of pipelineFindings) {
  children.push(new Paragraph({
    spacing: { before: 80, after: 20 },
    children: [new TextRun({ text: stage, font: "Calibri", size: 22, color: BRAND.dark, bold: true })],
  }));
  children.push(new Paragraph({
    spacing: { after: 60 },
    indent: { left: convertInchesToTwip(0.25) },
    children: [new TextRun({ text: desc, font: "Calibri", size: 20, color: BRAND.textDark })],
  }));
}

// Conditions for approval
children.push(new Paragraph({
  spacing: { before: 250, after: 80 },
  children: [new TextRun({ text: "7 Conditions for Board Approval", font: "Calibri", size: 24, color: BRAND.accentDark, bold: true })],
}));

const conditions = [
  "DPA Emergency Capacity Protocol as MSA exhibit \u2014 graduated thresholds, FCC compliance bright-line carve-out, design-time DPA capacity engineering",
  "Licensed-spectrum failover infrastructure ($4\u20135M DFW CapEx) \u2014 DPA-immune backup for Tier 0\u20131 ramp operations",
  "Airline pricing term sheet at concession/cargo-equivalent specificity \u2014 per-departure cap, Terminal F prepaid amortization, symmetric exit rights",
  "CWP degradation attribution methodology as MSA exhibit \u2014 seasonal normalization, joint root-cause process, independent RF adjudicator",
  "Inter-operator handoff SLA (\u2264500ms, \u22640.1% failure) \u2014 binding acceptance criteria for Terminal F carrier-operations award",
  "Per-gate-cluster SLA (99.95%) with application-layer monitoring and edge compute N+1 redundancy",
  "Concession deployment timeline contractually independent of airline LOI execution",
];
for (let c = 0; c < conditions.length; c++) {
  children.push(new Paragraph({
    spacing: { before: 40, after: 40 },
    indent: { left: convertInchesToTwip(0.35), hanging: convertInchesToTwip(0.35) },
    children: [
      new TextRun({ text: `${c + 1}.  `, font: "Calibri", size: 20, color: BRAND.accent, bold: true }),
      new TextRun({ text: conditions[c], font: "Calibri", size: 20, color: BRAND.textDark }),
    ],
  }));
}

// Methodology note
children.push(new Paragraph({
  spacing: { before: 300, after: 100 },
  shading: { type: ShadingType.SOLID, color: BRAND.lightGray },
  border: { left: { style: BorderStyle.SINGLE, size: 12, color: BRAND.accent } },
  indent: { left: 0 },
  children: [
    new TextRun({ text: "  Methodology: ", font: "Calibri", size: 18, bold: true, color: BRAND.accentDark }),
    new TextRun({
      text: "Six Claude Opus agents, each with distinct personas, hard constraints, and DFW-specific context, ran autonomously through four chained protocols: 1-2-4-All stakeholder discovery, Analysis of Competing Hypotheses, multi-round constraint negotiation, and dynamic Red/Blue/White team stress-testing. No human intervention shaped agent positions or outcomes.",
      font: "Calibri", size: 18, color: BRAND.textDark,
    }),
  ],
}));

children.push(new Paragraph({ children: [new PageBreak()] }));

// --- PROCESS SECTIONS ---
function processSection(section) {
  const elements = [];

  // Section heading
  if (section.level === 1 && section.title) {
    elements.push(new Paragraph({
      heading: HeadingLevel.HEADING_1,
      spacing: { before: 400, after: 200 },
      border: { bottom: { style: BorderStyle.SINGLE, size: 4, color: BRAND.accent, space: 8 } },
      children: [new TextRun({ text: section.title, font: "Calibri Light", size: 36, color: BRAND.dark, bold: true })],
    }));
  } else if (section.level === 2 && section.title) {
    elements.push(new Paragraph({
      heading: HeadingLevel.HEADING_2,
      spacing: { before: 300, after: 150 },
      children: [new TextRun({ text: section.title, font: "Calibri", size: 28, color: BRAND.accentDark, bold: true })],
    }));
  } else if (section.level === 3 && section.title) {
    elements.push(new Paragraph({
      heading: HeadingLevel.HEADING_3,
      spacing: { before: 200, after: 100 },
      children: [new TextRun({ text: section.title, font: "Calibri", size: 24, color: BRAND.dark, bold: true })],
    }));
  }

  // Process content lines
  const content = section.content;
  let i = 0;
  let inCodeBlock = false;
  let codeLines = [];

  while (i < content.length) {
    const line = content[i];

    // Skip HR lines
    if (line.match(/^---+$/)) { i++; continue; }

    // Code blocks - render as diagram images
    if (line.startsWith("```")) {
      if (inCodeBlock) {
        const idx = diagramCounter++;
        if (diagramImages[idx]) {
          const origW = diagramImages[`${idx}_w`];
          const origH = diagramImages[`${idx}_h`];
          // Scale to fit ~6 inches wide, preserving aspect ratio
          // ImageRun transformation expects pixels
          const targetW = 576; // 6 inches at 96 DPI
          const scale = targetW / origW;
          const targetH = Math.round(origH * scale);
          elements.push(new Paragraph({
            alignment: AlignmentType.CENTER,
            spacing: { before: 200, after: 200 },
            children: [new ImageRun({
              data: diagramImages[idx],
              transformation: { width: targetW, height: targetH },
              type: "png",
            })],
          }));
        }
        codeLines = [];
        inCodeBlock = false;
      } else {
        inCodeBlock = true;
      }
      i++; continue;
    }
    if (inCodeBlock) { codeLines.push(line); i++; continue; }

    // Tables
    if (line.includes("|") && line.trim().startsWith("|")) {
      const tableLines = [];
      while (i < content.length && content[i].includes("|") && content[i].trim().startsWith("|")) {
        tableLines.push(content[i]);
        i++;
      }
      const table = parseTable(tableLines);
      if (table) elements.push(table);
      elements.push(new Paragraph({ spacing: { after: 100 } }));
      continue;
    }

    // Blockquotes - styled callout
    if (line.startsWith("> ")) {
      const text = line.replace(/^> /, "").replace(/\*\*/g, "");
      elements.push(new Paragraph({
        shading: { type: ShadingType.SOLID, color: BRAND.lightGray },
        border: { left: { style: BorderStyle.SINGLE, size: 12, color: BRAND.accent } },
        spacing: { before: 100, after: 100 },
        indent: { left: convertInchesToTwip(0.3) },
        children: [new TextRun({ text, font: "Calibri", size: 20, italics: true, color: BRAND.textDark })],
      }));
      i++; continue;
    }

    // Bullet points
    if (line.match(/^[-*] /)) {
      const text = line.replace(/^[-*] /, "");
      elements.push(new Paragraph({
        bullet: { level: 0 },
        spacing: { before: 40, after: 40 },
        children: parseInline(text),
      }));
      i++; continue;
    }

    // Numbered items
    if (line.match(/^\d+\. /)) {
      const text = line.replace(/^\d+\. /, "");
      elements.push(new Paragraph({
        numbering: { reference: "numbered", level: 0 },
        spacing: { before: 40, after: 40 },
        children: parseInline(text),
      }));
      i++; continue;
    }

    // Empty lines
    if (line.trim() === "") { i++; continue; }

    // Regular paragraph
    elements.push(new Paragraph({
      spacing: { before: 80, after: 80 },
      children: parseInline(line),
    }));
    i++;
  }

  return elements;
}

// Process all sections
for (const section of sections) {
  if (section.level === 0) continue; // Skip pre-header
  // Page break before Stage headers
  if (section.level === 2 && section.title.startsWith("Stage ")) {
    children.push(new Paragraph({ children: [new PageBreak()] }));
  }
  children.push(...processSection(section));
}

// Build document
const doc = new Document({
  numbering: {
    config: [{
      reference: "numbered",
      levels: [{
        level: 0,
        format: NumberFormat.DECIMAL,
        text: "%1.",
        alignment: AlignmentType.START,
        style: { paragraph: { indent: { left: convertInchesToTwip(0.5), hanging: convertInchesToTwip(0.25) } } },
      }],
    }],
  },
  styles: {
    default: {
      document: {
        run: { font: "Calibri", size: 22, color: BRAND.textDark },
      },
    },
  },
  sections: [{
    properties: {
      page: {
        margin: {
          top: convertInchesToTwip(1),
          bottom: convertInchesToTwip(0.75),
          left: convertInchesToTwip(1),
          right: convertInchesToTwip(1),
        },
      },
    },
    headers: {
      default: new Header({
        children: [new Paragraph({
          alignment: AlignmentType.RIGHT,
          children: [
            new TextRun({ text: "IMAGINE WIRELESS", font: "Calibri Light", size: 16, color: BRAND.accent, bold: true, characterSpacing: 200 }),
            new TextRun({ text: "  |  DFW Private 5G Decision-Maker Simulation", font: "Calibri", size: 16, color: BRAND.medGray }),
          ],
        })],
      }),
    },
    footers: {
      default: new Footer({
        children: [new Paragraph({
          alignment: AlignmentType.CENTER,
          border: { top: { style: BorderStyle.SINGLE, size: 1, color: BRAND.medGray, space: 4 } },
          children: [
            new TextRun({ text: "Confidential  |  Prepared by Scott Ewalt for Imagine Wireless  |  Page ", font: "Calibri", size: 16, color: BRAND.textLight }),
            new TextRun({ children: [PageNumber.CURRENT], font: "Calibri", size: 16, color: BRAND.textLight }),
          ],
        })],
      }),
    },
    children,
  }],
});

const buffer = await Packer.toBuffer(doc);
const outPath = "/Users/scottewalt/Documents/CE - AGENTS/CE - Multi-Agent Orchesration/output/airport_5g_test/DFW_Private_5G_Board_Report.docx";
fs.writeFileSync(outPath, buffer);
console.log(`Written: ${outPath} (${(buffer.length / 1024).toFixed(0)} KB)`);
