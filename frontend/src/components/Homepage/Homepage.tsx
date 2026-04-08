import { useState, useCallback, useEffect, useRef, useMemo } from "react";
import { useNoteStore } from "@/store/useNoteStore";
import {
  aiKGStats,
  aiIngestDocument,
  type AIKGStatsResponse,
  type NoteData,
} from "@/api/client";

/* ── Helpers ───────────────────────────────────────────────────────────────── */

function timeAgo(dateStr: string): string {
  const now = Date.now();
  const then = new Date(dateStr).getTime();
  const diff = Math.max(0, now - then);
  const seconds = Math.floor(diff / 1000);
  if (seconds < 60) return "just now";
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  if (days < 7) return `${days}d ago`;
  return new Date(dateStr).toLocaleDateString();
}

function greeting(): string {
  const h = new Date().getHours();
  if (h < 12) return "Good morning";
  if (h < 17) return "Good afternoon";
  return "Good evening";
}

/* ── Icons ─────────────────────────────────────────────────────────────────── */

function NoteIcon({ className = "w-4 h-4" }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round">
      <path d="M4 2h8a1 1 0 011 1v10a1 1 0 01-1 1H4a1 1 0 01-1-1V3a1 1 0 011-1z" />
      <path d="M5 5h6M5 8h6M5 11h3" />
    </svg>
  );
}

function FolderIcon({ className = "w-4 h-4" }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round">
      <path d="M2 4.5V12.5H14V6.5H8L6.5 4.5H2Z" />
    </svg>
  );
}

function UploadIcon({ className = "w-5 h-5" }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round">
      <path d="M8 10V2M8 2L5 5M8 2l3 3" />
      <path d="M2 10v3a1 1 0 001 1h10a1 1 0 001-1v-3" />
    </svg>
  );
}

function ChatIcon({ className = "w-5 h-5" }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round">
      <path d="M2 3h12v8H5l-3 3V3z" />
      <path d="M5 6.5h6M5 8.5h4" />
    </svg>
  );
}

function QueryIcon({ className = "w-5 h-5" }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="7" cy="7" r="5" />
      <path d="M10.5 10.5L14 14" />
    </svg>
  );
}

function AnalyzeIcon({ className = "w-5 h-5" }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round">
      <rect x="1" y="10" width="3" height="4" rx="0.5" />
      <rect x="6" y="6" width="3" height="8" rx="0.5" />
      <rect x="11" y="2" width="3" height="12" rx="0.5" />
    </svg>
  );
}

function ExtractIcon({ className = "w-5 h-5" }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round">
      <path d="M3 2h10a1 1 0 011 1v10a1 1 0 01-1 1H3a1 1 0 01-1-1V3a1 1 0 011-1z" />
      <path d="M5 5h6M5 8h6M5 11h3" />
      <circle cx="12" cy="12" r="3" fill="#191919" stroke="currentColor" />
      <path d="M12 10.5v3M10.5 12h3" />
    </svg>
  );
}

function GraphIcon({ className = "w-5 h-5" }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="4" cy="4" r="1.5" />
      <circle cx="12" cy="4" r="1.5" />
      <circle cx="8" cy="12" r="1.5" />
      <path d="M5.3 5.2L7 10.5M10.7 5.2L9 10.5M5.5 4h5" />
    </svg>
  );
}

function IngestIcon({ className = "w-5 h-5" }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round">
      <path d="M2 8h12" />
      <path d="M8 2v12" />
      <rect x="2" y="2" width="12" height="12" rx="2" />
    </svg>
  );
}

function PlusIcon({ className = "w-4 h-4" }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round">
      <path d="M8 3v10M3 8h10" />
    </svg>
  );
}

/* ── Component ─────────────────────────────────────────────────────────────── */

interface HomepageProps {
  onOpenChat: () => void;
  onOpenAITools: () => void;
  onOpenGraph: () => void;
}

