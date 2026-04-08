import { useState, useCallback, useEffect, useRef, useMemo, type FC } from "react";
import "@assistant-ui/react/styles/index.css";
import {
  AssistantRuntimeProvider,
  Thread,
  Composer,
  AssistantMessage as AssistantMessageUI,
  UserMessage as UserMessageUI,
  ThreadWelcome,
  useMessage,
  type ThreadConfig,
} from "@assistant-ui/react";
import type { TextContentPartProps } from "@assistant-ui/react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { useNoteStore } from "@/store/useNoteStore";
import { useNoteGuyRuntime, type SourceNote } from "@/components/Chat/useNoteGuyRuntime";
import KnowledgeGraph from "@/components/KnowledgeGraph";
import {
  fetchAIStatus,
  aiQuery,
  aiAnalyze,
  aiExtract,
  aiExtractNote,
  aiIngestNote,
  aiIngestAll,
  aiIngestDocument,
  aiKGStats,
  type AIStatusResponse,
} from "@/api/client";

// ── Types ──────────────────────────────────────────────────────────────────

type PanelMode = "chat" | "graph" | "query" | "analyze" | "extract" | "ingest";

interface AIPanelProps {
  isOpen: boolean;
  onClose: () => void;
  initialMode?: PanelMode;
}

// ── Chat sub-components ────────────────────────────────────────────────────

const MarkdownText: FC<TextContentPartProps> = ({ text }) => (
  <div className="prose-vault text-sm">
    <ReactMarkdown remarkPlugins={[remarkGfm]}>{text}</ReactMarkdown>
  </div>
);

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
          <svg className="w-3 h-3 shrink-0" viewBox="0 0 16 16" fill="currentColor">
            <path d="M4 1.5A1.5 1.5 0 015.5 0h5.586a.5.5 0 01.353.146l2.415 2.415a.5.5 0 01.146.354V14.5a1.5 1.5 0 01-1.5 1.5h-7A1.5 1.5 0 014 14.5v-13z" />
          </svg>
          {src.note_title}
        </button>
      ))}
    </div>
  );
};

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
        const res = await fetch("/api/ingest/upload", { method: "POST", body: formData });
        if (res.ok) await load();
      } catch { /* silently fail */ }
      if (inputRef.current) inputRef.current.value = "";
    },
    [activeFolderId, load],
  );

  return (
    <>
      <input ref={inputRef} type="file" accept=".md,.txt,.docx,.pdf,.pptx,.xlsx,.jpg,.jpeg,.png" className="hidden" onChange={handleUpload} />
      <button
        type="button"
        onClick={() => inputRef.current?.click()}
        className="aui-composer-attach flex h-9 w-9 items-center justify-center rounded-lg bg-transparent text-vault-muted hover:text-vault-text hover:bg-vault-accent-subtle transition-colors"
        title="Upload file"
      >
        <svg className="w-4 h-4" viewBox="0 0 16 16" fill="currentColor">
          <path d="M7.646 1.146a.5.5 0 01.708 0l3 3a.5.5 0 01-.708.708L8.5 2.707V10.5a.5.5 0 01-1 0V2.707L5.354 4.854a.5.5 0 11-.708-.708l3-3z" />
          <path d="M.5 9.9a.5.5 0 01.5.5v2.6A1.5 1.5 0 002.5 14.5h11a1.5 1.5 0 001.5-1.5v-2.6a.5.5 0 011 0V13a2.5 2.5 0 01-2.5 2.5h-11A2.5 2.5 0 010 13v-2.6a.5.5 0 01.5-.5z" />
        </svg>
      </button>
    </>
  );
};

// ── Spinner ────────────────────────────────────────────────────────────────

const Spinner: FC = () => (
  <svg className="animate-spin h-4 w-4 text-vault-muted" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <circle cx="12" cy="12" r="10" opacity="0.25" />
    <path d="M12 2a10 10 0 019.95 9" opacity="0.75" />
  </svg>
);

// ── Mode definitions ───────────────────────────────────────────────────────

interface ModeInfo {
  id: PanelMode;
  label: string;
  description: string;
  icon: (active: boolean) => React.ReactNode;
}

