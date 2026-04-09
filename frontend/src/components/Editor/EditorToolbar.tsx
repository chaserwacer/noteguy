type ToolbarCommand = "h1" | "h2" | "h3" | "bold" | "italic" | "code" | "bullet-list" | "ordered-list" | "blockquote" | "link";

interface ToolbarProps {
  visible: boolean;
  onCommand: (command: ToolbarCommand) => void;
  historyActive: boolean;
  onToggleHistory: () => void;
}

interface ToolbarButton {
  command: ToolbarCommand;
  label: string;
  title: string;
}

const buttons: ToolbarButton[] = [
  { command: "h1", label: "H1", title: "Heading 1" },
  { command: "h2", label: "H2", title: "Heading 2" },
  { command: "h3", label: "H3", title: "Heading 3" },
  { command: "bold", label: "B", title: "Bold" },
  { command: "italic", label: "I", title: "Italic" },
  { command: "code", label: "<>", title: "Inline Code" },
  { command: "bullet-list", label: "\u2022", title: "Bullet List" },
  { command: "ordered-list", label: "1.", title: "Ordered List" },
  { command: "blockquote", label: "\u201C", title: "Quote" },
  { command: "link", label: "Link", title: "Insert Link" },
];

export default function EditorToolbar({
  visible,
  onCommand,
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
          key={btn.command}
          title={btn.title}
          onMouseDown={(e) => {
            e.preventDefault();
            onCommand(btn.command);
          }}
          className="px-2 py-0.5 text-xs text-vault-text-secondary hover:text-vault-text hover:bg-vault-surface-hover rounded transition-colors"
        >
          {btn.label}
        </button>
      ))}

      <div className="w-px h-4 bg-vault-border mx-1" />

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
