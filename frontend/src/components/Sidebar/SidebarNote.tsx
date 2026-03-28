import type { NoteData } from "@/api/client";

/* ── SVG Icon ───────────────────────────────────────────────────────────── */

function FileIcon() {
  return (
    <svg
      width="16"
      height="16"
      viewBox="0 0 16 16"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className="shrink-0"
    >
      <path d="M4.5 2H10L12 4.5V14H4.5V2Z" />
      <path d="M10 2V4.5H12" />
    </svg>
  );
}

/* ── Component ──────────────────────────────────────────────────────────── */

interface SidebarNoteProps {
  note: NoteData;
  isActive: boolean;
  depth?: number;
  onSelect: (id: string) => void;
  onContextMenu: (e: React.MouseEvent, noteId: string) => void;
}

export default function SidebarNote({
  note,
  isActive,
  depth = 0,
  onSelect,
  onContextMenu,
}: SidebarNoteProps) {
  return (
    <button
      draggable
      onDragStart={(e) => {
        e.dataTransfer.setData("text/note-id", note.id);
        e.dataTransfer.effectAllowed = "move";
      }}
      onClick={() => onSelect(note.id)}
      onContextMenu={(e) => onContextMenu(e, note.id)}
      className={`w-full flex items-center gap-1.5 px-2 py-1 rounded text-sm transition-colors duration-150 ${
        isActive
          ? "bg-vault-accent/10 text-vault-accent font-medium"
          : "text-vault-muted hover:text-vault-text hover:bg-vault-border/40"
      }`}
      style={{ paddingLeft: `${depth * 12 + 20}px` }}
    >
      <FileIcon />
      <span className="truncate font-mono text-[13px]">
        {note.title || "Untitled"}
      </span>
    </button>
  );
}
