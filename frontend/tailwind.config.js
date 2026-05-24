/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: 'class',
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "var(--color-background)",
        sidebar: "var(--color-sidebar)",
        accent: {
          DEFAULT: "#9D1C34", // Burgundy-like color of Universidad de Sevilla
          hover: "#b3223f",
        },
        card: "var(--color-card)",
        border: "var(--color-border)",
        header: "var(--color-header)",
        hover: "var(--color-hover)",
        textMain: "var(--color-text-main)",
        textMuted: "var(--color-text-muted)",
        inputBg: "var(--color-input-bg)",
        cardLighter: "var(--color-card-lighter)",
      },
      fontFamily: {
        sans: ["var(--font-inter)", "Inter", "sans-serif"],
      },
    },
  },
  plugins: [],
}
