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

  return (
    <div
      ref={ref}
      className="fixed z-50 bg-vault-surface border border-vault-border-strong rounded-lg shadow-float py-1 min-w-[160px] animate-fade-in"
      style={{ left: x, top: y }}
    >
      {items.map((item, i) => (
        <button
          key={i}
          onClick={() => {
            item.onClick();
            onClose();
          }}
          className="w-full text-left px-3 py-1.5 text-[13px] text-vault-text hover:bg-vault-surface-hover transition-colors"
        >
          {item.label}
        </button>
      ))}
    </div>
  );
}
