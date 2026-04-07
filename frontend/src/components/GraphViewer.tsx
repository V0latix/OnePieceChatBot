interface GraphViewerProps {
  nodes: Array<{ id: string; label: string }>;
  edges: Array<{ source: string; target: string; type: string }>;
}

export default function GraphViewer({ nodes, edges }: GraphViewerProps) {
  return (
    <section className="card fade-in rounded-2xl p-5 md:p-6">
      <h3 className="mb-4 text-2xl tracking-wide [font-family:var(--font-display)]">Knowledge Graph</h3>
      <div className="space-y-2 text-sm text-[#d9caa8]">
        {nodes.length === 0 ? <p>Aucun sous-graphe charge.</p> : null}
        {edges.slice(0, 8).map((edge) => (
          <p key={`${edge.source}-${edge.target}-${edge.type}`}>
            <span className="text-gold">{edge.source}</span> -[{edge.type}]-&gt; {edge.target}
          </p>
        ))}
      </div>
    </section>
  );
}
