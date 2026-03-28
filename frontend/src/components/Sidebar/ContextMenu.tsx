import { useEffect, useRef } from "react";

export interface MenuItem {
  label: string;
  onClick: () => void;
}

interface ContextMenuProps {
  x: number;
  y: number;
  items: MenuItem[];
  onClose: () => void;
}

export default function ContextMenu({ x, y, items, onClose }: ContextMenuProps) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClick = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) onClose();
    };
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("mousedown", handleClick);
    document.addEventListener("keydown", handleKey);
    return () => {
      document.removeEventListener("mousedown", handleClick);
      document.removeEventListener("keydown", handleKey);
    };
  }, [onClose]);

  // Keep the menu inside the viewport
  const style: React.CSSProperties = {
    left: x,
    top: y,
  };

  return (
    <div
      ref={ref}
      className="fixed z-50 bg-vault-surface border border-vault-border rounded-md shadow-lg py-1 min-w-[160px]"
      style={style}
    >
      {items.map((item, i) => (
        <button
          key={i}
          onClick={() => {
            item.onClick();
            onClose();
          }}
          className="w-full text-left px-3 py-1.5 text-sm text-vault-text hover:bg-vault-accent/10 hover:text-vault-accent transition-colors duration-150"
        >
          {item.label}
        </button>
      ))}
    </div>
  );
}
