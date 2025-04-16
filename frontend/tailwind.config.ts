import type { Config } from "tailwindcss";

export default {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "var(--background)",
        foreground: "var(--foreground)",
        card: {
          DEFAULT: "#ffffff",
          dark: "#0f172a",
        },
        'card-foreground': {
          DEFAULT: "var(--foreground)",
          dark: "var(--foreground)",
        },
        'muted-foreground': {
          DEFAULT: "#6b7280",
          dark: "#94a3b8",
        },
        accent: {
          DEFAULT: "#14b8a6",
          dark: "#2dd4bf",
        },
      },
    },
  },
  plugins: [],
} satisfies Config;
