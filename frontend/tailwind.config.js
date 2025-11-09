/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        teal: {
          500: '#0ea5a4',
          600: '#0d8f8e',
        },
      },
    },
  },
  plugins: [],
}
