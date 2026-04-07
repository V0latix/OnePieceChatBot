"use client";

import { FormEvent, useState } from "react";

import { askQuestion } from "../lib/api";

interface Message {
  role: "user" | "assistant";
  content: string;
}

export default function ChatInterface() {
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
      const response = await askQuestion(userMessage.content);
      setMessages((current) => [...current, { role: "assistant", content: response.answer }]);
    } catch {
      setMessages((current) => [
        ...current,
        {
          role: "assistant",
          content: "Erreur API. Verifie que le backend FastAPI est demarre sur http://localhost:8000.",
        },
      ]);
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
          <article
            key={`${message.role}-${index}`}
            className={`rounded-xl border px-4 py-3 text-sm leading-relaxed ${
              message.role === "user"
                ? "ml-auto max-w-[85%] border-ember bg-[#2b1f1a]"
                : "mr-auto max-w-[85%] border-gold/40 bg-[#131f33]"
            }`}
          >
            {message.content}
          </article>
        ))}
        {loading ? <p className="text-sm text-gold">Recherche du contexte en cours...</p> : null}
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
    </section>
  );
}
