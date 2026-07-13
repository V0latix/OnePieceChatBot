import { GraphEdge, GraphNode } from "../lib/api";

interface D3ForceGraphProps {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

interface PositionedNode extends GraphNode {
  x: number;
  y: number;
}

// ponytail: static radial layout, no force simulation. Swap in d3-force if the
// graph ever needs drag/zoom or grows past a few dozen nodes.
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
    <div className="overflow-x-auto border border-foreground bg-background p-2">
      <svg viewBox={`0 0 ${width} ${height}`} className="h-[280px] w-full min-w-[620px]">
        {edges.map((edge, index) => {
          const source = byId.get(edge.source);
          const target = byId.get(edge.target);
          if (!source || !target) {
            return null;
          }
          return (
            <g key={`${edge.source}-${edge.target}-${edge.type}-${index}`}>
              <line
                x1={source.x}
                y1={source.y}
                x2={target.x}
                y2={target.y}
                stroke="#0a0a0a"
                strokeOpacity="0.35"
                strokeWidth="1"
              />
              <text
                x={(source.x + target.x) / 2}
                y={(source.y + target.y) / 2 - 6}
                textAnchor="middle"
                fontSize="9"
                fill="#777777"
              >
                {edge.type}
              </text>
            </g>
          );
        })}

        {positioned.map((node) => (
          <g key={node.id}>
            <circle cx={node.x} cy={node.y} r="22" fill="#1a56db" stroke="#0a0a0a" strokeWidth="1.5" />
            <text x={node.x} y={node.y + 3} textAnchor="middle" fontSize="9" fill="#ffffff">
              {node.label.length > 17 ? `${node.label.slice(0, 14)}...` : node.label}
            </text>
          </g>
        ))}
      </svg>
    </div>
  );
}
