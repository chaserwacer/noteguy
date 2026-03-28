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

const SAVE_DEBOUNCE_MS = 800;

/* ── Syntax highlight style ──────────────────────────────────────────────── */

const mdHighlight = HighlightStyle.define([
  { tag: tags.heading1, color: "#7aa2f7", fontWeight: "700", fontSize: "1.6em" },
  { tag: tags.heading2, color: "#7aa2f7", fontWeight: "600", fontSize: "1.35em" },
  { tag: tags.heading3, color: "#7aa2f7", fontWeight: "600", fontSize: "1.15em" },
  { tag: tags.heading4, color: "#7aa2f7", fontWeight: "500" },
  { tag: tags.strong, color: "#c0caf5", fontWeight: "700" },
  { tag: tags.emphasis, color: "#c0caf5", fontStyle: "italic" },
  { tag: tags.monospace, color: "#9ece6a", fontFamily: "'JetBrains Mono', monospace" },
  { tag: tags.link, color: "#89b4fa", textDecoration: "underline" },
  { tag: tags.url, color: "#565f89" },
  { tag: tags.quote, color: "#565f89", fontStyle: "italic" },
  { tag: tags.processingInstruction, color: "#565f89" }, // markdown markers like **, #, etc.
]);

/* ── Editor theme ────────────────────────────────────────────────────────── */

const vaultTheme = EditorView.theme(
  {
    "&": {
      backgroundColor: "#16161e",
      color: "#c0caf5",
      fontFamily: "'JetBrains Mono', monospace",
      fontSize: "14px",
      lineHeight: "1.8",
      height: "100%",
    },
    ".cm-content": {
      padding: "1.5rem 2rem",
      caretColor: "#7aa2f7",
      maxWidth: "72ch",
      marginLeft: "auto",
      marginRight: "auto",
    },
    ".cm-cursor": {
      borderLeftColor: "#7aa2f7",
    },
    "&.cm-focused .cm-selectionBackground, .cm-selectionBackground": {
      backgroundColor: "#3b4261",
    },
    ".cm-gutters": {
      display: "none",
    },
    ".cm-scroller": {
      overflow: "auto",
    },
    ".cm-placeholder": {
      color: "#3b4261",
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

  const activeNote = notes.find((n) => n.id === activeNoteId);

  const [saveStatus, setSaveStatus] = useState<SaveStatus>("idle");
  const [showPreview, setShowPreview] = useState(false);
  const [toolbarVisible, setToolbarVisible] = useState(false);

  /* ── Autosave content (800ms debounce) ─────────────────────────────────── */

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

  /* ── Autosave title (800ms debounce) ───────────────────────────────────── */

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
    // Re-create when note changes
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeNoteId]);

  /* ── Keyboard shortcut: Cmd/Ctrl+Shift+P → toggle preview ─────────────── */

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key === "p") {
        e.preventDefault();
        setShowPreview((v) => !v);
      }
    };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, []);

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
      <div className="flex items-center justify-center h-full bg-[#16161e] text-vault-muted text-sm">
        Select or create a note to start writing.
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full bg-[#16161e] relative">
      {/* Title field */}
      <div className="px-8 pt-6 pb-2 max-w-[72ch] mx-auto w-full">
        <input
          type="text"
          value={activeNote.title}
          onChange={(e) => handleTitleChange(e.target.value)}
          placeholder="Untitled"
          className="w-full bg-transparent text-vault-text text-2xl font-semibold outline-none placeholder:text-vault-border font-mono"
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
      </div>

      {/* Save status indicator */}
      {saveStatus !== "idle" && (
        <div className="absolute bottom-3 right-3 text-xs text-vault-muted">
          {saveStatus === "saving" ? "Saving..." : "Saved"}
        </div>
      )}
    </div>
  );
}
