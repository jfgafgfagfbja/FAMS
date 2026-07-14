// VITE_API_URL la ten chinh; VITE_API_BASE_URL duoc giu de tuong thich nguoc.
export const API_BASE_URL =
  import.meta.env.VITE_API_URL || import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'
