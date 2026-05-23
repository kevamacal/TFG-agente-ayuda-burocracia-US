export const getApiUrl = (): string => {
  if (typeof window !== "undefined") {
    // Si estamos en el navegador, usamos el host actual con el puerto del backend (8000)
    return `${window.location.protocol}//${window.location.hostname}:8000`;
  }
  // En el servidor (SSR/Build) usamos la variable de entorno o localhost
  return process.env.API_URL || "http://localhost:8000";
};

export const API_URL = getApiUrl();
