import { create } from "zustand";
import {
  fetchNotes,
  fetchFolders,
  createNote,
  updateNote,
  deleteNote,
  createFolder,
  updateFolder,
  deleteFolder,
  type NoteData,
  type FolderData,
} from "@/api/client";

interface NoteStore {
  notes: NoteData[];
  folders: FolderData[];
  activeNoteId: string | null;
  activeFolderId: string | null;
  /** IDs of folders that are expanded in the tree. */
  openFolderIds: string[];

  /** Fetch all notes and folders from the API. */
  load: () => Promise<void>;

  setActiveNote: (id: string | null) => void;
  setActiveFolder: (id: string | null) => void;
  /** Toggle a folder open/closed in the sidebar tree. */
  toggleFolder: (id: string) => void;

  addNote: (title?: string) => Promise<NoteData>;
  saveNote: (id: string, patch: Partial<NoteData>) => Promise<void>;
  removeNote: (id: string) => Promise<void>;
  /** Move a note into a different folder (or root when folderId is null). */
  moveNote: (noteId: string, folderId: string | null) => Promise<void>;

  addFolder: (name: string, parentId?: string) => Promise<FolderData>;
  renameFolder: (id: string, name: string) => Promise<void>;
  removeFolder: (id: string) => Promise<void>;
}

export const useNoteStore = create<NoteStore>((set, get) => ({
  notes: [],
  folders: [],
  activeNoteId: null,
  activeFolderId: null,
  openFolderIds: [],

  async load() {
    const [notes, folders] = await Promise.all([
      fetchNotes(),
      fetchFolders(),
    ]);
    set({ notes, folders });
  },

  setActiveNote(id) {
    set({ activeNoteId: id });
  },

  setActiveFolder(id) {
    set({ activeFolderId: id });
  },

  toggleFolder(id) {
    set((s) => ({
      openFolderIds: s.openFolderIds.includes(id)
        ? s.openFolderIds.filter((fid) => fid !== id)
        : [...s.openFolderIds, id],
    }));
  },

  async addNote(title = "Untitled") {
    const note = await createNote({
      title,
      folder_id: get().activeFolderId,
    });
    set((s) => ({ notes: [note, ...s.notes], activeNoteId: note.id }));
    // Auto-expand the parent folder so the new note is visible
    const fid = note.folder_id;
    if (fid && !get().openFolderIds.includes(fid)) {
      set((s) => ({ openFolderIds: [...s.openFolderIds, fid] }));
    }
    return note;
  },

  async saveNote(id, patch) {
    const updated = await updateNote(id, patch);
    set((s) => ({
      notes: s.notes.map((n) => (n.id === id ? updated : n)),
    }));
  },

  async removeNote(id) {
    await deleteNote(id);
    set((s) => ({
      notes: s.notes.filter((n) => n.id !== id),
      activeNoteId: s.activeNoteId === id ? null : s.activeNoteId,
    }));
  },

  async moveNote(noteId, folderId) {
    const updated = await updateNote(noteId, { folder_id: folderId } as Partial<NoteData>);
    set((s) => ({
      notes: s.notes.map((n) => (n.id === noteId ? updated : n)),
    }));
  },

  async addFolder(name, parentId) {
    const folder = await createFolder({ name, parent_id: parentId ?? null });
    set((s) => ({ folders: [...s.folders, folder] }));
    // Auto-expand parent so the new folder is visible
    if (parentId && !get().openFolderIds.includes(parentId)) {
      set((s) => ({ openFolderIds: [...s.openFolderIds, parentId] }));
    }
    return folder;
  },

  async renameFolder(id, name) {
    const updated = await updateFolder(id, { name });
    set((s) => ({
      folders: s.folders.map((f) => (f.id === id ? updated : f)),
    }));
  },

  async removeFolder(id) {
    await deleteFolder(id);
    // Remove the folder and any notes that were inside it (cascade on backend)
    set((s) => {
      const removedIds = new Set([id]);
      // Also remove child folders from local state
      const collectChildren = (parentId: string) => {
        s.folders.forEach((f) => {
          if (f.parent_id === parentId) {
            removedIds.add(f.id);
            collectChildren(f.id);
          }
        });
      };
      collectChildren(id);

      return {
        folders: s.folders.filter((f) => !removedIds.has(f.id)),
        notes: s.notes.filter((n) => !n.folder_id || !removedIds.has(n.folder_id)),
        activeFolderId: removedIds.has(s.activeFolderId ?? "")
          ? null
          : s.activeFolderId,
        activeNoteId:
          s.notes.find((n) => n.id === s.activeNoteId && n.folder_id && removedIds.has(n.folder_id))
            ? null
            : s.activeNoteId,
        openFolderIds: s.openFolderIds.filter((fid) => !removedIds.has(fid)),
      };
    });
  },
}));
