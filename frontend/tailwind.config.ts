import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: ["class"],
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    container: { center: true, padding: "1.25rem" },
    extend: {
      colors: {
        bg: {
          DEFAULT: "#07090d",
          elev: "#0c1118",
          card: "#0f1521",
        },
        ink: {
          DEFAULT: "#e6edf7",
          muted: "#8b97ad",
          dim: "#5a667e",
        },
        line: "#1a2235",
        accent: {
          DEFAULT: "#7cf0c8",
          warn: "#ffb547",
          danger: "#ff6b6b",
          info: "#6aa9ff",
        },
      },
      fontFamily: {
        sans: ["var(--font-inter)", "ui-sans-serif", "system-ui"],
        mono: ["ui-monospace", "SFMono-Regular", "Menlo", "monospace"],
      },
      boxShadow: {
        glow: "0 0 0 1px rgba(124,240,200,0.18), 0 0 30px -10px rgba(124,240,200,0.35)",
        card: "0 1px 0 rgba(255,255,255,0.04) inset, 0 8px 32px -16px rgba(0,0,0,0.6)",
      },
      keyframes: {
        "pulse-dot": {
          "0%,100%": { opacity: "1" },
          "50%": { opacity: "0.35" },
        },
        "fade-up": {
          "0%": { opacity: "0", transform: "translateY(6px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
      },
      animation: {
        "pulse-dot": "pulse-dot 1.4s ease-in-out infinite",
        "fade-up": "fade-up 280ms ease-out both",
      },
    },
  },
  plugins: [],
};

export default config;
