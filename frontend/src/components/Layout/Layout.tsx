import { useState } from "react";
import Sidebar from "@/components/Sidebar";
import Editor from "@/components/Editor";
import Chat from "@/components/Chat";

export default function Layout() {
  const [chatOpen, setChatOpen] = useState(true);

  return (
    <div className="flex h-screen w-screen overflow-hidden">
      {/* Sidebar — fixed width file tree */}
      <Sidebar />

      {/* Main content area */}
      <div className="flex flex-1 min-w-0">
        {/* Editor — fills remaining space */}
        <main className="flex-1 min-w-0">
          <Editor />
        </main>

        {/* Chat pane — toggleable */}
        {chatOpen && (
          <div className="w-80 shrink-0">
            <Chat />
          </div>
        )}
      </div>

      {/* Chat toggle button */}
      <button
        onClick={() => setChatOpen((prev) => !prev)}
        className="fixed bottom-4 right-4 z-50 p-2 rounded-full bg-vault-accent text-vault-bg shadow-lg hover:bg-vault-accent-hover transition-colors"
        title={chatOpen ? "Hide Chat" : "Show Chat"}
      >
        {chatOpen ? "✕" : "💬"}
      </button>
    </div>
  );
}
