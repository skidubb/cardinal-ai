import * as React from "react";

export interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  hoverable?: boolean;
  elevated?: boolean;
}

export function Card({
  hoverable = false,
  elevated = false,
  className = "",
  ...rest
}: CardProps) {
  return (
    <div
      className={[
        "rounded-xl border border-border bg-card p-6",
        hoverable && "transition-all duration-300 hover:border-primary/50",
        elevated && "shadow-2xl",
        className,
      ]
        .filter(Boolean)
        .join(" ")}
      {...rest}
    />
  );
}

export function CardHeader({ className = "", ...rest }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={["mb-4 space-y-1.5", className].join(" ")} {...rest} />;
}

export function CardTitle({ className = "", ...rest }: React.HTMLAttributes<HTMLHeadingElement>) {
  return (
    <h3
      className={["text-xl font-semibold leading-snug tracking-tight", className].join(" ")}
      {...rest}
    />
  );
}

export function CardDescription({
  className = "",
  ...rest
}: React.HTMLAttributes<HTMLParagraphElement>) {
  return (
    <p className={["text-sm text-muted-foreground leading-relaxed", className].join(" ")} {...rest} />
  );
}

export function CardContent({ className = "", ...rest }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={className} {...rest} />;
}
