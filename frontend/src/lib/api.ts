export interface SourceCitation {
  entity_name: string;
  section: string;
  source_url: string;
  score: number;
}

export interface AskResponse {
  answer: string;
  entities: string[];
  confidence: number;
  sources: SourceCitation[];
}

export interface EntityRelation {
  source?: string;
  relation?: string;
  target?: string;
  target_type?: string;
}

export interface EntityResponse {
  name: string;
  type: string;
  infobox: Record<string, string>;
  relations: EntityRelation[];
}

export interface GraphNode {
  id: string;
  label: string;
  type: string;
}

export interface GraphEdge {
  source: string;
  target: string;
  type: string;
}

export interface GraphResponse {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

function apiBaseUrl(): string {
  return process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
}

export async function askQuestion(question: string, spoilerLimitArc?: string): Promise<AskResponse> {
  const response = await fetch(`${apiBaseUrl()}/api/ask`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      question,
      spoiler_limit_arc: spoilerLimitArc && spoilerLimitArc !== "Aucun" ? spoilerLimitArc : null,
    }),
  });

  if (!response.ok) {
    throw new Error(`API error: ${response.status}`);
  }

  return (await response.json()) as AskResponse;
}

export async function fetchEntity(name: string): Promise<EntityResponse> {
  const response = await fetch(`${apiBaseUrl()}/api/entity/${encodeURIComponent(name)}`);
  if (!response.ok) {
    throw new Error(`Entity API error: ${response.status}`);
  }
  return (await response.json()) as EntityResponse;
}

export async function fetchGraph(name: string, depth = 2): Promise<GraphResponse> {
  const response = await fetch(
    `${apiBaseUrl()}/api/graph/${encodeURIComponent(name)}?depth=${encodeURIComponent(String(depth))}`,
  );
  if (!response.ok) {
    throw new Error(`Graph API error: ${response.status}`);
  }
  return (await response.json()) as GraphResponse;
}
