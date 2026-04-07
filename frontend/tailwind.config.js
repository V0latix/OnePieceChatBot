/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ocean: "#0c1b2f",
        ember: "#d94f2b",
        gold: "#e7b24a",
        parchment: "#f4e8cc"
      },
      boxShadow: {
        sail: "0 10px 40px rgba(231, 178, 74, 0.15)"
      }
    },
  },
  plugins: [],
};
