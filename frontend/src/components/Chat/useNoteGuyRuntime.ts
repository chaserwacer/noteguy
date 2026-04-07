/**
 * Custom assistant-ui runtime adapter that connects to the NoteGuy
 * /api/chat/stream SSE endpoint, powered by LightRAG.
 */

import { useLocalRuntime, type ChatModelAdapter } from "@assistant-ui/react";
import { useNoteStore } from "@/store/useNoteStore";
import { useRef, useMemo, useCallback } from "react";

export interface SourceNote {
  note_id: string;
  note_title: string;
  folder_path: string;
}

export type SourceNotesMap = Map<string, SourceNote[]>;

export function useNoteGuyRuntime() {
  const sourceNotesRef = useRef<SourceNotesMap>(new Map());
  const versionRef = useRef(0);
  const listenersRef = useRef<Set<() => void>>(new Set());

  const subscribe = useCallback((cb: () => void) => {
    listenersRef.current.add(cb);
    return () => {
      listenersRef.current.delete(cb);
    };
  }, []);

  const setSources = useCallback((msgId: string, notes: SourceNote[]) => {
    sourceNotesRef.current.set(msgId, notes);
    versionRef.current++;
    listenersRef.current.forEach((cb) => cb());
  }, []);

  const getSources = useCallback((msgId: string) => {
    return sourceNotesRef.current.get(msgId) ?? [];
  }, []);

  const adapter: ChatModelAdapter = useMemo(
    () => ({
      async *run({ messages, abortSignal }) {
        const activeFolderId = useNoteStore.getState().activeFolderId;

        // Build conversation history from prior messages
        const conversationHistory = messages.slice(0, -1).map((msg) => ({
          role: msg.role,
          content:
            msg.content
              ?.filter(
                (part): part is { type: "text"; text: string } =>
                  part.type === "text",
              )
              .map((part) => part.text)
              .join("") ?? "",
        }));

        const lastMessage = messages[messages.length - 1];
        const userMessage =
          lastMessage.content
            ?.filter(
              (part): part is { type: "text"; text: string } =>
                part.type === "text",
            )
            .map((part) => part.text)
            .join("") ?? "";

        // Get folder scope path if a folder is active
        let folderScope: string | undefined;
        if (activeFolderId) {
          const folder = useNoteStore
            .getState()
            .folders.find((f) => f.id === activeFolderId);
          folderScope = folder?.path;
        }

        const response = await fetch("/api/chat/stream", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            message: userMessage,
            conversation_history: conversationHistory,
            folder_scope: folderScope,
          }),
          signal: abortSignal,
        });

        if (!response.ok) {
          throw new Error(
            `Chat stream error: ${response.status} ${response.statusText}`,
          );
        }

        const reader = response.body!.getReader();
        const decoder = new TextDecoder();
        let accumulatedText = "";
        let buffer = "";
        let sourceNotes: SourceNote[] = [];

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });

          const lines = buffer.split("\n");
          buffer = lines.pop() ?? "";

          for (const line of lines) {
            if (!line.startsWith("data: ")) continue;
            const jsonStr = line.slice(6);

            try {
              const event = JSON.parse(jsonStr);

              if (event.type === "text_delta") {
                accumulatedText += event.delta;
                yield {
                  content: [{ type: "text" as const, text: accumulatedText }],
                };
              } else if (event.type === "source_notes") {
                sourceNotes = event.notes;
              }
            } catch {
              // Skip malformed JSON lines
            }
          }
        }

        // Store source notes for this message
        const msgId = `assistant-${messages.length}`;
        if (sourceNotes.length > 0) {
          setSources(msgId, sourceNotes);
        }

        yield {
          content: [{ type: "text" as const, text: accumulatedText }],
          metadata: {
            custom: {
              sourceMessageId: msgId,
              sourceNotes,
            },
          },
        };
      },
    }),
    [setSources],
  );

  const runtime = useLocalRuntime(adapter);

  return { runtime, getSources, subscribe, sourceNotesRef };
}
