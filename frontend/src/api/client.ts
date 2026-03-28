/**
 * Typed HTTP client for the NoteGuy backend API.
 *
 * All fetch calls go through the Vite dev-server proxy so no absolute
 * URLs are needed — just prefix paths with `/api`.
 */

export interface NoteData {
  id: string;
  title: string;
  content: string;
  folder_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface FolderData {
  id: string;
  name: string;
  parent_id: string | null;
  path: string;
  created_at: string;
  updated_at: string;
}

export interface ChatResponse {
  answer: string;
  sources: string[];
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!response.ok) {
    throw new Error(`API error ${response.status}: ${response.statusText}`);
  }
  if (response.status === 204) return undefined as T;
  return response.json();
}

// ── Notes ───────────────────────────────────────────────────────────────────

export function fetchNotes(folderId?: string): Promise<NoteData[]> {
  const query = folderId ? `?folder_id=${folderId}` : "";
  return request(`/api/notes${query}`);
}

export function fetchNote(id: string): Promise<NoteData> {
  return request(`/api/notes/${id}`);
}

export function createNote(body: Partial<NoteData>): Promise<NoteData> {
  return request("/api/notes", { method: "POST", body: JSON.stringify(body) });
}

export function updateNote(
  id: string,
  body: Partial<NoteData>,
): Promise<NoteData> {
  return request(`/api/notes/${id}`, {
    method: "PATCH",
    body: JSON.stringify(body),
  });
}

export function deleteNote(id: string): Promise<void> {
  return request(`/api/notes/${id}`, { method: "DELETE" });
}

// ── Folders ─────────────────────────────────────────────────────────────────

export function fetchFolders(): Promise<FolderData[]> {
  return request("/api/folders");
}

export function createFolder(body: Partial<FolderData>): Promise<FolderData> {
  return request("/api/folders", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function updateFolder(
  id: string,
  body: Partial<FolderData>,
): Promise<FolderData> {
  return request(`/api/folders/${id}`, {
    method: "PATCH",
    body: JSON.stringify(body),
  });
}

export function deleteFolder(id: string): Promise<void> {
  return request(`/api/folders/${id}`, { method: "DELETE" });
}

// ── History ──────────────────────────────────────────────────────────────────

export interface VersionEntry {
  sha: string;
  short_sha: string;
  message: string;
  author: string;
  timestamp: string;
}

export interface VersionContent {
  sha: string;
  content: string;
}

export interface DiffResponse {
  sha: string;
  diff: string;
}

export function fetchNoteHistory(noteId: string): Promise<VersionEntry[]> {
  return request(`/api/notes/${noteId}/history`);
}

export function fetchNoteVersion(
  noteId: string,
  sha: string,
): Promise<VersionContent> {
  return request(`/api/notes/${noteId}/versions/${sha}`);
}

export function fetchNoteDiff(
  noteId: string,
  sha: string,
): Promise<DiffResponse> {
  return request(`/api/notes/${noteId}/diff/${sha}`);
}

export function restoreNoteVersion(
  noteId: string,
  sha: string,
): Promise<NoteData> {
  return request(`/api/notes/${noteId}/restore`, {
    method: "POST",
    body: JSON.stringify({ sha }),
  });
}

// ── Chat ────────────────────────────────────────────────────────────────────

export function sendChatMessage(
  message: string,
  folderId?: string,
): Promise<ChatResponse> {
  return request("/api/chat", {
    method: "POST",
    body: JSON.stringify({ message, folder_id: folderId }),
  });
}
