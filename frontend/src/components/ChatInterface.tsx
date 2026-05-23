import React, { useState, useRef, useEffect } from "react";
import { MessageSquare, Send, BookOpen, User, Bot, ChevronDown, ChevronUp, ThumbsUp, ThumbsDown } from "lucide-react";
import { Message } from "../hooks/useChat";
import ReactMarkdown from "react-markdown";

interface ChatInterfaceProps {
  messages: Message[];
  isLoading: boolean;
  onSendMessage: (text: string) => void;
  activeConversationId: number | null;
  onSubmitFeedback: (messageId: number, feedback: boolean, comentario?: string) => Promise<void>;
}

export function ChatInterface({
  messages,
  isLoading,
  onSendMessage,
  activeConversationId,
  onSubmitFeedback,
}: ChatInterfaceProps) {
  const [input, setInput] = useState("");
  const [expandedIndex, setExpandedIndex] = useState<number | null>(null);
  const [activeCommentMsgId, setActiveCommentMsgId] = useState<number | null>(null);
  const [commentText, setCommentText] = useState("");
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
    <div className="flex flex-1 flex-col bg-[#0d0e12] min-h-0">
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
      <div className="flex-1 overflow-y-auto p-6 space-y-6 min-h-0">
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
                    msg.isStreaming && (
                      <div className="flex items-center space-x-2 text-xs text-gray-400 italic py-1">
                        <span className="h-1.5 w-1.5 rounded-full bg-accent animate-ping shrink-0" />
                        <span className="animate-pulse">{msg.status || "Pensando..."}</span>
                      </div>
                    )
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

                {/* Feedback */}
                {!isUser && msg.id && (
                  <div className="mt-2.5 flex flex-col space-y-2 border-t border-border/40 pt-2 text-xs text-gray-500">
                    <div className="flex items-center space-x-3">
                      <button
                        onClick={() => onSubmitFeedback(msg.id!, true)}
                        className={`hover:text-green-400 transition-colors flex items-center space-x-1 ${
                          msg.feedback === true ? "text-green-500 font-semibold" : ""
                        }`}
                        title="Respuesta útil"
                      >
                        <ThumbsUp size={12} className={msg.feedback === true ? "fill-green-500/20" : ""} />
                        <span>Útil</span>
                      </button>

                      <button
                        onClick={() => {
                          onSubmitFeedback(msg.id!, false);
                          setActiveCommentMsgId(msg.id!);
                          setCommentText(msg.feedback_comentario || "");
                        }}
                        className={`hover:text-red-400 transition-colors flex items-center space-x-1 ${
                          msg.feedback === false ? "text-red-500 font-semibold" : ""
                        }`}
                        title="Respuesta incorrecta o incompleta"
                      >
                        <ThumbsDown size={12} className={msg.feedback === false ? "fill-red-500/20" : ""} />
                        <span>No útil</span>
                      </button>
                      
                      {msg.feedback === false && msg.feedback_comentario && activeCommentMsgId !== msg.id && (
                        <span className="text-[10px] text-gray-400 italic truncate max-w-[200px]" title={msg.feedback_comentario}>
                          Comentario: "{msg.feedback_comentario}"
                        </span>
                      )}
                    </div>

                    {activeCommentMsgId === msg.id && (
                      <div className="mt-1 rounded-lg bg-[#0d0e12] border border-border/80 p-2 space-y-2">
                        <label className="block text-[9px] font-bold uppercase tracking-wider text-gray-400">
                          ¿Qué ha fallado en esta respuesta?
                        </label>
                        <textarea
                          value={commentText}
                          onChange={(e) => setCommentText(e.target.value)}
                          className="w-full rounded bg-[#090a0c] border border-border p-1.5 text-xs text-white placeholder-gray-500 focus:outline-none focus:border-accent"
                          placeholder="Ej: La fecha indicada es incorrecta..."
                          rows={2}
                        />
                        <div className="flex justify-end space-x-1.5 text-[9px]">
                          <button
                            type="button"
                            onClick={() => {
                              setActiveCommentMsgId(null);
                              setCommentText("");
                            }}
                            className="rounded border border-border px-2 py-0.5 text-gray-400 hover:text-white"
                          >
                            Cancelar
                          </button>
                          <button
                            type="button"
                            onClick={async () => {
                              await onSubmitFeedback(msg.id!, false, commentText);
                              setActiveCommentMsgId(null);
                              setCommentText("");
                            }}
                            className="rounded bg-accent px-2 py-0.5 text-white hover:bg-accent-hover font-semibold"
                          >
                            Enviar Comentario
                          </button>
                        </div>
                      </div>
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
