import { useState } from "react";
import type { FolderData, NoteData } from "@/api/client";
import SidebarNote from "./SidebarNote";

/* ── SVG Icons ──────────────────────────────────────────────────────────── */

function ChevronIcon({ open }: { open: boolean }) {
  return (
    <svg
      width="12"
      height="12"
      viewBox="0 0 12 12"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={`shrink-0 transition-transform duration-150 ${open ? "rotate-90" : ""}`}
    >
      <path d="M4.5 2.5L7.5 6L4.5 9.5" />
    </svg>
  );
}

function FolderIcon({ open }: { open: boolean }) {
  return (
    <svg
      width="16"
      height="16"
      viewBox="0 0 16 16"
      fill={open ? "currentColor" : "none"}
      fillOpacity={open ? 0.2 : 0}
      stroke="currentColor"
      strokeWidth="1.2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className="shrink-0"
    >
      <path d="M2 4.5V12.5H14V6.5H8L6.5 4.5H2Z" />
    </svg>
  );
}

/* ── Component ──────────────────────────────────────────────────────────── */

interface SidebarFolderProps {
  folder: FolderData;
  folders: FolderData[];
  notes: NoteData[];
  activeFolderId: string | null;
  activeNoteId: string | null;
  isOpen: boolean;
  openFolderIds: string[];
  depth?: number;
  onToggle: (id: string) => void;
  onSelectFolder: (id: string) => void;
  onSelectNote: (id: string) => void;
  onFolderContextMenu: (e: React.MouseEvent, folderId: string) => void;
  onNoteContextMenu: (e: React.MouseEvent, noteId: string) => void;
  onMoveNote: (noteId: string, folderId: string) => void;
}

export default function SidebarFolder({
  folder,
  folders,
  notes,
  activeFolderId,
  activeNoteId,
  isOpen,
  openFolderIds,
  depth = 0,
  onToggle,
  onSelectFolder,
  onSelectNote,
  onFolderContextMenu,
  onNoteContextMenu,
  onMoveNote,
}: SidebarFolderProps) {
  const [isDragOver, setIsDragOver] = useState(false);

  const children = folders.filter((f) => f.parent_id === folder.id);
  const folderNotes = notes.filter((n) => n.folder_id === folder.id);
  const isActive = activeFolderId === folder.id;

  const handleClick = () => {
    onSelectFolder(folder.id);
    onToggle(folder.id);
  };

  return (
    <div>
      {/* Folder row */}
      <button
        onClick={handleClick}
        onContextMenu={(e) => onFolderContextMenu(e, folder.id)}
        onDragOver={(e) => {
          e.preventDefault();
          e.stopPropagation();
          setIsDragOver(true);
        }}
        onDragLeave={() => setIsDragOver(false)}
        onDrop={(e) => {
          e.preventDefault();
          e.stopPropagation();
          setIsDragOver(false);
          const noteId = e.dataTransfer.getData("text/note-id");
          if (noteId) onMoveNote(noteId, folder.id);
        }}
        className={`w-full flex items-center gap-1.5 px-2 py-1 rounded text-sm transition-colors duration-150 ${
          isActive
            ? "bg-vault-accent/10 text-vault-accent"
            : "text-vault-muted hover:text-vault-text hover:bg-vault-border/40"
        } ${isDragOver ? "ring-1 ring-vault-accent bg-vault-accent/20" : ""}`}
        style={{ paddingLeft: `${depth * 12 + 8}px` }}
      >
        <ChevronIcon open={isOpen} />
        <FolderIcon open={isOpen} />
        <span className="truncate">{folder.name}</span>
      </button>

      {/* Expanded children */}
      {isOpen && (
        <div className="transition-all duration-150">
          {children.map((child) => (
            <SidebarFolder
              key={child.id}
              folder={child}
              folders={folders}
              notes={notes}
              activeFolderId={activeFolderId}
              activeNoteId={activeNoteId}
              isOpen={openFolderIds.includes(child.id)}
              openFolderIds={openFolderIds}
              depth={depth + 1}
              onToggle={onToggle}
              onSelectFolder={onSelectFolder}
              onSelectNote={onSelectNote}
              onFolderContextMenu={onFolderContextMenu}
              onNoteContextMenu={onNoteContextMenu}
              onMoveNote={onMoveNote}
            />
          ))}
          {folderNotes.map((note) => (
            <SidebarNote
              key={note.id}
              note={note}
              isActive={note.id === activeNoteId}
              depth={depth + 1}
              onSelect={onSelectNote}
              onContextMenu={onNoteContextMenu}
            />
          ))}
        </div>
      )}
    </div>
  );
}
