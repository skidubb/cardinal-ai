import * as React from "react";

export interface EyebrowProps extends React.HTMLAttributes<HTMLSpanElement> {
  number?: string;
}

export function Eyebrow({ number, className = "", children, ...rest }: EyebrowProps) {
  return (
    <span
      className={[
        "font-mono text-sm uppercase tracking-tight text-primary",
        className,
      ].join(" ")}
      {...rest}
    >
      {number ? `${number}. ` : null}
      {children}
    </span>
  );
}
