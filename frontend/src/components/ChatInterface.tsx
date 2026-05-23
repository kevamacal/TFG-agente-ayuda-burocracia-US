import React, { useState, useRef, useEffect } from "react";
import { MessageSquare, Send, BookOpen, User, Bot, ChevronDown, ChevronUp } from "lucide-react";
import { Message } from "../hooks/useChat";
import ReactMarkdown from "react-markdown";

interface ChatInterfaceProps {
  messages: Message[];
  isLoading: boolean;
  onSendMessage: (text: string) => void;
  activeConversationId: number | null;
}

export function ChatInterface({
  messages,
  isLoading,
  onSendMessage,
  activeConversationId,
}: ChatInterfaceProps) {
  const [input, setInput] = useState("");
  const [expandedIndex, setExpandedIndex] = useState<number | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;
    onSendMessage(input);
    setInput("");
  };

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const toggleExpand = (index: number) => {
    setExpandedIndex(expandedIndex === index ? null : index);
  };

  if (!activeConversationId) {
    return (
      <div className="flex flex-1 flex-col items-center justify-center bg-[#0d0e12] p-8 text-center">
        <div className="rounded-full bg-accent/10 p-6 text-accent animate-pulse">
          <MessageSquare size={48} />
        </div>
        <h2 className="mt-6 text-xl font-semibold text-white">
          Asistente Académico de la US
        </h2>
        <p className="mt-2 max-w-sm text-sm text-gray-400">
          Crea una nueva conversación o selecciona una del historial lateral para comenzar a resolver tus dudas sobre becas, matrículas y reglamentos.
        </p>
      </div>
    );
  }

  return (
    <div className="flex flex-1 flex-col bg-[#0d0e12]">
      {/* Header */}
      <div className="flex h-16 items-center justify-between border-b border-border bg-[#090a0c] px-6">
        <h3 className="font-semibold text-white flex items-center space-x-2">
          <Bot size={18} className="text-accent" />
          <span>Asistente RAG</span>
        </h3>
        <span className="rounded bg-accent/10 px-2.5 py-1 text-xs font-semibold text-accent">
          Llama-3 + Pinecone
        </span>
      </div>

      {/* Messages area */}
      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        {messages.length === 0 && (
          <div className="flex h-full flex-col items-center justify-center text-center">
            <Bot size={36} className="text-gray-600 mb-4 animate-bounce" />
            <p className="text-sm text-gray-500">
              Pregunta algo sobre normativas de grado, máster, liquidaciones de viaje o baremos de evaluación...
            </p>
          </div>
        )}

        {messages.map((msg, index) => {
          const isUser = msg.role === "user";
          const showRefs = msg.referencias && msg.referencias.length > 0;
          const isExpanded = expandedIndex === index;

          return (
            <div
              key={index}
              className={`flex items-start space-x-4 animate-fade-in ${
                isUser ? "justify-end" : "justify-start"
              }`}
            >
              {!isUser && (
                <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-accent text-white">
                  <Bot size={16} />
                </div>
              )}

              <div
                className={`max-w-[70%] rounded-xl px-4 py-3 text-sm shadow-md border ${
                  isUser
                    ? "bg-accent/10 border-accent/20 text-white"
                    : "bg-card border-border text-gray-200"
                }`}
              >
                {/* Content */}
                <div className="leading-relaxed text-gray-200">
                  {msg.content ? (
                    <ReactMarkdown
                      components={{
                        p: ({ node, ...props }) => <p className="mb-3 last:mb-0" {...props} />,
                        ul: ({ node, ...props }) => <ul className="list-disc list-inside mb-3 pl-2 space-y-1" {...props} />,
                        ol: ({ node, ...props }) => <ol className="list-decimal list-inside mb-3 pl-2 space-y-1" {...props} />,
                        li: ({ node, ...props }) => <li className="mb-0.5" {...props} />,
                        strong: ({ node, ...props }) => <strong className="font-bold text-white" {...props} />,
                        a: ({ node, ...props }) => <a className="text-accent hover:underline" target="_blank" rel="noopener noreferrer" {...props} />,
                        h1: ({ node, ...props }) => <h1 className="text-lg font-bold mt-4 mb-2 text-white" {...props} />,
                        h2: ({ node, ...props }) => <h2 className="text-base font-bold mt-4 mb-2 text-white" {...props} />,
                        h3: ({ node, ...props }) => <h3 className="text-sm font-bold mt-3 mb-1 text-white" {...props} />,
                        code: ({ node, ...props }) => <code className="bg-[#0d0e12] border border-border px-1.5 py-0.5 rounded text-xs font-mono text-accent" {...props} />,
                      }}
                    >
                      {msg.content + (msg.isStreaming ? " ▎" : "")}
                    </ReactMarkdown>
                  ) : (
                    msg.isStreaming && <span className="inline-block w-2 h-4 bg-accent animate-pulse">▎</span>
                  )}
                </div>

                {/* References */}
                {!isUser && showRefs && (
                  <div className="mt-3 border-t border-border/60 pt-2.5">
                    <button
                      onClick={() => toggleExpand(index)}
                      className="flex items-center space-x-1 text-xs font-semibold text-accent hover:text-white transition-all focus:outline-none"
                    >
                      <BookOpen size={12} />
                      <span>Fuentes y referencias consultadas</span>
                      {isExpanded ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
                    </button>

                    {isExpanded && (
                      <ul className="mt-2 space-y-1 rounded bg-[#0d0e12] border border-border/50 p-2 text-xs text-gray-400">
                        {msg.referencias?.map((ref, idx) => (
                          <li key={idx} className="list-disc list-inside">
                            {ref}
                          </li>
                        ))}
                      </ul>
                    )}
                  </div>
                )}
              </div>

              {isUser && (
                <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-[#1f222d] border border-border text-white">
                  <User size={16} />
                </div>
              )}
            </div>
          );
        })}
        <div ref={messagesEndRef} />
      </div>

      {/* Message input */}
      <div className="border-t border-border bg-[#090a0c] p-4">
        <form onSubmit={handleSubmit} className="flex items-center space-x-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={isLoading}
            placeholder="Escribe tu duda aquí (ej: ¿Cómo anulo la matrícula?)"
            className="flex-1 rounded-xl border border-border bg-[#0d0e12] px-4 py-3.5 text-sm text-white placeholder-gray-500 transition-all focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent/30 disabled:opacity-50"
          />
          <button
            type="submit"
            disabled={isLoading || !input.trim()}
            className="flex h-12 w-12 items-center justify-center rounded-xl bg-accent text-white shadow-lg transition-all hover:bg-accent-hover active:scale-95 disabled:opacity-30 disabled:pointer-events-none"
          >
            <Send size={18} />
          </button>
        </form>
      </div>
    </div>
  );
}
