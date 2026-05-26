export const getApiUrl = (): string => {
  // Priorizar la variable de entorno API_URL (que Next.js inyecta en el build de producción)
  if (process.env.API_URL && !process.env.API_URL.includes("localhost")) {
    return process.env.API_URL;
  }

  if (typeof window !== "undefined") {
    // En el navegador, si estamos en localhost, usamos el puerto 8000
    if (window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1") {
      return `${window.location.protocol}//localhost:8000`;
    }
    // Si estamos en producción en el navegador (pero no se configuró API_URL en el build),
    // usamos el host actual con protocolo pero sin el puerto 8000 de desarrollo
    return `${window.location.protocol}//${window.location.hostname}`;
  }

  // En el servidor (SSR/Build)
  return process.env.API_URL || "http://localhost:8000";
};

export const API_URL = getApiUrl();

