import { useEffect, useState, useCallback } from "react";
import { useNoteStore } from "@/store/useNoteStore";
import SidebarFolder from "./SidebarFolder";
import SidebarNote from "./SidebarNote";
import ContextMenu, { type MenuItem } from "./ContextMenu";

/* ── Icons ──────────────────────────────────────────────────────────────── */

function PlusIcon() {
  return (
    <svg
      width="14"
      height="14"
      viewBox="0 0 14 14"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.6"
      strokeLinecap="round"
    >
      <path d="M7 2V12M2 7H12" />
    </svg>
  );
}

function FolderPlusIcon() {
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
    >
      <path d="M2 4.5V12.5H14V6.5H8L6.5 4.5H2Z" />
      <path d="M8 8.5V10.5M7 9.5H9" />
    </svg>
  );
}

/* ── Component ──────────────────────────────────────────────────────────── */

export default function Sidebar() {
  const {
    notes,
    folders,
    activeNoteId,
    activeFolderId,
    openFolderIds,
    load,
    setActiveNote,
    setActiveFolder,
    toggleFolder,
    addNote,
    addFolder,
    saveNote,
    removeNote,
    renameFolder,
    removeFolder,
    moveNote,
  } = useNoteStore();

  const [contextMenu, setContextMenu] = useState<{
    x: number;
    y: number;
    items: MenuItem[];
  } | null>(null);

  useEffect(() => {
    load();
  }, [load]);

  const handleNewNote = useCallback(() => addNote(), [addNote]);

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === "n") {
        e.preventDefault();
        handleNewNote();
      }
    };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [handleNewNote]);

  const handleNewFolder = () => {
    const name = prompt("Folder name:");
    if (name?.trim()) addFolder(name.trim(), activeFolderId ?? undefined);
  };

  const handleFolderContextMenu = (e: React.MouseEvent, folderId: string) => {
    e.preventDefault();
    setContextMenu({
      x: e.clientX,
      y: e.clientY,
      items: [
        {
          label: "New Note",
          onClick: () => {
            const prev = useNoteStore.getState().activeFolderId;
            setActiveFolder(folderId);
            addNote().then(() => {
              if (prev !== folderId) setActiveFolder(prev);
            });
          },
        },
        {
          label: "New Folder",
          onClick: () => {
            const name = prompt("Sub-folder name:");
            if (name?.trim()) addFolder(name.trim(), folderId);
          },
        },
        {
          label: "Rename",
          onClick: () => {
            const current = folders.find((f) => f.id === folderId);
            const name = prompt("Rename folder:", current?.name);
            if (name?.trim()) renameFolder(folderId, name.trim());
          },
        },
        {
          label: "Delete",
          onClick: () => {
            if (confirm("Delete this folder and all its contents?")) {
              removeFolder(folderId);
            }
          },
        },
      ],
    });
  };

  const handleNoteContextMenu = (e: React.MouseEvent, noteId: string) => {
    e.preventDefault();
    setContextMenu({
      x: e.clientX,
      y: e.clientY,
      items: [
        {
          label: "Rename",
          onClick: () => {
            const note = notes.find((n) => n.id === noteId);
            const title = prompt("Rename note:", note?.title);
            if (title?.trim()) saveNote(noteId, { title: title.trim() });
          },
        },
        {
          label: "Delete",
          onClick: () => {
            if (confirm("Delete this note?")) removeNote(noteId);
          },
        },
      ],
    });
  };

  const handleBackgroundContextMenu = (e: React.MouseEvent) => {
    if (e.target !== e.currentTarget) return;
    e.preventDefault();
    setContextMenu({
      x: e.clientX,
      y: e.clientY,
      items: [
        { label: "New Note", onClick: () => addNote() },
        { label: "New Folder", onClick: handleNewFolder },
      ],
    });
  };

  const handleBackgroundDrop = (e: React.DragEvent) => {
    e.preventDefault();
    const noteId = e.dataTransfer.getData("text/note-id");
    if (noteId) moveNote(noteId, null);
  };

  const rootFolders = folders.filter((f) => !f.parent_id);
  const rootNotes = notes.filter((n) => !n.folder_id);

  return (
    <aside className="flex flex-col h-full w-60 border-r border-vault-border bg-vault-surface select-none">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3">
        <h1 className="text-[13px] font-semibold text-vault-text-secondary tracking-wide">
          NoteGuy
        </h1>
        <div className="flex gap-0.5">
          <button
            onClick={handleNewFolder}
            className="p-1.5 rounded-md text-vault-muted hover:text-vault-text hover:bg-vault-surface-hover transition-colors"
            title="New Folder"
          >
            <FolderPlusIcon />
          </button>
          <button
            onClick={handleNewNote}
            className="p-1.5 rounded-md text-vault-muted hover:text-vault-text hover:bg-vault-surface-hover transition-colors"
            title="New Note (Ctrl+N)"
          >
            <PlusIcon />
          </button>
        </div>
      </div>

      {/* All Notes shortcut */}
      <button
        onClick={() => setActiveFolder(null)}
        className={`mx-2 px-3 py-1.5 text-left text-[13px] rounded-md transition-colors ${
          activeFolderId === null
            ? "bg-vault-accent-subtle text-vault-accent"
            : "text-vault-text-secondary hover:text-vault-text hover:bg-vault-surface-hover"
        }`}
      >
        All Notes
      </button>

      {/* Folder tree + root notes */}
      <nav
        className="flex-1 overflow-y-auto px-2 py-2 space-y-0.5"
        onContextMenu={handleBackgroundContextMenu}
        onDragOver={(e) => e.preventDefault()}
        onDrop={handleBackgroundDrop}
      >
        {rootFolders.map((folder) => (
          <SidebarFolder
            key={folder.id}
            folder={folder}
            folders={folders}
            notes={notes}
            activeFolderId={activeFolderId}
            activeNoteId={activeNoteId}
            isOpen={openFolderIds.includes(folder.id)}
            openFolderIds={openFolderIds}
            onToggle={toggleFolder}
            onSelectFolder={setActiveFolder}
            onSelectNote={setActiveNote}
            onFolderContextMenu={handleFolderContextMenu}
            onNoteContextMenu={handleNoteContextMenu}
            onMoveNote={(noteId, folderId) => moveNote(noteId, folderId)}
          />
        ))}

        {rootNotes.map((note) => (
          <SidebarNote
            key={note.id}
            note={note}
            isActive={note.id === activeNoteId}
            onSelect={setActiveNote}
            onContextMenu={handleNoteContextMenu}
          />
        ))}
      </nav>

      {contextMenu && (
        <ContextMenu
          x={contextMenu.x}
          y={contextMenu.y}
          items={contextMenu.items}
          onClose={() => setContextMenu(null)}
        />
      )}
    </aside>
  );
}
