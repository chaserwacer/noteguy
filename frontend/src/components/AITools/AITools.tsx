import { useState, useCallback, type FC } from "react";
import { useNoteStore } from "@/store/useNoteStore";
import {
  fetchAIFrameworks,
  langchainAsk,
  llamaIndexQuery,
  crewaiResearch,
  crewaiSummarise,
  crewaiWrite,
  dspyAsk,
  dspySummarise,
  dspyTopics,
  instructorTags,
  instructorEntities,
  instructorSummary,
  mem0Chat,
  pydanticAiAsk,
  pydanticAiEnhance,
  pydanticAiConnections,
  type AIFrameworkInfo,
} from "@/api/client";

// ── Framework icons (simple SVG) ─────────────────────────────────────────

const FrameworkIcon: FC<{ id: string }> = ({ id }) => {
  const iconMap: Record<string, string> = {
    langchain: "LC",
    llama_index: "LI",
    crewai: "CA",
    dspy: "DS",
    instructor: "IN",
    mem0: "M0",
    pydantic_ai: "PA",
  };
  return (
    <div className="flex h-8 w-8 items-center justify-center rounded-md bg-vault-accent-subtle text-vault-accent text-[10px] font-bold shrink-0">
      {iconMap[id] || "AI"}
    </div>
  );
};

// ── Tool card ────────────────────────────────────────────────────────────

interface ToolAction {
  label: string;
  description: string;
  requiresNote: boolean;
  requiresInput: boolean;
  run: (noteId?: string, input?: string) => Promise<unknown>;
}

const FRAMEWORK_ACTIONS: Record<string, ToolAction[]> = {
  langchain: [
    {
      label: "Ask (LangChain RAG)",
      description: "Answer a question using LangChain's RetrievalQA chain",
      requiresNote: false,
      requiresInput: true,
      run: (_n, input) => langchainAsk(input!),
    },
  ],
  llama_index: [
    {
      label: "Query (LlamaIndex)",
      description: "Query notes using LlamaIndex's vector store index",
      requiresNote: false,
      requiresInput: true,
      run: (_n, input) => llamaIndexQuery(input!),
    },
  ],
  crewai: [
    {
      label: "Research Crew",
      description: "Multi-agent research across your notes",
      requiresNote: false,
      requiresInput: true,
      run: (_n, input) => crewaiResearch(input!),
    },
    {
      label: "Summarise Crew",
      description: "Multi-agent summarisation of a note",
      requiresNote: true,
      requiresInput: false,
      run: (noteId) => crewaiSummarise(noteId!),
    },
    {
      label: "Writing Crew",
      description: "Multi-agent content generation on a topic",
      requiresNote: false,
      requiresInput: true,
      run: (_n, input) => crewaiWrite(input!),
    },
  ],
  dspy: [
    {
      label: "Ask (DSPy CoT)",
      description: "Chain-of-thought RAG with DSPy modules",
      requiresNote: false,
      requiresInput: true,
      run: (_n, input) => dspyAsk(input!),
    },
    {
      label: "Summarise (DSPy)",
      description: "Structured summary with TL;DR and action items",
      requiresNote: true,
      requiresInput: false,
      run: (noteId) => dspySummarise(noteId!),
    },
    {
      label: "Extract Topics",
      description: "Extract topics, themes, and connections",
      requiresNote: true,
      requiresInput: false,
      run: (noteId) => dspyTopics(noteId!),
    },
  ],
  instructor: [
    {
      label: "Auto-Tag",
      description: "Extract structured tags and metadata with Pydantic validation",
      requiresNote: true,
      requiresInput: false,
      run: (noteId) => instructorTags(noteId!),
    },
    {
      label: "Extract Entities",
      description: "Find people, concepts, and technologies mentioned",
      requiresNote: true,
      requiresInput: false,
      run: (noteId) => instructorEntities(noteId!),
    },
    {
      label: "Structured Summary",
      description: "Generate summary with action items and related topics",
      requiresNote: true,
      requiresInput: false,
      run: (noteId) => instructorSummary(noteId!),
    },
  ],
  mem0: [
    {
      label: "Chat with Memory",
      description: "Chat with persistent memory across sessions",
      requiresNote: false,
      requiresInput: true,
      run: (_n, input) => mem0Chat(input!),
    },
  ],
  pydantic_ai: [
    {
      label: "Ask (PydanticAI)",
      description: "Type-safe QA with confidence scores and follow-ups",
      requiresNote: false,
      requiresInput: true,
      run: (_n, input) => pydanticAiAsk(input!),
    },
    {
      label: "Enhance Note",
      description: "Improve grammar, structure, and formatting",
      requiresNote: true,
      requiresInput: false,
      run: (noteId) => pydanticAiEnhance(noteId!),
    },
    {
      label: "Find Connections",
      description: "Discover links between this note and others",
      requiresNote: true,
      requiresInput: false,
      run: (noteId) => pydanticAiConnections(noteId!),
    },
  ],
};

// ── Main component ──────────────────────────────────────────────────────

interface AIToolsProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function AITools({ isOpen, onClose }: AIToolsProps) {
  const [frameworks, setFrameworks] = useState<AIFrameworkInfo[]>([]);
  const [loaded, setLoaded] = useState(false);
  const [selectedFramework, setSelectedFramework] = useState<string | null>(null);
  const [input, setInput] = useState("");
  const [result, setResult] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const activeNoteId = useNoteStore((s) => s.activeNoteId);

