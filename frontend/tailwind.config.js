/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        risk: {
          low: "#2563eb",
          high: "#dc2626",
        },
      },
    },
  },
  plugins: [],
};
