import { useState, useEffect } from "react";
import Sidebar from "@/components/Sidebar";
import Editor from "@/components/Editor";
import Chat from "@/components/Chat";
import AITools from "@/components/AITools";

export default function Layout() {
  const [chatOpen, setChatOpen] = useState(false);
  const [chatExpanded, setChatExpanded] = useState(false);
  const [aiToolsOpen, setAiToolsOpen] = useState(false);

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
      // Escape to close expanded chat or AI tools
      if (e.key === "Escape") {
        if (aiToolsOpen) setAiToolsOpen(false);
        else if (chatExpanded) setChatExpanded(false);
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [chatExpanded, aiToolsOpen]);

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

      {/* AI Framework Tools panel */}
      <AITools
        isOpen={aiToolsOpen}
        onClose={() => setAiToolsOpen(false)}
      />

      {/* FAB buttons */}
      {!chatOpen && (
        <div className="fixed bottom-4 right-4 z-30 flex flex-col gap-2">
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
