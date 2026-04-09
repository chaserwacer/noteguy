/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      fontFamily: {
        sans: ["Inter", "system-ui", "-apple-system", "sans-serif"],
        mono: ["JetBrains Mono", "Fira Code", "monospace"],
      },
      colors: {
        vault: {
          bg: "var(--vault-bg)",
          surface: "var(--vault-surface)",
          "surface-hover": "var(--vault-surface-hover)",
          border: "var(--vault-border)",
          "border-strong": "var(--vault-border-strong)",
          text: "var(--vault-text)",
          "text-secondary": "var(--vault-text-secondary)",
          muted: "var(--vault-muted)",
          accent: "var(--vault-accent)",
          "accent-hover": "var(--vault-accent-hover)",
          "accent-subtle": "var(--vault-accent-subtle)",
          success: "var(--vault-success)",
          danger: "var(--vault-danger)",
        },
      },
      boxShadow: {
        modal: "0 -4px 32px rgba(0, 0, 0, 0.4)",
        "modal-full": "0 0 0 1px rgba(46, 46, 46, 0.5)",
        float: "0 2px 12px rgba(0, 0, 0, 0.3)",
      },
      animation: {
        "slide-up": "slideUp 200ms ease-out",
        "fade-in": "fadeIn 150ms ease-out",
        "modal-in": "modalIn 150ms ease-out",
      },
      keyframes: {
        slideUp: {
          from: { transform: "translateY(100%)", opacity: "0" },
          to: { transform: "translateY(0)", opacity: "1" },
        },
        fadeIn: {
          from: { opacity: "0" },
          to: { opacity: "1" },
        },
        modalIn: {
          from: { opacity: "0", transform: "scale(0.95)" },
          to: { opacity: "1", transform: "scale(1)" },
        },
      },
    },
  },
  plugins: [],
};
