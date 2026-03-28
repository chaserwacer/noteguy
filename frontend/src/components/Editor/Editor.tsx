import { useEffect, useRef, useCallback, useState } from "react";
import { EditorState, type Extension } from "@codemirror/state";
import { EditorView, keymap, placeholder } from "@codemirror/view";
import { markdown } from "@codemirror/lang-markdown";
import { defaultKeymap } from "@codemirror/commands";
import {
  syntaxHighlighting,
  HighlightStyle,
} from "@codemirror/language";
import { tags } from "@lezer/highlight";
import { useNoteStore } from "@/store/useNoteStore";
import EditorToolbar from "./EditorToolbar";
import MarkdownPreview from "./MarkdownPreview";
import HistoryPanel from "./HistoryPanel";

const SAVE_DEBOUNCE_MS = 1200;

/* ── Syntax highlight style ──────────────────────────────────────────────── */

const mdHighlight = HighlightStyle.define([
  { tag: tags.heading1, color: "#e8e4df", fontWeight: "700", fontSize: "1.6em" },
  { tag: tags.heading2, color: "#e8e4df", fontWeight: "600", fontSize: "1.35em" },
  { tag: tags.heading3, color: "#e8e4df", fontWeight: "600", fontSize: "1.15em" },
  { tag: tags.heading4, color: "#e8e4df", fontWeight: "500" },
  { tag: tags.strong, color: "#e8e4df", fontWeight: "700" },
  { tag: tags.emphasis, color: "#e8e4df", fontStyle: "italic" },
  { tag: tags.monospace, color: "#7dae80", fontFamily: "'JetBrains Mono', monospace" },
  { tag: tags.link, color: "#c4956a", textDecoration: "underline" },
  { tag: tags.url, color: "#6b6560" },
  { tag: tags.quote, color: "#a8a29e", fontStyle: "italic" },
  { tag: tags.processingInstruction, color: "#6b6560" },
]);

/* ── Editor theme ────────────────────────────────────────────────────────── */

const vaultTheme = EditorView.theme(
  {
    "&": {
      backgroundColor: "#191919",
      color: "#e8e4df",
      fontFamily: "'Inter', system-ui, sans-serif",
      fontSize: "15px",
      lineHeight: "1.75",
      height: "100%",
    },
    ".cm-content": {
      padding: "1rem 2rem",
      caretColor: "#c4956a",
      maxWidth: "72ch",
      marginLeft: "auto",
      marginRight: "auto",
    },
    ".cm-cursor": {
      borderLeftColor: "#c4956a",
      borderLeftWidth: "2px",
    },
    "&.cm-focused .cm-selectionBackground, .cm-selectionBackground": {
      backgroundColor: "rgba(196, 149, 106, 0.15)",
    },
    ".cm-gutters": {
      display: "none",
    },
    ".cm-scroller": {
      overflow: "auto",
    },
    ".cm-placeholder": {
      color: "#3a3a3a",
      fontStyle: "italic",
    },
    "&.cm-focused": {
      outline: "none",
    },
  },
  { dark: true },
);

/* ── Save status type ────────────────────────────────────────────────────── */

type SaveStatus = "idle" | "saving" | "saved";

/* ── Component ───────────────────────────────────────────────────────────── */

