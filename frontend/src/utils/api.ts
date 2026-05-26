export const getApiUrl = (): string => {
  if (typeof window !== "undefined") {
    // En el navegador, usamos el proxy relativo '/api' para que Next.js reenvíe las peticiones al backend
    return "/api";
  }

  // En el servidor (SSR/Build)
  return process.env.API_URL || "http://localhost:8000";
};

export const API_URL = getApiUrl();