const MODES: ModeInfo[] = [
  {
    id: "chat",
    label: "Chat",
    description: "Conversational Q&A powered by graph-augmented retrieval",
    icon: (a) => (
      <svg className={`w-4 h-4 ${a ? "text-vault-accent" : "text-vault-muted"}`} viewBox="0 0 16 16" fill="currentColor">
        <path d="M2 3h12v8H5l-3 3V3z" />
      </svg>
    ),
  },
  {
    id: "graph",
    label: "Knowledge Graph",
    description: "Interactive entity-relationship graph visualization",
    icon: (a) => (
      <svg className={`w-4 h-4 ${a ? "text-vault-accent" : "text-vault-muted"}`} viewBox="0 0 16 16" fill="currentColor">
        <circle cx="4" cy="4" r="2" />
        <circle cx="12" cy="4" r="2" />
        <circle cx="8" cy="12" r="2" />
        <path d="M5.5 5.5l2 4.5M10.5 5.5l-2 4.5M6 4h4" opacity="0.5" />
      </svg>
    ),
  },
  {
    id: "query",
    label: "Query",
    description: "Hybrid knowledge graph search",
    icon: (a) => (
      <svg className={`w-4 h-4 ${a ? "text-vault-accent" : "text-vault-muted"}`} viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
        <circle cx="7" cy="7" r="5" />
        <path d="M10.5 10.5L14 14" />
      </svg>
    ),
  },
  {
    id: "analyze",
    label: "Analyze",
    description: "Cross-document analysis using global knowledge graph traversal",
    icon: (a) => (
      <svg className={`w-4 h-4 ${a ? "text-vault-accent" : "text-vault-muted"}`} viewBox="0 0 16 16" fill="currentColor">
        <path d="M1 11a1 1 0 011-1h2a1 1 0 011 1v3a1 1 0 01-1 1H2a1 1 0 01-1-1v-3zm5-4a1 1 0 011-1h2a1 1 0 011 1v7a1 1 0 01-1 1H7a1 1 0 01-1-1V7zm5-5a1 1 0 011-1h2a1 1 0 011 1v12a1 1 0 01-1 1h-2a1 1 0 01-1-1V2z" />
      </svg>
    ),
  },
  {
    id: "extract",
    label: "Extract",
    description: "Extract entities and relationships from your notes",
    icon: (a) => (
      <svg className={`w-4 h-4 ${a ? "text-vault-accent" : "text-vault-muted"}`} viewBox="0 0 16 16" fill="currentColor">
        <path d="M3 2a1 1 0 011-1h8a1 1 0 011 1v12a1 1 0 01-1 1H4a1 1 0 01-1-1V2zm2 1v1h6V3H5zm0 3v1h6V6H5zm0 3v1h4V9H5z" />
      </svg>
    ),
  },
  {
    id: "ingest",
    label: "Ingest",
    description: "Index notes and documents into the knowledge graph",
    icon: (a) => (
      <svg className={`w-4 h-4 ${a ? "text-vault-accent" : "text-vault-muted"}`} viewBox="0 0 16 16" fill="currentColor">
        <path d="M7.646 1.146a.5.5 0 01.708 0l3 3a.5.5 0 01-.708.708L8.5 2.707V10.5a.5.5 0 01-1 0V2.707L5.354 4.854a.5.5 0 11-.708-.708l3-3z" />
        <path d="M.5 9.9a.5.5 0 01.5.5v2.6A1.5 1.5 0 002.5 14.5h11a1.5 1.5 0 001.5-1.5v-2.6a.5.5 0 011 0V13a2.5 2.5 0 01-2.5 2.5h-11A2.5 2.5 0 010 13v-2.6a.5.5 0 01.5-.5z" />
      </svg>
    ),
  },
];

// ── Main component ─────────────────────────────────────────────────────────