export default function Editor() {
  const containerRef = useRef<HTMLDivElement>(null);
  const viewRef = useRef<EditorView | null>(null);
  const saveTimerRef = useRef<ReturnType<typeof setTimeout>>(undefined);
  const titleTimerRef = useRef<ReturnType<typeof setTimeout>>(undefined);

  const activeNoteId = useNoteStore((s) => s.activeNoteId);
  const notes = useNoteStore((s) => s.notes);
  const saveNote = useNoteStore((s) => s.saveNote);

  const historyPanelOpen = useNoteStore((s) => s.historyPanelOpen);
  const previewContent = useNoteStore((s) => s.previewContent);
  const selectedVersionSha = useNoteStore((s) => s.selectedVersionSha);
  const toggleHistoryPanel = useNoteStore((s) => s.toggleHistoryPanel);

  const activeNote = notes.find((n) => n.id === activeNoteId);

  const [saveStatus, setSaveStatus] = useState<SaveStatus>("idle");
  const [showPreview, setShowPreview] = useState(false);
  const [toolbarVisible, setToolbarVisible] = useState(false);

  /* ── Autosave content ────────────────────────────────────────────────────── */

  const handleContentChange = useCallback(
    (content: string) => {
      if (!activeNoteId) return;
      clearTimeout(saveTimerRef.current);
      setSaveStatus("saving");
      saveTimerRef.current = setTimeout(async () => {
        await saveNote(activeNoteId, { content });
        setSaveStatus("saved");
        setTimeout(() => setSaveStatus("idle"), 1500);
      }, SAVE_DEBOUNCE_MS);
    },
    [activeNoteId, saveNote],
  );

  /* ── Autosave title ──────────────────────────────────────────────────────── */

  const handleTitleChange = useCallback(
    (title: string) => {
      if (!activeNoteId) return;
      clearTimeout(titleTimerRef.current);
      setSaveStatus("saving");
      titleTimerRef.current = setTimeout(async () => {
        await saveNote(activeNoteId, { title });
        setSaveStatus("saved");
        setTimeout(() => setSaveStatus("idle"), 1500);
      }, SAVE_DEBOUNCE_MS);
    },
    [activeNoteId, saveNote],
  );

  /* ── CodeMirror setup ──────────────────────────────────────────────────── */

  useEffect(() => {
    if (!containerRef.current) return;

    const extensions: Extension[] = [
      keymap.of(defaultKeymap),
      markdown(),
      vaultTheme,
      syntaxHighlighting(mdHighlight),
      EditorView.lineWrapping,
      placeholder("Start writing..."),
      EditorView.updateListener.of((update) => {
        if (update.docChanged) {
          handleContentChange(update.state.doc.toString());
        }
      }),
    ];

    const state = EditorState.create({
      doc: activeNote?.content ?? "",
      extensions,
    });

    const view = new EditorView({ state, parent: containerRef.current });
    viewRef.current = view;

    return () => {
      clearTimeout(saveTimerRef.current);
      view.destroy();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeNoteId]);

  /* ── Keyboard shortcuts ──────────────────────────────────────────────── */

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.shiftKey) {
        if (e.key === "p") {
          e.preventDefault();
          setShowPreview((v) => !v);
        } else if (e.key === "h" || e.key === "H") {
          e.preventDefault();
          toggleHistoryPanel();
        }
      }
    };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [toggleHistoryPanel]);

  /* ── Toolbar command helper ────────────────────────────────────────────── */

  const insertMarkdown = useCallback((before: string, after: string) => {
    const view = viewRef.current;
    if (!view) return;
    const { from, to } = view.state.selection.main;
    const selected = view.state.sliceDoc(from, to);
    view.dispatch({
      changes: { from, to, insert: `${before}${selected}${after}` },
      selection: {
        anchor: from + before.length,
        head: to + before.length,
      },
    });
    view.focus();
  }, []);

  /* ── Empty state ───────────────────────────────────────────────────────── */

  if (!activeNote) {
    return (
      <div className="flex items-center justify-center h-full bg-vault-bg text-vault-muted text-sm select-none">
        <div className="text-center space-y-2">
          <div className="text-2xl opacity-30">&#9998;</div>
          <p>Select or create a note to start writing</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-full bg-vault-bg relative">
      <div className="flex flex-col flex-1 min-w-0">
        {/* Title field */}
        <div className="px-8 pt-8 pb-1 max-w-[72ch] mx-auto w-full">
          <input
            type="text"
            value={activeNote.title}
            onChange={(e) => handleTitleChange(e.target.value)}
            placeholder="Untitled"
            className="w-full bg-transparent text-vault-text text-[28px] font-bold outline-none placeholder:text-vault-border-strong"
          />
        </div>

        {/* Editor + Preview area */}
        <div className="flex-1 flex min-h-0 relative">
          {/* Toolbar hover zone */}
          <div
            className="absolute top-0 left-0 right-0 h-12 z-20"
            onMouseEnter={() => setToolbarVisible(true)}
            onMouseLeave={() => setToolbarVisible(false)}
          >
            <EditorToolbar
              visible={toolbarVisible}
              onCommand={insertMarkdown}
              previewActive={showPreview}
              onTogglePreview={() => setShowPreview((v) => !v)}
              historyActive={historyPanelOpen}
              onToggleHistory={toggleHistoryPanel}
            />
          </div>

          {/* CodeMirror container */}
          <div
            ref={containerRef}
            className={`flex-1 overflow-auto ${showPreview ? "border-r border-vault-border" : ""}`}
          />

          {/* Live preview panel */}
          {showPreview && (
            <div className="flex-1 overflow-auto">
              <MarkdownPreview content={activeNote.content} />
            </div>
          )}

          {/* Version preview overlay */}
          {selectedVersionSha && previewContent !== null && (
            <div className="absolute inset-0 z-10 bg-vault-bg overflow-auto">
              <div className="px-8 pt-6 pb-2 max-w-[72ch] mx-auto">
                <div className="flex items-center gap-2 mb-4">
                  <span className="text-xs font-mono text-vault-muted bg-vault-surface px-2 py-0.5 rounded">
                    {selectedVersionSha.slice(0, 7)}
                  </span>
                  <span className="text-xs text-vault-muted">
                    Read-only preview
                  </span>
                </div>
              </div>
              <div className="px-8 max-w-[72ch] mx-auto">
                <MarkdownPreview content={previewContent} />
              </div>
            </div>
          )}
        </div>

        {/* Save status indicator */}
        {saveStatus !== "idle" && (
          <div className="absolute bottom-3 right-3 text-xs text-vault-muted animate-fade-in">
            {saveStatus === "saving" ? "Saving..." : "Saved"}
          </div>
        )}
      </div>

      {/* History panel */}
      {historyPanelOpen && <HistoryPanel />}
    </div>
  );
}
