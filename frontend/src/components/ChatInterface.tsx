"use client";

import { FormEvent, useRef, useState } from "react";

import { askQuestionStream, ConversationMessage, SourceCitation } from "../lib/api";
import { Button } from "./ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";
import { Input } from "./ui/input";
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
  onPrimaryEntityChange?: (entityName: string | null) => void;
}

export default function ChatInterface({ onPrimaryEntityChange }: ChatInterfaceProps) {
  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(false);
  // streamingStarted passe a true des que le premier token arrive (utilise dans le JSX)
  const [streamingStarted, setStreamingStarted] = useState(false);
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
    setStreamingStarted(false);
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
            setStreamingStarted(true);
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
            setStreamingStarted(false);
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
            setStreamingStarted(false);
            setLoading(false);
          },
        },
        history,
      );
    } catch (err) {
      setMessages((current) => {
        const idx = streamingIndexRef.current;
        const errorContent =
          "Backend injoignable. Lance les deux commandes affichees en bas de page (uvicorn, puis le tunnel ngrok).";
        if (idx !== null) {
          const updated = [...current];
          updated[idx] = { ...updated[idx], content: errorContent, streaming: false };
          return updated;
        }
        return [...current, { role: "assistant", content: errorContent }];
      });
      streamingIndexRef.current = null;
      setStreamingStarted(false);
      onPrimaryEntityChange?.(null);
      setLoading(false);
    }
  }

  return (
    <Card className="fade-in flex flex-col">
      <CardHeader>
        <CardTitle>Log Pose Chat</CardTitle>
      </CardHeader>
      <CardContent className="flex flex-1 flex-col gap-4">
        <div className="max-h-96 space-y-3 overflow-y-auto pr-1">
          {messages.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              Pose une question sur les personnages, arcs, fruits du demon, ou lieux.
            </p>
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
          {loading && !streamingStarted ? <LoadingIndicator label="Recherche du contexte en cours..." /> : null}
        </div>
        <form onSubmit={onSubmit} className="flex flex-col gap-3 sm:flex-row">
          <Input
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            placeholder="Ex: Quel est le fruit du demon de Trafalgar Law ?"
          />
          <Button type="submit" disabled={loading}>
            Envoyer
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}
