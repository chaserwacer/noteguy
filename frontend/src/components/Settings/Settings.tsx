import { useState, useEffect, useCallback, type FC } from "react";
import {
  fetchAISettings,
  updateAISettings,
  type AISettingsResponse,
  type AISettingsUpdate,
} from "@/api/client";

// ── Spinner ─────────────────────────────────────────────────────────────────

const Spinner: FC = () => (
  <svg
    className="animate-spin h-4 w-4 text-vault-muted"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
  >
    <circle cx="12" cy="12" r="10" opacity="0.25" />
    <path d="M12 2a10 10 0 019.95 9" opacity="0.75" />
  </svg>
);

// ── Main component ──────────────────────────────────────────────────────────

interface SettingsProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function Settings({ isOpen, onClose }: SettingsProps) {
  const [settings, setSettings] = useState<AISettingsResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  // Form state
  const [llmModel, setLlmModel] = useState("");
  const [embeddingModel, setEmbeddingModel] = useState("");
  const [embeddingDimension, setEmbeddingDimension] = useState(3072);
  const [visionModel, setVisionModel] = useState("");
  const [openaiApiKey, setOpenaiApiKey] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchAISettings();
      setSettings(data);
      setLlmModel(data.llm_model);
      setEmbeddingModel(data.embedding_model);
      setEmbeddingDimension(data.embedding_dimension);
      setVisionModel(data.vision_model);
      setOpenaiApiKey("");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load settings");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (isOpen) load();
  }, [isOpen, load]);

  const handleSave = useCallback(async () => {
    setSaving(true);
    setError(null);
    setSuccess(null);
    try {
      const update: AISettingsUpdate = {
        llm_model: llmModel,
        embedding_model: embeddingModel,
        embedding_dimension: embeddingDimension,
        vision_model: visionModel,
      };
      if (openaiApiKey.trim()) {
        update.openai_api_key = openaiApiKey.trim();
      }
      const updated = await updateAISettings(update);
      setSettings(updated);
      setSuccess("Settings saved. AI services reinitialized.");
      setOpenaiApiKey("");
      setTimeout(() => setSuccess(null), 4000);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to save settings");
    } finally {
      setSaving(false);
    }
  }, [llmModel, embeddingModel, embeddingDimension, visionModel, openaiApiKey]);

  if (!isOpen) return null;

  const inputCls =
    "w-full px-3 py-2 rounded-md bg-vault-bg border border-vault-border text-sm text-vault-text placeholder-vault-muted focus:outline-none focus:ring-1 focus:ring-vault-accent";
  const labelCls = "block text-xs font-medium text-vault-text-secondary mb-1";

  return (
    <div className="fixed inset-0 z-50 bg-vault-bg/80 backdrop-blur-sm animate-fade-in">
      <div className="absolute inset-y-4 right-4 w-[420px] bg-vault-surface border border-vault-border rounded-xl shadow-modal-full overflow-hidden flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-3 border-b border-vault-border/70 bg-gradient-to-r from-vault-surface to-vault-bg/60">
          <div>
            <p className="text-sm font-semibold text-vault-text">AI Settings</p>
            <p className="text-[11px] text-vault-text-secondary">
              Configure your OpenAI models
            </p>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-md text-vault-muted hover:text-vault-text hover:bg-vault-surface-hover transition-colors"
          >
            <svg className="w-4 h-4" viewBox="0 0 16 16" fill="currentColor">
              <path d="M3.72 3.72a.75.75 0 011.06 0L8 6.94l3.22-3.22a.75.75 0 111.06 1.06L9.06 8l3.22 3.22a.75.75 0 11-1.06 1.06L8 9.06l-3.22 3.22a.75.75 0 01-1.06-1.06L6.94 8 3.72 4.78a.75.75 0 010-1.06z" />
            </svg>
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto px-5 py-4 space-y-5">
          {loading && (
            <div className="flex items-center gap-2 text-vault-muted text-sm">
              <Spinner /> Loading settings...
            </div>
          )}

          {error && (
            <div className="text-red-400 text-sm bg-red-400/10 rounded-md px-3 py-2">
              {error}
            </div>
          )}

          {success && (
            <div className="text-green-400 text-sm bg-green-400/10 rounded-md px-3 py-2">
              {success}
            </div>
          )}

          {!loading && settings && (
            <>
              {/* ── API Key ─────────────────────────────────────── */}
              <section>
                <h3 className="text-xs font-semibold text-vault-accent uppercase tracking-wider mb-3">
                  Connection
                </h3>
                <div>
                  <label className={labelCls}>
                    OpenAI API Key{" "}
                    {settings.openai_api_key_set && (
                      <span className="text-green-400 ml-1">(set)</span>
                    )}
                  </label>
                  <input
                    type="password"
                    value={openaiApiKey}
                    onChange={(e) => setOpenaiApiKey(e.target.value)}
                    placeholder={
                      settings.openai_api_key_set
                        ? "Leave blank to keep current key"
                        : "sk-..."
                    }
                    className={inputCls}
                  />
                </div>
              </section>

              {/* ── LLM Models ──────────────────────────────────── */}
              <section>
                <h3 className="text-xs font-semibold text-vault-accent uppercase tracking-wider mb-3">
                  Models
                </h3>
                <div className="space-y-3">
                  <div>
                    <label className={labelCls}>LLM Model</label>
                    <input
                      type="text"
                      value={llmModel}
                      onChange={(e) => setLlmModel(e.target.value)}
                      placeholder="gpt-4o"
                      className={inputCls}
                    />
                  </div>
                  <div>
                    <label className={labelCls}>Vision Model</label>
                    <input
                      type="text"
                      value={visionModel}
                      onChange={(e) => setVisionModel(e.target.value)}
                      placeholder="gpt-4o"
                      className={inputCls}
                    />
                  </div>
                </div>
              </section>

              {/* ── Embeddings ──────────────────────────────────── */}
              <section>
                <h3 className="text-xs font-semibold text-vault-accent uppercase tracking-wider mb-3">
                  Embeddings
                </h3>
                <div className="space-y-3">
                  <div>
                    <label className={labelCls}>Embedding Model</label>
                    <input
                      type="text"
                      value={embeddingModel}
                      onChange={(e) => setEmbeddingModel(e.target.value)}
                      placeholder="text-embedding-3-large"
                      className={inputCls}
                    />
                  </div>
                  <div>
                    <label className={labelCls}>Embedding Dimension</label>
                    <input
                      type="number"
                      value={embeddingDimension}
                      onChange={(e) =>
                        setEmbeddingDimension(parseInt(e.target.value, 10) || 0)
                      }
                      className={inputCls}
                    />
                  </div>
                </div>
              </section>
            </>
          )}
        </div>

        {/* Footer */}
        {!loading && settings && (
          <div className="px-5 py-3 border-t border-vault-border/70 flex items-center justify-end gap-2">
            <button
              onClick={onClose}
              className="px-3 py-1.5 rounded-md text-xs font-medium text-vault-text-secondary hover:text-vault-text hover:bg-vault-surface-hover transition-colors"
            >
              Cancel
            </button>
            <button
              onClick={handleSave}
              disabled={saving}
              className="inline-flex items-center gap-1.5 px-4 py-1.5 rounded-md text-xs font-medium bg-vault-accent text-white hover:bg-vault-accent/80 disabled:opacity-50 transition-colors"
            >
              {saving && <Spinner />}
              Save Settings
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
