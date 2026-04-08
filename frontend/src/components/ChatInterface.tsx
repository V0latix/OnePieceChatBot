"use client";

import { FormEvent, useRef, useState } from "react";

import { askQuestionStream, ConversationMessage, SourceCitation } from "../lib/api";
import LoadingIndicator from "./LoadingIndicator";
import MessageBubble from "./MessageBubble";

interface Message {
  role: "user" | "assistant";
  content: string;
  sources?: SourceCitation[];
  confidence?: number;
  entities?: string[];
  streaming?: boolean;
}

interface ChatInterfaceProps {
  spoilerLimitArc?: string;
  onPrimaryEntityChange?: (entityName: string | null) => void;
}

export default function ChatInterface({ spoilerLimitArc, onPrimaryEntityChange }: ChatInterfaceProps) {
  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(false);
  // Ref pour accumuler les tokens sans re-render a chaque caractere
  const streamingIndexRef = useRef<number | null>(null);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!question.trim() || loading) {
      return;
    }

    const userMessage: Message = { role: "user", content: question.trim() };
    // Capture l'historique avant d'ajouter le nouveau message (max 6 = 3 echanges)
    const history: ConversationMessage[] = messages
      .filter((m) => !m.streaming && m.content.trim())
      .slice(-6)
      .map((m) => ({ role: m.role, content: m.content }));

    setMessages((current) => [...current, userMessage]);
    setQuestion("");
    setLoading(true);

    // Ajouter un message assistant vide qui sera rempli par le stream
    const assistantMessage: Message = { role: "assistant", content: "", streaming: true };
    setMessages((current) => {
      streamingIndexRef.current = current.length;
      return [...current, assistantMessage];
    });

    try {
      await askQuestionStream(
        userMessage.content,
        {
          onMetadata: ({ sources, entities, confidence }) => {
            setMessages((current) => {
              const idx = streamingIndexRef.current;
              if (idx === null) return current;
              const updated = [...current];
              updated[idx] = { ...updated[idx], sources, entities, confidence };
              return updated;
            });
            onPrimaryEntityChange?.(entities[0] ?? null);
          },
          onToken: (text) => {
            setMessages((current) => {
              const idx = streamingIndexRef.current;
              if (idx === null) return current;
              const updated = [...current];
              updated[idx] = { ...updated[idx], content: updated[idx].content + text };
              return updated;
            });
          },
          onDone: () => {
            setMessages((current) => {
              const idx = streamingIndexRef.current;
              if (idx === null) return current;
              const updated = [...current];
              updated[idx] = { ...updated[idx], streaming: false };
              return updated;
            });
            streamingIndexRef.current = null;
            setLoading(false);
          },
          onError: (err) => {
            setMessages((current) => {
              const idx = streamingIndexRef.current;
              if (idx === null) return current;
              const updated = [...current];
              updated[idx] = {
                ...updated[idx],
                content: `Erreur streaming: ${err.message}`,
                streaming: false,
              };
              return updated;
            });
            streamingIndexRef.current = null;
            setLoading(false);
          },
        },
        spoilerLimitArc,
        history,
      );
    } catch (err) {
      setMessages((current) => {
        const idx = streamingIndexRef.current;
        const errorContent = "Erreur API. Verifie que le backend FastAPI est demarre sur http://localhost:8000.";
        if (idx !== null) {
          const updated = [...current];
          updated[idx] = { ...updated[idx], content: errorContent, streaming: false };
          return updated;
        }
        return [...current, { role: "assistant", content: errorContent }];
      });
      streamingIndexRef.current = null;
      onPrimaryEntityChange?.(null);
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
          <div key={`${message.role}-${index}`}>
            <MessageBubble
              role={message.role}
              content={message.content}
              sources={message.sources}
              confidence={message.confidence}
              streaming={message.streaming}
            />
          </div>
        ))}
        {loading && streamingIndexRef.current === null ? (
          <LoadingIndicator label="Recherche du contexte en cours..." />
        ) : null}
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
