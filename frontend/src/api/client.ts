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

// ── AI Frameworks ──────────────────────────────────────────────────────────

export interface AIFrameworkInfo {
  id: string;
  name: string;
  description: string;
  capabilities: string[];
  category: string;
}

export interface AIAskResponse {
  answer: string;
  sources?: string[];
  reasoning?: string;
  framework: string;
}

export interface AIAnalysisResponse {
  category?: string;
  tags?: Array<{ name: string; confidence: number }>;
  complexity?: number;
  summary_sentence?: string;
  entities?: Array<{ name: string; entity_type: string; context: string }>;
  key_concepts?: string[];
  title_suggestion?: string;
  tldr?: string;
  key_points?: string[];
  action_items?: Array<{ task: string; priority: string; deadline?: string }>;
  related_topics?: string[];
  framework: string;
}

export interface AICrewResponse {
  result: string;
  framework: string;
}

export interface AIMemoryResponse {
  memories: Array<{ memory: string; score?: number; metadata?: Record<string, unknown> }>;
  framework: string;
}

export interface AIEnhanceResponse {
  enhanced_content: string;
  changes_made: string[];
  readability_score: number;
  framework: string;
}

export interface AIConnectionResponse {
  connections: Array<{ related_title: string; relationship: string; strength: number }>;
  suggested_tags: string[];
  knowledge_gaps: string[];
  framework: string;
}

export interface AIRoutingInfo {
  ollama: { available: boolean; base_url: string; model: string };
  routing: {
    light_tasks: string[];
    heavy_tasks: string[];
    auto_description: string;
  };
  cloud_models: { openai: string };
}

export interface AIRoutingMeta {
  provider_requested: string;
  provider_used: string;
  model_used: string;
  local_inference: boolean;
  task: string;
}

export function fetchAIFrameworks(): Promise<{ frameworks: AIFrameworkInfo[] }> {
  return request("/api/ai/frameworks");
}

export function fetchAIRoutingInfo(): Promise<AIRoutingInfo> {
  return request("/api/ai/routing-info");
}

// LangChain
export function langchainAsk(
  question: string,
  folderScope?: string,
  provider = "openai",
): Promise<AIAskResponse> {
  return request("/api/ai/langchain/ask", {
    method: "POST",
    body: JSON.stringify({ question, folder_scope: folderScope, provider }),
  });
}

// LlamaIndex
export function llamaIndexQuery(
  question: string,
  folderScope?: string,
  provider = "openai",
): Promise<AIAskResponse> {
  return request("/api/ai/llama-index/query", {
    method: "POST",
    body: JSON.stringify({ question, folder_scope: folderScope, provider }),
  });
}

// CrewAI
export function crewaiResearch(
  question: string,
  provider = "openai",
): Promise<AICrewResponse> {
  return request("/api/ai/crewai/research", {
    method: "POST",
    body: JSON.stringify({ question, provider }),
  });
}

export function crewaiSummarise(
  noteId: string,
  provider = "openai",
): Promise<AICrewResponse> {
  return request("/api/ai/crewai/summarise", {
    method: "POST",
    body: JSON.stringify({ note_id: noteId, provider }),
  });
}

export function crewaiWrite(
  topic: string,
  provider = "openai",
): Promise<AICrewResponse> {
  return request("/api/ai/crewai/write", {
    method: "POST",
    body: JSON.stringify({ topic, provider }),
  });
}

// DSPy
export function dspyAsk(
  question: string,
  folderScope?: string,
  provider = "openai",
): Promise<AIAskResponse> {
  return request("/api/ai/dspy/ask", {
    method: "POST",
    body: JSON.stringify({ question, folder_scope: folderScope, provider }),
  });
}

export function dspySummarise(
  noteId: string,
  provider = "openai",
): Promise<Record<string, string>> {
  return request("/api/ai/dspy/summarise", {
    method: "POST",
    body: JSON.stringify({ note_id: noteId, provider }),
  });
}

export function dspyTopics(
  noteId: string,
  provider = "openai",
): Promise<Record<string, string>> {
  return request("/api/ai/dspy/topics", {
    method: "POST",
    body: JSON.stringify({ note_id: noteId, provider }),
  });
}

// Instructor
export function instructorTags(
  noteId: string,
  provider = "openai",
): Promise<AIAnalysisResponse> {
  return request("/api/ai/instructor/tags", {
    method: "POST",
    body: JSON.stringify({ note_id: noteId, provider }),
  });
}

export function instructorEntities(
  noteId: string,
  provider = "openai",
): Promise<AIAnalysisResponse> {
  return request("/api/ai/instructor/entities", {
    method: "POST",
    body: JSON.stringify({ note_id: noteId, provider }),
  });
}

export function instructorSummary(
  noteId: string,
  provider = "openai",
): Promise<AIAnalysisResponse> {
  return request("/api/ai/instructor/summary", {
    method: "POST",
    body: JSON.stringify({ note_id: noteId, provider }),
  });
}

// Mem0
export function mem0AddMemory(
  content: string,
  userId = "default",
): Promise<{ status: string; framework: string }> {
  return request("/api/ai/mem0/add", {
    method: "POST",
    body: JSON.stringify({ content, user_id: userId }),
  });
}

export function mem0Search(
  query: string,
  userId = "default",
  limit = 5,
): Promise<AIMemoryResponse> {
  return request("/api/ai/mem0/search", {
    method: "POST",
    body: JSON.stringify({ query, user_id: userId, limit }),
  });
}

export function mem0Chat(
  message: string,
  userId = "default",
  provider = "openai",
): Promise<{ answer: string; memories_used: unknown[]; framework: string }> {
  return request("/api/ai/mem0/chat", {
    method: "POST",
    body: JSON.stringify({ message, user_id: userId, provider }),
  });
}

// PydanticAI
export function pydanticAiAsk(
  question: string,
  folderScope?: string,
  provider = "openai",
): Promise<AIAskResponse & { confidence: number; follow_up_questions: string[] }> {
  return request("/api/ai/pydantic-ai/ask", {
    method: "POST",
    body: JSON.stringify({ question, folder_scope: folderScope, provider }),
  });
}

export function pydanticAiEnhance(
  noteId: string,
  provider = "openai",
): Promise<AIEnhanceResponse> {
  return request("/api/ai/pydantic-ai/enhance", {
    method: "POST",
    body: JSON.stringify({ note_id: noteId, provider }),
  });
}

export function pydanticAiConnections(
  noteId: string,
  provider = "openai",
): Promise<AIConnectionResponse> {
  return request("/api/ai/pydantic-ai/connections", {
    method: "POST",
    body: JSON.stringify({ note_id: noteId, provider }),
  });
}