export default function AIPanel({ isOpen, onClose, initialMode = "chat" }: AIPanelProps) {
  const [activeMode, setActiveMode] = useState<PanelMode>(initialMode);
  const [status, setStatus] = useState<AIStatusResponse | null>(null);
  const [loaded, setLoaded] = useState(false);
  const [input, setInput] = useState("");
  const [result, setResult] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [kgStats, setKgStats] = useState<{ entities: number; relations: number } | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const activeNoteId = useNoteStore((s) => s.activeNoteId);
  const activeFolderId = useNoteStore((s) => s.activeFolderId);
  const load = useNoteStore((s) => s.load);

  // Chat runtime (always initialized so chat state persists across tab switches)
  const { runtime } = useNoteGuyRuntime();

  const threadConfig = useMemo<ThreadConfig>(
    () => ({
      assistantAvatar: { fallback: "NG", alt: "Note Guy assistant" },
      welcome: {
        message: "Hi! I'm Note Guy, your note assistant.",
        suggestions: [
          { text: "Summarize the open note", prompt: "Summarize the active note succinctly." },
          { text: "Find related notes", prompt: "Find notes that are related to this topic." },
          { text: "Draft an outline", prompt: "Draft a concise outline I can expand on." },
        ],
      },
      assistantMessage: {
        allowCopy: true,
        allowReload: true,
        components: { Text: MarkdownText, Footer: SourcePills },
      },
      composer: { allowAttachments: false },
      strings: {
        composer: { input: { placeholder: "Ask Note Guy about your notes..." } },
        assistantMessage: {
          copy: { tooltip: "Copy answer" },
          reload: { tooltip: "Regenerate" },
        },
      },
    }),
    [],
  );

  // Update mode when initialMode prop changes
  useEffect(() => {
    if (isOpen) setActiveMode(initialMode);
  }, [initialMode, isOpen]);

  // Load status on first open
  useEffect(() => {
    if (!isOpen || loaded) return;
    (async () => {
      try {
        const [statusData, stats] = await Promise.all([
          fetchAIStatus(),
          aiKGStats().catch(() => ({ entities: 0, relations: 0 })),
        ]);
        setStatus(statusData);
        setKgStats(stats);
        setLoaded(true);
      } catch {
        setError("Failed to load AI status");
      }
    })();
  }, [isOpen, loaded]);

  // ── Tool action handlers ──────────────────────────────────────────────

  const handleQuery = useCallback(async () => {
    if (!input.trim()) { setError("Enter a question"); return; }
    setLoading(true); setError(null); setResult(null);
    try {
      const res = await aiQuery(input.trim());
      setResult(res.answer);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Query failed");
    } finally { setLoading(false); }
  }, [input]);

  const handleAnalyze = useCallback(async () => {
    if (!input.trim()) { setError("Enter a question for analysis"); return; }
    setLoading(true); setError(null); setResult(null);
    try {
      const res = await aiAnalyze(input.trim());
      setResult(res.answer);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Analysis failed");
    } finally { setLoading(false); }
  }, [input]);

  const handleExtract = useCallback(async () => {
    setLoading(true); setError(null); setResult(null);
    try {
      let res;
      if (activeNoteId) {
        res = await aiExtractNote(activeNoteId);
      } else if (input.trim()) {
        res = await aiExtract(input.trim());
      } else {
        setError("Enter a query or select a note to extract entities from");
        setLoading(false); return;
      }
      setResult(JSON.stringify(res, null, 2));
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Extraction failed");
    } finally { setLoading(false); }
  }, [input, activeNoteId]);

  const handleIngestNote = useCallback(async () => {
    if (!activeNoteId) { setError("Select a note to ingest"); return; }
    setLoading(true); setError(null); setResult(null);
    try {
      const res = await aiIngestNote(activeNoteId);
      setResult(JSON.stringify(res, null, 2));
      const stats = await aiKGStats().catch(() => null);
      if (stats) setKgStats(stats);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Ingestion failed");
    } finally { setLoading(false); }
  }, [activeNoteId]);

  const handleIngestAll = useCallback(async () => {
    setLoading(true); setError(null); setResult(null);
    try {
      const res = await aiIngestAll();
      setResult(JSON.stringify(res, null, 2));
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Vault re-index failed");
    } finally { setLoading(false); }
  }, []);

  const handleFileUpload = useCallback(
    async (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (!file) return;
      setLoading(true); setError(null); setResult(null);
      try {
        const res = await aiIngestDocument(file as unknown as File, activeFolderId ?? undefined);
        setResult(JSON.stringify(res, null, 2));
        await load();
        const stats = await aiKGStats().catch(() => null);
        if (stats) setKgStats(stats);
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : "Upload failed");
      } finally {
        setLoading(false);
        if (fileInputRef.current) fileInputRef.current.value = "";
      }
    },
    [activeFolderId, load],
  );

  const handleKGStats = useCallback(async () => {
    setLoading(true); setError(null);
    try {
      const stats = await aiKGStats();
      setKgStats(stats);
      setResult(`Knowledge Graph: ${stats.entities} entities, ${stats.relations} relationships`);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load KG stats");
    } finally { setLoading(false); }
  }, []);

  if (!isOpen) return null;

  const activeModeInfo = MODES.find((m) => m.id === activeMode)!;

  // ── Tool mode content (query, analyze, extract, ingest) ───────────────

  function renderToolContent() {
    return (
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Mode description */}
        <div className="px-5 py-3 border-b border-vault-border/30">
          <p className="text-xs text-vault-text-secondary">{activeModeInfo.description}</p>
        </div>

        {/* Input area */}
        <div className="px-5 py-3 border-b border-vault-border/30">
          {activeMode === "ingest" ? (
            <div className="flex flex-wrap gap-2">
              <button onClick={handleIngestNote} disabled={loading || !activeNoteId}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium bg-vault-accent-subtle text-vault-accent hover:bg-vault-accent/20 disabled:opacity-50 transition-colors">
                Index Active Note
              </button>
              <button onClick={handleIngestAll} disabled={loading}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium bg-vault-accent-subtle text-vault-accent hover:bg-vault-accent/20 disabled:opacity-50 transition-colors">
                Re-index Entire Vault
              </button>
              <button onClick={() => fileInputRef.current?.click()} disabled={loading}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium bg-vault-accent-subtle text-vault-accent hover:bg-vault-accent/20 disabled:opacity-50 transition-colors">
                Upload Document
              </button>
              <input ref={fileInputRef} type="file"
                accept=".md,.txt,.docx,.pdf,.pptx,.xlsx,.jpg,.jpeg,.png"
                className="hidden" onChange={handleFileUpload} />
            </div>
          ) : (
            <div className="space-y-2">
              <div className="flex gap-2">
                <input
                  type="text"
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  placeholder={
                    activeMode === "extract" ? "Entity or concept to extract (or select a note)..."
                    : activeMode === "analyze" ? "Question for cross-document analysis..."
                    : "Search your knowledge graph..."
                  }
                  className="flex-1 px-3 py-2 rounded-md bg-vault-bg border border-vault-border text-sm text-vault-text placeholder-vault-muted focus:outline-none focus:ring-1 focus:ring-vault-accent"
                  onKeyDown={(e) => {
                    if (e.key === "Enter") {
                      if (activeMode === "query") handleQuery();
                      else if (activeMode === "analyze") handleAnalyze();
                      else if (activeMode === "extract") handleExtract();
                    }
                  }}
                />
              </div>
              <div className="flex flex-wrap gap-2">
                <button
                  onClick={activeMode === "query" ? handleQuery : activeMode === "analyze" ? handleAnalyze : handleExtract}
                  disabled={loading}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium bg-vault-accent text-white hover:bg-vault-accent/80 disabled:opacity-50 transition-colors"
                >
                  {loading ? <Spinner /> : null}
                  {activeMode === "query" ? "Query" : activeMode === "analyze" ? "Analyze" : "Extract"}
                </button>
                {activeMode === "extract" && activeNoteId && (
                  <button onClick={handleExtract} disabled={loading}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium bg-vault-accent-subtle text-vault-accent hover:bg-vault-accent/20 disabled:opacity-50 transition-colors">
                    Extract from Active Note
                  </button>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Result / Error */}
        <div className="flex-1 overflow-y-auto px-5 py-3">
          {loading && !result && (
            <div className="flex items-center gap-2 text-vault-muted text-sm">
              <Spinner /> Processing...
            </div>
          )}
          {error && (
            <div className="text-red-400 text-sm bg-red-400/10 rounded-md px-3 py-2">{error}</div>
          )}
          {result && (
            <div className="space-y-2">
              {result.startsWith("{") || result.startsWith("[") ? (
                <pre className="text-xs text-vault-text-secondary whitespace-pre-wrap font-mono bg-vault-bg rounded-md px-4 py-3 overflow-x-auto leading-relaxed">
                  {result}
                </pre>
              ) : (
                <div className="prose-vault text-sm text-vault-text-secondary bg-vault-bg rounded-md px-4 py-3 overflow-x-auto leading-relaxed">
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>{result}</ReactMarkdown>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="fixed inset-0 z-50 bg-vault-bg/80 backdrop-blur-sm animate-fade-in">
      <div className="absolute inset-4 bg-vault-surface border border-vault-border rounded-xl shadow-modal-full overflow-hidden flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-3 border-b border-vault-border/70 bg-gradient-to-r from-vault-surface to-vault-bg/60">
          <div className="space-y-0.5">
            <p className="text-sm font-semibold text-vault-text">NoteGuy AI</p>
            <p className="text-[11px] text-vault-text-secondary">
              {status?.config.llm_model ?? "loading..."}
              {kgStats && (
                <span className="ml-2 text-vault-accent">
                  {kgStats.entities} entities &middot; {kgStats.relations} relations
                </span>
              )}
            </p>
          </div>
          <div className="flex items-center gap-3">
            {status?.config.embedding_model && (
              <div className="flex items-center gap-1.5 px-2 py-1 rounded-md text-[10px] font-medium bg-vault-accent-subtle text-vault-accent">
                <span className="w-1.5 h-1.5 rounded-full bg-vault-accent" />
                {status.config.embedding_model}
              </div>
            )}
            <button
              onClick={onClose}
              className="p-1.5 rounded-md text-vault-muted hover:text-vault-text hover:bg-vault-surface-hover transition-colors"
            >
              <svg className="w-4 h-4" viewBox="0 0 16 16" fill="currentColor">
                <path d="M3.72 3.72a.75.75 0 011.06 0L8 6.94l3.22-3.22a.75.75 0 111.06 1.06L9.06 8l3.22 3.22a.75.75 0 11-1.06 1.06L8 9.06l-3.22 3.22a.75.75 0 01-1.06-1.06L6.94 8 3.72 4.78a.75.75 0 010-1.06z" />
              </svg>
            </button>
          </div>
        </div>

        <div className="flex flex-1 min-h-0">
          {/* Sidebar - mode selector */}
          <div className="w-44 border-r border-vault-border/50 overflow-y-auto py-1 flex flex-col">
            {MODES.map((mode) => (
              <button
                key={mode.id}
                onClick={() => {
                  setActiveMode(mode.id);
                  if (mode.id !== "chat" && mode.id !== "graph") {
                    setResult(null);
                    setError(null);
                  }
                }}
                className={`w-full flex items-center gap-2.5 px-3 py-2 text-left transition-colors ${
                  activeMode === mode.id
                    ? "bg-vault-accent-subtle text-vault-accent"
                    : "text-vault-text-secondary hover:bg-vault-surface-hover hover:text-vault-text"
                }`}
              >
                {mode.icon(activeMode === mode.id)}
                <span className="text-xs font-medium truncate">{mode.label}</span>
              </button>
            ))}

            {/* Stats footer in sidebar */}
            {kgStats && (
              <div className="mt-auto px-3 py-3 border-t border-vault-border/30">
                <div className="grid grid-cols-2 gap-1.5">
                  <div className="text-center">
                    <p className="text-sm font-bold text-vault-accent">{kgStats.entities}</p>
                    <p className="text-[9px] text-vault-muted">entities</p>
                  </div>
                  <div className="text-center">
                    <p className="text-sm font-bold text-vault-accent">{kgStats.relations}</p>
                    <p className="text-[9px] text-vault-muted">relations</p>
                  </div>
                </div>
                <button
                  onClick={handleKGStats}
                  className="w-full mt-2 px-2 py-1 rounded text-[10px] font-medium text-vault-muted hover:text-vault-text hover:bg-vault-surface-hover transition-colors"
                >
                  Refresh Stats
                </button>
              </div>
            )}
          </div>

          {/* Main content area */}
          <AssistantRuntimeProvider runtime={runtime}>
            <div className="flex-1 flex flex-col min-w-0 min-h-0">
              {/* Chat mode */}
              {activeMode === "chat" && (
                <Thread.Root config={threadConfig} className="flex flex-1 flex-col min-h-0">
                  <Thread.Viewport className="aui-thread-viewport px-3 md:px-4">
                    <ThreadWelcome />
                    <Thread.Messages
                      components={{ UserMessage: UserMessageUI, AssistantMessage: AssistantMessageUI }}
                    />
                    <Thread.FollowupSuggestions />
                  </Thread.Viewport>
                  <Thread.ViewportFooter className="aui-thread-viewport-footer border-t border-vault-border bg-vault-bg/60">
                    <Thread.ScrollToBottom />
                    <div className="w-full">
                      <FolderScopeChip />
                      <Composer.Root className="aui-composer-root mt-2">
                        <AttachButton />
                        <Composer.Input />
                        <Composer.Action />
                      </Composer.Root>
                    </div>
                  </Thread.ViewportFooter>
                </Thread.Root>
              )}

              {/* Knowledge Graph mode */}
              {activeMode === "graph" && <KnowledgeGraph />}

              {/* Tool modes (query, analyze, extract, ingest) */}
              {activeMode !== "chat" && activeMode !== "graph" && renderToolContent()}
            </div>
          </AssistantRuntimeProvider>
        </div>
      </div>
    </div>
  );
}
