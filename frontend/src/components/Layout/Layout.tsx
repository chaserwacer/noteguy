import { useState, useEffect } from "react";
import Sidebar from "@/components/Sidebar";
import Editor from "@/components/Editor";
import Chat from "@/components/Chat";

export default function Layout() {
  const [chatOpen, setChatOpen] = useState(false);
  const [chatExpanded, setChatExpanded] = useState(false);

  // Keyboard shortcut: Cmd/Ctrl + Shift + C
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.shiftKey && e.key === "C") {
        e.preventDefault();
        setChatOpen((prev) => !prev);
        setChatExpanded(false);
      }
      // Escape to close expanded chat
      if (e.key === "Escape" && chatExpanded) {
        setChatExpanded(false);
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [chatExpanded]);

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

      {/* Chat FAB button */}
      {!chatOpen && (
        <button
          onClick={() => setChatOpen(true)}
          className="fixed bottom-4 right-4 z-30 flex items-center gap-2 px-4 py-2.5 rounded-full bg-vault-surface border border-vault-border shadow-float text-vault-text-secondary hover:text-vault-text hover:border-vault-border-strong transition-all group"
          title="Open AI Chat (Ctrl+Shift+C)"
        >
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round" className="text-vault-accent">
            <path d="M2 3h12v8H5l-3 3V3z" />
            <path d="M5 6.5h6M5 8.5h4" />
          </svg>
          <span className="text-xs font-medium">AI</span>
        </button>
      )}
    </div>
  );
}
