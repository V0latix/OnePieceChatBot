import { GraphResponse } from "../lib/api";
import D3ForceGraph from "./D3ForceGraph";

interface GraphViewerProps {
  graph: GraphResponse | null;
  loading?: boolean;
  error?: string | null;
}

export default function GraphViewer({ graph, loading = false, error = null }: GraphViewerProps) {
  const nodes = graph?.nodes ?? [];
  const edges = graph?.edges ?? [];

  return (
    <section className="card fade-in rounded-2xl p-5 md:p-6">
      <h3 className="mb-4 text-2xl tracking-wide [font-family:var(--font-display)]">Knowledge Graph</h3>
      {loading ? <p className="mb-3 text-sm text-[#cdbb98]">Chargement du graphe...</p> : null}
      {error ? <p className="mb-3 text-sm text-ember">{error}</p> : null}
      {!nodes.length ? <p className="text-sm text-[#d9caa8]">Aucun sous-graphe charge.</p> : <D3ForceGraph nodes={nodes} edges={edges} />}
    </section>
  );
}
