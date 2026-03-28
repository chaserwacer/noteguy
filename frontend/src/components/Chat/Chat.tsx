import { useRef, useCallback, type FC } from "react";
import {
  AssistantRuntimeProvider,
  ThreadPrimitive,
  ComposerPrimitive,
  MessagePrimitive,
  useMessage,
} from "@assistant-ui/react";
import { useNoteStore } from "@/store/useNoteStore";
import { useNoteGuyRuntime, type SourceNote } from "./useNoteGuyRuntime";

// ── Source pills shown below assistant messages ──────────────────────────

const SourcePills: FC = () => {
  const message = useMessage();
  const sourceNotes: SourceNote[] =
    (message as any).metadata?.custom?.sourceNotes ?? [];

  const setActiveNote = useNoteStore((s) => s.setActiveNote);

  if (sourceNotes.length === 0) return null;

  return (
    <div className="flex flex-wrap gap-1.5 mt-2">
      {sourceNotes.map((src) => (
        <button
          key={src.note_id}
          onClick={() => setActiveNote(src.note_id)}
          className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-medium bg-vault-accent-subtle text-vault-accent hover:bg-vault-accent/20 transition-colors cursor-pointer"
          title={`Open ${src.note_title}`}
        >
          <svg
            className="w-3 h-3 shrink-0"
            viewBox="0 0 16 16"
            fill="currentColor"
          >
            <path d="M4 1.5A1.5 1.5 0 015.5 0h5.586a.5.5 0 01.353.146l2.415 2.415a.5.5 0 01.146.354V14.5a1.5 1.5 0 01-1.5 1.5h-7A1.5 1.5 0 014 14.5v-13z" />
          </svg>
          {src.note_title}
        </button>
      ))}
    </div>
  );
};

// ── Folder scope chip ────────────────────────────────────────────────────

const FolderScopeChip: FC = () => {
  const activeFolderId = useNoteStore((s) => s.activeFolderId);
  const folders = useNoteStore((s) => s.folders);
  const setActiveFolder = useNoteStore((s) => s.setActiveFolder);

  if (!activeFolderId) return null;

  const folder = folders.find((f) => f.id === activeFolderId);
  if (!folder) return null;

  return (
    <div className="flex items-center gap-2 px-3 py-1.5 mx-3 mt-2 rounded-md bg-vault-accent-subtle text-vault-accent text-xs font-medium">
      <span className="truncate">Searching in: {folder.name}</span>
      <button
        onClick={() => setActiveFolder(null)}
        className="ml-auto shrink-0 hover:text-vault-text transition-colors"
        title="Clear folder scope"
      >
        <svg className="w-3 h-3" viewBox="0 0 16 16" fill="currentColor">
          <path d="M3.72 3.72a.75.75 0 011.06 0L8 6.94l3.22-3.22a.75.75 0 111.06 1.06L9.06 8l3.22 3.22a.75.75 0 11-1.06 1.06L8 9.06l-3.22 3.22a.75.75 0 01-1.06-1.06L6.94 8 3.72 4.78a.75.75 0 010-1.06z" />
        </svg>
      </button>
    </div>
  );
};

// ── File upload button ───────────────────────────────────────────────────

const AttachButton: FC = () => {
  const inputRef = useRef<HTMLInputElement>(null);
  const activeFolderId = useNoteStore((s) => s.activeFolderId);
  const load = useNoteStore((s) => s.load);

  const handleUpload = useCallback(
    async (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (!file) return;

      const formData = new FormData();
      formData.append("file", file);
      if (activeFolderId) formData.append("folder_id", activeFolderId);

      try {
        const res = await fetch("/api/ingest/upload", {
          method: "POST",
          body: formData,
        });
        if (res.ok) {
          await load();
        }
      } catch {
        // Silently fail for upload errors
      }
      if (inputRef.current) inputRef.current.value = "";
    },
    [activeFolderId, load],
  );

  return (
    <>
      <input
        ref={inputRef}
        type="file"
        accept=".md,.docx"
        className="hidden"
        onChange={handleUpload}
      />
      <button
        type="button"
        onClick={() => inputRef.current?.click()}
        className="p-1.5 rounded-md text-vault-muted hover:text-vault-accent hover:bg-vault-accent-subtle transition-colors"
        title="Upload file (.md, .docx)"
      >
        <svg className="w-4 h-4" viewBox="0 0 16 16" fill="currentColor">
          <path d="M7.646 1.146a.5.5 0 01.708 0l3 3a.5.5 0 01-.708.708L8.5 2.707V10.5a.5.5 0 01-1 0V2.707L5.354 4.854a.5.5 0 11-.708-.708l3-3z" />
          <path d="M.5 9.9a.5.5 0 01.5.5v2.6A1.5 1.5 0 002.5 14.5h11a1.5 1.5 0 001.5-1.5v-2.6a.5.5 0 011 0V13a2.5 2.5 0 01-2.5 2.5h-11A2.5 2.5 0 010 13v-2.6a.5.5 0 01.5-.5z" />
        </svg>
      </button>
    </>
  );
};

// ── Expand / Collapse icons ──────────────────────────────────────────────

function ExpandIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M4 10L2 12V4L4 6" />
      <path d="M12 10L14 12V4L12 6" />
      <path d="M2 2H14M2 14H14" />
    </svg>
  );
}

function CollapseIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M5 4L8 2L11 4" />
      <path d="M5 12L8 14L11 12" />
    </svg>
  );
}

function MinimizeIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round">
      <path d="M3 8H13" />
    </svg>
  );
}

// ── Chat modal content ──────────────────────────────────────────────────

interface ChatContentProps {
  isExpanded: boolean;
  onExpand: () => void;
  onCollapse: () => void;
  onClose: () => void;
}

function ChatContent({ isExpanded, onExpand, onCollapse, onClose }: ChatContentProps) {
  const { runtime } = useNoteGuyRuntime();

  return (
    <AssistantRuntimeProvider runtime={runtime}>
      <div className="flex flex-col h-full">
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-2.5 border-b border-vault-border shrink-0">
          <h2 className="text-[13px] font-medium text-vault-text-secondary">
            AI Assistant
          </h2>
          <div className="flex items-center gap-1">
            <button
              onClick={isExpanded ? onCollapse : onExpand}
              className="p-1 rounded-md text-vault-muted hover:text-vault-text hover:bg-vault-surface-hover transition-colors"
              title={isExpanded ? "Collapse" : "Expand"}
            >
              {isExpanded ? <CollapseIcon /> : <ExpandIcon />}
            </button>
            <button
              onClick={onClose}
              className="p-1 rounded-md text-vault-muted hover:text-vault-text hover:bg-vault-surface-hover transition-colors"
              title="Close"
            >
              <MinimizeIcon />
            </button>
          </div>
        </div>

        <FolderScopeChip />

        {/* Thread */}
        <ThreadPrimitive.Root className="flex-1 flex flex-col min-h-0">
          <ThreadPrimitive.Viewport className="flex-1 overflow-y-auto p-4 space-y-3">
            <ThreadPrimitive.Empty>
              <p className="text-sm text-vault-muted text-center mt-6">
                Ask a question about your notes
              </p>
            </ThreadPrimitive.Empty>
            <ThreadPrimitive.Messages
              components={{ UserMessage, AssistantMessage }}
            />
          </ThreadPrimitive.Viewport>

          {/* Composer */}
          <div className="border-t border-vault-border p-3 shrink-0">
            <ComposerPrimitive.Root className="flex items-end gap-2">
              <AttachButton />
              <ComposerPrimitive.Input
                placeholder="Ask about your notes..."
                className="flex-1 bg-vault-bg border border-vault-border rounded-lg px-3 py-2 text-sm text-vault-text placeholder:text-vault-muted focus:outline-none focus:border-vault-accent resize-none max-h-32"
                autoFocus
              />
              <ComposerPrimitive.Send className="px-3.5 py-2 rounded-lg bg-vault-accent text-vault-bg text-sm font-medium hover:bg-vault-accent-hover disabled:opacity-30 transition-colors">
                Send
              </ComposerPrimitive.Send>
            </ComposerPrimitive.Root>
          </div>
        </ThreadPrimitive.Root>
      </div>
    </AssistantRuntimeProvider>
  );
}

// ── Main Chat export ─────────────────────────────────────────────────────

export default function Chat({
  isOpen,
  isExpanded,
  onExpand,
  onCollapse,
  onClose,
}: {
  isOpen: boolean;
  isExpanded: boolean;
  onExpand: () => void;
  onCollapse: () => void;
  onClose: () => void;
}) {
  if (!isOpen) return null;

  // Full-screen expanded mode
  if (isExpanded) {
    return (
      <div className="fixed inset-0 z-50 bg-vault-bg/80 backdrop-blur-sm animate-fade-in">
        <div className="absolute inset-4 bg-vault-surface border border-vault-border rounded-xl shadow-modal-full overflow-hidden flex flex-col">
          <ChatContent
            isExpanded={isExpanded}
            onExpand={onExpand}
            onCollapse={onCollapse}
            onClose={onClose}
          />
        </div>
      </div>
    );
  }

  // Bottom modal (collapsed)
  return (
    <div className="fixed bottom-0 right-0 z-40 w-full max-w-lg animate-slide-up"
      style={{ maxHeight: "60vh" }}
    >
      <div className="mx-3 mb-3 bg-vault-surface border border-vault-border rounded-xl shadow-modal overflow-hidden flex flex-col"
        style={{ height: "min(56vh, 560px)" }}
      >
        <ChatContent
          isExpanded={isExpanded}
          onExpand={onExpand}
          onCollapse={onCollapse}
          onClose={onClose}
        />
      </div>
    </div>
  );
}

// ── Message components ───────────────────────────────────────────────────

const UserMessage: FC = () => {
  return (
    <MessagePrimitive.Root className="flex justify-end">
      <div className="text-sm rounded-lg px-3 py-2 max-w-[85%] bg-vault-accent-subtle text-vault-text">
        <MessagePrimitive.Content />
      </div>
    </MessagePrimitive.Root>
  );
};

const AssistantMessage: FC = () => {
  return (
    <MessagePrimitive.Root className="flex flex-col items-start">
      <div className="text-sm rounded-lg px-3 py-2 max-w-[85%] bg-vault-surface-hover text-vault-text">
        <MessagePrimitive.Content />
      </div>
      <SourcePills />
    </MessagePrimitive.Root>
  );
};
