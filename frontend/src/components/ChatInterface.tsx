"use client";

import { FormEvent, useState } from "react";

import { askQuestion, SourceCitation } from "../lib/api";
import LoadingIndicator from "./LoadingIndicator";
import MessageBubble from "./MessageBubble";

interface Message {
  role: "user" | "assistant";
  content: string;
  sources?: SourceCitation[];
  confidence?: number;
  entities?: string[];
}

interface ChatInterfaceProps {
  spoilerLimitArc?: string;
  onPrimaryEntityChange?: (entityName: string | null) => void;
}

export default function ChatInterface({ spoilerLimitArc, onPrimaryEntityChange }: ChatInterfaceProps) {
  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(false);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!question.trim() || loading) {
      return;
    }

    const userMessage: Message = { role: "user", content: question.trim() };
    setMessages((current) => [...current, userMessage]);
    setQuestion("");
    setLoading(true);

    try {
      const response = await askQuestion(userMessage.content, spoilerLimitArc);
      setMessages((current) => [
        ...current,
        {
          role: "assistant",
          content: response.answer,
          sources: response.sources,
          confidence: response.confidence,
          entities: response.entities,
        },
      ]);
      onPrimaryEntityChange?.(response.entities[0] ?? null);
    } catch {
      setMessages((current) => [
        ...current,
        {
          role: "assistant",
          content: "Erreur API. Verifie que le backend FastAPI est demarre sur http://localhost:8000.",
        },
      ]);
      onPrimaryEntityChange?.(null);
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="card fade-in rounded-2xl p-5 md:p-7">
      <h2 className="mb-4 text-3xl tracking-wide [font-family:var(--font-display)]">Log Pose Chat</h2>
      <div className="mb-4 max-h-96 space-y-3 overflow-y-auto pr-1">
        {messages.length === 0 ? (
          <p className="text-sm text-[#c9bc9f]">Pose une question sur les personnages, arcs, fruits du demon, ou lieux.</p>
        ) : null}
        {messages.map((message, index) => (
          <div
            key={`${message.role}-${index}`}
          >
            <MessageBubble
              role={message.role}
              content={message.content}
              sources={message.sources}
              confidence={message.confidence}
            />
          </div>
        ))}
        {loading ? <LoadingIndicator label="Recherche du contexte en cours..." /> : null}
      </div>
      <form onSubmit={onSubmit} className="flex flex-col gap-3 sm:flex-row">
        <input
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
          placeholder="Ex: Quel est le fruit du demon de Trafalgar Law ?"
          className="w-full rounded-xl border border-gold/30 bg-[#0d1729] px-4 py-3 text-sm text-parchment outline-none transition focus:border-gold"
        />
        <button
          type="submit"
          disabled={loading}
          className="rounded-xl bg-ember px-5 py-3 text-sm font-semibold text-white transition hover:bg-[#ef613a] disabled:opacity-60"
        >
          Envoyer
        </button>
      </form>
      {spoilerLimitArc && spoilerLimitArc !== "Aucun" ? (
        <p className="mt-3 text-xs text-[#bdaa82]">Filtre spoiler actif: {spoilerLimitArc}</p>
      ) : null}
    </section>
  );
}