  // Load frameworks on first open
  const loadFrameworks = useCallback(async () => {
    if (loaded) return;
    try {
      const data = await fetchAIFrameworks();
      setFrameworks(data.frameworks);
      setLoaded(true);
    } catch {
      setError("Failed to load AI frameworks");
    }
  }, [loaded]);

  if (isOpen && !loaded) {
    loadFrameworks();
  }

  const runAction = useCallback(
    async (action: ToolAction) => {
      if (action.requiresNote && !activeNoteId) {
        setError("Select a note first to use this tool");
        return;
      }
      if (action.requiresInput && !input.trim()) {
        setError("Enter a question or prompt first");
        return;
      }

      setLoading(true);
      setError(null);
      setResult(null);

      try {
        const res = await action.run(
          activeNoteId ?? undefined,
          input.trim() || undefined,
        );
        setResult(JSON.stringify(res, null, 2));
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : "Request failed");
      } finally {
        setLoading(false);
      }
    },
    [activeNoteId, input],
  );

  if (!isOpen) return null;

  const actions = selectedFramework
    ? FRAMEWORK_ACTIONS[selectedFramework] ?? []
    : [];

  return (
    <div className="fixed inset-0 z-50 bg-vault-bg/80 backdrop-blur-sm animate-fade-in">
      <div className="absolute inset-4 bg-vault-surface border border-vault-border rounded-xl shadow-modal-full overflow-hidden flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-3 border-b border-vault-border/70 bg-gradient-to-r from-vault-surface to-vault-bg/60">
          <div className="space-y-0.5">
            <p className="text-sm font-semibold text-vault-text">AI Framework Tools</p>
            <p className="text-[11px] text-vault-text-secondary">
              7 frameworks &middot; LangChain, LlamaIndex, CrewAI, DSPy, Instructor, Mem0, PydanticAI
            </p>
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

        <div className="flex flex-1 min-h-0">
          {/* Framework sidebar */}
          <div className="w-56 border-r border-vault-border/50 overflow-y-auto py-2">
            {frameworks.map((fw) => (
              <button
                key={fw.id}
                onClick={() => {
                  setSelectedFramework(fw.id);
                  setResult(null);
                  setError(null);
                }}
                className={`w-full flex items-center gap-3 px-4 py-2.5 text-left transition-colors ${
                  selectedFramework === fw.id
                    ? "bg-vault-accent-subtle text-vault-accent"
                    : "text-vault-text-secondary hover:bg-vault-surface-hover hover:text-vault-text"
                }`}
              >
                <FrameworkIcon id={fw.id} />
                <div className="min-w-0">
                  <p className="text-xs font-medium truncate">{fw.name}</p>
                  <p className="text-[10px] text-vault-muted truncate">
                    {fw.category}
                  </p>
                </div>
              </button>
            ))}
          </div>

          {/* Main content */}
          <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
            {selectedFramework ? (
              <>
                {/* Framework info */}
                <div className="px-5 py-3 border-b border-vault-border/30">
                  <p className="text-xs text-vault-text-secondary">
                    {frameworks.find((f) => f.id === selectedFramework)?.description}
                  </p>
                </div>

                {/* Input */}
                <div className="px-5 py-3 border-b border-vault-border/30">
                  <input
                    type="text"
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    placeholder="Enter a question or prompt..."
                    className="w-full px-3 py-2 rounded-md bg-vault-bg border border-vault-border text-sm text-vault-text placeholder-vault-muted focus:outline-none focus:ring-1 focus:ring-vault-accent"
                    onKeyDown={(e) => {
                      if (e.key === "Enter" && actions.length > 0) {
                        runAction(actions[0]);
                      }
                    }}
                  />
                </div>

                {/* Actions */}
                <div className="px-5 py-3 border-b border-vault-border/30 flex flex-wrap gap-2">
                  {actions.map((action) => (
                    <button
                      key={action.label}
                      onClick={() => runAction(action)}
                      disabled={loading}
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium bg-vault-accent-subtle text-vault-accent hover:bg-vault-accent/20 disabled:opacity-50 transition-colors"
                      title={action.description}
                    >
                      {action.label}
                      {action.requiresNote && (
                        <span className="text-[9px] opacity-60">(note)</span>
                      )}
                    </button>
                  ))}
                </div>

                {/* Result / Error */}
                <div className="flex-1 overflow-y-auto px-5 py-3">
                  {loading && (
                    <div className="flex items-center gap-2 text-vault-muted text-sm">
                      <svg
                        className="animate-spin h-4 w-4"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="2"
                      >
                        <circle cx="12" cy="12" r="10" opacity="0.25" />
                        <path d="M12 2a10 10 0 019.95 9" opacity="0.75" />
                      </svg>
                      Processing with{" "}
                      {frameworks.find((f) => f.id === selectedFramework)?.name}...
                    </div>
                  )}
                  {error && (
                    <div className="text-red-400 text-sm bg-red-400/10 rounded-md px-3 py-2">
                      {error}
                    </div>
                  )}
                  {result && (
                    <pre className="text-xs text-vault-text-secondary whitespace-pre-wrap font-mono bg-vault-bg rounded-md px-4 py-3 overflow-x-auto">
                      {result}
                    </pre>
                  )}
                </div>
              </>
            ) : (
              <div className="flex-1 flex items-center justify-center text-vault-muted text-sm">
                Select a framework from the sidebar to get started
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
