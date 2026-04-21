import { Show, SignInButton, SignUpButton, UserButton, OrganizationSwitcher } from "@clerk/nextjs";
import Link from "next/link";

export default function Home() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-12">
      <div className="max-w-2xl w-full space-y-8">
        <header className="space-y-2">
          <h1 className="text-4xl font-semibold tracking-tight">
            Cardinal<span className="bg-gradient-to-r from-pink-400 via-fuchsia-400 to-cyan-400 bg-clip-text text-transparent"> Element</span>
          </h1>
          <p className="text-slate-400 text-lg">
            AI-Native Growth Architecture. Your business has a brain.
          </p>
        </header>

        <Show when="signed-out">
          <div className="space-y-4">
            <p className="text-slate-300">
              An institutional knowledge graph for your business &mdash; built and maintained by AI agents.
            </p>
            <div className="flex gap-3">
              <SignInButton>
                <button className="rounded-md bg-fuchsia-600 px-4 py-2 text-sm font-medium hover:bg-fuchsia-500 transition">
                  Sign in
                </button>
              </SignInButton>
              <SignUpButton>
                <button className="rounded-md border border-slate-700 px-4 py-2 text-sm font-medium hover:bg-slate-900 transition">
                  Create account
                </button>
              </SignUpButton>
            </div>
          </div>
        </Show>

        <Show when="signed-in">
          <div className="space-y-6">
            <div className="flex items-center gap-4">
              <UserButton />
              <OrganizationSwitcher hidePersonal />
            </div>
            <Link
              href="/dashboard"
              className="inline-block rounded-md bg-fuchsia-600 px-4 py-2 text-sm font-medium hover:bg-fuchsia-500 transition"
            >
              Go to dashboard &rarr;
            </Link>
          </div>
        </Show>
      </div>
    </main>
  );
}
