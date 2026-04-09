import { useEffect, useRef, useCallback, useState, type FC } from "react";
import { useNoteStore } from "@/store/useNoteStore";
import EditorToolbar from "./EditorToolbar";
import MarkdownPreview from "./MarkdownPreview";
import HistoryPanel from "./HistoryPanel";

import { Editor as MilkdownEditor, rootCtx, defaultValueCtx } from "@milkdown/kit/core";
import { commonmark, toggleStrongCommand, toggleEmphasisCommand, toggleInlineCodeCommand, wrapInHeadingCommand, wrapInBulletListCommand, wrapInOrderedListCommand, wrapInBlockquoteCommand, toggleLinkCommand } from "@milkdown/kit/preset/commonmark";
import { gfm } from "@milkdown/kit/preset/gfm";
import { history } from "@milkdown/kit/plugin/history";
import { listener, listenerCtx } from "@milkdown/kit/plugin/listener";
import { callCommand } from "@milkdown/kit/utils";
import { Milkdown, MilkdownProvider, useEditor, useInstance } from "@milkdown/react";

import "@milkdown/kit/prose/view/style/prosemirror.css";

const SAVE_DEBOUNCE_MS = 1200;

type SaveStatus = "idle" | "saving" | "saved";
type ToolbarCommand = "h1" | "h2" | "h3" | "bold" | "italic" | "code" | "bullet-list" | "ordered-list" | "blockquote" | "link";

/* ── Inner editor mounted inside MilkdownProvider ────────────────────────── */

interface InnerEditorProps {
  initialContent: string;
  onChange: (markdown: string) => void;
}

const InnerEditor: FC<InnerEditorProps> = ({ initialContent, onChange }) => {
  const onChangeRef = useRef(onChange);
  onChangeRef.current = onChange;

  useEditor((root) =>
    MilkdownEditor.make()
      .config((ctx) => {
        ctx.set(rootCtx, root);
        ctx.set(defaultValueCtx, initialContent);
        ctx.get(listenerCtx).markdownUpdated((_ctx, md, prevMd) => {
          if (prevMd == null) return;
          onChangeRef.current(md);
        });
      })
      .use(commonmark)
      .use(gfm)
      .use(history)
      .use(listener),
  );

  return <Milkdown />;
};

/* ── Main Editor component ──────────────────────────────────────────────── */

