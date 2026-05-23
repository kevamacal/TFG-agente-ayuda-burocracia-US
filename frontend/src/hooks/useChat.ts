import { useState, useEffect, useRef } from "react";
import Cookies from "js-cookie";

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

export interface Conversation {
  id: number;
  titulo: string;
  fecha_creacion: string;
}
import { API_URL } from "@/utils/api";

export function useChat() {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeConversationId, setActiveConversationId] = useState<number | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  
  const token = Cookies.get("auth_token");

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
        throw new Error("Failed to send message");
      }

      const reader = response.body?.getReader();
      const decoder = new TextDecoder("utf-8");
      if (!reader) throw new Error("No reader available");

      let done = false;
      let buffer = "";

      let currentAssistantResponse = "";
      let currentReferences: string[] = [];
      let currentContext = "";

      while (!done) {
        const { value, done: readerDone } = await reader.read();
        done = readerDone;
        
        if (value) {
          buffer += decoder.decode(value, { stream: true });
          
          // Split buffer by event markers (double-newlines)
          const parts = buffer.split("\n\n");
          // Keep the last part if it is incomplete
          buffer = parts.pop() || "";

          for (const part of parts) {
            if (!part.trim()) continue;

            // Parse Event Source format
            // example:
            // event: token
            // data: {"token": "hello"}
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
                
                if (eventType === "status") {
                  const statusMsg = parsedData.message || "";
                  setMessages((prev) => {
                    const next = [...prev];
                    const idx = next.length - 1;
                    if (idx >= 0 && next[idx].role === "assistant") {
                      next[idx] = {
                        ...next[idx],
                        status: statusMsg,
                      };
                    }
                    return next;
                  });
                } else if (eventType === "metadata") {
                  currentReferences = parsedData.referencias || [];
                  currentContext = parsedData.contexto || "";
                  
                  // Update message with metadata
                  setMessages((prev) => {
                    const next = [...prev];
                    const idx = next.length - 1;
                    if (idx >= 0 && next[idx].role === "assistant") {
                      next[idx] = {
                        ...next[idx],
                        referencias: currentReferences,
                        contexto: currentContext,
                      };
                    }
                    return next;
                  });
                } else if (eventType === "token") {
                  currentAssistantResponse += parsedData.token;
                  
                  // Update message content
                  setMessages((prev) => {
                    const next = [...prev];
                    const idx = next.length - 1;
                    if (idx >= 0 && next[idx].role === "assistant") {
                      next[idx] = {
                        ...next[idx],
                        content: currentAssistantResponse,
                      };
                    }
                    return next;
                  });
                } else if (eventType === "error") {
                  console.error("SSE agent error:", parsedData.detail);
                  currentAssistantResponse += `\n[Error del agente: ${parsedData.detail}]`;
                  setMessages((prev) => {
                    const next = [...prev];
                    const idx = next.length - 1;
                    if (idx >= 0 && next[idx].role === "assistant") {
                      next[idx] = {
                        ...next[idx],
                        content: currentAssistantResponse,
                        isStreaming: false,
                      };
                    }
                    return next;
                  });
                }
              } catch (e) {
                console.error("Error parsing chunk JSON:", e, dataString);
              }
            }
          }
        }
      }

      // Mark streaming as finished
      setMessages((prev) => {
        const next = [...prev];
        const idx = next.length - 1;
        if (idx >= 0 && next[idx].role === "assistant") {
          next[idx] = {
            ...next[idx],
            isStreaming: false,
          };
        }
        return next;
      });

      // Reload conversations to fetch any updated title in background
      await fetchConversations();
      // Fetch messages again to populate database IDs for feedback
      await fetchMessages(activeConversationId);

    } catch (err) {
      console.error("Error sending message:", err);
      setMessages((prev) => {
        const next = [...prev];
        const idx = next.length - 1;
        if (idx >= 0 && next[idx].role === "assistant") {
          next[idx] = {
            ...next[idx],
            content: "Hubo un error de conexión con el servidor al intentar generar la respuesta.",
            isStreaming: false,
          };
        }
        return next;
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
