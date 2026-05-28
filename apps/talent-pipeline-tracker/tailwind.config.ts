/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./app/**/*.{js,ts,jsx,tsx}",
    "./components/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Brasaland palette from application.html
        stone: {
          950: "#0c0a09",
          900: "#1c1917",
          700: "#44403c",
          600: "#57534e",
          500: "#78716c",
          400: "#a8a29e",
          200: "#e7e5e4",
          100: "#f5f5f4",
          50: "#fafaf9"
        },
        amber: {
          950: "#78350f",
          300: "#fcd34d",
          200: "#fde68a",
          100: "#fef3c7"
        },
        red: {
          300: "#fca5a5"
        }
      },
    },
  },
  plugins: [],
};
