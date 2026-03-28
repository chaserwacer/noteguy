import { useEffect, useRef, useState, useCallback, type ReactNode } from "react";

/* ── Backdrop + panel wrapper ──────────────────────────────────────────── */

function ModalShell({
  children,
  onClose,
}: {
  children: ReactNode;
  onClose: () => void;
}) {
  const overlayRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [onClose]);

  return (
    <div
      ref={overlayRef}
      className="fixed inset-0 z-[60] flex items-center justify-center bg-black/50 animate-fade-in"
      onMouseDown={(e) => {
        if (e.target === overlayRef.current) onClose();
      }}
    >
      <div className="bg-vault-surface border border-vault-border-strong rounded-xl shadow-modal w-full max-w-sm mx-4 animate-modal-in">
        {children}
      </div>
    </div>
  );
}

/* ── Confirm modal ─────────────────────────────────────────────────────── */

export interface ConfirmModalProps {
  title: string;
  message: string;
  confirmLabel?: string;
  danger?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}

export function ConfirmModal({
  title,
  message,
  confirmLabel = "Delete",
  danger = true,
  onConfirm,
  onCancel,
}: ConfirmModalProps) {
  return (
    <ModalShell onClose={onCancel}>
      <div className="px-5 pt-5 pb-4">
        <h3 className="text-sm font-semibold text-vault-text">{title}</h3>
        <p className="text-[13px] text-vault-text-secondary mt-1.5 leading-relaxed">
          {message}
        </p>
      </div>
      <div className="flex justify-end gap-2 px-5 pb-4">
        <button
          onClick={onCancel}
          className="px-3 py-1.5 text-[13px] rounded-lg text-vault-text-secondary hover:text-vault-text hover:bg-vault-surface-hover transition-colors"
        >
          Cancel
        </button>
        <button
          onClick={onConfirm}
          autoFocus
          className={`px-3 py-1.5 text-[13px] font-medium rounded-lg transition-colors ${
            danger
              ? "bg-vault-danger/15 text-vault-danger hover:bg-vault-danger/25"
              : "bg-vault-accent text-vault-bg hover:bg-vault-accent-hover"
          }`}
        >
          {confirmLabel}
        </button>
      </div>
    </ModalShell>
  );
}

/* ── Prompt modal ──────────────────────────────────────────────────────── */

export interface PromptModalProps {
  title: string;
  placeholder?: string;
  defaultValue?: string;
  confirmLabel?: string;
  onConfirm: (value: string) => void;
  onCancel: () => void;
}

export function PromptModal({
  title,
  placeholder,
  defaultValue = "",
  confirmLabel = "Save",
  onConfirm,
  onCancel,
}: PromptModalProps) {
  const [value, setValue] = useState(defaultValue);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    // Select all text on open for easy replacement
    inputRef.current?.select();
  }, []);

  const handleSubmit = () => {
    if (value.trim()) onConfirm(value.trim());
  };

  return (
    <ModalShell onClose={onCancel}>
      <div className="px-5 pt-5 pb-3">
        <h3 className="text-sm font-semibold text-vault-text mb-3">{title}</h3>
        <input
          ref={inputRef}
          type="text"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") handleSubmit();
          }}
          placeholder={placeholder}
          autoFocus
          className="w-full bg-vault-bg border border-vault-border rounded-lg px-3 py-2 text-sm text-vault-text placeholder:text-vault-muted outline-none focus:border-vault-accent transition-colors"
        />
      </div>
      <div className="flex justify-end gap-2 px-5 pb-4">
        <button
          onClick={onCancel}
          className="px-3 py-1.5 text-[13px] rounded-lg text-vault-text-secondary hover:text-vault-text hover:bg-vault-surface-hover transition-colors"
        >
          Cancel
        </button>
        <button
          onClick={handleSubmit}
          disabled={!value.trim()}
          className="px-3 py-1.5 text-[13px] font-medium rounded-lg bg-vault-accent text-vault-bg hover:bg-vault-accent-hover disabled:opacity-30 transition-colors"
        >
          {confirmLabel}
        </button>
      </div>
    </ModalShell>
  );
}

/* ── Hook for modal state management ───────────────────────────────────── */

type ModalState =
  | null
  | { type: "confirm"; props: ConfirmModalProps }
  | { type: "prompt"; props: PromptModalProps };

export function useModal() {
  const [modal, setModal] = useState<ModalState>(null);

  const showConfirm = useCallback(
    (props: Omit<ConfirmModalProps, "onCancel">) => {
      setModal({
        type: "confirm",
        props: { ...props, onCancel: () => setModal(null) },
      });
    },
    [],
  );

  const showPrompt = useCallback(
    (props: Omit<PromptModalProps, "onCancel">) => {
      setModal({
        type: "prompt",
        props: { ...props, onCancel: () => setModal(null) },
      });
    },
    [],
  );

  const close = useCallback(() => setModal(null), []);

  const renderModal = useCallback(() => {
    if (!modal) return null;
    if (modal.type === "confirm") return <ConfirmModal {...modal.props} />;
    if (modal.type === "prompt") return <PromptModal {...modal.props} />;
    return null;
  }, [modal]);

  return { showConfirm, showPrompt, close, renderModal };
}
