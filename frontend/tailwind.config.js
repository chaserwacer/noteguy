/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ["Inter", "system-ui", "-apple-system", "sans-serif"],
        mono: ["JetBrains Mono", "Fira Code", "monospace"],
      },
      colors: {
        vault: {
          bg: "#191919",
          surface: "#1e1e1e",
          "surface-hover": "#252525",
          border: "#2e2e2e",
          "border-strong": "#3a3a3a",
          text: "#e8e4df",
          "text-secondary": "#a8a29e",
          muted: "#6b6560",
          accent: "#c4956a",
          "accent-hover": "#d4a57a",
          "accent-subtle": "rgba(196, 149, 106, 0.12)",
          success: "#7dae80",
          danger: "#d48585",
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
