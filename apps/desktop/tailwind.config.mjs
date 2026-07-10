/** @type {import('tailwindcss').Config} */
export default {
  content: ["./src/renderer/index.html", "./src/renderer/src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // Bloomberg/TradingView-inspired dark palette.
        bg: {
          DEFAULT: "#0a0e14",
          panel: "#0f141c",
          elevated: "#151b26",
          hover: "#1b2330",
        },
        border: {
          DEFAULT: "#1e2733",
          strong: "#2a3543",
        },
        text: {
          DEFAULT: "#d6deeb",
          muted: "#8a97a8",
          faint: "#5a6675",
        },
        accent: {
          DEFAULT: "#2f81f7",
          hover: "#4090ff",
        },
        up: "#16c784",
        down: "#ea3943",
        warn: "#f0b90b",
      },
      fontFamily: {
        sans: ["Inter", "Segoe UI", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "Consolas", "ui-monospace", "monospace"],
      },
      fontSize: {
        "2xs": "0.6875rem",
      },
    },
  },
  plugins: [],
};
