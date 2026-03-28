/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        mono: ["JetBrains Mono", "Fira Code", "monospace"],
        sans: ["Inter", "system-ui", "sans-serif"],
      },
      colors: {
        vault: {
          bg: "#1a1b26",
          surface: "#24283b",
          border: "#3b4261",
          text: "#c0caf5",
          muted: "#565f89",
          accent: "#7aa2f7",
          "accent-hover": "#89b4fa",
        },
      },
    },
  },
  plugins: [],
};