export default function Homepage({ onOpenChat, onOpenAITools, onOpenGraph }: HomepageProps) {
  const notes = useNoteStore((s) => s.notes);
  const folders = useNoteStore((s) => s.folders);
  const setActiveNote = useNoteStore((s) => s.setActiveNote);
  const addNote = useNoteStore((s) => s.addNote);
  const load = useNoteStore((s) => s.load);

  const [kgStats, setKgStats] = useState<AIKGStatsResponse | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadMsg, setUploadMsg] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Load KG stats on mount
  useEffect(() => {
    aiKGStats()
      .then(setKgStats)
      .catch(() => {});
  }, []);

  // Recently edited notes (top 8, sorted by updated_at desc)
  const recentNotes = useMemo(() => {
    return [...notes]
      .sort((a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime())
      .slice(0, 8);
  }, [notes]);

  // Folder name lookup
  const folderNameMap = useMemo(() => {
    const map = new Map<string, string>();
    folders.forEach((f) => map.set(f.id, f.name));
    return map;
  }, [folders]);

  // Upload handler
  const handleUpload = useCallback(
    async (files: FileList | File[]) => {
      const file = files[0];
      if (!file) return;
      setUploading(true);
      setUploadMsg(null);
      try {
        const res = await aiIngestDocument(file);
        setUploadMsg(`Uploaded "${res.title ?? file.name}" successfully`);
        await load();
        const stats = await aiKGStats().catch(() => null);
        if (stats) setKgStats(stats);
      } catch (err: unknown) {
        setUploadMsg(err instanceof Error ? err.message : "Upload failed");
      } finally {
        setUploading(false);
        if (fileInputRef.current) fileInputRef.current.value = "";
        setTimeout(() => setUploadMsg(null), 4000);
      }
    },
    [load],
  );

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragOver(false);
      if (e.dataTransfer.files.length) {
        handleUpload(Array.from(e.dataTransfer.files));
      }
    },
    [handleUpload],
  );

  const handleNewNote = useCallback(async () => {
    const note = await addNote();
    setActiveNote(note.id);
  }, [addNote, setActiveNote]);

  // Content preview helper
  const contentPreview = (note: NoteData) => {
    const text = note.content.replace(/^#+\s+/gm, "").replace(/[*_`~\[\]]/g, "").trim();
    if (!text) return "Empty note";
    return text.length > 80 ? text.slice(0, 80) + "..." : text;
  };

  const aiTools = [
    { id: "chat", name: "Chat", desc: "Ask questions about your notes", icon: ChatIcon, action: onOpenChat },
    { id: "query", name: "Query", desc: "Hybrid knowledge graph search", icon: QueryIcon, action: onOpenAITools },
    { id: "analyze", name: "Analyze", desc: "Cross-document analysis", icon: AnalyzeIcon, action: onOpenAITools },
    { id: "extract", name: "Extract", desc: "Extract entities & relations", icon: ExtractIcon, action: onOpenAITools },
    { id: "ingest", name: "Ingest", desc: "Index notes into knowledge graph", icon: IngestIcon, action: onOpenAITools },
    { id: "knowledge_graph", name: "Knowledge Graph", desc: "Interactive entity graph view", icon: GraphIcon, action: onOpenGraph },
  ];

  return (
    <div className="h-full overflow-y-auto bg-vault-bg">
      <div className="max-w-3xl mx-auto px-6 py-10 space-y-8">
        {/* Greeting */}
        <div className="space-y-1">
          <h1 className="text-2xl font-bold text-vault-text">{greeting()}</h1>
          <p className="text-sm text-vault-text-secondary">
            {notes.length} {notes.length === 1 ? "note" : "notes"} across{" "}
            {folders.length} {folders.length === 1 ? "folder" : "folders"}
            {kgStats && (
              <span className="text-vault-muted">
                {" "}&middot; {kgStats.entities} entities &middot; {kgStats.relations} relations
              </span>
            )}
          </p>
        </div>

        {/* Quick actions */}
        <div className="flex gap-3">
          <button
            onClick={handleNewNote}
            className="inline-flex items-center gap-2 px-4 py-2.5 rounded-lg bg-vault-accent text-white text-sm font-medium hover:bg-vault-accent-hover transition-colors"
          >
            <PlusIcon className="w-4 h-4" />
            New Note
          </button>
          <button
            onClick={() => fileInputRef.current?.click()}
            disabled={uploading}
            className="inline-flex items-center gap-2 px-4 py-2.5 rounded-lg bg-vault-surface border border-vault-border text-vault-text text-sm font-medium hover:bg-vault-surface-hover hover:border-vault-border-strong transition-colors disabled:opacity-50"
          >
            <UploadIcon className="w-4 h-4" />
            {uploading ? "Uploading..." : "Upload Document"}
          </button>
          <input
            ref={fileInputRef}
            type="file"
            accept=".md,.txt,.docx,.pdf,.pptx,.xlsx,.jpg,.jpeg,.png"
            className="hidden"
            onChange={(e) => {
              if (e.target.files?.length) handleUpload(Array.from(e.target.files));
            }}
          />
        </div>

        {uploadMsg && (
          <div className={`text-xs px-3 py-2 rounded-md ${uploadMsg.includes("failed") || uploadMsg.includes("error") ? "bg-red-400/10 text-red-400" : "bg-vault-success/10 text-vault-success"}`}>
            {uploadMsg}
          </div>
        )}

        {/* Recently edited */}
        <section className="space-y-3">
          <h2 className="text-xs font-semibold uppercase tracking-wider text-vault-muted">
            Recently Edited
          </h2>
          {recentNotes.length === 0 ? (
            <div className="text-sm text-vault-muted py-6 text-center border border-dashed border-vault-border rounded-lg">
              No notes yet. Create one to get started.
            </div>
          ) : (
            <div className="grid gap-2">
              {recentNotes.map((note) => (
                <button
                  key={note.id}
                  onClick={() => setActiveNote(note.id)}
                  className="group flex items-start gap-3 w-full text-left px-4 py-3 rounded-lg bg-vault-surface border border-vault-border hover:border-vault-border-strong hover:bg-vault-surface-hover transition-all"
                >
                  <NoteIcon className="w-4 h-4 text-vault-muted mt-0.5 shrink-0" />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-baseline justify-between gap-2">
                      <span className="text-sm font-medium text-vault-text truncate group-hover:text-vault-accent transition-colors">
                        {note.title || "Untitled"}
                      </span>
                      <span className="text-[11px] text-vault-muted whitespace-nowrap shrink-0">
                        {timeAgo(note.updated_at)}
                      </span>
                    </div>
                    <div className="flex items-center gap-2 mt-0.5">
                      <p className="text-xs text-vault-muted truncate">
                        {contentPreview(note)}
                      </p>
                      {note.folder_id && folderNameMap.has(note.folder_id) && (
                        <span className="inline-flex items-center gap-1 text-[10px] text-vault-muted bg-vault-bg px-1.5 py-0.5 rounded shrink-0">
                          <FolderIcon className="w-2.5 h-2.5" />
                          {folderNameMap.get(note.folder_id)}
                        </span>
                      )}
                    </div>
                  </div>
                </button>
              ))}
            </div>
          )}
        </section>

        {/* Document upload drop zone */}
        <section className="space-y-3">
          <h2 className="text-xs font-semibold uppercase tracking-wider text-vault-muted">
            Upload Documents
          </h2>
          <div
            onDragOver={(e) => {
              e.preventDefault();
              setDragOver(true);
            }}
            onDragLeave={() => setDragOver(false)}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
            className={`flex flex-col items-center justify-center gap-2 py-8 rounded-lg border-2 border-dashed cursor-pointer transition-all ${
              dragOver
                ? "border-vault-accent bg-vault-accent-subtle"
                : "border-vault-border hover:border-vault-border-strong hover:bg-vault-surface"
            }`}
          >
            <UploadIcon className={`w-6 h-6 ${dragOver ? "text-vault-accent" : "text-vault-muted"}`} />
            <p className="text-sm text-vault-text-secondary">
              {dragOver ? "Drop to upload" : "Drag & drop files here"}
            </p>
            <p className="text-[11px] text-vault-muted">
              .md, .txt, .docx, .pdf, .pptx, .xlsx, images
            </p>
          </div>
        </section>

        {/* AI Tools grid */}
        <section className="space-y-3">
          <h2 className="text-xs font-semibold uppercase tracking-wider text-vault-muted">
            AI Tools
          </h2>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
            {aiTools.map((tool) => (
              <button
                key={tool.id}
                onClick={tool.action}
                className="group flex flex-col items-start gap-2 px-4 py-3 rounded-lg bg-vault-surface border border-vault-border hover:border-vault-accent/40 hover:bg-vault-surface-hover transition-all text-left"
              >
                <tool.icon className="w-5 h-5 text-vault-muted group-hover:text-vault-accent transition-colors" />
                <div>
                  <p className="text-sm font-medium text-vault-text group-hover:text-vault-accent transition-colors">
                    {tool.name}
                  </p>
                  <p className="text-[11px] text-vault-muted leading-tight">
                    {tool.desc}
                  </p>
                </div>
              </button>
            ))}
          </div>
        </section>

        {/* Vault stats */}
        {kgStats && (kgStats.entities > 0 || kgStats.relations > 0) && (
          <section className="space-y-3">
            <h2 className="text-xs font-semibold uppercase tracking-wider text-vault-muted">
              Knowledge Graph
            </h2>
            <div className="flex gap-4">
              <div className="flex-1 px-4 py-3 rounded-lg bg-vault-surface border border-vault-border">
                <p className="text-2xl font-bold text-vault-accent">{kgStats.entities}</p>
                <p className="text-[11px] text-vault-muted">Entities</p>
              </div>
              <div className="flex-1 px-4 py-3 rounded-lg bg-vault-surface border border-vault-border">
                <p className="text-2xl font-bold text-vault-accent">{kgStats.relations}</p>
                <p className="text-[11px] text-vault-muted">Relations</p>
              </div>
              <div className="flex-1 px-4 py-3 rounded-lg bg-vault-surface border border-vault-border">
                <p className="text-2xl font-bold text-vault-text">{notes.length}</p>
                <p className="text-[11px] text-vault-muted">Notes</p>
              </div>
              <div className="flex-1 px-4 py-3 rounded-lg bg-vault-surface border border-vault-border">
                <p className="text-2xl font-bold text-vault-text">{folders.length}</p>
                <p className="text-[11px] text-vault-muted">Folders</p>
              </div>
            </div>
          </section>
        )}

        {/* Keyboard shortcuts hint */}
        <div className="flex flex-wrap gap-x-4 gap-y-1 text-[11px] text-vault-muted pt-2">
          <span><kbd className="px-1.5 py-0.5 rounded bg-vault-surface border border-vault-border text-[10px]">Ctrl+N</kbd> New note</span>
          <span><kbd className="px-1.5 py-0.5 rounded bg-vault-surface border border-vault-border text-[10px]">Ctrl+Shift+C</kbd> Chat</span>
          <span><kbd className="px-1.5 py-0.5 rounded bg-vault-surface border border-vault-border text-[10px]">Ctrl+Shift+A</kbd> AI Tools</span>
          <span><kbd className="px-1.5 py-0.5 rounded bg-vault-surface border border-vault-border text-[10px]">Ctrl+/</kbd> Search</span>
        </div>
      </div>
    </div>
  );
}
