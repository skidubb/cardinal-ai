"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

/**
 * Branded markdown renderer for agent transcripts + synthesis blocks.
 * Tight vertical rhythm, indigo headings, clean tables, monospace code.
 */
export function Markdown({ children, className = "" }: { children: string; className?: string }) {
  return (
    <div className={`markdown text-sm leading-relaxed text-foreground ${className}`}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          h1: ({ children }) => (
            <h1 className="mt-6 mb-3 text-xl font-bold tracking-tight text-foreground first:mt-0">
              {children}
            </h1>
          ),
          h2: ({ children }) => (
            <h2 className="mt-5 mb-2 border-b border-border pb-1.5 text-lg font-bold tracking-tight text-primary first:mt-0">
              {children}
            </h2>
          ),
          h3: ({ children }) => (
            <h3 className="mt-4 mb-1.5 text-base font-semibold tracking-tight text-foreground">
              {children}
            </h3>
          ),
          h4: ({ children }) => (
            <h4 className="mt-3 mb-1 text-sm font-semibold text-foreground">{children}</h4>
          ),
          p: ({ children }) => (
            <p className="my-2 text-pretty leading-relaxed text-foreground">{children}</p>
          ),
          strong: ({ children }) => (
            <strong className="font-semibold text-foreground">{children}</strong>
          ),
          em: ({ children }) => <em className="italic">{children}</em>,
          ul: ({ children }) => <ul className="my-2 list-disc space-y-1 pl-5">{children}</ul>,
          ol: ({ children }) => <ol className="my-2 list-decimal space-y-1 pl-5">{children}</ol>,
          li: ({ children }) => <li className="text-pretty leading-relaxed">{children}</li>,
          blockquote: ({ children }) => (
            <blockquote className="my-3 rounded-r-lg border-l-3 border-primary bg-primary/5 px-4 py-2 text-muted-foreground">
              {children}
            </blockquote>
          ),
          code: ({ children, className: codeClass }) => {
            const isInline = !codeClass;
            if (isInline) {
              return (
                <code className="rounded bg-secondary px-1 py-0.5 font-mono text-[0.85em] text-foreground">
                  {children}
                </code>
              );
            }
            return (
              <code className="font-mono text-xs text-foreground">{children}</code>
            );
          },
          pre: ({ children }) => (
            <pre className="my-3 overflow-x-auto rounded-lg border border-border bg-[rgb(var(--ce-slate-900))] p-4 font-mono text-xs leading-relaxed text-[rgb(var(--ce-slate-100))]">
              {children}
            </pre>
          ),
          a: ({ children, href }) => (
            <a
              href={href}
              target="_blank"
              rel="noopener noreferrer"
              className="text-primary underline decoration-primary/40 underline-offset-4 transition-colors hover:decoration-primary"
            >
              {children}
            </a>
          ),
          hr: () => <hr className="my-5 border-border" />,
          table: ({ children }) => (
            <div className="my-3 overflow-x-auto rounded-lg border border-border">
              <table className="w-full border-collapse text-xs">{children}</table>
            </div>
          ),
          thead: ({ children }) => <thead className="bg-primary text-primary-foreground">{children}</thead>,
          th: ({ children }) => (
            <th className="px-3 py-2 text-left text-[10px] font-semibold uppercase tracking-wider">
              {children}
            </th>
          ),
          td: ({ children }) => (
            <td className="border-t border-border px-3 py-2 align-top text-foreground">{children}</td>
          ),
          tr: ({ children }) => <tr className="even:bg-muted">{children}</tr>,
        }}
      >
        {children}
      </ReactMarkdown>
    </div>
  );
}
