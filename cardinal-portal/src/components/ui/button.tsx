import * as React from "react";

type Variant = "primary" | "secondary" | "outline" | "ghost" | "onDark" | "onDarkSolid";
type Size = "sm" | "md" | "lg";

const variantClasses: Record<Variant, string> = {
  primary:
    "bg-primary text-primary-foreground hover:bg-[rgb(var(--ce-indigo-500))] shadow-[var(--shadow-indigo)]",
  secondary: "bg-secondary text-secondary-foreground hover:bg-[rgb(var(--ce-slate-200))]",
  outline: "border border-border bg-transparent hover:bg-secondary",
  ghost: "bg-transparent hover:bg-secondary",
  onDark:
    "border border-white/20 bg-white/10 text-white backdrop-blur-sm hover:bg-white/20",
  onDarkSolid: "bg-white text-slate-950 font-bold hover:opacity-90",
};

const sizeClasses: Record<Size, string> = {
  sm: "h-8 px-3 text-xs",
  md: "h-10 px-4 text-sm",
  lg: "h-13 px-7 text-sm font-bold",
};

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: Size;
  pill?: boolean;
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ variant = "primary", size = "md", pill = false, className = "", ...rest }, ref) => {
    const radius = pill ? "rounded-full" : "rounded-md";
    const base =
      "inline-flex items-center justify-center gap-2 font-medium whitespace-nowrap transition-colors focus-visible:outline-none focus-visible:ring-[3px] focus-visible:ring-ring/50 disabled:pointer-events-none disabled:opacity-50";
    return (
      <button
        ref={ref}
        className={[base, radius, sizeClasses[size], variantClasses[variant], className]
          .filter(Boolean)
          .join(" ")}
        {...rest}
      />
    );
  }
);
Button.displayName = "Button";
