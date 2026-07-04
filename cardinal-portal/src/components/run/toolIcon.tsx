import {
  Database,
  FileText,
  Globe,
  Image as ImageIcon,
  Newspaper,
  Search,
  TrendingUp,
  Wrench,
  type LucideIcon,
} from "lucide-react";

const TOOL_ICONS: Array<[RegExp, LucideIcon]> = [
  [/^(sec_edgar|edgar|filings)/i, Newspaper],
  [/^(pinecone|memory|recall|retrieve)/i, Database],
  [/^(brave|search|web_search|google_search)/i, Search],
  [/^(github|gh_)/i, Wrench],
  [/^(notion)/i, FileText],
  [/^(census|bls|fred|stat)/i, TrendingUp],
  [/^(image_gen|nano_banana|midjourney)/i, ImageIcon],
  [/^(http|fetch|web)/i, Globe],
];

export function iconForTool(toolName: string): LucideIcon {
  for (const [pattern, icon] of TOOL_ICONS) {
    if (pattern.test(toolName)) return icon;
  }
  return Wrench;
}
