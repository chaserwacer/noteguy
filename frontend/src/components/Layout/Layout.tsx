import { useState, useEffect } from "react";
import Sidebar from "@/components/Sidebar";
import Editor from "@/components/Editor";
import Chat from "@/components/Chat";
import AITools from "@/components/AITools";
import Settings from "@/components/Settings";

export default function Layout() {
  const [chatOpen, setChatOpen] = useState(false);
  const [chatExpanded, setChatExpanded] = useState(false);
  const [aiToolsOpen, setAiToolsOpen] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);

  // Keyboard shortcuts
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      // Cmd/Ctrl + Shift + C — toggle chat
      if ((e.metaKey || e.ctrlKey) && e.shiftKey && e.key === "C") {
        e.preventDefault();
        setChatOpen((prev) => !prev);
        setChatExpanded(false);
      }
      // Cmd/Ctrl + Shift + A — toggle AI tools
      if ((e.metaKey || e.ctrlKey) && e.shiftKey && e.key === "A") {
        e.preventDefault();
        setAiToolsOpen((prev) => !prev);
      }
      // Cmd/Ctrl + , — open settings
      if ((e.metaKey || e.ctrlKey) && e.key === ",") {
        e.preventDefault();
        setSettingsOpen((prev) => !prev);
      }
      // Escape to close expanded chat, AI tools, or settings
      if (e.key === "Escape") {
        if (settingsOpen) setSettingsOpen(false);
        else if (aiToolsOpen) setAiToolsOpen(false);
        else if (chatExpanded) setChatExpanded(false);
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [chatExpanded, aiToolsOpen, settingsOpen]);

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-vault-bg">
      {/* Sidebar */}
      <Sidebar />

      {/* Editor fills remaining space */}
      <main className="flex-1 min-w-0">
        <Editor />
      </main>

      {/* Chat modal (bottom sheet / fullscreen) */}
      <Chat
        isOpen={chatOpen}
        isExpanded={chatExpanded}
        onExpand={() => setChatExpanded(true)}
        onCollapse={() => setChatExpanded(false)}
        onClose={() => {
          setChatOpen(false);
          setChatExpanded(false);
        }}
      />

      {/* AI Tools panel (LightRAG + RAG-Anything) */}
      <AITools
        isOpen={aiToolsOpen}
        onClose={() => setAiToolsOpen(false)}
      />

      {/* Settings panel */}
      <Settings
        isOpen={settingsOpen}
        onClose={() => setSettingsOpen(false)}
      />

      {/* FAB buttons */}
      {!chatOpen && (
        <div className="fixed bottom-4 right-4 z-30 flex flex-col gap-2">
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

          {/* AI Tools button */}
          <button
            onClick={() => setAiToolsOpen(true)}
            className="flex items-center gap-2 px-4 py-2.5 rounded-full bg-vault-surface border border-vault-border shadow-float text-vault-text-secondary hover:text-vault-text hover:border-vault-border-strong transition-all"
            title="AI Framework Tools (Ctrl+Shift+A)"
          >
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round" className="text-vault-accent">
              <path d="M8 1v2M8 13v2M1 8h2M13 8h2M3.5 3.5l1.4 1.4M11.1 11.1l1.4 1.4M3.5 12.5l1.4-1.4M11.1 4.9l1.4-1.4" />
              <circle cx="8" cy="8" r="3" />
            </svg>
            <span className="text-xs font-medium">Tools</span>
          </button>

          {/* Chat button */}
          <button
            onClick={() => setChatOpen(true)}
            className="flex items-center gap-2 px-4 py-2.5 rounded-full bg-vault-surface border border-vault-border shadow-float text-vault-text-secondary hover:text-vault-text hover:border-vault-border-strong transition-all"
            title="Open AI Chat (Ctrl+Shift+C)"
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
