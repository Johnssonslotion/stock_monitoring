/** @type {import('tailwindcss').Config} */
export default {
    content: [
        "./index.html",
        "./src/**/*.{js,ts,jsx,tsx}",
    ],
    theme: {
        extend: {
            colors: {
                background: '#0f172a',
                card: '#1e293b',
                primary: '#38bdf8',
                success: '#22c55e',
                warning: '#f59e0b',
                danger: '#ef4444',
            },
        },
    },
    plugins: [],
}
