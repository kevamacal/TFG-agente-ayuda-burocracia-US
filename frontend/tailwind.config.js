/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "#0d0e12",
        sidebar: "#15171e",
        accent: {
          DEFAULT: "#9D1C34", // Burgundy-like color of Universidad de Sevilla
          hover: "#b3223f",
        },
        card: "#1b1d26",
        border: "#292c3a",
      },
      fontFamily: {
        sans: ["var(--font-inter)", "Inter", "sans-serif"],
      },
    },
  },
  plugins: [],
}
