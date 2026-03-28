import type { NoteData } from "@/api/client";

function FileIcon() {
  return (
    <svg
      width="15"
      height="15"
      viewBox="0 0 16 16"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className="shrink-0 opacity-60"
    >
      <path d="M4.5 2H10L12 4.5V14H4.5V2Z" />
      <path d="M10 2V4.5H12" />
    </svg>
  );
}

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
      className={`w-full flex items-center gap-2 px-2.5 py-1 rounded-md text-[13px] transition-colors ${
        isActive
          ? "bg-vault-accent-subtle text-vault-accent font-medium"
          : "text-vault-text-secondary hover:text-vault-text hover:bg-vault-surface-hover"
      }`}
      style={{ paddingLeft: `${depth * 12 + 20}px` }}
    >
      <FileIcon />
      <span className="truncate">
        {note.title || "Untitled"}
      </span>
    </button>
  );
}
