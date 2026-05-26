import { useState, useEffect } from "react";
import Cookies from "js-cookie";
import { API_URL } from "@/utils/api";
import { parseSSEStream } from "@/utils/sse";

export interface Message {
  id?: number;
  role: "user" | "assistant" | "system";
  content: string;
  referencias?: string[];
  contexto?: string;
  isStreaming?: boolean;
  status?: string;
  feedback?: boolean | null;
  feedback_comentario?: string | null;
}

const formatSSEError = (detail: string): string => {
  // Rate limits (Error 429)
  if (detail.includes("429") || detail.includes("rate_limit_exceeded") || detail.includes("Rate limit")) {
    let friendlyMessage = "⚠️ **Límite de peticiones alcanzado (Error 429)**\n\nEl servidor de IA está experimentando una alta demanda o se han agotado los tokens gratuitos diarios del proveedor (Groq).";
    
    // Intentar extraer el tiempo de espera (ej: 1h32m26s o similar)
    const timeMatch = detail.match(/try again in ([0-9a-zA-Z\.]+)/i);
    if (timeMatch && timeMatch[1]) {
      let timeStr = timeMatch[1];
      timeStr = timeStr
        .replace(/h/g, " hora(s) ")
        .replace(/m/g, " minuto(s) ")
        .replace(/s/g, " segundo(s) ");
      friendlyMessage += `\n\nPor favor, vuelve a intentarlo en: **${timeStr.trim()}**.`;
    } else {
      friendlyMessage += "\n\nPor favor, inténtalo de nuevo en unos minutos o más tarde.";
    }
    
    return friendlyMessage;
  }

  // Límite de tokens de contexto superado
  if (detail.includes("context_length_exceeded") || detail.includes("context length")) {
    return "⚠️ **Ventana de contexto superada**\n\nEl historial de esta conversación se ha vuelto demasiado largo para ser procesado por el modelo. Por favor, crea una **nueva conversación** desde el panel lateral para poder continuar.";
  }

  // Errores de API de Groq o Proveedor
  if (detail.includes("Groq") || detail.includes("API connection") || detail.includes("Failed to establish a new connection")) {
    return "⚠️ **Error de conexión con el servicio de IA**\n\nNo se ha podido establecer comunicación con los servidores del modelo de lenguaje (Groq). Por favor, comprueba tu conexión a internet o inténtalo de nuevo en unos momentos.";
  }

  // Fallback general
  return `⚠️ **Error en el agente**\n\nEl asistente no pudo completar tu respuesta debido al siguiente inconveniente:\n\n*${detail}*`;
};

export interface Conversation {
  id: number;
  titulo: string;
  fecha_creacion: string;
}