export default function Editor() {
  const saveTimerRef = useRef<ReturnType<typeof setTimeout>>(undefined);
  const titleTimerRef = useRef<ReturnType<typeof setTimeout>>(undefined);
  const contentRef = useRef("");

  const activeNoteId = useNoteStore((s) => s.activeNoteId);
  const notes = useNoteStore((s) => s.notes);
  const saveNote = useNoteStore((s) => s.saveNote);

  const historyPanelOpen = useNoteStore((s) => s.historyPanelOpen);
  const previewContent = useNoteStore((s) => s.previewContent);
  const selectedVersionSha = useNoteStore((s) => s.selectedVersionSha);
  const toggleHistoryPanel = useNoteStore((s) => s.toggleHistoryPanel);

  const activeNote = notes.find((n) => n.id === activeNoteId);

  const [saveStatus, setSaveStatus] = useState<SaveStatus>("idle");
  const [toolbarVisible, setToolbarVisible] = useState(false);
  const [titleDraft, setTitleDraft] = useState(activeNote?.title ?? "");
  const [wordCount, setWordCount] = useState({ words: 0, chars: 0 });

  /* Sync title when note changes */
  useEffect(() => {
    setTitleDraft(activeNote?.title ?? "");
  }, [activeNoteId, activeNote?.title]);

  /* Seed word count from loaded note */
  useEffect(() => {
    const text = activeNote?.content ?? "";
    contentRef.current = text;
    setWordCount({
      words: text.trim() ? text.trim().split(/\s+/).length : 0,
      chars: text.length,
    });
  }, [activeNoteId, activeNote?.content]);

  /* ── Autosave content ────────────────────────────────────────────────── */

  const handleContentChange = useCallback(
    (markdown: string) => {
      if (!activeNoteId) return;
      contentRef.current = markdown;
      setWordCount({
        words: markdown.trim() ? markdown.trim().split(/\s+/).length : 0,
        chars: markdown.length,
      });
      clearTimeout(saveTimerRef.current);
      setSaveStatus("saving");
      saveTimerRef.current = setTimeout(async () => {
        await saveNote(activeNoteId, { content: markdown });
        setSaveStatus("saved");
        setTimeout(() => setSaveStatus("idle"), 1500);
      }, SAVE_DEBOUNCE_MS);
    },
    [activeNoteId, saveNote],
  );

  /* ── Autosave title ──────────────────────────────────────────────────── */

  const handleTitleChange = useCallback(
    (title: string) => {
      if (!activeNoteId) return;
      clearTimeout(titleTimerRef.current);
      if (title === activeNote?.title) {
        setSaveStatus("idle");
        return;
      }
      setSaveStatus("saving");
      titleTimerRef.current = setTimeout(async () => {
        await saveNote(activeNoteId, { title });
        setSaveStatus("saved");
        setTimeout(() => setSaveStatus("idle"), 1500);
      }, SAVE_DEBOUNCE_MS);
    },
    [activeNoteId, activeNote?.title, saveNote],
  );

  /* ── Cleanup save timers ─────────────────────────────────────────────── */

  useEffect(() => {
    return () => {
      clearTimeout(saveTimerRef.current);
      clearTimeout(titleTimerRef.current);
    };
  }, [activeNoteId]);

  /* ── Keyboard shortcuts ──────────────────────────────────────────────── */

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && !e.shiftKey && e.key === "s") {
        e.preventDefault();
        if (!activeNoteId) return;
        clearTimeout(saveTimerRef.current);
        clearTimeout(titleTimerRef.current);
        setSaveStatus("saving");
        saveNote(activeNoteId, { content: contentRef.current, title: titleDraft }).then(() => {
          setSaveStatus("saved");
          setTimeout(() => setSaveStatus("idle"), 1500);
        });
        return;
      }
      if ((e.ctrlKey || e.metaKey) && e.shiftKey && (e.key === "h" || e.key === "H")) {
        e.preventDefault();
        toggleHistoryPanel();
      }
    };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [activeNoteId, titleDraft, saveNote, toggleHistoryPanel]);

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
            value={titleDraft}
            onChange={(e) => {
              const value = e.target.value;
              setTitleDraft(value);
              handleTitleChange(value);
            }}
            placeholder="Untitled"
            className="w-full bg-transparent text-vault-text text-[28px] font-bold outline-none placeholder:text-vault-border-strong"
          />
        </div>

        {/* Editor area */}
        <div className="flex-1 flex min-h-0 relative">
          {/* Toolbar hover zone */}
          <div
            className="absolute top-0 left-0 right-0 h-12 z-20"
            onMouseEnter={() => setToolbarVisible(true)}
            onMouseLeave={() => setToolbarVisible(false)}
          >
            <MilkdownToolbarBridge
              visible={toolbarVisible}
              historyActive={historyPanelOpen}
              onToggleHistory={toggleHistoryPanel}
            />
          </div>

          {/* Milkdown WYSIWYG editor */}
          <div className="flex-1 overflow-auto">
            <MilkdownProvider key={activeNoteId}>
              <InnerEditor
                initialContent={activeNote.content}
                onChange={handleContentChange}
              />
            </MilkdownProvider>
          </div>

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

        {/* Status bar */}
        <div className="flex items-center justify-between px-4 py-1 border-t border-vault-border text-[11px] text-vault-muted tabular-nums select-none">
          <div className="flex gap-3">
            <span>{wordCount.words} {wordCount.words === 1 ? "word" : "words"}</span>
            <span>{wordCount.chars} {wordCount.chars === 1 ? "char" : "chars"}</span>
          </div>
          <div className="animate-fade-in">
            {saveStatus === "saving" ? "Saving..." : saveStatus === "saved" ? "Saved" : ""}
          </div>
        </div>
      </div>

      {/* History panel */}
      {historyPanelOpen && <HistoryPanel />}
    </div>
  );
}

/* ── Toolbar bridge: reads Milkdown instance, dispatches commands ────────── */

interface ToolbarBridgeProps {
  visible: boolean;
  historyActive: boolean;
  onToggleHistory: () => void;
}

const MilkdownToolbarBridge: FC<ToolbarBridgeProps> = ({ visible, historyActive, onToggleHistory }) => {
  const [, getEditor] = useInstance();

  const handleCommand = useCallback(
    (command: ToolbarCommand) => {
      const editor = getEditor();
      if (!editor) return;
      switch (command) {
        case "h1":
          editor.action(callCommand(wrapInHeadingCommand.key, 1));
          break;
        case "h2":
          editor.action(callCommand(wrapInHeadingCommand.key, 2));
          break;
        case "h3":
          editor.action(callCommand(wrapInHeadingCommand.key, 3));
          break;
        case "bold":
          editor.action(callCommand(toggleStrongCommand.key));
          break;
        case "italic":
          editor.action(callCommand(toggleEmphasisCommand.key));
          break;
        case "code":
          editor.action(callCommand(toggleInlineCodeCommand.key));
          break;
        case "bullet-list":
          editor.action(callCommand(wrapInBulletListCommand.key));
          break;
        case "ordered-list":
          editor.action(callCommand(wrapInOrderedListCommand.key));
          break;
        case "blockquote":
          editor.action(callCommand(wrapInBlockquoteCommand.key));
          break;
        case "link": {
          const href = prompt("Enter URL:");
          if (href) {
            editor.action(callCommand(toggleLinkCommand.key, { href }));
          }
          break;
        }
      }
    },
    [getEditor],
  );

  return (
    <EditorToolbar
      visible={visible}
      onCommand={handleCommand}
      historyActive={historyActive}
      onToggleHistory={onToggleHistory}
    />
  );
};
