import {
  siGithub,
  siNotion,
  siGooglegemini,
  siGoogledrive,
  siHubspot,
  siGmail,
  siLinear,
  siJira,
  siDropbox,
  siAirtable,
  siLangchain,
  siAnthropic,
  siClaude,
} from "simple-icons";
import type { SimpleIcon } from "simple-icons";
import { Plug } from "lucide-react";

// Static map of slugs to icons we actively surface. Tree-shakes cleanly.
// Note: simple-icons removed Slack and OpenAI per brand requests — use lettermarks below.
const SLUG_MAP: Record<string, SimpleIcon> = {
  github: siGithub,
  notion: siNotion,
  googlegemini: siGooglegemini,
  googledrive: siGoogledrive,
  hubspot: siHubspot,
  gmail: siGmail,
  linear: siLinear,
  jira: siJira,
  dropbox: siDropbox,
  airtable: siAirtable,
  langchain: siLangchain,
  anthropic: siAnthropic,
  claude: siClaude,
};

// Hand-styled lettermarks for brands not in simple-icons
const LETTERMARK: Record<string, { letter: string; hex: string }> = {
  pinecone: { letter: "P", hex: "#000000" },
  "sec-edgar": { letter: "S", hex: "#0F172A" },
  sec: { letter: "S", hex: "#0F172A" },
  census: { letter: "C", hex: "#1E40AF" },
  bls: { letter: "B", hex: "#7F1D1D" },
  granola: { letter: "G", hex: "#F59E0B" },
  pricing: { letter: "$", hex: "#0F172A" },
  "pricing-calculator": { letter: "$", hex: "#0F172A" },
  adobeacrobatreader: { letter: "A", hex: "#EB1000" },
  "github-intel": { letter: "G", hex: `#${siGithub.hex}` },
  openai: { letter: "O", hex: "#10A37F" },
  slack: { letter: "S", hex: "#4A154B" },
};

export function BrandIcon({
  slug,
  size = 20,
  className = "",
  colored = true,
}: {
  slug?: string | null;
  size?: number;
  className?: string;
  colored?: boolean;
}) {
  if (!slug) {
    return <Plug size={size} strokeWidth={1.75} className={`text-muted-foreground ${className}`} />;
  }

  const icon = SLUG_MAP[slug];
  if (icon) {
    return (
      <svg
        width={size}
        height={size}
        viewBox="0 0 24 24"
        xmlns="http://www.w3.org/2000/svg"
        className={className}
        role="img"
        aria-label={icon.title}
      >
        <title>{icon.title}</title>
        <path fill={colored ? `#${icon.hex}` : "currentColor"} d={icon.path} />
      </svg>
    );
  }

  const letter = LETTERMARK[slug];
  if (letter) {
    return (
      <div
        className={`flex items-center justify-center rounded font-bold ${className}`}
        style={{
          width: size,
          height: size,
          background: colored ? letter.hex : "rgb(var(--secondary))",
          color: colored ? "#fff" : "rgb(var(--foreground))",
          fontSize: size * 0.55,
          lineHeight: 1,
        }}
        aria-label={slug}
      >
        {letter.letter}
      </div>
    );
  }

  return <Plug size={size} strokeWidth={1.75} className={`text-muted-foreground ${className}`} />;
}
