import { Show, SignInButton, SignUpButton, UserButton, OrganizationSwitcher } from "@clerk/nextjs";
import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Pill } from "@/components/ui/pill";
import { Logo } from "@/components/brand/logo";

export default function Home() {
  return (
    <main className="flex min-h-screen flex-col">
      <nav className="flex items-center justify-between px-6 py-6 md:px-12">
        <Logo priority />
        <div className="flex items-center gap-3">
          <Show when="signed-out">
            <SignInButton>
              <Button variant="ghost" size="sm">
                Sign in
              </Button>
            </SignInButton>
            <SignUpButton>
              <Button size="sm">Get Started</Button>
            </SignUpButton>
          </Show>
          <Show when="signed-in">
            <OrganizationSwitcher hidePersonal />
            <UserButton />
          </Show>
        </div>
      </nav>

      <section className="flex flex-1 items-center px-6 py-24 md:px-12">
        <div className="mx-auto max-w-4xl space-y-8 text-center">
          <Pill tone="light">AI-Native Growth Architecture</Pill>

          <h1 className="text-balance text-5xl font-bold leading-tight tracking-tight md:text-7xl">
            A Growth Engine Built for the{" "}
            <span className="ce-gradient-text">AI Era.</span>
          </h1>

          <p className="mx-auto max-w-2xl text-pretty text-lg leading-relaxed text-muted-foreground">
            When complexity and manual processes are choking growth, revenue leaders need a clean,
            AI-native engine that actually moves pipeline, conversion, and retention.
          </p>

          <Show when="signed-out">
            <div className="flex flex-wrap items-center justify-center gap-3 pt-4">
              <SignUpButton>
                <Button size="lg">
                  Get a Readiness Audit
                  <ArrowRight size={16} />
                </Button>
              </SignUpButton>
              <SignInButton>
                <Button variant="outline" size="lg">
                  Sign In
                </Button>
              </SignInButton>
            </div>
          </Show>

          <Show when="signed-in">
            <div className="flex justify-center pt-4">
              <Link
                href="/dashboard"
                className="inline-flex h-13 items-center justify-center gap-2 rounded-md bg-primary px-7 text-sm font-bold text-primary-foreground shadow-[var(--shadow-indigo)] transition-colors hover:bg-[rgb(var(--ce-indigo-500))]"
              >
                Go to Dashboard
                <ArrowRight size={16} />
              </Link>
            </div>
          </Show>
        </div>
      </section>
    </main>
  );
}