export function useChat() {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeConversationId, setActiveConversationId] = useState<number | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  
  const token = Cookies.get("auth_token");

  // Helper local para actualizar el último mensaje del asistente en el estado de React
  const updateLastAssistantMessage = (updates: Partial<Message>) => {
    setMessages((prev) => {
      const next = [...prev];
      const idx = next.length - 1;
      if (idx >= 0 && next[idx].role === "assistant") {
        next[idx] = { ...next[idx], ...updates };
      }
      return next;
    });
  };

  // Fetch all conversations
  const fetchConversations = async () => {
    if (!token) return;
    try {
      const res = await fetch(`${API_URL}/conversaciones`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setConversations(data);
      }
    } catch (err) {
      console.error("Error fetching conversations:", err);
    }
  };

  // Fetch messages for active conversation
  const fetchMessages = async (id: number) => {
    if (!token) return;
    try {
      const res = await fetch(`${API_URL}/conversaciones/${id}/mensajes`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        const parsed = data.map((m: any) => {
          let refs = [];
          if (m.referencias) {
            try {
              refs = JSON.parse(m.referencias);
            } catch {
              refs = [];
            }
          }
          return {
            id: m.id,
            role: m.rol,
            content: m.contenido,
            referencias: refs,
            feedback: m.feedback,
            feedback_comentario: m.feedback_comentario,
          };
        });
        setMessages(parsed);
      }
    } catch (err) {
      console.error("Error fetching messages:", err);
    }
  };

  // Create new conversation
  const createConversation = async () => {
    if (!token) return;
    try {
      const res = await fetch(`${API_URL}/conversaciones`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ titulo: "Nueva conversación" }),
      });
      if (res.ok) {
        const newConv = await res.json();
        setConversations((prev) => [newConv, ...prev]);
        setActiveConversationId(newConv.id);
        setMessages([]);
      }
    } catch (err) {
      console.error("Error creating conversation:", err);
    }
  };

  // Delete conversation
  const deleteConversation = async (id: number) => {
    if (!token) return;
    try {
      const res = await fetch(`${API_URL}/conversaciones/${id}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        setConversations((prev) => prev.filter((c) => c.id !== id));
        if (activeConversationId === id) {
          setActiveConversationId(null);
          setMessages([]);
        }
      }
    } catch (err) {
      console.error("Error deleting conversation:", err);
    }
  };

  // Rename conversation
  const renameConversation = async (id: number, titulo: string) => {
    if (!token) return;
    try {
      const res = await fetch(`${API_URL}/conversaciones/${id}`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ titulo }),
      });
      if (res.ok) {
        const updated = await res.json();
        setConversations((prev) => prev.map((c) => (c.id === id ? updated : c)));
      }
    } catch (err) {
      console.error("Error renaming conversation:", err);
    }
  };

  // Send message with SSE streaming
  const sendMessage = async (text: string) => {
    if (!token || !activeConversationId || !text.trim()) return;

    // Add user message to UI
    const userMsg: Message = { role: "user", content: text };
    setMessages((prev) => [...prev, userMsg]);
    setIsLoading(true);

    // Add empty assistant message that will stream
    const assistantMsg: Message = {
      role: "assistant",
      content: "",
      referencias: [],
      isStreaming: true,
    };
    setMessages((prev) => [...prev, assistantMsg]);

    try {
      const response = await fetch(`${API_URL}/conversaciones/${activeConversationId}/chat`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ pregunta: text }),
      });

      if (!response.ok) {
        throw new Error("Error al enviar la consulta");
      }

      let currentAssistantResponse = "";

      // Procesar el flujo usando la utilidad centralizada de SSE
      await parseSSEStream(response, {
        onStatus: (message) => {
          updateLastAssistantMessage({ status: message });
        },
        onMetadata: (data) => {
          updateLastAssistantMessage({
            referencias: data.referencias || [],
            contexto: data.contexto || "",
          });
        },
        onToken: (tokenText) => {
          currentAssistantResponse += tokenText;
          updateLastAssistantMessage({ content: currentAssistantResponse });
        },
        onError: (detail) => {
          console.error("SSE agent error:", detail);
          const friendlyError = formatSSEError(detail);
          const newContent = currentAssistantResponse
            ? `${currentAssistantResponse}\n\n${friendlyError}`
            : friendlyError;
          updateLastAssistantMessage({
            content: newContent,
            isStreaming: false,
          });
        },
      });

      // Finalizar estado de streaming
      updateLastAssistantMessage({ isStreaming: false });

      // Recargar conversaciones para capturar el título generado en background
      await fetchConversations();
      // Obtener mensajes de nuevo para mapear IDs reales de base de datos para el feedback
      await fetchMessages(activeConversationId);

    } catch (err) {
      console.error("Error sending message:", err);
      updateLastAssistantMessage({
        content: "Hubo un error de conexión con el servidor al intentar generar la respuesta.",
        isStreaming: false,
      });
    } finally {
      setIsLoading(false);
    }
  };

  const submitFeedback = async (messageId: number, feedback: boolean, comentario?: string) => {
    if (!token || !activeConversationId) return;
    try {
      const res = await fetch(`${API_URL}/conversaciones/${activeConversationId}/mensajes/${messageId}/feedback`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ feedback, feedback_comentario: comentario || null }),
      });
      if (res.ok) {
        setMessages((prev) =>
          prev.map((m) =>
            m.id === messageId
              ? { ...m, feedback, feedback_comentario: comentario || null }
              : m
          )
        );
      }
    } catch (err) {
      console.error("Error submitting feedback:", err);
    }
  };

  // Sync active conversation
  useEffect(() => {
    if (activeConversationId !== null) {
      fetchMessages(activeConversationId);
    } else {
      setMessages([]);
    }
  }, [activeConversationId]);

  // Load conversations on mount
  useEffect(() => {
    if (token) {
      fetchConversations();
    }
  }, [token]);

  return {
    conversations,
    activeConversationId,
    setActiveConversationId,
    messages,
    isLoading,
    createConversation,
    deleteConversation,
    renameConversation,
    sendMessage,
    submitFeedback,
    reloadConversations: fetchConversations,
  };
}
