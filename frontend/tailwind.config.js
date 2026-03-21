/** @type {import('tailwindcss').Config} */
export default {
    content: [
        "./index.html",
        "./src/**/*.{js,ts,jsx,tsx}",
    ],
    theme: {
        extend: {
            // Puedes añadir colores corporativos aquí para la defensa
            colors: {
                prosperas: {
                    light: '#6366f1',
                    dark: '#4f46e5',
                }
            }
        },
    },
    plugins: [],
}