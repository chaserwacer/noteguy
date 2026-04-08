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

// ── Notes ───────��───────────────────────────────────────────────────────────

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

// ── Chat ───────────────────────────────────────���────────────────────────────

export function sendChatMessage(
  message: string,
  folderId?: string,
): Promise<ChatResponse> {
  return request("/api/chat", {
    method: "POST",
    body: JSON.stringify({ message, folder_id: folderId }),
  });
}

// ── Unified AI API ──────��───────────────────────────────────────────────────

export interface AICapability {
  id: string;
  name: string;
  description: string;
  icon: string;
}

export interface AIStatusResponse {
  engine: string;
  version: string;
  capabilities: AICapability[];
  config: {
    llm_model: string;
    embedding_model: string;
    embedding_dimension: number;
    raganything_available: boolean;
    raganything_parser: string | null;
  };
}

export interface AIQueryResponse {
  answer: string;
  mode: string;
}

export interface AIAnalyzeResponse {
  answer: string;
  context: string | Record<string, unknown>;
}

export interface AIExtractResponse {
  query: string;
  mode: string;
  context: string | Record<string, unknown>;
  note_id?: string;
}

export interface AIKGStatsResponse {
  entities: number;
  relations: number;
}

export interface AIIngestResponse {
  status: string;
  note_id?: string;
  doc_id?: string;
  title?: string;
  indexed?: number;
  skipped?: number;
  error?: string;
}

export function fetchAIStatus(): Promise<AIStatusResponse> {
  return request("/api/ai/status");
}

export function aiQuery(
  question: string,
  conversationHistory: { role: string; content: string }[] = [],
  responseType = "Multiple Paragraphs",
  topK?: number,
): Promise<AIQueryResponse> {
  return request("/api/ai/query", {
    method: "POST",
    body: JSON.stringify({
      question,
      mode: "hybrid",
      conversation_history: conversationHistory,
      response_type: responseType,
      top_k: topK,
    }),
  });
}

export function aiAnalyze(
  question: string,
  responseType = "Multiple Paragraphs",
  topK?: number,
): Promise<AIAnalyzeResponse> {
  return request("/api/ai/analyze", {
    method: "POST",
    body: JSON.stringify({
      question,
      response_type: responseType,
      top_k: topK,
    }),
  });
}

export function aiExtract(question: string): Promise<AIExtractResponse> {
  return request("/api/ai/extract", {
    method: "POST",
    body: JSON.stringify({ question, mode: "local" }),
  });
}

export function aiExtractNote(noteId: string): Promise<AIExtractResponse> {
  return request("/api/ai/extract/note", {
    method: "POST",
    body: JSON.stringify({ note_id: noteId }),
  });
}

export function aiIngestNote(noteId: string): Promise<AIIngestResponse> {
  return request("/api/ai/ingest/note", {
    method: "POST",
    body: JSON.stringify({ note_id: noteId }),
  });
}

export function aiIngestAll(): Promise<AIIngestResponse> {
  return request("/api/ai/ingest/all", { method: "POST" });
}

export async function aiIngestDocument(
  file: File,
  folderId?: string,
): Promise<AIIngestResponse> {
  const formData = new FormData();
  formData.append("file", file);
  if (folderId) formData.append("folder_id", folderId);

  const response = await fetch("/api/ai/ingest/document", {
    method: "POST",
    body: formData,
  });
  if (!response.ok) {
    throw new Error(`API error ${response.status}: ${response.statusText}`);
  }
  return response.json();
}

export function aiKGStats(): Promise<AIKGStatsResponse> {
  return request("/api/ai/kg/stats");
}

export interface KGGraphNode {
  id: string;
  label: string;
  type: string;
  description: string;
  degree: number;
}

export interface KGGraphEdge {
  id: string;
  source: string;
  target: string;
  label: string;
  weight: number;
}

export interface KGGraphResponse {
  nodes: KGGraphNode[];
  edges: KGGraphEdge[];
}

export function aiKGGraph(limit = 200): Promise<KGGraphResponse> {
  return request(`/api/ai/kg/graph?limit=${limit}`);
}

export function aiDeleteDocument(docId: string): Promise<{ status: string }> {
  return request("/api/ai/kg/document", {
    method: "DELETE",
    body: JSON.stringify({ doc_id: docId }),
  });
}

// ── Settings API ───────────────────────────────────────────────────────────

export interface AISettingsResponse {
  llm_model: string;
  embedding_model: string;
  embedding_dimension: number;
  vision_model: string;
  openai_api_key_set: boolean;
}

export interface AISettingsUpdate {
  llm_model?: string;
  embedding_model?: string;
  embedding_dimension?: number;
  vision_model?: string;
  openai_api_key?: string;
}

export function fetchAISettings(): Promise<AISettingsResponse> {
  return request("/api/settings");
}

export function updateAISettings(
  body: AISettingsUpdate,
): Promise<AISettingsResponse> {
  return request("/api/settings", {
    method: "PUT",
    body: JSON.stringify(body),
  });
}
