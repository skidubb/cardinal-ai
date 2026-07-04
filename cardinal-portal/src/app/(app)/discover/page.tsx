import { auth } from "@clerk/nextjs/server";
import { fetchAgents, fetchProtocols } from "@/lib/api";
import { DiscoverForm } from "./DiscoverForm";

export default async function DiscoverPage() {
  const { orgSlug } = await auth();
  const [protocols, agents] = await Promise.all([
    fetchProtocols().catch(() => []),
    fetchAgents().catch(() => []),
  ]);

  return (
    <div className="mx-auto max-w-4xl px-8 py-10 space-y-6">
      <header>
        <span className="ce-eyebrow">Discover</span>
        <h1 className="mt-2 text-3xl font-bold tracking-tight">
          Pull questions out of a document
        </h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Upload a 10-K, CIM, research paper, or memo. We surface the most
          analytically vexing questions — categorized, ranked, and pre-mapped
          to the best-fit protocol.
          {orgSlug ? <span className="ml-2 font-mono">· {orgSlug}</span> : null}
        </p>
      </header>

      <DiscoverForm protocols={protocols} agents={agents} />
    </div>
  );
}
