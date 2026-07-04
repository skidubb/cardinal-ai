import { auth } from "@clerk/nextjs/server";
import { PricingTable } from "@clerk/nextjs";
import { fetchUsage } from "@/lib/api";
import { UsageMeter } from "@/components/billing/UsageMeter";

export default async function BillingPage() {
  const { orgSlug } = await auth();

  const usage = orgSlug ? await fetchUsage().catch(() => null) : null;

  return (
    <div className="mx-auto max-w-5xl px-8 py-10 space-y-8">
      <header>
        <span className="ce-eyebrow">Workspace</span>
        <h1 className="mt-2 text-3xl font-bold tracking-tight">Billing</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Current plan
          {usage?.plan ? (
            <span className="ml-2 font-medium text-foreground">
              {usage.plan.charAt(0).toUpperCase() + usage.plan.slice(1)}
            </span>
          ) : null}
          {orgSlug ? <span className="ml-2 font-mono">· {orgSlug}</span> : null}
        </p>
      </header>

      {!orgSlug ? (
        <div className="rounded-xl border border-[rgb(var(--ce-yellow-500))]/40 bg-[rgb(var(--ce-yellow-500))]/10 p-4">
          <p className="text-[rgb(var(--ce-yellow-500))]">
            Pick or create an organization to view billing.
          </p>
        </div>
      ) : (
        <>
          {usage ? <UsageMeter usage={usage} /> : null}

          <section>
            <h2 className="mb-3 text-sm font-semibold tracking-tight text-foreground">Plans</h2>
            <PricingTable for="organization" />
          </section>
        </>
      )}
    </div>
  );
}
