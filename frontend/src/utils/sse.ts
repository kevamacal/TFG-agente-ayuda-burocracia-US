export interface SSECallbacks {
  onStatus?: (message: string) => void;
  onMetadata?: (data: { referencias: any[]; contexto: string }) => void;
  onToken?: (token: string) => void;
  onError?: (detail: string) => void;
}

export async function parseSSEStream(
  response: Response,
  callbacks: SSECallbacks
): Promise<void> {
  const reader = response.body?.getReader();
  const decoder = new TextDecoder("utf-8");
  if (!reader) {
    throw new Error("El cuerpo de la respuesta no es legible.");
  }

  let done = false;
  let buffer = "";

  while (!done) {
    const { value, done: readerDone } = await reader.read();
    done = readerDone;

    if (value) {
      buffer += decoder.decode(value, { stream: true });

      // Dividir el búfer por el delimitador de eventos SSE (doble salto de línea)
      const parts = buffer.split("\n\n");
      // Conservar el último trozo si está incompleto
      buffer = parts.pop() || "";

      for (const part of parts) {
        if (!part.trim()) continue;

        const lines = part.split("\n");
        let eventType = "";
        let dataString = "";

        for (const line of lines) {
          if (line.startsWith("event: ")) {
            eventType = line.replace("event: ", "").trim();
          } else if (line.startsWith("data: ")) {
            dataString = line.replace("data: ", "").trim();
          }
        }

        if (dataString) {
          try {
            const parsedData = JSON.parse(dataString);

            if (eventType === "status" && callbacks.onStatus) {
              callbacks.onStatus(parsedData.message || "");
            } else if (eventType === "metadata" && callbacks.onMetadata) {
              callbacks.onMetadata(parsedData);
            } else if (eventType === "token" && callbacks.onToken) {
              callbacks.onToken(parsedData.token || "");
            } else if (eventType === "error" && callbacks.onError) {
              callbacks.onError(parsedData.detail || "Error desconocido en el agente.");
            }
          } catch (e) {
            console.error("Error al procesar el JSON del fragmento SSE:", e, dataString);
          }
        }
      }
    }
  }
}
