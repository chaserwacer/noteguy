import { useEffect, type FC } from "react";
import { useNoteStore } from "@/store/useNoteStore";

function relativeTime(isoDate: string): string {
  const diff = Date.now() - new Date(isoDate).getTime();
  const mins = Math.floor(diff / 60_000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  if (days < 30) return `${days}d ago`;
  return new Date(isoDate).toLocaleDateString();
}

const HistoryPanel: FC = () => {
  const activeNoteId = useNoteStore((s) => s.activeNoteId);
  const versionHistory = useNoteStore((s) => s.versionHistory);
  const selectedVersionSha = useNoteStore((s) => s.selectedVersionSha);
  const selectVersion = useNoteStore((s) => s.selectVersion);
  const restoreVersion = useNoteStore((s) => s.restoreVersion);
  const toggleHistoryPanel = useNoteStore((s) => s.toggleHistoryPanel);
  const loadHistory = useNoteStore((s) => s.loadHistory);

  // Reload history when the active note changes
  useEffect(() => {
    if (activeNoteId) {
      loadHistory(activeNoteId);
    }
  }, [activeNoteId, loadHistory]);

  return (
    <div className="flex flex-col h-full border-l border-vault-border bg-vault-surface w-64 shrink-0">
      {/* Header */}
      <div className="flex items-center justify-between px-3 py-2.5 border-b border-vault-border">
        <h3 className="text-xs font-semibold text-vault-accent uppercase tracking-wide">
          Version History
        </h3>
        <button
          onClick={toggleHistoryPanel}
          className="text-vault-muted hover:text-vault-text transition-colors"
          title="Close history"
        >
          <svg className="w-4 h-4" viewBox="0 0 16 16" fill="currentColor">
            <path d="M3.72 3.72a.75.75 0 011.06 0L8 6.94l3.22-3.22a.75.75 0 111.06 1.06L9.06 8l3.22 3.22a.75.75 0 11-1.06 1.06L8 9.06l-3.22 3.22a.75.75 0 01-1.06-1.06L6.94 8 3.72 4.78a.75.75 0 010-1.06z" />
          </svg>
        </button>
      </div>

      {/* Timeline */}
      <div className="flex-1 overflow-y-auto">
        {versionHistory.length === 0 ? (
          <p className="text-xs text-vault-muted text-center mt-8 px-3">
            No version history yet. History is recorded when you save notes.
          </p>
        ) : (
          <div className="py-2">
            {versionHistory.map((entry, idx) => {
              const isSelected = selectedVersionSha === entry.sha;
              const isCurrent = idx === 0;
              return (
                <button
                  key={entry.sha}
                  onClick={() =>
                    selectVersion(isSelected ? null : entry.sha)
                  }
                  className={`w-full text-left px-3 py-2 transition-colors ${
                    isSelected
                      ? "bg-vault-accent/15 border-l-2 border-vault-accent"
                      : "hover:bg-vault-border/30 border-l-2 border-transparent"
                  }`}
                >
                  <div className="flex items-center gap-1.5">
                    {/* Commit dot */}
                    <div
                      className={`w-2 h-2 rounded-full shrink-0 ${
                        isCurrent
                          ? "bg-vault-accent"
                          : "bg-vault-muted/50"
                      }`}
                    />
                    <span className="text-xs font-mono text-vault-muted">
                      {entry.short_sha}
                    </span>
                    <span className="text-[10px] text-vault-muted ml-auto">
                      {relativeTime(entry.timestamp)}
                    </span>
                  </div>
                  <p className="text-xs text-vault-text mt-0.5 pl-3.5 truncate">
                    {entry.message}
                  </p>

                  {/* Restore button */}
                  {isSelected && !isCurrent && activeNoteId && (
                    <div className="pl-3.5 mt-1.5">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          restoreVersion(activeNoteId, entry.sha);
                        }}
                        className="px-2 py-0.5 text-[11px] font-medium rounded bg-vault-accent text-vault-bg hover:bg-vault-accent-hover transition-colors"
                      >
                        Restore this version
                      </button>
                    </div>
                  )}
                </button>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};

export default HistoryPanel;
