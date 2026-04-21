export const brandAppearance = {
  variables: {
    colorPrimary: "rgb(79 70 229)",
    colorBackground: "rgb(255 255 255)",
    colorText: "rgb(15 23 42)",
    colorTextSecondary: "rgb(100 116 139)",
    colorDanger: "rgb(239 68 68)",
    colorSuccess: "rgb(34 197 94)",
    colorInputBackground: "rgb(255 255 255)",
    colorInputText: "rgb(15 23 42)",
    borderRadius: "0.75rem",
    fontFamily: "var(--font-geist-sans)",
    fontFamilyButtons: "var(--font-geist-sans)",
    fontSize: "0.875rem",
  },
  elements: {
    card: "shadow-2xl border border-border bg-card",
    formButtonPrimary:
      "bg-primary hover:bg-[rgb(var(--ce-indigo-500))] text-primary-foreground normal-case font-medium",
    headerTitle: "text-foreground tracking-tight",
    headerSubtitle: "text-muted-foreground",
    socialButtonsBlockButton: "border border-border hover:bg-secondary",
    formFieldInput:
      "border border-input bg-background focus-visible:ring-[3px] focus-visible:ring-ring/50",
    footerActionLink: "text-primary hover:underline underline-offset-4",
    dividerLine: "bg-border",
    dividerText: "text-muted-foreground",
    identityPreviewEditButton: "text-primary",
  },
} as const;
