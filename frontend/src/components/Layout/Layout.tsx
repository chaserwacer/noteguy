import { useState, useEffect, useCallback } from "react";
import { useNoteStore } from "@/store/useNoteStore";
import { useThemeStore } from "@/store/useThemeStore";
import Sidebar from "@/components/Sidebar";
import Editor from "@/components/Editor";
import Homepage from "@/components/Homepage";
import AIPanel from "@/components/AIPanel";
import Settings from "@/components/Settings";

type PanelMode = "chat" | "graph" | "query" | "analyze" | "extract" | "ingest";

export default function Layout() {
  const activeNoteId = useNoteStore((s) => s.activeNoteId);
  const theme = useThemeStore((s) => s.theme);
  const toggleTheme = useThemeStore((s) => s.toggleTheme);
  const [aiPanelOpen, setAiPanelOpen] = useState(false);
  const [aiPanelMode, setAiPanelMode] = useState<PanelMode>("chat");
  const [settingsOpen, setSettingsOpen] = useState(false);

  const openAIPanel = useCallback((mode: PanelMode = "chat") => {
    setAiPanelMode(mode);
    setAiPanelOpen(true);
  }, []);

  // Keyboard shortcuts
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      // Cmd/Ctrl + Shift + C — toggle AI panel (chat mode)
      if ((e.metaKey || e.ctrlKey) && e.shiftKey && e.key === "C") {
        e.preventDefault();
        if (aiPanelOpen && aiPanelMode === "chat") {
          setAiPanelOpen(false);
        } else {
          openAIPanel("chat");
        }
      }
      // Cmd/Ctrl + Shift + A — toggle AI panel (tools mode)
      if ((e.metaKey || e.ctrlKey) && e.shiftKey && e.key === "A") {
        e.preventDefault();
        if (aiPanelOpen) {
          setAiPanelOpen(false);
        } else {
          openAIPanel("query");
        }
      }
      // Cmd/Ctrl + Shift + G — toggle AI panel (graph mode)
      if ((e.metaKey || e.ctrlKey) && e.shiftKey && e.key === "G") {
        e.preventDefault();
        if (aiPanelOpen && aiPanelMode === "graph") {
          setAiPanelOpen(false);
        } else {
          openAIPanel("graph");
        }
      }
      // Cmd/Ctrl + , — open settings
      if ((e.metaKey || e.ctrlKey) && e.key === ",") {
        e.preventDefault();
        setSettingsOpen((prev) => !prev);
      }
      // Escape to close panels
      if (e.key === "Escape") {
        if (settingsOpen) setSettingsOpen(false);
        else if (aiPanelOpen) setAiPanelOpen(false);
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [aiPanelOpen, aiPanelMode, settingsOpen, openAIPanel]);

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-vault-bg">
      {/* Sidebar */}
      <Sidebar />

      {/* Main content: Homepage when no note selected, Editor otherwise */}
      <main className="flex-1 min-w-0">
        {activeNoteId ? (
          <Editor />
        ) : (
          <Homepage
            onOpenChat={() => openAIPanel("chat")}
            onOpenAITools={() => openAIPanel("query")}
            onOpenGraph={() => openAIPanel("graph")}
          />
        )}
      </main>

      {/* Unified AI Panel (Chat + Graph + Tools) */}
      <AIPanel
        isOpen={aiPanelOpen}
        onClose={() => setAiPanelOpen(false)}
        initialMode={aiPanelMode}
      />

      {/* Settings panel */}
      <Settings
        isOpen={settingsOpen}
        onClose={() => setSettingsOpen(false)}
      />

      {/* FAB buttons */}
      {!aiPanelOpen && (
        <div className="fixed bottom-4 right-4 z-30 flex flex-col gap-2">
          {/* Theme toggle */}
          <button
            onClick={toggleTheme}
            className="flex items-center gap-2 px-4 py-2.5 rounded-full bg-vault-surface border border-vault-border shadow-float text-vault-text-secondary hover:text-vault-text hover:border-vault-border-strong transition-all"
            title={`Switch to ${theme === "dark" ? "light" : "dark"} mode`}
          >
            {theme === "dark" ? (
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round" className="text-vault-accent">
                <circle cx="8" cy="8" r="3" />
                <path d="M8 1.5v1M8 13.5v1M1.5 8h1M13.5 8h1M3.4 3.4l.7.7M11.9 11.9l.7.7M3.4 12.6l.7-.7M11.9 4.1l.7-.7" />
              </svg>
            ) : (
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round" className="text-vault-accent">
                <path d="M13.5 8.5a5.5 5.5 0 01-7.5 5.1A5.5 5.5 0 018.5 2.5a4.5 4.5 0 005 6z" />
              </svg>
            )}
            <span className="text-xs font-medium">{theme === "dark" ? "Light" : "Dark"}</span>
          </button>

          {/* Settings button */}
          <button
            onClick={() => setSettingsOpen(true)}
            className="flex items-center gap-2 px-4 py-2.5 rounded-full bg-vault-surface border border-vault-border shadow-float text-vault-text-secondary hover:text-vault-text hover:border-vault-border-strong transition-all"
            title="AI Settings (Ctrl+,)"
          >
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round" className="text-vault-accent">
              <circle cx="8" cy="8" r="2.5" />
              <path d="M13.5 8a5.5 5.5 0 01-.3 1.8l1.3.8-.8 1.4-1.4-.5a5.5 5.5 0 01-1.6 1l-.2 1.5h-1.6l-.2-1.5a5.5 5.5 0 01-1.6-1l-1.4.5-.8-1.4 1.3-.8A5.5 5.5 0 015.8 8a5.5 5.5 0 01.3-1.8l-1.3-.8.8-1.4 1.4.5a5.5 5.5 0 011.6-1l.2-1.5h1.6l.2 1.5a5.5 5.5 0 011.6 1l1.4-.5.8 1.4-1.3.8c.2.6.3 1.2.3 1.8z" />
            </svg>
            <span className="text-xs font-medium">Settings</span>
          </button>

          {/* Knowledge Graph button */}
          <button
            onClick={() => openAIPanel("graph")}
            className="flex items-center gap-2 px-4 py-2.5 rounded-full bg-vault-surface border border-vault-border shadow-float text-vault-text-secondary hover:text-vault-text hover:border-vault-border-strong transition-all"
            title="Knowledge Graph (Ctrl+Shift+G)"
          >
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round" className="text-vault-accent">
              <circle cx="4" cy="4" r="1.5" />
              <circle cx="12" cy="4" r="1.5" />
              <circle cx="8" cy="12" r="1.5" />
              <path d="M5.3 5.2L7 10.5M10.7 5.2L9 10.5M5.5 4h5" />
            </svg>
            <span className="text-xs font-medium">Graph</span>
          </button>

          {/* AI Panel button */}
          <button
            onClick={() => openAIPanel("chat")}
            className="flex items-center gap-2 px-4 py-2.5 rounded-full bg-vault-surface border border-vault-border shadow-float text-vault-text-secondary hover:text-vault-text hover:border-vault-border-strong transition-all"
            title="AI Panel (Ctrl+Shift+C)"
          >
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round" className="text-vault-accent">
              <path d="M2 3h12v8H5l-3 3V3z" />
              <path d="M5 6.5h6M5 8.5h4" />
            </svg>
            <span className="text-xs font-medium">AI</span>
          </button>
        </div>
      )}
    </div>
  );
}
