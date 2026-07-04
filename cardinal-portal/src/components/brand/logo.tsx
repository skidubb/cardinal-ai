import Image from "next/image";

export interface LogoProps {
  variant?: "wordmark" | "icon";
  width?: number;
  height?: number;
  className?: string;
  priority?: boolean;
}

export function Logo({
  variant = "wordmark",
  width,
  height,
  className = "",
  priority = false,
}: LogoProps) {
  if (variant === "icon") {
    return (
      <Image
        src="/icon.svg"
        alt="Cardinal Element"
        width={width ?? 32}
        height={height ?? 32}
        className={className}
        priority={priority}
      />
    );
  }
  return (
    <Image
      src="/cardinal-element-light.svg"
      alt="Cardinal Element"
      width={width ?? 180}
      height={height ?? 40}
      className={className}
      priority={priority}
    />
  );
}
