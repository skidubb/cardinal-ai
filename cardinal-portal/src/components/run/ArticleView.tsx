import type { Article } from "@/lib/api";
import { Markdown } from "@/components/ui/markdown";

/**
 * Editorial "Story" rendering of a protocol run — the magazine-quality
 * counterpart to the raw agent-transcript stack ("Analyst view").
 */
export function ArticleView({ article }: { article: Article }) {
  const bylineDate = article.byline.generated_at
    ? new Date(article.byline.generated_at).toLocaleDateString(undefined, {
        year: "numeric",
        month: "long",
        day: "numeric",
      })
    : null;

  return (
    <article className="mx-auto max-w-3xl px-2 py-4">
      <header className="border-b border-border pb-6 text-center">
        <div className="ce-eyebrow mb-4 uppercase tracking-[0.15em]">
          Cardinal Element Analysis
        </div>
        <h1
          className="text-balance text-4xl font-semibold leading-[1.1] tracking-tight text-foreground md:text-5xl"
          style={{ fontFamily: "var(--font-serif-display)" }}
        >
          {article.headline}
        </h1>
        {article.deck ? (
          <p
            className="mx-auto mt-4 max-w-2xl text-lg leading-snug text-muted-foreground"
            style={{ fontFamily: "var(--font-serif-text)" }}
          >
            {article.deck}
          </p>
        ) : null}
        <div className="mt-5 text-xs text-muted-foreground">
          By {formatAgentList(article.byline.agents)}
          {" · "}
          <span className="font-mono">{article.byline.protocol}</span>
          {bylineDate ? (
            <>
              {" · "}
              {bylineDate}
            </>
          ) : null}
        </div>
      </header>

      <div className="article-lede article-prose mt-8">
        <Markdown>{article.lede}</Markdown>
      </div>

      {article.sections.map((section, i) => (
        <section key={`${section.heading}-${i}`} className="mt-10">
          <h2
            className="mb-3 text-center text-2xl font-semibold tracking-tight text-foreground"
            style={{ fontFamily: "var(--font-serif-display)" }}
          >
            {section.heading}
          </h2>
          <div className="article-prose">
            <Markdown>{section.body_markdown}</Markdown>
          </div>
          {section.pull_quote ? (
            <figure className="article-pull-quote">
              &ldquo;{section.pull_quote.text}&rdquo;
              <figcaption className="article-pull-quote-attribution">
                {section.pull_quote.attribution}
              </figcaption>
            </figure>
          ) : null}
        </section>
      ))}

      {article.tensions.length > 0 ? (
        <section className="mt-10 border-t border-border pt-6">
          <h3 className="ce-label mb-4 text-center">Point / Counterpoint</h3>
          {article.tensions.map((tension, i) => (
            <div key={`${tension.framing}-${i}`} className="mb-6 last:mb-0">
              <div
                className="mb-3 text-center text-sm font-semibold text-foreground"
                style={{ fontFamily: "var(--font-serif-display)" }}
              >
                {tension.framing}
              </div>
              <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                {tension.sides.map((side, j) => (
                  <div
                    key={j}
                    className={`border-l-2 pl-4 text-sm leading-relaxed text-foreground ${
                      j === 0 ? "border-primary" : "border-accent"
                    }`}
                    style={{ fontFamily: "var(--font-serif-text)" }}
                  >
                    {side}
                  </div>
                ))}
              </div>
            </div>
          ))}
        </section>
      ) : null}

      {article.what_next ? (
        <section className="mt-10 border-t border-border pt-6">
          <h3
            className="mb-3 text-center text-xl font-semibold tracking-tight text-foreground"
            style={{ fontFamily: "var(--font-serif-display)" }}
          >
            What happens next
          </h3>
          <div className="article-prose">
            <Markdown>{article.what_next}</Markdown>
          </div>
          <div className="text-center">
            <span className="article-end-mark" aria-hidden="true">
              &#9632;
            </span>
          </div>
        </section>
      ) : null}
    </article>
  );
}

function formatAgentList(agents: string[]): string {
  if (agents.length === 0) return "Cardinal Element";
  if (agents.length === 1) return agents[0];
  if (agents.length === 2) return `${agents[0]} and ${agents[1]}`;
  return `${agents.slice(0, -1).join(", ")}, and ${agents[agents.length - 1]}`;
}
