export const getApiUrl = (): string => {
  if (typeof window !== "undefined") {
    // Si estamos en producción en el navegador, conectamos directamente al backend público en Render
    if (
      window.location.hostname !== "localhost" &&
      window.location.hostname !== "127.0.0.1"
    ) {
      return "https://tfg-agente-ayuda-burocracia-us.onrender.com";
    }
    // En desarrollo local en el navegador, conectamos a localhost:8000
    return `${window.location.protocol}//${window.location.hostname}:8000`;
  }

  // En el servidor (SSR/Build)
  return process.env.API_URL || "http://localhost:8000";
};

export const API_URL = getApiUrl();
