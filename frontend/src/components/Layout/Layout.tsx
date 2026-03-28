import { useState, useEffect, useCallback, useRef } from "react";
import Sidebar from "@/components/Sidebar";
import Editor from "@/components/Editor";
import Chat from "@/components/Chat";

const MIN_CHAT_WIDTH = 280;
const MAX_CHAT_FRACTION = 0.6;
const DEFAULT_CHAT_FRACTION = 0.4;

export default function Layout() {
  const [chatOpen, setChatOpen] = useState(true);
  const [chatFraction, setChatFraction] = useState(DEFAULT_CHAT_FRACTION);
  const containerRef = useRef<HTMLDivElement>(null);
  const isDragging = useRef(false);

  // ── Keyboard shortcut: Cmd/Ctrl + Shift + C ──────────────────────────
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.shiftKey && e.key === "C") {
        e.preventDefault();
        setChatOpen((prev) => !prev);
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, []);

  // ── Resize handle drag logic ─────────────────────────────────────────
  const handlePointerDown = useCallback(
    (e: React.PointerEvent) => {
      if (!containerRef.current) return;
      e.preventDefault();
      isDragging.current = true;
      const el = e.currentTarget as HTMLElement;
      el.setPointerCapture(e.pointerId);

      const containerRect = containerRef.current.getBoundingClientRect();

      const onPointerMove = (ev: PointerEvent) => {
        if (!isDragging.current) return;
        const containerWidth = containerRect.width;
        // Chat is on the right — calculate from right edge
        const chatWidth = containerRect.right - ev.clientX;
        let fraction = chatWidth / containerWidth;
        // Clamp
        const minFraction = MIN_CHAT_WIDTH / containerWidth;
        fraction = Math.max(minFraction, Math.min(MAX_CHAT_FRACTION, fraction));
        setChatFraction(fraction);
      };

      const onPointerUp = () => {
        isDragging.current = false;
        window.removeEventListener("pointermove", onPointerMove);
        window.removeEventListener("pointerup", onPointerUp);
      };

      window.addEventListener("pointermove", onPointerMove);
      window.addEventListener("pointerup", onPointerUp);
    },
    [],
  );

  const chatWidthPercent = chatOpen ? `${chatFraction * 100}%` : "0px";

  return (
    <div className="flex h-screen w-screen overflow-hidden">
      {/* Sidebar — fixed width file tree */}
      <Sidebar />

      {/* Main content area (editor + chat) */}
      <div ref={containerRef} className="flex flex-1 min-w-0">
        {/* Editor — fills remaining space */}
        <main
          className="min-w-0"
          style={{
            flex: "1 1 0%",
            transition: isDragging.current
              ? "none"
              : "flex 200ms ease",
          }}
        >
          <Editor />
        </main>

        {/* Resize handle */}
        {chatOpen && (
          <div
            onPointerDown={handlePointerDown}
            className="w-1 shrink-0 cursor-col-resize bg-vault-border hover:bg-vault-accent transition-colors relative group"
          >
            {/* Larger invisible hit target */}
            <div className="absolute inset-y-0 -left-1 -right-1" />
          </div>
        )}

        {/* Chat pane */}
        <div
          className="shrink-0 overflow-hidden"
          style={{
            width: chatWidthPercent,
            transition: isDragging.current
              ? "none"
              : "width 200ms ease",
          }}
        >
          {chatOpen && <Chat />}
        </div>
      </div>

      {/* Chat toggle button */}
      <button
        onClick={() => setChatOpen((prev) => !prev)}
        className="fixed bottom-4 right-4 z-50 p-2 rounded-full bg-vault-accent text-vault-bg shadow-lg hover:bg-vault-accent-hover transition-colors"
        title={
          chatOpen
            ? "Hide Chat (Ctrl+Shift+C)"
            : "Show Chat (Ctrl+Shift+C)"
        }
      >
        {chatOpen ? "✕" : "💬"}
      </button>
    </div>
  );
}
