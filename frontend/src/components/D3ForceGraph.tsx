import { GraphEdge, GraphNode } from "../lib/api";

interface D3ForceGraphProps {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

interface PositionedNode extends GraphNode {
  x: number;
  y: number;
}

export default function D3ForceGraph({ nodes, edges }: D3ForceGraphProps) {
  const width = 820;
  const height = 340;
  const centerX = width / 2;
  const centerY = height / 2;
  const radius = Math.min(width, height) * 0.34;

  const positioned: PositionedNode[] = nodes.map((node, index) => {
    const angle = (index / Math.max(nodes.length, 1)) * Math.PI * 2;
    return {
      ...node,
      x: centerX + Math.cos(angle) * radius,
      y: centerY + Math.sin(angle) * radius,
    };
  });

  const byId = new Map(positioned.map((node) => [node.id, node]));

  return (
    <div className="overflow-x-auto rounded-xl border border-gold/20 bg-[#0c172a] p-2">
      <svg viewBox={`0 0 ${width} ${height}`} className="h-[280px] w-full min-w-[620px]">
        <defs>
          <linearGradient id="edgeGradient" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#d94f2b" />
            <stop offset="100%" stopColor="#e7b24a" />
          </linearGradient>
        </defs>

        {edges.map((edge, index) => {
          const source = byId.get(edge.source);
          const target = byId.get(edge.target);
          if (!source || !target) {
            return null;
          }
          return (
            <g key={`${edge.source}-${edge.target}-${edge.type}-${index}`}>
              <line x1={source.x} y1={source.y} x2={target.x} y2={target.y} stroke="url(#edgeGradient)" strokeOpacity="0.75" strokeWidth="1.5" />
              <text x={(source.x + target.x) / 2} y={(source.y + target.y) / 2 - 6} textAnchor="middle" fontSize="9" fill="#ccb88d">
                {edge.type}
              </text>
            </g>
          );
        })}

        {positioned.map((node) => (
          <g key={node.id}>
            <circle cx={node.x} cy={node.y} r="20" fill="#0e223b" stroke="#e7b24a" strokeWidth="1.6" />
            <text x={node.x} y={node.y + 3} textAnchor="middle" fontSize="9" fill="#f7e5bf">
              {node.label.length > 17 ? `${node.label.slice(0, 14)}...` : node.label}
            </text>
          </g>
        ))}
      </svg>
    </div>
  );
}
