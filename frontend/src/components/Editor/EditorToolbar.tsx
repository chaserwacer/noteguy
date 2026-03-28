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
  { label: "Link", title: "Link", before: "[", after: "](url)" },
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
      className={`flex items-center gap-0.5 px-2 py-1 bg-vault-surface border border-vault-border rounded-lg shadow-float mx-auto w-fit mt-2 transition-opacity duration-150 ${
        visible ? "opacity-100" : "opacity-0 pointer-events-none"
      }`}
    >
      {buttons.map((btn) => (
        <button
          key={btn.label}
          title={btn.title}
          onMouseDown={(e) => {
            e.preventDefault();
            onCommand(btn.before, btn.after);
          }}
          className="px-2 py-0.5 text-xs text-vault-text-secondary hover:text-vault-text hover:bg-vault-surface-hover rounded transition-colors"
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
        className={`px-2 py-0.5 text-xs rounded transition-colors ${
          previewActive
            ? "text-vault-accent bg-vault-accent-subtle"
            : "text-vault-text-secondary hover:text-vault-text hover:bg-vault-surface-hover"
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
        className={`px-2 py-0.5 text-xs rounded transition-colors ${
          historyActive
            ? "text-vault-accent bg-vault-accent-subtle"
            : "text-vault-text-secondary hover:text-vault-text hover:bg-vault-surface-hover"
        }`}
      >
        History
      </button>
    </div>
  );
}
