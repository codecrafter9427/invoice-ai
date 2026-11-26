import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        ink: "#0f1c2e",
        slate: "#3d4f66",
        mist: "#e8eef5",
        paper: "#f7f9fc",
        accent: "#1a6b5c",
        accentSoft: "#d4ebe6",
        warn: "#b45309",
      },
      fontFamily: {
        display: ["var(--font-display)", "Georgia", "serif"],
        sans: ["var(--font-sans)", "Segoe UI", "sans-serif"],
      },
    },
  },
  plugins: [],
};

export default config;
