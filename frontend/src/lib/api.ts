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

export interface ConversationMessage {
  role: "user" | "assistant";
  content: string;
}

export interface StreamCallbacks {
  onMetadata: (meta: { sources: SourceCitation[]; entities: string[]; confidence: number }) => void;
  onToken: (text: string) => void;
  onDone: () => void;
  onError: (err: Error) => void;
}

export async function askQuestionStream(
  question: string,
  callbacks: StreamCallbacks,
  spoilerLimitArc?: string,
  history?: ConversationMessage[],
): Promise<void> {
  const response = await fetch(`${apiBaseUrl()}/api/ask/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      question,
      spoiler_limit_arc: spoilerLimitArc && spoilerLimitArc !== "Aucun" ? spoilerLimitArc : null,
      history: history ?? [],
    }),
  });

  if (!response.ok || !response.body) {
    throw new Error(`Stream API error: ${response.status}`);
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const parts = buffer.split("\n\n");
    buffer = parts.pop() ?? "";

    for (const part of parts) {
      const eventMatch = part.match(/^event: (\w+)\ndata: (.+)$/s);
      if (!eventMatch) continue;
      const [, eventName, dataRaw] = eventMatch;

      try {
        const data = JSON.parse(dataRaw) as Record<string, unknown>;
        if (eventName === "metadata") {
          callbacks.onMetadata(data as { sources: SourceCitation[]; entities: string[]; confidence: number });
        } else if (eventName === "token") {
          callbacks.onToken((data as { text: string }).text);
        } else if (eventName === "done") {
          callbacks.onDone();
        }
      } catch {
        // Ignore les lignes malformees
      }
    }
  }
}

export async function fetchEntity(name: string): Promise<EntityResponse> {
  const response = await fetch(`${apiBaseUrl()}/api/entity/${encodeURIComponent(name)}`);
  if (!response.ok) {
    throw new Error(`Entity API error: ${response.status}`);
  }
  return (await response.json()) as EntityResponse;
}

export interface SearchResult {
  chunk_id: string;
  entity_name: string;
  entity_type: string;
  section: string;
  content: string;
  source_url: string;
  score: number;
}

export async function searchChunks(query: string, entityType?: string, spoilerLimitArc?: string): Promise<SearchResult[]> {
  const params = new URLSearchParams({ q: query });
  if (entityType) params.set("type", entityType);
  if (spoilerLimitArc && spoilerLimitArc !== "Aucun") params.set("spoiler_limit_arc", spoilerLimitArc);
  const response = await fetch(`${apiBaseUrl()}/api/search?${params.toString()}`);
  if (!response.ok) {
    throw new Error(`Search API error: ${response.status}`);
  }
  const data = (await response.json()) as { results: SearchResult[] };
  return data.results;
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
