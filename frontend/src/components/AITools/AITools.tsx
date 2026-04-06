import { useState, useCallback, useEffect, useRef, type FC } from "react";
import { useNoteStore } from "@/store/useNoteStore";
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
  type AICapability,
  type QueryMode,
} from "@/api/client";

// ── Mode icons ──────────────────────────────────────────────────────────────

const ModeIcon: FC<{ icon: string; active?: boolean }> = ({ icon, active }) => {
  const cls = `w-4 h-4 ${active ? "text-vault-accent" : "text-vault-muted"}`;
  switch (icon) {
    case "chat":
      return (
        <svg className={cls} viewBox="0 0 16 16" fill="currentColor">
          <path d="M2 3h12v8H5l-3 3V3z" />
        </svg>
      );
    case "upload":
      return (
        <svg className={cls} viewBox="0 0 16 16" fill="currentColor">
          <path d="M7.646 1.146a.5.5 0 01.708 0l3 3a.5.5 0 01-.708.708L8.5 2.707V10.5a.5.5 0 01-1 0V2.707L5.354 4.854a.5.5 0 11-.708-.708l3-3z" />
          <path d="M.5 9.9a.5.5 0 01.5.5v2.6A1.5 1.5 0 002.5 14.5h11a1.5 1.5 0 001.5-1.5v-2.6a.5.5 0 011 0V13a2.5 2.5 0 01-2.5 2.5h-11A2.5 2.5 0 010 13v-2.6a.5.5 0 01.5-.5z" />
        </svg>
      );
    case "extract":
      return (
        <svg className={cls} viewBox="0 0 16 16" fill="currentColor">
          <path d="M3 2a1 1 0 011-1h8a1 1 0 011 1v12a1 1 0 01-1 1H4a1 1 0 01-1-1V2zm2 1v1h6V3H5zm0 3v1h6V6H5zm0 3v1h4V9H5z" />
        </svg>
      );
    case "analyze":
      return (
        <svg className={cls} viewBox="0 0 16 16" fill="currentColor">
          <path d="M1 11a1 1 0 011-1h2a1 1 0 011 1v3a1 1 0 01-1 1H2a1 1 0 01-1-1v-3zm5-4a1 1 0 011-1h2a1 1 0 011 1v7a1 1 0 01-1 1H7a1 1 0 01-1-1V7zm5-5a1 1 0 011-1h2a1 1 0 011 1v12a1 1 0 01-1 1h-2a1 1 0 01-1-1V2z" />
        </svg>
      );
    case "graph":
      return (
        <svg className={cls} viewBox="0 0 16 16" fill="currentColor">
          <circle cx="4" cy="4" r="2" />
          <circle cx="12" cy="4" r="2" />
          <circle cx="8" cy="12" r="2" />
          <path d="M5.5 5.5l2 4.5M10.5 5.5l-2 4.5M6 4h4" opacity="0.5" />
        </svg>
      );
    default:
      return (
        <svg className={cls} viewBox="0 0 16 16" fill="currentColor">
          <circle cx="8" cy="8" r="6" />
        </svg>
      );
  }
};

// ── Spinner ─────────────────────────────────────────────────────────────────

const Spinner: FC = () => (
  <svg
    className="animate-spin h-4 w-4 text-vault-muted"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
  >
    <circle cx="12" cy="12" r="10" opacity="0.25" />
    <path d="M12 2a10 10 0 019.95 9" opacity="0.75" />
  </svg>
);

// ── Main component ──────────────────────────────────────────────────────────

interface AIToolsProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function AITools({ isOpen, onClose }: AIToolsProps) {
  const [status, setStatus] = useState<AIStatusResponse | null>(null);
  const [loaded, setLoaded] = useState(false);
  const [activeMode, setActiveMode] = useState<string>("chat");
  const [input, setInput] = useState("");
  const [result, setResult] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [queryMode, setQueryMode] = useState<QueryMode>("hybrid");
  const [kgStats, setKgStats] = useState<{ entities: number; relations: number } | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const activeNoteId = useNoteStore((s) => s.activeNoteId);
  const activeFolderId = useNoteStore((s) => s.activeFolderId);
  const load = useNoteStore((s) => s.load);

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

  const activeCapability = status?.capabilities.find((c) => c.id === activeMode);

  // ── Action handlers ─────────────────────────────────────────────────────

