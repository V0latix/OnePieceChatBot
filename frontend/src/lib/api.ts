export interface AskResponse {
  answer: string;
  entities: string[];
  confidence: number;
  sources: Array<{
    entity_name: string;
    section: string;
    source_url: string;
    score: number;
  }>;
}

export async function askQuestion(question: string): Promise<AskResponse> {
  const response = await fetch("http://localhost:8000/api/ask", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ question }),
  });

  if (!response.ok) {
    throw new Error(`API error: ${response.status}`);
  }

  return (await response.json()) as AskResponse;
}
