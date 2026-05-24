// In development: Vite proxies /api → localhost:8000 (vite.config.js)
// In production:  VITE_API_URL is set to the Render backend URL on Vercel
export const API_BASE = import.meta.env.VITE_API_URL || ''