  const handleChat = useCallback(async () => {
    if (!input.trim()) {
      setError("Enter a question");
      return;
    }
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const res = await aiQuery(input.trim(), queryMode);
      setResult(res.answer);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Query failed");
    } finally {
      setLoading(false);
    }
  }, [input, queryMode]);

  const handleAnalyze = useCallback(async () => {
    if (!input.trim()) {
      setError("Enter a question for analysis");
      return;
    }
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const res = await aiAnalyze(input.trim());
      setResult(res.answer);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Analysis failed");
    } finally {
      setLoading(false);
    }
  }, [input]);

  const handleExtract = useCallback(async () => {
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      let res;
      if (activeNoteId) {
        res = await aiExtractNote(activeNoteId);
      } else if (input.trim()) {
        res = await aiExtract(input.trim());
      } else {
        setError("Enter a query or select a note to extract entities from");
        setLoading(false);
        return;
      }
      setResult(JSON.stringify(res, null, 2));
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Extraction failed");
    } finally {
      setLoading(false);
    }
  }, [input, activeNoteId]);

  const handleIngestNote = useCallback(async () => {
    if (!activeNoteId) {
      setError("Select a note to ingest");
      return;
    }
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const res = await aiIngestNote(activeNoteId);
      setResult(JSON.stringify(res, null, 2));
      const stats = await aiKGStats().catch(() => null);
      if (stats) setKgStats(stats);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Ingestion failed");
    } finally {
      setLoading(false);
    }
  }, [activeNoteId]);

  const handleIngestAll = useCallback(async () => {
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const res = await aiIngestAll();
      setResult(JSON.stringify(res, null, 2));
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Vault re-index failed");
    } finally {
      setLoading(false);
    }
  }, []);

  const handleFileUpload = useCallback(
    async (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (!file) return;
      setLoading(true);
      setError(null);
      setResult(null);
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
    setLoading(true);
    setError(null);
    try {
      const stats = await aiKGStats();
      setKgStats(stats);
      setResult(
        `Knowledge Graph: ${stats.entities} entities, ${stats.relations} relationships`,
      );
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load KG stats");
    } finally {
      setLoading(false);
    }
  }, []);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 bg-vault-bg/80 backdrop-blur-sm animate-fade-in">
      <div className="absolute inset-4 bg-vault-surface border border-vault-border rounded-xl shadow-modal-full overflow-hidden flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-3 border-b border-vault-border/70 bg-gradient-to-r from-vault-surface to-vault-bg/60">
          <div className="space-y-0.5">
            <p className="text-sm font-semibold text-vault-text">NoteGuy AI</p>
            <p className="text-[11px] text-vault-text-secondary">
              Powered by LightRAG
              {status?.config.raganything_available && " + RAG-Anything"}
              {" "}
              &middot; {status?.config.llm_model ?? "loading..."}
              {kgStats && (
                <span className="ml-2 text-vault-accent">
                  {kgStats.entities} entities &middot; {kgStats.relations} relations
                </span>
              )}
            </p>
          </div>
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-1.5 px-2 py-1 rounded-md text-[10px] font-medium bg-vault-accent-subtle text-vault-accent">
              <span className="w-1.5 h-1.5 rounded-full bg-vault-accent" />
              {status?.config.embedding_model ?? "..."}
            </div>
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
          {/* Mode selector sidebar */}
          <div className="w-52 border-r border-vault-border/50 overflow-y-auto py-2">
            {(status?.capabilities ?? []).map((cap: AICapability) => (
              <button
                key={cap.id}
                onClick={() => {
                  setActiveMode(cap.id);
                  setResult(null);
                  setError(null);
                }}
                className={`w-full flex items-center gap-3 px-4 py-2.5 text-left transition-colors ${
                  activeMode === cap.id
                    ? "bg-vault-accent-subtle text-vault-accent"
                    : "text-vault-text-secondary hover:bg-vault-surface-hover hover:text-vault-text"
                }`}
              >
                <ModeIcon icon={cap.icon} active={activeMode === cap.id} />
                <div className="min-w-0">
                  <p className="text-xs font-medium truncate">{cap.name}</p>
                  <p className="text-[10px] text-vault-muted truncate">
                    {cap.description.split(" ").slice(0, 4).join(" ")}...
                  </p>
                </div>
              </button>
            ))}
          </div>

          {/* Main content area */}
          <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
            {/* Mode description */}
            <div className="px-5 py-3 border-b border-vault-border/30">
              <p className="text-xs text-vault-text-secondary">
                {activeCapability?.description ?? "Select a mode"}
              </p>
            </div>

            {/* Input area */}
            <div className="px-5 py-3 border-b border-vault-border/30">
              {activeMode === "ingest" ? (
                <div className="flex flex-wrap gap-2">
                  <button
                    onClick={handleIngestNote}
                    disabled={loading || !activeNoteId}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium bg-vault-accent-subtle text-vault-accent hover:bg-vault-accent/20 disabled:opacity-50 transition-colors"
                  >
                    Index Active Note
                  </button>
                  <button
                    onClick={handleIngestAll}
                    disabled={loading}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium bg-vault-accent-subtle text-vault-accent hover:bg-vault-accent/20 disabled:opacity-50 transition-colors"
                  >
                    Re-index Entire Vault
                  </button>
                  <button
                    onClick={() => fileInputRef.current?.click()}
                    disabled={loading}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium bg-vault-accent-subtle text-vault-accent hover:bg-vault-accent/20 disabled:opacity-50 transition-colors"
                  >
                    Upload Document
                  </button>
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept=".md,.txt,.docx,.pdf,.pptx,.xlsx,.jpg,.jpeg,.png"
                    className="hidden"
                    onChange={handleFileUpload}
                  />
                </div>
              ) : activeMode === "knowledge_graph" ? (
                <div className="flex flex-wrap gap-2">
                  <button
                    onClick={handleKGStats}
                    disabled={loading}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium bg-vault-accent-subtle text-vault-accent hover:bg-vault-accent/20 disabled:opacity-50 transition-colors"
                  >
                    Refresh Stats
                  </button>
                </div>
              ) : (
                <div className="space-y-2">
                  <div className="flex gap-2">
                    <input
                      type="text"
                      value={input}
                      onChange={(e) => setInput(e.target.value)}
                      placeholder={
                        activeMode === "extract"
                          ? "Entity or concept to extract (or select a note)..."
                          : activeMode === "analyze"
                            ? "Question for cross-document analysis..."
                            : "Ask about your notes..."
                      }
                      className="flex-1 px-3 py-2 rounded-md bg-vault-bg border border-vault-border text-sm text-vault-text placeholder-vault-muted focus:outline-none focus:ring-1 focus:ring-vault-accent"
                      onKeyDown={(e) => {
                        if (e.key === "Enter") {
                          if (activeMode === "chat") handleChat();
                          else if (activeMode === "analyze") handleAnalyze();
                          else if (activeMode === "extract") handleExtract();
                        }
                      }}
                    />
                    {activeMode === "chat" && (
                      <select
                        value={queryMode}
                        onChange={(e) => setQueryMode(e.target.value as QueryMode)}
                        className="px-2 py-2 rounded-md bg-vault-bg border border-vault-border text-xs text-vault-text focus:outline-none focus:ring-1 focus:ring-vault-accent"
                      >
                        <option value="hybrid">Hybrid</option>
                        <option value="local">Local</option>
                        <option value="global">Global</option>
                        <option value="naive">Naive</option>
                        <option value="mix">Mix</option>
                      </select>
                    )}
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <button
                      onClick={
                        activeMode === "chat"
                          ? handleChat
                          : activeMode === "analyze"
                            ? handleAnalyze
                            : handleExtract
                      }
                      disabled={loading}
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium bg-vault-accent text-white hover:bg-vault-accent/80 disabled:opacity-50 transition-colors"
                    >
                      {loading ? <Spinner /> : null}
                      {activeMode === "chat"
                        ? "Query"
                        : activeMode === "analyze"
                          ? "Analyze"
                          : "Extract"}
                    </button>
                    {activeMode === "extract" && activeNoteId && (
                      <button
                        onClick={handleExtract}
                        disabled={loading}
                        className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium bg-vault-accent-subtle text-vault-accent hover:bg-vault-accent/20 disabled:opacity-50 transition-colors"
                      >
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
                  <Spinner />
                  Processing...
                </div>
              )}
              {error && (
                <div className="text-red-400 text-sm bg-red-400/10 rounded-md px-3 py-2">
                  {error}
                </div>
              )}
              {result && (
                <div className="space-y-2">
                  <pre className="text-xs text-vault-text-secondary whitespace-pre-wrap font-mono bg-vault-bg rounded-md px-4 py-3 overflow-x-auto leading-relaxed">
                    {result}
                  </pre>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
