interface ToolbarProps {
  visible: boolean;
  onCommand: (before: string, after: string) => void;
  previewActive: boolean;
  onTogglePreview: () => void;
  historyActive: boolean;
  onToggleHistory: () => void;
}

interface ToolbarButton {
  label: string;
  title: string;
  before: string;
  after: string;
}

const buttons: ToolbarButton[] = [
  { label: "H1", title: "Heading 1", before: "# ", after: "" },
  { label: "H2", title: "Heading 2", before: "## ", after: "" },
  { label: "B", title: "Bold", before: "**", after: "**" },
  { label: "I", title: "Italic", before: "_", after: "_" },
  { label: "<>", title: "Code", before: "`", after: "`" },
  { label: "🔗", title: "Link", before: "[", after: "](url)" },
];

export default function EditorToolbar({
  visible,
  onCommand,
  previewActive,
  onTogglePreview,
  historyActive,
  onToggleHistory,
}: ToolbarProps) {
  return (
    <div
      className={`flex items-center gap-1 px-3 py-1.5 bg-vault-surface/90 backdrop-blur-sm rounded-lg shadow-lg border border-vault-border/50 mx-auto w-fit mt-2 transition-opacity duration-150 ${
        visible ? "opacity-100" : "opacity-0 pointer-events-none"
      }`}
    >
      {buttons.map((btn) => (
        <button
          key={btn.label}
          title={btn.title}
          onMouseDown={(e) => {
            e.preventDefault(); // keep editor focus
            onCommand(btn.before, btn.after);
          }}
          className="px-2 py-0.5 text-xs font-mono text-vault-muted hover:text-vault-text hover:bg-vault-border/40 rounded transition-colors duration-150"
        >
          {btn.label}
        </button>
      ))}

      <div className="w-px h-4 bg-vault-border mx-1" />

      <button
        title="Toggle Preview (Ctrl+Shift+P)"
        onMouseDown={(e) => {
          e.preventDefault();
          onTogglePreview();
        }}
        className={`px-2 py-0.5 text-xs font-mono rounded transition-colors duration-150 ${
          previewActive
            ? "text-vault-accent bg-vault-accent/10"
            : "text-vault-muted hover:text-vault-text hover:bg-vault-border/40"
        }`}
      >
        Preview
      </button>

      <button
        title="Toggle History (Ctrl+Shift+H)"
        onMouseDown={(e) => {
          e.preventDefault();
          onToggleHistory();
        }}
        className={`px-2 py-0.5 text-xs font-mono rounded transition-colors duration-150 ${
          historyActive
            ? "text-vault-accent bg-vault-accent/10"
            : "text-vault-muted hover:text-vault-text hover:bg-vault-border/40"
        }`}
      >
        History
      </button>
    </div>
  );
}
