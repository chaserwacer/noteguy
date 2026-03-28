import { useState, useRef, useEffect } from "react";
import { sendChatMessage } from "@/api/client";
import { useNoteStore } from "@/store/useNoteStore";

interface Message {
  role: "user" | "assistant";
  content: string;
}

export default function Chat() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const activeFolderId = useNoteStore((s) => s.activeFolderId);

  useEffect(() => {
    scrollRef.current?.scrollTo(0, scrollRef.current.scrollHeight);
  }, [messages]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = input.trim();
    if (!trimmed || isLoading) return;

    const userMessage: Message = { role: "user", content: trimmed };
    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setIsLoading(true);

    try {
      const response = await sendChatMessage(
        trimmed,
        activeFolderId ?? undefined,
      );
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: response.answer },
      ]);
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: "Sorry, something went wrong. Please try again.",
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-full border-l border-vault-border bg-vault-surface">
      {/* Header */}
      <div className="px-4 py-3 border-b border-vault-border">
        <h2 className="text-sm font-semibold text-vault-accent">
          AI Assistant
        </h2>
        <p className="text-xs text-vault-muted mt-0.5">
          Ask questions about your notes
        </p>
      </div>

      {/* Messages */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto p-4 space-y-3">
        {messages.length === 0 && (
          <p className="text-sm text-vault-muted text-center mt-8">
            Ask a question and the assistant will search your notes for an
            answer.
          </p>
        )}
        {messages.map((msg, i) => (
          <div
            key={i}
            className={`text-sm rounded-lg px-3 py-2 max-w-[90%] ${
              msg.role === "user"
                ? "ml-auto bg-vault-accent/20 text-vault-text"
                : "mr-auto bg-vault-border/40 text-vault-text"
            }`}
          >
            {msg.content}
          </div>
        ))}
        {isLoading && (
          <div className="text-sm text-vault-muted animate-pulse">
            Thinking...
          </div>
        )}
      </div>

      {/* Input */}
      <form
        onSubmit={handleSubmit}
        className="flex gap-2 p-3 border-t border-vault-border"
      >
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask about your notes..."
          className="flex-1 bg-vault-bg border border-vault-border rounded-lg px-3 py-2 text-sm text-vault-text placeholder:text-vault-muted focus:outline-none focus:border-vault-accent"
        />
        <button
          type="submit"
          disabled={isLoading || !input.trim()}
          className="px-4 py-2 rounded-lg bg-vault-accent text-vault-bg text-sm font-medium hover:bg-vault-accent-hover disabled:opacity-40 transition-colors"
        >
          Send
        </button>
      </form>
    </div>
  );
}
